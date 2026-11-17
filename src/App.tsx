import {ImageEditor} from "./components/ImageEditor";
import {VideoEditor} from "./components/VideoEditor";
import { DownloadPage } from "./components/DownloadPage";
import { AutomationPage } from "./components/AutomationPage";
import { ConversionPresets } from "./components/ConversionPresets";
import { FilePreview } from "./components/FilePreview";
import { AppIcon } from "./components/AppIcon";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
  ArrowLeftRight,
  Download,
  Workflow,
  Wrench,
  PanelLeftClose,
  PanelLeftOpen,
  ArrowRight,
  AudioLines,
  CircleAlert,
  CircleCheck,
  Clock3,
  FileText,
  Film,
  FolderOpen,
  History,
  Image as ImageIcon,
  LoaderCircle,
  Maximize2,
  Minus,
  Plus,
  RotateCcw,
  Search,
  Settings2,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { call, desktop, pickFiles, pickFolder } from "./api";
import { defaults, mergeSettings } from "./defaults";
import type {
  HardwareDevice,
  Draft,
  Registry,
  ConversionMode,
  Engines,
  InputFile,
  Job,
  Page,
  Settings,
  Snapshot,
  Status,
} from "./types";
import { Button, Modal } from "./components/ui";
import { ConversionWorkspace } from "./components/ConversionWorkspace";
import { SettingsPage } from "./components/SettingsPage";

import { ConversionModeBar } from "./components/ConversionModeBar";
import { Toolbox, type Tool } from "./components/Toolbox";
import { conversionIssue } from "./conversion";
const navigation: {
  id: Page | "download" | "workflow";
  label: string;
  icon: LucideIcon;
  phase?: string;
}[] = [
  { id: "converter", label: "轉換檔案", icon: ArrowLeftRight },
  { id: "image-editor", label: "圖片編輯器", icon: ImageIcon },
  { id: "video-editor", label: "影片編輯器", icon: Film },
  { id: "download", label: "網址下載", icon: Download },
  { id: "toolbox", label: "工具箱", icon: Wrench },
  { id: "workflow", label: "自動化工作流程", icon: Workflow },
  { id: "history", label: "歷史紀錄", icon: History },
  { id: "settings", label: "設定", icon: Settings2 },
];
const categories = [
  { id: "video", icon: Film, color: "blue" },
  { id: "audio", icon: AudioLines, color: "violet" },
  { id: "image", icon: ImageIcon, color: "teal" },
  { id: "pdf", icon: FileText, color: "orange" },
  { id: "office", icon: FileText, color: "orange" },
];
const labels: Record<Status, string> = {
  queued: "等待中",
  running: "轉換中",
  cancelling: "取消中",
  completed: "已完成",
  failed: "失敗",
  cancelled: "已取消",
};
const active = (job: Job) =>
  ["queued", "running", "cancelling"].includes(job.status);
const categoryIcon = (category: string) =>
  categories.find((c) => c.id === category)?.icon || FileText;
function fileStyle(category: string) {
  return categories.find((c) => c.id === category)?.color || "orange";
}
function relativeDate(seconds: number) {
  return new Date(seconds * 1000).toLocaleString("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
function rgb(hex: string) {
  return `${parseInt(hex.slice(1, 3), 16)} ${parseInt(hex.slice(3, 5), 16)} ${parseInt(hex.slice(5, 7), 16)}`;
}

export default function App() {
  const [page, setPage] = useState<Page>("converter");
  const [registry, setRegistry] = useState<Registry>({
    version: 1,
    edges: [],
    sources: [],
    adapters: [],
    execution: "",
  });
  const [mode, setMode] = useState<ConversionMode>("auto");
  const [presetSource, setPresetSource] = useState("");
  const [presetTarget, setPresetTarget] = useState("");
  const presetRef = useRef({
    mode,
    source: presetSource,
    target: presetTarget,
  });
  presetRef.current = { mode, source: presetSource, target: presetTarget };
  const [settings, setSettings] = useState<Settings>(defaults);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [engines, setEngines] = useState<Engines>({
    ffmpeg: null,
    ffprobe: null,
    soffice: null,
  });
  const [hardware, setHardware] = useState<HardwareDevice[]>([]);
  const hardwarePending = hardware.some((device) => device.pending);
  useEffect(() => {
    if (!desktop || !hardwarePending) return;
    const timer = setInterval(() => {
      void call<HardwareDevice[]>("hardware")
        .then(setHardware)
        .catch(() => {});
    }, 1500);
    return () => clearInterval(timer);
  }, [hardwarePending]);
  const [dataDir, setDataDir] = useState("");
  const [ready, setReady] = useState(false);
  const [engineError, setEngineError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [importing, setImporting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [details, setDetails] = useState(true);
  const [activityExpanded, setActivityExpanded] = useState(false);
  const [focused, setFocused] = useState<string | null>(null);
  const [toasts, setToasts] = useState<
    { id: number; text: string; error: boolean }[]
  >([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [confirmClear, setConfirmClear] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [previewPaths, setPreviewPaths] = useState<string[] | null>(null);
  const [clock, setClock] = useState(Date.now());
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const saveRevision = useRef(0);
  const lastSaved = useRef("");
  const pageScroll = useRef<HTMLDivElement>(null);
  useEffect(() => {
    pageScroll.current?.scrollTo({ top: 0, left: 0 });
  }, [page]);
  const notify = useCallback((text: string, error = false) => {
    const id = Date.now() + Math.random();
    setToasts([{ id, text, error }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);
  const upsert = useCallback(
    (job: Job) =>
      setJobs((all) => {
        const existing = all.findIndex((j) => j.id === job.id);
        return existing < 0
          ? [job, ...all]
          : all.map((j) => (j.id === job.id ? job : j));
      }),
    [],
  );
  const load = useCallback(async () => {
    setEngineError("");
    try {
      const s = await call<Snapshot>("snapshot");
      const merged = mergeSettings(s.settings);
      setSettings(merged);
      lastSaved.current = JSON.stringify(merged);
      setJobs(s.jobs);
      setRegistry(s.registry);
      void call<HardwareDevice[]>("hardware")
        .then(setHardware)
        .catch(() => {});
      setEngines(s.engines);
      setDataDir(s.dataDir);
      setReady(true);
      if (merged.appearance.nativeMica) {
        try {
          await invoke("native_material", { enabled: true });
        } catch {
          setSettings({
            ...merged,
            appearance: { ...merged.appearance, nativeMica: false },
          });
          notify("Mica 無法使用，已退回 CSS 玻璃", true);
        }
      }
    } catch (e) {
      setEngineError(String(e));
    }
  }, [notify]);
  useEffect(() => {
    if (desktop) void load();
    else {
      try {
        const saved = localStorage.getItem("rai-appearance-preview");
        if (saved) setSettings(mergeSettings(JSON.parse(saved)));
      } catch {
        /* use defaults */
      }
      setReady(true);
    }
  }, [load]);
  useEffect(() => {
    if (!desktop) return;
    let disposed = false;
    const unsubscribers: (() => void)[] = [];
    void (async () => {
      const unlisten = await listen<Job>("engine-job", (e) => {
        if (e.payload.previewOnly) return;
        upsert(e.payload);
        if (e.payload.status === "completed")
          notify(`${e.payload.name} 轉換完成`);
        if (e.payload.status === "failed")
          notify(`${e.payload.name}：${e.payload.error}`, true);
      });
      if (disposed) unlisten();
      else unsubscribers.push(unlisten);
      const stop = await listen<string>("engine-stopped", (e) =>
        setEngineError(e.payload),
      );
      if (disposed) stop();
      else unsubscribers.push(stop);
    })();
    return () => {
      disposed = true;
      unsubscribers.forEach((fn) => fn());
    };
  }, [upsert, notify]);
  useEffect(() => {
    if (!ready) return;
    const revision = ++saveRevision.current;
    const timer = setTimeout(() => {
      const value = JSON.stringify(settings);
      if (value === lastSaved.current) return;
      if (!desktop) {
        try {
          localStorage.setItem("rai-appearance-preview", value);
        } catch {
          notify("外觀預覽儲存空間不足", true);
        }
        return;
      }
      void call("settings", { settings })
        .then(() => {
          if (revision === saveRevision.current) lastSaved.current = value;
        })
        .catch((e) => notify(`設定未能儲存：${String(e)}`, true));
    }, 350);
    return () => clearTimeout(timer);
  }, [settings, ready, notify]);
  // Flush the last revision before closing; no browser beforeunload promises.
  useEffect(() => {
    if (!desktop) return;
    let disposed = false;
    let off: (() => void) | undefined;
    void getCurrentWindow()
      .onCloseRequested(async (event) => {
        event.preventDefault();
        try {
          await call("settings", { settings: settingsRef.current });
          await invoke("shutdown_app");
        } catch (e) {
          notify(`無法儲存設定：${String(e)}`, true);
        }
      })
      .then((fn) => {
        if (disposed) fn();
        else off = fn;
      });
    return () => {
      disposed = true;
      off?.();
    };
  }, [notify]);
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const importPaths = useCallback(
    async (paths: string[], tool?: Tool) => {
      if (!paths.length) return;
      if (
        !tool &&
        presetRef.current.mode === "preset" &&
        (!presetRef.current.source || !presetRef.current.target)
      ) {
        setDragging(false);
        notify("請先選擇來源與目標格式，再匯入檔案", true);
        return;
      }
      setImporting(true);
      try {
        const found = await call<InputFile[]>("inspect", { paths });
        const accepted = found.filter((f) => f.formats.length);
        const unsupported = found.length - accepted.length;
        const next = accepted.map((f) => ({
          ...f,
          id: crypto.randomUUID(),
          format: tool
            ? tool.target
            : presetRef.current.mode === "preset"
              ? presetRef.current.target
              : "",
          expectedSource:
            tool?.source ||
            (presetRef.current.mode === "preset"
              ? presetRef.current.source
              : undefined),
          options: { ...settingsRef.current.defaults, ...tool?.options },
          selected: true,
        }));
        setDrafts((old) => [
          ...old.map((f) => (tool ? { ...f, selected: false } : f)),
          ...next.filter((n) => tool || !old.some((f) => f.path === n.path)),
        ]);
        setPage("converter");
        if (tool?.merge) setMergeOpen(true);
        if (next[0]) setFocused(next[0].id);
        notify(
          `已加入 ${accepted.length} 個檔案${unsupported ? `；${unsupported} 個格式尚未支援` : ""}`,
          !!unsupported,
        );
      } catch (e) {
        notify(String(e), true);
      } finally {
        setImporting(false);
        setDragging(false);
      }
    },
    [notify],
  );
  useEffect(() => {
    if (!desktop || !ready) return;
    let disposed = false;
    let off: (() => void) | undefined;
    const take = async () => {
      try {
        const requests =
          await invoke<{ paths: string[]; target: string }[]>(
            "take_open_requests",
          );
        for (const request of requests) {
          // Shell actions only stage files and target selection. Starting a conversion remains explicit.
          if (request.target)
            await importPaths(request.paths, {
              target: request.target,
            } as Tool);
          else await importPaths(request.paths);
        }
      } catch (e) {
        notify(String(e), true);
      }
    };
    void listen("open-files-ready", () => void take()).then((fn) => {
      if (disposed) fn();
      else off = fn;
      void take();
    });
    return () => {
      disposed = true;
      off?.();
    };
  }, [ready, importPaths, notify]);
  useEffect(() => {
    if (!desktop) return;
    let disposed = false;
    let off: (() => void) | undefined;
    void getCurrentWindow()
      .onDragDropEvent((e) => {
        if (e.payload.type === "over" || e.payload.type === "enter")
          setDragging(true);
        else if (e.payload.type === "leave") setDragging(false);
        else if (e.payload.type === "drop") void importPaths(e.payload.paths);
      })
      .then((fn) => {
        if (disposed) fn();
        else off = fn;
      });
    return () => {
      disposed = true;
      off?.();
    };
  }, [importPaths]);
  const addFiles = async () => {
    try {
      await importPaths(await pickFiles());
    } catch (e) {
      notify(String(e), true);
    }
  };
  const act = async (method: string, args: unknown = {}) => {
    try {
      return await call(method, args);
    } catch (e) {
      notify(String(e), true);
      return null;
    }
  };
  const refreshEngines = async () => {
    try {
      const detected = await call<Engines>("engines");
      setEngines(detected);
      void call<HardwareDevice[]>("hardware", { refresh: true })
        .then(setHardware)
        .catch(() => {});
      setRegistry(await call<Registry>("registry"));
      setDrafts((old) =>
        old.map((f) => ({
          ...f,
          available:
            f.category === "office"
              ? !!detected.soffice
              : ["video", "audio"].includes(f.category)
                ? !!detected.ffmpeg && !!detected.ffprobe
                : true,
        })),
      );
      notify("本機引擎已重新檢測");
    } catch (e) {
      notify(String(e), true);
    }
  };
  const submit = async (merge = false) => {
    const selected = drafts.filter((f) => f.selected && f.available);
    if (!selected.length) return;
    if (!merge && selected.some((f) => conversionIssue(f, registry))) {
      notify("請先為所有勾選檔案設定有效的轉換選項", true);
      return;
    }
    setSubmitting(true);
    try {
      const specs = merge
        ? [
            {
              sources: selected.map((f) => f.path),
              format: "pdf",
              options: settings.defaults,
              outputDir: settings.outputDir,
            },
          ]
        : selected.map((f) => ({
            sources: [f.path],
            format: f.format,
            options: f.options,
            outputDir: settings.outputDir,
          }));
      const created = await call<Job[]>("enqueue", { jobs: specs });
      created.forEach(upsert);
      setDrafts((old) =>
        old.filter((f) => !selected.some((s) => s.id === f.id)),
      );
      setMergeOpen(false);
      notify(`已建立 ${created.length} 個轉檔任務`);
    } catch (e) {
      notify(String(e), true);
    } finally {
      setSubmitting(false);
    }
  };
  const retry = async (job: Job) => {
    const result = await act("retry", { id: job.id });
    if (result) (result as Job[]).forEach(upsert);
  };
  const clear = async () => {
    const result = await act("clear");
    if (result) setJobs((old) => old.filter(active));
    setConfirmClear(false);
  };
  const chooseOutput = async () => {
    try {
      const path = await pickFolder();
      if (path) setSettings({ ...settings, outputDir: path });
    } catch (e) {
      notify(String(e), true);
    }
  };
  const reorder = (index: number, direction: number) =>
    setDrafts((old) => {
      const next = [...old];
      const target = index + direction;
      if (target < 0 || target >= next.length) return old;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  const selected = drafts.filter((f) => f.selected);
  const focusedFile = drafts.find((f) => f.id === focused) || drafts[0];
  const running = jobs.filter((j) => active(j));
  const completed = jobs.filter((j) => j.status === "completed");
  const failed = jobs.filter((j) => j.status === "failed");
  const sortedJobs = [...jobs].sort((a, b) => b.created - a.created);
  const totalProgress = running.length
    ? running.reduce((s, j) => s + j.progress, 0) / running.length
    : 0;
  const runningWithEta = running.filter(
    (j) =>
      j.status === "running" &&
      j.progress > 2 &&
      j.started &&
      clock / 1000 - j.started > 2,
  );
  const eta =
    runningWithEta.length ===
      running.filter((j) => j.status === "running").length &&
    runningWithEta.length &&
    !running.some((j) => j.status === "queued")
      ? Math.ceil(
          Math.max(
            ...runningWithEta.map(
              (j) =>
                ((clock / 1000 - j.started!) * (100 - j.progress)) / j.progress,
            ),
          ),
        )
      : null;
  const a = settings.appearance;
  const vars: Record<string, string | number> = {
    "--accent": a.accent,
    "--accent-rgb": rgb(a.accent),
  };
  for (const [key, m] of Object.entries(a.materials)) {
    vars[`--${key}-rgb`] = rgb(m.tint);
    vars[`--${key}-alpha`] = m.opacity / 100;
    vars[`--${key}-blur`] = `${m.blur}px`;
    vars[`--${key}-border`] = m.border / 100;
    vars[`--${key}-shadow`] = m.shadow / 100;
  }
  const theme = a.mode === "system" ? "system" : a.mode;
  const dropzone = () => (
    <button
      className={`dropzone glass ${dragging ? "dragging" : ""}`}
      data-material="card"
      onClick={addFiles}
      disabled={importing || !desktop || !!engineError}
      aria-label="選擇或拖入檔案"
    >
      <span className="upload-symbol">
        {importing ? (
          <LoaderCircle className="spin" size={28} />
        ) : (
          <Upload size={28} />
        )}
      </span>
      <span>
        <strong>
          {importing
            ? "正在讀取檔案…"
            : dragging
              ? "放開以加入檔案"
              : "將檔案拖到這裡"}
        </strong>
        <span className="drop-subtitle">
          影片、音訊、圖片、PDF、Office · 支援多檔加入
        </span>
      </span>
      <span className="pick-files-label">
        <Plus size={19} />
        選擇檔案
      </span>
    </button>
  );
  const jobRow = (job: Job) => {
    const Icon = categoryIcon(job.category);
    return (
      <motion.div
        layout={jobs.length < 80}
        key={job.id}
        className={`job-row ${job.status === "failed" ? "error-row" : ""}`}
        initial={false}
      >
        <span className={`file-icon ${fileStyle(job.category)}`}>
          <Icon size={21} />
        </span>
        <div className="job-main">
          <strong title={job.name}>{job.name}</strong>
          <span>
            {job.format.toUpperCase()}
            <span className="dot-separator">·</span>
            {relativeDate(job.created)}
          </span>
          {job.stats?.encoder && (
            <span>
              {job.stats.encoder} · {job.stats.fps || 0} FPS ·{" "}
              {job.stats.speed || "處理中"}
            </span>
          )}
          {job.stats?.hardwareFallback && (
            <p className="hint">{job.stats.hardwareFallback}</p>
          )}
          {job.kind === "download" && job.stats && (
            <span>
              {String(job.stats.phase || "下載")} ·{" "}
              {typeof job.stats.downloadedBytes === "number"
                ? `${(job.stats.downloadedBytes / 1024 ** 2).toFixed(1)} MB`
                : ""}
              {typeof job.stats.downloadSpeed === "number"
                ? ` · ${(job.stats.downloadSpeed / 1024 ** 2).toFixed(2)} MB/s`
                : ""}
              {typeof job.stats.downloadEta === "number"
                ? ` · 剩餘 ${Math.ceil(job.stats.downloadEta)} 秒`
                : ""}
            </span>
          )}
          {job.stats?.warning && (
            <p className="error-text">{job.stats.warning}</p>
          )}
          {job.error && <p className="error-text">{job.error}</p>}
          {active(job) && (
            <div className="progress-track">
              <motion.i
                initial={false}
                animate={{ width: `${job.progress}%` }}
                transition={{ duration: 0.25 }}
              />
            </div>
          )}
        </div>
        <span className={`status ${job.status}`}>
          {job.status === "running" ? (
            <LoaderCircle size={13} className="spin" />
          ) : job.status === "completed" ? (
            <CircleCheck size={13} />
          ) : job.status === "failed" ? (
            <CircleAlert size={13} />
          ) : (
            <Clock3 size={13} />
          )}{" "}
          {labels[job.status]}
          {job.status === "running" && ` ${Math.floor(job.progress)}%`}
        </span>
        <div className="job-actions">
          {active(job) ? (
            <Button
              compact
              aria-label={`取消 ${job.name}`}
              disabled={job.status === "cancelling"}
              onClick={() => act("cancel", { id: job.id })}
            >
              <X size={16} />
            </Button>
          ) : (
            <Button
              compact
              aria-label={`重新轉換 ${job.name}`}
              onClick={() => retry(job)}
            >
              <RotateCcw size={15} />
            </Button>
          )}
          {job.status === "completed" && (
            <Button
              compact
              aria-label={`預覽與比較 ${job.name}`}
              onClick={() =>
                setPreviewPaths(
                  job.sources.length
                    ? [job.sources[0], job.outputs[0]]
                    : [job.outputs[0]],
                )
              }
            >
              預覽
            </Button>
          )}
          {job.status === "completed" && (
            <Button
              compact
              aria-label={`開啟 ${job.name} 輸出資料夾`}
              onClick={() => act("open_output", { id: job.id })}
            >
              <FolderOpen size={16} />
            </Button>
          )}
        </div>
      </motion.div>
    );
  };
  return (
    <MotionConfig
      reducedMotion={settings.reducedMotion ? "always" : "user"}
      transition={{ duration: 0.2 }}
    >
      <div
        className={`app ${settings.sidebarCollapsed ? "sidebar-collapsed" : ""} theme-${theme} ${a.nativeMica ? "native-mica" : ""} ${settings.reducedMotion ? "reduced-motion" : ""}`}
        style={vars as CSSProperties}
      >
        <div
          className={`wallpaper wallpaper-${a.background}`}
          style={{
            backgroundColor: a.background === "solid" ? a.color : undefined,
            backgroundImage:
              a.background === "image" && a.image
                ? `url(${a.image})`
                : undefined,
            backgroundSize: a.fit,
            backgroundPosition: `${a.positionX}% ${a.positionY}%`,
            opacity: a.background === "image" ? a.imageOpacity / 100 : 1,
            filter:
              [
                a.brightness !== 100 ? `brightness(${a.brightness}%)` : "",
                a.backgroundBlur > 0 ? `blur(${a.backgroundBlur}px)` : "",
              ]
                .filter(Boolean)
                .join(" ") || "none",
            transform: a.scale === 100 ? "none" : `scale(${a.scale / 100})`,
          }}
        />
        <div
          className="wallpaper-mask"
          style={{ background: `rgb(0 0 0 / ${a.overlay / 100})` }}
        />
        <header className="titlebar" data-tauri-drag-region>
          <span data-tauri-drag-region>
            <AppIcon size={18} />
            File Converter
          </span>
          <div className="window-controls">
            <button
              aria-label="最小化"
              disabled={!desktop}
              onClick={() => getCurrentWindow().minimize()}
            >
              <Minus size={16} />
            </button>
            <button
              aria-label="最大化或還原"
              disabled={!desktop}
              onClick={() => getCurrentWindow().toggleMaximize()}
            >
              <Maximize2 size={15} />
            </button>
            <button
              aria-label="關閉應用程式"
              disabled={!desktop}
              onClick={() => getCurrentWindow().close()}
            >
              <X size={18} />
            </button>
          </div>
        </header>
        <div className="app-body">
          <aside className="sidebar glass" data-material="sidebar">
            <div className="brand">
              <AppIcon />
              <strong>File Converter</strong>
            </div>
            <Button
              compact
              className="sidebar-toggle"
              aria-label={
                settings.sidebarCollapsed ? "展開側邊欄" : "收合側邊欄"
              }
              onClick={() =>
                setSettings({
                  ...settings,
                  sidebarCollapsed: !settings.sidebarCollapsed,
                })
              }
            >
              {settings.sidebarCollapsed ? (
                <PanelLeftOpen size={19} />
              ) : (
                <PanelLeftClose size={19} />
              )}
              <span>收合導覽</span>
            </Button>
            <nav aria-label="主要導覽">
              {navigation.map((item) => (
                <button
                  key={item.id}
                  aria-label={item.label}
                  className={`nav-item ${page === item.id ? "active" : ""}`}
                  disabled={!!item.phase}
                  title={
                    item.phase
                      ? `${item.label} · ${item.phase} 尚未實作`
                      : item.label
                  }
                  onClick={() => {
                    if (!item.phase) setPage(item.id as Page);
                  }}
                >
                  {page === item.id && (
                    <motion.span
                      className="nav-active-bg"
                      layoutId="nav-active"
                      transition={{
                        type: "spring",
                        stiffness: 420,
                        damping: 36,
                      }}
                    />
                  )}
                  <item.icon size={21} />
                  <span>{item.label}</span>
                  {item.phase && (
                    <small className="nav-phase">{item.phase}</small>
                  )}
                  {item.id === "converter" &&
                    drafts.length + running.length > 0 && (
                      <b>{drafts.length + running.length}</b>
                    )}
                </button>
              ))}
            </nav>
            <div className="sidebar-bottom">
              <span>v1.0.0-rc.1</span>
              <Button
                compact
                aria-label="開啟個人化設定"
                onClick={() => setPage("settings")}
              >
                <Settings2 size={19} />
              </Button>
            </div>
          </aside>
          <main className="main-panel" data-material="main">
            <div
              ref={pageScroll}
              className={`page-scroll ${page === "converter" ? "converter-page" : ""}`}
            >
              <div className="page-heading">
                <div>
                  <h1>
                    {page === "converter"
                      ? "File Converter"
                      : page === "video-editor"
                        ? "影片編輯器"
                      : page === "image-editor" ? "圖片編輯器"
                      : page === "history"
                        ? "轉換紀錄"
                        : page === "workflow"
                          ? "自動化工作流程"
                          : page === "download"
                            ? "網址下載"
                            : page === "toolbox"
                              ? "工具箱"
                              : "設定"}
                  </h1>
                  <p>
                    {page === "converter"
                      ? "加入檔案，選擇輸出格式後開始轉換。"
                      : page === "history"
                        ? "搜尋已完成、失敗或取消的任務。"
                        : page === "download"
                          ? "解析實際畫質與字幕，選擇項目後下載。"
                          : page === "workflow"
                            ? "保存轉檔配置、串連處理步驟與監看指定資料夾。"
                            : page === "toolbox"
                              ? "選擇工具、匯入檔案，並檢查輸出設定。"
                              : "調整外觀、轉檔偏好與引擎設定。"}
                  </p>
                </div>
                {page === "converter" && (
                  <Button
                    onClick={addFiles}
                    disabled={!desktop || importing || !!engineError}
                  >
                    <Plus size={19} />
                    加入檔案
                  </Button>
                )}
              </div>
              {!desktop && (
                <div className="preview-banner">
                  <CircleAlert size={18} />
                  <span>
                    瀏覽器外觀預覽；本機檔案操作請使用 Windows 桌面版。
                  </span>
                </div>
              )}
              {engineError && (
                <div className="engine-banner">
                  <CircleAlert size={20} />
                  <span>{engineError}</span>
                  <Button compact onClick={load}>
                    <RotateCcw size={17} />
                    重新連線
                  </Button>
                </div>
              )}
              <div hidden={page!=="image-editor"}><ImageEditor notify={notify}/></div>
              <div hidden={page!=="video-editor"}><VideoEditor hardware={hardware} notify={notify}/></div>
              <AnimatePresence mode="wait">
                <motion.div
                  className="page-transition"
                  key={page}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -3 }}
                  transition={{ duration: 0.16 }}
                >
                  {page === "converter" && (
                    <ConversionWorkspace
                      hardware={hardware}
                      modeBar={
                        <>
                          <ConversionPresets
                            focused={focusedFile}
                            notify={notify}
                            onApply={(source, target, options) => {
                              setDrafts((old) =>
                                old.map((f) =>
                                  f.selected &&
                                  f.extension === source &&
                                  f.formats.includes(target)
                                    ? {
                                        ...f,
                                        format: target,
                                        options: { ...f.options, ...options },
                                      }
                                    : f,
                                ),
                              );
                              notify("已套用至來源格式相符的勾選檔案");
                            }}
                          />
                          <ConversionModeBar
                            mode={mode}
                            setMode={(v) => {
                              setMode(v);
                              if (v === "auto")
                                setDrafts((old) =>
                                  old.map((f) => ({
                                    ...f,
                                    expectedSource: undefined,
                                  })),
                                );
                            }}
                            source={presetSource}
                            target={presetTarget}
                            setSource={(v) => {
                              setPresetSource(v);
                              setPresetTarget("");
                            }}
                            setTarget={setPresetTarget}
                            registry={registry}
                            drafts={drafts}
                            apply={(target, source) => {
                              setDrafts((old) =>
                                old.map((f) => {
                                  if (
                                    !f.selected ||
                                    !f.formats.includes(target) ||
                                    (source && f.extension !== source)
                                  )
                                    return f;
                                  return {
                                    ...f,
                                    format: target,
                                    expectedSource: source,
                                  };
                                }),
                              );
                              notify(
                                "已套用至相容的勾選檔案；不相容的檔案保留原設定",
                              );
                            }}
                          />
                        </>
                      }
                      registry={registry}
                      totalProgress={totalProgress}
                      runningCount={running.length}
                      cancelAll={() =>
                        running.forEach((j) => {
                          if (j.status !== "cancelling")
                            void act("cancel", { id: j.id });
                        })
                      }
                      drafts={drafts}
                      setDrafts={setDrafts}
                      focusedFile={focusedFile}
                      setFocused={setFocused}
                      details={details}
                      setDetails={setDetails}
                      dropzone={dropzone()}
                      outputDir={settings.outputDir}
                      chooseOutput={chooseOutput}
                      canUseDesktop={desktop}
                      submitting={submitting}
                      ready={ready}
                      hasError={!!engineError}
                      submit={() => submit()}
                      merge={() => setMergeOpen(true)}
                      reorder={reorder}
                      notify={notify}
                      activity={
                        jobs.length > 0 ? (
                          <section
                            className={`queue-panel glass activity-panel ${drafts.length && !activityExpanded ? "compact-activity" : ""}`}
                            data-material="card"
                            aria-label="轉換進度與狀態"
                          >
                            <div className="queue-heading row between">
                              <h2>
                                轉換進度
                                {running.length > 0 && (
                                  <span className="count-badge">
                                    {running.length} 個處理中
                                  </span>
                                )}
                              </h2>
                              <div className="row">
                                {drafts.length > 0 && (
                                  <Button
                                    compact
                                    onClick={() =>
                                      setActivityExpanded(!activityExpanded)
                                    }
                                    aria-label={
                                      activityExpanded
                                        ? "收合轉換進度"
                                        : "展開轉換進度"
                                    }
                                  >
                                    {activityExpanded ? "收合進度" : "展開進度"}
                                  </Button>
                                )}
                                <Button
                                  compact
                                  disabled={!jobs.some((j) => !active(j))}
                                  onClick={() => setConfirmClear(true)}
                                >
                                  <Trash2 size={17} />
                                  清除已結束
                                </Button>
                                <Button
                                  compact
                                  onClick={() => setPage("history")}
                                >
                                  全部紀錄
                                  <ArrowRight size={16} />
                                </Button>
                              </div>
                            </div>
                            <div className="activity-list">
                              {[
                                ...sortedJobs.filter(active),
                                ...sortedJobs.filter((j) => !active(j)),
                              ]
                                .slice(0, 100)
                                .map(jobRow)}
                            </div>
                          </section>
                        ) : null
                      }
                    />
                  )}
                  {page === "download" && (
                    <DownloadPage
                      disabled={
                        !desktop || !ready || !!engineError || !engines.ytdlp
                      }
                      outputDir={settings.downloadDir}
                      onDirectory={(path) =>
                        setSettings((old) => ({ ...old, downloadDir: path }))
                      }
                      notify={notify}
                    />
                  )}
                  {page === "workflow" && (
                    <AutomationPage
                      registry={registry}
                      defaults={settings.defaults}
                      hardware={hardware}
                      outputDir={settings.outputDir}
                      notify={notify}
                    />
                  )}
                  {page === "toolbox" && (
                    <Toolbox
                      outputDir={settings.outputDir}
                      defaults={settings.defaults}
                      notify={notify}
                      registry={registry}
                      disabled={
                        !desktop || !ready || importing || !!engineError
                      }
                      run={async (tool) => {
                        try {
                          const paths = await pickFiles();
                          if (!paths.length) return;
                          const found = await call<InputFile[]>("inspect", {
                            paths,
                          });
                          const category = {
                            PDF: "pdf",
                            圖片: "image",
                            影片: "video",
                            音訊: "audio",
                            文件: "office",
                            電子書: "ebook",
                          }[tool.category];
                          const valid = found.filter((f) =>
                            tool.merge
                              ? ["image", "pdf"].includes(f.category) &&
                                (tool.category !== "圖片" ||
                                  f.category === "image")
                              : f.category === category &&
                                f.formats.includes(tool.target),
                          );
                          if (valid.length !== found.length)
                            notify("已略過不符合此工具的檔案", true);
                          if (!valid.length) return;
                          setMode("auto");
                          await importPaths(
                            valid.map((f) => f.path),
                            tool,
                          );
                        } catch (e) {
                          notify(String(e), true);
                        }
                      }}
                    />
                  )}
                  {page === "history" && (
                    <div className="history-page">
                      <div className="history-summary">
                        <span>共 {jobs.length} 筆</span>
                        <span>已完成 {completed.length}</span>
                        <span>處理中 {running.length}</span>
                        <span>失敗 {failed.length}</span>
                      </div>
                      <div className="history-toolbar">
                        <label className="search-box">
                          <Search size={20} />
                          <input
                            aria-label="搜尋轉換紀錄"
                            placeholder="搜尋檔名或格式"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                          />
                        </label>
                        <select
                          aria-label="篩選任務狀態"
                          value={filter}
                          onChange={(e) => setFilter(e.target.value)}
                        >
                          <option value="all">所有狀態</option>
                          {Object.entries(labels).map(([id, label]) => (
                            <option key={id} value={id}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <Button
                          disabled={!jobs.some((j) => !active(j))}
                          onClick={() => setConfirmClear(true)}
                        >
                          <Trash2 size={18} />
                          清除紀錄
                        </Button>
                      </div>
                      <div className="history-list glass" data-material="card">
                        {sortedJobs.filter(
                          (j) =>
                            (filter === "all" || j.status === filter) &&
                            `${j.name} ${j.format}`
                              .toLowerCase()
                              .includes(search.toLowerCase()),
                        ).length ? (
                          sortedJobs
                            .filter(
                              (j) =>
                                (filter === "all" || j.status === filter) &&
                                `${j.name} ${j.format}`
                                  .toLowerCase()
                                  .includes(search.toLowerCase()),
                            )
                            .slice(0, 300)
                            .map(jobRow)
                        ) : (
                          <div className="history-empty">
                            <History size={30} />
                            <h2>
                              {jobs.length
                                ? "沒有符合條件的紀錄"
                                : "尚無轉換紀錄"}
                            </h2>
                            <Button onClick={() => setPage("converter")}>
                              <Plus size={18} />
                              加入檔案
                            </Button>
                          </div>
                        )}
                      </div>
                      <p className="hint">
                        每次最多顯示 300 筆，可使用搜尋查找較早紀錄。
                      </p>
                    </div>
                  )}
                  {page === "settings" && (
                    <SettingsPage
                      settings={settings}
                      setSettings={setSettings}
                      engines={engines}
                      refresh={refreshEngines}
                      notify={notify}
                      dataDir={dataDir}
                    />
                  )}
                </motion.div>
              </AnimatePresence>
            </div>
            <footer className="workspace-footer">
              <span>
                <i
                  className={`status-dot ${engineError ? "amber" : "green"}`}
                />
                {!desktop
                  ? "外觀預覽"
                  : engineError
                    ? "引擎離線"
                    : ready
                      ? "準備就緒"
                      : "正在連接引擎…"}
              </span>
              {running.length > 0 && (
                <span>
                  <LoaderCircle size={16} className="spin" />
                  {running.length} 個任務 · 平均 {Math.floor(totalProgress)}%
                  {eta !== null &&
                    ` · 估計 ${eta < 60 ? `${eta} 秒` : `${Math.ceil(eta / 60)} 分鐘`}`}
                </span>
              )}
            </footer>
          </main>
        </div>
        <AnimatePresence>
          {dragging && (
            <motion.div
              className="drag-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Upload size={42} />
              <h2>放開以加入檔案</h2>
            </motion.div>
          )}
        </AnimatePresence>
        <div className="toast-stack" aria-live="polite">
          <AnimatePresence>
            {toasts.map((t) => (
              <motion.div
                key={t.id}
                className={`toast glass ${t.error ? "error" : ""}`}
                data-material="modal"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 12 }}
              >
                {t.error ? (
                  <CircleAlert size={20} />
                ) : (
                  <CircleCheck size={20} />
                )}
                <span>{t.text}</span>
                <button
                  aria-label="關閉通知"
                  onClick={() =>
                    setToasts((old) => old.filter((x) => x.id !== t.id))
                  }
                >
                  <X size={18} />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
        {previewPaths && (
          <FilePreview
            paths={previewPaths}
            onClose={() => setPreviewPaths(null)}
          />
        )}
        <Modal
          open={confirmClear}
          onOpenChange={setConfirmClear}
          title="清除已結束的轉換紀錄？"
          description="來源與輸出檔案不會刪除，執行中的任務會保留。"
        >
          <div className="row end">
            <Button onClick={() => setConfirmClear(false)}>取消</Button>
            <Button variant="danger" onClick={clear}>
              <Trash2 size={18} />
              清除紀錄
            </Button>
          </div>
        </Modal>
        <Modal
          open={mergeOpen}
          onOpenChange={setMergeOpen}
          title="合併 PDF"
          description="依目前清單順序，合併已勾選的圖片與 PDF。"
        >
          <p>已選取 {selected.length} 個檔案</p>
          <ol className="merge-list">
            {selected.map((f) => (
              <li key={f.id}>{f.name}</li>
            ))}
          </ol>
          <Button
            variant="primary"
            disabled={submitting}
            onClick={() => submit(true)}
          >
            <FileText size={18} />
            合併並輸出 PDF
          </Button>
        </Modal>
      </div>
    </MotionConfig>
  );
}
