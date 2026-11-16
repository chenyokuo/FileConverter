"""Collect the actual installed package notices for local binary artifacts."""
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import os
import stat
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'src-tauri'/'notices'
DEST.mkdir(exist_ok=True)
for file in DEST.rglob('*'):
    if file.is_file():os.chmod(file,stat.S_IREAD|stat.S_IWRITE)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.is_file():shutil.copy2(python_license,DEST/'PYTHON-LICENSE.txt')
for name in ['LICENSE','THIRD_PARTY_NOTICES.md']:
    shutil.copy2(ROOT/name,DEST/name)
inventory=[]
for meta in importlib.metadata.distributions():
    name=meta.metadata['Name'];version=meta.version
    inventory.append({'name':name,'version':version,'license':meta.metadata.get('License-Expression') or meta.metadata.get('License','')})
    for file in meta.files or []:
        if any(token in str(file).lower() for token in ['license','copying','notice']) and not str(file).endswith('.py'):
            src=Path(meta.locate_file(file))
            if src.is_file():
                dest=DEST/'python'/name/str(file);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
(DEST/'python-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
for package in (ROOT/'node_modules').glob('**/package.json'):
    # Walk licenses from installed packages; do not copy source, cache or binaries.
    for file in package.parent.iterdir():
        if file.is_file() and any(file.name.upper().startswith(x) for x in ['LICENSE','COPYING','NOTICE','OFL']):
            target=DEST/'npm'/package.parent.relative_to(ROOT/'node_modules')/file.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
cargo=ROOT/'.tools/cargo/registry/src'
if not cargo.exists():cargo=Path.home()/'.cargo/registry/src'
for package in cargo.glob('*/*'):
    if not package.is_dir():continue
    for file in package.iterdir():
        if file.is_file() and any(file.name.upper().startswith(x) for x in ['LICENSE','COPYING','NOTICE','UNLICENSE']):
            target=DEST/'rust'/package.name/file.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
ffmpeg=ROOT/'vendor/ffmpeg'
for name in ['LICENSE','manifest.json']:
    if (ffmpeg/name).is_file():
        target=DEST/'ffmpeg'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ffmpeg/name,target)
import subprocess
with (DEST/'ffmpeg/buildconf.txt').open('w',encoding='utf-8') as f:
    subprocess.run([str(ffmpeg/'ffmpeg.exe'),'-buildconf'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Collected third-party notices:',sum(1 for p in DEST.rglob('*') if p.is_file()))

# Runtime executables carry their own component notices. Preserve the actual
# payload inventory separately from development-only Python/npm tools.
runtime=ROOT/'src-tauri/bundled-engines'
for file in runtime.rglob('*'):
    if file.is_file() and (any(token in file.name.lower() for token in ['license','copying','copyright','notice']) or file.name in {'engine-lock.json','manifest.json','payload-manifest.json'}):
        target=DEST/'engines'/file.relative_to(runtime);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
shutil.copy2(ROOT/'engine-lock.json',DEST/'engine-lock.json')
for file in (ROOT/'src-tauri/webview-runtime').rglob('*'):
    if file.is_file() and any(token in file.name.lower() for token in ['license','credits','terms']):
        target=DEST/'webview2'/file.relative_to(ROOT/'src-tauri/webview-runtime');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
for file in DEST.rglob('*'):
    if file.is_file() and not file.stat().st_mode&stat.S_IWRITE:os.chmod(file,stat.S_IREAD|stat.S_IWRITE)
