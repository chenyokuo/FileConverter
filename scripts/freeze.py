"""Freeze local engines and explicit downloader; no end-user Python installation."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
DIST=Path(sys.argv[sys.argv.index('--dist')+1]).resolve() if '--dist' in sys.argv else ROOT/'src-tauri/binaries'
if not DIST.is_relative_to(ROOT):raise ValueError('Frozen staging must stay inside the project')
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--onedir','--name','FileConverterEngine','--icon',str(ROOT/'src-tauri/icons/icon.ico'),
    '--distpath',str(DIST),'--workpath',str(ROOT/'.tools/pyinstaller'),'--specpath',str(ROOT/'.tools'),
    '--additional-hooks-dir',str(ROOT/'scripts/hooks'),'--exclude-module','pymupdf.layout','--exclude-module','pymupdf4llm',
    '--exclude-module','onnxruntime','--exclude-module','tkinter','--exclude-module','IPython','--exclude-module','matplotlib',
    '--collect-all','pillow_heif','--collect-data','yt_dlp_ejs','--copy-metadata','yt-dlp','--copy-metadata','yt-dlp-ejs',
    '--add-data',str(ROOT/'engine/verified-capabilities.json')+';.',str(ROOT/'engine/service.py')],check=True,cwd=ROOT)
