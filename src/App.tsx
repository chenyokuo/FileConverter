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
  ArrowDown,
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowRight,
  ArrowUp,
  AudioLines,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  Clock3,
  File,
  FileImage,
  FileText,
  Film,
  FolderOpen,
  History,
  Image as ImageIcon,
  LayoutDashboard,
  LoaderCircle,
  Maximize2,
  Minus,
  PanelRightClose,
  PanelRightOpen,
  Play,
  Plus,
  RotateCcw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { call, desktop, pickFiles, pickFolder } from "./api";
import { defaults, mergeSettings } from "./defaults";
import type {
  Draft,
  Engines,
  InputFile,
  Job,
  MaterialName,
  Page,
  Settings,
  Snapshot,
  Status,
} from "./types";
import { Button, Modal } from "./components/ui";
import { OptionsEditor } from "./components/OptionsEditor";
import { SettingsPage } from "./components/SettingsPage";

const navigation: {
  id: Page;
  label: string;
  english: string;
  icon: LucideIcon;
}[] = [
  {
    id: "dashboard",
    label: "工作概覽",
    english: "Overview",
    icon: LayoutDashboard,
  },
  {
    id: "converter",
    label: "檔案轉換",
    english: "Converter",
    icon: ArrowLeftRight,
  },
  { id: "history", label: "轉換紀錄", english: "History", icon: History },
  { id: "settings", label: "設定", english: "Settings", icon: Settings2 },
];
const categories = [
  {
    id: "video",
    name: "影片",
    formats: "MP4, MOV, MKV…",
    icon: Film,
    color: "blue",
  },
  {
    id: "audio",
    name: "音訊",
    formats: "MP3, WAV, FLAC…",
    icon: AudioLines,
    color: "violet",
  },
  {
    id: "image",
    name: "圖片",
    formats: "JPG, PNG, WebP…",
    icon: ImageIcon,
    color: "teal",
  },
  {
    id: "pdf",
    name: "PDF 與文件",
    formats: "PDF, DOCX, XLSX…",
    icon: FileText,
    color: "orange",
  },
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
const bytes = (size: number) =>
  size < 1024
    ? `${size} B`
    : size < 1024 ** 2
      ? `${(size / 1024).toFixed(1)} KB`
      : size < 1024 ** 3
        ? `${(size / 1024 ** 2).toFixed(1)} MB`
        : `${(size / 1024 ** 3).toFixed(2)} GB`;
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
  const [page, setPage] = useState<Page>("dashboard");
  const [settings, setSettings] = useState<Settings>(defaults);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [engines, setEngines] = useState<Engines>({
    ffmpeg: null,
    ffprobe: null,
    soffice: null,
  });
  const [dataDir, setDataDir] = useState("");
  const [ready, setReady] = useState(false);
  const [engineError, setEngineError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [importing, setImporting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [details, setDetails] = useState(true);
  const [focused, setFocused] = useState<string | null>(null);
  const [toasts, setToasts] = useState<
    { id: number; text: string; error: boolean }[]
  >([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [confirmClear, setConfirmClear] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [clock, setClock] = useState(Date.now());
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const saveRevision = useRef(0);
  const lastSaved = useRef("");
  const notify = useCallback((text: string, error = false) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-3), { id, text, error }]);
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
          await getCurrentWindow().destroy();
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
    async (paths: string[]) => {
      if (!paths.length) return;
      setImporting(true);
      try {
        const found = await call<InputFile[]>("inspect", { paths });
        const accepted = found.filter((f) => f.formats.length);
        const unsupported = found.length - accepted.length;
        const next = accepted.map((f) => ({
          ...f,
          id: crypto.randomUUID(),
          format:
            f.category === "video"
              ? "mp4"
              : f.category === "audio"
                ? "mp3"
                : f.category === "image"
                  ? "webp"
                  : "pdf",
          options: { ...settingsRef.current.defaults },
          selected: true,
        }));
        setDrafts((old) => [
          ...old,
          ...next.filter((n) => !old.some((f) => f.path === n.path)),
        ]);
        setPage("converter");
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
      setEngines(await call<Engines>("engines"));
      notify("本機引擎已重新檢測");
    } catch (e) {
      notify(String(e), true);
    }
  };
  const submit = async (merge = false) => {
    const selected = drafts.filter((f) => f.selected && f.available);
    if (!selected.length) return;
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
  const dropzone = (compact = false) => (
    <button
      className={`dropzone glass ${dragging ? "dragging" : ""} ${compact ? "small" : ""}`}
      data-material="card"
      onClick={addFiles}
      disabled={importing || !desktop || !!engineError}
      aria-label="選擇或拖入檔案"
    >
      <span className="upload-symbol">
        {importing ? (
          <LoaderCircle className="spin" size={24} />
        ) : (
          <Upload size={24} />
        )}
      </span>
      <span>
        <strong>
          {importing
            ? "正在讀取檔案…"
            : dragging
              ? "放開，交給 RAI。"
              : "把檔案拖到這裡，剩下的交給 RAI。"}
        </strong>
        <span className="drop-subtitle">
          或點擊選擇檔案 <span className="keycap">＋</span>
        </span>
      </span>
      {!compact && (
        <span className="drop-formats">
          影片、音訊、圖片、PDF 與 Office 文件
          <span>多檔批次處理 · 原始檔案安全保留</span>
        </span>
      )}
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
  const currentNav = navigation.find((n) => n.id === page)!;
  return (
    <MotionConfig
      reducedMotion={settings.reducedMotion ? "always" : "user"}
      transition={{ duration: 0.2 }}
    >
      <div
        className={`app theme-${theme} ${a.nativeMica ? "native-mica" : ""} ${settings.reducedMotion ? "reduced-motion" : ""}`}
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
            filter: `brightness(${a.brightness}%) blur(${a.backgroundBlur}px)`,
            transform: `scale(${a.scale / 100})`,
          }}
        />
        <div
          className="wallpaper-mask"
          style={{ background: `rgb(0 0 0 / ${a.overlay / 100})` }}
        />
        <header className="titlebar" data-tauri-drag-region>
          <span data-tauri-drag-region>
            <span className="title-dot" />
            RAI Converter{" "}
            <span className="title-edition">/ Premium Glass Edition</span>
          </span>
          <div className="window-controls">
            <button
              aria-label="最小化"
              disabled={!desktop}
              onClick={() => getCurrentWindow().minimize()}
            >
              <Minus size={14} />
            </button>
            <button
              aria-label="最大化或還原"
              disabled={!desktop}
              onClick={() => getCurrentWindow().toggleMaximize()}
            >
              <Maximize2 size={12} />
            </button>
            <button
              aria-label="關閉應用程式"
              disabled={!desktop}
              onClick={() => getCurrentWindow().close()}
            >
              <X size={16} />
            </button>
          </div>
        </header>
        <div className="app-body">
          <aside className="sidebar glass" data-material="sidebar">
            <div className="brand">
              <div className="brand-mark">
                R<span />
              </div>
              <div>
                <strong>
                  RAI<span>Converter</span>
                </strong>
                <small>PREMIUM GLASS</small>
              </div>
            </div>
            <span className="nav-label">WORKSPACE</span>
            <nav aria-label="主要導覽">
              {navigation.map((item) => (
                <button
                  key={item.id}
                  className={`nav-item ${page === item.id ? "active" : ""}`}
                  aria-label={item.label}
                  onClick={() => setPage(item.id)}
                >
                  {page === item.id && (
                    <motion.span
                      layoutId="nav-active"
                      className="nav-active-bg"
                      transition={{
                        type: "spring",
                        stiffness: 420,
                        damping: 36,
                      }}
                    />
                  )}
                  <item.icon size={19} />
                  <span>{item.label}</span>
                  {item.id === "converter" &&
                    drafts.length + running.length > 0 && (
                      <b>{drafts.length + running.length}</b>
                    )}
                </button>
              ))}
            </nav>
            <div className="sidebar-bottom">
              <div className="privacy-card">
                <div className="privacy-icon">
                  <ShieldCheck size={19} />
                </div>
                <strong>你的檔案，只屬於你。</strong>
                <p>
                  100% 本機處理
                  <br />
                  無上傳、無追蹤，安心離線。
                </p>
                <span>
                  <i /> OFFLINE BY DESIGN
                </span>
              </div>
              <button
                className="sidebar-version"
                onClick={() => setPage("settings")}
              >
                <span className="avatar">R</span>
                <span>
                  RAI Studio<small>Version 0.1.0</small>
                </span>
                <Settings2 size={15} />
              </button>
            </div>
          </aside>
          <main className="main-panel glass" data-material="main">
            <div className="workspace-header">
              <div className="breadcrumb">
                工作空間
                <ChevronRight size={13} />
                <span>{currentNav.label}</span>
              </div>
              <div className="row header-right">
                <span
                  className={`connection ${engineError ? "error-text" : ""}`}
                >
                  <i />
                  {!desktop
                    ? "外觀預覽"
                    : engineError
                      ? "引擎離線"
                      : "本機安全處理"}
                </span>
                <Button
                  compact
                  aria-label="開啟個人化設定"
                  onClick={() => setPage("settings")}
                >
                  <Settings2 size={17} />
                </Button>
              </div>
            </div>
            <div className="page-scroll">
              <div className="page-heading">
                <div>
                  <span className="eyebrow">
                    {currentNav.english.toUpperCase()}
                  </span>
                  <h1>
                    {page === "dashboard"
                      ? "每一次轉換，都是新的可能。"
                      : page === "converter"
                        ? "檔案轉換"
                        : page === "history"
                          ? "每一次完成，都有跡可循。"
                          : "打造你的專屬空間。"}
                  </h1>
                  <p>
                    {page === "dashboard"
                      ? "一個安靜、高效的空間，處理所有重要的檔案。"
                      : page === "converter"
                        ? "選擇格式、調整細節，接著讓 RAI 為你完成。"
                        : page === "history"
                          ? "所有轉換紀錄保留在這台電腦，隨時查找、再次執行。"
                          : "個人化外觀與轉檔偏好，讓工具配合你的習慣。"}
                  </p>
                </div>
                {page === "converter" && (
                  <Button
                    variant="primary"
                    onClick={addFiles}
                    disabled={!desktop || importing || !!engineError}
                  >
                    <Plus size={17} />
                    加入檔案
                  </Button>
                )}
              </div>
              {!desktop && (
                <div className="preview-banner">
                  <InfoIcon />
                  <span>
                    瀏覽器外觀預覽 · 真實檔案轉換、背景匯入與本機紀錄請使用
                    Windows 桌面版。
                  </span>
                </div>
              )}
              {engineError && (
                <div className="engine-banner">
                  <CircleAlert size={18} />
                  <span>{engineError}</span>
                  <Button compact onClick={load}>
                    <RotateCcw size={15} />
                    重新連線
                  </Button>
                </div>
              )}
              <AnimatePresence mode="wait">
                <motion.div
                  key={page}
                  initial={{ opacity: 0, y: 7 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  transition={{ duration: 0.17 }}
                >
                  {page === "dashboard" && (
                    <>
                      <section className="hero glass" data-material="card">
                        <div className="hero-copy">
                          <span className="hero-tag">
                            <Sparkles size={13} /> SIMPLE. SEAMLESS. YOURS.
                          </span>
                          <h2>
                            轉換格式，
                            <br />
                            不打斷你的靈感。
                          </h2>
                          <p>
                            從影像到文件，一次完成。
                            <br />
                            精準轉換、完整掌控，全程留在本機。
                          </p>
                          <Button
                            variant="primary"
                            onClick={addFiles}
                            disabled={!desktop || importing || !!engineError}
                          >
                            開始轉換
                            <ArrowRight size={17} />
                          </Button>
                        </div>
                        <div className="hero-art" aria-hidden="true">
                          <div className="orbit orbit-one" />
                          <div className="orbit orbit-two" />
                          <div className="art-glass art-back">
                            <FileImage size={30} />
                            <span>INPUT</span>
                          </div>
                          <div className="art-glass art-front">
                            <ArrowLeftRight size={43} />
                            <span>RAI</span>
                          </div>
                          <div className="art-badge">
                            <Check size={13} />
                            Converted
                          </div>
                          <i className="art-star one" />
                          <i className="art-star two" />
                        </div>
                        <span className="hero-caption">
                          YOUR FILES. NEW POSSIBILITIES.
                        </span>
                      </section>
                      <div className="section-title">
                        <h2>從什麼開始？</h2>
                        <span>一個工作空間，多種可能</span>
                      </div>
                      <div className="category-grid">
                        {categories.map((c) => (
                          <button
                            className="category-card glass"
                            data-material="card"
                            key={c.id}
                            onClick={addFiles}
                            disabled={!desktop || !!engineError}
                          >
                            <span className={`category-icon ${c.color}`}>
                              <c.icon size={22} />
                            </span>
                            <strong>{c.name}</strong>
                            <span>{c.formats}</span>
                            <ArrowRight size={15} className="category-arrow" />
                          </button>
                        ))}
                      </div>
                      {dropzone()}
                      <div className="dashboard-lower">
                        <section className="recent-section">
                          <div className="section-title">
                            <h2>最近轉換</h2>
                            <button
                              className="text-link"
                              onClick={() => setPage("history")}
                            >
                              查看全部
                              <ArrowRight size={13} />
                            </button>
                          </div>
                          <div
                            className="recent-list glass"
                            data-material="card"
                          >
                            {sortedJobs.length ? (
                              sortedJobs.slice(0, 3).map(jobRow)
                            ) : (
                              <div className="empty-recent">
                                <History size={24} />
                                <div>
                                  <strong>
                                    下一個完成的檔案，會出現在這裡。
                                  </strong>
                                  <p>加入第一個檔案，開啟你的轉換紀錄。</p>
                                </div>
                              </div>
                            )}
                          </div>
                        </section>
                        <section
                          className="summary-card glass"
                          data-material="card"
                        >
                          <div className="row between">
                            <h3>任務摘要</h3>
                            <span className="tiny-label">THIS DEVICE</span>
                          </div>
                          <div className="summary-values">
                            <div>
                              <strong>
                                {completed.length.toString().padStart(2, "0")}
                              </strong>
                              <span>
                                <i className="status-dot green" />
                                已完成
                              </span>
                            </div>
                            <div>
                              <strong>
                                {running.length.toString().padStart(2, "0")}
                              </strong>
                              <span>
                                <i className="status-dot blue-dot" />
                                處理中
                              </span>
                            </div>
                            <div>
                              <strong>
                                {failed.length.toString().padStart(2, "0")}
                              </strong>
                              <span>
                                <i className="status-dot amber" />
                                待處理
                              </span>
                            </div>
                          </div>
                          <span className="summary-foot">
                            <ShieldCheck size={13} /> 每個檔案，都在本機安心轉換
                          </span>
                        </section>
                      </div>
                    </>
                  )}
                  {page === "converter" && (
                    <>
                      <div className="converter-layout">
                        <div className="converter-content">
                          {dropzone(true)}
                          <section
                            className="queue-panel glass"
                            data-material="card"
                          >
                            <div className="queue-heading row between">
                              <div className="row">
                                <h2>準備轉換</h2>
                                <span className="count-badge">
                                  {drafts.length}
                                </span>
                              </div>
                              <div className="row">
                                <Button
                                  compact
                                  onClick={() =>
                                    setDrafts((old) =>
                                      old.map((f) => ({
                                        ...f,
                                        selected: !old.every((x) => x.selected),
                                      })),
                                    )
                                  }
                                  disabled={!drafts.length}
                                >
                                  <CheckCheck size={15} />
                                  全選
                                </Button>
                                <Button
                                  compact
                                  aria-label="清空待轉換檔案"
                                  onClick={() => {
                                    setDrafts([]);
                                    setFocused(null);
                                  }}
                                  disabled={!drafts.length}
                                >
                                  <Trash2 size={15} />
                                </Button>
                                <Button
                                  compact
                                  aria-label={
                                    details ? "收合詳細設定" : "展開詳細設定"
                                  }
                                  onClick={() => setDetails(!details)}
                                >
                                  {details ? (
                                    <PanelRightClose size={17} />
                                  ) : (
                                    <PanelRightOpen size={17} />
                                  )}
                                </Button>
                              </div>
                            </div>
                            {drafts.length ? (
                              <div className="draft-list">
                                {drafts.map((file, index) => {
                                  const Icon = categoryIcon(file.category);
                                  return (
                                    <motion.div
                                      layout={drafts.length < 80}
                                      initial={
                                        drafts.length < 40
                                          ? { opacity: 0, y: 6 }
                                          : false
                                      }
                                      animate={{ opacity: 1, y: 0 }}
                                      key={file.id}
                                      className={`draft-row ${focusedFile?.id === file.id ? "focused" : ""}`}
                                      onClick={() => setFocused(file.id)}
                                    >
                                      <input
                                        aria-label={`選擇 ${file.name}`}
                                        type="checkbox"
                                        checked={file.selected}
                                        onChange={(e) =>
                                          setDrafts((old) =>
                                            old.map((f) =>
                                              f.id === file.id
                                                ? {
                                                    ...f,
                                                    selected: e.target.checked,
                                                  }
                                                : f,
                                            ),
                                          )
                                        }
                                      />
                                      {file.preview ? (
                                        <img
                                          className="file-thumbnail"
                                          src={file.preview}
                                          alt=""
                                        />
                                      ) : (
                                        <span
                                          className={`file-icon ${fileStyle(file.category)}`}
                                        >
                                          <Icon size={22} />
                                        </span>
                                      )}
                                      <div className="draft-info">
                                        <strong title={file.name}>
                                          {file.name}
                                        </strong>
                                        <span>
                                          {bytes(file.size)} ·{" "}
                                          {file.extension.toUpperCase()}
                                          {file.dimensions
                                            ? ` · ${file.dimensions[0]} × ${file.dimensions[1]}`
                                            : ""}
                                        </span>
                                        {!file.available && (
                                          <span className="error-text">
                                            缺少{" "}
                                            {file.category === "office"
                                              ? "LibreOffice"
                                              : "FFmpeg"}{" "}
                                            引擎
                                          </span>
                                        )}
                                      </div>
                                      <ArrowRight size={14} className="muted" />
                                      <select
                                        aria-label={`${file.name} 輸出格式`}
                                        value={file.format}
                                        onChange={(e) =>
                                          setDrafts((old) =>
                                            old.map((f) =>
                                              f.id === file.id
                                                ? {
                                                    ...f,
                                                    format: e.target.value,
                                                  }
                                                : f,
                                            ),
                                          )
                                        }
                                      >
                                        {file.formats.map((fmt) => (
                                          <option key={fmt} value={fmt}>
                                            {fmt.toUpperCase()}
                                          </option>
                                        ))}
                                      </select>
                                      <div className="draft-actions">
                                        <Button
                                          compact
                                          aria-label={`上移 ${file.name}`}
                                          disabled={index === 0}
                                          onClick={() => reorder(index, -1)}
                                        >
                                          <ArrowUp size={13} />
                                        </Button>
                                        <Button
                                          compact
                                          aria-label={`下移 ${file.name}`}
                                          disabled={index === drafts.length - 1}
                                          onClick={() => reorder(index, 1)}
                                        >
                                          <ArrowDown size={13} />
                                        </Button>
                                        <Button
                                          compact
                                          aria-label={`移除 ${file.name}`}
                                          onClick={() =>
                                            setDrafts((old) =>
                                              old.filter(
                                                (f) => f.id !== file.id,
                                              ),
                                            )
                                          }
                                        >
                                          <X size={14} />
                                        </Button>
                                      </div>
                                    </motion.div>
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="queue-empty">
                                <div className="empty-file-icon">
                                  <File size={29} />
                                  <Plus size={13} />
                                </div>
                                <strong>一切就緒，等你的檔案。</strong>
                                <p>
                                  支援多檔加入，並可為每個檔案設定不同格式。
                                </p>
                                <Button
                                  onClick={addFiles}
                                  disabled={!desktop || !!engineError}
                                >
                                  <Plus size={16} />
                                  選擇檔案
                                </Button>
                              </div>
                            )}
                            {drafts.length > 0 && (
                              <div className="queue-footer">
                                <span>
                                  {selected.length} 個已選取 ·{" "}
                                  {bytes(
                                    selected.reduce(
                                      (sum, f) => sum + f.size,
                                      0,
                                    ),
                                  )}
                                </span>
                                <Button
                                  compact
                                  onClick={() => setMergeOpen(true)}
                                  disabled={
                                    selected.length < 2 ||
                                    !selected.every((f) =>
                                      ["image", "pdf"].includes(f.category),
                                    )
                                  }
                                >
                                  <FileText size={14} />
                                  合併 PDF
                                </Button>
                              </div>
                            )}
                          </section>
                          {jobs.length > 0 && (
                            <section
                              className="queue-panel glass"
                              data-material="card"
                            >
                              <div className="queue-heading row between">
                                <div className="row">
                                  <h2>轉檔佇列</h2>
                                  <span className="count-badge">
                                    {jobs.length}
                                  </span>
                                </div>
                                <Button
                                  compact
                                  onClick={() => setConfirmClear(true)}
                                  disabled={!jobs.some((j) => !active(j))}
                                >
                                  <Trash2 size={14} />
                                  清除已結束
                                </Button>
                              </div>
                              {sortedJobs.slice(0, 100).map(jobRow)}
                              {jobs.length > 100 && (
                                <button
                                  className="text-link"
                                  onClick={() => setPage("history")}
                                >
                                  到紀錄頁搜尋全部任務
                                </button>
                              )}
                            </section>
                          )}
                        </div>
                        <AnimatePresence>
                          {details && (
                            <motion.aside
                              className="detail-panel glass"
                              data-material="settings"
                              initial={{ opacity: 0, width: 0 }}
                              animate={{ opacity: 1, width: 270 }}
                              exit={{ opacity: 0, width: 0 }}
                              transition={{ duration: 0.22 }}
                            >
                              <div className="detail-inner">
                                <div className="row between">
                                  <h3>轉換細節</h3>
                                  <Settings2 size={16} />
                                </div>
                                {focusedFile ? (
                                  <>
                                    <div
                                      className={`detail-preview ${fileStyle(focusedFile.category)}`}
                                    >
                                      {focusedFile.preview ? (
                                        <img
                                          src={focusedFile.preview}
                                          alt={focusedFile.name}
                                        />
                                      ) : (
                                        <File size={42} />
                                      )}
                                    </div>
                                    <strong className="detail-name">
                                      {focusedFile.name}
                                    </strong>
                                    <span className="detail-meta">
                                      {focusedFile.extension.toUpperCase()}
                                      <ArrowRight size={12} />
                                      {focusedFile.format.toUpperCase()}
                                    </span>
                                    <hr />
                                    <OptionsEditor
                                      category={focusedFile.category}
                                      format={focusedFile.format}
                                      value={focusedFile.options}
                                      onChange={(options) =>
                                        setDrafts((old) =>
                                          old.map((f) =>
                                            f.id === focusedFile.id
                                              ? { ...f, options }
                                              : f,
                                          ),
                                        )
                                      }
                                    />
                                    <Button
                                      compact
                                      disabled={!selected.length}
                                      onClick={() => {
                                        setDrafts((old) =>
                                          old.map((f) =>
                                            f.selected &&
                                            f.category === focusedFile.category
                                              ? {
                                                  ...f,
                                                  options: {
                                                    ...focusedFile.options,
                                                  },
                                                  format: f.formats.includes(
                                                    focusedFile.format,
                                                  )
                                                    ? focusedFile.format
                                                    : f.format,
                                                }
                                              : f,
                                          ),
                                        );
                                        notify("已套用至勾選的同類型檔案");
                                      }}
                                    >
                                      <CheckCheck size={14} />
                                      套用至勾選的同類檔案
                                    </Button>
                                  </>
                                ) : (
                                  <div className="detail-placeholder">
                                    <Settings2 size={28} />
                                    <p>
                                      加入檔案後，
                                      <br />
                                      在這裡調整每個細節。
                                    </p>
                                  </div>
                                )}
                              </div>
                            </motion.aside>
                          )}
                        </AnimatePresence>
                      </div>
                      <div
                        className="conversion-toolbar glass"
                        data-material="toolbar"
                      >
                        <div className="output-path">
                          <span className="tiny-label">輸出位置</span>
                          <button
                            title={
                              settings.outputDir || "來源資料夾 / RAI Output"
                            }
                            onClick={chooseOutput}
                            disabled={!desktop}
                          >
                            <FolderOpen size={15} />
                            <span>
                              {settings.outputDir || "來源資料夾 / RAI Output"}
                            </span>
                            <ChevronDown size={13} />
                          </button>
                        </div>
                        <div className="toolbar-actions">
                          {running.length > 0 && (
                            <span className="running-count">
                              <i className="status-dot blue-dot" />
                              {running.length} 個處理中
                            </span>
                          )}
                          <Button
                            variant="primary"
                            disabled={
                              !selected.some((f) => f.available) ||
                              submitting ||
                              !ready ||
                              !!engineError
                            }
                            onClick={() => submit()}
                          >
                            {submitting ? (
                              <LoaderCircle className="spin" size={16} />
                            ) : (
                              <Play size={16} />
                            )}
                            開始轉換
                            {selected.length > 0 && (
                              <span className="button-count">
                                {selected.filter((f) => f.available).length}
                              </span>
                            )}
                          </Button>
                        </div>
                      </div>
                    </>
                  )}
                  {page === "history" && (
                    <>
                      <div className="history-stats">
                        <div className="glass" data-material="card">
                          <CircleCheck size={20} />
                          <strong>{completed.length}</strong>
                          <span>已完成</span>
                        </div>
                        <div className="glass" data-material="card">
                          <LoaderCircle size={20} />
                          <strong>{running.length}</strong>
                          <span>處理中</span>
                        </div>
                        <div className="glass" data-material="card">
                          <CircleAlert size={20} />
                          <strong>{failed.length}</strong>
                          <span>失敗</span>
                        </div>
                        <div className="glass" data-material="card">
                          <Clock3 size={20} />
                          <strong>
                            {
                              jobs.filter((j) => j.status === "cancelled")
                                .length
                            }
                          </strong>
                          <span>已取消</span>
                        </div>
                      </div>
                      <div className="history-toolbar">
                        <label className="search-box">
                          <Search size={17} />
                          <input
                            aria-label="搜尋轉換紀錄"
                            placeholder="搜尋檔名或輸出格式…"
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
                            <option value={id} key={id}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <Button
                          onClick={() => setConfirmClear(true)}
                          disabled={!jobs.some((j) => !active(j))}
                        >
                          <Trash2 size={15} />
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
                            <History size={36} />
                            <h3>
                              {jobs.length
                                ? "找不到符合條件的紀錄"
                                : "你的轉換故事，從這裡開始。"}
                            </h3>
                            <p>
                              {jobs.length
                                ? "試試其他關鍵字或篩選條件。"
                                : "完成第一個轉檔後，所有紀錄會自動保存在這裡。"}
                            </p>
                            <Button onClick={() => setPage("converter")}>
                              <ArrowLeftRight size={16} />
                              前往轉檔
                            </Button>
                          </div>
                        )}
                      </div>
                      <p className="hint">
                        共 {jobs.length} 筆紀錄 · 每次最多顯示 300
                        筆，使用搜尋可查找更早的紀錄。
                      </p>
                    </>
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
                <ShieldCheck size={12} />
                所有檔案皆在本機處理
              </span>
              {running.length > 0 ? (
                <span className="footer-progress">
                  <LoaderCircle size={12} className="spin" />
                  {running.length} 個任務 · 平均 {Math.floor(totalProgress)}%
                  {eta !== null &&
                    ` · 估計 ${eta < 60 ? `${eta} 秒` : `${Math.ceil(eta / 60)} 分鐘`}`}
                </span>
              ) : (
                <span>
                  <i className="status-dot green" />
                  {desktop
                    ? ready
                      ? "準備就緒"
                      : "正在連接引擎…"
                    : "外觀預覽模式"}
                </span>
              )}
            </footer>
          </main>
        </div>
        <AnimatePresence>
          {dragging && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="drag-overlay"
            >
              <Upload size={48} />
              <h2>放開，開始新的可能。</h2>
              <p>檔案不會離開這台電腦。</p>
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
                initial={{ opacity: 0, y: 12, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 20 }}
              >
                {t.error ? (
                  <CircleAlert size={18} />
                ) : (
                  <CircleCheck size={18} />
                )}
                <span>{t.text}</span>
                <button
                  aria-label="關閉通知"
                  onClick={() =>
                    setToasts((old) => old.filter((x) => x.id !== t.id))
                  }
                >
                  <X size={14} />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
        <Modal
          open={confirmClear}
          onOpenChange={setConfirmClear}
          title="清除已結束的轉換紀錄？"
          description="只會刪除本機紀錄，來源檔案與轉換結果都會保留。執行中的任務不受影響。"
        >
          <div className="row end">
            <Button onClick={() => setConfirmClear(false)}>保留紀錄</Button>
            <Button variant="danger" onClick={clear}>
              <Trash2 size={16} />
              清除紀錄
            </Button>
          </div>
        </Modal>
        <Modal
          open={mergeOpen}
          onOpenChange={setMergeOpen}
          title="合併為一份 PDF"
          description="依照檔案清單目前順序，將勾選的圖片與 PDF 合併。圖片會依原始尺寸嵌入。"
        >
          <p className="muted">已選取 {selected.length} 個檔案</p>
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
            <FileText size={16} />
            合併並輸出 PDF
          </Button>
        </Modal>
      </div>
    </MotionConfig>
  );
}
function InfoIcon() {
  return <CircleAlert size={16} />;
}
