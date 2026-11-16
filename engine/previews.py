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

def preview(path,engines,page=0,time=0):
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
            pix=document[index].get_pixmap(dpi=100,alpha=False)
            result['image']='data:image/png;base64,'+base64.b64encode(pix.tobytes('png')).decode()
            result['metadata']={'pages':len(document),'page':index+1,'dimensions':[document[index].rect.width,document[index].rect.height]}
    elif fmt in {'mp4','mov','mkv','avi','wmv','webm','mp3','wav','m4a','aac','ogg','flac','opus'}:
        from worker import probe
        info=probe(path,engines['ffprobe']);streams=info.get('streams',[])
        result['metadata']={'duration':info.get('format',{}).get('duration'),'streams':[{k:s.get(k) for k in ['index','codec_type','codec_name','width','height','sample_rate','channels','tags']} for s in streams]}
        if any(s.get('codec_type')=='video' for s in streams):
            with tempfile.TemporaryDirectory(prefix='file-converter-frame-') as directory:
                frame=Path(directory)/'frame.png'
                command([engines['ffmpeg'],'-v','error','-nostdin','-ss',str(max(0,float(time))),'-i',path,'-frames:v','1','-vf','scale=1000:-1','-n',frame],timeout=45)
                if frame.exists():
                    with Image.open(frame) as image:result['image']=data_image(image)
    elif path.suffix.lower() in {'.txt','.md','.html','.csv','.tsv','.json','.srt','.vtt','.ass'}:
        with path.open('r',encoding='utf-8-sig',errors='replace') as source:result['text']=source.read(16000)
    return result
