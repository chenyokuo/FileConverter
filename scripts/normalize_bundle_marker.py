"""Restore only Tauri's three-byte standalone marker after a failed NSIS bundle."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def normalize():
    path=ROOT/'src-tauri/target/release/FileConverter.exe'
    if not path.exists():return
    data=path.read_bytes();marker=b'__TAURI_BUNDLE_TYPE_VAR_';offset=data.find(marker)
    if offset<0 or data.find(marker,offset+1)>=0:raise RuntimeError('Unexpected Tauri marker layout')
    start=offset+len(marker);value=data[start:start+3]
    if value==b'UNK':return
    if value!=b'NSS':raise RuntimeError('Unexpected bundle marker; refusing to patch')
    path.write_bytes(data[:start]+b'UNK'+data[start+3:]);print('Restored Tauri standalone marker NSS -> UNK')
if __name__=='__main__':normalize()
