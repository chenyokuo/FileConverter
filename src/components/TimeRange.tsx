import { useRef, useState, type PointerEvent } from "react";
export type TimeSpan = { start: number; end: number };
export function timecode(n: number) {
  const s = Math.max(0, Math.floor(Number.isFinite(n) ? n : 0));
  return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
}
function parse(value: string): number | null {
  if (!/^\d{1,6}:[0-5]\d:[0-5]\d$/.test(value)) return null;
  return value.split(":").reduce((n, v) => n * 60 + Number(v), 0);
}
function TimeInput({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  disabled: boolean;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const [error, setError] = useState(false);
  return (
    <label className="field">
      <span>{label}</span>
      <input
        aria-label={label}
        aria-invalid={error}
        disabled={disabled}
        value={draft ?? timecode(value)}
        inputMode="numeric"
        onChange={(e) => {
          setDraft(e.target.value);
          setError(false);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          if (e.key === "Escape") {
            setDraft(null);
            setError(false);
            e.currentTarget.blur();
          }
        }}
        onBlur={() => {
          if (draft === null) return;
          const n = parse(draft);
          if (n === null) {
            setError(true);
            return;
          }
          onChange(n);
          setDraft(null);
          setError(false);
        }}
      />
      {error && <span role="alert">請輸入 HH:MM:SS</span>}
    </label>
  );
}
export function TimeRange({
  duration,
  range,
  current,
  onChange,
  onSeek,
  disabled = false,
}: {
  duration: number;
  range: TimeSpan;
  current: number;
  onChange: (v: TimeSpan) => void;
  onSeek: (v: number) => void;
  disabled?: boolean;
}) {
  const track = useRef<HTMLDivElement>(null);
  const inactive = disabled || !Number.isFinite(duration) || duration <= 0;
  const minimum = Math.min(1, duration);
  const update = (edge: "start" | "end", n: number) =>
    onChange(
      edge === "start"
        ? { ...range, start: Math.max(0, Math.min(n, range.end - minimum)) }
        : {
            ...range,
            end: Math.min(duration, Math.max(n, range.start + minimum)),
          },
    );
  const seek = (e: PointerEvent<HTMLElement>) => {
    const box = track.current!.getBoundingClientRect();
    return Math.max(
      0,
      Math.min(duration, ((e.clientX - box.left) / box.width) * duration),
    );
  };
  const drag = (e: PointerEvent<HTMLButtonElement>, edge?: "start" | "end") => {
    if (inactive) return;
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    if (edge) update(edge, seek(e));
    else onSeek(seek(e));
  };
  const percent = (n: number) =>
    `${!duration ? 0 : Math.max(0, Math.min(100, (n / duration) * 100))}%`;
  return (
    <section className="time-range" aria-label="影片區間選取">
      <div className="row between">
        <strong>選取下載區間</strong>
        <span>總長度 {inactive ? "未知" : timecode(duration)}</span>
      </div>
      <div
        ref={track}
        className={`range-track ${inactive ? "inactive" : ""}`}
        onPointerDown={(e) => {
          if (!inactive) onSeek(seek(e));
        }}
      >
        <div className="range-ticks" aria-hidden="true">
          {Array.from({ length: 9 }, (_, i) => (
            <span key={i}>{timecode((duration * i) / 8)}</span>
          ))}
        </div>
        <div
          className="range-selection"
          style={{
            left: percent(range.start),
            width: percent(range.end - range.start),
          }}
        />
        {(["start", "end"] as const).map((edge) => (
          <button
            key={edge}
            type="button"
            className={`range-handle ${edge}`}
            role="slider"
            aria-label={edge === "start" ? "起點把手" : "終點把手"}
            aria-valuemin={edge === "start" ? 0 : range.start + minimum}
            aria-valuemax={edge === "start" ? range.end - minimum : duration}
            aria-valuenow={range[edge]}
            aria-valuetext={timecode(range[edge])}
            disabled={inactive}
            style={{ left: percent(range[edge]) }}
            onPointerDown={(e) => drag(e, edge)}
            onPointerMove={(e) => {
              if (e.currentTarget.hasPointerCapture(e.pointerId))
                update(edge, seek(e));
            }}
            onKeyDown={(e) => {
              if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
                e.preventDefault();
                update(
                  edge,
                  e.key === "Home"
                    ? 0
                    : e.key === "End"
                      ? duration
                      : range[edge] +
                        (e.key === "ArrowRight" ? 1 : -1) *
                          (e.shiftKey ? 10 : 1),
                );
              }
            }}
          >
            <span />
          </button>
        ))}
        <button
          type="button"
          className="range-playhead"
          role="slider"
          aria-label="播放位置"
          aria-valuemin={0}
          aria-valuemax={duration || 0}
          aria-valuenow={current}
          disabled={inactive}
          style={{ left: percent(current) }}
          onPointerDown={(e) => drag(e)}
          onPointerMove={(e) => {
            if (e.currentTarget.hasPointerCapture(e.pointerId)) onSeek(seek(e));
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
              e.preventDefault();
              onSeek(
                Math.max(
                  0,
                  Math.min(
                    duration,
                    current + (e.key === "ArrowRight" ? 1 : -1),
                  ),
                ),
              );
            }
          }}
        />
      </div>
      <div className="range-inputs">
        {(["start", "end"] as const).map((edge) => (
          <div key={edge}>
            <TimeInput
              label={edge === "start" ? "起始時間" : "結束時間"}
              disabled={inactive}
              value={range[edge]}
              onChange={(n) => update(edge, n)}
            />
            <input
              type="range"
              aria-label={edge === "start" ? "調整起始時間" : "調整結束時間"}
              disabled={inactive}
              min={0}
              max={duration || 1}
              step={1}
              value={range[edge]}
              onChange={(e) => update(edge, Number(e.target.value))}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
