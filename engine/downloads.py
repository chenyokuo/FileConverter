"""Explicit network-only feature. Local conversion never imports or calls it."""
import base64
import contextlib
import io
import json
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
        'socket_timeout':20,'retries':3,'fragment_retries':3,'nocheckcertificate':False,
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

def clean_entry(info,index=1,engines=None):
    if info.get('has_drm'):raise ValueError('此來源標示為 DRM，File Converter 不處理')
    formats=[]
    for f in info.get('formats') or []:
        if f.get('has_drm'):continue
        formats.append({k:f.get(k) for k in ['format_id','ext','width','height','fps','vcodec','acodec','filesize','filesize_approx','format_note','abr']})
    if not formats and info.get('url') and info.get('_type') not in {'url','url_transparent'}:
        formats=[{'format_id':str(info.get('format_id','direct')),'ext':info.get('ext'),'height':info.get('height'),'width':info.get('width'),'vcodec':info.get('vcodec'),'acodec':info.get('acodec')}]
    return {'key':str(index),'id':str(info.get('id',index)),'title':info.get('title') or str(info.get('id',index)),
        'url':info.get('webpage_url') or info.get('original_url') or info.get('url'),'duration':info.get('duration'),
        'formats':formats,'subtitles':sorted(set(info.get('subtitles') or {})|set(info.get('automatic_captions') or {})),'automaticSubtitles':sorted(info.get('automatic_captions') or {}),'resolved':bool(formats)}

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
        result.append({'url':validate_url(entry['url']),'title':entry['title'],'entryId':entry['id'],'formatId':format_id,
            'audioOnly':bool(item.get('audioOnly')),'audioFormat':audio_format,'subtitles':languages,'convertTo':convert_to})
    if not result:raise ValueError('請選擇下載項目')
    return result

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
    if p['audioOnly']:
        options.update(format='bestaudio/best',postprocessors=[{'key':'FFmpegExtractAudio','preferredcodec':p['audioFormat'],'preferredquality':'192'}])
    else:
        options['format']='bestvideo*+bestaudio/best' if p['formatId']=='best' else p['formatId']+'+bestaudio/'+p['formatId']
        options['merge_output_format']='mkv'
    with yt_dlp.YoutubeDL(options) as ydl:
        info=ydl.extract_info(validate_url(p['url']),download=False)
        if info and info.get('_type') in {'playlist','multi_video'}:
            info=next((entry for entry in info.get('entries',[]) if entry and str(entry.get('id'))==p.get('entryId')),None)
            if not info:raise ValueError('播放清單項目已變更，請重新解析')
        if not info or info.get('has_drm'):raise ValueError('此來源不可下載或包含 DRM')
        info=ydl.process_ie_result(info,download=True)
    if not info or info.get('has_drm'):raise ValueError('此來源不可下載或包含 DRM')
    files=[];media=[]
    for file in cache.iterdir():
        if not file.is_file() or file.suffix.lower() not in {'.mp4','.mkv','.mov','.avi','.wmv','.webm','.mp3','.m4a','.aac','.flac','.wav','.ogg','.opus','.srt','.vtt','.ass'}:continue
        fmt=detect(file,engines)['format']
        if category(fmt) in {'video','audio'}:media.append(file)
        elif file.suffix.lower() in {'.srt','.vtt','.ass'}:files.append(file)
    if not media:raise RuntimeError('下載結果沒有可讀的影音檔案')
    if p.get('convertTo') and not p['audioOnly']:
        emit(0,stats={'phase':'轉檔'})
        files+=convert_media(dict(job,format=p['convertTo'],options=job.get('options',{})),[media[0]],stage,engines)
    else:files+=media
    published=[]
    for file in files:
        if file.parent==stage:published.append(file)
        else:
            target=stage/file.name;shutil.copy2(file,target);published.append(target)
    emit(stats={'phase':'完成下載與後處理'})
    return published
