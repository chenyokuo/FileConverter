"""Copy only pinned app-local runtime payloads; never package MSI extraction caches."""
from pathlib import Path
import hashlib
import json
import shutil
import stat
import os
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'src-tauri/bundled-engines'
ENGINES=['ffmpeg','libreoffice','calibre','pandoc','ghostscript','7zip','deno','tessdata','fonts']
EXCLUDED={'$PLUGINSDIR','.ready','.fc-runtime-integrity.json','uninstgs.exe.nsis'}
def ignore(directory,names):
    if Path(directory).resolve()==(ROOT/'vendor/7zip').resolve():return [n for n in names if n not in {'7z.exe','7z.dll','License.txt','readme.txt','History.txt'}]
    return [name for name in names if name in EXCLUDED or name.lower().endswith(('.msi','.log','.partial','.tmp')) or name.startswith(('__pycache__','.~lock.'))]
def main():
    import sys
    sys.path.insert(0,str(ROOT/'engine'))
    from runtime import locate
    from fsutils import remove_tree
    if DEST.exists():remove_tree(DEST,ROOT/'src-tauri')
    DEST.mkdir()
    for engine in ENGINES:
        source=ROOT/'vendor'/engine
        if not source.is_dir():raise RuntimeError('Missing bundled engine: '+engine)
        shutil.copytree(source,DEST/engine,ignore=ignore)
    # MSI administrative images keep VC runtimes in System64; they would normally
    # be installed globally. Keep them beside soffice instead of relying on the host.
    for dll in (DEST/'libreoffice/System64').glob('*.dll'):
        target=DEST/'libreoffice/program'/dll.name
        if not target.exists():shutil.copy2(dll,target)
    (DEST/'engine-lock.json').write_bytes((ROOT/'engine-lock.json').read_bytes())
    engines=locate(DEST)
    if any(not value for value in engines.values()):raise RuntimeError('Incomplete staged runtime: '+str(engines))
    for file in DEST.rglob('*'):
        if file.is_file() and not file.stat().st_mode&stat.S_IWRITE:os.chmod(file,stat.S_IREAD|stat.S_IWRITE)
    manifest={str(p.relative_to(DEST)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in DEST.rglob('*') if p.is_file()}
    (DEST/'payload-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Staged',len(manifest),'files,',round(sum(p['bytes'] for p in manifest.values())/1024**2),'MiB')
if __name__=='__main__':main()
