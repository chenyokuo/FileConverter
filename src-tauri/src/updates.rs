//! Official Tauri updater behind app-owned commands: the webview cannot bypass
//! signature checks, select arbitrary endpoints, or install while work is active.
use serde_json::{json, Value};
use std::{collections::HashMap, path::PathBuf, sync::{Arc, Mutex}, time::{Duration, Instant}};
use tauri::{Emitter, Manager};
use tauri_plugin_updater::{Update, UpdaterExt};

const REPO: &str = "chenyokuo/FileConverter";
// Non-installing publisher preflight, using the same minisign verifier and signed
// version rules as the official updater. No key or endpoint can be overridden.
pub fn verify_release_cli()->Option<Result<(),String>>{
    let args:Vec<String>=std::env::args().collect();
    if args.get(1).map(String::as_str)!=Some("--verify-release-signature"){return None}
    Some((||{
        if args.len()!=5{return Err("Expected artifact, signature file, version".into())}
        use base64::Engine;
        let decode=|v:&str|->Result<String,String>{String::from_utf8(base64::engine::general_purpose::STANDARD.decode(v.trim()).map_err(|e|e.to_string())?).map_err(|e|e.to_string())};
        let config:Value=serde_json::from_str(include_str!("../tauri.conf.json")).map_err(|e|e.to_string())?;
        let key=minisign_verify::PublicKey::decode(&decode(config["plugins"]["updater"]["pubkey"].as_str().ok_or("Missing public key")?)?).map_err(|e|e.to_string())?;
        let signature=minisign_verify::Signature::decode(&decode(&std::fs::read_to_string(&args[3]).map_err(|e|e.to_string())?)?).map_err(|e|e.to_string())?;
        let data=std::fs::read(&args[2]).map_err(|e|e.to_string())?;
        key.verify(&data,&signature,true).map_err(|e|e.to_string())?;
        let signed=signature.trusted_comment().split('\t').find_map(|f|f.strip_prefix("version:")).ok_or("Missing signed version")?;
        if semver::Version::parse(signed.trim_start_matches('v')).map_err(|e|e.to_string())?!=semver::Version::parse(&args[4]).map_err(|e|e.to_string())?{return Err("Signed version mismatch".into())}
        Ok(())
    })())
}
#[derive(Default)]
pub struct Activity {
    pub calls: usize,
    pub installing: bool,
    pub jobs: HashMap<String, String>,
}
impl Activity {
    pub fn busy(&self) -> bool {
        self.calls > 0 || self.jobs.values().any(|s| matches!(s.as_str(), "queued" | "running" | "cancelling"))
    }
}
pub struct Session {
    update: Option<Update>,
    pub view: Value,
    file: Option<PathBuf>,
}
pub struct Updates(pub Arc<Mutex<Session>>);
impl Default for Updates {
    fn default() -> Self { Self(Arc::new(Mutex::new(Session { update: None, file: None, view: json!({"phase":"idle","downloaded":0,"verified":false}) }))) }
}
fn installed() -> bool {
    std::env::current_exe().ok().and_then(|p|p.parent().map(|p|p.join("uninstall.exe").is_file())).unwrap_or(false)
}
fn event(app: &tauri::AppHandle, state: &Arc<Mutex<Session>>, patch: Value) -> Value {
    let mut session=state.lock().unwrap();
    for (k,v) in patch.as_object().unwrap() { session.view[k]=v.clone(); }
    session.view["installed"]=json!(installed());
    let result=session.view.clone();
    let _=app.emit("update-state", &result); result
}
pub fn work_method(method: &str) -> bool {
    matches!(method,"editor"|"enqueue"|"retry"|"enqueue_tool"|"enqueue_download"|"download_preview"|"preview"|"enqueue_workflow"|"watch_action")
}
fn select_release<'a>(releases:&'a [Value],channel:&str)->Option<(semver::Version,&'a Value)>{
    releases.iter().filter(|r|r["draft"]!=true)
        .filter_map(|r|Some((semver::Version::parse(r["tag_name"].as_str()?.trim_start_matches('v')).ok()?,r)))
        .filter(|(v,r)|channel=="rc" || (v.pre.is_empty() && r["prerelease"]!=true))
        .filter(|(_,r)|r["assets"].as_array().is_some_and(|a|a.iter().any(|a|a["name"]=="latest.json")))
        .max_by(|(a,_),(b,_)|a.cmp(b))
}
#[tauri::command]
pub fn update_status(app: tauri::AppHandle, state: tauri::State<Updates>, bridge: tauri::State<Arc<crate::Bridge>>) -> Value {
    let busy=bridge.activity.lock().unwrap().busy();
    event(&app,&state.0,json!({"busy":busy}))
}
#[tauri::command]
pub async fn update_check(app: tauri::AppHandle, state: tauri::State<'_,Updates>, channel: String) -> Result<Value,String> {
    if !["stable","rc"].contains(&channel.as_str()) { return Err("無效更新通道".into()) }
    {
        let mut s=state.0.lock().unwrap();
        if ["checking","downloading","installing"].contains(&s.view["phase"].as_str().unwrap_or("")) { return Err("更新作業進行中".into()) }
        s.update=None; s.file=None;
        s.view["phase"]=json!("checking");
    }
    event(&app,&state.0,json!({"phase":"checking","error":null,"waitReason":null,"version":null,"notes":"","downloaded":0,"total":null,"verified":false,"downloadPath":null,"channel":channel}));
    let result=check_inner(&app,&state.0,&channel).await;
    match result {
        Ok(value)=>Ok(value),
        Err(error)=>{event(&app,&state.0,json!({"phase":"error","error":error}));Err(error)}
    }
}
async fn check_inner(app: &tauri::AppHandle, state: &Arc<Mutex<Session>>, channel: &str) -> Result<Value,String> {
    let client=reqwest::Client::builder().timeout(Duration::from_secs(30)).user_agent(format!("FileConverter/{}",app.package_info().version)).build().map_err(|e|e.to_string())?;
    // A GitHub /latest redirect excludes prereleases. Select the greatest SemVer
    // from published releases instead; pagination is unnecessary for our newest 100.
    let releases=client.get(format!("https://api.github.com/repos/{REPO}/releases?per_page=100")).send().await.map_err(|e|e.to_string())?.error_for_status().map_err(|e|format!("GitHub 更新檢查失敗：{e}"))?.json::<Vec<Value>>().await.map_err(|e|e.to_string())?;
    let chosen=select_release(&releases,channel);
    let Some((version,release))=chosen else { return Ok(event(app,state,json!({"phase":"current","message":"此通道尚無已發布的更新","version":null}))) };
    let endpoint=release["assets"].as_array().unwrap().iter().find(|a|a["name"]=="latest.json").unwrap()["browser_download_url"].as_str().ok_or("更新資訊缺少網址")?;
    let url=reqwest::Url::parse(endpoint).map_err(|e|e.to_string())?;
    if url.scheme()!="https" || url.host_str()!=Some("github.com") || !url.path().starts_with(&format!("/{REPO}/releases/download/")) { return Err("更新資訊不是本專案的 GitHub Release".into()) }
    let cleanup=app.clone();
    let update=app.updater_builder().target(if installed(){"windows-x86_64"}else{"windows-x86_64-portable"})
        .endpoints(vec![url]).map_err(|e|e.to_string())?.timeout(Duration::from_secs(30))
        .on_before_exit(move || { crate::stop_engine(&cleanup); cleanup.cleanup_before_exit(); })
        .build().map_err(|e|e.to_string())?.check().await.map_err(|e|format!("Manifest 檢查失敗：{e}"))?;
    if let Some(update)=update {
        if update.version!=version.to_string() { return Err("Manifest 與 Release 版本不一致".into()) }
        if update.download_url.scheme()!="https" || update.download_url.host_str()!=Some("github.com") || !update.download_url.path().starts_with(&format!("/{REPO}/releases/download/")) { return Err("更新檔不是本專案的 GitHub Release".into()) }
        let notes=update.body.clone().unwrap_or_default();
        state.lock().unwrap().update=Some(update);
        Ok(event(app,state,json!({"phase":"available","version":version.to_string(),"notes":notes,"message":"有新版本可下載"})))
    } else { Ok(event(app,state,json!({"phase":"current","version":version.to_string(),"notes":release["body"],"message":"目前已是此通道的最新版本"}))) }
}
#[tauri::command]
pub async fn update_download(app: tauri::AppHandle, state: tauri::State<'_,Updates>) -> Result<Value,String> {
    let update={
        let mut s=state.0.lock().unwrap();
        if !["available","error"].contains(&s.view["phase"].as_str().unwrap_or("")) { return Err("請先檢查更新".into()) }
        let u=s.update.clone().ok_or("請先檢查更新")?; s.view["phase"]=json!("downloading"); u
    };
    event(&app,&state.0,json!({"phase":"downloading","error":null,"downloaded":0,"total":null,"verified":false}));
    let result=download_inner(&app,&state.0,update).await;
    match result { Ok(value)=>Ok(value),Err(error)=>{event(&app,&state.0,json!({"phase":"error","error":error,"verified":false}));Err(error)} }
}
async fn download_inner(app: &tauri::AppHandle,state: &Arc<Mutex<Session>>,mut update: Update)->Result<Value,String>{
    let version=semver::Version::parse(&update.version).map_err(|e|e.to_string())?;
    let directory=app.path().app_data_dir().map_err(|e|e.to_string())?.join("updates").join(version.to_string());
    std::fs::create_dir_all(&directory).map_err(|e|e.to_string())?;
    let file=directory.join(if installed(){"FileConverter-setup.exe"}else{"FileConverter-Portable.zip"});
    update.timeout=Some(Duration::from_secs(1800));
    if let Ok(payload)=std::fs::read(&file) {
        if update.verify(&payload).is_ok(){
            state.lock().unwrap().file=Some(file.clone());
            return Ok(event(app,state,json!({"phase":"ready","downloaded":payload.len(),"total":payload.len(),"verified":true,"downloadPath":file,"message":"已重新驗證快取更新檔的簽章"})))
        }
    }
    let mut bytes=0u64;let mut last=Instant::now()-Duration::from_secs(1);
    let payload=update.download(|length,total|{
        bytes+=length as u64;
        if last.elapsed()>Duration::from_millis(100) { event(app,state,json!({"downloaded":bytes,"total":total}));last=Instant::now(); }
    },||{}).await.map_err(|e|format!("下載或 Tauri 簽章驗證失敗：{e}"))?;
    // download() has verified the signature; never expose a partial/unverified file.
    std::fs::write(&file,&payload).map_err(|e|e.to_string())?;
    state.lock().unwrap().file=Some(file.clone());
    Ok(event(app,state,json!({"phase":"ready","downloaded":payload.len(),"total":payload.len(),"verified":true,"downloadPath":file,"message":if installed(){"簽章驗證通過，可安裝更新"}else{"Portable ZIP 已下載並通過簽章驗證；請完整解壓至新資料夾"}})))
}
#[tauri::command]
pub async fn update_install(app: tauri::AppHandle,state:tauri::State<'_,Updates>,bridge:tauri::State<'_,Arc<crate::Bridge>>) -> Result<Value,String> {
    if !installed(){return Err("Portable 請下載新版 ZIP，完整解壓至新資料夾".into())}
    let (update,file)={let s=state.0.lock().unwrap();if s.view["phase"]!="ready" {return Err("請先下載並驗證更新".into())} (s.update.clone().ok_or("請重新檢查更新")?,s.file.clone().ok_or("更新檔不存在")?)};
    {
        let mut a=bridge.activity.lock().unwrap();
        if a.busy() || a.installing {return Ok(event(&app,&state.0,json!({"waitReason":"工作尚未結束，更新將等待轉檔、下載、預覽或匯出完成","busy":true})))}
        a.installing=true;
    }
    // Watchers can create jobs without a frontend request. Do not close an active
    // watcher session; the user can pause it in the existing workflow page.
    let snapshot=crate::bridge_request(Arc::clone(bridge.inner()),"automation".into(),json!({})).await;
    let allowed=match &snapshot {Ok(s)=>!s["states"].as_object().is_some_and(|m|m.values().any(|v|v=="running")),Err(_)=>false};
    if !allowed || bridge.activity.lock().unwrap().busy() {
        bridge.activity.lock().unwrap().installing=false;
        return Ok(event(&app,&state.0,json!({"waitReason":"請等待工作完成並暫停監看資料夾，再安裝更新","busy":true})))
    }
    event(&app,&state.0,json!({"phase":"installing","waitReason":null,"busy":false}));
    let result=tauri::async_runtime::spawn_blocking(move||{
        let payload=std::fs::read(file).map_err(|e|e.to_string())?;
        update.install(payload).map_err(|e|e.to_string())
    }).await.map_err(|e|e.to_string()).and_then(|r|r);
    bridge.activity.lock().unwrap().installing=false;
    match result { Ok(())=>Ok(event(&app,&state.0,json!({"phase":"ready"}))),Err(error)=>{event(&app,&state.0,json!({"phase":"error","error":error,"verified":false}));Err(error)} }
}
#[tauri::command]
pub fn update_open_download(state:tauri::State<Updates>)->Result<(),String>{
    let file=state.0.lock().unwrap().file.clone().ok_or("尚未下載更新")?;
    #[cfg(windows)] {std::process::Command::new("explorer.exe").arg(file.parent().unwrap()).spawn().map_err(|e|e.to_string())?;}
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn release(v:&str,draft:bool,prerelease:bool)->Value{json!({"tag_name":v,"draft":draft,"prerelease":prerelease,"assets":[{"name":"latest.json"}]})}
    #[test]fn channels_use_semver_not_release_order(){
        let releases=vec![release("v1.1.0-rc.9",false,true),release("v1.1.0-rc.10",false,true),release("v9.0.0",true,false),release("updates-rc",false,true),release("v1.0.0",false,false)];
        assert_eq!(select_release(&releases,"rc").unwrap().0.to_string(),"1.1.0-rc.10");
        assert_eq!(select_release(&releases,"stable").unwrap().0.to_string(),"1.0.0");
        let mut final_release=releases;final_release.push(release("v1.1.0",false,false));
        assert_eq!(select_release(&final_release,"rc").unwrap().0.to_string(),"1.1.0");
        assert!(select_release(&[],"rc").is_none());
    }
    #[test]fn every_active_task_and_rpc_blocks_installation(){
        let mut a=Activity::default();assert!(!a.busy());
        for status in ["queued","running","cancelling"]{a.jobs.insert("preview-or-export".into(),status.into());assert!(a.busy())}
        a.jobs.insert("preview-or-export".into(),"completed".into());assert!(!a.busy());
        a.calls=1;assert!(a.busy());
        for method in ["editor","enqueue","enqueue_download","download_preview","preview","enqueue_workflow","watch_action"]{assert!(work_method(method));}
    }
}
