"""One actual public-site range smoke; failures are recorded, never bypass access controls."""
from pathlib import Path
import sys,json,time,contextlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate
from downloads import analyze,selected,execute
from worker import probe
result={'url':'https://www.youtube.com/watch?v=aqz-KE-bpKQ','purpose':'Big Buck Bunny public preview, 1.5-second section only','started':time.time(),'status':'not-run'}
root=ROOT/'.tools/youtube-live';root.mkdir(exist_ok=True);stage=root/'stage';stage.mkdir(exist_ok=True)
try:
 e=locate(ROOT/'vendor');info=analyze(result['url'],e);entry=info['entries'][0]
 result.update(title=entry['title'],duration=entry['duration'],formats=len(entry['formats']),previewAvailable=bool(entry.get('previewUrl')))
 choice=next((str(f['format_id']) for f in entry['formats'] if f.get('ext')=='mp4' and f.get('acodec') not in {None,'none'} and f.get('vcodec') not in {None,'none'} and (f.get('height') or 0)<=480),'best')
 result['chosenFormat']=choice
 item=selected(info['analysisId'],[{'key':entry['key'],'formatId':choice,'sections':[{'start':1,'end':2.5}],'precise':True,'convertTo':'mp4'}])[0]
 files=execute({'download':item,'downloadCache':str(root/'cache'),'options':{'hardware':'cpu'}},stage,e)
 metadata=probe(files[0],e['ffprobe']);duration=float(metadata['format']['duration']);assert abs(duration-1.5)<.2
 result.update(status='passed',outputDuration=duration)
except Exception as error:result.update(status='restricted-or-failed',error=str(error)[-2000:])
finally:
 result['finished']=time.time();target=ROOT/'test-results/youtube-live.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(result,ensure_ascii=False))
