from pathlib import Path
import hashlib
import json
import shutil
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
from normalize_bundle_marker import normalize
if '--stage-only' not in sys.argv:normalize()
def copy_changed(source,target):
    source,target=Path(source),Path(target)
    if target.exists() and source.stat().st_size==target.stat().st_size and source.stat().st_mtime_ns==target.stat().st_mtime_ns:return str(target)
    return shutil.copy2(source,target)
VERSION=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version']
DEST=ROOT/'release'/f'FileConverter-{VERSION}-Portable'
DEST.mkdir(parents=True,exist_ok=True)
copy_changed(ROOT/'src-tauri/target/release/FileConverter.exe',DEST/'FileConverter.exe')
shutil.copytree(ROOT/'src-tauri/binaries/FileConverterEngine',DEST/'binaries/FileConverterEngine',dirs_exist_ok=True,copy_function=copy_changed)
shutil.copytree(ROOT/'src-tauri/bundled-engines',DEST/'engines',dirs_exist_ok=True,copy_function=copy_changed)
shutil.copytree(ROOT/'src-tauri/webview-runtime',DEST/'webview-runtime',dirs_exist_ok=True,copy_function=copy_changed)
shutil.copytree(ROOT/'src-tauri/notices',DEST/'licenses',dirs_exist_ok=True,copy_function=copy_changed)
shutil.copytree(ROOT/'docs',DEST/'docs',dirs_exist_ok=True,copy_function=copy_changed)
for name in ['LICENSE','README.md','THIRD_PARTY_NOTICES.md']:
    shutil.copy2(ROOT/name,DEST/name)
(DEST/'PORTABLE-NOTES.txt').write_text(f'File Converter {VERSION}\nExtract the entire folder, then run FileConverter.exe.\nWindows 10/11 x64. Fixed WebView2, Python, FFmpeg, LibreOffice, Pandoc, Calibre, Ghostscript, 7-Zip, OCR models and downloader runtimes are app-local. No separate engine installation.\nSettings and history: %APPDATA%/studio.rai.converter.\nRight-click integration is optional in Settings / Advanced. Disable it before moving/deleting a Portable folder.\nThis release candidate is unsigned. See docs/VALIDATION.md and THIRD_PARTY_NOTICES.md for acceptance status and distribution obligations.\n',encoding='utf-8')
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
