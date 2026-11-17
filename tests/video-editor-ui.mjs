import {chromium,expect} from '@playwright/test';import {execFileSync} from 'node:child_process';import path from 'node:path';import fs from 'node:fs/promises';import {bridge,installBridge} from './editor-bridge.mjs';
const b=await bridge();const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const code=`from pathlib import Path
import sys
sys.path.insert(0,'engine')
from runtime import command,locate
e=locate(Path('vendor'))
root=Path('.tools/editor-ui')
for name,color in [('red','red'),('blue','blue'),('green','green')]:
 target=root/(name+'.mp4')
 if not target.exists():command([e['ffmpeg'],'-v','error','-f','lavfi','-i','color=c='+color+':s=320x180:r=20:d=2','-f','lavfi','-i','sine=f=440:d=2','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',target])`;
 execFileSync('.venv/Scripts/python.exe',['-X','utf8','-c',code]);
 const page=await browser.newPage({viewport:{width:1500,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));await installBridge(page,b.port);await page.goto('http://127.0.0.1:1420/tests/editor-harness.html');
 const pick=async(files)=>page.evaluate(files=>window.__picks.push(files),files);
 await pick(['red','blue','green'].map(n=>path.join(b.data,n+'.mp4')));await page.getByRole('button',{name:'匯入素材',exact:true}).click();await expect(page.locator('.editor-clip')).toHaveCount(3);await expect(page.locator('video')).toBeVisible({timeout:30000});
 // Actual pointer trim: shorten the final clip by .5 sec, then undo/redo.
 const last=page.locator('.editor-clip').last();await last.scrollIntoViewIfNeeded();const right=await last.locator('.clip-trim.right').boundingBox();await page.mouse.move(right.x+right.width/2,right.y+25);await page.mouse.down();await page.mouse.move(right.x+right.width/2-22.5,right.y+25,{steps:8});await page.mouse.up();await expect(page.getByLabel('來源終點 秒',{exact:true})).toHaveValue(/1\.[45]/);await page.getByRole('button',{name:'復原',exact:true}).click();await expect(page.getByLabel('來源終點 秒',{exact:true})).toHaveValue('2');await page.getByRole('button',{name:'重做',exact:true}).click();
 // Move selected clip on the actual track without changing another clip.
 const block=await last.boundingBox();await page.mouse.move(block.x+25,block.y+15);await page.mouse.down();await page.mouse.move(block.x+70,block.y+15,{steps:8});await page.mouse.up();await expect(page.getByLabel('專案位置 秒',{exact:true})).toHaveValue('5');
 await page.getByRole('button',{name:'分離音軌',exact:true}).click();await expect(page.locator('.editor-track').filter({hasText:'A1'}).locator('.editor-clip')).toHaveCount(1);
 const targetTrack=page.locator('.editor-track[data-track="A2"]');await targetTrack.scrollIntoViewIfNeeded();const trackBox=await targetTrack.boundingBox();const assetBox=await page.locator('.editor-assets button').filter({hasText:'red.mp4'}).boundingBox();await page.mouse.move(assetBox.x+25,assetBox.y+20);await page.mouse.down();await page.mouse.move(trackBox.x+100,trackBox.y+35,{steps:12});await page.mouse.up();await expect(targetTrack.locator('.editor-clip')).toHaveCount(1);
 const project=path.join(b.data,'saved.fcvideo.json');await pick(project);await page.getByRole('button',{name:'儲存',exact:true}).click();await expect.poll(async()=>JSON.parse(await fs.readFile(project,'utf8').catch(()=>'{"clips":[]}')).clips.length).toBe(5);
 await page.getByRole('button',{name:'新增專案',exact:true}).click();await expect(page.locator('.editor-clip')).toHaveCount(0);await pick(project);await page.getByRole('button',{name:'開啟專案',exact:true}).click();await expect(page.locator('.editor-clip')).toHaveCount(5);
 await expect(page.locator('video')).toBeVisible({timeout:30000});await page.locator('video').evaluate(async v=>await v.play());await expect.poll(()=>page.locator('video').evaluate(v=>v.currentTime)).toBeGreaterThan(.1);await page.locator('video').evaluate(v=>v.pause());
 await page.getByRole('button',{name:'輸出完整作品',exact:true}).click();await expect.poll(async()=>{const s=await b.rpc('snapshot');return s.jobs.filter(j=>j.kind==='fcvideo'&&!j.previewOnly).at(-1)?.status},{timeout:30000}).toBe('completed');
 await page.locator('.app').evaluate(e=>e.scrollTop=0);await page.screenshot({path:'test-results/video-editor-ui.png'});expect(errors).toEqual([]);console.log('PASS: real engine UI import 3 sources, pointer trim/move, undo/redo, separate A1, save/reopen, actual preview playback, export.');
}finally{await browser.close();await b.close()}
