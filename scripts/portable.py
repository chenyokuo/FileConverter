from pathlib import Path
import hashlib
import json
import shutil
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
VERSION=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version']
DEST=ROOT/'release'/f'FileConverter-{VERSION}-Portable'
DEST.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'src-tauri/target/release/FileConverter.exe',DEST/'FileConverter.exe')
shutil.copytree(ROOT/'src-tauri/binaries/FileConverterEngine',DEST/'binaries/FileConverterEngine',dirs_exist_ok=True)
shutil.copytree(ROOT/'vendor/ffmpeg',DEST/'engines/ffmpeg',dirs_exist_ok=True)
shutil.copytree(ROOT/'src-tauri/notices',DEST/'licenses',dirs_exist_ok=True)
shutil.copytree(ROOT/'docs',DEST/'docs',dirs_exist_ok=True)
for name in ['LICENSE','README.md','THIRD_PARTY_NOTICES.md']:
    shutil.copy2(ROOT/name,DEST/name)
(DEST/'PORTABLE-NOTES.txt').write_text(f'File Converter {VERSION}\nExtract the entire folder, then run FileConverter.exe.\nRequires Windows 10/11 x64 and installed WebView2.\nPython / Node / Rust are not required.\nSettings and history are saved in %APPDATA%/studio.rai.converter.\nLibreOffice is an optional separate installation for Office conversions.\nThis evaluation build is unsigned. See THIRD_PARTY_NOTICES.md before redistribution.\n',encoding='utf-8')
if '--stage-only' in sys.argv:
    print(DEST)
    sys.exit(0)
archive=ROOT/'release'/f'FileConverter-{VERSION}-windows-x64-portable.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as z:
    for p in DEST.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(DEST.parent))
manifest={archive.name:hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()}
for p in ([] if '--no-installer' in sys.argv else (ROOT/'src-tauri/target/release/bundle/nsis').glob(f'*_{VERSION}_x64-setup.exe')):
    target=ROOT/'release'/p.name;shutil.copy2(p,target);manifest[p.name]=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
(ROOT/'release/SHA256SUMS.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(archive)
