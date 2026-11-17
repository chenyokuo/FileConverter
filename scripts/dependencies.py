"""Pinned, cache-aware Windows runtime restoration; no host 7-Zip/Office dependency."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,urllib.request,zipfile,concurrent.futures
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path(os.environ.get('FILE_CONVERTER_DOWNLOAD_CACHE',ROOT/'.tools/engine-downloads')).resolve()
LOCK=json.loads((ROOT/'engine-lock.json').read_text('utf-8'))
def sha(path):
 with Path(path).open('rb') as file:return hashlib.file_digest(file,'sha256').hexdigest()
def destination(relative):
 target=(ROOT/relative).resolve()
 if not target.is_relative_to(ROOT):raise ValueError('Runtime destination escapes workspace')
 target.mkdir(parents=True,exist_ok=True);return target
def fetch(name,spec):
 CACHE.mkdir(parents=True,exist_ok=True);target=CACHE/spec['url'].rsplit('/',1)[1]
 alternatives=[ROOT/'.tools/ffmpeg-complete.zip',ROOT/'.tools/ffmpeg-8.1.2.zip'] if name=='ffmpeg' else []
 if name.startswith('tessdata-'):alternatives.append(ROOT/'vendor/tessdata'/(name.removeprefix('tessdata-')+'.traineddata'))
 if name=='font-license':alternatives.append(ROOT/'vendor/fonts/LICENSE')
 if name=='font':alternatives.append(ROOT/'vendor/fonts/NotoSansCJKtc-Regular.otf')
 if not target.exists():
  for old in alternatives:
   if old.is_file() and sha(old)==spec['sha256']:shutil.copy2(old,target);break
 if not target.exists():
  if os.environ.get('FILE_CONVERTER_OFFLINE')=='1':raise RuntimeError('Offline cache missing: '+name)
  partial=target.with_suffix(target.suffix+'.partial')
  try:
   request=urllib.request.Request(spec['url'],headers={'User-Agent':'FileConverter-dependency-restore'})
   with urllib.request.urlopen(request,timeout=120) as source,partial.open('wb') as out:shutil.copyfileobj(source,out)
   if sha(partial)!=spec['sha256']:raise RuntimeError('Download checksum mismatch: '+name)
   partial.replace(target)
  finally:partial.unlink(missing_ok=True)
 if sha(target)!=spec['sha256']:raise RuntimeError('Cached archive checksum mismatch: '+name+'; preserve for inspection, do not execute')
 print('Verified cached/downloaded runtime: '+name,flush=True);return target
def unzip(archive,target):
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   resolved=(target/item.filename).resolve()
   if not resolved.is_relative_to(target) or (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe archive member')
  z.extractall(target)
def complete(target,spec):
 marker=target/'.fc-runtime-integrity.json'
 if not marker.is_file():return False
 try:
  record=json.loads(marker.read_text('utf-8'))
  return record['archive']==spec['sha256'] and all((target/p).is_file() and sha(target/p)==digest for p,digest in record['critical'].items())
 except (KeyError,ValueError,OSError):return False
def mark(target,spec,critical):
 files=[p for pattern in critical for p in target.glob(pattern) if p.is_file()]
 if not files:raise RuntimeError('Runtime extraction incomplete: '+str(target))
 (target/'.fc-runtime-integrity.json').write_text(json.dumps({'archive':spec['sha256'],'critical':{p.relative_to(target).as_posix():sha(p) for p in files}},indent=2),'utf-8')
def prepare(only=None):
 selected={k:v for k,v in LOCK.items() if not only or k in only}
 if any(k in selected for k in ['7zip','ghostscript']):selected['7zip-bootstrap']=LOCK['7zip-bootstrap'];selected['7zip']=LOCK['7zip']
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:downloads=dict(zip(selected,pool.map(lambda k:fetch(k,selected[k]),selected)))
 seven_target=destination('vendor/7zip');seven=seven_target/'7z.exe'
 if '7zip' in downloads:
  spec=LOCK['7zip']
  if not complete(seven_target,spec):
   subprocess.run([str(downloads['7zip-bootstrap']),'x',str(downloads['7zip']),'-o'+str(seven_target),'-y'],check=True,stdout=subprocess.DEVNULL,creationflags=0x08000000)
   for name,digest in spec['files'].items():
    if sha(seven_target/name)!=digest:raise RuntimeError('7-Zip extracted binary mismatch')
   mark(seven_target,spec,['7z.exe','7z.dll'])
 for name,spec in selected.items():
  if name in {'7zip','7zip-bootstrap'}:continue
  archive=downloads[name];target=destination(spec['destination'])
  if name.startswith('tessdata-'):
   file=target/(name.removeprefix('tessdata-')+'.traineddata')
   if not file.exists() or sha(file)!=spec['sha256']:shutil.copy2(archive,file)
   continue
  if name=='font-license':
   file=target/'LICENSE'
   if not file.exists() or sha(file)!=spec['sha256']:shutil.copy2(archive,file)
   continue
  if name=='font':
   file=target/'NotoSansCJKtc-Regular.otf'
   if not file.exists() or sha(file)!=spec['sha256']:shutil.copy2(archive,file)
   continue
  if name=='webview2':
   runtime=target/('Microsoft.WebView2.FixedVersionRuntime.'+spec['version']+'.x64')
   if not complete(target,spec):
    subprocess.run(['expand.exe',str(archive),'-F:*',str(target)],check=True,stdout=subprocess.DEVNULL,creationflags=0x08000000);mark(target,spec,[runtime.name+'/msedgewebview2.exe',runtime.name+'/msedge.dll'])
   continue
  if complete(target,spec):continue
  if name=='ffmpeg':
   with zipfile.ZipFile(archive) as z:
    for member in z.namelist():
     if member.endswith(('/ffmpeg.exe','/ffprobe.exe','/LICENSE','/LICENSE.txt')):
      with z.open(member) as source,(target/Path(member).name).open('wb') as out:shutil.copyfileobj(source,out)
   for file,digest in spec['files'].items():
    if sha(target/file)!=digest:raise RuntimeError('FFmpeg binary mismatch')
   (target/'manifest.json').write_text(json.dumps({'url':spec['url'],'archive_sha256':spec['sha256'],'license':spec['license']}),'utf-8')
   critical=['ffmpeg.exe','ffprobe.exe']
  elif archive.suffix=='.zip':unzip(archive,target);critical=['**/*.exe']
  elif archive.suffix=='.msi':
   result=subprocess.run(['msiexec.exe','/a',str(archive),'/qn','TARGETDIR='+str(target),'/L*v',str(CACHE/(name+'-extract.log'))],creationflags=0x08000000)
   if result.returncode not in (0,3010):raise RuntimeError(name+' administrative extraction failed: '+str(result.returncode))
   critical=['**/soffice.com'] if name=='libreoffice' else ['**/ebook-convert.exe']
  else:
   subprocess.run([str(seven),'x',str(archive),'-o'+str(target),'-y'],check=True,stdout=subprocess.DEVNULL,creationflags=0x08000000);critical=['**/gswin64c.exe']
  mark(target,spec,critical)
 print('Runtime restore complete; no application build or system application installation.',flush=True)
if __name__=='__main__':prepare()
