"""Resolve only app-local runtimes; never require installations on end-user PCs."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess

FLAGS=0x08000000 if os.name=='nt' else 0
def locate(root):
    root=Path(root)
    def find(pattern):return next((str(p.resolve()) for p in root.glob(pattern) if p.is_file()),None)
    engines={
        'ffmpeg':find('ffmpeg/ffmpeg.exe'),'ffprobe':find('ffmpeg/ffprobe.exe'),
        'soffice':find('libreoffice/**/program/soffice.com') or find('libreoffice/**/program/soffice.exe'),
        'pandoc':find('pandoc/**/pandoc.exe'),'calibre':find('calibre/**/ebook-convert.exe'),
        'ghostscript':find('ghostscript/**/gswin64c.exe'), 'sevenzip':find('7zip/7z.exe'),
        'deno':find('deno/deno.exe'), 'tessdata':str((root/'tessdata').resolve()) if (root/'tessdata/eng.traineddata').is_file() else None,
    }
    for name,module in [('heif','pillow_heif'),('pdf2docx','pdf2docx'),('pypdf','pypdf'),('opencv','cv2'),('ytdlp','yt_dlp')]:
        engines[name]=module if importlib.util.find_spec(module) else None
    return engines

def command(args, timeout=600, return_stderr=False, **kwargs):
    import ctypes
    from windows_jobs import prevent_orphans
    proc=subprocess.Popen([str(a) for a in args],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        creationflags=FLAGS | (4 if os.name=='nt' else 0),**kwargs)
    handle=None
    try:
        if os.name=='nt':
            handle=prevent_orphans(int(proc._handle))
            resume=ctypes.WinDLL('ntdll').NtResumeProcess;resume.argtypes=[ctypes.c_void_p]
            if resume(int(proc._handle))!=0:raise RuntimeError('Could not resume runtime')
        stdout,stderr=proc.communicate(timeout=timeout)
        if proc.returncode:raise RuntimeError((stderr+stdout).decode('utf-8','replace')[-4000:] or f'Engine exit {proc.returncode}')
        return stderr if return_stderr else stdout
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        if proc.stdout:proc.stdout.close()
        if proc.stderr:proc.stderr.close()
        if handle:
            from windows_jobs import finish_job
            finish_job(handle)


def image_plugins():
    import pillow_heif
    pillow_heif.register_heif_opener()

_HARDWARE_CACHE={}

def hardware(ffmpeg,refresh=False):
    """Actual H.264/HEVC device/driver encodes, not encoder-list advertising."""
    if not refresh and ffmpeg in _HARDWARE_CACHE:return _HARDWARE_CACHE[ffmpeg]
    rows=[{'id':'cpu','label':'CPU','available':True,'encoder':'libx264','codecs':{'h264':True,'h265':True},'reason':''}]
    for id,label,h264,hevc in [('nvidia','NVIDIA','h264_nvenc','hevc_nvenc'),('amd','AMD','h264_amf','hevc_amf'),('intel','Intel','h264_qsv','hevc_qsv')]:
        codecs={};errors=[]
        for codec,encoder in [('h264',h264),('h265',hevc)]:
            try:
                if not ffmpeg:raise RuntimeError('FFmpeg 不可用')
                command([ffmpeg,'-hide_banner','-v','error','-f','lavfi','-i','color=s=128x128:r=30:d=0.15','-an','-c:v',encoder,'-frames:v','3','-f','null','-'],timeout=4)
                codecs[codec]=True
            except Exception as e:codecs[codec]=False;errors.append(str(e)[-250:])
        rows.append({'id':id,'label':label,'available':any(codecs.values()),'encoder':h264,'codecs':codecs,'reason':' / '.join(errors)})
    _HARDWARE_CACHE[ffmpeg]=rows
    return rows
