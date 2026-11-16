"""Cleanup confined to an explicitly owned staging root, including read-only files."""
from pathlib import Path
import os
import shutil
import stat
import time

def ordinary_path(value):
    """Remove Rust's verbatim prefix for runtimes (not all C libraries accept it)."""
    value=os.fspath(value)
    if os.name=='nt':
        if value.startswith('\\\\?\\UNC\\'):return '\\\\'+value[8:]
        if value.startswith('\\\\?\\'):return value[4:]
    return value

def remove_tree(path,allowed_parent):
    path=Path(path).resolve();parent=Path(allowed_parent).resolve()
    if path==parent or not path.is_relative_to(parent):raise ValueError('Cleanup path escaped its staging root')
    # LibreOffice profiles contain deeply nested language/extension caches. Use the
    # Windows extended path form after checking the ordinary resolved boundary.
    if os.name=='nt' and not str(path).startswith('\\\\?\\'):
        value=str(path);path=Path('\\\\?\\UNC\\'+value[2:] if value.startswith('\\\\') else '\\\\?\\'+value)
    def writable(function,name,error):
        target=Path(name)
        if not target.resolve().is_relative_to(path):raise ValueError('Unsafe cleanup link')
        os.chmod(target,stat.S_IREAD|stat.S_IWRITE|stat.S_IEXEC)
        function(target)
    for attempt in range(8):
        try:shutil.rmtree(path,onexc=writable);return
        except FileNotFoundError:return
        except OSError:
            if attempt==7:raise
            time.sleep(.05*(attempt+1))

def publish_file(source,out):
    """Atomic no-clobber publication; tolerate short Windows indexing/AV locks."""
    target=out/source.name;index=1;attempts=0
    while True:
        try:
            if os.name=='nt':os.rename(source,target)  # Windows rename never replaces an existing target
            else:os.link(source,target);source.unlink()
            return target
        except (FileExistsError,IsADirectoryError):
            target=out/f'{source.stem} ({index}){source.suffix}';index+=1;attempts=0
        except PermissionError:
            if target.exists():
                target=out/f'{source.stem} ({index}){source.suffix}';index+=1;attempts=0
            elif attempts<6:
                time.sleep(.025*2**attempts);attempts+=1
            else:raise
