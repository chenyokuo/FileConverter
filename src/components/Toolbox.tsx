import { useState } from "react";
import { ArrowUpRight, Search, Wrench } from "lucide-react";
import type { Options, Registry } from "../types";
export interface Tool {
  id: string;
  category: string;
  name: string;
  detail: string;
  source: string;
  target: string;
  options?: Partial<Options>;
  merge?: boolean;
  phase?: string;
}
const categories = [
  "PDF",
  "圖片",
  "影片",
  "音訊",
  "文件",
  "壓縮",
  "電子書",
  "去浮水印／物件修復",
];
const tools: Tool[] = [
  {
    id: "pdf-images",
    category: "PDF",
    name: "PDF 轉圖片",
    detail: "逐頁輸出 PNG，可調整 DPI",
    source: "pdf",
    target: "png",
  },
  {
    id: "pdf-merge",
    category: "PDF",
    name: "合併 PDF 與圖片",
    detail: "依佇列順序合併；可在加入後調整順序",
    source: "",
    target: "pdf",
    merge: true,
  },
  {
    id: "pdf-split",
    category: "PDF",
    name: "分割 PDF",
    detail: "每頁另存為 PDF，支援頁碼範圍",
    source: "pdf",
    target: "pdf",
    options: { split: true },
  },
  {
    id: "pdf-rotate",
    category: "PDF",
    name: "旋轉 PDF",
    detail: "預設順時針 90°，可於詳細設定變更",
    source: "pdf",
    target: "pdf",
    options: { rotation: 90 },
  },
  {
    id: "pdf-extract",
    category: "PDF",
    name: "擷取 PDF 頁面",
    detail: "預設擷取第 1 頁，請於設定輸入頁碼",
    source: "pdf",
    target: "pdf",
    options: { pages: "1" },
  },
  {
    id: "pdf-docx",
    category: "PDF",
    name: "PDF 轉 DOCX",
    detail: "文字、表格、字型與排版可能失真；掃描文件請先 OCR",
    source: "pdf",
    target: "docx",
  },
  {
    id: "image-jpg",
    category: "圖片",
    name: "圖片轉 JPG",
    detail: "支援品質、尺寸及透明背景底色",
    source: "",
    target: "jpg",
  },
  {
    id: "image-webp",
    category: "圖片",
    name: "圖片轉 WebP",
    detail: "調整品質與輸出尺寸",
    source: "",
    target: "webp",
  },
  {
    id: "image-pdf",
    category: "圖片",
    name: "圖片合併 PDF",
    detail: "多張圖片依序組成 PDF",
    source: "",
    target: "pdf",
    merge: true,
  },
  {
    id: "video-mp4",
    category: "影片",
    name: "影片轉 MP4",
    detail: "H.264 / H.265、解析度、FPS 與音訊設定",
    source: "",
    target: "mp4",
  },
  {
    id: "video-audio",
    category: "影片",
    name: "擷取影片音軌",
    detail: "影片須包含音軌，輸出 MP3",
    source: "",
    target: "mp3",
  },
  {
    id: "audio-mp3",
    category: "音訊",
    name: "音訊轉 MP3",
    detail: "位元率、取樣率與聲道",
    source: "",
    target: "mp3",
  },
  {
    id: "audio-wav",
    category: "音訊",
    name: "音訊轉 WAV",
    detail: "輸出 PCM 音訊，可選取樣率",
    source: "",
    target: "wav",
  },
  {
    id: "office-pdf",
    category: "文件",
    name: "Office 轉 PDF",
    detail: "使用隨附 LibreOffice Runtime，保留原始文件",
    source: "",
    target: "pdf",
  },
  {
    id: "archive",
    category: "壓縮",
    name: "壓縮與解壓縮",
    detail: "P2：尚未整合 7-Zip Adapter",
    source: "",
    target: "",
    phase: "P2",
  },
  ...["epub", "mobi", "azw3", "fb2"].map((target) => ({
    id: "ebook-" + target,
    category: "電子書",
    name: "電子書轉 " + target.toUpperCase(),
    detail: "使用隨附 Calibre，來源與目標須相容",
    source: "",
    target,
  })),
  {
    id: "repair",
    category: "去浮水印／物件修復",
    name: "局部物件修復",
    detail: "P2：尚未整合本機模型與遮罩編輯器",
    source: "",
    target: "",
    phase: "P2",
  },
];
const kind = (category: string) =>
  ({ PDF: "pdf", 圖片: "image", 影片: "video", 音訊: "audio", 文件: "office" })[
    category
  ] || "";
export function Toolbox({
  registry,
  run,
  disabled,
}: {
  registry: Registry;
  run: (tool: Tool) => void;
  disabled: boolean;
}) {
  const [category, setCategory] = useState("PDF");
  const [matrix, setMatrix] = useState(false);
  const [query, setQuery] = useState("");
  const edges = registry.edges.filter((e) =>
    `${e.source} ${e.target} ${e.engine}`.includes(query.toLowerCase()),
  );
  return (
    <div className="toolbox-page">
      <div className="toolbox-tabs" aria-label="工具分類">
        {categories.map((c) => (
          <button
            key={c}
            aria-pressed={!matrix && category === c}
            onClick={() => {
              setCategory(c);
              setMatrix(false);
            }}
          >
            {c}工具
          </button>
        ))}
        <button aria-pressed={matrix} onClick={() => setMatrix(true)}>
          轉換能力表
        </button>
      </div>
      {matrix ? (
        <section className="registry-panel glass" data-material="card">
          <div className="row between">
            <h2>Conversion Registry</h2>
            <label className="search-box">
              <Search size={18} />
              <input
                aria-label="搜尋轉換能力"
                placeholder="格式或引擎"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          </div>
          <p className="hint">
            顯示後端的直接轉換能力。測試覆蓋代表有整合案例，並非所有編碼器、選項及內容皆已驗證。
          </p>
          <div className="registry-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>來源 → 目標</th>
                  <th>引擎／狀態</th>
                  <th>測試</th>
                  <th>品質與設定</th>
                </tr>
              </thead>
              <tbody>
                {edges.map((e) => (
                  <tr key={e.id}>
                    <td>
                      {e.source.toUpperCase()} → {e.target.toUpperCase()}
                      <small>{e.intermediate ? "需要中介" : "直接轉換"}</small>
                    </td>
                    <td>
                      {e.engine}
                      <small title={e.reason}>
                        {e.available ? "可使用" : e.reason}
                      </small>
                    </td>
                    <td>
                      {e.testStatus === "regression-covered"
                        ? "回歸案例覆蓋"
                        : "尚未驗證"}
                    </td>
                    <td>
                      {e.lossy ? "可能有損 · " : ""}
                      {e.qualityNote}
                      <small>
                        {e.settings.join(" · ") || "無額外輸出選項"}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <div className="tool-grid">
          {tools
            .filter((t) => t.category === category)
            .map((tool) => {
              const available =
                !tool.phase &&
                registry.edges.some(
                  (e) =>
                    e.category === kind(tool.category) &&
                    e.target === tool.target &&
                    e.available,
                );
              return (
                <button
                  key={tool.id}
                  className="tool-card glass"
                  data-material="card"
                  disabled={disabled || !available}
                  onClick={() => run(tool)}
                  title={tool.detail}
                >
                  <div className="row between">
                    <Wrench size={21} />
                    {available ? (
                      <ArrowUpRight size={20} />
                    ) : (
                      <span className="badge">
                        {tool.phase || "引擎未安裝"}
                      </span>
                    )}
                  </div>
                  <strong>{tool.name}</strong>
                  <span>{tool.detail}</span>
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}
