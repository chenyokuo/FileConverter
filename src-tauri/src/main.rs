#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::{collections::HashMap, io::{BufRead, BufReader, Write}, process::{Child, ChildStdin, Command, Stdio}, sync::{atomic::{AtomicU64, Ordering}, mpsc, Arc, Mutex}, time::Duration};
use tauri::{Emitter, Manager};

struct Bridge {
    child: Mutex<Child>,
    input: Mutex<ChildStdin>,
    pending: Arc<Mutex<HashMap<u64, mpsc::Sender<Result<Value, String>>>>>,
    serial: AtomicU64,
}

#[tauri::command]
async fn engine_call(bridge: tauri::State<'_, Arc<Bridge>>, method: String, mut args: Value) -> Result<Value,String> {
    const ALLOWED: &[&str] = &["snapshot","inspect","enqueue","settings","background","engines","cancel","retry","clear","open_output","registry","plan","hardware","tools","enqueue_tool","preview","preview_status","clear_preview","analyze_url","resolve_download","enqueue_download"];
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
    command.arg("--data").arg(data).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)] {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = command.spawn()?;
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
    Ok(Arc::new(Bridge {child:Mutex::new(child),input:Mutex::new(input),pending,serial:AtomicU64::new(1)}))
}

fn main() {
    tauri::Builder::default().plugin(tauri_plugin_dialog::init())
        .setup(|app| { app.manage(start_engine(app)?); Ok(()) })
        .invoke_handler(tauri::generate_handler![engine_call,native_material,shutdown_app])
        .build(tauri::generate_context!()).expect("Could not start File Converter")
        .run(|app,event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(bridge)=app.try_state::<Arc<Bridge>>() {
                    if let Ok(mut child)=bridge.child.lock() { let _=child.kill(); let _=child.wait(); }
                }
            }
        });
}
