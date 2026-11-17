import {convertFileSrc} from "@tauri-apps/api/core";
import {call} from "../api";
import type {Job} from "../types";
import {release} from "./editor-hooks";
import { useEffect, useRef, useState } from "react";
import { Play, RotateCcw, Plus, X } from "lucide-react";
import { Button } from "./ui";
import { TimeRange, timecode, type TimeSpan } from "./TimeRange";
export interface RangeOptions {
  only: boolean;
  ranges: TimeSpan[];
  precise: boolean;
  merge: boolean;
}
export const defaultRanges = (): RangeOptions => ({
  only: false,
  ranges: [],
  precise: false,
  merge: false,
});
export function DownloadRange({
  analysisId, entryKey, sourceUrl,
  duration = 0,
  previewUrl,
  loading,
  value,
  onChange,
}: {
  analysisId?:string; entryKey?:string; sourceUrl?:string;
  duration?: number;
  previewUrl?: string;
  loading: boolean;
  value: RangeOptions;
  onChange: (v: RangeOptions) => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [current, setCurrent] = useState(0);
  const [buffering, setBuffering] = useState(true);
  const [failed, setFailed] = useState(false);
  const [failure,setFailure]=useState("");
  const [local,setLocal]=useState("");
  const [previewJob,setPreviewJob]=useState<Job|null>(null);
  const mounted=useRef(true);
  const jobRef=useRef<Job|null>(null);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;if(jobRef.current)void release(jobRef.current)}},[]);
  useEffect(()=>{if(!previewJob || !["running","queued","cancelling"].includes(previewJob.status))return;const timer=setInterval(()=>void call<Job>("preview_status",{id:previewJob.id}).then(job=>{setPreviewJob(job);jobRef.current=job;if(job.status==="completed"){setLocal(convertFileSrc(job.outputs[0]));setFailed(false);setBuffering(true)}if(job.status==="failed")setFailure(job.error || "本機預覽建立失敗")}).catch(e=>setFailure(String(e))),500);return()=>clearInterval(timer)},[previewJob?.id,previewJob?.status]);
  const preparing=!!previewJob && ["running","queued","cancelling"].includes(previewJob.status);
  useEffect(()=>{if(!buffering || !previewUrl && !local)return;const timer=setTimeout(()=>{setFailure("播放器載入逾時；可重試或建立本機預覽，下載控制仍可使用。");setFailed(true)},20000);return()=>clearTimeout(timer)},[buffering,previewUrl,local]);

  const [active, setActive] = useState(0);
  const known = Number.isFinite(duration) && duration > 0;
  const ranges = value.ranges.length
    ? value.ranges
    : [{ start: 0, end: known ? duration : 0 }];
  const index = Math.min(active, ranges.length - 1);
  const range = ranges[index];
  const seek = (n: number) => {
    setCurrent(n);
    if (video.current && Number.isFinite(video.current.duration))
      video.current.currentTime = n;
  };
  return (
    <div className="download-range glass" data-material="card">
      <div className="range-player">
        {(local || previewUrl) && !failed ? (
          <video
            ref={video}
            src={local || previewUrl}
            controls
            playsInline
            preload="metadata"
            onLoadedMetadata={e=>{e.currentTarget.currentTime=Math.min(current,e.currentTarget.duration)}}
            onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime)}
            onWaiting={() => setBuffering(true)}
            onCanPlay={() => setBuffering(false)}
            onError={(e) => {const error=e.currentTarget.error;setFailure(`HTML MediaError ${error?.code ?? 0}：${error?.message || "來源串流無法直接播放（可能是 URL、解碼或來源網路限制）"}`);setFailed(true)}}
          />
        ) : (
          <div className="range-player-empty">
            <Play size={38} />
            <span>{loading ? "正在載入影片資訊…" : "影片預覽區"}</span>
            {!loading && (
              <span className="hint">
                {failed
                  ? "來源串流無法直接播放；這不代表禁止嵌入。可建立本機預覽，仍可選段下載。"
                  : previewUrl
                    ? ""
                    : "此來源未提供可直接播放的影音串流。"}
              </span>
            )}
          </div>
        )}
        {(local || previewUrl) && !failed && buffering && (
          <span className="range-buffering" role="status">
            影片載入中…
          </span>
        )}
      </div>
      {failure && <p className="hint" role="status">{failure}</p>}
      {analysisId && entryKey && <div className="range-preview-actions row">
        <Button disabled={preparing || loading} onClick={async()=>{try{if(jobRef.current)await release(jobRef.current);setFailure("");const job=await call<Job>("download_preview",{analysisId,key:entryKey});if(!mounted.current){void release(job);return}jobRef.current=job;setPreviewJob(job)}catch(e){setFailure(String(e))}}}>建立本機預覽（下載低畫質完整影片）</Button>
        {preparing && <><span>建立中 {Math.floor(previewJob!.progress)}%</span><Button onClick={()=>call("cancel",{id:previewJob!.id})}>取消預覽</Button></>}
        {sourceUrl && <Button onClick={()=>call("open_source",{url:sourceUrl}).catch(e=>setFailure(String(e)))}>開啟原始影片</Button>}
        <Button onClick={()=>{setFailed(false);setFailure("");setBuffering(true);video.current?.load()}}>重試播放器</Button>
      </div>}
      {!known && !loading && (
        <p className="hint" role="status">
          影片長度未知或為直播，區間選取已停用；仍可下載完整來源。
        </p>
      )}
      <TimeRange
        duration={duration}
        range={range}
        current={current}
        disabled={loading}
        onSeek={seek}
        onChange={(next) =>
          onChange({
            ...value,
            ranges: ranges.map((r, i) => (i === index ? next : r)),
          })
        }
      />
      <div className="row between range-footer">
        <strong>選取時長：{timecode(range.end - range.start)}</strong>
        <label>
          <input
            type="checkbox"
            disabled={!known || loading}
            checked={value.only && known}
            onChange={(e) =>
              onChange({ ...value, only: e.target.checked, ranges })
            }
          />
          只輸出所選片段
        </label>
      </div>
      <div className="row range-actions">
        <Button
          compact
          disabled={!known || loading}
          onClick={() => {
            onChange({ ...value, ranges: [{ start: 0, end: duration }] });
            setActive(0);
          }}
        >
          <RotateCcw size={16} />
          重設區間
        </Button>
        <Button
          compact
          disabled={!known || loading}
          onClick={() => {
            onChange({
              ...value,
              only: true,
              ranges: [...ranges, { start: 0, end: duration }],
            });
            setActive(ranges.length);
          }}
        >
          <Plus size={16} />
          新增區間
        </Button>
        {ranges.map((r, i) => (
          <div className="row" key={i}>
            <Button
              compact
              disabled={!known || loading}
              aria-pressed={index === i}
              onClick={() => setActive(i)}
            >
              片段 {i + 1} · {timecode(r.end - r.start)}
            </Button>
            {ranges.length > 1 && (
              <Button
                compact
                aria-label={`移除片段 ${i + 1}`}
                onClick={() => {
                  onChange({
                    ...value,
                    ranges: ranges.filter((_, n) => n !== i),
                  });
                  setActive(0);
                }}
              >
                <X size={14} />
              </Button>
            )}
          </div>
        ))}
      </div>
      {value.only && (
        <div className="range-inputs">
          <label className="field">
            <span>裁切方式</span>
            <select
              value={value.precise ? "precise" : "fast"}
              onChange={(e) =>
                onChange({ ...value, precise: e.target.value === "precise" })
              }
            >
              <option value="fast">快速裁切（切點可能依關鍵影格偏移）</option>
              <option value="precise">精確裁切（重新編碼，較慢）</option>
            </select>
          </label>
          <label className="field">
            <span>多片段輸出</span>
            <select
              value={value.merge ? "merge" : "separate"}
              onChange={(e) =>
                onChange({ ...value, merge: e.target.value === "merge" })
              }
            >
              <option value="separate">各片段分別輸出</option>
              <option value="merge">依清單順序合併</option>
            </select>
          </label>
        </div>
      )}
    </div>
  );
}
