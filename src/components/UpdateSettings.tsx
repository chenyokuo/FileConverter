import { version } from "../../package.json";
import { Download, RefreshCw } from "lucide-react";
import type { Settings } from "../types";
import type { UpdateController } from "../updates";
import { Button, Toggle } from "./ui";

const size = (bytes: number) => `${(bytes/1024/1024).toFixed(1)} MB`;
export function UpdateSettings({settings,setSettings,controller}: {settings:Settings;setSettings:(s:Settings)=>void;controller:UpdateController}) {
  const {view,check,download,install,openDownload}=controller;
  const preferences=settings.updater;
  const patch=(change:Partial<Settings["updater"]>)=>setSettings({...settings,updater:{...preferences,...change}});
  const working=["checking","downloading","installing"].includes(view.phase);
  return <section className="settings-card glass" data-material="settings" aria-label="軟體更新">
    <div className="section-heading"><div><h2>軟體更新</h2><p>目前版本 {version} · {view.installed?"Installer":"Portable／開發模式"}</p></div>
      <Button onClick={check} disabled={working}><RefreshCw size={16}/>{view.phase==="checking"?"正在檢查…":"檢查更新"}</Button>
    </div>
    <label className="field"><span>更新通道</span><select value={preferences.channel} disabled={working} onChange={e=>patch({channel:e.target.value as "rc"|"stable"})}><option value="stable">正式版</option><option value="rc">候選版（包含正式版）</option></select></label>
    {view.channel && view.channel!==preferences.channel && <p className="hint">通道已變更，請重新檢查更新。</p>}
    <Toggle label="啟動時檢查更新" checked={preferences.checkOnStartup} onChange={v=>patch({checkOnStartup:v})}/>
    <Toggle label="自動下載更新" checked={preferences.autoDownload} onChange={v=>patch({autoDownload:v,...(!v?{autoInstall:false}:{})})}/>
    <Toggle label="自動安裝更新（等待工作完成）" checked={preferences.autoInstall} onChange={v=>patch({autoInstall:v,...(v?{autoDownload:true}:{})})} disabled={!view.installed}/>
    {preferences.autoInstall && view.installed && <p className="hint">啟用後會在工作結束時安裝並重啟；請先儲存編輯專案。</p>}
    {!view.installed && <p className="hint">Portable 可檢查及下載經簽章驗證的 ZIP；請完整解壓到新資料夾後使用。</p>}
    <div role="status" aria-live="polite">
      {view.version && <h3>最新版本 {view.version}</h3>}
      {view.phase==="current" && <p>{view.message}</p>}
      {view.phase==="downloading" && <><p>下載中：{size(view.downloaded)}{view.total?` / ${size(view.total)}`:"（總大小未知）"}</p><progress style={{width:"100%"}} aria-label="更新下載進度" max={view.total||undefined} value={view.total?view.downloaded:undefined}/></>}
      {view.phase==="ready" && <p>{view.message}</p>}
      {view.phase==="installing" && <p>正在交由 NSIS 安裝，完成後會重新啟動。</p>}
      {view.waitReason && <p className="hint">{view.waitReason}</p>}
      {view.error && <p className="error" role="alert">{view.error}</p>}
    </div>
    {view.notes && <details open><summary>更新說明</summary><p style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{view.notes}</p></details>}
    {((view.phase==="available" || view.phase==="error") && view.version && view.channel===preferences.channel) && <Button variant="primary" onClick={download}><Download size={16}/>下載新版</Button>}
    {view.phase==="ready" && <div className="button-row">
      {view.installed && <Button variant="primary" disabled={view.channel!==preferences.channel} onClick={install}>安裝更新並重新啟動</Button>}
      <Button onClick={()=>void openDownload()}>開啟下載資料夾</Button>
    </div>}
  </section>;
}
