"""Observe a real NSIS update/restart; restore only QA-changed preferences."""
from pathlib import Path
import ctypes,hashlib,json,os,sqlite3,sys,time
from ctypes import wintypes
import psutil
ROOT=Path(__file__).resolve().parents[1]
candidate=Path(sys.argv[1]).resolve()
assert candidate.parent==ROOT/'.tools' and candidate.name=='multimedia-installed-1.1.0-rc.3'
expected=json.loads((ROOT/'test-results/release-verification.json').read_text())['installerExeSha256']
exe=candidate/'FileConverter.exe';deadline=time.monotonic()+600;process=None
while time.monotonic()<deadline:
    try:
        with exe.open('rb') as f:matches=hashlib.file_digest(f,'sha256').hexdigest()==expected
        if matches:
            process=next((p for p in psutil.process_iter() if p.name().lower()=='fileconverter.exe' and Path(p.exe()).resolve()==exe),None)
            if process:break
    except (OSError,psutil.Error):pass
    time.sleep(1)
assert process,'Signed NSIS did not install and restart the final release'
user32=ctypes.windll.user32
user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes=[wintypes.HWND]
user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
windows=[]
@ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
def collect(hwnd,_):
    pid=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
    if pid.value==process.pid and user32.IsWindowVisible(hwnd):
        text=ctypes.create_unicode_buffer(256);user32.GetWindowTextW(hwnd,text,256)
        if text.value=='File Converter':windows.append(hwnd)
    return True
deadline=time.monotonic()+45
while time.monotonic()<deadline:
    user32.EnumWindows(collect,0)
    if windows:break
    time.sleep(.25)
assert windows,'Updated app did not show its actual native window'
time.sleep(3)
children=[p for p in process.children(recursive=True) if p.name().lower()=='fileconverterengine.exe']
assert children and all(Path(p.exe()).is_relative_to(candidate/'binaries') for p in children)
data=Path(os.environ['APPDATA'])/'studio.rai.converter';database=data/'history.sqlite3'
with sqlite3.connect(database) as con:settings=json.loads(con.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0])
before=json.loads((ROOT/'.tools/updater-restore-settings.json').read_text())
assert settings['updater']['autoInstall'] and settings['updater']['autoDownload'],'Auto-install preference was not preserved'
without_update=lambda value:{k:v for k,v in value.items() if k!='updater'}
assert without_update(settings)==without_update(before),'Existing appearance/conversion settings changed'
report={'realSignedNSISUpdate':True,'finalInstallerPayloadHash':expected,'nativeWindowRestarted':True,'appLocalFrozenSidecar':True,'autoInstallExercised':True,'settingsPreservedAcrossUpdate':True}
user32.PostMessageW(windows[0],0x10,0,0)
process.wait(timeout=30)
assert not any(p.name().lower()=='fileconverterengine.exe' and Path(p.exe()).is_relative_to(candidate) for p in psutil.process_iter())
# The preference toggles belong only to this QA session. Restore the exact user
# settings after the updated application closes; never replace history tables.
with sqlite3.connect(database) as con:con.execute('INSERT OR REPLACE INTO settings VALUES (1,?)',(json.dumps(before),));con.commit()
report['normalExitNoSidecar']=True;report['qaPreferencesRestored']=True
(ROOT/'test-results/updater-installed-upgrade.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
