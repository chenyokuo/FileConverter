#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[cfg(windows)]
mod engine_job;

use serde_json::{json, Value};
use std::{collections::HashMap, io::{BufRead, BufReader, Write}, process::{Child, ChildStdin, Command, Stdio}, sync::{atomic::{AtomicU64, Ordering}, mpsc, Arc, Mutex}, time::Duration};
use tauri::{Emitter, Manager};

struct Bridge {
    #[cfg(windows)]
    engine_job: engine_job::EngineJob,
    child: Mutex<Child>,
    input: Mutex<ChildStdin>,
    pending: Arc<Mutex<HashMap<u64, mpsc::Sender<Result<Value, String>>>>>,
    serial: AtomicU64,
}

#[derive(Default)]
struct OpenRequests(Mutex<Vec<Value>>);

fn queue_open(app: &tauri::AppHandle, args: Vec<String>, cwd: &str) {
    let mut target = String::new();
    let mut paths = Vec::new();
    let mut iter = args.iter().skip(1);
    while let Some(arg) = iter.next() {
        if arg == "--target" {
            if let Some(value) = iter.next() { if ["pdf","jpg","mp3"].contains(&value.as_str()) { target=value.clone(); } }
        } else if arg == "--open" {
            if let Some(value) = iter.next() {
                let p=std::path::Path::new(value);
                let p=if p.is_absolute() { p.to_path_buf() } else { std::path::Path::new(cwd).join(p) };
                if p.is_file() { paths.push(p.to_string_lossy().into_owned()); }
            }
        }
    }
    if !paths.is_empty() {
        if let Some(requests)=app.try_state::<OpenRequests>() { if let Ok(mut list)=requests.0.lock() { list.push(json!({"paths":paths,"target":target})); } }
        let _=app.emit("open-files-ready", ());
    }
}

#[tauri::command]
fn take_open_requests(requests: tauri::State<'_, OpenRequests>) -> Vec<Value> {
    requests.0.lock().map(|mut list|std::mem::take(&mut *list)).unwrap_or_default()
}

#[tauri::command]
async fn engine_call(bridge: tauri::State<'_, Arc<Bridge>>, method: String, mut args: Value) -> Result<Value,String> {
    const ALLOWED: &[&str] = &["editor","snapshot","inspect","enqueue","settings","background","engines","cancel","retry","clear","open_output","registry","plan","hardware","tools","enqueue_tool","preview","preview_status","clear_preview","analyze_url","resolve_download","enqueue_download","automation","save_automation","delete_automation","watch_action","plan_workflow","enqueue_workflow","context_menu"];
    if !ALLOWED.contains(&method.as_str()) { return Err("Command is not allowed".into()); }
    let bridge = Arc::clone(bridge.inner());
    tauri::async_runtime::spawn_blocking(move || {
        if method == "inspect" {
            let mut hints = serde_json::Map::new();
            if let Some(paths) = args["paths"].as_array() {
                for path in paths.iter().filter_map(Value::as_str) {
                    use std::io::Read;
                    if let Ok(file) = std::fs::File::open(path) {
                        let mut bytes = Vec::new();
                        if file.take(16384).read_to_end(&mut bytes).is_ok() {
                            if let Some(kind) = infer::get(&bytes) {
                                hints.insert(path.to_string(), json!({"extension":kind.extension(),"mime":kind.mime_type()}));
                            }
                        }
                    }
                }
            }
            args["nativeHints"] = Value::Object(hints);
        }
        let id = bridge.serial.fetch_add(1, Ordering::Relaxed);
        let (tx,rx) = mpsc::channel();
        bridge.pending.lock().map_err(|e| e.to_string())?.insert(id,tx);
        let request = json!({"id":id,"method":method,"args":args}).to_string()+"\n";
        let result = (|| {
            let mut stdin = bridge.input.lock().map_err(|e| e.to_string())?;
            stdin.write_all(request.as_bytes()).map_err(|e| format!("Engine unavailable: {e}"))?;
            stdin.flush().map_err(|e|e.to_string())?;
            drop(stdin);
            rx.recv_timeout(Duration::from_secs(120)).map_err(|_| "Engine did not respond".to_string())?
        })();
        if let Ok(mut pending)=bridge.pending.lock() { pending.remove(&id); }
        result
    }).await.map_err(|e|e.to_string())?
}

#[tauri::command]
fn shutdown_app(app: tauri::AppHandle) {
    // The frontend flushes settings before requesting application exit.
    // Explicit exit also closes hidden windows and invokes sidecar cleanup.
    app.exit(0);
}

#[tauri::command]
fn native_material(app: tauri::AppHandle, enabled: bool) -> Result<(),String> {
    #[cfg(windows)] {
        let window = app.get_webview_window("main").ok_or("Window unavailable")?;
        if enabled { window_vibrancy::apply_mica(&window, Some(true)).map_err(|e| e.to_string())?; }
        else { window_vibrancy::clear_mica(&window).map_err(|e|e.to_string())?; }
    }
    Ok(())
}

fn start_engine(app: &tauri::App) -> Result<Arc<Bridge>, Box<dyn std::error::Error>> {
    let data = app.path().app_data_dir()?;
    std::fs::create_dir_all(&data)?;
    let resource = app.path().resource_dir()?;
    #[cfg(debug_assertions)]
    let mut command = {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
        let mut c = Command::new(root.join(".venv/Scripts/python.exe"));
        c.arg(root.join("engine/service.py")).arg("--engines").arg(root.join("vendor")); c
    };
    #[cfg(not(debug_assertions))]
    let mut command = {
        let mut c = Command::new(resource.join("binaries/FileConverterEngine/FileConverterEngine.exe"));
        c.arg("--engines").arg(resource.join("engines")); c
    };
    let _ = resource;
    command.arg("--data").arg(data).arg("--app-exe").arg(std::env::current_exe()?).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000 | 0x00000004);
    }
    let mut child = command.spawn()?;
    #[cfg(windows)]
    let engine_job=engine_job::EngineJob::attach(&mut child)?;
    let input = child.stdin.take().ok_or("No stdin")?;
    let output = child.stdout.take().ok_or("No stdout")?;
    let stderr = child.stderr.take().ok_or("No stderr")?;
    std::thread::spawn(move || { for line in BufReader::new(stderr).lines().map_while(Result::ok) { eprintln!("engine: {line}"); } });
    let pending: Arc<Mutex<HashMap<u64,mpsc::Sender<Result<Value,String>>>>> = Arc::default();
    let waiting = Arc::clone(&pending); let handle = app.handle().clone();
    std::thread::spawn(move || {
        for line in BufReader::new(output).lines().map_while(Result::ok) {
            if let Ok(value)=serde_json::from_str::<Value>(&line) {
                if value["event"]=="job" { let _=handle.emit("engine-job", &value["data"]); }
                else if let Some(id)=value["id"].as_u64() {
                    if let Ok(mut map)=waiting.lock() { if let Some(tx)=map.remove(&id) {
                        let answer=if let Some(error)=value["error"].as_str() { Err(error.to_string()) } else { Ok(value["result"].clone()) };
                        let _=tx.send(answer);
                    } }
                }
            }
        }
        if let Ok(mut map)=waiting.lock() { for (_,tx) in map.drain() { let _=tx.send(Err("Conversion engine stopped".into())); } }
        let _=handle.emit("engine-stopped", "本機轉檔引擎已停止，請重新啟動程式。");
    });
    Ok(Arc::new(Bridge {#[cfg(windows)] engine_job,child:Mutex::new(child),input:Mutex::new(input),pending,serial:AtomicU64::new(1)}))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app,args,cwd| {
            queue_open(app,args,&cwd);
            if let Some(window)=app.get_webview_window("main") { let _=window.unminimize(); let _=window.show(); let _=window.set_focus(); }
        }))
        .plugin(tauri_plugin_dialog::init())
        .manage(OpenRequests::default())
        .setup(|app| {
            app.manage(start_engine(app)?);
            queue_open(app.handle(),std::env::args().collect(),&std::env::current_dir()?.to_string_lossy());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![engine_call,native_material,shutdown_app,take_open_requests])
        .build(tauri::generate_context!()).expect("Could not start File Converter")
        .run(|app,event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(bridge)=app.try_state::<Arc<Bridge>>() {
                    #[cfg(windows)] bridge.engine_job.terminate();
                    if let Ok(mut child)=bridge.child.lock() { let _=child.kill(); let _=child.wait(); }
                }
            }
        });
}
