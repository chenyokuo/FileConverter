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

def publish_file(source,out):
    """Atomic no-clobber publication; tolerate short Windows indexing/AV locks."""
    target=out/source.name;index=1;attempts=0
    while True:
        try:
            if os.name=='nt':os.rename(source,target)  # Windows rename never replaces an existing target
            else:os.link(source,target);source.unlink()
            return target
        except (FileExistsError,IsADirectoryError):
            target=out/f'{source.stem} ({index}){source.suffix}';index+=1;attempts=0
        except PermissionError:
            if target.exists():
                target=out/f'{source.stem} ({index}){source.suffix}';index+=1;attempts=0
            elif attempts<6:
                time.sleep(.025*2**attempts);attempts+=1
            else:raise

def prevent_orphans(process_handle=None):
    """Windows job kills all descendants if service dies or desktop closes."""
    if os.name != 'nt': return
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [('ProcessTime',ctypes.c_int64),('JobTime',ctypes.c_int64),('LimitFlags',w.DWORD),('Min',ctypes.c_size_t),('Max',ctypes.c_size_t),('Active',w.DWORD),('Affinity',ctypes.c_size_t),('Priority',w.DWORD),('Scheduling',w.DWORD)]
    class Io(ctypes.Structure):
        _fields_ = [(n,ctypes.c_uint64) for n in ['ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes']]
    class Limits(ctypes.Structure):
        _fields_ = [('Basic',Basic),('Io',Io),('ProcessMemory',ctypes.c_size_t),('JobMemory',ctypes.c_size_t),('PeakProcess',ctypes.c_size_t),('PeakJob',ctypes.c_size_t)]
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateJobObjectW.restype=w.HANDLE
    k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
    k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
    k.GetCurrentProcess.restype=w.HANDLE
    handle=k.CreateJobObjectW(None,None)
    limits=Limits();limits.Basic.LimitFlags=0x2000
    if not handle or not k.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not k.AssignProcessToJobObject(handle,process_handle or k.GetCurrentProcess()):
        raise RuntimeError('Windows Job Object 初始化失敗，無法保證程序清理')
    return handle  # intentionally held for lifetime of service

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
        self.processes={};self.process_jobs={};self.stages={};self.reserved=set();self.engines=self.detect_engines()
        for job in self.jobs.values():
            if job['status'] in {'running','queued','cancelling'}:
                job.update(status='cancelled',error='程式上次關閉，任務已安全中止',finished=time.time());self.save(job)
        threading.Thread(target=self.scheduler,daemon=True).start()

    def detect_engines(self):
        def find(name, extra=()):
            paths=[self.engine_root/'ffmpeg'/(name+'.exe'),self.engine_root/(name+'.exe'),*map(Path,extra)]
            return next((str(p) for p in paths if p.is_file()),shutil.which(name))
        return {'ffmpeg':find('ffmpeg'),'ffprobe':find('ffprobe'),'soffice':find('soffice',[
            os.path.join(os.environ.get('PROGRAMFILES','C:/Program Files'),'LibreOffice/program/soffice.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'),'LibreOffice/program/soffice.exe')])}

    def save(self,job):
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
            spec={'job':dict(job),'engines':self.engines,'stage':str(stage)}
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
                        if file.parent!=stage.resolve() or not file.is_file():raise RuntimeError('Invalid engine output')
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
            if stage:shutil.rmtree(stage,ignore_errors=True)
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
            result.append({'path':str(p),'name':p.name,'size':p.stat().st_size,'extension':ext,'category':kind,'formats':outputs(ext),'preview':preview,'dimensions':dimensions,'available':bool(ext) and (not required or bool(self.engines.get(required))), 'detection':detection, 'reason':detection['warning'] if not ext else ''})
        return result

    def call(self,method,args):
        with self.lock:
            if method=='snapshot':
                return {'jobs':list(self.jobs.values()),'settings':self.settings,'engines':self.engines,'dataDir':str(self.root),'registry':registry(self.engines)}
            if method=='inspect':return self.inspect(args['paths'],args.get('nativeHints'))
            if method=='registry':return registry(self.engines)
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
                if job['status']=='queued':job.update(status='cancelled',finished=time.time());self.save(job);self.event(job)
                elif job['status']=='running':
                    job['status']='cancelling';self.save(job);self.event(job)
                    proc=self.processes.get(job['id'])
                    threading.Thread(target=self.kill,args=(proc,),daemon=True).start()
                return dict(job)
            if method=='retry':
                job=self.jobs[args['id']]
                if job['status'] not in {'failed','cancelled','completed'}:raise ValueError('任務仍在執行')
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
    try:
        for line in sys.stdin:
            request={}
            try:
                request=json.loads(line);result=service.call(request['method'],request.get('args',{}))
                service.send({'id':request['id'],'result':result})
            except Exception as error:service.send({'id':request.get('id'),'error':str(error)})
    finally:service.close()

if __name__=='__main__':main()
