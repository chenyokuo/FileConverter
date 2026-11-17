"""Versioned non-destructive timelines; the same renderer powers preview and export."""
import math,json,shutil,subprocess,tempfile
from pathlib import Path
from runtime import FLAGS

def number(value,low,high,label):
 try:v=float(value)
 except (ValueError,TypeError):raise ValueError(label+' 必須為數字')
 if not math.isfinite(v) or not low<=v<=high:raise ValueError(label+' 超出範圍')
 return v

def validate(project,engines,check_sources=True):
 from worker import probe
 from PIL import Image
 if project.get('type')!='fcvideo' or project.get('version')!=1:raise ValueError('不支援的影片專案版本')
 clean={'type':'fcvideo','version':1,'width':int(number(project.get('width',1280),64,7680,'寬度'))//2*2,'height':int(number(project.get('height',720),64,4320,'高度'))//2*2,'fps':number(project.get('fps',30),1,120,'FPS'),'clips':[],'titles':[],'export':project.get('export',{})}
 if len(project.get('clips',[]))>1000:raise ValueError('單一專案最多 1000 片段')
 cache={};ids=set()
 for raw in project.get('clips',[]):
  clip={'id':str(raw['id']),'source':str(Path(raw['source']).resolve()),'track':str(raw.get('track','V1'))}
  if clip['id'] in ids:raise ValueError('片段 ID 重複')
  ids.add(clip['id'])
  if not __import__('re').fullmatch(r'[VA][1-9][0-9]*',clip['track']):raise ValueError('無效軌道')
  for key,default,lo,hi in [('at',0,0,864000),('in',0,0,864000),('out',5,.001,864000),('speed',1,.25,4),('volume',1,0,4),('fadeIn',0,0,864000),('fadeOut',0,0,864000),('transition',0,0,864000),('x',.65,0,1),('y',.65,0,1),('size',.3,.05,1)]:clip[key]=number(raw.get(key,default),lo,hi,key)
  clip['mute']=bool(raw.get('mute',False));clip['kind']=raw.get('kind','video')
  if clip['out']<=clip['in']:raise ValueError('片段終點必須大於起點')
  duration=(clip['out']-clip['in'])/clip['speed']
  if max(clip['fadeIn'],clip['fadeOut'],clip['transition'])>duration:raise ValueError('淡入淡出／轉場超過片段長度')
  if check_sources:
   path=Path(clip['source'])
   if not path.is_file():raise ValueError('遺失素材：'+str(path))
   if clip['source'] not in cache:
    try:
     with Image.open(path) as image:cache[clip['source']]={'kind':'image','duration':None}
    except (OSError,ValueError):
     info=probe(path,engines['ffprobe']);cache[clip['source']]={'kind':'video' if any(s.get('codec_type')=='video' for s in info['streams']) else 'audio','duration':float(info.get('format',{}).get('duration') or 0),'streams':info['streams']}
   meta=cache[clip['source']];clip['kind']=meta['kind']
   if meta['duration'] and clip['out']>meta['duration']+.05:raise ValueError('裁切超過來源長度：'+path.name)
   if clip['track'].startswith('V') and clip['kind']=='audio':raise ValueError('音訊不能放在影片軌')
  clean['clips'].append(clip)
 for raw in project.get('titles',[]):
  title={key:number(raw.get(key,default),lo,hi,key) for key,default,lo,hi in [('start',0,0,864000),('end',5,.001,864000),('x',.1,0,1),('y',.1,0,1),('size',40,8,300)]}
  title['text']=str(raw.get('text',''))
  if len(title['text'])>2000 or title['end']<=title['start']:raise ValueError('標題長度或時間不正確')
  clean['titles'].append(title)
 clean['subtitles']=str(project.get('subtitles') or '')
 if check_sources and clean['subtitles'] and (not Path(clean['subtitles']).is_file() or Path(clean['subtitles']).suffix.lower()!='.srt'):raise ValueError('字幕必須為存在的 SRT 檔案')
 # Only explicitly declared dissolves allow same-track overlap.
 for track in {c['track'] for c in clean['clips']}:
  clips=sorted([c for c in clean['clips'] if c['track']==track],key=lambda c:c['at'])
  for before,after in zip(clips,clips[1:]):
   overlap=before['at']+(before['out']-before['in'])/before['speed']-after['at']
   if overlap>.002 and (not track.startswith('V') or abs(overlap-after['transition'])>.02 or overlap>min((before['out']-before['in'])/before['speed'],(after['out']-after['in'])/after['speed'])/2):raise ValueError('同軌片段重疊；請移動片段或設定相符的交叉溶解長度')
 return clean

def length(project):return max([c['at']+(c['out']-c['in'])/c['speed'] for c in project['clips']]+[t['end'] for t in project.get('titles',[])]+[0])
def tempo(speed):
 factors=[]
 while speed>2:factors.append(2);speed/=2
 while speed<.5:factors.append(.5);speed/=.5
 return ','.join('atempo='+str(x) for x in [*factors,speed])

def render(job,stage,engines):
 from worker import probe,emit
 from media_engine import convert_media
 project=validate(job['project'],engines);duration=length(project)
 if duration<=0:raise ValueError('時間軸沒有內容')
 preview=bool(job.get('previewOnly'));width=640 if preview else project['width'];height=max(2,round(width*project['height']/project['width']/2)*2);fps=min(24,project['fps']) if preview else project['fps']
 args=[engines['ffmpeg'],'-hide_banner','-nostdin','-n','-f','lavfi','-i',f'color=c=black:s={width}x{height}:r={fps}:d={duration}'];graph=[];audio=[];base='0:v';metadata={}
 clips=sorted(project['clips'],key=lambda c:(0 if c['track']=='V1' else 1 if c['track'].startswith('V') else 2,c['at']))
 for i,c in enumerate(clips,1):
  d=(c['out']-c['in'])/c['speed'];path=Path(c['source'])
  if c['kind']=='image':args+=['-loop','1','-t',str(c['out']-c['in']),'-i',path]
  else:args+=['-ss',str(c['in']),'-t',str(c['out']-c['in']),'-i',path]
  if c['track'].startswith('V'):
   pip=c['track']!='V1';w=max(2,round(width*(c['size'] if pip else 1)/2)*2);h=max(2,round(height*(c['size'] if pip else 1)/2)*2)
   filters=f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=rgba,setpts=(PTS-STARTPTS)/{c["speed"]}'
   fade=max(c['fadeIn'],c['transition'])
   if fade:filters+=f',fade=t=in:st=0:d={fade}:alpha=1'
   if c['fadeOut']:filters+=f',fade=t=out:st={d-c["fadeOut"]}:d={c["fadeOut"]}:alpha=1'
   filters+=f',setpts=PTS+{c["at"]}/TB'
   graph.append(f'[{i}:v:0]{filters}[v{i}]');x=round(c['x']*width) if pip else 0;y=round(c['y']*height) if pip else 0
   graph.append(f'[{base}][v{i}]overlay=x={x}:y={y}:eof_action=pass:enable=\'between(t,{c["at"]},{c["at"]+d})\'[b{i}]');base=f'b{i}'
  if c['source'] not in metadata and c['kind']!='image':metadata[c['source']]=probe(path,engines['ffprobe'])
  has_audio=any(s.get('codec_type')=='audio' for s in metadata.get(c['source'],{}).get('streams',[]))
  if has_audio and not c['mute']:
   filters=f'asetpts=PTS-STARTPTS,{tempo(c["speed"])},aresample=48000,aformat=channel_layouts=stereo,volume={c["volume"]}'
   fade=max(c['fadeIn'],c['transition'])
   if fade:filters+=f',afade=t=in:d={fade}'
   if c['fadeOut']:filters+=f',afade=t=out:st={d-c["fadeOut"]}:d={c["fadeOut"]}'
   filters+=f',adelay={round(c["at"]*1000)}:all=1';graph.append(f'[{i}:a:0]{filters}[a{i}]');audio.append(f'[a{i}]')
 if project['titles']:
  if not engines.get('font'):raise ValueError('本機標題字型缺失')
  shutil.copy2(engines['font'],stage/'font.otf')
 for i,t in enumerate(project['titles']):
  (stage/f'title-{i}.txt').write_text(t['text'],encoding='utf-8');out=f'title{i}';size=t['size']*width/project['width']
  graph.append(f'[{base}]drawtext=fontfile=font.otf:textfile=title-{i}.txt:expansion=none:fontcolor=white:fontsize={size}:x={round(t["x"]*width)}:y={round(t["y"]*height)}:enable=\'between(t,{t["start"]},{t["end"]})\'[{out}]');base=out
 if project['subtitles']:
  shutil.copy2(project['subtitles'],stage/'captions.srt');graph.append(f'[{base}]subtitles=filename=captions.srt[subtitled]');base='subtitled'
 graph.append(f'[{base}]format=yuv420p[vout]')
 if audio:graph.append(''.join(audio)+f'amix=inputs={len(audio)}:duration=longest:normalize=0,alimiter=limit=.95,apad,atrim=duration={duration}[aout]')
 else:graph.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={duration}[aout]')
 master_dir=stage if preview else stage/'render';master_dir.mkdir(exist_ok=True)
 master=master_dir/('preview.mp4' if preview else 'timeline-master.mkv')
 args+=['-filter_complex_threads','1','-filter_complex',';'.join(graph),'-map','[vout]','-map','[aout]','-t',str(duration),'-c:v','libx264','-preset','ultrafast','-crf','25' if preview else '0','-c:a','aac' if preview else 'pcm_s16le','-progress','pipe:1','-nostats',master]
 if preview:args[-1:-1]=['-movflags','+faststart']
 emit(stats={'phase':'預覽合成' if preview else '時間軸合成'})
 with tempfile.TemporaryFile() as errors:
  proc=subprocess.Popen([str(a) for a in args],stdout=subprocess.PIPE,stderr=errors,cwd=stage,creationflags=FLAGS)
  try:
   for line in proc.stdout:
    key,_,value=line.decode('utf-8','replace').strip().partition('=')
    if key=='out_time_us':
     try:emit(min(99,float(value)/1e6/duration*100))
     except ValueError:pass
   if proc.wait():errors.seek(0);raise ValueError(errors.read().decode('utf-8','replace')[-4000:])
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
   proc.stdout.close()
 if preview:return [master]
 emit(stats={'phase':'輸出編碼'})
 return convert_media(dict(job,format=job.get('format','mp4'),options=project['export']),[master],stage,engines)
