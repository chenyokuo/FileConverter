"""Prepare development runtimes once; this never builds an app or installs MSIs."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.tools/engine-downloads';CACHE.mkdir(exist_ok=True)
LOCK=ROOT/'engine-lock.json'
SPECS={
 'libreoffice':{'version':'26.8.3','url':'https://download.documentfoundation.org/libreoffice/stable/26.8.3/win/x86_64/LibreOffice_26.8.3_Win_x86-64.msi','sha256':'0e6918c273eabbdbbd800ee0dacbbf130a14c13c2e4cec861b06dd59e015bf94','license':'MPL-2.0 / LGPL and component licenses'},
 'calibre':{'version':'9.18.0','url':'https://github.com/kovidgoyal/calibre/releases/download/v9.18.0/calibre-64bit-9.18.0.msi','sha256':'05c0f2223866f8082e05b2d4bc9c57b31a833de8355a1191fd79c260c2636d38','license':'GPL-3.0-or-later'},
 'pandoc':{'version':'3.14','url':'https://github.com/jgm/pandoc/releases/download/3.14/pandoc-3.14-windows-x86_64.zip','sha256':'0144b96e8c7b023fd382ec5ef5bdc475e873f1019d6fa72502492df2c9a94a3b','license':'GPL-2.0-or-later'},
 'ghostscript':{'version':'10.08.0','url':'https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10080/gs10080w64.exe','sha256':'52a91b8bf09298788d7a57b9206127026c23eacd75405f0a131e26dc381dce50','license':'AGPL-3.0-or-later'},
 'deno':{'version':'2.9.8','url':'https://github.com/denoland/deno/releases/download/v2.9.8/deno-x86_64-pc-windows-msvc.zip','sha256':'cba84b26e0df5ae7f74fc66b86a95b866872a86292ebd84fa1e959927edd93bf','license':'MIT'},
}
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def fetch(name,spec):
    archive=CACHE/spec['url'].rsplit('/',1)[1]
    if not archive.exists():
        print('Downloading runtime:',name,flush=True)
        request=urllib.request.Request(spec['url'],headers={'User-Agent':'FileConverter-build'})
        part=archive.with_suffix('.partial')
        try:
            with urllib.request.urlopen(request,timeout=120) as source,part.open('wb') as out:shutil.copyfileobj(source,out)
        except urllib.error.URLError:
            # Windows curl uses the native certificate store; keep TLS checks on.
            subprocess.run(['curl.exe','--fail','--location','--retry','2','--output',str(part),spec['url']],check=True,stdout=subprocess.DEVNULL)
        part.replace(archive)
    if sha(archive)!=spec['sha256']:raise RuntimeError('Runtime checksum mismatch: '+name)
    print('Verified runtime:',name,flush=True)
    return name,archive

def prepare():
    downloads=dict(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(lambda item:fetch(*item),SPECS.items()))
    seven=Path('C:/Program Files/7-Zip/7z.exe')
    for name,archive in downloads.items():
        target=(ROOT/'vendor'/name).resolve()
        if not target.is_relative_to((ROOT/'vendor').resolve()):raise ValueError('Invalid runtime path')
        marker=target/'.ready'
        if marker.exists() and marker.read_text()==SPECS[name]['sha256']:continue
        target.mkdir(exist_ok=True)
        if archive.suffix=='.zip':
            with zipfile.ZipFile(archive) as z:
                for item in z.infolist():
                    destination=(target/item.filename).resolve()
                    if not destination.is_relative_to(target):raise ValueError('Unsafe runtime archive path')
                z.extractall(target)
        elif archive.suffix=='.msi':
            # Administrative extraction only. No product installation, shortcuts or associations.
            log=CACHE/(name+'-extract.log')
            result=subprocess.run(['msiexec.exe','/a',str(archive),'/qn','TARGETDIR='+str(target),'/L*v',str(log)],creationflags=0x08000000)
            if result.returncode not in (0,3010):raise RuntimeError(f'{name}: MSI extraction failed {result.returncode}; see {log}')
        else:
            subprocess.run([str(seven),'x',str(archive),'-o'+str(target),'-y'],stdout=subprocess.DEVNULL,check=True,creationflags=0x08000000)
        marker.write_text(SPECS[name]['sha256'])
    target=ROOT/'vendor/7zip';target.mkdir(exist_ok=True)
    for name in ['7z.exe','7z.dll','License.txt','readme.txt']:
        shutil.copy2(seven.parent/name,target/name)
    lock=dict(SPECS)
    import re
    seven_info=subprocess.check_output([str(target/'7z.exe'),'i']).decode('utf-8','replace')
    lock['7zip']={'version':re.search(r'7-Zip (\d+\.\d+)',seven_info)[1],'source':'https://www.7-zip.org/','license':'LGPL-2.1-or-later with unRAR restriction','files':{n:sha(target/n) for n in ['7z.exe','7z.dll']}}
    tess=ROOT/'vendor/tessdata';tess.mkdir(exist_ok=True)
    previous=json.loads(LOCK.read_text()) if LOCK.exists() else {}
    for lang in ['eng','chi_tra']:
        key='tessdata-'+lang
        spec=previous.get(key) or {'url':f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/{lang}.traineddata','license':'Apache-2.0','version':'fast model, SHA-256 pinned'}
        file=tess/(lang+'.traineddata')
        if not file.exists():urllib.request.urlretrieve(spec['url'],file)
        digest=sha(file)
        if spec.get('sha256') and spec['sha256']!=digest:raise RuntimeError('OCR model checksum mismatch')
        lock[key]={**spec,'sha256':digest}
    LOCK.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    print('Runtimes prepared in vendor; no application packaging performed.',flush=True)

if __name__=='__main__':prepare()
