// Real Python service behind a localhost test transport; only native pickers are supplied.
import {spawn} from 'node:child_process';import {createInterface} from 'node:readline';import http from 'node:http';import path from 'node:path';import fs from 'node:fs/promises';
export async function bridge(){
 const root=process.cwd(),data=path.join(root,'.tools/editor-ui');await fs.mkdir(data,{recursive:true});
 const service=spawn(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8','engine/service.py','--data',path.join(data,'data-'+Date.now()),'--engines',path.join(root,'vendor')],{cwd:root,stdio:['pipe','pipe','pipe']});let serial=0;const pending=new Map();let stderr='';service.stderr.on('data',d=>stderr+=d.toString());
 createInterface({input:service.stdout}).on('line',line=>{try{const m=JSON.parse(line);const p=pending.get(m.id);if(p){pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(new Error(m.error)):p.resolve(m.result)}}catch{}});
 const rpc=(method,args={})=>new Promise((resolve,reject)=>{const id=++serial;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Editor test IPC timeout '+method+stderr.slice(-1000)))},120000);pending.set(id,{resolve,reject,timer});service.stdin.write(JSON.stringify({id,method,args})+'\n')});
 const server=http.createServer(async(req,res)=>{res.setHeader('Access-Control-Allow-Origin','http://127.0.0.1:1420');res.setHeader('Access-Control-Allow-Headers','Content-Type');if(req.method==='OPTIONS'){res.end();return}try{let body='';for await(const chunk of req)body+=chunk;const data=JSON.parse(body);const result=await rpc(data.method,data.args);res.setHeader('Content-Type','application/json');res.end(JSON.stringify({result}))}catch(e){res.end(JSON.stringify({error:String(e)}))}});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 return {root,data,rpc,port:server.address().port,async close(){server.closeAllConnections();await new Promise(r=>server.close(r));service.stdin.end();await new Promise(r=>{if(service.exitCode!==null)r();else service.once('exit',r)});for(const p of pending.values())clearTimeout(p.timer)}};
}
export async function installBridge(page,port){await page.addInitScript(({port})=>{window.isTauri=true;window.__picks=[];window.__TAURI_INTERNALS__={convertFileSrc:path=>'http://127.0.0.1:1420/@fs/'+path.replaceAll('\\','/'),invoke:async(command,args)=>{if(command==='engine_call'){const response=await fetch('http://127.0.0.1:'+port,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(args)});const data=await response.json();if(data.error)throw new Error(data.error);return data.result}if(command==='plugin:dialog|open'||command==='plugin:dialog|save')return window.__picks.shift()??null;throw new Error('Unexpected native command '+command)}}},{port})}

export async function installAppBridge(page,port){
 await installBridge(page,port);
 await page.addInitScript(({port})=>{
  const internals=window.__TAURI_INTERNALS__;const callbacks=new Map(),listeners=new Map();let serial=0;const previous=internals.invoke;
  internals.metadata={currentWindow:{label:'main'},currentWebview:{label:'main'}};
  internals.transformCallback=fn=>{const id=++serial;callbacks.set(id,fn);return id};internals.unregisterCallback=id=>callbacks.delete(id);
  window.__TAURI_EVENT_PLUGIN_INTERNALS__={unregisterListener:()=>{}};
  internals.invoke=async(command,args)=>{if(command==='plugin:event|listen'){listeners.set(args.handler,{event:args.event,fn:callbacks.get(args.handler)});return args.handler}if(command==='plugin:event|unlisten'){listeners.delete(args.eventId);return}if(command==='take_open_requests')return [];if(command==='native_material')return false;return previous(command,args)};
  const seen=new Map();setInterval(async()=>{try{const response=await fetch('http://127.0.0.1:'+port,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({method:'snapshot',args:{}})});const data=await response.json();for(const job of data.result.jobs){const value=JSON.stringify(job);if(seen.get(job.id)===value)continue;seen.set(job.id,value);for(const [id,l] of listeners)if(l.event==='engine-job')l.fn({event:'engine-job',id,payload:job})}}catch{}},400);
  window.__testDrop=paths=>{for(const [id,l] of listeners)if(l.event==='tauri://drag-drop')l.fn({event:l.event,id,payload:{paths,position:{x:400,y:300}}})};
 },{port});
}
