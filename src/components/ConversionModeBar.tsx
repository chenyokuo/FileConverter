import { ArrowRight } from "lucide-react";
import type { ConversionMode, Draft, Registry } from "../types";
import { Button } from "./ui";

interface Props {
  mode: ConversionMode;
  setMode: (v: ConversionMode) => void;
  source: string;
  target: string;
  setSource: (v: string) => void;
  setTarget: (v: string) => void;
  registry: Registry;
  drafts: Draft[];
  apply: (target: string, source?: string) => void;
}
export function ConversionModeBar(p: Props) {
  const selected = p.drafts.filter((f) => f.selected);
  const edges = p.registry.edges.filter((e) =>
    p.mode === "preset"
      ? e.source === p.source
      : selected.some((f) => f.extension === e.source),
  );
  const targets = [...new Set(edges.map((e) => e.target))];
  return (
    <section
      className="mode-bar glass"
      data-material="toolbar"
      aria-label="轉換模式與格式"
    >
      <div className="mode-switch" role="group" aria-label="轉換模式">
        <button
          aria-pressed={p.mode === "auto"}
          onClick={() => p.setMode("auto")}
        >
          智慧自動辨識
        </button>
        <button
          aria-pressed={p.mode === "preset"}
          onClick={() => p.setMode("preset")}
        >
          指定格式轉換
        </button>
      </div>
      {p.mode === "preset" ? (
        <div className="preset-format-row">
          <label>
            來源格式
            <select
              aria-label="指定來源格式"
              value={p.source}
              onChange={(e) => p.setSource(e.target.value)}
            >
              <option value="">選擇來源</option>
              {p.registry.sources.map((s) => (
                <option key={s} value={s}>
                  {s.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
          <ArrowRight size={18} />
          <label>
            目標格式
            <select
              aria-label="指定目標格式"
              value={p.target}
              onChange={(e) => p.setTarget(e.target.value)}
            >
              <option value="">選擇目標</option>
              {targets.map((t) => {
                const edge = edges.find((e) => e.target === t)!;
                return (
                  <option key={t} value={t} disabled={!edge.available}>
                    {t.toUpperCase()}
                    {!edge.available ? " · 引擎未安裝" : ""}
                  </option>
                );
              })}
            </select>
          </label>
          <Button
            compact
            disabled={!p.source || !p.target || !selected.length}
            onClick={() => p.apply(p.target, p.source)}
          >
            套用至勾選檔案
          </Button>
          {p.source && edges.every((e) => !e.available) && (
            <span className="hint">{edges[0]?.reason}</span>
          )}
        </div>
      ) : (
        <div className="quick-formats">
          <span>快速套用</span>
          {targets.length ? (
            targets.slice(0, 12).map((t) => (
              <button
                key={t}
                onClick={() => p.apply(t)}
                disabled={!edges.some((e) => e.target === t && e.available)}
              >
                {t.toUpperCase()}
              </button>
            ))
          ) : (
            <span className="hint">匯入後，依實際內容顯示合法格式</span>
          )}
        </div>
      )}
    </section>
  );
}
