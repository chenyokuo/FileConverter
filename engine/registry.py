"""Single capability registry and directed conversion graph for UI and workers."""
from collections import deque
from detection import normalize

IMAGE = {'jpg','png','webp','bmp','tiff','gif','heic','avif'}
VIDEO = {'mp4','mov','mkv','avi','webm','wmv'}
AUDIO = {'mp3','wav','flac','aac','ogg','m4a','opus'}
OFFICE = {
    'csv':['xlsx','ods','pdf','tsv'], 'tsv':['xlsx','ods','pdf','csv'],
    'md':['html','docx','pdf','txt'], 'html':['md','docx','pdf','txt'], 'txt':['md','html','docx','pdf'],
    'docx':['pdf','doc','odt','docx','rtf','txt','md','html'], 'odt':['pdf','doc','docx','odt','rtf','txt'],
    'doc':['pdf','docx','odt','rtf','txt'], 'rtf':['pdf','docx','odt','txt'],
    'xlsx':['pdf','xls','ods','xlsx','csv','tsv'], 'ods':['pdf','xls','xlsx','ods','csv','tsv'], 'xls':['pdf','xlsx','ods','csv'],
    'pptx':['pdf','ppt','odp','pptx'], 'odp':['pdf','ppt','pptx','odp'], 'ppt':['pdf','pptx','odp'],
}
def category(fmt):
    fmt = normalize(fmt)
    return 'image' if fmt in IMAGE else 'video' if fmt in VIDEO else 'audio' if fmt in AUDIO else 'pdf' if fmt=='pdf' else 'office' if fmt in OFFICE else 'ebook' if fmt in {'epub','mobi','azw3','fb2'} else 'vector' if fmt in {'svg','eps'} else 'unsupported'

class ConversionGraph:
    def __init__(self, edges): self.edges = edges
    def path(self, source, target, available_only=True):
        source,target = normalize(source),normalize(target)
        direct = [e for e in self.edges if e['source']==source and e['target']==target and (e['available'] or not available_only)]
        if direct: return direct[:1]
        queue=deque([(source,[])]);seen={source}
        while queue:
            node,path=queue.popleft()
            for edge in self.edges:
                if edge['source'] != node or (available_only and not edge['available']):continue
                route=path+[edge]
                if edge['target']==target:return route
                if edge['target'] not in seen:seen.add(edge['target']);queue.append((edge['target'],route))
        return []

def capabilities(engines=None):
    engines=engines or {};edges=[]
    from pathlib import Path
    import json
    verified_path=Path(__file__).with_name('verified-capabilities.json')
    verified=set(json.loads(verified_path.read_text(encoding='utf-8'))) if verified_path.exists() else set()
    sources=IMAGE|VIDEO|AUDIO|{'pdf','svg','eps','epub','mobi','azw3','fb2'}|set(OFFICE)
    for source in sorted(sources):
        kind=category(source)
        targets=sorted(IMAGE)+['pdf'] if kind=='image' else ['mp4','mov','mkv','avi','webm','wmv',*sorted(AUDIO)] if kind=='video' else sorted(AUDIO) if kind=='audio' else ['png','jpg','pdf','docx','txt','svg','eps'] if kind=='pdf' else ['pdf','png','eps'] if source=='svg' else ['pdf','png'] if source=='eps' else [x for x in ['epub','mobi','azw3','fb2'] if x!=source] if kind=='ebook' else OFFICE[source]
        for target in targets:
            engine='ffmpeg' if kind in {'video','audio'} else 'calibre' if kind=='ebook' else 'ghostscript' if source=='eps' or target=='eps' else 'pymupdf-vector' if source=='svg' or target=='svg' else 'pdf2docx' if source=='pdf' and target=='docx' else 'pdf-text' if source=='pdf' and target=='txt' else 'pandoc' if source in {'md','html','txt'} or source=='docx' and target in {'md','html'} else 'libreoffice' if kind=='office' else 'pymupdf' if kind=='pdf' or target=='pdf' else 'pillow'
            required={'ffmpeg':['ffmpeg','ffprobe'],'calibre':['calibre'],'ghostscript':['ghostscript'],'pdf2docx':['pdf2docx'],'pandoc':['pandoc']+(['soffice'] if target=='pdf' else []),'libreoffice':['soffice']}.get(engine,[])
            if source=='heic' or target=='heic':required+=['heif']
            available=all(engines.get(k) for k in required)
            lossy=target in {'jpg','webp','heic','avif','gif','mp3','aac','m4a','ogg','opus'} or kind in {'video','office'} or source=='pdf' and target!='pdf'
            settings=['quality','width','height','matte'] if engine=='pillow' else (['pdfDpi'] if target in {'png','jpg'} else ['pages','rotation','split'] if source==target=='pdf' else []) if engine=='pymupdf' else ['hardware','qualityPreset','videoCodec','crf','videoBitrate','videoHeight','fps','audioBitrate','sampleRate','channels'] if kind=='video' else ['audioBitrate','sampleRate','channels'] if kind=='audio' else []
            id=source+':'+target
            legacy=source in {'png','pdf','mp4'} and target in {'png','jpg','webp','bmp','tiff','pdf','mp4','mov','mkv','avi','webm',*AUDIO}
            edges.append({'id':id,'source':source,'target':target,'category':kind,'engine':engine,'available':available,
                'reason':'' if available else '隨附 Runtime 不完整：'+', '.join(k for k in required if not engines.get(k)),
                'testStatus':'regression-covered' if id in verified or legacy else 'not-verified',
                'lossy':lossy,'settings':settings,'qualityNote':'PDF → DOCX 無法保證文字、表格、字型及版面完全還原；掃描文件請先 OCR' if engine=='pdf2docx' else '動畫僅 GIF / WebP 輸出保留；其他格式使用第一畫格。可能損失中繼資料或色彩' if kind=='image' else '重新編碼或重排可能改變品質、樣式或中繼資料' if lossy else '保留內容；未保證所有中繼資料保真',
                'intermediate':engine in {'ghostscript','pandoc'} and (source=='svg' or target=='pdf' and source!='eps'),
                'operationRequired':source==target=='pdf'})
    return edges

def outputs(source): return [e['target'] for e in capabilities() if e['source']==normalize(source)]
def registry(engines):
    edges=capabilities(engines)
    return {'version':1,'edges':edges,'sources':sorted({e['source'] for e in edges}),
        'adapters':[{'id':name,'available':any(e['available'] for e in edges if e['engine']==name)} for name in sorted({e['engine'] for e in edges})],
        'execution':'direct-only; intermediate routes are planning information, not automatically executed'}

def validate(source, target, engines, options=None, count=1):
    edge=next((e for e in capabilities(engines) if e['source']==normalize(source) and e['target']==normalize(target)),None)
    if not edge:raise ValueError(f'不支援 {source} → {target}')
    opt=options or {}
    if edge['operationRequired'] and count==1 and not (str(opt.get('pages','')).strip() or opt.get('split') or int(opt.get('rotation',0))):
        raise ValueError('PDF → PDF 請設定頁碼、旋轉、分割，或加入多檔合併')
    return edge
