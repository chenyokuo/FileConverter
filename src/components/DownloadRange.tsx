import { useRef, useState } from "react";
import { Play, RotateCcw, Plus, X } from "lucide-react";
import { Button } from "./ui";
import { TimeRange, timecode, type TimeSpan } from "./TimeRange";
export interface RangeOptions {
  only: boolean;
  ranges: TimeSpan[];
  precise: boolean;
  merge: boolean;
}
export const defaultRanges = (): RangeOptions => ({
  only: false,
  ranges: [],
  precise: false,
  merge: false,
});
export function DownloadRange({
  duration = 0,
  previewUrl,
  loading,
  value,
  onChange,
}: {
  duration?: number;
  previewUrl?: string;
  loading: boolean;
  value: RangeOptions;
  onChange: (v: RangeOptions) => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [current, setCurrent] = useState(0);
  const [failed, setFailed] = useState(false);
  const [buffering, setBuffering] = useState(true);
  const [active, setActive] = useState(0);
  const known = Number.isFinite(duration) && duration > 0;
  const ranges = value.ranges.length
    ? value.ranges
    : [{ start: 0, end: known ? duration : 0 }];
  const index = Math.min(active, ranges.length - 1);
  const range = ranges[index];
  const seek = (n: number) => {
    setCurrent(n);
    if (video.current && Number.isFinite(video.current.duration))
      video.current.currentTime = n;
  };
  return (
    <div className="download-range glass" data-material="card">
      <div className="range-player">
        {previewUrl && !failed ? (
          <video
            ref={video}
            src={previewUrl}
            controls
            playsInline
            preload="metadata"
            onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime)}
            onWaiting={() => setBuffering(true)}
            onCanPlay={() => setBuffering(false)}
            onError={() => setFailed(true)}
          />
        ) : (
          <div className="range-player-empty">
            <Play size={38} />
            <span>{loading ? "正在載入影片資訊…" : "影片預覽區"}</span>
            {!loading && (
              <span className="hint">
                {failed
                  ? "來源無法在播放器預覽，仍可使用已知長度選取下載區間。"
                  : previewUrl
                    ? ""
                    : "此來源未提供可直接播放的影音串流。"}
              </span>
            )}
          </div>
        )}
        {previewUrl && !failed && buffering && (
          <span className="range-buffering" role="status">
            影片載入中…
          </span>
        )}
      </div>
      {!known && !loading && (
        <p className="hint" role="status">
          影片長度未知或為直播，區間選取已停用；仍可下載完整來源。
        </p>
      )}
      <TimeRange
        duration={duration}
        range={range}
        current={current}
        disabled={loading}
        onSeek={seek}
        onChange={(next) =>
          onChange({
            ...value,
            ranges: ranges.map((r, i) => (i === index ? next : r)),
          })
        }
      />
      <div className="row between range-footer">
        <strong>選取時長：{timecode(range.end - range.start)}</strong>
        <label>
          <input
            type="checkbox"
            disabled={!known || loading}
            checked={value.only && known}
            onChange={(e) =>
              onChange({ ...value, only: e.target.checked, ranges })
            }
          />
          只輸出所選片段
        </label>
      </div>
      <div className="row range-actions">
        <Button
          compact
          disabled={!known || loading}
          onClick={() => {
            onChange({ ...value, ranges: [{ start: 0, end: duration }] });
            setActive(0);
          }}
        >
          <RotateCcw size={16} />
          重設區間
        </Button>
        <Button
          compact
          disabled={!known || loading}
          onClick={() => {
            onChange({
              ...value,
              only: true,
              ranges: [...ranges, { start: 0, end: duration }],
            });
            setActive(ranges.length);
          }}
        >
          <Plus size={16} />
          新增區間
        </Button>
        {ranges.map((r, i) => (
          <div className="row" key={i}>
            <Button
              compact
              disabled={!known || loading}
              aria-pressed={index === i}
              onClick={() => setActive(i)}
            >
              片段 {i + 1} · {timecode(r.end - r.start)}
            </Button>
            {ranges.length > 1 && (
              <Button
                compact
                aria-label={`移除片段 ${i + 1}`}
                onClick={() => {
                  onChange({
                    ...value,
                    ranges: ranges.filter((_, n) => n !== i),
                  });
                  setActive(0);
                }}
              >
                <X size={14} />
              </Button>
            )}
          </div>
        ))}
      </div>
      {value.only && (
        <div className="range-inputs">
          <label className="field">
            <span>裁切方式</span>
            <select
              value={value.precise ? "precise" : "fast"}
              onChange={(e) =>
                onChange({ ...value, precise: e.target.value === "precise" })
              }
            >
              <option value="fast">快速裁切（切點可能依關鍵影格偏移）</option>
              <option value="precise">精確裁切（重新編碼，較慢）</option>
            </select>
          </label>
          <label className="field">
            <span>多片段輸出</span>
            <select
              value={value.merge ? "merge" : "separate"}
              onChange={(e) =>
                onChange({ ...value, merge: e.target.value === "merge" })
              }
            >
              <option value="separate">各片段分別輸出</option>
              <option value="merge">依清單順序合併</option>
            </select>
          </label>
        </div>
      )}
    </div>
  );
}
