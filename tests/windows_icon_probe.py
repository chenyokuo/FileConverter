"""Read only this app's Shell/window icons. Never alters associations or caches."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import json
import sys
from PIL import Image, ImageChops, ImageStat

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
app=Path(sys.argv[1]).resolve()
if not app.is_relative_to(ROOT) or app.name!='FileConverter.exe':raise ValueError('Only this project application may be inspected')
pid=int(sys.argv[2])
u=c.WinDLL('user32',use_last_error=True);g=c.WinDLL('gdi32',use_last_error=True);shell=c.WinDLL('shell32',use_last_error=True)
class SHINFO(c.Structure):
    _fields_=[('icon',w.HICON),('index',c.c_int),('attributes',w.DWORD),('name',w.WCHAR*260),('type',w.WCHAR*80)]
class ICONINFO(c.Structure):
    _fields_=[('is_icon',w.BOOL),('x',w.DWORD),('y',w.DWORD),('mask',w.HBITMAP),('color',w.HBITMAP)]
class BITMAP(c.Structure):
    _fields_=[('type',w.LONG),('width',w.LONG),('height',w.LONG),('stride',w.LONG),('planes',w.WORD),('bits',w.WORD),('data',c.c_void_p)]
class HEADER(c.Structure):
    _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),('bits',w.WORD),('compression',w.DWORD),('image_size',w.DWORD),('x',w.LONG),('y',w.LONG),('used',w.DWORD),('important',w.DWORD)]
u.GetIconInfo.argtypes=[w.HICON,c.POINTER(ICONINFO)]
u.DestroyIcon.argtypes=[w.HICON]
g.GetObjectW.argtypes=[w.HANDLE,c.c_int,c.c_void_p]
g.CreateCompatibleDC.argtypes=[w.HDC];g.CreateCompatibleDC.restype=w.HDC
g.CreateDIBSection.argtypes=[w.HDC,c.c_void_p,w.UINT,c.POINTER(c.c_void_p),w.HANDLE,w.DWORD];g.CreateDIBSection.restype=w.HBITMAP
g.SelectObject.argtypes=[w.HDC,w.HANDLE];g.SelectObject.restype=w.HANDLE
g.DeleteObject.argtypes=[w.HANDLE];g.DeleteDC.argtypes=[w.HDC]
u.DrawIconEx.argtypes=[w.HDC,c.c_int,c.c_int,w.HICON,c.c_int,c.c_int,w.UINT,w.HBRUSH,w.UINT]

def capture(handle,name):
    info=ICONINFO()
    if not u.GetIconInfo(handle,c.byref(info)):raise c.WinError(c.get_last_error())
    bitmap=BITMAP();g.GetObjectW(info.color,c.sizeof(bitmap),c.byref(bitmap))
    width,height=bitmap.width,bitmap.height
    if not width or not height:raise ValueError('No color icon bitmap')
    dc=g.CreateCompatibleDC(None);pixels=c.c_void_p()
    header=HEADER(c.sizeof(HEADER),width,-height,1,32,0,width*height*4,0,0,0,0)
    dib=g.CreateDIBSection(dc,c.byref(header),0,c.byref(pixels),None,0);previous=g.SelectObject(dc,dib)
    try:
        c.memset(pixels,0,width*height*4)
        if not u.DrawIconEx(dc,0,0,handle,width,height,0,None,3):raise c.WinError(c.get_last_error())
        image=Image.frombytes('RGBA',(width,height),c.string_at(pixels,width*height*4),'raw','BGRA')
        image.save(OUT/f'{name}.png')
        with Image.open(ROOT/'src-tauri/icons/icon.ico') as ico:
            expected=ico.ico.getimage((width,height)).convert('RGB')
        difference=ImageStat.Stat(ImageChops.difference(image.convert('RGB'),expected)).mean
        error=sum(difference)/3
        if error>20:raise AssertionError(f'{name}: unexpected icon pixels, mean error={error}')
        return {'size':[width,height],'meanPixelDifference':round(error,3),'image':f'{name}.png'}
    finally:
        g.SelectObject(dc,previous);g.DeleteObject(dib);g.DeleteDC(dc)
        if info.mask:g.DeleteObject(info.mask)
        if info.color:g.DeleteObject(info.color)

shell.SHGetFileInfoW.argtypes=[w.LPCWSTR,w.DWORD,c.POINTER(SHINFO),w.UINT,w.UINT];shell.SHGetFileInfoW.restype=c.c_size_t
info=SHINFO()
if not shell.SHGetFileInfoW(str(app),0,c.byref(info),c.sizeof(info),0x100):raise c.WinError(c.get_last_error())
result={}
try:result['shell']=capture(info.icon,'p0-shell-icon')
finally:u.DestroyIcon(info.icon)

windows=[]
CALLBACK=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
u.EnumWindows.argtypes=[CALLBACK,w.LPARAM]
u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
@CALLBACK
def visit(hwnd,_):
    owner=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(owner))
    if owner.value==pid:
        title=c.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
        if title.value=='File Converter':windows.append(hwnd)
    return True
u.EnumWindows(visit,0)
if not windows:raise AssertionError('File Converter window was not found')
u.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];u.SendMessageW.restype=c.c_ssize_t
u.GetClassLongPtrW.argtypes=[w.HWND,c.c_int];u.GetClassLongPtrW.restype=c.c_size_t
handle=u.SendMessageW(windows[0],0x7f,0,0) or u.GetClassLongPtrW(windows[0],-14)
if not handle:raise AssertionError('Application window has no native icon')
result['window']=capture(handle,'p0-window-icon')
(OUT/'windows-icons.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
