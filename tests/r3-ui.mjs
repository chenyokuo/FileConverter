import {chromium,expect} from '@playwright/test';import {execFileSync} from 'node:child_process';import fs from 'node:fs/promises';import path from 'node:path';import {bridge,installBridge} from './editor-bridge.mjs';
const api=await bridge();const browser=await chromium.launch({channel:'msedge',headless:true});const results=[];
try{
 execFileSync('.venv/Scripts/python.exe',['-X','utf8','-c',`from pathlib import Path
from PIL import Image,ImageDraw
root=Path('.tools/editor-ui')
for w,h in [(1255,893),(1920,1080),(1080,1920),(4000,3000),(1000,1000)]:
 im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);d.rectangle((20,20,w-21,h-21),fill=(90,150,200,255));d.rectangle((25,25,75,75),fill='red');d.rectangle((w-76,h-76,w-26,h-26),fill='blue');im.save(root/f'{w}x{h}.png')`]);
 const page=await browser.newPage({viewport:{width:1500,height:1100}});await installBridge(page,api.port);await page.goto('http://127.0.0.1:1420/tests/editor-harness.html?image');
 const pick=files=>page.evaluate(files=>window.__picks.push(files),files);
 for(const [w,h] of [[1255,893],[1920,1080],[1080,1920],[4000,3000],[1000,1000]]){
  await page.getByRole('button',{name:'新增圖片',exact:true}).click();await pick([path.join(api.data,`${w}x${h}.png`)]);await page.getByRole('button',{name:'開啟圖片／加入圖層',exact:true}).click();await expect(page.locator('.image-layer-list .row')).toHaveCount(1);
  const visible=async()=>page.locator('.image-stage').evaluate(e=>{const b=e.getBoundingClientRect(),v=e.parentElement.getBoundingClientRect();return b.width<=v.width-32 && b.height<=v.height-32 && b.left>=v.left && b.top>=v.top && b.right<=v.right && b.bottom<=v.bottom});
  await expect.poll(visible).toBe(true);await page.setViewportSize({width:1280,height:720});await expect.poll(visible).toBe(true);
  await page.getByRole('button',{name:'100%',exact:true}).click();expect(await page.locator('.image-stage').evaluate(e=>e.clientWidth)).toBe(w);await page.setViewportSize({width:1366,height:768});expect(await page.locator('.image-stage').evaluate(e=>e.clientWidth)).toBe(w);
  await page.getByRole('button',{name:'Fit to Canvas',exact:true}).click();await expect.poll(visible).toBe(true);
  const project=path.join(api.data,`r3-${w}.fcimage.json`);await pick(project);await page.getByRole('button',{name:'儲存圖片專案',exact:true}).click();await expect.poll(async()=>JSON.parse(await fs.readFile(project,'utf8').catch(()=>'{"width":0}')).width).toBe(w);const p=JSON.parse(await fs.readFile(project,'utf8'));expect(p.height).toBe(h);
  const exports=[];for(const format of ['png','jpg','webp']){const job=await api.rpc('editor',{action:'enqueue',type:'fcimage',project:p,format,outputDir:path.join(api.data,'r3-output')});await expect.poll(async()=>{const s=await api.rpc('snapshot');const j=s.jobs.find(x=>x.id===job.id);if(j?.status==='failed')throw Error(j.error);exports.push(...(j?.status==='completed'?j.outputs:[]));return j?.status},{timeout:40000}).toBe('completed');}
  const files=[...new Set(exports)];execFileSync('.venv/Scripts/python.exe',['-X','utf8','-c',`import json,sys
from PIL import Image
for p in json.loads(sys.argv[1]):
 with Image.open(p) as im:
  im.load();assert im.size==(${w},${h});assert im.getpixel((50,50))[0]>200;assert im.getpixel((${w}-50,${h}-50))[2]>200
  if im.format!='JPEG':assert im.mode=='RGBA' and im.getpixel((0,0))[3]==0`,JSON.stringify(files)]);
  // Exercise image-space tools at every tested resolution, then restore the original.
  const save=async()=>{await page.getByRole('button',{name:'儲存圖片專案',exact:true}).click();};
  const read=async()=>JSON.parse(await fs.readFile(project,'utf8'));
  const canvas=page.getByLabel('圖片編輯畫布');await canvas.scrollIntoViewIfNeeded();let b=await canvas.boundingBox();
  await page.getByRole('button',{name:'畫筆',exact:true}).click();await page.mouse.move(b.x+b.width*.2,b.y+b.height*.3);await page.mouse.down();await page.mouse.move(b.x+b.width*.4,b.y+b.height*.5,{steps:5});await page.mouse.up();await save();await expect.poll(async()=>(await read()).layers.length).toBe(2);let edited=await read();expect(Math.abs(edited.layers[1].points[0][0]-w*.2)).toBeLessThan(2);expect(Math.abs(edited.layers[1].points[0][1]-h*.3)).toBeLessThan(2);await page.getByRole('button',{name:'復原',exact:true}).click();
  await page.getByRole('button',{name:'裁切',exact:true}).click();await canvas.scrollIntoViewIfNeeded();b=await canvas.boundingBox();await page.mouse.move(b.x+b.width*.1,b.y+b.height*.1);await page.mouse.down();await page.mouse.move(b.x+b.width*.7,b.y+b.height*.6,{steps:5});await page.mouse.up();await save();await expect.poll(async()=>(await read()).crop[2]).toBeLessThan(w*.7);edited=await read();expect(Math.abs(edited.crop[0]-w*.1)).toBeLessThan(2);expect(Math.abs(edited.crop[2]-w*.6)).toBeLessThan(2);await page.getByRole('button',{name:'復原',exact:true}).click();
  await page.getByRole('button',{name:'選取／移動',exact:true}).click();await canvas.scrollIntoViewIfNeeded();b=await canvas.boundingBox();await page.mouse.move(b.x+b.width*.4,b.y+b.height*.4);await page.mouse.down();await page.mouse.move(b.x+b.width*.45,b.y+b.height*.45,{steps:5});await page.mouse.up();await save();await expect.poll(async()=>(await read()).layers[0].x).toBeGreaterThan(0);edited=await read();expect(Math.abs(edited.layers[0].x-w*.05)).toBeLessThan(2);await page.getByRole('button',{name:'復原',exact:true}).click();await save();await expect.poll(async()=>(await read()).layers[0].x).toBe(0);
  await page.getByRole('button',{name:'新增圖片',exact:true}).click();await pick(project);await page.getByRole('button',{name:'開啟圖片專案',exact:true}).click();await expect(page.locator('.image-layer-list .row')).toHaveCount(1);await expect.poll(visible).toBe(true);
  results.push({width:w,height:h,fitEdges:true,manualPreservedOnResize:true,formats:['png','jpg','webp'],pixelsAlpha:true});
  if(w===1255){await page.screenshot({path:'test-results/r3-fit.png'});}
 }
 // Real SVG inverse-coordinate brush, crop and wheel while the fitted square is active.
 await page.getByRole('button',{name:'畫筆',exact:true}).click();const box=await page.getByLabel('圖片編輯畫布').boundingBox();await page.mouse.move(box.x+box.width*.2,box.y+box.height*.3);await page.mouse.down();await page.mouse.move(box.x+box.width*.4,box.y+box.height*.5,{steps:6});await page.mouse.up();await expect(page.locator('.image-layer-list .row')).toHaveCount(2);
 const project=path.join(api.data,'r3-brush.fcimage.json');await pick(project);await page.getByRole('button',{name:'另存圖片專案',exact:true}).click();await expect.poll(async()=>JSON.parse(await fs.readFile(project,'utf8').catch(()=>'{"layers":[]}')).layers.length).toBe(2);const p=JSON.parse(await fs.readFile(project,'utf8'));expect(p.layers[1].points[0][0]).toBeCloseTo(200,-1);expect(p.layers[1].points[0][1]).toBeCloseTo(300,-1);
 await page.getByRole('button',{name:'復原',exact:true}).click();await expect(page.locator('.image-layer-list .row')).toHaveCount(1);await page.getByRole('button',{name:'重做',exact:true}).click();await expect(page.locator('.image-layer-list .row')).toHaveCount(2);
 const old=await page.locator('.image-stage').evaluate(e=>e.clientWidth);await page.mouse.move(box.x+50,box.y+50);await page.mouse.wheel(0,-200);await expect.poll(()=>page.locator('.image-stage').evaluate(e=>e.clientWidth)).toBeGreaterThan(old);
 console.log('PASS five real image sizes, auto/manual fit, 15 exports with corner pixels/alpha, inverse SVG brush coordinates, undo/redo and wheel.');
}finally{await fs.writeFile('test-results/r3-ui.json',JSON.stringify(results,null,2));await browser.close();await api.close()}
