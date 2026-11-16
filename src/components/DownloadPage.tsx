import {useState} from 'react';
import {Download,FolderOpen,LoaderCircle,Search} from 'lucide-react';
import {call,pickFolder} from '../api';
import type {Job} from '../types';
import {Button} from './ui';
interface SourceFormat {format_id:string;ext?:string;height?:number;width?:number;fps?:number;acodec?:string;vcodec?:string;format_note?:string;}
interface DownloadEntry {key:string;id:string;title:string;url:string;duration?:number;formats:SourceFormat[];subtitles:string[];automaticSubtitles?:string[];resolved:boolean;}
interface Analysis {analysisId:string;url:string;title:string;thumbnail:string|null;duration?:number;playlist:boolean;entries:DownloadEntry[];page:number;hasMore:boolean;}
const duration=(value?:number)=>value?`${Math.floor(value/60)}:${String(Math.floor(value%60)).padStart(2,'0')}`:'長度未知';
export function DownloadPage({disabled,outputDir,onDirectory,notify}:{disabled:boolean;outputDir:string;onDirectory:(path:string)=>void;notify:(text:string,error?:boolean)=>void}) {
 const [url,setUrl]=useState('');const [analysis,setAnalysis]=useState<Analysis|null>(null);const [busy,setBusy]=useState(false);const [resolving,setResolving]=useState('');
 const [selected,setSelected]=useState<Set<string>>(new Set());const [formats,setFormats]=useState<Record<string,string>>({});const [subtitles,setSubtitles]=useState<Record<string,string[]>>({});
 const [audioOnly,setAudioOnly]=useState(false);const [audioFormat,setAudioFormat]=useState('mp3');const [convertTo,setConvertTo]=useState('');const [error,setError]=useState('');
 const analyze=async(page=1)=>{setBusy(true);setError('');try{
  const result=await call<Analysis>('analyze_url',{url,page});setAnalysis(result);setSelected(new Set(result.entries.length===1?[result.entries[0].key]:[]));setFormats({});setSubtitles({});
 }catch(e){setError(String(e))}finally{setBusy(false)}};
 const resolve=async(key:string)=>{if(!analysis)return;setResolving(key);setError('');try{const entry=await call<DownloadEntry>('resolve_download',{analysisId:analysis.analysisId,key});setAnalysis(old=>old?{...old,entries:old.entries.map(e=>e.key===key?entry:e)}:old)}catch(e){setError(String(e))}finally{setResolving('')}};
 const start=async()=>{if(!analysis)return;setBusy(true);setError('');try{
  const jobs=await call<Job[]>('enqueue_download',{analysisId:analysis.analysisId,outputDir,items:analysis.entries.filter(e=>selected.has(e.key)).map(e=>({key:e.key,formatId:formats[e.key]||'best',subtitles:subtitles[e.key]||[],audioOnly,audioFormat,convertTo}))});
  notify(`已將 ${jobs.length} 個下載加入佇列，可於歷史紀錄查看進度、取消或重試`);
 }catch(e){setError(String(e))}finally{setBusy(false)}};
 return <div className="download-page">
  <form className="download-source glass" data-material="card" onSubmit={e=>{e.preventDefault();void analyze()}}><label className="field"><span>影片或播放清單網址</span><input aria-label="影片網址" type="url" autoComplete="off" placeholder="https://…" value={url} onChange={e=>setUrl(e.target.value)} required/></label><Button type="submit" variant="primary" disabled={disabled||busy||!url.trim()}>{busy?<LoaderCircle size={18} className="spin"/>:<Search size={18}/>}解析網址</Button></form>
  <p className="hint">只有網址下載需要網路。預設不讀取瀏覽器 Cookie；不提供 DRM 或網站存取限制繞過。</p>
  {error&&<p className="error-text" role="alert">{error}</p>}
  {analysis&&<>
   <div className="download-summary glass" data-material="card">{analysis.thumbnail&&<img src={analysis.thumbnail} alt="來源縮圖"/>}<div><h2>{analysis.title}</h2><p>{duration(analysis.duration)} · {analysis.entries.length} 個{analysis.playlist?'播放清單項目':'來源'}</p></div></div>
   <div className="row between"><span>已選 {selected.size} / {analysis.entries.length}</span><div className="row"><Button compact onClick={()=>setSelected(new Set(analysis.entries.map(e=>e.key)))}>全選</Button><Button compact onClick={()=>setSelected(new Set())}>清除選取</Button></div></div>
   <div className="download-entries glass" data-material="card">{analysis.entries.map(entry=><section className="download-entry" key={entry.key}>
    <label className="download-entry-title"><input type="checkbox" checked={selected.has(entry.key)} onChange={e=>setSelected(old=>{const next=new Set(old);if(e.target.checked)next.add(entry.key);else next.delete(entry.key);return next})}/><strong>{entry.title}</strong><span>{duration(entry.duration)}</span></label>
    <div className="download-entry-options">
     {!entry.resolved?<Button compact disabled={busy||!!resolving} onClick={()=>resolve(entry.key)}>{resolving===entry.key?<LoaderCircle size={17} className="spin"/>:<Search size={17}/>}取得實際格式</Button>:<label className="field"><span>來源畫質與格式</span><select aria-label={`${entry.title} 下載格式`} disabled={audioOnly} value={formats[entry.key]||'best'} onChange={e=>setFormats(old=>({...old,[entry.key]:e.target.value}))}><option value="best">最佳可用（依來源決定）</option>{entry.formats.filter(f=>f.vcodec!=='none').map(f=><option key={f.format_id} value={f.format_id}>{f.height?`${f.height}p`:'原始畫質'} · {f.ext?.toUpperCase()||'來源格式'}{f.fps?` · ${f.fps} FPS`:''} · {f.format_id}{f.acodec==='none'?' · 視訊軌':''}</option>)}</select></label>}
     {!!entry.subtitles.length&&<fieldset className="subtitle-choices"><legend>字幕語言</legend>{entry.subtitles.map(language=><label key={language}><input type="checkbox" checked={(subtitles[entry.key]||[]).includes(language)} onChange={e=>setSubtitles(old=>({...old,[entry.key]:e.target.checked?[...(old[entry.key]||[]),language]:(old[entry.key]||[]).filter(l=>l!==language)}))}/>{language}{entry.automaticSubtitles?.includes(language)?' · 自動':''}</label>)}</fieldset>}
    </div>
   </section>)}</div>
   {analysis.playlist&&<div className="row between"><Button compact disabled={analysis.page<=1||busy} onClick={()=>analyze(analysis.page-1)}>上一頁</Button><span>第 {analysis.page} 頁 · 每頁最多 50 項</span><Button compact disabled={!analysis.hasMore||busy} onClick={()=>analyze(analysis.page+1)}>下一頁</Button></div>}
   <div className="download-settings glass" data-material="settings"><label className="tool-checkbox"><span>僅下載音訊</span><input type="checkbox" checked={audioOnly} onChange={e=>setAudioOnly(e.target.checked)}/></label>{audioOnly?<label className="field"><span>音訊後處理</span><select value={audioFormat} onChange={e=>setAudioFormat(e.target.value)}>{['mp3','m4a','flac','wav'].map(f=><option value={f} key={f}>{f.toUpperCase()}</option>)}</select></label>:<label className="field"><span>下載後自動轉檔</span><select value={convertTo} onChange={e=>setConvertTo(e.target.value)}><option value="">保留下載格式</option>{['mp4','mkv','webm'].map(f=><option value={f} key={f}>{f.toUpperCase()}</option>)}</select></label>}</div>
   <div className="conversion-toolbar glass" data-material="toolbar"><div className="output-path"><span>下載資料夾</span><button onClick={async()=>{try{const path=await pickFolder();if(path)onDirectory(path)}catch(e){setError(String(e))}}}><FolderOpen size={18}/><span>{outputDir||'應用程式資料 / Downloads'}</span></button></div><Button variant="primary" disabled={disabled||busy||!selected.size} onClick={start}><Download size={18}/>下載選取項目 {selected.size}</Button></div>
  </>}
 </div>;
}

