import { conversionIssue } from "../conversion";
import {
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CheckCheck,
  ChevronDown,
  File,
  FileText,
  FolderOpen,
  LoaderCircle,
  PanelRightClose,
  PanelRightOpen,
  Play,
  Pencil,
  Settings2,
  Trash2,
  X,
} from "lucide-react";
import type { Draft, Options, Registry, HardwareDevice } from "../types";
import { Button } from "./ui";
import { OptionsEditor } from "./OptionsEditor";
import { FilePreview } from "./FilePreview";

const types = [
  ["all", "全部"],
  ["video", "影片"],
  ["audio", "音訊"],
  ["image", "圖片"],
  ["pdf", "PDF"],
  ["office", "文件"],
  ["vector", "向量"],
  ["ebook", "電子書"],
] as const;
const sizeLabel = (size: number) =>
  size < 1024 ** 2
    ? `${(size / 1024).toFixed(1)} KB`
    : size < 1024 ** 3
      ? `${(size / 1024 ** 2).toFixed(1)} MB`
      : `${(size / 1024 ** 3).toFixed(2)} GB`;
interface Props {
  onEdit?: (path: string, category: string) => void;
  hardware: HardwareDevice[];
  registry: Registry;
  modeBar: ReactNode;
  totalProgress: number;
  runningCount: number;
  cancelAll: () => void;
  drafts: Draft[];
  setDrafts: Dispatch<SetStateAction<Draft[]>>;
  focusedFile: Draft | undefined;
  setFocused: (id: string | null) => void;
  details: boolean;
  setDetails: (v: boolean) => void;
  dropzone: ReactNode;
  outputDir: string;
  chooseOutput: () => void;
  canUseDesktop: boolean;
  submitting: boolean;
  ready: boolean;
  hasError: boolean;
  submit: () => void;
  merge: () => void;
  reorder: (index: number, direction: number) => void;
  notify: (message: string) => void;
  activity: ReactNode;
}
export function ConversionWorkspace(p: Props) {
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const [category, setCategory] = useState("all");
  const selected = p.drafts.filter((f) => f.selected);
  const visible = p.drafts.filter(
    (f) => category === "all" || f.category === category,
  );
  const focused = p.focusedFile;
  const setOptions = (options: Options) =>
    p.setDrafts((old) =>
      old.map((f) => (f.id === focused?.id ? { ...f, options } : f)),
    );
  return (
    <div className="converter-workspace">
      {p.modeBar}
      {p.dropzone}
      <div className={`converter-layout ${p.details ? "with-details" : ""}`}>
        <section
          className="queue-panel glass draft-panel"
          data-material="card"
          aria-label="已匯入檔案佇列"
        >
          <div className="queue-heading row between">
            <div className="row">
              <h2>檔案佇列</h2>
              <span className="count-badge">{p.drafts.length}</span>
            </div>
            <div className="row">
              <Button
                compact
                disabled={!visible.length}
                onClick={() => {
                  const ids = new Set(visible.map((f) => f.id));
                  const checked = !visible.every((f) => f.selected);
                  p.setDrafts((old) =>
                    old.map((f) =>
                      ids.has(f.id) ? { ...f, selected: checked } : f,
                    ),
                  );
                }}
              >
                <CheckCheck size={18} />
                全選
              </Button>
              <Button
                compact
                aria-label="清空待轉換檔案"
                disabled={!p.drafts.length}
                onClick={() => {
                  p.setDrafts([]);
                  p.setFocused(null);
                }}
              >
                <Trash2 size={18} />
              </Button>
              <Button
                compact
                aria-label={p.details ? "收合詳細設定" : "展開詳細設定"}
                onClick={() => p.setDetails(!p.details)}
              >
                {p.details ? (
                  <PanelRightClose size={19} />
                ) : (
                  <PanelRightOpen size={19} />
                )}
              </Button>
            </div>
          </div>
          <div className="type-filters" aria-label="檔案類型篩選">
            {types.map(([id, label]) => (
              <button
                key={id}
                aria-pressed={category === id}
                className={category === id ? "active" : ""}
                onClick={() => setCategory(id)}
              >
                {label}
                {(id === "all"
                  ? p.drafts.length
                  : p.drafts.filter((f) => f.category === id).length) > 0 && (
                  <span>
                    {id === "all"
                      ? p.drafts.length
                      : p.drafts.filter((f) => f.category === id).length}
                  </span>
                )}
              </button>
            ))}
          </div>
          {visible.length ? (
            <div className="draft-list">
              {visible.map((file) => {
                const index = p.drafts.findIndex((f) => f.id === file.id);
                const issue = conversionIssue(file, p.registry);
                return (
                  <motion.div
                    key={file.id}
                    layout={p.drafts.length < 80}
                    initial={
                      p.drafts.length < 40 ? { opacity: 0, y: 4 } : false
                    }
                    animate={{ opacity: 1, y: 0 }}
                    className={`draft-row ${focused?.id === file.id ? "focused" : ""}`}
                    onClick={() => p.setFocused(file.id)}
                    onFocus={() => p.setFocused(file.id)}
                  >
                    <input
                      type="checkbox"
                      aria-label={`選擇 ${file.name}`}
                      checked={file.selected}
                      onChange={(e) =>
                        p.setDrafts((old) =>
                          old.map((f) =>
                            f.id === file.id
                              ? { ...f, selected: e.target.checked }
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
                      <span className="file-icon">
                        <File size={23} />
                      </span>
                    )}
                    <div className="draft-info">
                      <button
                        className="draft-name"
                        onClick={() => p.setFocused(file.id)}
                        title={file.name}
                      >
                        {file.name}
                      </button>
                      <span>
                        {sizeLabel(file.size)} · {file.extension.toUpperCase()}
                        {file.dimensions
                          ? ` · ${file.dimensions.join(" × ")}`
                          : ""}
                      </span>
                      {file.detection?.warning && (
                        <span className="hint">{file.detection.warning}</span>
                      )}
                      {issue &&
                        (file.format ||
                          !file.available ||
                          file.expectedSource) && (
                          <span
                            className={
                              file.format ||
                              !file.available ||
                              file.expectedSource
                                ? "error-text"
                                : "hint"
                            }
                          >
                            {issue}
                          </span>
                        )}
                    </div>
                    <ArrowRight size={16} className="format-arrow" />
                    <select
                      className={!file.format ? "unassigned-format" : ""}
                      aria-label={`${file.name} 輸出格式`}
                      value={file.format}
                      onChange={(e) =>
                        p.setDrafts((old) =>
                          old.map((f) =>
                            f.id === file.id
                              ? { ...f, format: e.target.value }
                              : f,
                          ),
                        )
                      }
                    >
                      <option value="">請選擇輸出格式</option>
                      {file.formats.map((fmt) => (
                        <option key={fmt} value={fmt}>
                          {fmt.toUpperCase()}
                        </option>
                      ))}
                    </select>
                    <div className="draft-actions">
                      {p.onEdit &&
                        ["video", "audio", "image"].includes(file.category) && (
                          <Button
                            compact
                            aria-label={`送入${file.category === "image" ? "圖片" : "影片"}編輯器`}
                            title={`送入${file.category === "image" ? "圖片" : "影片"}編輯器`}
                            onClick={() => p.onEdit?.(file.path, file.category)}
                          >
                            <Pencil size={16} />
                          </Button>
                        )}
                      <Button
                        compact
                        aria-label={`預覽 ${file.name}`}
                        onClick={() => setPreviewPath(file.path)}
                      >
                        預覽
                      </Button>
                      <Button
                        compact
                        aria-label={`上移 ${file.name}`}
                        disabled={index === 0}
                        onClick={() => p.reorder(index, -1)}
                      >
                        <ArrowUp size={16} />
                      </Button>
                      <Button
                        compact
                        aria-label={`下移 ${file.name}`}
                        disabled={index === p.drafts.length - 1}
                        onClick={() => p.reorder(index, 1)}
                      >
                        <ArrowDown size={16} />
                      </Button>
                      <Button
                        compact
                        aria-label={`移除 ${file.name}`}
                        onClick={() =>
                          p.setDrafts((old) =>
                            old.filter((f) => f.id !== file.id),
                          )
                        }
                      >
                        <X size={17} />
                      </Button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="queue-empty">
              <File size={27} />
              <strong>
                {p.drafts.length ? "沒有符合此類型的檔案" : "尚未加入檔案"}
              </strong>
              <p>
                {p.drafts.length
                  ? "切換篩選可查看其他檔案。"
                  : "拖入多個檔案，或使用上方選擇檔案。"}
              </p>
            </div>
          )}
          <div className="queue-footer">
            <span>
              已選取 {selected.length} / {p.drafts.length} 個
            </span>
            <Button
              compact
              disabled={
                selected.length < 2 ||
                !selected.every((f) => ["image", "pdf"].includes(f.category))
              }
              onClick={p.merge}
            >
              <FileText size={17} />
              合併 PDF
            </Button>
          </div>
        </section>
        <AnimatePresence>
          {p.details && (
            <motion.aside
              className="detail-panel glass"
              data-material="settings"
              aria-label="輸出設定"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 8 }}
              transition={{ duration: 0.18 }}
            >
              <div className="detail-heading row between">
                <h2>輸出設定</h2>
                <Settings2 size={18} />
              </div>
              <div className="detail-inner">
                {focused ? (
                  <>
                    <div className="detail-file">
                      {focused.preview ? (
                        <img src={focused.preview} alt="" />
                      ) : (
                        <File size={26} />
                      )}
                      <div>
                        <strong title={focused.name}>{focused.name}</strong>
                        <span>
                          {focused.extension.toUpperCase()} →{" "}
                          {focused.format
                            ? focused.format.toUpperCase()
                            : "請選擇輸出格式"}
                        </span>
                      </div>
                    </div>
                    {focused.detection && (
                      <p
                        className="hint detection-note"
                        title={focused.detection.method}
                      >
                        來源已依檔案內容辨識為 {focused.extension.toUpperCase()}
                      </p>
                    )}
                    {focused.format ? (
                      <OptionsEditor
                        hardware={p.hardware}
                        category={focused.category}
                        format={focused.format}
                        value={focused.options}
                        onChange={setOptions}
                      />
                    ) : (
                      <p className="hint">請先在檔案列選擇輸出格式。</p>
                    )}
                    <Button
                      className="apply-options"
                      compact
                      disabled={!selected.length || !focused.format}
                      onClick={() => {
                        p.setDrafts((old) =>
                          old.map((f) =>
                            f.selected && f.category === focused.category
                              ? {
                                  ...f,
                                  options: { ...focused.options },
                                  format: f.formats.includes(focused.format)
                                    ? focused.format
                                    : f.format,
                                }
                              : f,
                          ),
                        );
                        p.notify("已套用至勾選的同類型檔案");
                      }}
                    >
                      <CheckCheck size={17} />
                      套用至勾選的同類檔案
                    </Button>
                  </>
                ) : (
                  <div className="detail-placeholder">
                    <p>加入檔案後可調整格式、品質及尺寸。</p>
                  </div>
                )}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
      <div className="conversion-toolbar glass" data-material="toolbar">
        <div className="output-path">
          <span>輸出資料夾</span>
          <button
            aria-label="選擇輸出資料夾"
            onClick={p.chooseOutput}
            disabled={!p.canUseDesktop}
            title={p.outputDir || "來源資料夾 / File Converter Output"}
          >
            <FolderOpen size={19} />
            <span>{p.outputDir || "來源資料夾 / File Converter Output"}</span>
            <ChevronDown size={17} />
          </button>
        </div>
        <div className="toolbar-progress" aria-live="polite">
          <span>
            可轉換{" "}
            {selected.filter((f) => !conversionIssue(f, p.registry)).length} /{" "}
            {selected.length}
          </span>
          {p.runningCount > 0 && (
            <span>
              處理中 {p.runningCount} · {Math.floor(p.totalProgress)}%
            </span>
          )}
        </div>
        {p.runningCount > 0 && (
          <Button compact onClick={p.cancelAll}>
            取消全部
          </Button>
        )}
        <Button
          variant="primary"
          className="start-conversion"
          disabled={
            !selected.length ||
            selected.some((f) => !!conversionIssue(f, p.registry)) ||
            p.submitting ||
            !p.ready ||
            p.hasError
          }
          onClick={p.submit}
        >
          {p.submitting ? (
            <LoaderCircle className="spin" size={19} />
          ) : (
            <Play size={19} />
          )}
          開始轉換
          {selected.length > 0 && (
            <span className="button-count">
              {selected.filter((f) => !conversionIssue(f, p.registry)).length}
            </span>
          )}
        </Button>
      </div>
      {p.activity}
      {previewPath && (
        <FilePreview
          paths={[previewPath]}
          onClose={() => setPreviewPath(null)}
        />
      )}
    </div>
  );
}
