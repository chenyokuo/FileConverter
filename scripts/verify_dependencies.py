"""Verify actual prepared runtimes, pinned Python packages and no AI dependency modules."""
from pathlib import Path
import hashlib,json,sys,os,importlib.util,importlib.metadata
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate
from dependencies import LOCK,CACHE,sha,complete
report={'runtime':{},'python':{},'aiModulesAbsent':True}
for name,spec in LOCK.items():
 archive=CACHE/spec['url'].rsplit('/',1)[1]
 if not archive.is_file() or sha(archive)!=spec['sha256']:raise RuntimeError('Missing/invalid cached archive: '+name)
 if name=='7zip-bootstrap':continue
 target=ROOT/spec['destination']
 if name.startswith('tessdata-'):file=target/(name.removeprefix('tessdata-')+'.traineddata');assert sha(file)==spec['sha256']
 elif name=='font-license':assert sha(target/'LICENSE')==spec['sha256']
 elif name=='font':assert sha(target/'NotoSansCJKtc-Regular.otf')==spec['sha256']
 elif not complete(target,spec):raise RuntimeError('Runtime extraction incomplete/corrupt: '+name)
 report['runtime'][name]={'version':spec['version'],'archiveSha256':spec['sha256'],'verified':True}
for line in (ROOT/'engine/requirements-lock.txt').read_text().splitlines():
 if not line.strip() or line.startswith('#'):continue
 name,expected=line.split('==');actual=importlib.metadata.version(name)
 if actual!=expected:raise RuntimeError('Unexpected Python version: '+name+' '+actual)
 report['python'][name]=actual
# Existing development venvs may predate this expansion; new setup never installs these.
report['aiModulesAbsent']=all(importlib.util.find_spec(name) is None for name in ['pymupdf_layout','pymupdf.layout','pymupdf4llm','onnxruntime'])
if not report['aiModulesAbsent']:raise RuntimeError('Unwanted AI modules in prepared environment; restore into a new venv with --no-deps and the approved hash lock')
engines=locate(ROOT/'vendor');assert all(engines.values()),str(engines)
from PIL import Image
import pymupdf,cv2,yt_dlp,pillow_heif
report['actualCoreImports']=True
output=ROOT/'test-results/dependencies.json';output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,indent=2),'utf-8');print('Verified pinned runtimes and',len(report['python']),'explicit Python packages; no AI modules.')
