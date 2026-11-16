"""Single capability registry and directed conversion graph for UI and workers."""
from collections import deque
from detection import normalize

IMAGE = {'jpg','png','webp','bmp','tiff'}
VIDEO = {'mp4','mov','mkv','avi','webm'}
AUDIO = {'mp3','wav','flac','aac','ogg','m4a','opus'}
OFFICE = {
    'docx':['pdf','odt','docx','rtf','txt'], 'odt':['pdf','docx','odt','rtf','txt'],
    'doc':['pdf','docx','odt','rtf','txt'], 'rtf':['pdf','docx','odt','txt'],
    'xlsx':['pdf','ods','xlsx','csv'], 'ods':['pdf','xlsx','ods','csv'], 'xls':['pdf','xlsx','ods','csv'],
    'pptx':['pdf','odp','pptx'], 'odp':['pdf','pptx','odp'], 'ppt':['pdf','pptx','odp'],
}
def category(fmt):
    fmt = normalize(fmt)
    return 'image' if fmt in IMAGE else 'video' if fmt in VIDEO else 'audio' if fmt in AUDIO else 'pdf' if fmt=='pdf' else 'office' if fmt in OFFICE else 'unsupported'

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
    engines = engines or {}
    edges=[]
    for source in sorted(IMAGE|VIDEO|AUDIO|{'pdf'}|set(OFFICE)):
        kind=category(source)
        targets = ['png','jpg','webp','bmp','tiff','pdf'] if kind=='image' else ['mp4','mov','mkv','avi','webm',*sorted(AUDIO)] if kind=='video' else sorted(AUDIO) if kind=='audio' else ['png','jpg','pdf'] if kind=='pdf' else OFFICE[source]
        for target in targets:
            adapter='ffmpeg' if kind in {'video','audio'} else 'libreoffice' if kind=='office' else 'pymupdf' if kind=='pdf' or target=='pdf' else 'pillow'
            available=bool(engines.get('ffmpeg') and engines.get('ffprobe')) if adapter=='ffmpeg' else bool(engines.get('soffice')) if adapter=='libreoffice' else True
            lossy = target in {'jpg','webp','mp3','aac','m4a','ogg','opus'} or kind in {'video','office'} or kind=='pdf' and target!='pdf'
            settings = ['quality','width','height','matte'] if adapter=='pillow' else (['pdfDpi'] if target!='pdf' else ['pages','rotation','split'] if source=='pdf' else []) if adapter=='pymupdf' else ['videoCodec','crf','videoBitrate','videoHeight','fps','audioBitrate','sampleRate','channels'] if kind=='video' else ['audioBitrate','sampleRate','channels'] if kind=='audio' else []
            tested = source=='png' and kind=='image' or source=='pdf' or source=='mp4'
            edges.append({'id':f'{source}:{target}', 'source':source,'target':target,'category':kind,'engine':adapter,
                'available':available, 'reason':'' if available else '需要 FFmpeg 與 FFprobe' if adapter=='ffmpeg' else '需要本機 LibreOffice；完整離線 Runtime 封裝排定 P1',
                'testStatus':'regression-covered' if tested and adapter!='libreoffice' else 'not-verified',
                'lossy':lossy,'settings':settings, 'qualityNote':'會重新編碼；品質、透明度或排版可能改變' if lossy else '保留內容；色彩描述、動畫或中繼資料未保證保留',
                'intermediate':False, 'operationRequired':source==target=='pdf'})
    return edges

def outputs(source): return [e['target'] for e in capabilities() if e['source']==normalize(source)]
def registry(engines):
    edges=capabilities(engines)
    return {'version':1,'edges':edges,'sources':sorted({e['source'] for e in edges}),
        'adapters':[{'id':name,'available':any(e['available'] for e in edges if e['engine']==name)} for name in ['pillow','pymupdf','ffmpeg','libreoffice']],
        'execution':'direct-only; intermediate routes are planning information, not automatically executed'}

def validate(source, target, engines, options=None, count=1):
    edge=next((e for e in capabilities(engines) if e['source']==normalize(source) and e['target']==normalize(target)),None)
    if not edge:raise ValueError(f'不支援 {source} → {target}')
    opt=options or {}
    if edge['operationRequired'] and count==1 and not (str(opt.get('pages','')).strip() or opt.get('split') or int(opt.get('rotation',0))):
        raise ValueError('PDF → PDF 請設定頁碼、旋轉、分割，或加入多檔合併')
    return edge
