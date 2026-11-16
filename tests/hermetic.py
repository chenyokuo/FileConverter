"""Run the frozen engine with only Windows directories on PATH. Not a clean VM."""
from pathlib import Path
import os
import sys
import json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from test_engine import Client
from PIL import Image
from worker import probe
from runtime import locate
root=ROOT/'.tools/p5-hermetic';root.mkdir(exist_ok=True);fixtures=ROOT/'.tools/p5-matrix'
os.environ['PATH']=str(Path(os.environ['SystemRoot'])/'System32')+';'+os.environ['SystemRoot']
for key in ['PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','CALIBRE_CONFIG_DIRECTORY','CALIBRE_CACHE_DIRECTORY']:os.environ.pop(key,None)
os.environ['FILE_CONVERTER_TEST_FROZEN']=str(ROOT/'src-tauri/binaries/FileConverterEngine/FileConverterEngine.exe');os.environ['FILE_CONVERTER_TEST_ENGINES']=str(ROOT/'src-tauri/bundled-engines')
client=Client(root/'data');checks=[]
try:
 for source,target in [('png','heic'),('pdf','docx'),('docx','pdf'),('md','html'),('epub','mobi'),('eps','png'),('mp4','mp3'),('zip','7z')]:
  file=fixtures/('來源 中文 & '+source+'.'+source);assert file.exists()
  job=client.call('enqueue',{'jobs':[{'sources':[str(file)],'format':target,'outputDir':str(root/'out'),'options':{'hardware':'cpu'}}]})[0]
  result=client.wait([job['id']],timeout=120)[0];assert result['status']=='completed',result.get('error')
  files=[Path(p) for p in result['outputs']];assert all(p.stat().st_size>0 for p in files)
  if target in {'png','heic'}:
   from runtime import image_plugins
   image_plugins()
   with Image.open(files[0]) as image:image.load();assert image.width>0
  if target=='mp3':assert probe(files[0],locate(ROOT/'src-tauri/bundled-engines')['ffprobe'])['streams'][0]['codec_name']=='mp3'
  if target=='pdf':
   import pymupdf
   with pymupdf.open(files[0]) as d:assert 'Matrix' in ''.join(p.get_text() for p in d)
  checks.append({'direction':source+':'+target,'status':'passed'})
 job=client.call('enqueue_tool',{'operation':'image.repair','sources':[str(fixtures/'來源 中文 & png.png')],'params':{'region':[.1,.1,.3,.3]},'outputDir':str(root/'out')})[0];result=client.wait([job['id']])[0];assert result['status']=='completed',result.get('error');checks.append({'operation':'OpenCV repair','status':'passed'})
finally:client.close()
report={'PATH':os.environ['PATH'],'checks':checks,'cleanWindowsVM':False,'note':'Host PATH excludes developer tools. Uses only bundled executables. Installed system DLLs are still present; this cannot certify a clean Windows machine.'};(ROOT/'test-results/hermetic.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
