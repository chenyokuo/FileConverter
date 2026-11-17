"""Read-only bounded visual previews; never expose arbitrary filesystem URLs."""
import base64
import io
from pathlib import Path
import tempfile
from PIL import Image,ImageOps
from runtime import image_plugins,command
from detection import detect

def data_image(image):
    image=ImageOps.exif_transpose(image).convert('RGBA');image.thumbnail((1400,1000))
    stream=io.BytesIO();image.save(stream,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()

def preview(path,engines,page=0,time=0,play=False,scratch=None):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('預覽檔案不存在')
    image_plugins();detected=detect(path,engines);fmt=detected['format']
    result={'path':str(path),'name':path.name,'format':fmt,'size':path.stat().st_size,'image':None,'metadata':{}}
    try:
        with Image.open(path) as image:
            from file_tools import image_metadata
            result['image']=data_image(image);result['metadata']=image_metadata(path)
            return result
    except (OSError,ValueError):pass
    if fmt in {'pdf','svg','epub','fb2'}:
        import pymupdf
        with pymupdf.open(path) as document:
            if document.needs_pass:raise ValueError('加密 PDF 請先使用授權解密工具')
            index=int(page)
            if not 0<=index<len(document):raise ValueError('預覽頁碼超出範圍')
            rect=document[index].rect
            pix=document[index].get_pixmap(matrix=pymupdf.Matrix(min(1.4,1400/max(1,rect.width),1000/max(1,rect.height)),min(1.4,1400/max(1,rect.width),1000/max(1,rect.height))),alpha=False)
            result['image']='data:image/png;base64,'+base64.b64encode(pix.tobytes('png')).decode()
            result['metadata']={'pages':len(document),'page':index+1,'dimensions':[document[index].rect.width,document[index].rect.height]}
    elif fmt in {'mp4','mov','mkv','avi','wmv','webm','mp3','wav','m4a','aac','ogg','flac','opus'}:
        from worker import probe
        info=probe(path,engines['ffprobe']);streams=info.get('streams',[])
        result['metadata']={'duration':info.get('format',{}).get('duration'),'streams':[{k:s.get(k) for k in ['index','codec_type','codec_name','width','height','sample_rate','channels','tags']} for s in streams]}
        if any(s.get('codec_type')=='video' for s in streams):
            with tempfile.TemporaryDirectory(prefix='frame-',dir=scratch) as directory:
                frame=Path(directory)/'frame.png'
                command([engines['ffmpeg'],'-v','error','-nostdin','-ss',str(max(0,float(time))),'-i',path,'-frames:v','1','-vf','scale=1000:-1','-n',frame],timeout=45)
                if frame.exists():
                    with Image.open(frame) as image:result['image']=data_image(image)
        if play:
            has_video=any(s.get('codec_type')=='video' for s in streams)
            with tempfile.TemporaryDirectory(prefix='play-',dir=scratch) as directory:
                sample=Path(directory)/('sample.mp4' if has_video else 'sample.m4a')
                args=[engines['ffmpeg'],'-v','error','-nostdin','-ss',str(max(0,float(time))),'-i',path,'-t','15']
                args+=['-map','0:v:0','-map','0:a:0?','-vf','scale=640:-2','-c:v','libx264','-preset','ultrafast','-crf','25','-pix_fmt','yuv420p'] if has_video else ['-vn']
                command(args+['-c:a','aac','-b:a','96k','-movflags','+faststart','-n',sample],timeout=90)
                result['media']='data:'+('video/mp4' if has_video else 'audio/mp4')+';base64,'+base64.b64encode(sample.read_bytes()).decode()
                result['mediaKind']='video' if has_video else 'audio';result['clipSeconds']=15
    elif fmt in __import__('registry').OFFICE and fmt not in {'txt','md','html','csv','tsv'}:
        from documents import office
        from fsutils import remove_tree
        directory=Path(tempfile.mkdtemp(prefix='doc-',dir=scratch))
        try:
            files=office({'format':'pdf'},[path],directory,engines)
            rendered=preview(files[0],engines,page=page,scratch=scratch)
            result['image']=rendered['image'];result['metadata']=rendered['metadata'];result['metadata']['renderedWith']='LibreOffice PDF 預覽，可能與原版面不同'
        finally:remove_tree(directory,directory.parent)
    elif path.suffix.lower() in {'.txt','.md','.html','.csv','.tsv','.json','.srt','.vtt','.ass'}:
        with path.open('r',encoding='utf-8-sig',errors='replace') as source:result['text']=source.read(16000)
    return result
