"""Local JSONL service. Owns a persistent, bounded, cancellable subprocess queue."""
import base64
import ctypes
import json
import mimetypes
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from registry import category, outputs, registry, validate, ConversionGraph
from detection import detect, normalize
from worker import CREATE_NO_WINDOW, run_worker

from fsutils import publish_file

from windows_jobs import prevent_orphans

class Service:
    def __init__(self, data_dir, engine_root=None):
        self.root=Path(data_dir).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.engine_root=Path(engine_root) if engine_root else Path(__file__).resolve().parents[1]/'vendor'
        self.lock=threading.RLock();self.write_lock=threading.Lock();self.stop=threading.Event()
        self.db=sqlite3.connect(self.root/'history.sqlite3',check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
        self.jobs={r[0]:json.loads(r[1]) for r in self.db.execute('SELECT id,payload FROM jobs')}
        row=self.db.execute('SELECT payload FROM settings WHERE id=1').fetchone();self.settings=json.loads(row[0]) if row else {}
        self.secrets={};self.processes={};self.process_jobs={};self.stages={};self.reserved=set();self.engines=self.detect_engines()
        for job in self.jobs.values():
            if job['status'] in {'running','queued','cancelling'}:
                job.update(status='cancelled',error='程式上次關閉，任務已安全中止',finished=time.time());self.save(job)
        self.hardware_cache=[{'id':'cpu','label':'CPU','available':True,'encoder':'libx264','codecs':{'h264':True,'h265':True},'reason':''}]+[
            {'id':key,'label':label,'available':False,'encoder':'','reason':'偵測中','pending':True} for key,label in [('nvidia','NVIDIA'),('amd','AMD'),('intel','Intel')]]
        self.hardware_detecting=False
        self.refresh_hardware()
        threading.Thread(target=self.scheduler,daemon=True).start()

    def detect_engines(self):
        from runtime import locate
        return locate(self.engine_root)

    def refresh_hardware(self):
        if self.hardware_detecting:return
        self.hardware_detecting=True
        self.hardware_cache=[dict(row,available=False,pending=True,reason='偵測中') if row['id']!='cpu' else row for row in self.hardware_cache]
        def run():
            from runtime import hardware
            try:
                result=hardware(self.engines.get('ffmpeg'),refresh=True)
                with self.lock:self.hardware_cache=result
            finally:self.hardware_detecting=False
        threading.Thread(target=run,daemon=True).start()

    def save(self,job):
        if job.get('previewOnly'):return
        self.db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?)',(job['id'],json.dumps(job,ensure_ascii=True)));self.db.commit()

    def send(self,data):
        with self.write_lock: print(json.dumps(data,ensure_ascii=True),flush=True)

    def event(self,job): self.send({'event':'job','data':dict(job)})

    def scheduler(self):
        while not self.stop.wait(0.12):
            with self.lock:
                limit=max(1,min(4,int(self.settings.get('concurrency',2))))
                available=limit-len(self.processes)
                for job in list(self.jobs.values()):
                    if available<=0:break
                    if job['status']!='queued':continue
                    job.update(status='running',started=time.time(),error=None,progress=0);self.save(job)
                    # Reserve slot before spawning the thread.
                    self.processes[job['id']]=None;available-=1;self.event(job)
                    threading.Thread(target=self.execute,args=(job,),daemon=True).start()

    def kill(self,proc):
        if proc and proc.poll() is None:
            if os.name=='nt':
                from ctypes import wintypes as w
                k=ctypes.WinDLL('kernel32',use_last_error=True)
                k.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]
                handle=self.process_jobs.get(proc.pid)
                if not handle or not k.TerminateJobObject(handle,1):proc.kill()
            else: proc.kill()
            proc.wait(timeout=15)

    def execute(self,job):
        stage=None
        try:
            out=Path(job['outputDir']);out.mkdir(parents=True,exist_ok=True)
            stage=Path(tempfile.mkdtemp(prefix='.rai-',dir=out));self.stages[job['id']]=stage
            worker_job=dict(job)
            if self.secrets.get(job['id']):worker_job['params']={**job.get('params',{}),**self.secrets[job['id']]}
            spec={'job':worker_job,'engines':self.engines,'stage':str(stage),'hardwareCapabilities':self.hardware_cache}
            command=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve())]
            with self.lock:
                if job['status']=='cancelling': raise InterruptedError()
                proc=subprocess.Popen(command+['--worker'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=CREATE_NO_WINDOW | (4 if os.name=='nt' else 0))
                if os.name=='nt':
                    try:
                        self.process_jobs[proc.pid]=prevent_orphans(int(proc._handle))
                        resume=ctypes.WinDLL('ntdll').NtResumeProcess
                        resume.argtypes=[ctypes.c_void_p]
                        if resume(int(proc._handle))!=0:raise RuntimeError('Could not resume worker')
                    except Exception:
                        proc.kill();proc.wait();raise
                self.processes[job['id']]=proc
            proc.stdin.write(json.dumps(spec,ensure_ascii=True).encode()+b'\n');proc.stdin.close()
            files=[];error=None
            # Drain stderr concurrently; dependencies can be noisy, never block the worker pipe.
            errors=[]
            def drain():
                for line in proc.stderr:
                    errors.append(line)
                    if len(errors)>100:errors.pop(0)
            drainer=threading.Thread(target=drain,daemon=True);drainer.start()
            for line in proc.stdout:
                try: message=json.loads(line)
                except ValueError:continue
                with self.lock:
                    if job['status']=='cancelling':continue
                    if 'stats' in message:job.setdefault('stats',{}).update(message['stats']);self.event(job)
                    if 'progress' in message: job['progress']=min(99,message['progress']);self.event(job)
                    if 'files' in message:files=message['files']
                    if 'error' in message:error=message['error']
            code=proc.wait()
            if os.name=='nt':
                from ctypes import wintypes as w
                k=ctypes.WinDLL('kernel32');k.CloseHandle.argtypes=[w.HANDLE]
                handle=self.process_jobs.pop(proc.pid,None)
                if handle:k.CloseHandle(handle)
            drainer.join(timeout=2)
            with self.lock:
                if job['status']=='cancelling':raise InterruptedError()
                if code or error or not files:raise RuntimeError(error or b''.join(errors).decode('utf-8','replace')[-3000:] or '引擎未產生檔案')
                published=[]
                try:
                    for raw in files:
                        file=Path(raw).resolve()
                        if not file.is_relative_to(stage.resolve()) or not (file.is_file() or job.get('operation')=='archive.extract' and file.is_dir()):raise RuntimeError('Invalid engine output')
                        target=publish_file(file,out)
                        published.append(str(target))
                except Exception:
                    for file in published:Path(file).unlink(missing_ok=True)
                    raise
                job.update(status='completed',progress=100,outputs=published,finished=time.time());self.save(job);self.event(job)
        except Exception as error:
            with self.lock:
                job.update(status='cancelled' if isinstance(error,InterruptedError) or job['status']=='cancelling' else 'failed',error=None if isinstance(error,InterruptedError) else str(error),finished=time.time())
                self.save(job);self.event(job)
        finally:
            self.secrets.pop(job['id'],None)
            if stage:
                from fsutils import remove_tree
                try:remove_tree(stage,Path(job['outputDir']))
                except OSError as error:job.setdefault('stats',{})['cleanupWarning']=str(error);self.save(job)
            with self.lock:self.processes.pop(job['id'],None);self.stages.pop(job['id'],None)

    def inspect(self,paths,native_hints=None):
        result=[]
        for raw in paths:
            p=Path(raw).resolve()
            if not p.is_file():raise ValueError(f'檔案不存在：{p}')
            detection=detect(p,self.engines,(native_hints or {}).get(str(p)));ext=detection['format'];kind=category(ext);preview=None;dimensions=None
            if kind=='image':
                try:
                    from PIL import Image,ImageOps
                    import io
                    with Image.open(p) as image:
                        dimensions=[image.width,image.height];image=ImageOps.exif_transpose(image);image.thumbnail((180,180))
                        buf=io.BytesIO();image.convert('RGBA').save(buf,format='PNG');preview='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
                except Exception:pass
            required='soffice' if kind=='office' else 'ffmpeg' if kind in {'video','audio'} else None
            result.append({'path':str(p),'name':p.name,'size':p.stat().st_size,'extension':ext,'category':kind,'formats':outputs(ext),'preview':preview,'dimensions':dimensions,'available':bool(ext) and any(e['available'] for e in registry(self.engines)['edges'] if e['source']==ext), 'detection':detection, 'reason':detection['warning'] if not ext else ''})
        return result

    def create_tool(self,args):
        from tool_catalog import validate_tool
        sources=[str(Path(p).resolve()) for p in args['sources']]
        definition,params=validate_tool(args['operation'],args.get('params',{}),sources,self.engines)
        id=uuid.uuid4().hex;preview=bool(args.get('preview'))
        output=self.root/'previews'/id if preview else Path(args.get('outputDir') or Path(sources[0]).parent/'File Converter Output').resolve()
        secret={f['key']:params.pop(f['key']) for f in definition['fields'] if f.get('secret')}
        self.secrets[id]=secret
        job={'id':id,'sources':sources,'name':Path(sources[0]).name+' · '+definition['name'],'operation':definition['id'],
            'params':params,'requiresSecret':bool(secret),'previewOnly':preview,'category':category(detect(sources[0],self.engines)['format']) if Path(sources[0]).is_file() else 'archive',
            'format':params.get('format',detect(sources[0],self.engines)['format'] if definition['output']=='source' else definition['output']),'outputDir':str(output),'options':{**self.settings.get('defaults',{}),**args.get('options',{})},
            'status':'queued','progress':0,'created':time.time(),'outputs':[],'error':None}
        self.jobs[id]=job;self.save(job);self.event(job);return [dict(job)]

    def call(self,method,args):
        if method=='preview':
            from previews import preview
            return preview(args['path'],self.engines,args.get('page',0),args.get('time',0))
        with self.lock:
            if method=='snapshot':
                return {'jobs':[j for j in self.jobs.values() if not j.get('previewOnly')],'settings':self.settings,'engines':self.engines,'dataDir':str(self.root),'registry':registry(self.engines)}
            if method=='inspect':return self.inspect(args['paths'],args.get('nativeHints'))
            if method=='tools':
                from tool_catalog import catalog
                return catalog(self.engines)
            if method=='enqueue_tool':return self.create_tool(args)
            if method=='preview_status':return dict(self.jobs[args['id']])
            if method=='clear_preview':
                job=self.jobs.get(args['id'])
                if not job or not job.get('previewOnly'):raise ValueError('無效預覽任務')
                if job['status'] in {'queued','running','cancelling'}:raise ValueError('請先取消並等候預覽任務結束')
                from fsutils import remove_tree
                if Path(job['outputDir']).exists():remove_tree(job['outputDir'],self.root/'previews')
                self.jobs.pop(job['id'],None);self.secrets.pop(job['id'],None);return True
            if method=='registry':return registry(self.engines)
            if method=='hardware':
                if args.get('refresh'):self.refresh_hardware()
                return self.hardware_cache
            if method=='plan':
                route=ConversionGraph(registry(self.engines)['edges']).path(args['source'],args['target'])
                return {'route':route,'executable':len(route)==1,'intermediate':len(route)>1}
            if method=='engines':self.engines=self.detect_engines();return self.engines
            if method=='settings':
                settings=args['settings']
                if not isinstance(settings,dict):raise ValueError('Invalid settings')
                if not 1<=int(settings.get('concurrency',2))<=4:raise ValueError('Concurrency must be 1–4')
                self.settings=settings;self.db.execute('INSERT OR REPLACE INTO settings VALUES (1,?)',(json.dumps(settings),));self.db.commit();return settings
            if method=='background':
                from PIL import Image,ImageOps
                p=Path(args['path'])
                if p.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:raise ValueError('僅支援 JPG、PNG、WebP 背景')
                # Decode and re-encode: do not trust extension or retain external file references.
                with Image.open(p) as image:
                    import io
                    image=ImageOps.exif_transpose(image)
                    buf=io.BytesIO();image.convert('RGBA' if 'A' in image.getbands() else 'RGB').save(buf,format='WEBP',lossless=True)
                data=buf.getvalue();(self.root/'background.webp').write_bytes(data)
                return 'data:image/webp;base64,'+base64.b64encode(data).decode()
            if method=='enqueue':
                created=[]
                for item in args['jobs']:
                    sources=[str(Path(p).resolve()) for p in item['sources']]
                    if not sources or any(not Path(p).is_file() for p in sources):raise ValueError('無效來源檔案')
                    detected=detect(sources[0],self.engines)['format']
                    # Corrupt known inputs become isolated failed jobs, preserving the rest of a batch.
                    source_format=detected or normalize(Path(sources[0]).suffix)
                    validate(source_format,item['format'],self.engines,item.get('options'),len(sources))
                    out=Path(item.get('outputDir') or sources[0]).resolve()
                    if not item.get('outputDir'):out=out.parent/'File Converter Output'
                    job={'id':uuid.uuid4().hex,'sources':sources,'name':Path(sources[0]).name+(' + '+str(len(sources)-1) if len(sources)>1 else ''),'category':category(source_format),'sourceFormat':source_format,'format':item['format'],'outputDir':str(out),'options':item.get('options',{}),'status':'queued','progress':0,'created':time.time(),'outputs':[],'error':None}
                    self.jobs[job['id']]=job;self.save(job);self.event(job);created.append(job)
                return created
            if method=='cancel':
                job=self.jobs[args['id']]
                if job['status']=='queued':job.update(status='cancelled',finished=time.time());self.secrets.pop(job['id'],None);self.save(job);self.event(job)
                elif job['status']=='running':
                    job['status']='cancelling';self.save(job);self.event(job)
                    proc=self.processes.get(job['id'])
                    threading.Thread(target=self.kill,args=(proc,),daemon=True).start()
                return dict(job)
            if method=='retry':
                job=self.jobs[args['id']]
                if job['status'] not in {'failed','cancelled','completed'}:raise ValueError('任務仍在執行')
                if job.get('operation'):
                    if job.get('requiresSecret'):raise ValueError('請重新開啟工具輸入密碼，密碼不會保存在歷史')
                    return self.create_tool({k:job[k] for k in ['sources','operation','params','outputDir']})
                return self.call('enqueue',{'jobs':[{k:job[k] for k in ['sources','format','outputDir','options']}]})
            if method=='clear':
                active={'running','queued','cancelling'}
                ids=set(args['ids']) if 'ids' in args else None
                for key,job in list(self.jobs.items()):
                    if job['status'] not in active and (ids is None or key in ids):self.db.execute('DELETE FROM jobs WHERE id=?',(key,));del self.jobs[key]
                self.db.commit();return True
            if method=='open_output':
                job=self.jobs[args['id']];path=Path(job['outputDir'])
                if not path.is_dir():raise ValueError('輸出資料夾尚未建立')
                os.startfile(str(path));return True
            raise ValueError('不允許的命令')

    def close(self):
        self.stop.set()
        with self.lock:
            procs=list(self.processes.values())
            for job in self.jobs.values():
                if job['status'] in {'queued','running','cancelling'}:
                    job.update(status='cancelled',finished=time.time());self.save(job)
        for proc in procs:self.kill(proc)

def main():
    # Rust sends UTF-8 JSON; Windows' default console encoding may be CP950/1252.
    # This must also be explicit in the frozen sidecar (there is no console).
    for stream in (sys.stdin,sys.stdout,sys.stderr):
        if stream is not None:stream.reconfigure(encoding='utf-8',errors='strict')
    if '--worker' in sys.argv:
        spec=json.loads(sys.stdin.buffer.readline());sys.exit(run_worker(spec))
    job_handle=prevent_orphans()
    data=sys.argv[sys.argv.index('--data')+1] if '--data' in sys.argv else str(Path.home()/'.rai-converter')
    engines=sys.argv[sys.argv.index('--engines')+1] if '--engines' in sys.argv else None
    service=Service(data,engines)
    from concurrent.futures import ThreadPoolExecutor
    preview_pool=ThreadPoolExecutor(max_workers=2)
    try:
        for line in sys.stdin:
            request={}
            try:
                request=json.loads(line)
                def handle(req):
                    try:service.send({'id':req['id'],'result':service.call(req['method'],req.get('args',{}))})
                    except Exception as error:service.send({'id':req['id'],'error':str(error)})
                if request['method']=='preview':preview_pool.submit(handle,dict(request))
                else:handle(request)
            except Exception as error:service.send({'id':request.get('id'),'error':str(error)})
    finally:service.close();preview_pool.shutdown(wait=False,cancel_futures=True)

if __name__=='__main__':main()
