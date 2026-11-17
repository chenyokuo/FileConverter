import {chromium,expect} from '@playwright/test';import fs from 'node:fs/promises';import path from 'node:path';
const b=await chromium.connectOverCDP('http://127.0.0.1:9222'),c=b.contexts()[0];await expect.poll(()=>c.pages().some(p=>p.url().includes('tauri.localhost')),{timeout:20000}).toBe(true);const page=c.pages().find(p=>p.url().includes('tauri.localhost'));
const invoke=(cmd,args={})=>page.evaluate(({cmd,args})=>window.__TAURI_INTERNALS__.invoke(cmd,args),{cmd,args}),rpc=(method,args={})=>invoke('engine_call',{method,args});
const snapshot=await rpc('snapshot');const report={version:await b.version(),engines:snapshot.engines,jobs:[]};const base=process.env.FILE_CONVERTER_INSTALL_ROOT||path.join(process.cwd(),'.tools/p5-installed');
for(const key of ['ffmpeg','ffprobe','soffice','pandoc','calibre','ghostscript','sevenzip','deno','tessdata','font'])expect(snapshot.engines[key].replace(/^\\\\\?\\/,'').toLowerCase().startsWith(base.toLowerCase())).toBe(true);
const outputDir=path.join(process.cwd(),'.tools/p5-installed-output');let ids=[];
try{
 for(const [file,format] of [[path.join(process.cwd(),'.tools/ui-fixtures/中文 alpha & 測試.png'),'jpg'],[path.join(process.cwd(),'.tools/p5-matrix/來源 中文 & docx.docx'),'pdf']]){const jobs=await rpc('enqueue',{jobs:[{sources:[file],format,outputDir,options:{hardware:'cpu'}}]});ids.push(jobs[0].id);}
 const ocr=await rpc('enqueue_tool',{operation:'pdf.ocr',sources:[path.join(process.cwd(),'.tools/p5-installed-fixtures/繁中掃描.pdf')],params:{language:'chi_tra+eng',dpi:200,onlyScans:true},outputDir});ids.push(ocr[0].id);
 await expect.poll(async()=>(await rpc('snapshot')).jobs.filter(j=>ids.includes(j.id)).map(j=>j.status).every(s=>['completed','failed','cancelled'].includes(s)),{timeout:120000}).toBe(true);
 expect((await rpc('snapshot')).jobs.filter(j=>ids.includes(j.id)).map(j=>j.status)).toEqual(['completed','completed','completed']);
 report.jobs=(await rpc('snapshot')).jobs.filter(j=>ids.includes(j.id));
 if(process.env.FILE_CONVERTER_CONTEXT_UNINSTALL_TEST!=='0'){await rpc('context_menu',{enabled:true});expect((await rpc('context_menu')).enabled).toBe(true);report.contextMenuEnabledForUninstallTest=true;}
 await page.getByRole('button',{name:'設定',exact:true}).click();await page.getByRole('button',{name:'關於 File Converter',exact:true}).click();await expect(page.locator('.about-card')).toContainText('v'+JSON.parse(await fs.readFile('package.json','utf8')).version);await page.screenshot({path:'test-results/installed-about.png'});
 await fs.writeFile(process.env.FILE_CONVERTER_SMOKE_REPORT||'test-results/installed-smoke.json',JSON.stringify(report,null,2));console.log('PASS app-local runtimes, image, Office PDF and Chinese OCR',report.contextMenuEnabledForUninstallTest?'with shell registration':'');
}finally{await rpc('clear',{ids});await rpc('settings',{settings:snapshot.settings});await invoke('shutdown_app');await b.close().catch(()=>{});}
