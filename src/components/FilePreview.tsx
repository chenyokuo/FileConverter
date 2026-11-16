import { useEffect, useState } from "react";
import { call } from "../api";
import { Button, Modal } from "./ui";
import type { FilePreview as Preview } from "./AdvancedTools";
type RichPreview = Preview & { mediaKind?: string; clipSeconds?: number };
const bytes = (n: number) =>
  n > 1048576
    ? `${(n / 1048576).toFixed(2)} MB`
    : `${(n / 1024).toFixed(1)} KB`;
function summary(p: RichPreview) {
  const m = p.metadata;
  const streams = (m.streams || []) as {
    codec_type: string;
    codec_name: string;
    width?: number;
    height?: number;
    sample_rate?: number;
    channels?: number;
  }[];
  return (
    <dl className="preview-metadata">
      <dt>大小</dt>
      <dd>{bytes(p.size)}</dd>
      <dt>格式</dt>
      <dd>{p.format.toUpperCase()}</dd>
      {Array.isArray(m.dimensions) && (
        <>
          <dt>尺寸</dt>
          <dd>{m.dimensions.join(" × ")}</dd>
        </>
      )}
      {m.width != null && (
        <>
          <dt>解析度</dt>
          <dd>
            {String(m.width)} × {String(m.height)}
          </dd>
        </>
      )}
      {m.pages != null && (
        <>
          <dt>頁數</dt>
          <dd>{String(m.pages)}</dd>
        </>
      )}
      {m.duration != null && (
        <>
          <dt>長度</dt>
          <dd>{Number(m.duration).toFixed(2)} 秒</dd>
        </>
      )}
      {streams.map((s, i) => (
        <span className="stream-info" key={i}>
          {s.codec_type} · {s.codec_name}
          {s.width ? ` · ${s.width} × ${s.height}` : ""}
          {s.sample_rate ? ` · ${s.sample_rate} Hz · ${s.channels} ch` : ""}
        </span>
      ))}
      {m.renderedWith != null && (
        <span className="hint stream-info">{String(m.renderedWith)}</span>
      )}
    </dl>
  );
}
export function FilePreview({
  paths,
  onClose,
}: {
  paths: string[];
  onClose: () => void;
}) {
  const [previews, setPreviews] = useState<(RichPreview | null)[]>(
      paths.map(() => null),
    ),
    [errors, setErrors] = useState<string[]>([]),
    [pages, setPages] = useState(paths.map(() => 0)),
    [busy, setBusy] = useState(-1),
    [split, setSplit] = useState(false),
    [position, setPosition] = useState(50);
  async function load(
    index: number,
    page = pages[index],
    play = false,
    time = 0,
  ) {
    setBusy(index);
    try {
      const p = await call<RichPreview>("preview", {
        path: paths[index],
        page,
        play,
        time,
      });
      setPreviews((old) => old.map((v, i) => (i === index ? p : v)));
      setErrors((old) => old.map((v, i) => (i === index ? "" : v)));
    } catch (e) {
      setErrors((old) => {
        const next = [...old];
        next[index] = String(e);
        return next;
      });
    } finally {
      setBusy(-1);
    }
  }
  useEffect(() => {
    let live = true;
    void (async () => {
      for (let i = 0; i < paths.length && live; i++) await load(i, 0);
    })();
    return () => {
      live = false;
    };
  }, [paths.join("|")]);
  const [before, after] = previews;
  return (
    <Modal
      open
      onOpenChange={(v) => !v && onClose()}
      title={paths.length > 1 ? "轉換前後比較" : "檔案預覽"}
      description="預覽以本機引擎產生；影音按下播放預覽後轉碼最多 15 秒。"
    >
      {before && after && (
        <div className="row between">
          <span>
            大小變化 {((1 - after.size / before.size) * 100).toFixed(1)}% ·{" "}
            {bytes(before.size)} → {bytes(after.size)}
          </span>
          {before.image && after.image && (
            <Button onClick={() => setSplit(!split)}>
              {split ? "並排比較" : "滑動比較"}
            </Button>
          )}
        </div>
      )}
      {split && before?.image && after?.image && (
        <div className="image-comparison">
          <img src={before.image} alt="處理前" />
          <img
            src={after.image}
            alt="處理後"
            style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
          />
          <input
            aria-label="比較分隔位置"
            type="range"
            min="0"
            max="100"
            value={position}
            onChange={(e) => setPosition(+e.target.value)}
          />
        </div>
      )}
      <div className={`preview-columns ${paths.length === 1 ? "single" : ""}`}>
        {paths.map((path, i) => {
          const p = previews[i],
            m = p?.metadata,
            stream = m?.streams as { codec_type: string }[] | undefined;
          return (
            <section key={path} className="preview-column">
              <h3 title={path}>
                {i === 0 && paths.length > 1
                  ? "來源 · "
                  : paths.length > 1
                    ? "輸出 · "
                    : ""}
                {path.split(/[\\/]/).pop()}
              </h3>
              {errors[i] && (
                <p role="alert" className="error-text">
                  {errors[i]}
                </p>
              )}
              {!p && !errors[i] && <p role="status">正在產生預覽…</p>}
              {p && (
                <>
                  {!split && p.image && (
                    <img className="preview-image" src={p.image} alt={p.name} />
                  )}
                  {p.text && <pre className="text-preview">{p.text}</pre>}
                  {summary(p)}
                  {Number(m?.pages) > 1 && (
                    <label className="row">
                      頁碼
                      <input
                        type="number"
                        min="1"
                        max={Number(m?.pages)}
                        value={pages[i] + 1}
                        onChange={(e) => {
                          const page = Math.max(
                            0,
                            Math.min(Number(m?.pages) - 1, +e.target.value - 1),
                          );
                          setPages((old) =>
                            old.map((v, n) => (n === i ? page : v)),
                          );
                          void load(i, page);
                        }}
                      />
                    </label>
                  )}
                  {stream?.some(
                    (s) => s.codec_type === "audio" || s.codec_type === "video",
                  ) && (
                    <div className="row">
                      <Button
                        disabled={busy === i}
                        onClick={() => void load(i, pages[i], true)}
                      >
                        {busy === i ? "產生播放片段…" : "播放預覽 · 15 秒"}
                      </Button>
                    </div>
                  )}
                  {p.media &&
                    (p.mediaKind === "video" ? (
                      <video controls src={p.media} />
                    ) : (
                      <audio controls src={p.media} />
                    ))}
                  {!p.image && !p.text && !stream && (
                    <p className="hint">此格式提供資訊預覽。</p>
                  )}
                </>
              )}
            </section>
          );
        })}
      </div>
    </Modal>
  );
}
