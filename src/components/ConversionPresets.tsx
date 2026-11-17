import { useEffect, useState } from "react";
import { call, desktop } from "../api";
import type { Draft, Options } from "../types";
import type { AutomationItem } from "./AutomationPage";
import { Button } from "./ui";
export function ConversionPresets({
  focused,
  onApply,
  notify,
}: {
  focused?: Draft;
  onApply: (source: string, target: string, options: Partial<Options>) => void;
  notify: (s: string, error?: boolean) => void;
}) {
  const [items, setItems] = useState<AutomationItem[]>([]),
    [selected, setSelected] = useState(""),
    [name, setName] = useState("");
  async function refresh() {
    if (!desktop) return;
    try {
      const result = await call<{ items: AutomationItem[] }>("automation");
      setItems(result.items.filter((i) => i.kind === "preset"));
    } catch (e) {
      notify(String(e), true);
    }
  }
  useEffect(() => {
    void refresh();
  }, []);
  return (
    <details className="conversion-presets-panel">
      <summary>轉檔預設</summary>
      <div className="conversion-presets row wrap">
        <label>
          轉檔預設
          <select
            aria-label="已保存的轉檔預設"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">選擇配置</option>
            {items.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.config.source} → {p.config.target}
              </option>
            ))}
          </select>
        </label>
        <Button
          compact
          disabled={!selected}
          onClick={() => {
            const p = items.find((i) => i.id === selected);
            if (p) {
              const step = p.config.steps[0];
              onApply(p.config.source, step.target || "", step.options || {});
            }
          }}
        >
          套用至相符的勾選檔案
        </Button>
        <input
          aria-label="新轉檔預設名稱"
          placeholder="預設名稱"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button
          compact
          disabled={!desktop || !focused?.format || !name.trim()}
          onClick={async () => {
            try {
              const config = {
                name: name.trim(),
                source: focused!.extension,
                steps: [
                  {
                    type: "convert",
                    target: focused!.format,
                    options: focused!.options,
                  },
                ],
                onError: "abort",
              };
              await call("save_automation", { kind: "preset", config });
              await refresh();
              setName("");
              notify("已保存轉檔預設；可在自動化工作流程編輯或刪除");
            } catch (e) {
              notify(String(e), true);
            }
          }}
        >
          保存目前設定
        </Button>
      </div>
    </details>
  );
}
