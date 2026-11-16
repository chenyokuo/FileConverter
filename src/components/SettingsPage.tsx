import { AppIcon } from "./AppIcon";
import { ContextIntegration } from "./ContextIntegration";
import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { motion, AnimatePresence } from "motion/react";
import {
  Check,
  ChevronDown,
  Cpu,
  FolderOpen,
  ImagePlus,
  Info,
  Layers3,
  Palette,
  RefreshCw,
  RotateCcw,
  Save,
  Settings2,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  backgroundPreset,
  defaultAppearance,
  materialNames,
} from "../defaults";
import { call, desktop, pickFiles, pickFolder } from "../api";
import type { Appearance, Engines, MaterialName, Settings } from "../types";
import { Button, Modal, Slider, Toggle } from "./ui";
const sections = [
  ["appearance", "個人化外觀", Palette],
  ["conversion", "轉檔偏好", Settings2],
  ["performance", "效能", Cpu],
  ["files", "檔案管理", FolderOpen],
  ["advanced", "進階", ShieldCheck],
  ["about", "關於 File Converter", Info],
] as const;
export function SettingsPage({
  settings,
  setSettings,
  engines,
  refresh,
  notify,
  dataDir,
}: {
  settings: Settings;
  setSettings: (v: Settings) => void;
  engines: Engines;
  refresh: () => void;
  notify: (s: string, error?: boolean) => void;
  dataDir: string;
}) {
  const [section, setSection] = useState("appearance");
  const [material, setMaterial] = useState<MaterialName>("card");
  const [expanded, setExpanded] = useState(true);
  const [saveOpen, setSaveOpen] = useState(false);
  const [presetName, setPresetName] = useState("");
  const a = settings.appearance;
  const appearance = (patch: Partial<Appearance>) =>
    setSettings({ ...settings, appearance: { ...a, ...patch } });
  const applyAppearance = async (value: Appearance) => {
    let next = value;
    if (desktop)
      try {
        await invoke("native_material", { enabled: value.nativeMica });
      } catch (error) {
        notify(`Mica 無法啟用，使用 CSS 玻璃：${String(error)}`, true);
        next = { ...value, nativeMica: false };
      }
    setSettings({ ...settings, appearance: structuredClone(next) });
  };
  const importBackground = async () => {
    try {
      const paths = await pickFiles(true);
      if (paths[0]) {
        const image = await call<string>("background", { path: paths[0] });
        appearance({ image, background: "image", backgroundBlur: 0 });
        notify("背景已匯入，外觀自動儲存");
      }
    } catch (error) {
      notify(String(error), true);
    }
  };
  const m = a.materials[material];
  const updateMaterial = (patch: Partial<typeof m>) =>
    appearance({
      materials: { ...a.materials, [material]: { ...m, ...patch } },
    });
  const folder = async () => {
    try {
      const path = await pickFolder();
      if (path) setSettings({ ...settings, outputDir: path });
    } catch (e) {
      notify(String(e), true);
    }
  };
  return (
    <div className="settings-layout">
      <nav className="settings-nav" aria-label="設定分類">
        {sections.map(([id, label, Icon]) => (
          <button
            key={id}
            className={section === id ? "active" : ""}
            onClick={() => setSection(id)}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}
      </nav>
      <div className="settings-content">
        <AnimatePresence mode="wait">
          <motion.div
            key={section}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.16 }}
          >
            {section === "appearance" && (
              <>
                <div className="section-heading">
                  <div>
                    <h2>個人化外觀</h2>
                    <p>所有調整即時預覽並自動儲存。</p>
                  </div>
                  <Button
                    compact
                    onClick={() => applyAppearance(defaultAppearance)}
                  >
                    <RotateCcw size={15} />
                    恢復預設
                  </Button>
                </div>
                <section
                  className="appearance-presets"
                  aria-label="背景預設配置"
                >
                  <Button
                    onClick={() =>
                      applyAppearance(backgroundPreset(a, "clear"))
                    }
                  >
                    清晰背景
                  </Button>
                  <Button
                    onClick={() =>
                      applyAppearance(backgroundPreset(a, "frosted"))
                    }
                  >
                    毛玻璃背景
                  </Button>
                  <span className="hint">
                    清晰背景為 0px；毛玻璃背景才會套用圖片模糊。
                  </span>
                </section>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  <div className="row between">
                    <h3>
                      <Palette size={17} />
                      外觀模式
                    </h3>
                    <span className="badge">即時預覽</span>
                  </div>
                  <div className="theme-grid">
                    {(["dark", "light", "system"] as const).map((mode, i) => (
                      <button
                        key={mode}
                        className={`theme-option ${a.mode === mode ? "selected" : ""}`}
                        onClick={() => appearance({ mode })}
                      >
                        <span className={`theme-mini ${mode}`}>
                          <i />
                          <i />
                          <i />
                        </span>
                        <span className="row between">
                          {["深色", "淺色", "跟隨系統"][i]}
                          {a.mode === mode && <Check size={14} />}
                        </span>
                      </button>
                    ))}
                  </div>
                  <div className="color-row">
                    <div>
                      <strong>強調色</strong>
                      <p className="hint">按鈕、選取狀態與進度指示</p>
                    </div>
                    <div className="row">
                      {[
                        "#4f8cff",
                        "#a78bfa",
                        "#2dd4bf",
                        "#f59e0b",
                        "#fb7185",
                      ].map((color) => (
                        <button
                          key={color}
                          className={`swatch ${a.accent === color ? "selected" : ""}`}
                          aria-label={`強調色 ${color}`}
                          style={{ background: color }}
                          onClick={() => appearance({ accent: color })}
                        />
                      ))}
                      <input
                        aria-label="自訂強調色"
                        type="color"
                        value={a.accent}
                        onChange={(e) => appearance({ accent: e.target.value })}
                      />
                    </div>
                  </div>
                </section>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  <div className="row between">
                    <h3>
                      <ImagePlus size={17} />
                      背景畫布
                    </h3>
                    <Button compact onClick={importBackground}>
                      <ImagePlus size={15} />
                      匯入圖片
                    </Button>
                  </div>
                  <div className="background-choices">
                    {(["aurora", "gradient", "solid", "image"] as const).map(
                      (bg, i) => (
                        <button
                          key={bg}
                          className={`background-choice ${bg} ${a.background === bg ? "selected" : ""}`}
                          disabled={bg === "image" && !a.image}
                          style={
                            bg === "image" && a.image
                              ? { backgroundImage: `url(${a.image})` }
                              : undefined
                          }
                          onClick={() => appearance({ background: bg })}
                        >
                          <span>
                            {
                              ["預設背景", "暮光漸層", "純粹單色", "我的圖片"][
                                i
                              ]
                            }
                          </span>
                          {a.background === bg && <Check size={15} />}
                        </button>
                      ),
                    )}
                  </div>
                  {a.background === "solid" && (
                    <label className="color-row">
                      <span>背景顏色</span>
                      <input
                        aria-label="背景顏色"
                        type="color"
                        value={a.color}
                        onChange={(e) => appearance({ color: e.target.value })}
                      />
                    </label>
                  )}
                  <div className="two-col controls-grid">
                    <Slider
                      label="背景圖片透明度"
                      value={a.imageOpacity}
                      onChange={(v) => appearance({ imageOpacity: v })}
                    />
                    <Slider
                      label="背景亮度"
                      value={a.brightness}
                      min={10}
                      max={150}
                      onChange={(v) => appearance({ brightness: v })}
                    />
                    <Slider
                      label="背景模糊"
                      value={a.backgroundBlur}
                      max={60}
                      unit="px"
                      onChange={(v) => appearance({ backgroundBlur: v })}
                    />
                    <Slider
                      label="暗色遮罩"
                      value={a.overlay}
                      max={90}
                      onChange={(v) => appearance({ overlay: v })}
                    />
                  </div>
                  {a.background === "image" && (
                    <div className="image-position">
                      <label className="field">
                        <span>圖片填滿方式</span>
                        <select
                          value={a.fit}
                          onChange={(e) =>
                            appearance({
                              fit: e.target.value as Appearance["fit"],
                            })
                          }
                        >
                          <option value="cover">裁切填滿 Cover</option>
                          <option value="contain">完整顯示 Contain</option>
                        </select>
                      </label>
                      <div className="two-col">
                        <Slider
                          label="水平位置"
                          value={a.positionX}
                          onChange={(v) => appearance({ positionX: v })}
                        />
                        <Slider
                          label="垂直位置"
                          value={a.positionY}
                          onChange={(v) => appearance({ positionY: v })}
                        />
                      </div>
                      <Slider
                        label="圖片縮放"
                        value={a.scale}
                        min={100}
                        max={200}
                        onChange={(v) => appearance({ scale: v })}
                      />
                      <p className="hint">
                        原始圖片會複製到應用程式資料；移動原檔不會影響背景。
                      </p>
                    </div>
                  )}
                </section>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  <button
                    className="disclosure row between"
                    onClick={() => setExpanded(!expanded)}
                    aria-expanded={expanded}
                  >
                    <h3>
                      <Layers3 size={17} />
                      分層玻璃材質
                    </h3>
                    <ChevronDown
                      size={17}
                      style={{
                        transform: expanded ? "rotate(180deg)" : undefined,
                      }}
                    />
                  </button>
                  <AnimatePresence>
                    {expanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        style={{ overflow: "hidden" }}
                        transition={{ duration: 0.22 }}
                      >
                        <p className="hint">
                          只改變材質底層，保留文字、圖示與操作元件的清晰度。
                        </p>
                        <div className="material-tabs">
                          {Object.entries(materialNames).map(([id, name]) => (
                            <button
                              key={id}
                              className={material === id ? "active" : ""}
                              onClick={() => setMaterial(id as MaterialName)}
                            >
                              {name}
                            </button>
                          ))}
                        </div>
                        <div className="two-col controls-grid">
                          <Slider
                            label="面板不透明度"
                            value={m.opacity}
                            min={0}
                            onChange={(v) => updateMaterial({ opacity: v })}
                          />
                          {material !== "main" ? (
                            <Slider
                              label="玻璃模糊"
                              value={m.blur}
                              max={60}
                              unit="px"
                              onChange={(v) => updateMaterial({ blur: v })}
                            />
                          ) : (
                            <p className="hint workspace-blur-note">
                              主工作區不套用模糊；背景保持清晰。
                            </p>
                          )}
                          <Slider
                            label="邊框可見度"
                            value={m.border}
                            max={40}
                            onChange={(v) => updateMaterial({ border: v })}
                          />
                          <Slider
                            label="陰影強度"
                            value={m.shadow}
                            max={60}
                            onChange={(v) => updateMaterial({ shadow: v })}
                          />
                        </div>
                        <label className="color-row">
                          <span>材質底色</span>
                          <input
                            aria-label="材質底色"
                            type="color"
                            value={m.tint}
                            onChange={(e) =>
                              updateMaterial({ tint: e.target.value })
                            }
                          />
                        </label>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  <Toggle
                    label="Windows 11 Mica"
                    description="原生視窗底層材質；不支援時自動退回 CSS 玻璃。"
                    checked={a.nativeMica}
                    onChange={(v) => applyAppearance({ ...a, nativeMica: v })}
                  />
                  <div className="inline-note">
                    <Info size={16} />
                    <span>
                      整個視窗透明度尚未提供；以上設定只調整背景與玻璃面板。
                    </span>
                  </div>
                </section>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  <div className="row between">
                    <h3>外觀預設配置</h3>
                    <Button
                      compact
                      onClick={() => {
                        setPresetName("");
                        setSaveOpen(true);
                      }}
                    >
                      <Save size={15} />
                      儲存目前外觀
                    </Button>
                  </div>
                  {settings.presets.length ? (
                    settings.presets.map((preset, i) => (
                      <div className="preset-row" key={i}>
                        <span
                          className="preset-dot"
                          style={{ background: preset.appearance.accent }}
                        />
                        <span>{preset.name}</span>
                        <Button
                          compact
                          onClick={() => applyAppearance(preset.appearance)}
                        >
                          套用
                        </Button>
                        <Button
                          compact
                          aria-label={`刪除 ${preset.name}`}
                          onClick={() =>
                            setSettings({
                              ...settings,
                              presets: settings.presets.filter(
                                (_, index) => index !== i,
                              ),
                            })
                          }
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    ))
                  ) : (
                    <p className="hint">
                      把喜歡的配色與玻璃設定存起來，隨時切換。
                    </p>
                  )}
                </section>
              </>
            )}
            {section === "conversion" && (
              <>
                <div className="section-heading">
                  <div>
                    <h2>轉檔偏好</h2>
                    <p>新加入檔案的預設參數，單檔仍可個別調整。</p>
                  </div>
                </div>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  <Slider
                    label="預設圖片品質"
                    min={1}
                    value={settings.defaults.quality}
                    onChange={(v) =>
                      setSettings({
                        ...settings,
                        defaults: { ...settings.defaults, quality: v },
                      })
                    }
                  />
                  <Slider
                    label="預設影片 CRF"
                    max={51}
                    unit=""
                    value={settings.defaults.crf}
                    onChange={(v) =>
                      setSettings({
                        ...settings,
                        defaults: { ...settings.defaults, crf: v },
                      })
                    }
                  />
                  <p className="hint">
                    預設影音為 CPU H.264 / 192 kbps
                    音訊。只有合法輸出格式會出現在檔案選單。
                  </p>
                </section>
              </>
            )}
            {section === "performance" && (
              <>
                <div className="section-heading">
                  <div>
                    <h2>效能</h2>
                    <p>轉檔在獨立程序執行，介面持續保持回應。</p>
                  </div>
                </div>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  <Slider
                    label="同時轉檔任務"
                    value={settings.concurrency}
                    min={1}
                    max={4}
                    unit=" 個"
                    onChange={(v) =>
                      setSettings({ ...settings, concurrency: v })
                    }
                  />
                  <p className="hint">
                    影片轉檔建議 1–2 個；較多並行會使用更多記憶體。
                  </p>
                  <Toggle
                    label="減少動態效果"
                    description="系統的 Reduced Motion 偏好也會自動生效。"
                    checked={settings.reducedMotion}
                    onChange={(v) =>
                      setSettings({ ...settings, reducedMotion: v })
                    }
                  />
                </section>
              </>
            )}
            {section === "files" && (
              <>
                <div className="section-heading">
                  <div>
                    <h2>檔案管理</h2>
                    <p>保護原始檔案；同名輸出會自動加上編號。</p>
                  </div>
                </div>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  <h3>預設輸出位置</h3>
                  <p className="path-box">
                    {settings.outputDir ||
                      "來源檔案所在資料夾 / File Converter Output"}
                  </p>
                  <div className="row">
                    <Button onClick={folder}>
                      <FolderOpen size={16} />
                      選擇資料夾
                    </Button>
                    <Button
                      onClick={() =>
                        setSettings({ ...settings, outputDir: "" })
                      }
                    >
                      使用來源位置
                    </Button>
                  </div>
                  <hr />
                  <h3>應用程式資料</h3>
                  <p className="path-box">{dataDir || "桌面版本啟動後顯示"}</p>
                  <p className="hint">
                    設定、背景與轉檔紀錄只保存在本機。清除紀錄不會刪除任何來源或輸出檔案。
                  </p>
                </section>
              </>
            )}
            {section === "advanced" && (
              <>
                <ContextIntegration notify={notify} />
                <div className="section-heading">
                  <div>
                    <h2>引擎與離線狀態</h2>
                    <p>缺少必要引擎時，會顯示具體原因。</p>
                  </div>
                  <Button compact onClick={refresh}>
                    <RefreshCw size={15} />
                    重新檢測
                  </Button>
                </div>
                <section
                  className="settings-card glass"
                  data-material="settings"
                >
                  {Object.entries(engines).map(([name, path]) => (
                    <div className="engine-row" key={name}>
                      <span
                        className={`status-dot ${path ? "green" : "amber"}`}
                      />
                      <div>
                        <strong>
                          {name === "soffice" ? "LibreOffice" : name}
                        </strong>
                        <p className="path-box">
                          {path || "未安裝 · 此引擎對應的功能暫不可用"}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div className="inline-note">
                    <ShieldCheck size={18} />
                    <span>
                      使用隨附的離線 Runtime。若顯示缺少引擎，請修復 File
                      Converter 套件。
                    </span>
                  </div>
                  <hr />
                  <h3>功能邊界</h3>
                  <p className="hint">
                    PDF → DOCX 可能失去版面保真；掃描文件請先
                    OCR。原生整窗透明度仍未通過相容性驗證。硬體編碼會先實際探測，失敗後使用
                    CPU 備援。
                  </p>
                </section>
              </>
            )}
            {section === "about" && (
              <section
                className="about-card settings-card glass"
                data-material="settings"
              >
                <AppIcon size={80} />

                <h2>File Converter</h2>

                <span className="badge">v1.0.0-rc.1 · Windows x64</span>
                <hr />
                <div className="about-stack">
                  <p>React · Tauri · Rust · Python</p>
                  <p>Pillow · PyMuPDF · FFmpeg · LibreOffice</p>
                  <p>
                    本專案採
                    AGPL-3.0-or-later。外部元件依各自授權散布；完整說明隨安裝包附帶。
                  </p>
                </div>
              </section>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
      <Modal
        open={saveOpen}
        onOpenChange={setSaveOpen}
        title="儲存外觀配置"
        description="保存背景、色彩與每一層玻璃材質。"
      >
        <label className="field">
          <span>配置名稱</span>
          <input
            autoFocus
            maxLength={60}
            value={presetName}
            placeholder="例如：午夜工作室"
            onChange={(e) => setPresetName(e.target.value)}
          />
        </label>
        <Button
          variant="primary"
          disabled={!presetName.trim()}
          onClick={() => {
            setSettings({
              ...settings,
              presets: [
                ...settings.presets,
                { name: presetName.trim(), appearance: structuredClone(a) },
              ],
            });
            setSaveOpen(false);
            notify("外觀配置已儲存");
          }}
        >
          <Save size={16} />
          儲存配置
        </Button>
      </Modal>
    </div>
  );
}
