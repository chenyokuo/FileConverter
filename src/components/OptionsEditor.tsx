import type { Options } from "../types";
import { Slider, Toggle } from "./ui";
export function OptionsEditor({
  category,
  format,
  value,
  onChange,
}: {
  category: string;
  format: string;
  value: Options;
  onChange: (v: Options) => void;
}) {
  const set = (key: keyof Options, v: unknown) =>
    onChange({ ...value, [key]: v });
  const num = (key: keyof Options, label: string, max = 100000) => (
    <label className="field" key={key}>
      <span>{label}</span>
      <input
        aria-label={label}
        type="number"
        min="0"
        max={max}
        value={value[key] as number}
        onChange={(e) => set(key, +e.target.value)}
      />
    </label>
  );
  const select = (
    key: keyof Options,
    label: string,
    items: [string, string][],
  ) => (
    <label className="field" key={key}>
      <span>{label}</span>
      <select
        value={String(value[key])}
        onChange={(e) =>
          set(
            key,
            typeof value[key] === "number" ? +e.target.value : e.target.value,
          )
        }
      >
        {items.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
  const isAudio = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "opus"].includes(
    format,
  );
  return (
    <div className="options-stack">
      {category === "image" && format !== "pdf" && (
        <>
          {["jpg", "webp"].includes(format) ? (
            <Slider
              label="圖片品質"
              value={value.quality}
              min={1}
              onChange={(v) => set("quality", v)}
            />
          ) : (
            <p className="hint">此格式使用無損輸出，不套用有損品質參數。</p>
          )}
          <div className="two-col">
            {num("width", "寬度 px · 0 自動")}
            {num("height", "高度 px · 0 自動")}
          </div>
          <p className="hint">
            任一尺寸為 0 時保留比例；兩者皆為 0 保留原尺寸。
          </p>
          {["jpg", "bmp"].includes(format) && (
            <label className="field">
              <span>透明區域底色</span>
              <input
                aria-label="透明區域底色"
                type="color"
                value={value.matte}
                onChange={(e) => set("matte", e.target.value)}
              />
            </label>
          )}
        </>
      )}
      {category === "video" && !isAudio && (
        <>
          {!["webm", "avi"].includes(format) &&
            select("videoCodec", "影片編碼器", [
              ["h264", "H.264 · CPU"],
              ["h265", "H.265 · CPU"],
              ["nvenc", "NVIDIA NVENC · 啟動時檢測"],
            ])}
          {format === "webm" && (
            <p className="hint">WebM 自動使用 VP9 / Opus。</p>
          )}
          {format === "avi" && <p className="hint">AVI 自動使用 MPEG-4。</p>}
          {format !== "avi" && value.videoBitrate === 0 && (
            <Slider
              label="CRF · 數值低畫質高"
              min={0}
              max={51}
              unit=""
              value={value.crf}
              onChange={(v) => set("crf", v)}
            />
          )}
          {num(
            "videoBitrate",
            format === "avi"
              ? "影片 kbps · 0 自動品質"
              : "影片 kbps · 0 使用 CRF",
            200000,
          )}
          {select("videoHeight", "解析度", [
            ["0", "保留來源"],
            ["2160", "2160p · 4K"],
            ["1440", "1440p · QHD"],
            ["1080", "1080p · Full HD"],
            ["720", "720p · HD"],
            ["480", "480p"],
          ])}
          {num("fps", "FPS · 0 保留來源", 240)}
        </>
      )}
      {(isAudio || category === "video") && (
        <>
          {!["wav", "flac"].includes(format) &&
            select("audioBitrate", "音訊位元率", [
              ["64", "64 kbps"],
              ["128", "128 kbps"],
              ["192", "192 kbps"],
              ["256", "256 kbps"],
              ["320", "320 kbps"],
            ])}
          {select(
            "sampleRate",
            "取樣率",
            format === "opus" || format === "webm"
              ? [
                  ["0", "自動相容取樣率"],
                  ["48000", "48 kHz"],
                ]
              : [
                  ["0", "保留來源"],
                  ["44100", "44.1 kHz"],
                  ["48000", "48 kHz"],
                  ...(!["mp3", "ogg"].includes(format)
                    ? [["96000", "96 kHz"] as [string, string]]
                    : []),
                ],
          )}
          {select("channels", "聲道", [
            ["0", "保留來源"],
            ["1", "單聲道"],
            ["2", "立體聲"],
          ])}
          <p className="hint">WAV / FLAC 使用無損編碼，不套用有損位元率。</p>
        </>
      )}
      {category === "pdf" && format !== "pdf" && (
        <Slider
          label="PDF 影像 DPI"
          min={36}
          max={600}
          unit=""
          value={value.pdfDpi}
          onChange={(v) => set("pdfDpi", v)}
        />
      )}
      {category === "pdf" && format === "pdf" && (
        <>
          <label className="field">
            <span>擷取頁碼 · 留空為全部</span>
            <input
              aria-label="擷取頁碼"
              placeholder="例如 1-3,5"
              value={value.pages}
              onChange={(e) => set("pages", e.target.value)}
            />
          </label>
          {select("rotation", "順時針旋轉", [
            ["0", "不旋轉"],
            ["90", "90°"],
            ["180", "180°"],
            ["270", "270°"],
          ])}
          <Toggle
            label="逐頁分割 PDF"
            checked={value.split}
            onChange={(v) => set("split", v)}
          />
        </>
      )}
      {category === "office" && (
        <p className="hint">
          由本機 LibreOffice 執行；字型與排版可能因電腦環境而異。CSV
          僅輸出作用中的工作表。
        </p>
      )}
      {category === "image" && format === "pdf" && (
        <p className="hint">
          圖片會嵌入 PDF；若要多張合併，請勾選檔案後使用「合併 PDF」。
        </p>
      )}
    </div>
  );
}
