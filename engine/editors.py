"""Narrow editor API: media inspection, validated project IO and queued renders."""
import base64,json,os,tempfile,time,uuid
from pathlib import Path
from runtime import command

def inspect(path,engines):
 from worker import probe
 from PIL import Image,ImageOps
 from previews import data_image
 path=Path(path).resolve()
 if not path.is_file():raise ValueError('素材不存在')
 result={'path':str(path),'name':path.name,'duration':5,'kind':'image','poster':None,'waveform':None}
 try:
  with Image.open(path) as im:result.update(width=im.width,height=im.height,poster=data_image(im))
  return result
 except (OSError,ValueError):pass
 info=probe(path,engines['ffprobe']);streams=info['streams'];video=next((s for s in streams if s.get('codec_type')=='video'),None);audio=any(s.get('codec_type')=='audio' for s in streams)
 result.update(duration=float(info.get('format',{}).get('duration') or 0),kind='video' if video else 'audio',hasAudio=audio,width=video.get('width') if video else None,height=video.get('height') if video else None)
 if result['duration']<=0:raise ValueError('素材長度未知，無法建立編輯時間軸')
 if video:
  png=command([engines['ffmpeg'],'-v','error','-i',path,'-frames:v','1','-vf','scale=640:-2','-f','image2pipe','-vcodec','png','-'],timeout=45);result['poster']='data:image/png;base64,'+base64.b64encode(png).decode()
 if audio:
  png=command([engines['ffmpeg'],'-v','error','-i',path,'-filter_complex','aformat=channel_layouts=mono,showwavespic=s=1200x64:colors=white','-frames:v','1','-f','image2pipe','-vcodec','png','-'],timeout=90);result['waveform']='data:image/png;base64,'+base64.b64encode(png).decode()
 return result

def project_io(args,engines):
 raw=Path(args['path']);kind=args.get('type','fcvideo');suffix='.'+kind+'.json'
 if kind not in {'fcvideo','fcimage'} or not raw.name.lower().endswith(suffix):raise ValueError('請使用 '+suffix+' 專案副檔名')
 if raw.is_symlink():raise ValueError('專案檔不可為符號連結')
 path=raw.resolve()
 if args['action']=='load':
  if path.stat().st_size>10*1024*1024:raise ValueError('專案描述超過 10 MiB')
  data=json.loads(path.read_text('utf-8'))
 else:data=args['project']
 if kind=='fcvideo':
  from video_editor import validate
  data=validate(data,engines,check_sources=False);paths=[c['source'] for c in data['clips']]
 else:
  from image_editor import validate
  data=validate(data,check_sources=False);paths=[l['source'] for l in data['layers'] if l.get('source')]
 if args['action']=='load':return {'project':data,'missing':sorted(set(p for p in paths if not Path(p).is_file()))}
 if str(path) in paths:raise ValueError('不能覆寫素材')
 if path.exists():
  old=json.loads(path.read_text('utf-8'))
  if old.get('type')!=kind or old.get('version')!=1:raise ValueError('不能覆寫其他檔案')
 path.parent.mkdir(parents=True,exist_ok=True);temp=None
 try:
  with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as file:temp=Path(file.name);json.dump(data,file,ensure_ascii=False,indent=2)
  os.replace(temp,path)
 finally:
  if temp and temp.exists():temp.unlink()
 return {'path':str(path),'project':data}

def enqueue(service,args):
 kind=args.get('type','fcvideo');project=args['project']
 if kind=='fcvideo':
  from video_editor import validate
  project=validate(project,service.engines);sources=list(dict.fromkeys(c['source'] for c in project['clips']));formats={'mp4','mkv','mov','webm','wav','mp3','flac'}
 elif kind=='fcimage':
  from image_editor import validate
  project=validate(project);sources=list(dict.fromkeys(l['source'] for l in project['layers'] if l.get('source')));formats={'png','jpg','webp'}
 else:raise ValueError('未知編輯器')
 fmt=args.get('format','mp4' if kind=='fcvideo' else 'png')
 if fmt not in formats:raise ValueError('不支援的輸出格式')
 id=uuid.uuid4().hex;preview=bool(args.get('preview'))
 out=service.root/'previews'/id if preview else Path(args.get('outputDir') or service.root/'Editor Output').resolve()
 job={'id':id,'kind':kind,'name':'影片編輯輸出' if kind=='fcvideo' else '圖片編輯輸出','sources':sources,'project':project,'previewOnly':preview,'format':fmt,'outputDir':str(out),'category':'video' if kind=='fcvideo' else 'image','options':{},'status':'queued','progress':0,'created':time.time(),'outputs':[],'error':None}
 with service.lock:service.jobs[id]=job;service.save(job);service.event(job)
 return dict(job)

def dispatch(service,args):
 action=args['action']
 if action=='inspect':return inspect(args['path'],service.engines)
 if action in {'save','load'}:return project_io(args,service.engines)
 if action=='enqueue':return enqueue(service,args)
 raise ValueError('未知編輯器動作')
