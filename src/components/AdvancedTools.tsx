import { useEffect, useRef, useState, type PointerEvent } from "react";
import {
  ArrowDown,
  ArrowUp,
  FolderOpen,
  Play,
  RotateCcw,
  Scan,
  Trash2,
  Wrench,
} from "lucide-react";
import { call, desktop, pickFiles, pickFolder } from "../api";
import type { Job, Options } from "../types";
import { Button, Modal } from "./ui";

export interface ToolField {
  key: string;
  label: string;
  type: string;
  default: unknown;
  min?: number;
  max?: number;
  secret?: boolean;
  choices?: { value: string; label: string }[];
}
export interface ToolDefinition {
  id: string;
  category: string;
  name: string;
  detail: string;
  sources: string[];
  output: string;
  fields: ToolField[];
  available: boolean;
  reason: string;
  minSources: number;
  maxSources: number | null;
  preview: boolean;
}
export interface FilePreview {
  path: string;
  name: string;
  format: string;
  size: number;
  image: string | null;
  text?: string;
  metadata: Record<string, unknown>;
  media?: string;
}
const formatSize = (size: number) =>
  size > 1024 ** 2
    ? `${(size / 1024 ** 2).toFixed(2)} MB`
    : `${(size / 1024).toFixed(1)} KB`;
const fileName = (path: string) => path.split(/[\\/]/).pop() || path;

export function RegionSelector({
  image,
  value,
  onChange,
}: {
  image: string;
  value: number[];
  onChange: (value: number[]) => void;
}) {
  const start = useRef<number[] | null>(null);
  const point = (e: PointerEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    return [
      Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)),
      Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)),
    ];
  };
  return (
    <div
      className="region-editor"
      aria-label="拖曳選取處理區域"
      onPointerDown={(e) => {
        start.current = point(e);
        e.currentTarget.setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (!start.current) return;
        const end = point(e);
        const x = Math.min(0.999, Math.min(start.current[0], end[0])),
          y = Math.min(0.999, Math.min(start.current[1], end[1]));
        onChange([
          x,
          y,
          Math.min(1 - x, Math.max(0.001, Math.abs(end[0] - start.current[0]))),
          Math.min(1 - y, Math.max(0.001, Math.abs(end[1] - start.current[1]))),
        ]);
      }}
      onPointerUp={() => {
        start.current = null;
      }}
      onPointerCancel={() => {
        start.current = null;
      }}
    >
      <img src={image} alt="原始檔案區域預覽" draggable={false} />
      <span
        className="region-selection"
        style={{
          left: `${value[0] * 100}%`,
          top: `${value[1] * 100}%`,
          width: `${value[2] * 100}%`,
          height: `${value[3] * 100}%`,
        }}
      />
    </div>
  );
}

export function BeforeAfter({
  before,
  after,
}: {
  before: FilePreview;
  after: FilePreview;
}) {
  return (
    <div className="before-after">
      <figure>
        {before.image && <img src={before.image} alt="處理前" />}
        <figcaption>原始 · {formatSize(before.size)}</figcaption>
      </figure>
      <figure>
        {after.image && <img src={after.image} alt="處理後" />}
        <figcaption>
          處理後 · {formatSize(after.size)} · 大小變化{" "}
          {before.size
            ? ((after.size / before.size - 1) * 100).toFixed(1)
            : "0"}
          %
        </figcaption>
      </figure>
    </div>
  );
}

export function AdvancedTools({
  category,
  disabled,
  outputDir,
  defaults,
  notify,
}: {
  category: string;
  disabled: boolean;
  outputDir: string;
  defaults: Options;
  notify: (message: string, error?: boolean) => void;
}) {
  const [catalog, setCatalog] = useState<ToolDefinition[]>([]);
  const [tool, setTool] = useState<ToolDefinition | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [output, setOutput] = useState(outputDir);
  const [before, setBefore] = useState<FilePreview | null>(null);
  const [after, setAfter] = useState<FilePreview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [previewTask, setPreviewTask] = useState<Job | null>(null);
  const activePreview = useRef<string | null>(null);
  useEffect(() => {
    if (desktop && !disabled)
      void call<ToolDefinition[]>("tools")
        .then(setCatalog)
        .catch((e) => notify(String(e), true));
  }, [disabled]);
  const cleanup = async (id: string) => {
    try {
      let task = await call<Job>("preview_status", { id });
      if (["queued", "running", "cancelling"].includes(task.status))
        await call("cancel", { id });
      for (
        let i = 0;
        i < 50 && ["queued", "running", "cancelling"].includes(task.status);
        i++
      ) {
        await new Promise((r) => setTimeout(r, 200));
        task = await call<Job>("preview_status", { id });
      }
      if (!["queued", "running", "cancelling"].includes(task.status))
        await call("clear_preview", { id });
    } catch {
      /* Already removed or app closed. */
    }
  };
  useEffect(() => {
    setAfter(null);
    if (!tool || !sources[0] || !tool.preview) {
      setBefore(null);
      return;
    }
    let disposed = false;
    void call<FilePreview>("preview", { path: sources[0] })
      .then((value) => {
        if (!disposed) setBefore(value);
      })
      .catch((e) => {
        if (!disposed) setError(String(e));
      });
    return () => {
      disposed = true;
    };
  }, [tool?.id, sources[0]]);
  useEffect(() => {
    if (
      !previewTask ||
      !["queued", "running", "cancelling"].includes(previewTask.status)
    )
      return;
    const timer = setTimeout(() => {
      void call<Job>("preview_status", { id: previewTask.id })
        .then(async (task) => {
          setPreviewTask(task);
          if (task.status === "completed") {
            const result = await call<FilePreview>("preview", {
              path: task.outputs[0],
            });
            setAfter(result);
            setBusy(false);
            if (task.stats?.warning) setError(String(task.stats.warning));
          } else if (["failed", "cancelled"].includes(task.status)) {
            setError(task.error || "預覽已取消");
            setBusy(false);
          }
        })
        .catch((e) => {
          setError(String(e));
          setBusy(false);
        });
    }, 350);
    return () => clearTimeout(timer);
  }, [previewTask]);
  const open = (item: ToolDefinition) => {
    if (activePreview.current) {
      void cleanup(activePreview.current);
      activePreview.current = null;
    }
    setTool(item);
    setParams(
      Object.fromEntries(
        item.fields.map((f) => [f.key, structuredClone(f.default)]),
      ),
    );
    setSources([]);
    setBefore(null);
    setAfter(null);
    setPreviewTask(null);
    setBusy(false);
    setError("");
    setOutput(outputDir);
  };
  const close = () => {
    if (activePreview.current) {
      void cleanup(activePreview.current);
      activePreview.current = null;
    }
    setTool(null);
    setBusy(false);
  };
  const submit = async (preview: boolean) => {
    if (!tool) return;
    setBusy(true);
    setError("");
    try {
      if (preview && activePreview.current) {
        await cleanup(activePreview.current);
        activePreview.current = null;
      }
      const jobs = await call<Job[]>("enqueue_tool", {
        operation: tool.id,
        sources: preview ? sources.slice(0, 1) : sources,
        params,
        outputDir: output,
        options: defaults,
        preview,
      });
      if (preview) {
        activePreview.current = jobs[0].id;
        setPreviewTask(jobs[0]);
      } else {
        notify("已加入工作佇列");
        close();
      }
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  };
  const update = (key: string, value: unknown) => {
    if (busy) return;
    setAfter(null);
    setParams((old) => ({ ...old, [key]: value }));
  };
  const visible = catalog.filter(
    (t) =>
      t.category === category || (category === "壓縮" && t.category === "檔案"),
  );
  return (
    <>
      {visible.length > 0 && (
        <>
          <h2 className="tools-section-heading">處理工具</h2>
          <div className="tool-grid">
            {visible.map((t) => (
              <button
                key={t.id}
                className="tool-card glass"
                data-material="card"
                disabled={disabled || !t.available}
                onClick={() => open(t)}
                title={t.reason || t.detail}
              >
                <Wrench size={20} />
                <strong>{t.name}</strong>
                <span>{t.reason || t.detail}</span>
              </button>
            ))}
          </div>
        </>
      )}
      <Modal
        open={!!tool}
        onOpenChange={(value) => {
          if (!value) close();
        }}
        title={tool?.name || "工具"}
        description={tool?.detail || ""}
      >
        {tool && (
          <div className="advanced-tool">
            <div className="tool-sources">
              <div className="row between">
                <strong>來源檔案 · {sources.length}</strong>
                <div className="row">
                  <Button
                    compact
                    disabled={busy}
                    onClick={async () => {
                      try {
                        const paths = await pickFiles();
                        setSources((old) => [...new Set([...old, ...paths])]);
                        setError("");
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    <FolderOpen size={17} />
                    加入檔案
                  </Button>
                  {tool.id === "archive.pack" && (
                    <Button
                      compact
                      onClick={async () => {
                        const path = await pickFolder();
                        if (path)
                          setSources((old) => [...new Set([...old, path])]);
                      }}
                    >
                      加入資料夾
                    </Button>
                  )}
                </div>
              </div>
              <ol>
                {sources.map((path, index) => (
                  <li key={path}>
                    <span title={path}>{fileName(path)}</span>
                    <Button
                      compact
                      aria-label={`上移來源 ${index + 1}`}
                      disabled={index === 0 || busy}
                      onClick={() =>
                        setSources((old) => {
                          const next = [...old];
                          [next[index], next[index - 1]] = [
                            next[index - 1],
                            next[index],
                          ];
                          return next;
                        })
                      }
                    >
                      <ArrowUp size={15} />
                    </Button>
                    <Button
                      compact
                      aria-label={`下移來源 ${index + 1}`}
                      disabled={index === sources.length - 1 || busy}
                      onClick={() =>
                        setSources((old) => {
                          const next = [...old];
                          [next[index], next[index + 1]] = [
                            next[index + 1],
                            next[index],
                          ];
                          return next;
                        })
                      }
                    >
                      <ArrowDown size={15} />
                    </Button>
                    <Button
                      compact
                      aria-label={`移除來源 ${index + 1}`}
                      disabled={busy}
                      onClick={() =>
                        setSources((old) => old.filter((p) => p !== path))
                      }
                    >
                      <Trash2 size={15} />
                    </Button>
                  </li>
                ))}
              </ol>
            </div>
            <div className="tool-edit-layout">
              <fieldset className="tool-fields" disabled={busy}>
                {tool.fields.map((f) => {
                  if (
                    ["quality", "minQuality"].includes(f.key) &&
                    params.format === "png"
                  )
                    return null;
                  if (f.type === "region")
                    return (
                      <div key={f.key} className="field">
                        <span>{f.label} · 可直接在預覽拖曳</span>
                        <div className="region-values">
                          {["X", "Y", "寬", "高"].map((label, i) => (
                            <label key={label}>
                              {label} %
                              <input
                                aria-label={`${label} 區域百分比`}
                                type="number"
                                min="0"
                                max="100"
                                step="0.1"
                                value={
                                  Math.round(
                                    (params[f.key] as number[])[i] * 1000,
                                  ) / 10
                                }
                                onChange={(e) => {
                                  const next = [...(params[f.key] as number[])];
                                  next[i] = Number(e.target.value) / 100;
                                  update(f.key, next);
                                }}
                              />
                            </label>
                          ))}
                        </div>
                      </div>
                    );
                  return (
                    <label
                      className={`field ${f.type === "switch" ? "tool-checkbox" : ""}`}
                      key={f.key}
                    >
                      <span>{f.label}</span>
                      {f.type === "select" ? (
                        <select
                          value={String(params[f.key])}
                          onChange={(e) => update(f.key, e.target.value)}
                        >
                          {f.choices?.map((c) => (
                            <option key={c.value} value={c.value}>
                              {c.label}
                            </option>
                          ))}
                        </select>
                      ) : f.type === "switch" ? (
                        <input
                          type="checkbox"
                          checked={!!params[f.key]}
                          onChange={(e) => update(f.key, e.target.checked)}
                        />
                      ) : (
                        <input
                          type={
                            f.type === "color"
                              ? "color"
                              : f.type === "password"
                                ? "password"
                                : f.type === "number"
                                  ? "number"
                                  : "text"
                          }
                          value={String(params[f.key] ?? "")}
                          min={f.min}
                          max={f.max}
                          step={f.type === "number" ? "any" : undefined}
                          autoComplete="off"
                          onChange={(e) =>
                            update(
                              f.key,
                              f.type === "number"
                                ? Number(e.target.value)
                                : e.target.value,
                            )
                          }
                        />
                      )}
                    </label>
                  );
                })}
              </fieldset>
              {tool.preview && (
                <div className="tool-preview">
                  <strong>第一頁／影格預覽</strong>
                  {before?.image ? (
                    tool.fields.some((f) => f.type === "region") ? (
                      <RegionSelector
                        image={before.image}
                        value={params.region as number[]}
                        onChange={(value) => update("region", value)}
                      />
                    ) : (
                      <img
                        className="source-preview"
                        src={before.image}
                        alt="原始檔案預覽"
                      />
                    )
                  ) : (
                    <p className="hint">加入相容檔案後顯示預覽。</p>
                  )}
                  {before && (
                    <p className="hint">
                      {before.name} · {formatSize(before.size)}
                    </p>
                  )}
                </div>
              )}
            </div>
            {before && after && <BeforeAfter before={before} after={after} />}
            {previewTask && busy && (
              <p className="hint" aria-live="polite">
                {previewTask.status === "running"
                  ? "正在實際處理預覽"
                  : "預覽排隊中"}
                {previewTask.progress > 0
                  ? ` · ${Math.floor(previewTask.progress)}%`
                  : ""}
              </p>
            )}
            {error && (
              <p className="error-text" role="alert">
                {error}
              </p>
            )}
            <div className="tool-output">
              <label className="field">
                <span>輸出資料夾</span>
                <button
                  className="path-button"
                  disabled={busy}
                  onClick={async () => {
                    const path = await pickFolder();
                    if (path) setOutput(path);
                  }}
                >
                  <FolderOpen size={18} />
                  {output || "來源資料夾 / File Converter Output"}
                </button>
              </label>
            </div>
            <div className="row between tool-modal-actions">
              <div className="row">
                <Button
                  disabled={busy}
                  onClick={() => {
                    setParams(
                      Object.fromEntries(
                        tool.fields.map((f) => [
                          f.key,
                          structuredClone(f.default),
                        ]),
                      ),
                    );
                    setAfter(null);
                    setError("");
                  }}
                >
                  <RotateCcw size={17} />
                  還原設定
                </Button>
                {tool.preview && (
                  <Button
                    disabled={busy || !sources.length}
                    onClick={() => submit(true)}
                  >
                    <Scan size={17} />
                    處理前後預覽
                  </Button>
                )}
              </div>
              <div className="row">
                <Button onClick={close}>取消</Button>
                <Button
                  variant="primary"
                  disabled={
                    busy ||
                    sources.length < tool.minSources ||
                    (!!tool.maxSources && sources.length > tool.maxSources)
                  }
                  onClick={() => submit(false)}
                >
                  <Play size={17} />
                  加入佇列
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
