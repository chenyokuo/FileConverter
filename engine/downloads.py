"""Explicit network-only feature. Local conversion never imports or calls it."""
import base64
import contextlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import time
import urllib.parse
import urllib.request
import uuid

ANALYSES={}

def validate_url(url):
    value=str(url).strip();parts=urllib.parse.urlsplit(value)
    if parts.scheme not in {'https','http'} or not parts.hostname or parts.username or parts.password:raise ValueError('只接受不含內嵌帳密的 HTTP／HTTPS 影片網址')
    return value

class QuietLogger:
    def debug(self,message):pass
    def warning(self,message):pass
    def error(self,message):pass

def settings(engines):
    os.environ['YTDLP_NO_PLUGINS']='1'
    return {'quiet':True,'no_warnings':True,'logger':QuietLogger(),'ignoreerrors':False,'noplaylist':True,
        'socket_timeout':20,'external_downloader_args':{'ffmpeg_i':['-rw_timeout','20000000']},'retries':3,'fragment_retries':3,'nocheckcertificate':False,
        'cookiesfrombrowser':None,'cookiefile':None,'remote_components':set(),
        'js_runtimes':{'deno':{'path':engines['deno']}} if engines.get('deno') else {},
        'ffmpeg_location':str(Path(engines['ffmpeg']).parent) if engines.get('ffmpeg') else None,
        'windowsfilenames':True,'restrictfilenames':False,'trim_file_name':170,'continuedl':True,
        'overwrites':False,'allow_unplayable_formats':False}

def thumbnail(url):
    if not url:return None
    try:
        validate_url(url)
        from PIL import Image
        with urllib.request.urlopen(url,timeout=8) as response:data=response.read(8*1024*1024)
        with Image.open(io.BytesIO(data)) as image:
            image.thumbnail((640,360));out=io.BytesIO();image.convert('RGB').save(out,format='JPEG',quality=85)
        return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()
    except Exception:return None

def preview_url(info):
    # HTML media playback needs a muxed stream; never present a silent video as full preview.
    candidates=[f for f in info.get('formats') or [info] if f.get('url') and f.get('vcodec')!='none' and f.get('acodec')!='none' and f.get('ext') in {'mp4','webm'} and not f.get('has_drm') and f.get('protocol','https') in {'http','https'}]
    candidates.sort(key=lambda f:abs((f.get('height') or 360)-360))
    for f in candidates:
        try:return validate_url(f['url'])
        except ValueError:pass
    return None

def sections(value,duration):
    if not value:return []
    if not isinstance(value,list) or len(value)>100:raise ValueError('區間清單格式錯誤或超過 100 段')
    try:duration=float(duration)
    except (ValueError,TypeError):raise ValueError('長度未知，無法下載指定區間')
    if not math.isfinite(duration) or duration<=0:raise ValueError('長度未知，無法下載指定區間')
    result=[]
    for part in value:
        try:start=float(part['start']);end=float(part['end'])
        except (KeyError,TypeError,ValueError):raise ValueError('區間須包含起訖秒數')
        if not math.isfinite(start) or not math.isfinite(end) or not 0<=start<end<=duration:raise ValueError('區間須符合 0 ≤ 起點 < 終點 ≤ 影片長度')
        result.append({'start':start,'end':end})
    return result

def clean_entry(info,index=1,engines=None):
    if info.get('has_drm'):raise ValueError('此來源標示為 DRM，File Converter 不處理')
    formats=[]
    for f in info.get('formats') or []:
        if f.get('has_drm'):continue
        formats.append({k:f.get(k) for k in ['format_id','ext','width','height','fps','vcodec','acodec','filesize','filesize_approx','format_note','abr']})
    if not formats and info.get('url') and info.get('_type') not in {'url','url_transparent'}:
        formats=[{'format_id':str(info.get('format_id','direct')),'ext':info.get('ext'),'height':info.get('height'),'width':info.get('width'),'vcodec':info.get('vcodec'),'acodec':info.get('acodec')}]
    return {'key':str(index),'id':str(info.get('id',index)),'title':info.get('title') or str(info.get('id',index)),
        'url':info.get('webpage_url') or info.get('original_url') or info.get('url'),'duration':None if info.get('is_live') else info.get('duration'),
        'previewUrl':preview_url(info),'formats':formats,'subtitles':sorted(set(info.get('subtitles') or {})|set(info.get('automatic_captions') or {})),'automaticSubtitles':sorted(info.get('automatic_captions') or {}),'resolved':bool(formats)}

def analyze(url,engines,page=1):
    import yt_dlp
    url=validate_url(url);page=max(1,int(page));options=settings(engines)
    options.update(noplaylist=False,extract_flat='in_playlist',playlist_items=f'{(page-1)*50+1}:{page*50}',skip_download=True)
    with yt_dlp.YoutubeDL(options) as ydl:info=ydl.extract_info(url,download=False)
    if not info:raise ValueError('來源未回傳影片資訊')
    playlist=info.get('_type') in {'playlist','multi_video'}
    raw=list(info.get('entries') or []) if playlist else [info]
    raw=[item for item in raw if item]
    entries=[clean_entry(item,(page-1)*50+i+1,engines) for i,item in enumerate(raw)]
    if not entries:raise ValueError('來源沒有可下載項目')
    token=uuid.uuid4().hex
    ANALYSES[token]={'url':url,'created':time.time(),'entries':{e['key']:e for e in entries}}
    for key in list(ANALYSES):
        if time.time()-ANALYSES[key]['created']>3600 or len(ANALYSES)>64:ANALYSES.pop(key,None)
    return {'analysisId':token,'url':url,'title':info.get('title') or entries[0]['title'],'thumbnail':thumbnail(info.get('thumbnail') or raw[0].get('thumbnail')),
        'duration':info.get('duration'),'playlist':playlist,'entries':entries,'page':page,'hasMore':playlist and len(entries)==50}

def resolve(token,key,engines):
    import yt_dlp
    record=ANALYSES.get(token)
    if not record:raise ValueError('解析資料已過期，請重新解析網址')
    entry=record['entries'].get(str(key))
    if not entry:raise ValueError('無效播放清單項目')
    with yt_dlp.YoutubeDL(settings(engines)) as ydl:info=ydl.extract_info(validate_url(entry['url']),download=False)
    if info.get('_type') in {'playlist','multi_video'}:
        match=next((i for i in info.get('entries',[]) if str(i.get('id'))==entry['id']),None)
        if not match:raise ValueError('此項目需要以獨立影片網址解析')
        info=match
    resolved=clean_entry(info,int(key),engines)
    resolved['url']=info.get('webpage_url') or entry['url']
    record['entries'][str(key)]=resolved
    return resolved

def selected(token,items):
    record=ANALYSES.get(token)
    if not record:raise ValueError('解析資料已過期，請重新解析')
    result=[]
    for item in items:
        entry=record['entries'].get(str(item['key']))
        if not entry:raise ValueError('下載項目不在解析結果中')
        format_id=str(item.get('formatId','best'))
        if format_id!='best' and format_id not in [str(f['format_id']) for f in entry['formats']]:raise ValueError('來源沒有選定的畫質')
        languages=list(item.get('subtitles') or [])
        if any(lang not in entry['subtitles'] for lang in languages):raise ValueError('此項目沒有選定的字幕語言')
        audio_format=item.get('audioFormat','mp3')
        if audio_format not in {'mp3','m4a','flac','wav'}:raise ValueError('不支援的音訊後處理')
        convert_to=item.get('convertTo','')
        if convert_to not in {'','mp4','mkv','webm'}:raise ValueError('不支援的下載後轉檔格式')
        result.append({'url':validate_url(entry['url']),'title':entry['title'],'entryId':entry['id'],'formatId':format_id,'formatHasAudio':any(str(f['format_id'])==format_id and f.get('acodec') not in {None,'none'} for f in entry['formats']),
            'sections':sections(item.get('sections'),entry.get('duration')),'duration':entry.get('duration'),'precise':bool(item.get('precise')),'mergeSections':bool(item.get('mergeSections')),'audioOnly':bool(item.get('audioOnly')),'audioFormat':audio_format,'subtitles':languages,'convertTo':convert_to})
    if not result:raise ValueError('請選擇下載項目')
    return result

@contextlib.contextmanager
def ffmpeg_context(engines):
    # yt-dlp CLI also sets this context for static FFmpegFD capability checks.
    # A per-context token avoids PATH mutation and cross-thread engine leakage.
    from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
    token=FFmpegPostProcessor._ffmpeg_location.set(str(Path(engines['ffmpeg']).parent))
    try:yield
    finally:FFmpegPostProcessor._ffmpeg_location.reset(token)

def execute(job,stage,engines):
    import yt_dlp
    from worker import emit
    from detection import detect
    from registry import category
    from media_engine import convert_media
    p=job['download'];cache=Path(job['downloadCache']);cache.mkdir(parents=True,exist_ok=True)
    options=settings(engines)
    def progress(data):
        total=data.get('total_bytes') or data.get('total_bytes_estimate')
        current=data.get('downloaded_bytes') or 0
        stats={'downloadedBytes':current,'totalBytes':total,'downloadSpeed':data.get('speed'),'downloadEta':data.get('eta'),'phase':'下載'}
        emit(min(99,current/total*100) if total else None,stats=stats)
    def postprocess(data):emit(0 if data.get('status')=='started' else None,stats={'phase':'後處理','postprocessor':data.get('postprocessor')})
    options.update(paths={'home':str(cache),'temp':str(cache)},outtmpl={'default':'%(title).130B [%(id)s].%(ext)s'},
        progress_hooks=[progress],postprocessor_hooks=[postprocess],writesubtitles=bool(p.get('subtitles')),
        writeautomaticsub=bool(p.get('subtitles')),subtitleslangs=p.get('subtitles',[]),subtitlesformat='srt/vtt/best',noplaylist=True)
    parts=sections(p.get('sections'),p.get('duration'))
    if parts:
        # Python API equivalent of official --download-sections. Preserve caller order.
        options['download_ranges']=lambda *_: [{'start_time':r['start'],'end_time':r['end'],'index':i+1} for i,r in enumerate(parts)]
        options['force_keyframes_at_cuts']=bool(p.get('precise'))
        options['outtmpl']={'default':'%(title).100B [%(id)s]-section-%(section_number)03d.%(ext)s'}
        emit(stats={'phase':'區間下載','warning':'精確模式重新編碼' if p.get('precise') else '快速裁切依關鍵影格，實際起訖可能偏移；可改精確模式'})
    if parts and p.get('subtitles'):emit(stats={'warning':'字幕保留來源完整時間軸；不自動裁切或重設字幕時間，請另行裁切字幕並調整時間'})
    if p['audioOnly']:
        options.update(format='bestaudio/best',postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':p['audioFormat'],'preferredquality':'192'}])
    else:
        options['format']='bestvideo*+bestaudio/best' if p['formatId']=='best' else p['formatId'] if p.get('formatHasAudio') else p['formatId']+'+bestaudio/'+p['formatId']
        options['merge_output_format']='mkv'
    with ffmpeg_context(engines),yt_dlp.YoutubeDL(options) as ydl:
        info=ydl.extract_info(validate_url(p['url']),download=False)
        if info and info.get('_type') in {'playlist','multi_video'}:
            info=next((entry for entry in info.get('entries',[]) if entry and str(entry.get('id'))==p.get('entryId')),None)
            if not info:raise ValueError('播放清單項目已變更，請重新解析')
        if not info or info.get('has_drm'):raise ValueError('此來源不可下載或包含 DRM')
        if parts:
            if info.get('is_live'):raise ValueError('直播來源不支援已知長度區間下載')
            sections(parts,info.get('duration') or p.get('duration'))
        info=ydl.process_ie_result(info,download=True)
    if not info or info.get('has_drm'):raise ValueError('此來源不可下載或包含 DRM')
    files=[];media=[]
    for file in cache.iterdir():
        if not file.is_file() or file.suffix.lower() not in {'.mp4','.mkv','.mov','.avi','.wmv','.webm','.mp3','.m4a','.aac','.flac','.wav','.ogg','.opus','.srt','.vtt','.ass'}:continue
        fmt=detect(file,engines)['format']
        if category(fmt) in {'video','audio'}:media.append(file)
        elif file.suffix.lower() in {'.srt','.vtt','.ass'}:files.append(file)
    if not media:raise RuntimeError('下載結果沒有可讀的影音檔案')
    media.sort(key=lambda f:f.name)
    if parts and len(media)!=len(parts):raise RuntimeError('區間輸出數量與選取不一致；來源可能不支援區間取得，請改下載完整影片後裁切')
    if p.get('mergeSections') and len(media)>1:
        emit(stats={'phase':'合併下載片段'})
        if p['audioOnly']:
            target=stage/('merged.'+p['audioFormat']);args=[engines['ffmpeg'],'-v','error','-nostdin']
            for path in media:args+=['-i',path]
            graph=''.join(f'[{i}:a:0]' for i in range(len(media)))+f'concat=n={len(media)}:v=0:a=1[a]'
            from runtime import command
            command([*args,'-filter_complex',graph,'-map','[a]','-n',target]);media=[target]
        else:
            from media_tools import merge
            media=merge(job,media,stage,engines,stage/'merged.mkv')
    if p.get('convertTo') and not p['audioOnly']:
        emit(0,stats={'phase':'轉檔'})
        for index,path in enumerate(media):
            # Separate staging avoids duplicate names between section conversion outputs.
            part_stage=stage/f'part-{index+1:03d}';part_stage.mkdir()
            for converted in convert_media(dict(job,format=p['convertTo'],options=job.get('options',{})),[path],part_stage,engines):
                target=stage/converted.name;converted.rename(target);files.append(target)
            part_stage.rmdir()
    else:files+=media
    published=[]
    for file in files:
        if file.parent==stage:published.append(file)
        else:
            target=stage/file.name;shutil.copy2(file,target);published.append(target)
    emit(stats={'phase':'完成下載與後處理'})
    return published
