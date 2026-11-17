import { useEffect, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  FolderOpen,
  Plus,
  Save,
  Trash2,
  Play,
} from "lucide-react";
import { call, desktop, pickFiles, pickFolder } from "../api";
import type { Options, Registry, HardwareDevice } from "../types";
import { Button } from "./ui";
import { OptionsEditor } from "./OptionsEditor";
import type { ToolDefinition, ToolField } from "./AdvancedTools";
export interface WorkflowStep {
  type: "convert" | "tool";
  target?: string;
  options?: Partial<Options>;
  operation?: string;
  params?: Record<string, unknown>;
  source?: string;
  output?: string;
}
export interface WorkflowConfig {
  name: string;
  source: string;
  steps: WorkflowStep[];
  onError: "abort" | "skip";
  target?: string;
}
export interface AutomationItem {
  id: string;
  kind: "preset" | "workflow" | "watch";
  name: string;
  config: WorkflowConfig;
  sourceDir?: string;
  outputDir?: string;
}
interface AutomationSnapshot {
  items: AutomationItem[];
  states: Record<string, string>;
  logs: {
    watchId: string;
    time: number;
    message: string;
    error?: boolean;
    jobId?: string;
  }[];
  tools: ToolDefinition[];
}
export function Fields({
  fields,
  value,
  onChange,
}: {
  fields: ToolField[];
  value: Record<string, unknown>;
  onChange: (v: Record<string, unknown>) => void;
}) {
  return (
    <div className="automation-fields">
      {fields.map((f) => (
        <label key={f.key}>
          <span>{f.label}</span>
          {f.type === "select" ? (
            <select
              value={String(value[f.key] ?? f.default)}
              onChange={(e) => onChange({ ...value, [f.key]: e.target.value })}
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
              checked={Boolean(value[f.key] ?? f.default)}
              onChange={(e) =>
                onChange({ ...value, [f.key]: e.target.checked })
              }
            />
          ) : f.type === "region" ? (
            <input
              aria-label={f.label}
              value={(
                (value[f.key] as number[]) || (f.default as number[])
              ).join(",")}
              onChange={(e) =>
                onChange({
                  ...value,
                  [f.key]: e.target.value.split(",").map(Number),
                })
              }
            />
          ) : (
            <input
              type={
                f.type === "number"
                  ? "number"
                  : f.type === "color"
                    ? "color"
                    : "text"
              }
              min={f.min}
              max={f.max}
              step="any"
              value={String(value[f.key] ?? f.default)}
              onChange={(e) =>
                onChange({
                  ...value,
                  [f.key]:
                    f.type === "number" ? +e.target.value : e.target.value,
                })
              }
            />
          )}
        </label>
      ))}
    </div>
  );
}
export function AutomationPage({
  registry,
  defaults,
  hardware,
  outputDir,
  notify,
}: {
  registry: Registry;
  defaults: Options;
  hardware: HardwareDevice[];
  outputDir: string;
  notify: (s: string, error?: boolean) => void;
}) {
  const empty: WorkflowConfig = {
    name: "新工作流程",
    source: "png",
    steps: [{ type: "convert", target: "webp", options: { quality: 85 } }],
    onError: "abort",
  };
  const [state, setState] = useState<AutomationSnapshot>({
      items: [],
      states: {},
      logs: [],
      tools: [],
    }),
    [kind, setKind] = useState<AutomationItem["kind"]>("workflow"),
    [id, setId] = useState(""),
    [config, setConfig] = useState(empty),
    [sourceDir, setSourceDir] = useState(""),
    [out, setOut] = useState(outputDir),
    [route, setRoute] = useState<WorkflowConfig | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const refresh = async () => {
    try {
      setState(await call<AutomationSnapshot>("automation"));
    } catch (e) {
      setError(String(e));
    }
  };
  useEffect(() => {
    if (!desktop) return;
    void refresh();
    const timer = setInterval(() => void refresh(), 2000);
    return () => clearInterval(timer);
  }, []);
  const run = async (fn: () => Promise<unknown>, message?: string) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
      if (message) notify(message);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  function change(c: WorkflowConfig) {
    setConfig(c);
    setRoute(null);
  }
  function step(index: number, value: WorkflowStep) {
    change({
      ...config,
      steps: config.steps.map((s, i) => (i === index ? value : s)),
    });
  }
  function reorder(index: number, dir: number) {
    const steps = [...config.steps];
    [steps[index], steps[index + dir]] = [steps[index + dir], steps[index]];
    change({ ...config, steps });
  }
  function newItem(type: AutomationItem["kind"]) {
    setKind(type);
    setId("");
    change({
      ...empty,
      name:
        type === "preset"
          ? "新轉檔預設"
          : type === "watch"
            ? "新資料夾監看"
            : "新工作流程",
    });
    setSourceDir("");
    setError("");
  }
  const engineCategory = (fmt: string) =>
    registry.edges.find((e) => e.source === fmt)?.category || "image";
  return (
    <div className="automation-page">
      <div className="automation-list glass" data-material="card">
        <div className="row between">
          <h2>已保存配置</h2>
          <Button compact onClick={() => newItem(kind)}>
            <Plus size={18} />
            新增
          </Button>
        </div>
        <div className="type-filters">
          {(["workflow", "preset", "watch"] as const).map((k) => (
            <button
              key={k}
              className={kind === k ? "active" : ""}
              onClick={() => newItem(k)}
            >
              {k === "workflow"
                ? "工作流程"
                : k === "preset"
                  ? "轉檔預設"
                  : "監看資料夾"}
            </button>
          ))}
        </div>
        {!state.items.some((i) => i.kind === kind) && (
          <p className="hint">尚無配置，使用右側建立。</p>
        )}
        {state.items
          .filter((i) => i.kind === kind)
          .map((item) => (
            <div
              key={item.id}
              className={`automation-saved ${id === item.id ? "active" : ""}`}
            >
              <button
                onClick={() => {
                  setId(item.id);
                  change(structuredClone(item.config));
                  setSourceDir(item.sourceDir || "");
                  setOut(item.outputDir || outputDir);
                  setError("");
                }}
              >
                <strong>{item.name}</strong>
                <span>
                  {item.config.source.toUpperCase()} →{" "}
                  {item.config.target?.toUpperCase() || "…"}
                  {item.kind === "watch"
                    ? ` · ${{ running: "監看中", paused: "已暫停", stopped: "已停止" }[state.states[item.id] || "stopped"]}`
                    : ""}
                </span>
              </button>
              <Button
                compact
                aria-label={`刪除 ${item.name}`}
                onClick={() =>
                  void run(async () => {
                    await call("delete_automation", { id: item.id });
                    if (id === item.id) newItem(kind);
                  }, "已刪除配置")
                }
              >
                <Trash2 size={17} />
              </Button>
            </div>
          ))}
      </div>
      <section className="automation-editor glass" data-material="settings">
        <div className="row between">
          <h2>
            {kind === "workflow"
              ? "工作流程"
              : kind === "preset"
                ? "轉檔預設"
                : "監看資料夾"}
          </h2>
          <span>{id ? "編輯配置" : "新配置"}</span>
        </div>
        <div className="automation-fields">
          <label>
            名稱
            <input
              value={config.name}
              onChange={(e) => change({ ...config, name: e.target.value })}
            />
          </label>
          <label>
            來源格式
            <select
              value={config.source}
              onChange={(e) => change({ ...config, source: e.target.value })}
            >
              {registry.sources.map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          </label>
          <label>
            步驟錯誤時
            <select
              value={config.onError}
              onChange={(e) =>
                change({
                  ...config,
                  onError: e.target.value as "abort" | "skip",
                })
              }
            >
              <option value="abort">中止此檔案</option>
              <option value="skip">略過失敗步驟，繼續檢查下一步</option>
            </select>
          </label>
        </div>
        <ol className="workflow-steps">
          {config.steps.map((s, i) => {
            const tool = state.tools.find((t) => t.id === s.operation);
            let source = config.source;
            for (const previous of config.steps.slice(0, i)) {
              const t = state.tools.find((t) => t.id === previous.operation);
              source =
                previous.type === "convert"
                  ? previous.target || ""
                  : String(
                      previous.params?.format ||
                        (t?.output === "source" ? source : t?.output || ""),
                    );
            }
            const formats = registry.edges.filter(
              (e) => e.source === source && e.available,
            );
            return (
              <li key={i}>
                <div className="row between">
                  <strong>步驟 {i + 1}</strong>
                  <div className="row">
                    <Button
                      compact
                      disabled={i === 0 || kind === "preset"}
                      aria-label={`上移步驟 ${i + 1}`}
                      onClick={() => reorder(i, -1)}
                    >
                      <ArrowUp size={16} />
                    </Button>
                    <Button
                      compact
                      disabled={
                        i === config.steps.length - 1 || kind === "preset"
                      }
                      aria-label={`下移步驟 ${i + 1}`}
                      onClick={() => reorder(i, 1)}
                    >
                      <ArrowDown size={16} />
                    </Button>
                    <Button
                      compact
                      disabled={config.steps.length === 1 || kind === "preset"}
                      aria-label={`刪除步驟 ${i + 1}`}
                      onClick={() =>
                        change({
                          ...config,
                          steps: config.steps.filter((_, n) => n !== i),
                        })
                      }
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </div>
                <div className="automation-fields">
                  <label>
                    操作
                    <select
                      value={s.type === "convert" ? "convert" : s.operation}
                      onChange={(e) =>
                        step(
                          i,
                          e.target.value === "convert"
                            ? {
                                type: "convert",
                                target: formats[0]?.target || "",
                                options: {},
                              }
                            : {
                                type: "tool",
                                operation: e.target.value,
                                params: {},
                              },
                        )
                      }
                    >
                      <option value="convert">格式轉換</option>
                      {kind !== "preset" &&
                        state.tools
                          .filter(
                            (t) =>
                              t.sources.includes("any") ||
                              t.sources.includes(engineCategory(source)),
                          )
                          .map((t) => (
                            <option value={t.id} key={t.id}>
                              {t.name}
                            </option>
                          ))}
                    </select>
                  </label>
                  {s.type === "convert" && (
                    <label>
                      輸出格式
                      <select
                        value={s.target || ""}
                        onChange={(e) =>
                          step(i, { ...s, target: e.target.value })
                        }
                      >
                        <option value="">請選擇</option>
                        {formats.map((e) => (
                          <option key={e.id} value={e.target}>
                            {e.target.toUpperCase()}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
                {s.type === "convert" ? (
                  <details>
                    <summary>品質與進階設定</summary>
                    <OptionsEditor
                      hardware={hardware}
                      category={engineCategory(source)}
                      format={s.target || ""}
                      value={{ ...defaults, ...s.options }}
                      onChange={(options) => step(i, { ...s, options })}
                    />
                  </details>
                ) : (
                  tool && (
                    <>
                      <p className="hint">{tool.detail}</p>
                      <Fields
                        fields={tool.fields}
                        value={s.params || {}}
                        onChange={(params) => step(i, { ...s, params })}
                      />
                    </>
                  )
                )}
              </li>
            );
          })}
        </ol>
        {kind !== "preset" && (
          <Button
            onClick={() =>
              change({
                ...config,
                steps: [
                  ...config.steps,
                  { type: "convert", target: "", options: {} },
                ],
              })
            }
          >
            <Plus size={18} />
            新增步驟
          </Button>
        )}
        <div className="automation-directories">
          {kind === "watch" && (
            <label>
              監看來源 · 僅處理啟用後新增或修改的直接子檔案
              <Button
                onClick={() =>
                  void run(async () => {
                    const path = await pickFolder();
                    if (path) setSourceDir(path);
                  })
                }
              >
                <FolderOpen size={18} />
                {sourceDir || "明確選擇來源資料夾"}
              </Button>
            </label>
          )}
          <label>
            輸出資料夾
            <Button
              onClick={() =>
                void run(async () => {
                  const path = await pickFolder();
                  if (path) setOut(path);
                })
              }
            >
              <FolderOpen size={18} />
              {out || "來源資料夾 / File Converter Output"}
            </Button>
          </label>
        </div>
        <div className="row wrap">
          <Button
            disabled={busy || !desktop}
            onClick={() =>
              void run(async () =>
                setRoute(
                  await call<WorkflowConfig>("plan_workflow", { config }),
                ),
              )
            }
          >
            預覽／驗證流程
          </Button>
          <Button
            disabled={busy || !desktop}
            onClick={() =>
              void run(async () => {
                const item = await call<AutomationItem>("save_automation", {
                  id: id || undefined,
                  kind,
                  config,
                  sourceDir,
                  outputDir: out,
                });
                setId(item.id);
                setConfig(item.config);
              }, "配置已保存")
            }
          >
            <Save size={18} />
            保存配置
          </Button>
          {kind !== "watch" && (
            <Button
              variant="primary"
              disabled={busy || !desktop}
              onClick={() =>
                void run(async () => {
                  await call("plan_workflow", { config });
                  const paths = await pickFiles();
                  if (paths.length)
                    await call("enqueue_workflow", {
                      config,
                      paths,
                      outputDir: out,
                    });
                }, "已加入佇列，進度可在歷史紀錄查看")
              }
            >
              <Play size={18} />
              選檔並批次執行
            </Button>
          )}
        </div>
        {route && (
          <div className="workflow-route" role="status">
            {route.source.toUpperCase()}
            {route.steps.map((s, i) => (
              <span key={i}>
                {" "}
                →{" "}
                {s.type === "convert"
                  ? s.output?.toUpperCase()
                  : state.tools.find((t) => t.id === s.operation)?.name}{" "}
                ({s.output})
              </span>
            ))}
          </div>
        )}
        {kind === "watch" && (
          <>
            <p className="hint">
              保存後才可開始。等待大小與修改時間穩定、寫入程序關閉檔案後才轉換。來源與輸出不可互相包含。關閉程式即停止；重開後需再次啟用。
            </p>
            <div className="row">
              {(["start", "pause", "stop"] as const).map((action) => (
                <Button
                  key={action}
                  disabled={!id || busy || !desktop}
                  onClick={() =>
                    void run(() => call("watch_action", { id, action }))
                  }
                >
                  {action === "start"
                    ? "開始／恢復"
                    : action === "pause"
                      ? "暫停"
                      : "停止"}
                </Button>
              ))}
            </div>
            <div className="watch-log" aria-live="polite">
              {state.logs
                .filter((l) => l.watchId === id)
                .slice(-40)
                .reverse()
                .map((l, i) => (
                  <p key={i} className={l.error ? "error-text" : ""}>
                    {new Date(l.time * 1000).toLocaleTimeString()} · {l.message}
                  </p>
                ))}
            </div>
          </>
        )}
        {error && (
          <p role="alert" className="error-text">
            {error}
          </p>
        )}
      </section>
    </div>
  );
}
