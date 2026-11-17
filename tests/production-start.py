"""Launch the shipping EXE without CDP, then close only its own native window."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]
candidate = Path(sys.argv[1]).resolve()
assert not any(p.name().lower() == 'fileconverter.exe' for p in psutil.process_iter()), 'An existing app is open'
env = os.environ.copy()
for key in ('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', 'WEBVIEW2_BROWSER_EXECUTABLE_FOLDER', 'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
    env.pop(key, None)
env['WEBVIEW2_USER_DATA_FOLDER'] = str(ROOT / '.tools/multimedia-production-webview')
system_root = os.environ['SystemRoot']
env['PATH'] = system_root + r'\System32;' + system_root
proc = subprocess.Popen([str(candidate / 'FileConverter.exe')], env=env)
user32 = ctypes.windll.user32
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
windows = []
@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def visit(hwnd, _):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title, len(title))
    if pid.value == proc.pid and title.value == 'File Converter' and user32.IsWindowVisible(hwnd):
        windows.append(hwnd)
    return True
deadline = time.monotonic() + 30
children = []
while time.monotonic() < deadline:
    windows.clear()
    user32.EnumWindows(visit, 0)
    children = psutil.Process(proc.pid).children(recursive=True)
    if windows and any(p.name() == 'FileConverterEngine.exe' for p in children) and any(p.name() == 'msedgewebview2.exe' for p in children):
        break
    time.sleep(.2)
assert windows and children, 'Native window/runtime did not start'
time.sleep(5)  # Allow frontend startup; do not close helper windows during initialization.
runtime = [p.exe() for p in children if p.name() in {'FileConverterEngine.exe', 'msedgewebview2.exe'}]
assert runtime and all(str(Path(p)).lower().startswith(str(candidate).lower()) for p in runtime)
for hwnd in windows[:1]:
    user32.PostMessageW(hwnd, 0x10, 0, 0)  # WM_CLOSE, only this test's window
assert proc.wait(timeout=30) == 0
time.sleep(.5)
assert not any(p.is_running() and p.name() == 'FileConverterEngine.exe' for p in children), 'Sidecar survived normal close'
report = {'version': json.loads((ROOT / 'package.json').read_text())['version'], 'nativeWindow': True,
          'CDP': False, 'systemOnlyPATH': True, 'appLocalRuntime': True, 'normalExit': True, 'noSidecarSurvivors': True}
(ROOT / 'test-results/multimedia-production-start.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
