"""Persisted presets/workflows and explicitly enabled folder watches."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid
from workflows import plan

def writable_finished(path):
    if os.name!='nt':return True
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE];kernel.CreateFileW.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.CreateFileW(str(path),0x80000000,0,None,3,0x80,None)
    if handle==w.HANDLE(-1).value:return False
    kernel.CloseHandle(handle);return True

class Automation:
    def __init__(self,service):
        self.service=service;self.db=service.db;self.db.execute('CREATE TABLE IF NOT EXISTS automation (id TEXT PRIMARY KEY, kind TEXT, payload TEXT)')
        self.items={r[0]:dict(json.loads(r[2]),kind=r[1]) for r in self.db.execute('SELECT id,kind,payload FROM automation')}
        self.states={};self.logs=[]
        # Explicit start per application session. Never silently resume directory access after restart.
        threading.Thread(target=self.monitor,daemon=True).start()

    def save(self,item):
        self.items[item['id']]=item;self.db.execute('INSERT OR REPLACE INTO automation VALUES (?,?,?)',(item['id'],item['kind'],json.dumps(item)));self.db.commit();return dict(item)

    def record(self,id,message,**extra):
        self.logs.append(dict(watchId=id,time=time.time(),message=message,**extra));self.logs=self.logs[-200:]

    def snapshot(self):
        return {'items':list(self.items.values()),'states':{key:state['status'] for key,state in self.states.items()},'logs':self.logs,'tools':__import__('workflows').workflow_tools(self.service.engines)}

    def put(self,args):
        kind=args.get('kind');id=args.get('id') or uuid.uuid4().hex
        if kind not in {'preset','workflow','watch'}:raise ValueError('無效自動化類型')
        existing=self.items.get(id)
        if existing and existing['kind']!=kind:raise ValueError('不可變更配置類型')
        config=plan(args['config'],self.service.engines)
        if kind=='preset' and (len(config['steps'])!=1 or config['steps'][0]['type']!='convert'):raise ValueError('轉檔預設需為單一步驟轉換')
        item={'id':id,'kind':kind,'name':config['name'],'config':config}
        if kind=='watch':
            source=Path(args.get('sourceDir','')).resolve();out=Path(args.get('outputDir','')).resolve()
            if not args.get('sourceDir') or not args.get('outputDir') or not source.is_dir():raise ValueError('請明確選擇來源及輸出資料夾')
            if out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('監看來源與輸出不可相同、包含或互相重疊')
            item.update(sourceDir=str(source),outputDir=str(out))
            if id in self.states:self.states[id]['status']='stopped'
        return self.save(item)

    def delete(self,id):
        self.states.pop(id,None);self.items.pop(id,None);self.db.execute('DELETE FROM automation WHERE id=?',(id,));self.db.commit();return True

    def watch_action(self,id,action):
        item=self.items[id]
        if item['kind']!='watch':raise ValueError('不是監看配置')
        if action not in {'start','pause','stop'}:raise ValueError('無效監看動作')
        state=self.states.get(id)
        if action=='start':
            plan(item['config'],self.service.engines)
            if not Path(item['sourceDir']).is_dir():raise ValueError('來源資料夾不存在')
            if not state or state['status']=='stopped':
                state={'status':'running','seen':{},'pending':{},'digests':{}};self.states[id]=state
                for p in Path(item['sourceDir']).iterdir():
                    if p.is_file():state['seen'][str(p)]=(p.stat().st_size,p.stat().st_mtime_ns)
            else:state['status']='running'
        elif state:state['status']='paused' if action=='pause' else 'stopped'
        self.record(id,{'start':'開始監看；既有檔案略過','pause':'已暫停','stop':'已停止'}[action]);return True

    def enqueue(self,config,paths,output):
        from detection import detect
        from registry import category
        config=plan(config,self.service.engines);created=[]
        for raw in paths:
            path=Path(raw).resolve()
            if not path.is_file() or detect(path,self.service.engines)['format']!=config['source']:raise ValueError('流程來源不符合檔案實際格式：'+path.name)
        for raw in paths:
            path=Path(raw).resolve();id=uuid.uuid4().hex
            job={'id':id,'kind':'workflow','workflow':config,'sources':[str(path)],'name':path.name+' · '+config['name'],
                'category':category(config['source']),'format':config['target'],'options':self.service.settings.get('defaults',{}),
                'outputDir':str(Path(output).resolve()) if output else str(path.parent/'File Converter Output'),
                'status':'queued','progress':0,'created':time.time(),'outputs':[],'error':None}
            self.service.jobs[id]=job;self.service.save(job);self.service.event(job);created.append(dict(job))
        if not created:raise ValueError('請選擇來源檔案')
        return created

    def monitor(self):
        while not self.service.stop.wait(.4):
            with self.service.lock:active=[(dict(self.items[id]),state) for id,state in self.states.items() if state['status']=='running' and id in self.items]
            for item,state in active:
                try:self.scan(item,state)
                except Exception as error:
                    with self.service.lock:
                        state['status']='paused';self.record(item['id'],str(error),error=True)

    def scan(self,item,state):
        from detection import detect
        root=Path(item['sourceDir']);now=time.monotonic()
        # Non-recursive: authorization covers only the directory selected, no linked trees.
        present=set()
        for path in root.iterdir():
            if not path.is_file() or path.is_symlink() or path.name.startswith(('.', '~')) or path.suffix.lower() in {'.tmp','.part','.crdownload'}:continue
            name=str(path);present.add(name);stat=path.stat();fingerprint=(stat.st_size,stat.st_mtime_ns)
            if state['seen'].get(name)==fingerprint:continue
            candidate=state['pending'].get(name)
            if not candidate or candidate['fingerprint']!=fingerprint:
                state['pending'][name]={'fingerprint':fingerprint,'since':now};continue
            if now-candidate['since']<1.5 or not writable_finished(path):continue
            # Reading and enqueueing occur only after the signature stabilizes and writer closes.
            if detect(path,self.service.engines)['format']!=item['config']['source']:
                state['seen'][name]=fingerprint;state['pending'].pop(name,None);continue
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if (path.stat().st_size,path.stat().st_mtime_ns)!=fingerprint:continue
            with self.service.lock:
                if state['status']!='running' or self.states.get(item['id']) is not state:return
                if state['digests'].get(name)!=digest:
                    jobs=self.enqueue(item['config'],[name],item['outputDir']);self.record(item['id'],path.name+' 已加入佇列',jobId=jobs[0]['id'])
                state['digests'][name]=digest
                state['seen'][name]=fingerprint;state['pending'].pop(name,None)
        for name in list(state['pending']):
            if name not in present:state['pending'].pop(name,None)
