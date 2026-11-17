import { useState, useRef, useEffect, type PointerEvent } from "react";
import {
  FolderOpen,
  Save,
  Undo2,
  Redo2,
  Download,
  Trash2,
  ArrowUp,
  ArrowDown,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "./ui";
import { call, pickFiles, pickFolder } from "../api";
import type { Job } from "../types";
import type { Asset } from "../editor-model";
import {
  blankImage,
  makeLayer,
  type ImageLayer,
  type ImageProject,
} from "../image-model";
import {
  useUndo,
  useRenderedPreview,
  projectDialog,
  editorStatus,
} from "./editor-hooks";
export function ImageEditor({
  notify,
  onConvert,
  imports = [],
}: {
  notify: (s: string, error?: boolean) => void;
  onConvert?: (path: string) => void;
  imports?: string[];
}) {
  const history = useUndo(blankImage());
  const p = history.value;
  const [selected, setSelected] = useState("");
  const [mode, setMode] = useState("select");
  const [zoom, setZoom] = useState(0.65);
  const [color, setColor] = useState("#ffffff");
  const [stroke, setStroke] = useState(12);
  const [draft, setDraft] = useState<number[][]>([]);
  const [path, setPath] = useState("");
  const [out, setOut] = useState("");
  const [format, setFormat] = useState("png");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);
  const drag = useRef<{
    point: number[];
    project: ImageProject;
    layer?: ImageLayer;
    points: number[][];
    scroll?: number[];
  } | null>(null);
  const token = useRef(imports);
  const preview = useRenderedPreview(p, true, "fcimage");
  const layer = p.layers.find((l) => l.id === selected);
  const addImage = async (paths?: string[]) => {
    setBusy(true);
    setError("");
    try {
      const files = paths || (await pickFiles());
      const added: ImageLayer[] = [];
      let width = p.width,
        height = p.height;
      for (const file of files) {
        const asset = await call<Asset>("editor", {
          action: "inspect",
          path: file,
        });
        if (asset.kind !== "image") throw new Error("圖片編輯器僅接受圖片素材");
        if (!p.layers.length && !added.length) {
          width = asset.width!;
          height = asset.height!;
        }
        added.push(
          makeLayer("image", {
            source: asset.path,
            name: asset.name,
            width: asset.width!,
            height: asset.height!,
          }),
        );
      }
      if (added.length) {
        const snapshot = history.read();
        if (snapshot.layers.length) {
          width = snapshot.width;
          height = snapshot.height;
        }
        history.change({
          ...snapshot,
          width,
          height,
          crop: snapshot.layers.length ? snapshot.crop : [0, 0, width, height],
          layers: [...snapshot.layers, ...added],
        });
        setSelected(added[added.length - 1].id);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (imports !== token.current) {
      token.current = imports;
      if (imports.length) void addImage(imports);
    }
  }, [imports]);
  useEffect(() => {
    if (!job || !["queued", "running", "cancelling"].includes(job.status))
      return;
    const timer = setInterval(
      () =>
        void call<Job>("preview_status", { id: job.id })
          .then(setJob)
          .catch((e) => setError(String(e))),
      500,
    );
    return () => clearInterval(timer);
  }, [job?.id, job?.status]);
  const change = (patch: Partial<ImageLayer>) => {
    if (layer)
      history.change({
        ...p,
        layers: p.layers.map((l) =>
          l.id === layer.id ? { ...l, ...patch } : l,
        ),
      });
  };
  const point = (e: PointerEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    return [
      Math.max(
        0,
        Math.min(p.width, ((e.clientX - box.left) / box.width) * p.width),
      ),
      Math.max(
        0,
        Math.min(p.height, ((e.clientY - box.top) / box.height) * p.height),
      ),
    ];
  };
  const down = (e: PointerEvent<SVGSVGElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    const at = point(e);
    let chosen: ImageLayer | undefined;
    if (mode === "select") {
      chosen = [...p.layers]
        .reverse()
        .find(
          (l) =>
            l.visible &&
            at[0] >= l.x &&
            at[1] >= l.y &&
            at[0] <= l.x + l.width &&
            at[1] <= l.y + l.height,
        );
      if (chosen) {
        setSelected(chosen.id);
        history.begin();
      } else setSelected("");
    }
    drag.current = {
      point: at,
      project: p,
      layer: chosen,
      points: [at],
      scroll:
        mode === "pan"
          ? [
              e.clientX,
              e.clientY,
              viewport.current!.scrollLeft,
              viewport.current!.scrollTop,
            ]
          : undefined,
    };
    setDraft([at]);
  };
  const move = (e: PointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (!d || !e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const at = point(e);
    if (mode === "pan" && d.scroll) {
      viewport.current!.scrollLeft = d.scroll[2] - (e.clientX - d.scroll[0]);
      viewport.current!.scrollTop = d.scroll[3] - (e.clientY - d.scroll[1]);
      return;
    }
    if (mode === "select" && d.layer) {
      history.replace({
        ...d.project,
        layers: d.project.layers.map((l) =>
          l.id === d.layer!.id
            ? {
                ...l,
                x: d.layer!.x + at[0] - d.point[0],
                y: d.layer!.y + at[1] - d.point[1],
              }
            : l,
        ),
      });
      return;
    }
    if (["brush", "eraser"].includes(mode)) {
      d.points.push(at);
      setDraft([...d.points]);
    } else {
      d.points = [d.point, at];
      setDraft([...d.points]);
    }
  };
  const up = () => {
    const d = drag.current;
    if (!d) return;
    drag.current = null;
    if (mode === "select" && d.layer) history.finish();
    else if (["brush", "eraser"].includes(mode)) {
      const l = makeLayer(mode as "brush" | "eraser", {
        name: mode === "brush" ? "畫筆" : "橡皮擦",
        points: d.points,
        width: p.width,
        height: p.height,
        color,
        stroke,
      });
      history.change({ ...p, layers: [...p.layers, l] });
      setSelected(l.id);
    } else if (["crop", "mosaic"].includes(mode) && d.points.length > 1) {
      const a = d.points[0],
        b = d.points[d.points.length - 1];
      const region = [
        Math.min(a[0], b[0]),
        Math.min(a[1], b[1]),
        Math.max(1, Math.abs(a[0] - b[0])),
        Math.max(1, Math.abs(a[1] - b[1])),
      ];
      if (mode === "crop") history.change({ ...p, crop: region });
      else {
        const l = makeLayer("mosaic", {
          name: "馬賽克",
          x: region[0],
          y: region[1],
          width: region[2],
          height: region[3],
          mosaicSize: stroke,
        });
        history.change({ ...p, layers: [...p.layers, l] });
        setSelected(l.id);
      }
    }
    setDraft([]);
  };
  const reorder = (delta: number) => {
    if (!layer) return;
    const items = [...p.layers],
      i = items.findIndex((l) => l.id === layer.id),
      n = i + delta;
    if (n < 0 || n >= items.length) return;
    [items[i], items[n]] = [items[n], items[i]];
    history.change({ ...p, layers: items });
  };
  const add = (type: ImageLayer["type"]) => {
    const l = makeLayer(type, {
      name: type === "text" ? "文字" : type === "rect" ? "矩形" : "橢圓",
      color,
      x: p.width * 0.1,
      y: p.height * 0.1,
      width: Math.min(p.width * 0.6, 400),
      height: Math.min(p.height * 0.3, 200),
    });
    history.change({ ...p, layers: [...p.layers, l] });
    setSelected(l.id);
    setMode("select");
  };
  const saveProject = async (as = false) => {
    try {
      const result = await projectDialog(
        "fcimage",
        "save",
        p,
        as ? undefined : path,
      );
      if (result) {
        setPath(result.path);
        notify("圖片專案已儲存");
      }
    } catch (e) {
      setError(String(e));
    }
  };
  const openProject = async () => {
    try {
      const result = await projectDialog("fcimage", "load");
      if (result) {
        history.change(result.project as ImageProject);
        setPath(result.path);
        setSelected("");
        setError(
          result.missing?.length
            ? "遺失素材：" + result.missing.join("、")
            : "",
        );
      }
    } catch (e) {
      setError(String(e));
    }
  };
  const exportImage = async () => {
    try {
      setJob(
        await call<Job>("editor", {
          action: "enqueue",
          type: "fcimage",
          project: p,
          format,
          outputDir: out,
        }),
      );
      setError("");
    } catch (e) {
      setError(String(e));
    }
  };
  return (
    <div
      className="image-editor"
      onKeyDown={(e) => {
        if ((e.target as HTMLElement).matches("input,textarea,select")) return;
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
          e.preventDefault();
          e.shiftKey ? history.redo() : history.undo();
        }
      }}
    >
      <div className="editor-filebar row">
        <Button
          onClick={() => {
            history.change(blankImage());
            setSelected("");
            setPath("");
          }}
        >
          新增圖片
        </Button>
        <Button disabled={busy} onClick={() => addImage()}>
          <FolderOpen size={17} />
          開啟圖片／加入圖層
        </Button>
        <Button onClick={openProject}>開啟圖片專案</Button>
        <Button onClick={() => saveProject()}>
          <Save size={17} />
          儲存圖片專案
        </Button>
        <Button onClick={() => saveProject(true)}>另存圖片專案</Button>
        <Button disabled={!history.canUndo} onClick={history.undo}>
          <Undo2 size={17} />
          復原
        </Button>
        <Button disabled={!history.canRedo} onClick={history.redo}>
          <Redo2 size={17} />
          重做
        </Button>
      </div>
      {(error || preview.error) && (
        <p className="error-text" role="alert">
          {error || preview.error}
        </p>
      )}
      <div className="image-editor-layout">
        <aside className="image-tools glass" data-material="toolbar">
          {[
            ["select", "選取／移動"],
            ["pan", "平移"],
            ["crop", "裁切"],
            ["brush", "畫筆"],
            ["eraser", "橡皮擦"],
            ["mosaic", "馬賽克"],
          ].map(([id, label]) => (
            <Button
              key={id}
              aria-pressed={mode === id}
              onClick={() => setMode(id)}
            >
              {label}
            </Button>
          ))}
          <Button onClick={() => add("text")}>新增文字</Button>
          <Button onClick={() => add("rect")}>新增矩形</Button>
          <Button onClick={() => add("ellipse")}>新增橢圓</Button>
          <label className="field">
            顏色
            <input
              type="color"
              value={color}
              onChange={(e) => {
                setColor(e.target.value);
                if (layer) change({ color: e.target.value });
              }}
            />
          </label>
          <label className="field">
            筆刷／馬賽克尺寸
            <input
              type="number"
              min={2}
              max={200}
              value={stroke}
              onChange={(e) =>
                setStroke(Math.max(2, Math.min(200, Number(e.target.value))))
              }
            />
          </label>
        </aside>
        <div className="image-viewport" ref={viewport}>
          <div
            className="image-stage"
            style={{ width: p.width * zoom, height: p.height * zoom }}
          >
            {preview.uri && (
              <img
                src={preview.uri}
                alt="圖片合成預覽"
                onError={() =>
                  setError("無法載入圖層預覽，請檢查預覽檔案與權限")
                }
                draggable={false}
              />
            )}
            <svg
              aria-label="圖片編輯畫布"
              viewBox={`0 0 ${p.width} ${p.height}`}
              onPointerDown={down}
              onPointerMove={move}
              onPointerUp={up}
              onPointerCancel={up}
              style={{
                cursor:
                  mode === "pan"
                    ? "grab"
                    : mode === "select"
                      ? "default"
                      : "crosshair",
              }}
            >
              <rect
                className="image-crop-outline"
                x={p.crop[0]}
                y={p.crop[1]}
                width={p.crop[2]}
                height={p.crop[3]}
              />
              {layer && (
                <rect
                  className="image-selection-outline"
                  x={layer.x}
                  y={layer.y}
                  width={layer.width}
                  height={layer.height}
                />
              )}{" "}
              {!!draft.length &&
                (["brush", "eraser"].includes(mode) ? (
                  <polyline
                    points={draft.map((v) => v.join(",")).join(" ")}
                    fill="none"
                    stroke={mode === "eraser" ? "var(--text)" : color}
                    strokeWidth={stroke}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                ) : (
                  draft.length > 1 && (
                    <rect
                      className="image-selection-outline"
                      x={Math.min(draft[0][0], draft[draft.length - 1][0])}
                      y={Math.min(draft[0][1], draft[draft.length - 1][1])}
                      width={Math.abs(draft[draft.length - 1][0] - draft[0][0])}
                      height={Math.abs(
                        draft[draft.length - 1][1] - draft[0][1],
                      )}
                    />
                  )
                ))}
            </svg>
          </div>
          {preview.dirty && (
            <p role="status">更新圖層預覽 {Math.floor(preview.progress)}%</p>
          )}
        </div>
        <aside className="image-inspector glass" data-material="settings">
          <h3>圖層</h3>
          <div className="image-layer-list">
            {[...p.layers].reverse().map((l) => (
              <div
                className={`row ${selected === l.id ? "selected" : ""}`}
                key={l.id}
              >
                <button
                  className="layer-select"
                  aria-pressed={selected === l.id}
                  onClick={() => {
                    setSelected(l.id);
                    setMode("select");
                  }}
                >
                  {l.name}
                </button>
                <Button
                  compact
                  aria-label={`切換 ${l.name} 顯示`}
                  onClick={() =>
                    history.change({
                      ...p,
                      layers: p.layers.map((x) =>
                        x.id === l.id ? { ...x, visible: !x.visible } : x,
                      ),
                    })
                  }
                >
                  {l.visible ? <Eye size={16} /> : <EyeOff size={16} />}
                </Button>
              </div>
            ))}
          </div>
          <div className="row">
            <Button
              compact
              disabled={!layer}
              aria-label="圖層上移"
              onClick={() => reorder(1)}
            >
              <ArrowUp size={16} />
            </Button>
            <Button
              compact
              disabled={!layer}
              aria-label="圖層下移"
              onClick={() => reorder(-1)}
            >
              <ArrowDown size={16} />
            </Button>
            <Button
              compact
              disabled={!layer}
              aria-label="刪除圖層"
              onClick={() =>
                history.change({
                  ...p,
                  layers: p.layers.filter((x) => x.id !== selected),
                })
              }
            >
              <Trash2 size={16} />
            </Button>
          </div>
          {layer && (
            <>
              <label className="field">
                圖層名稱
                <input
                  value={layer.name}
                  onChange={(e) => change({ name: e.target.value })}
                />
              </label>
              <div className="image-layer-fields">
                {(["x", "y", "width", "height", "opacity"] as const).map(
                  (key, i) => (
                    <label className="field" key={key}>
                      {
                        [
                          "水平位置",
                          "垂直位置",
                          "圖層寬度",
                          "圖層高度",
                          "圖層不透明度",
                        ][i]
                      }
                      <input
                        type="number"
                        step={key === "opacity" ? 0.1 : 1}
                        value={layer[key]}
                        onChange={(e) =>
                          change({ [key]: Number(e.target.value) })
                        }
                      />
                    </label>
                  ),
                )}
              </div>
              {layer.type === "text" && (
                <>
                  <label className="field">
                    文字內容
                    <textarea
                      aria-label="文字內容"
                      value={layer.text}
                      onChange={(e) => change({ text: e.target.value })}
                    />
                  </label>
                  <label className="field">
                    字體大小
                    <input
                      type="number"
                      value={layer.fontSize}
                      onChange={(e) =>
                        change({ fontSize: Number(e.target.value) })
                      }
                    />
                  </label>
                </>
              )}
              {layer.type === "image" && (
                <>
                  <div className="row image-transform">
                    <Button
                      onClick={() =>
                        change({
                          rotation: (layer.rotation + 90) % 360,
                          width: layer.height,
                          height: layer.width,
                        })
                      }
                    >
                      旋轉 90°
                    </Button>
                    <Button onClick={() => change({ flipH: !layer.flipH })}>
                      水平翻轉
                    </Button>
                    <Button onClick={() => change({ flipV: !layer.flipV })}>
                      垂直翻轉
                    </Button>
                  </div>
                  {(
                    [
                      "brightness",
                      "contrast",
                      "saturation",
                      "warmth",
                      "blur",
                      "sharpen",
                    ] as const
                  ).map((key, i) => (
                    <label className="field" key={key}>
                      {["亮度", "對比", "飽和度", "色溫", "模糊", "銳化"][i]}
                      <input
                        type="range"
                        aria-label={
                          ["亮度", "對比", "飽和度", "色溫", "模糊", "銳化"][i]
                        }
                        min={key === "warmth" ? -1 : 0}
                        max={
                          key === "blur"
                            ? 30
                            : key === "sharpen"
                              ? 5
                              : key === "warmth"
                                ? 1
                                : 3
                        }
                        step=".05"
                        value={layer[key]}
                        onChange={(e) =>
                          change({ [key]: Number(e.target.value) })
                        }
                      />
                    </label>
                  ))}
                  <label className="field">
                    濾鏡
                    <select
                      value={layer.filter}
                      onChange={(e) => change({ filter: e.target.value })}
                    >
                      <option value="none">原色</option>
                      <option value="grayscale">黑白</option>
                      <option value="sepia">復古</option>
                    </select>
                  </label>
                  <Button
                    onClick={async () => {
                      try {
                        const files = await pickFiles();
                        if (files[0]) change({ source: files[0] });
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    重新定位圖片
                  </Button>
                </>
              )}
            </>
          )}
        </aside>
      </div>
      <div className="row image-footer">
        <label>
          畫布縮放 {Math.round(zoom * 100)}%{" "}
          <input
            aria-label="畫布縮放"
            type="range"
            min={0.1}
            max={3}
            step={0.05}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          />
        </label>
        <span>
          {p.width} × {p.height} · 裁切 {Math.round(p.crop[2])} ×{" "}
          {Math.round(p.crop[3])}
        </span>
        <Button
          onClick={() =>
            history.change({ ...p, crop: [0, 0, p.width, p.height] })
          }
        >
          重設裁切
        </Button>
      </div>
      <details className="editor-export glass" data-material="settings">
        <summary>畫布與輸出設定</summary>
        <div className="editor-fields">
          {(
            [
              "width",
              "height",
              "outputWidth",
              "outputHeight",
              "quality",
            ] as const
          ).map((key, i) => (
            <label className="field" key={key}>
              {
                [
                  "畫布寬度",
                  "畫布高度",
                  "輸出寬度 · 0 自動",
                  "輸出高度 · 0 自動",
                  "輸出品質",
                ][i]
              }
              <input
                type="number"
                value={p[key]}
                onChange={(e) =>
                  history.change({
                    ...p,
                    [key]: Number(e.target.value),
                    ...(key === "width" || key === "height"
                      ? {
                          crop: [
                            0,
                            0,
                            key === "width" ? Number(e.target.value) : p.width,
                            key === "height"
                              ? Number(e.target.value)
                              : p.height,
                          ],
                        }
                      : {}),
                  })
                }
              />
            </label>
          ))}
        </div>
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
          aria-label="圖片匯出格式"
          value={format}
          onChange={(e) => setFormat(e.target.value)}
        >
          {["png", "jpg", "webp"].map((f) => (
            <option key={f}>{f}</option>
          ))}
        </select>
        <Button variant="primary" onClick={exportImage}>
          <Download size={17} />
          匯出圖片
        </Button>
      </div>
      {job && (
        <div className="row">
          <span>
            {editorStatus[job.status]} · {Math.floor(job.progress)}% {job.error}
          </span>
          {["queued", "running"].includes(job.status) && (
            <Button onClick={() => call("cancel", { id: job.id })}>
              取消圖片輸出
            </Button>
          )}
          {job.status === "completed" && (
            <>
              <Button onClick={() => call("open_output", { id: job.id })}>
                開啟圖片輸出資料夾
              </Button>
              {onConvert && (
                <Button onClick={() => onConvert(job.outputs[0])}>
                  加入轉檔佇列
                </Button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
