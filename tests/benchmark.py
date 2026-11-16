"""One measured CPU/GPU comparison plus streaming a real 1 GiB sparse WAV."""
from pathlib import Path
import contextlib
import io
import json
import struct
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate,hardware,command
from worker import convert,probe
from test_engine import Client
root=ROOT/'.tools/p5-performance';root.mkdir(exist_ok=True);engines=locate(ROOT/'src-tauri/bundled-engines')
source=root/'reference.mp4'
if not source.exists():command([engines['ffmpeg'],'-v','error','-f','lavfi','-i','testsrc2=s=1920x1080:r=30:d=3','-c:v','libx264','-preset','ultrafast',source])
devices=hardware(engines['ffmpeg']);engines['hardwareCapabilities']=devices;results=[]
for device in [d for d in devices if d['available']]:
 stage=root/device['id'];stage.mkdir(exist_ok=True)
 for file in stage.glob('*.mp4'):file.unlink()
 log=io.StringIO();start=time.monotonic()
 try:
  with contextlib.redirect_stdout(log):files=convert({'sources':[str(source)],'format':'mp4','options':{'hardware':device['id'],'qualityPreset':'fast','crf':23}},stage,engines)
  elapsed=time.monotonic()-start;stats={}
  for line in log.getvalue().splitlines():stats.update(json.loads(line).get('stats',{}))
  comparison=command([engines['ffmpeg'],'-v','info','-i',source,'-i',files[0],'-lavfi','ssim','-f','null','-'],return_stderr=True).decode('utf-8','replace')
  import re
  score=re.search(r'All:([\d.]+)',comparison)
  results.append({'requested':device['id'],'actual':stats.get('hardware'),'encoder':stats.get('encoder'),'fallback':stats.get('hardwareFallback'),'wallSeconds':round(elapsed,3),'wallFps':round(90/elapsed,2),'bytes':files[0].stat().st_size,'ssim':float(score[1]) if score else None})
 except Exception as error:results.append({'requested':device['id'],'error':str(error)})
wav=root/'1GiB 中文 & streaming.wav';length=1024**3
if not wav.exists():
 with wav.open('wb') as f:
  f.write(b'RIFF'+struct.pack('<I',length+36)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,48000,192000,4,16)+b'data'+struct.pack('<I',length));f.seek(44+length-1);f.write(b'\0')
client=Client(root/'data')
try:
 inspected=client.call('inspect',{'paths':[str(wav)]})[0];assert inspected['size']==length+44 and inspected['extension']=='wav'
 job=client.call('enqueue_tool',{'sources':[str(wav)],'operation':'audio.trim','params':{'start':0,'end':2,'format':'flac'},'outputDir':str(root/'large-output')})[0]
 done=client.wait([job['id']],timeout=60)[0];assert done['status']=='completed',done.get('error');info=probe(done['outputs'][0],engines['ffprobe']);assert 1.9<float(info['format']['duration'])<2.1
 large={'inputBytes':wav.stat().st_size,'operation':'Read 1 GiB WAV, stream first 2 seconds to FLAC','duration':float(info['format']['duration']),'status':'passed'}
finally:client.close()
report={'devices':devices,'comparison':results,'largeInput':large,'note':'Single run, synthetic 1080p30 3-second source. Wall time includes initialization; SSIM is against the encoded reference. No promise that GPU improves quality.'}
(ROOT/'test-results/performance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
