"""Freeze only the offline conversion API; exclude unused AI/layout modules."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','rai-engine',
    '--distpath',str(ROOT/'src-tauri/binaries'),'--workpath',str(ROOT/'.tools/pyinstaller'),'--specpath',str(ROOT/'.tools'),
    '--additional-hooks-dir',str(ROOT/'scripts/hooks'),'--exclude-module','pymupdf.layout','--exclude-module','pymupdf4llm',
    '--exclude-module','onnxruntime','--exclude-module','numpy','--exclude-module','tkinter',str(ROOT/'engine/service.py')],check=True,cwd=ROOT)
