import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';import {execFileSync} from 'node:child_process';import path from 'node:path';
import {bridge,installBridge} from './editor-bridge.mjs';
const bridgeApi=await bridge();const browser=await chromium.launch({channel:'msedge',headless:true});
try {
 const page=await browser.newPage({viewport:{width:1500,height:960}});await installBridge(page,bridgeApi.port);
 await page.goto('http://127.0.0.1:1420/tests/editor-harness.html');
 await page.evaluate(paths=>window.__picks.push(paths),['red','blue'].map(n=>path.join(bridgeApi.data,n+'.mp4')));
 await page.getByRole('button',{name:'匯入素材',exact:true}).click();
 const track=t=>page.locator(`.editor-track[data-track="${t}"] .editor-clip`);
 await expect(track('V1')).toHaveCount(2);await expect(track('A1')).toHaveCount(2);await expect(track('A2')).toHaveCount(0);
 await expect(page.locator('.track-A .clip-waveform')).toHaveCount(2);
 await track('V1').first().click();await page.getByLabel('專案位置 秒',{exact:true}).fill('.25');
 await track('A1').first().click();await expect(page.getByLabel('專案位置 秒',{exact:true})).toHaveJSProperty('valueAsNumber',0.25);
 await page.getByLabel('專案位置 秒',{exact:true}).fill('0');await track('V1').first().click();
 await expect(page.locator('video')).toBeVisible({timeout:30000});
 await page.locator('video').evaluate(v=>{v.currentTime=1;v.dispatchEvent(new Event('timeupdate'))});
 await page.getByRole('button',{name:'分割',exact:true}).click();
 await expect(track('V1')).toHaveCount(3);await expect(track('A1')).toHaveCount(3);
 await page.getByRole('button',{name:'解除連動',exact:true}).click();
 await track('A1').nth(1).click();await page.getByLabel('專案位置 秒',{exact:true}).fill('1.1');
 await track('V1').nth(1).click();await expect(page.getByLabel('專案位置 秒',{exact:true})).toHaveValue('1');
 await page.getByRole('button',{name:'重新連動',exact:true}).click();
 const project=path.join(bridgeApi.data,'r1.fcvideo.json');await page.evaluate(p=>window.__picks.push(p),project);
 await page.getByRole('button',{name:'儲存',exact:true}).click();
 await expect.poll(async()=>JSON.parse(await fs.readFile(project,'utf8').catch(()=>'{"clips":[]}')).clips.length).toBe(6);
 const saved=JSON.parse(await fs.readFile(project,'utf8'));expect(saved.clips.filter(c=>c.videoOnly)).toHaveLength(3);
 await page.getByRole('button',{name:'輸出所選片段',exact:true}).click();let selectedOutput;await expect.poll(async()=>{const state=await bridgeApi.rpc('snapshot');const job=state.jobs.find(j=>j.kind==='fcvideo');if(job?.status==='failed')throw Error(job.error);selectedOutput=job?.outputs?.[0];return job?.status},{timeout:30000}).toBe('completed');
 execFileSync('.venv/Scripts/python.exe',['-X','utf8','-c',`import sys,json,subprocess,array,math
+from pathlib import Path
+sys.path.insert(0,'engine')
+from runtime import locate
+e=locate(Path('vendor'));info=json.loads(subprocess.check_output([e['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',sys.argv[1]]));assert abs(float(info['format']['duration'])-1)<.1;assert any(s['codec_type']=='audio' for s in info['streams']);a=array.array('f');a.frombytes(subprocess.check_output([e['ffmpeg'],'-v','error','-i',sys.argv[1],'-f','f32le','-ac','1','-']));assert math.sqrt(sum(x*x for x in a)/len(a))>.02`.replaceAll('\n+','\n'),selectedOutput]);
 for(const [width,height] of [[1920,1080],[1366,768],[1280,720],[960,640]]){
  await page.setViewportSize({width,height});await page.waitForTimeout(150);
  expect(await page.locator('.video-editor').evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBe(true);
  expect((await page.locator('.editor-preview').boundingBox()).width).toBeLessThanOrEqual(640);
 }
 await page.setViewportSize({width:1500,height:960});await page.screenshot({path:'test-results/r1-editor.png'});
 console.log('PASS actual import V1/A1/waves, linked move, split, unlink/relink, saved metadata and compact responsive layout');
}finally{await browser.close();await bridgeApi.close()}
