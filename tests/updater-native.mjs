// Real Tauri IPC, GitHub HTTPS, official updater verification; no mocked bridge.
import {chromium,expect} from '@playwright/test';import fs from 'node:fs/promises';
const mode=process.argv[2]||'controls',label=process.env.FILE_CONVERTER_UPDATE_LABEL||`updater-${mode}`;
const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
await expect.poll(()=>browser.contexts()[0].pages().some(p=>/tauri.localhost|127.0.0.1:1420/.test(p.url())),{timeout:25000}).toBe(true);
const page=browser.contexts()[0].pages().find(p=>/tauri.localhost|127.0.0.1:1420/.test(p.url()));
const invoke=(command,args={})=>page.evaluate(({command,args})=>window.__TAURI_INTERNALS__.invoke(command,args),{command,args});
const rpc=(method,args={})=>invoke('engine_call',{method,args});
await expect(page.getByText('準備就緒',{exact:true})).toBeVisible({timeout:25000});
const before=await rpc('snapshot');const report={mode,actualNativeIPC:true,nativeVersion:await invoke('plugin:app|version')};let close=true;
try{
 await page.getByRole('button',{name:'設定',exact:true}).click();await page.getByRole('button',{name:'軟體更新',exact:true}).click();
 await expect(page.getByRole('button',{name:'檢查更新',exact:true})).toBeVisible();
 if(mode==='controls'){
  for(const command of ['plugin:updater|install','plugin:process|restart']){
   const error=await invoke(command,{rid:123}).then(()=>'',String);expect(error).toMatch(/not allowed|denied|not found|不允許/i);
  }report.rawLifecycleCommandsBlocked=true;
  const startup=page.getByRole('switch',{name:'啟動時檢查更新',exact:true});await startup.check();
  await expect.poll(async()=>(await rpc('snapshot')).settings.updater?.checkOnStartup).toBe(true);
  await startup.uncheck();await page.getByRole('switch',{name:'自動下載更新',exact:true}).check();
  await expect.poll(async()=>(await rpc('snapshot')).settings.updater?.autoDownload).toBe(true);
  await page.getByRole('switch',{name:'自動下載更新',exact:true}).uncheck();report.preferencePersistence=true;
  await page.getByLabel('更新通道').selectOption('stable');
  await page.getByRole('button',{name:'檢查更新',exact:true}).click();
  await expect.poll(async()=>(await invoke('update_status')).phase,{timeout:45000}).toMatch(/current|error/);
  report.check=await invoke('update_status');
 }else{
  await page.getByLabel('更新通道').selectOption('rc');await page.getByRole('button',{name:'檢查更新',exact:true}).click();
  const wanted=mode==='current'?'current':'available';await expect.poll(async()=>(await invoke('update_status')).phase,{timeout:45000}).toBe(wanted);
  report.check=await invoke('update_status');
  if(mode!=='current'){
   await page.getByRole('button',{name:'下載新版',exact:true}).click();
   const counts=[];await expect.poll(async()=>{const s=await invoke('update_status');counts.push(s.downloaded);if(s.phase==='error')throw Error(s.error);return s.phase},{timeout:1800000,intervals:[500,1000,2000]}).toBe('ready');
   const downloaded=await invoke('update_status');expect(downloaded.verified).toBe(true);expect(downloaded.downloaded).toBeGreaterThan(0);
   report.download={...downloaded,distinctByteCounts:[...new Set(counts)].length};
   if(mode==='install'){
    expect(downloaded.installed).toBe(true);
    // Corrupt the exact cached installer, call the genuine official install()
    // and prove it returns a signature error without exiting. Restore bytes.
    const file=await fs.open(downloaded.downloadPath,'r+');const first=Buffer.alloc(1);await file.read(first,0,1,0);await file.write(Buffer.from([first[0]^1]),0,1,0);await file.close();
    const error=await invoke('update_install').then(()=>'',String);expect(error).toMatch(/signature|verification|verify|簽章/i);report.corruptionRejected=true;
    const restored=await fs.open(downloaded.downloadPath,'r+');await restored.write(first,0,1,0);await restored.close();
    await invoke('update_download');expect((await invoke('update_status')).verified).toBe(true);
    const root=process.cwd();const input=root+'/.tools/editor-ui/red.mp4';
    const queued=await rpc('editor',{action:'enqueue',type:'fcvideo',project:{type:'fcvideo',version:1,width:1920,height:1080,fps:60,clips:[{id:'busy',source:input,track:'V1',in:0,out:2,at:0,speed:.1}],export:{hardware:'cpu',videoCodec:'h264',qualityPreset:'quality'}},format:'mp4',outputDir:root+'/.tools/updater-busy-output'});
    const blocked=await invoke('update_install');expect(blocked.phase).toBe('ready');expect(blocked.waitReason).toMatch(/工作/);report.realExportDeferredInstall=true;
    await rpc('cancel',{id:queued.id});await expect.poll(async()=>(await rpc('snapshot')).jobs.find(j=>j.id===queued.id)?.status,{timeout:45000}).toMatch(/cancelled|completed/);await rpc('clear',{ids:[queued.id]});
    await rpc('settings',{settings:before.settings});
    await page.screenshot({path:`test-results/${label}.png`});
    await fs.writeFile(`test-results/${label}.json`,JSON.stringify(report,null,2));close=false;
    // Success launches NSIS and ends this connection/process. Post-install
    // restart/version/user-data checks are performed by the Windows harness.
    await invoke('update_install').catch(()=>{});
   }
  }
 }
 if(close){await page.screenshot({path:`test-results/${label}.png`});await fs.writeFile(`test-results/${label}.json`,JSON.stringify(report,null,2));}
 console.log(`PASS ${label}`);
}finally{
 if(close){await rpc('settings',{settings:before.settings}).catch(()=>{});await invoke('shutdown_app').catch(()=>{});}
 await browser.close().catch(()=>{});
}
