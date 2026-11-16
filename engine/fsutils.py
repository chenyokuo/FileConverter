"""Cleanup confined to an explicitly owned staging root, including read-only files."""
from pathlib import Path
import os
import shutil
import stat
import time

def remove_tree(path,allowed_parent):
    path=Path(path).resolve();parent=Path(allowed_parent).resolve()
    if path==parent or not path.is_relative_to(parent):raise ValueError('Cleanup path escaped its staging root')
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
