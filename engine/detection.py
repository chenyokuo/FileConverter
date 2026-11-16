"""Content-first detection. Native infer is a hint, never authority for conversion."""
import json
import os
from pathlib import Path
import subprocess
import struct
import zipfile

ALIASES = {'jpeg': 'jpg', 'tif': 'tiff', 'm4v': 'mp4', 'heif':'heic', 'htm':'html', 'markdown':'md'}
def normalize(value):
    value = str(value).lower().lstrip('.')
    return ALIASES.get(value, value)

def compound_streams(path, header):
    """Read CFB FAT/directory chains, bounded by file size; never inspect macro code."""
    sector_size = 1 << struct.unpack_from('<H', header, 30)[0]
    if sector_size not in {512,4096}: raise ValueError('Invalid CFB sector size')
    count = Path(path).stat().st_size // sector_size
    free = 0xfffffffa
    with Path(path).open('rb') as stream:
        def sector(index):
            if index >= count: raise ValueError('Invalid CFB sector')
            stream.seek((index+1)*sector_size)
            data=stream.read(sector_size)
            if len(data)!=sector_size: raise ValueError('Truncated CFB sector')
            return data
        difat = list(struct.unpack_from('<109I',header,76))
        index = struct.unpack_from('<I',header,68)[0];visited=set()
        while index < free:
            if index in visited:raise ValueError('Cyclic CFB DIFAT')
            visited.add(index);items=struct.unpack('<'+'I'*(sector_size//4),sector(index))
            difat.extend(items[:-1]);index=items[-1]
        fat=[]
        for index in difat:
            if index < free:fat.extend(struct.unpack('<'+'I'*(sector_size//4),sector(index)))
        index=struct.unpack_from('<I',header,48)[0];visited=set();names=set()
        while index < free:
            if index in visited or index>=len(fat):raise ValueError('Invalid CFB directory chain')
            visited.add(index);data=sector(index)
            for offset in range(0,sector_size,128):
                length=struct.unpack_from('<H',data,offset+64)[0]
                if data[offset+66]==2 and 2<=length<=64:
                    names.add(data[offset:offset+length-2].decode('utf-16le','replace'))
            index=fat[index]
        return names

def detect(path, engines, native=None):
    try: return _detect(path, engines, native)
    except Exception as error:
        return {'format':'', 'extension':normalize(Path(path).suffix), 'method':'content validation failed',
                'native':native or None, 'warning':f'無法讀取或辨識檔案：{error}'}

def _detect(path, engines, native=None):
    from PIL import Image
    from runtime import image_plugins
    image_plugins()
    p = Path(path)
    ext = normalize(p.suffix)
    with p.open('rb') as stream: head = stream.read(16384)
    result = {'format': '', 'extension': ext, 'method': '', 'native': native or None, 'warning': ''}
    fmt = ''; method = ''
    try:
        with Image.open(p) as image:
            fmt = normalize(image.format); image.verify()
        method = 'Pillow header + decoder'
    except Exception: pass
    if not fmt and b'%PDF-' in head[:1024]:
        import pymupdf
        with pymupdf.open(p) as doc:
            if not doc.is_pdf: raise ValueError('PDF 容器無效')
        fmt = 'pdf'; method = 'PDF header + MuPDF container'
    if not fmt and head.startswith(b'PK'):
        try:
            with zipfile.ZipFile(p) as archive:
                names = set(archive.namelist())
                if '[Content_Types].xml' in names:
                    for part, office in [('word/document.xml','docx'),('xl/workbook.xml','xlsx'),('ppt/presentation.xml','pptx')]:
                        if part in names: fmt = office; break
                if 'mimetype' in names and archive.getinfo('mimetype').file_size < 256:
                    mime = archive.read('mimetype').decode('ascii', 'replace')
                    fmt = {'application/epub+zip':'epub','application/vnd.oasis.opendocument.text':'odt', 'application/vnd.oasis.opendocument.spreadsheet':'ods',
                           'application/vnd.oasis.opendocument.presentation':'odp'}.get(mime, fmt)
            method = 'ZIP package entries / ODF mimetype'
        except zipfile.BadZipFile: pass
    if not fmt and head.lstrip().startswith(b'{\\rtf'): fmt = 'rtf'; method = 'RTF header'
    if not fmt and head.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        # CFB directory names distinguish legacy Office containers without executing macros.
        streams = compound_streams(p,head)
        fmt = 'doc' if 'WordDocument' in streams else 'xls' if streams & {'Workbook','Book'} else 'ppt' if 'PowerPoint Document' in streams else ''
        method = 'OLE compound stream directory'
    if not fmt and head.startswith(b'%!PS-Adobe') and b'EPSF' in head[:128]:fmt='eps';method='PostScript EPS header'
    if not fmt and b'BOOKMOBI' in head[:80]:
        offset=struct.unpack_from('>I',head,78)[0]
        with p.open('rb') as stream:
            stream.seek(offset+36);version=struct.unpack('>I',stream.read(4))[0]
        fmt='azw3' if version>=8 else 'mobi';method='Palm/MOBI header version'
    if not fmt:
        try:
            text=head.decode('utf-8-sig')
            import re
            if re.search(r'<(?:\w+:)?svg[\s>]',text):fmt='svg';method='SVG XML root'
            elif re.search(r'<(?:\w+:)?FictionBook[\s>]',text):fmt='fb2';method='FictionBook XML root'
            elif re.search(r'<!doctype\s+html|<html[\s>]',text,re.I):fmt='html';method='HTML document header'
            elif ext in {'md','txt','csv','tsv'} and '\x00' not in text:
                fmt=ext;method='UTF-8 text; declared textual subtype'
        except UnicodeDecodeError:pass
    if not fmt and engines.get('ffprobe'):
        probe = subprocess.run([engines['ffprobe'], '-v','error','-show_format','-show_streams','-of','json',str(p)],
            capture_output=True, timeout=30, creationflags=0x08000000 if os.name=='nt' else 0)
        if probe.returncode == 0:
            info = json.loads(probe.stdout)
            streams = info.get('streams', [])
            video = any(s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic') for s in streams)
            names = info.get('format',{}).get('format_name','').split(',')
            if 'mov' in names:
                fmt = 'mov' if head[8:12] == b'qt  ' else 'mp4' if video else 'm4a'
            elif 'matroska' in names: fmt = 'webm' if b'webm' in head[:4096] else 'mkv'
            elif 'asf' in names: fmt='wmv' if video else ''
            elif 'ogg' in names: fmt = 'opus' if any(s.get('codec_name')=='opus' for s in streams) else 'ogg'
            else: fmt = next((n for n in names if n in {'avi','mp3','wav','flac','aac'}), '')
            method = 'FFprobe streams + container header'
    result.update(format=fmt, method=method)
    if fmt and fmt != ext: result['warning'] = f'副檔名 {ext or "無"} 與內容不同；依實際 {fmt.upper()} 處理'
    if not fmt: result['warning'] = '無法辨識內容、檔案已損壞，或此格式尚未支援'
    return result
