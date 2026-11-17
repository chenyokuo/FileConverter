// Opt-in real website and real Python API. No cookies, iframe API or mocked jobs.
import {chromium,expect} from '@playwright/test';import fs from 'node:fs/promises';
import {bridge,installAppBridge} from './editor-bridge.mjs';
const api=await bridge();const browser=await chromium.launch({channel:'msedge',headless:true});const results=[];
try{
 const page=await browser.newPage({viewport:{width:1500,height:960}});await installAppBridge(page,api.port);await page.goto('http://127.0.0.1:1420/');await expect(page.getByText('準備就緒',{exact:true})).toBeVisible({timeout:20000});await page.getByRole('button',{name:'網址下載',exact:true}).click();
 for(const id of ['4qXzCm9sRxE','aqz-KE-bpKQ']){
  const network=[];const listener=r=>{if(new URL(r.url()).hostname.endsWith('googlevideo.com'))network.push({status:r.status(),host:new URL(r.url()).hostname})};page.on('response',listener);
  await page.getByLabel('影片網址',{exact:true}).fill('https://www.youtube.com/watch?v='+id);await page.getByRole('button',{name:'解析網址',exact:true}).click();
  await expect(page.locator('.download-entry-title')).toBeVisible({timeout:45000});
  let directError=null;try{await expect.poll(()=>page.locator('.download-range video').evaluateAll(v=>v[0]?.readyState || 0),{timeout:22000}).toBeGreaterThanOrEqual(2)}catch{directError=await page.locator('.download-range').innerText()}
  const item={id,directPlayable:!directError,directError,network};
  if(directError){await page.getByRole('button',{name:'建立本機預覽（下載低畫質完整影片）',exact:true}).click();await expect.poll(()=>page.locator('.download-range video').evaluateAll(v=>v[0]?.readyState || 0),{timeout:180000}).toBeGreaterThanOrEqual(2);item.localFallback=true;}
  await page.locator('.download-range video').evaluate(async v=>{await v.play()});await expect.poll(()=>page.locator('.download-range video').evaluate(v=>v.currentTime)).toBeGreaterThan(.1);await page.locator('.download-range video').evaluate(v=>{v.pause();v.currentTime=2});await expect.poll(()=>page.locator('.download-range video').evaluate(v=>v.currentTime)).toBeGreaterThan(1.5);
  item.duration=await page.locator('.download-range video').evaluate(v=>v.duration);item.playerWidth=(await page.locator('.download-range .range-player').boundingBox()).width;expect(item.playerWidth).toBeLessThanOrEqual(640);
  await page.getByRole('textbox',{name:'起始時間',exact:true}).fill('00:00:01');await page.getByRole('textbox',{name:'起始時間',exact:true}).blur();await page.getByRole('textbox',{name:'結束時間',exact:true}).fill('00:00:03');await page.getByRole('textbox',{name:'結束時間',exact:true}).blur();await expect(page.getByText('選取時長：00:00:02',{exact:true})).toBeVisible();
  results.push(item);page.off('response',listener);
 }
 await page.screenshot({path:'test-results/r2-download.png'});console.log('PASS real-site direct/fallback playback, seek, synchronized fields and compact player.');
}finally{await fs.writeFile('test-results/r2-site-ui.json',JSON.stringify(results,null,2));await browser.close();await api.close()}
