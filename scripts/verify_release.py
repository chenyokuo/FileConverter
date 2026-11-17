"""Check actual shipping payloads, without executing or installing the installer."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
version=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version']
prefix=f'FileConverter-{version}-Portable/'
release=ROOT/'release'
archive=release/f'FileConverter-{version}-windows-x64-portable.zip'
installer=release/f'File Converter_{version}_x64-setup.exe'
exe=ROOT/'src-tauri/target/release/FileConverter.exe'
digest=lambda data:hashlib.sha256(data).hexdigest()
expected=digest(exe.read_bytes())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None, 'Corrupt Portable ZIP'
    names=z.namelist()
    for relative in ['FileConverter.exe','binaries/FileConverterEngine/FileConverterEngine.exe',
        'binaries/FileConverterEngine/_internal/python313.dll','engines/ffmpeg/ffmpeg.exe',
        'engines/ffmpeg/ffprobe.exe','LICENSE','THIRD_PARTY_NOTICES.md','README.md',
        'docs/P4.md','docs/FORMATS.md','engines/payload-manifest.json',
        'engines/libreoffice/program/soffice.com','engines/libreoffice/program/vcruntime140.dll',
        'engines/calibre/PFiles64/Calibre2/ebook-convert.exe','engines/pandoc/pandoc-3.14/pandoc.exe',
        'engines/ghostscript/bin/gswin64c.exe','engines/7zip/7z.exe','engines/deno/deno.exe',
        'engines/tessdata/eng.traineddata','engines/tessdata/chi_tra.traineddata','engines/fonts/NotoSansCJKtc-Regular.otf',
        'webview-runtime/Microsoft.WebView2.FixedVersionRuntime.157.0.4341.60.x64/msedgewebview2.exe']:
        assert prefix+relative in names, f'Missing Portable component: {relative}'
    assert any('/PIL/' in n and n.endswith('.pyd') for n in names), 'Missing native Pillow engine'
    assert any('/pymupdf/' in n and n.endswith('.pyd') for n in names), 'Missing native MuPDF engine'
    assert any('/cv2/' in n and n.endswith('.pyd') for n in names), 'Missing OpenCV'
    assert any('yt_dlp_ejs' in n and n.endswith('.js') for n in names), 'Missing packaged JavaScript solver'
    assert not any(('/onnxruntime/' in n or '/pymupdf/layout/' in n) and not n.startswith(prefix+'licenses/') for n in names), 'Unexpected AI runtime'
    assert not any(n.endswith('.msi') or '/$PLUGINSDIR/' in n or n.endswith('/.ready') for n in names), 'Extraction cache leaked'
    payload=json.loads(z.read(prefix+'engines/payload-manifest.json'))
    assert all(prefix+'engines/'+name in names for name in payload), 'Missing runtime payload entries'
    for name in payload:
        if name.endswith(('.exe','.com','.traineddata','.otf')):
            with z.open(prefix+'engines/'+name) as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            assert actual==payload[name]['sha256'], 'Changed runtime binary: '+name
    assert not any('/rai-engine/' in n or n.endswith('/RAI Converter.exe') for n in names)
    assert not any('/.tools/' in n or ('/node_modules/' in n and not n.startswith(prefix+'licenses/'))
        or n.endswith('/.env') or n.endswith('.sqlite3') for n in names)
    assert digest(z.read(prefix+'FileConverter.exe'))==expected, 'Portable EXE differs from release build'

seven=str(ROOT/'vendor/7zip/7z.exe')
assert Path(seven).is_file(), 'Run pinned dependency restore; system 7-Zip is not required'
result=subprocess.run([seven,'x',str(installer),'FileConverter.exe','-so'],capture_output=True,check=True)
installed=result.stdout
# Tauri temporarily patches its documented bundle-type marker for NSIS, then
# restores the standalone EXE. Permit exactly those three bytes, nothing else.
bundle_marker_only=False
if installed!=exe.read_bytes():
    standalone=exe.read_bytes()
    assert len(installed)==len(standalone), 'Installer EXE length differs'
    differences=[i for i,(a,b) in enumerate(zip(standalone,installed)) if a!=b]
    assert len(differences)==3 and differences==list(range(differences[0],differences[0]+3)), 'Unexpected executable changes'
    offset=differences[0];marker=b'__TAURI_BUNDLE_TYPE_VAR_'
    assert standalone[offset-len(marker):offset]==marker and installed[offset-len(marker):offset]==marker
    assert standalone[offset:offset+3]==b'UNK' and installed[offset:offset+3]==b'NSS', 'Unexpected bundle type'
    assert standalone[:offset]+standalone[offset+3:]==installed[:offset]+installed[offset+3:]
    bundle_marker_only=True
listing=subprocess.run([seven,'l',str(installer)],capture_output=True,check=True).stdout.decode('utf-8','replace')
assert 'msedgewebview2.exe' in listing and 'webview-runtime' in listing, 'Missing fixed WebView2 runtime'
assert 'binaries\\FileConverterEngine\\FileConverterEngine.exe' in listing, 'Missing frozen sidecar in installer'
assert 'engines\\ffmpeg\\ffmpeg.exe' in listing, 'Missing FFmpeg in installer'
for name in ['soffice.com','ebook-convert.exe','pandoc.exe','gswin64c.exe','7z.exe','deno.exe','chi_tra.traineddata','NotoSansCJKtc-Regular.otf']:
    assert name in listing,'Missing installer engine: '+name
script=(ROOT/'src-tauri/target/release/nsis/x64/installer.nsi').read_text(encoding='utf-8')
assert '!define PRODUCTNAME "File Converter"' in script
assert '!define MAINBINARYNAME "FileConverter"' in script
assert 'APP_ASSOCIATE' not in script and 'APP_UNASSOCIATE' not in script
hooks=(ROOT/'src-tauri/windows/hooks.nsh').read_text(encoding='utf-8')
assert 'NSIS_HOOK_PREUNINSTALL' in hooks and 'studio.rai.converter' in hooks and '$INSTDIR\\FileConverter.exe' in hooks
assert 'MUI_UNICON "${UNINSTALLERICON}"' in script
assert 'CreateShortcut "$DESKTOP\\${PRODUCTNAME}.lnk" "$INSTDIR\\${MAINBINARYNAME}.exe"' in script
assert 'CreateShortcut "$SMPROGRAMS\\$AppStartMenuFolder\\${PRODUCTNAME}.lnk" "$INSTDIR\\${MAINBINARYNAME}.exe"' in script
manifest=json.loads((release/'SHA256SUMS.json').read_text())
for artifact in (archive,installer):
    with artifact.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
    assert manifest[artifact.name]==actual, f'Incorrect checksum: {artifact.name}'
report={'version':version,'exeSha256':expected,'portableIntegrity':True,'installerPayloadMatches':True,
    'installerExeSha256':digest(installed),'installerDifference':'Tauri bundle-type marker UNK → NSS only' if bundle_marker_only else 'none',
    'fixedWebView2Included':True,'enginesIncluded':['Python','Pillow','MuPDF','FFmpeg','FFprobe','LibreOffice','Calibre','Pandoc','Ghostscript','7-Zip','Deno','OCR models','OpenCV','yt-dlp/ejs','CJK font'],
    'runtimePayloadEntries':len(payload),'externalEngineInstallationsRequired':False,'fileAssociations':False,
    'desktopAndStartMenuShortcutTarget':'FileConverter.exe','checksums':manifest}
(ROOT/'test-results').mkdir(exist_ok=True)
(ROOT/'test-results/release-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
