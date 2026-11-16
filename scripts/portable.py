from pathlib import Path
import hashlib
import json
import shutil
import zipfile
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'release'/'RAI-Converter-Portable'
DEST.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'src-tauri/target/release/rai-converter.exe',DEST/'RAI Converter.exe')
shutil.copytree(ROOT/'src-tauri/binaries',DEST/'binaries',dirs_exist_ok=True)
shutil.copytree(ROOT/'vendor/ffmpeg',DEST/'engines/ffmpeg',dirs_exist_ok=True)
shutil.copytree(ROOT/'src-tauri/notices',DEST/'licenses',dirs_exist_ok=True)
shutil.copytree(ROOT/'docs',DEST/'docs',dirs_exist_ok=True)
for name in ['LICENSE','README.md','THIRD_PARTY_NOTICES.md']:
    shutil.copy2(ROOT/name,DEST/name)
(DEST/'PORTABLE-NOTES.txt').write_text('RAI Converter 0.1.0\nExtract the entire folder, then run RAI Converter.exe.\nRequires Windows 10/11 x64 and installed WebView2.\nPython / Node / Rust are not required.\nSettings and history are saved in %APPDATA%/studio.rai.converter.\nLibreOffice is an optional separate installation for Office conversions.\nThis evaluation build is unsigned. See THIRD_PARTY_NOTICES.md before redistribution.\n',encoding='utf-8')
archive=ROOT/'release/RAI-Converter-0.1.0-windows-x64-portable.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as z:
    for p in DEST.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(DEST.parent))
manifest={p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in (ROOT/'release').glob('*.zip')}
for p in (ROOT/'src-tauri/target/release/bundle/nsis').glob('*.exe'):
    target=ROOT/'release'/p.name;shutil.copy2(p,target);manifest[p.name]=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
(ROOT/'release/SHA256SUMS.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(archive)
