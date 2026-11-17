"""Remove unused optional AI directories only from an explicitly setup-owned new venv.
Official cached wheels/hash locks are preserved. Never edits existing user runtimes.
"""
from pathlib import Path
import shutil,sys,json
ROOT=Path(__file__).resolve().parents[1];venv=(ROOT/'.venv').resolve();site=venv/'Lib/site-packages'
targets=[site/'pymupdf/layout',site/'pymupdf4llm',site/'pymupdf_layout']
present=[path for path in targets if path.exists()]
if present and not (venv/'.fileconverter-created').is_file():raise RuntimeError('Preserving existing venv: create a new setup-owned environment before pruning optional AI modules')
removed=[]
for path in present:
 resolved=path.resolve()
 if not resolved.is_relative_to(site.resolve()) or path.is_symlink():raise ValueError('Invalid optional module directory')
 removed.append(path.relative_to(venv).as_posix());shutil.rmtree(path)
if any(site.rglob('*.onnx')):raise RuntimeError('Unexpected model outside optional AI directories')
print('Classic API environment prepared; unused optional directories removed:',len(removed))
