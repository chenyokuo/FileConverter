import { useEffect, useRef, useState, type PointerEvent } from "react";
import {
  Play,
  Scissors,
  Undo2,
  Redo2,
  Plus,
  FolderOpen,
  Save,
  Download,
  VolumeX,
  Music,
  Layers,
  Trash2,
} from "lucide-react";
import { Button } from "./ui";
import { call, pickFiles, pickFolder } from "../api";
import { defaultOptions } from "../defaults";
import type { HardwareDevice, Job, Options } from "../types";
import {
  clipLength,
  timelineLength,
  newClip, importedClips, related, patchClip, splitClips,
  type VideoProject,
  type Clip,
  type Asset,
} from "../editor-model";
import {
  useUndo,
  useRenderedPreview,
  projectDialog,
  editorStatus,
} from "./editor-hooks";
import { OptionsEditor } from "./OptionsEditor";
import { timecode } from "./TimeRange";
const blank = (): VideoProject => ({
  type: "fcvideo",
  version: 1,
  width: 1280,
  height: 720,
  fps: 30,
  clips: [],
  titles: [],
  subtitles: "",
  export: { ...defaultOptions },
});
export function VideoEditor({
  active = true,
  hardware,
  notify,
  imports = [],
}: {
  active?: boolean;
  hardware: HardwareDevice[];
  notify: (s: string, error?: boolean) => void;
  imports?: string[];
}) {
  const history = useUndo(blank());
  const p = history.value;
  const [assets, setAssets] = useState<Record<string, Asset>>({});
  const [selected, setSelected] = useState("");
  const [track, setTrack] = useState("V1");
  const [current, setCurrent] = useState(0);
  const [showProperties,setShowProperties]=useState(true);
  const [showLibrary,setShowLibrary]=useState(true);
  const [fitAuto,setFitAuto]=useState(true);
  const timelineViewport=useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(45);
  const [menu,setMenu]=useState<{x:number;y:number}|null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [projectPath, setProjectPath] = useState("");
  const [out, setOut] = useState("");
  const [format, setFormat] = useState("mp4");
  const [job, setJob] = useState<Job | null>(null);
  const [title, setTitle] = useState("");
  const assetPointer = useRef<{ x: number; y: number } | null>(null);
  const assetDragged = useRef(false);
  const player = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (!active) player.current?.pause();
  }, [active]);
  const drag = useRef<{
    clip: Clip;
    mode: string;
    x: number;
    project: VideoProject;
  } | null>(null);
  const importToken = useRef(imports);
  const duration = timelineLength(p);
  useEffect(()=>{ const el=timelineViewport.current;if(!el || !fitAuto)return;const fit=()=>{if(el.clientWidth)setZoom(Math.max(.1,Math.min(160,(el.clientWidth-80)/Math.max(1,duration))))};const observer=new ResizeObserver(fit);observer.observe(el);fit();return()=>observer.disconnect(); },[duration,fitAuto,active]);
  const preview = useRenderedPreview(p, p.clips.length > 0);
  const c = p.clips.find((c) => c.id === selected);
  const tick=[1,2,5,10,30,60,300,600,3600].find(v=>v*zoom>=60) || 3600;
  const tracks = Array.from(
    new Set(["V1", "A1", "A2", ...p.clips.map((c) => c.track)]),
  );
  const audioClip=c?.pairId ? p.clips.find(v=>v.pairId===c.pairId && v.track.startsWith("A")) : undefined;
  const update = (patch: Partial<Clip>) => {
    if (c)
      history.change({
        ...p,
        clips: patchClip(p.clips, c.videoOnly && audioClip && ("volume" in patch || "mute" in patch) ? audioClip : c, patch),
      });
  };
  const loadAssets = async (paths: string[]) => {
    const result: Asset[] = [];
    for (const path of paths) {
      const asset =
        assets[path] ||
        (await call<Asset>("editor", { action: "inspect", path }));
      result.push(asset);
      setAssets((old) => ({ ...old, [path]: asset }));
    }
    return result;
  };
  const add = async (paths?: string[], mode = "append") => {
    setBusy(true);
    setError("");
    try {
      const list = await loadAssets(paths || (await pickFiles()));
      let snapshot = history.read();
      if(mode==="insert") for(const candidate of snapshot.clips.filter(v=>v.track===track && current>v.at+.01 && current<v.at+clipLength(v)-.01)) snapshot={...snapshot,clips:splitClips(snapshot.clips,candidate,current)};
      let at =
        mode === "insert"
          ? current
          : Math.max(
              0,
              ...snapshot.clips
                .filter((c) => c.track === track)
                .map((c) => c.at + clipLength(c)),
            );
      const added: Clip[] = [];
      for (const a of list) {
        const target =
          a.kind === "audio" ? (track.startsWith("A") ? track : "A2") : track;
        const clip = newClip(a, target, at);
        added.push(...importedClips(a,target,at));
        at += clipLength(clip);
      }
      const inserted = at - current;
      history.change({
        ...snapshot,
        clips: [
          ...snapshot.clips.map((c) =>
            mode === "insert" && (c.track === track || (c.linked && snapshot.clips.some(v=>v.track===track && related(c,v)))) && c.at >= current
              ? { ...c, at: c.at + inserted }
              : c,
          ),
          ...added,
        ],
      });
      if (added.length) {setSelected(added[0].id);setFitAuto(true);}
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (imports !== importToken.current) {
      importToken.current = imports;
      if (imports.length) void add(imports);
    }
  }, [imports]);
  useEffect(() => {
    if (!job || !["queued", "running", "cancelling"].includes(job.status))
      return;
    const timer = setInterval(() => {
      void call<Job>("preview_status", { id: job.id })
        .then(setJob)
        .catch((e) => setError(String(e)));
    }, 500);
    return () => clearInterval(timer);
  }, [job?.id, job?.status]);
  const seek = (value: number) => {
    const time = Math.max(0, Math.min(duration, value));
    setCurrent(time);
    if (player.current && !preview.dirty) player.current.currentTime = time;
  };
  const split = () => {
    if (!c || current <= c.at + 0.01 || current >= c.at + clipLength(c) - 0.01)
      return;
    const clips=splitClips(p.clips,c,current);
    history.change({...p,clips});
    setSelected(clips.find(x=>x.track===c.track && x.at===current)?.id || c.id);
  };
  const separate = () => {
    if (!c || !assets[c.source]?.hasAudio || c.videoOnly || !c.track.startsWith("V")) return;
    const destination =
      tracks
        .filter((t) => t.startsWith("A"))
        .find(
          (t) =>
            !p.clips.some(
              (a) =>
                a.track === t &&
                a.at < c.at + clipLength(c) &&
                a.at + clipLength(a) > c.at,
            ),
        ) ||
      "A" +
        (Math.max(
          2,
          ...tracks
            .filter((t) => t.startsWith("A"))
            .map((t) => Number(t.slice(1))),
        ) +
          1);
    history.change({
      ...p,
      clips: [
        ...p.clips.map((x) => (x.id === c.id ? { ...x, mute: true, videoOnly:true, pairId:c.id, linked:true } : x)),
        { ...c, id: crypto.randomUUID(), track: destination, mute: false, videoOnly:false, pairId:c.id, linked:true },
      ],
    });
  };
  const dissolve = () => {
    if (!c) return;
    const before = p.clips
      .filter((x) => x.track === c.track && x.at < c.at)
      .sort((a, b) => b.at - a.at)[0];
    if (!before) {
      setError("先選取同軌中較後的片段");
      return;
    }
    const amount = Math.min(0.5, clipLength(c) / 2, clipLength(before) / 2);
    update({ at: before.at + clipLength(before) - amount, transition: amount });
  };
  const addToMusic = async () => { const files=await pickFiles(); const list=await loadAssets(files); const snap=history.read(); history.change({...snap,clips:[...snap.clips,...list.map(a=>newClip(a,"A2",current))]}); };
  const saveProject = async (as = false) => {
    try {
      const result = await projectDialog(
        "fcvideo",
        "save",
        p,
        as ? undefined : projectPath,
      );
      if (result) {
        setProjectPath(result.path);
        notify("專案已儲存");
      }
    } catch (e) {
      setError(String(e));
    }
  };
  const openProject = async () => {
    try {
      const result = await projectDialog("fcvideo", "load");
      if (result) {
        history.change(result.project as VideoProject);
        setProjectPath(result.path);
        setSelected("");
        setCurrent(0);
        setError(
          result.missing?.length
            ? "遺失素材：" + result.missing.join("、")
            : "",
        );
        await loadAssets(
          (result.project as VideoProject).clips
            .map((c) => c.source)
            .filter((path) => !result.missing?.includes(path)),
        );
      }
    } catch (e) {
      setError(String(e));
    }
  };
  const exportVideo = async (audio = false) => {
    setError("");
    try {
      const next = await call<Job>("editor", {
        action: "enqueue",
        type: "fcvideo",
        project: p,
        format: audio ? "wav" : format,
        outputDir: out,
      });
      setJob(next);
      notify("已加入影片編輯輸出佇列");
    } catch (e) {
      setError(String(e));
    }
  };
  const pointerDown = (
    e: PointerEvent<HTMLDivElement>,
    clip: Clip,
    mode: string,
  ) => {
    e.stopPropagation();
    e.preventDefault();
    setSelected(clip.id);
    history.begin();
    drag.current = { clip: { ...clip }, mode, x: e.clientX, project: p };
    (e.currentTarget.closest(".editor-clip") as HTMLElement).setPointerCapture(
      e.pointerId,
    );
  };
  const pointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const state = drag.current;
    if (!state || !e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const original = state.clip;
    const delta = (e.clientX - state.x) / zoom;
    let changed = { ...original };
    if (state.mode === "move") changed.at = Math.max(0, original.at + delta);
    if (state.mode === "left") {
      const start = Math.max(
        0,
        Math.min(original.out - 0.02, original.in + delta * original.speed),
      );
      changed.in = start;
      changed.at = Math.max(
        0,
        original.at + (start - original.in) / original.speed,
      );
    }
    if (state.mode === "right")
      changed.out = Math.max(
        original.in + 0.02,
        Math.min(
          assets[original.source]?.duration || 864000,
          original.out + delta * original.speed,
        ),
      );
    const len = clipLength(changed);
    changed.fadeIn = Math.min(len, changed.fadeIn);
    changed.fadeOut = Math.min(len, changed.fadeOut);
    changed.transition = Math.min(len / 2, changed.transition);
    history.replace({
      ...state.project,
      clips: state.project.clips.map((x) =>
        patchClip(state.project.clips, original, changed).find(v=>v.id===x.id)!,
      ),
    });
  };
  return (
    <div
      className="video-editor"
      onKeyDown={(e) => {
        if ((e.target as HTMLElement).matches("input,textarea,select")) return;
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
          e.preventDefault();
          e.shiftKey ? history.redo() : history.undo();
        }
      }}
    >
      {menu && <div className="clip-context glass" role="menu" style={{left:Math.min(menu.x,innerWidth-240),top:Math.min(menu.y,innerHeight-180)}}><Button onClick={()=>{split();setMenu(null)}}>分割</Button><Button onClick={()=>{if(c)update({mute:!c.mute});setMenu(null)}}>靜音／取消靜音</Button><Button onClick={()=>{if(c)history.change({...p,clips:p.clips.filter(x=>!related(c,x))});setMenu(null)}}>刪除片段</Button><Button onClick={()=>setMenu(null)}>關閉選單</Button></div>}
      <div className="editor-filebar row">
        <Button
          onClick={() => {
            history.change(blank());
            setProjectPath("");
            setSelected("");
            setCurrent(0);
          }}
        >
          新增專案
        </Button>
        <Button onClick={()=>setShowLibrary(v=>!v)}>素材庫</Button><Button onClick={()=>setShowProperties(v=>!v)}>片段屬性</Button>
        <Button onClick={openProject}>
          <FolderOpen size={17} />
          開啟專案
        </Button>
        <Button onClick={() => saveProject()}>
          <Save size={17} />
          儲存
        </Button>
        <Button onClick={() => saveProject(true)}>另存專案</Button>
        <label>
          素材軌道{" "}
          <select value={track} onChange={(e) => setTrack(e.target.value)}>
            {Array.from(new Set([...tracks, "V2"])).map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <Button disabled={busy} onClick={() => add()}>
          <Plus size={17} />
          匯入素材
        </Button>
      </div>
      {(error || preview.error) && (
        <p role="alert" className="error-text">
          {error || preview.error}
        </p>
      )}
      <div className="editor-preview glass" data-material="card">
        {preview.uri && !preview.dirty ? (
          <video
            ref={player}
            src={preview.uri}
            controls
            onError={() =>
              setError("預覽播放器無法讀取媒體，請檢查檔案與預覽權限後重試")
            }
            onLoadedMetadata={(e) => {
              e.currentTarget.currentTime = Math.min(
                current,
                e.currentTarget.duration,
              );
            }}
            onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime)}
            onEnded={() => setCurrent(duration)}
          />
        ) : (
          <div className="range-player-empty">
            {assets[c?.source || ""]?.poster && (
              <img src={assets[c?.source || ""].poster} alt="素材預覽" />
            )}
            <Play size={32} />
            <span>
              {p.clips.length
                ? preview.error
                  ? "請修正時間軸後重試預覽"
                  : `預覽合成中 ${Math.floor(preview.progress)}%`
                : "匯入影片開始剪輯"}
            </span>
          </div>
        )}
      </div>
      <div className="editor-controls glass row" data-material="toolbar">
        <Button
          disabled={!preview.uri || preview.dirty}
          onClick={() => {
            const v = player.current;
            if (v) void (v.paused ? v.play() : Promise.resolve(v.pause()));
          }}
        >
          <Play size={18} />
          播放／暫停
        </Button>
        <span>
          {timecode(current)} / {timecode(duration)}
        </span>
        <Button disabled={!c} onClick={split}>
          <Scissors size={17} />
          分割
        </Button>
        <Button disabled={!history.canUndo} onClick={history.undo}>
          <Undo2 size={17} />
          復原
        </Button>
        <Button disabled={!history.canRedo} onClick={history.redo}>
          <Redo2 size={17} />
          重做
        </Button>
        <Button disabled={busy} onClick={() => add(undefined, "insert")}>
          在播放位置插入
        </Button>
        <Button
          disabled={!c}
          onClick={() =>
            history.change({
              ...p,
              clips: p.clips.filter((x) => !c || !related(c,x)),
            })
          }
        >
          <Trash2 size={17} />
          刪除片段
        </Button>
        <Button onClick={()=>{setFitAuto(true);setZoom(Math.max(.1,Math.min(160,((timelineViewport.current?.clientWidth || 700)-80)/Math.max(1,duration))))}}>Fit Timeline</Button>
        <Button disabled={!c?.pairId} onClick={()=>c && history.change({...p,clips:p.clips.map(x=>x.pairId===c.pairId?{...x,linked:!c.linked,...(!c.linked?{at:c.at,in:c.in,out:c.out,speed:c.speed}: {})}:x)})}>{c?.linked ? "解除連動" : "重新連動"}</Button>
        <Button disabled={!c} onClick={()=>c && history.change({...p,clips:[...p.clips,...p.clips.filter(x=>related(c,x)).map(x=>({...x,id:crypto.randomUUID(),pairId:x.pairId ? 'copy-'+p.clips.length+'-'+x.pairId:undefined,at:x.at+clipLength(c)}))]})}>複製片段</Button>
        <Button onClick={()=>{setTrack("A2");void addToMusic();}}>加入背景音樂</Button>
        <label>
          縮放{" "}
          <input
            type="range"
            aria-label="時間軸縮放"
            min={0.1}
            max={160}
            value={zoom}
            onChange={(e) => {setFitAuto(false);setZoom(Number(e.target.value));}}
          />
        </label>
      </div>
      <div className="editor-assets row" hidden={!showLibrary}>
        {Object.values(assets).map((a) => (
          <button
            key={a.path}
            draggable={false}
            onPointerDown={(e) => {
              e.preventDefault();
              assetPointer.current = { x: e.clientX, y: e.clientY };
              assetDragged.current = false;
              e.currentTarget.setPointerCapture(e.pointerId);
            }}
            onPointerUp={(e) => {
              const origin = assetPointer.current;
              assetPointer.current = null;
              if (
                !origin ||
                Math.hypot(e.clientX - origin.x, e.clientY - origin.y) < 5
              )
                return;
              assetDragged.current = true;
              const row = document
                .elementFromPoint(e.clientX, e.clientY)
                ?.closest<HTMLElement>(".editor-track");
              if (!row) return;
              const destination = row.dataset.track!;
              if (a.kind === "audio" && destination.startsWith("V")) {
                setError("音訊請拖入 A1／A2 軌道");
                return;
              }
              const box = row.getBoundingClientRect();
              const clip = newClip(
                a,
                destination,
                Math.max(0, (e.clientX - box.left - 60) / zoom),
              );
              history.change({ ...p, clips: [...p.clips, ...importedClips(a,clip.track,clip.at)] });
              setSelected(clip.id);
            }}
            onClick={() => {
              if (assetDragged.current) {
                assetDragged.current = false;
                return;
              }
              const clip = newClip(
                a,
                a.kind === "audio" ? "A2" : track,
                current,
              );
              history.change({ ...p, clips: [...p.clips, ...importedClips(a,clip.track,clip.at)] });
              setSelected(clip.id);
            }}
            title="拖入軌道或點擊插入播放位置"
          >
            {a.poster ? <img src={a.poster} alt="" /> : <Music size={20} />}
            <span>{a.name}</span>
          </button>
        ))}
      </div>
      <div className="editor-timeline-scroll" ref={timelineViewport}>
        <div
          className="editor-timeline"
          style={{ width: Math.max(300, duration * zoom + 80) }}
        >
          <div
            className="editor-ruler"
            onPointerDown={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              seek((e.clientX - rect.left - 60) / zoom);
            }}
          >
            {Array.from({ length: Math.floor(duration / tick)+1 }, (_, i) => (
              <span key={i} style={{ left: 60 + i * tick * zoom }}>
                {timecode(i * tick)}
              </span>
            ))}
          </div>
          {tracks.map((t) => (
            <div
              className={`editor-track track-${t[0]}`}
              data-track={t}
              key={t}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const asset =
                  assets[e.dataTransfer.getData("application/x-fc-asset")];
                if (asset) {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const clip = newClip(
                    asset,
                    t,
                    Math.max(0, (e.clientX - rect.left - 60) / zoom),
                  );
                  history.change({ ...p, clips: [...p.clips, ...importedClips(asset,clip.track,clip.at)] });
                  setSelected(clip.id);
                }
              }}
            >
              <strong>{t}</strong>
              <div
                className="track-seek"
                onPointerDown={(e) => {
                  const rect =
                    e.currentTarget.parentElement!.getBoundingClientRect();
                  seek((e.clientX - rect.left - 60) / zoom);
                }}
              />
              {p.clips
                .filter((x) => x.track === t)
                .map((clip) => (
                  <div
                    tabIndex={0}
                    role="button"
                    aria-label={`${t} ${assets[clip.source]?.name || clip.source.split(/[\\/]/).pop()}`}
                    aria-pressed={selected === clip.id}
                    key={clip.id}
                    className={`editor-clip ${selected === clip.id ? "selected" : ""}`}
                    style={{
                      left: 60 + clip.at * zoom,
                      width: Math.max(10, clipLength(clip) * zoom),
                    }}
                    title={clip.pairId ? (clip.linked ? "影音連動" : "影音已解除連動") : "獨立片段"}
                    onContextMenu={(e)=>{e.preventDefault();setSelected(clip.id);setMenu({x:e.clientX,y:e.clientY});}}
                    onPointerDown={(e) => pointerDown(e, clip, "move")}
                    onPointerMove={pointerMove}
                    onPointerUp={() => {
                      drag.current = null;
                      history.finish();
                    }}
                    onPointerCancel={() => {
                      drag.current = null;
                      history.finish();
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
                        e.preventDefault();
                        setSelected(clip.id);
                        history.change({
                          ...p,
                          clips: patchClip(p.clips,clip,{at:Math.max(0,clip.at+(e.key==="ArrowRight"?.1:-.1))}),
                        });
                      }
                    }}
                  >
                    <div
                      className="clip-trim left"
                      onPointerDown={(e) => pointerDown(e, clip, "left")}
                    />
                    <span>
                      {assets[clip.source]?.name ||
                        clip.source.split(/[\\/]/).pop()}
                    </span>
                    {clip.track.startsWith("A") && assets[clip.source]?.waveform && (
                      <img
                        className="clip-waveform"
                        src={assets[clip.source].waveform}
                        alt="音訊波形"
                        style={{
                          width: `${(assets[clip.source].duration / Math.max(0.001, clip.out - clip.in)) * 100}%`,
                          left: `-${(clip.in / Math.max(0.001, clip.out - clip.in)) * 100}%`,
                        }}
                      />
                    )}
                    <div
                      className="clip-trim right"
                      onPointerDown={(e) => pointerDown(e, clip, "right")}
                    />
                  </div>
                ))}
            </div>
          ))}
          <div
            className="editor-cursor"
            style={{ left: 60 + current * zoom }}
            onPointerDown={(e) => {
              e.currentTarget.setPointerCapture(e.pointerId);
            }}
            onPointerMove={(e) => {
              if (e.currentTarget.hasPointerCapture(e.pointerId)) {
                const rect =
                  e.currentTarget.parentElement!.getBoundingClientRect();
                seek((e.clientX - rect.left - 60) / zoom);
              }
            }}
          />
        </div>
      </div>
      {c && showProperties && (
        <div className="editor-properties glass" data-material="settings">
          <h3>片段設定</h3>
          <div className="editor-fields">
            <label className="field">
              軌道
              <select
                value={c.track}
                onChange={(e) => update({ track: e.target.value })}
              >
                {Array.from(new Set([...tracks, "V2"])).map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
            {(
              [
                "at",
                "in",
                "out",
                "speed",
                "volume",
                "fadeIn",
                "fadeOut",
                "transition",
              ] as const
            ).map((key, i) => (
              <label className="field" key={key}>
                {
                  [
                    "專案位置 秒",
                    "來源起點 秒",
                    "來源終點 秒",
                    "速度",
                    "音量",
                    "淡入 秒",
                    "淡出 秒",
                    "交叉溶解 秒",
                  ][i]
                }
                <input
                  type="number"
                  step="0.1"
                  min={key === "speed" ? 0.25 : 0}
                  value={key==="volume" && c.videoOnly && audioClip ? audioClip.volume : c[key]}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    if (Number.isFinite(v)) update({ [key]: v });
                  }}
                />
              </label>
            ))}
            {c.track !== "V1" &&
              c.track.startsWith("V") &&
              (["x", "y", "size"] as const).map((key) => (
                <label className="field" key={key}>
                  {key}
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step=".05"
                    value={c[key]}
                    onChange={(e) => update({ [key]: Number(e.target.value) })}
                  />
                </label>
              ))}
          </div>
          <div className="row">
            <Button onClick={() => update({ mute: !(c.videoOnly && audioClip ? audioClip.mute : c.mute) })}>
              <VolumeX size={16} />
              {(c.videoOnly && audioClip ? audioClip.mute : c.mute) ? "取消靜音" : "靜音"}
            </Button>
            <Button disabled={!assets[c.source]?.hasAudio || c.videoOnly || !c.track.startsWith("V")} title={c.videoOnly ? "已自動分離音軌" : "需選取包含音訊的影片"} onClick={separate}>
              <Layers size={16} />
              分離音軌
            </Button>
            <Button onClick={dissolve}>與前一段交叉溶解</Button>
            <Button
              onClick={async () => {
                try {
                  const files = await pickFiles();
                  if (files[0]) {
                    await loadAssets([files[0]]);
                    history.change({
                      ...p,
                      clips: p.clips.map((x) =>
                        x.source === c.source ? { ...x, source: files[0] } : x,
                      ),
                    });
                  }
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              重新定位素材
            </Button>
          </div>
        </div>
      )}
      <div className="editor-titles glass" data-material="settings">
        <div className="row">
          <input
            aria-label="文字標題"
            placeholder="文字標題"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Button
            disabled={!title.trim()}
            onClick={() => {
              history.change({
                ...p,
                titles: [
                  ...p.titles,
                  {
                    text: title,
                    start: current,
                    end: Math.max(
                      current + 0.1,
                      Math.min(duration || current + 5, current + 5),
                    ),
                    x: 0.1,
                    y: 0.1,
                    size: 40,
                  },
                ],
              });
              setTitle("");
            }}
          >
            插入文字
          </Button>
          <Button
            onClick={async () => {
              try {
                const files = await pickFiles();
                if (files[0]) history.change({ ...p, subtitles: files[0] });
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            匯入 SRT
          </Button>
          {p.subtitles && (
            <Button onClick={() => history.change({ ...p, subtitles: "" })}>
              移除字幕
            </Button>
          )}
        </div>
        {p.titles.map((t, i) => (
          <div className="row" key={i}>
            <input
              aria-label={`標題 ${i + 1}`}
              value={t.text}
              onChange={(e) =>
                history.change({
                  ...p,
                  titles: p.titles.map((v, n) =>
                    n === i ? { ...v, text: e.target.value } : v,
                  ),
                })
              }
            />
            {(["start", "end", "x", "y", "size"] as const).map((key) => (
              <label key={key}>
                {key}
                <input
                  type="number"
                  step=".1"
                  value={t[key]}
                  onChange={(e) =>
                    history.change({
                      ...p,
                      titles: p.titles.map((v, n) =>
                        n === i ? { ...v, [key]: Number(e.target.value) } : v,
                      ),
                    })
                  }
                />
              </label>
            ))}
            <Button
              onClick={() =>
                history.change({
                  ...p,
                  titles: p.titles.filter((_, n) => n !== i),
                })
              }
            >
              移除
            </Button>
          </div>
        ))}
      </div>
      <details className="glass editor-export" data-material="settings">
        <summary>輸出設定</summary>
        <div className="editor-fields">
          {(["width", "height", "fps"] as const).map((key) => (
            <label className="field" key={key}>
              {key}
              <input
                type="number"
                value={p[key]}
                onChange={(e) =>
                  history.change({ ...p, [key]: Number(e.target.value) })
                }
              />
            </label>
          ))}
        </div>
        <OptionsEditor
          category="video"
          format={format}
          value={p.export}
          hardware={hardware}
          onChange={(v: Options) => history.change({ ...p, export: v })}
        />
      </details>
      <div className="conversion-toolbar glass" data-material="toolbar">
        <Button
          className="editor-output-folder"
          title={out || "選擇輸出資料夾"}
          onClick={async () => {
            const folder = await pickFolder();
            if (folder) setOut(folder);
          }}
        >
          <FolderOpen size={17} />
          <span>{out || "選擇輸出資料夾"}</span>
        </Button>
        <select
          aria-label="編輯器輸出格式"
          value={format}
          onChange={(e) => setFormat(e.target.value)}
        >
          {["mp4", "mkv", "mov", "webm"].map((f) => (
            <option key={f}>{f}</option>
          ))}
        </select>
        <Button disabled={!p.clips.length} onClick={() => exportVideo(true)}>
          擷取完整音訊 WAV
        </Button>
        <Button
          variant="primary"
          disabled={!p.clips.length}
          onClick={() => exportVideo()}
        >
          <Download size={17} />
          輸出完整作品
        </Button>
        {c && (
          <Button
            onClick={async () => {
              try {
                setJob(
                  await call<Job>("editor", {
                    action: "enqueue",
                    type: "fcvideo",
                    project: {
                      ...p,
                      clips: [{ ...c, at: 0, transition: 0 }],
                      titles: [],
                      subtitles: "",
                    },
                    format,
                    outputDir: out,
                  }),
                );
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            輸出所選片段
          </Button>
        )}
      </div>
      {job && (
        <div className="row">
          <span>
            {editorStatus[job.status]} · {Math.floor(job.progress)}% {job.error}
          </span>
          {["queued", "running"].includes(job.status) && (
            <Button onClick={() => call("cancel", { id: job.id })}>
              取消輸出
            </Button>
          )}
          {job.status === "completed" && (
            <Button onClick={() => call("open_output", { id: job.id })}>
              開啟輸出資料夾
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
