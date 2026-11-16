import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');const page=browser.contexts()[0].pages().find(p=>p.url().includes('1420')||p.url().includes('tauri.localhost'));const invoke=(cmd,args={})=>page.evaluate(({cmd,args})=>window.__TAURI_INTERNALS__.invoke(cmd,args),{cmd,args});const rpc=(method,args={})=>invoke('engine_call',{method,args});
const before=await rpc('context_menu');const version=await browser.version();
try{
 await page.getByRole('button',{name:'設定',exact:true}).click();await page.getByRole('button',{name:'進階',exact:true}).click();
 if(before.enabled)await page.getByRole('button',{name:'停用並移除右鍵項目',exact:true}).click();
 await page.getByRole('button',{name:'啟用右鍵項目',exact:true}).click();await expect(page.getByRole('button',{name:'停用並移除右鍵項目',exact:true})).toBeVisible();expect((await rpc('context_menu')).enabled).toBe(true);
 await page.getByRole('button',{name:'停用並移除右鍵項目',exact:true}).click();expect((await rpc('context_menu')).enabled).toBe(false);
 await page.getByRole('button',{name:'轉換檔案',exact:true}).click();
 const file=path.join(process.cwd(),'.tools/ui-fixtures/中文 alpha & 測試.png');
 const child=spawn(process.env.FILE_CONVERTER_TEST_EXE||path.join(process.cwd(),'src-tauri/target/debug/FileConverter.exe'),['--open',file,'--target','jpg'],{windowsHide:true,stdio:'ignore'});
 const exit=await new Promise(resolve=>child.on('exit',resolve));expect(exit).toBe(0);
 await expect(page.locator('.draft-row').filter({hasText:'中文 alpha & 測試.png'}).locator('select')).toHaveValue('jpg',{timeout:15000});
 await fs.writeFile('test-results/windows-integration.json',JSON.stringify({browser:version,contextMenuEnableDisable:true,singleInstanceForwarding:true,automaticConversion:false,defaultFileAssociationsChanged:false},null,2));console.log('PASS Windows optional shell toggle and second-instance forwarding',version);
}finally{await rpc('context_menu',{enabled:before.enabled});await page.reload();await browser.close();}
