import type {
  Appearance,
  Material,
  MaterialName,
  Options,
  Settings,
} from "./types";
export const defaultOptions: Options = {
  hardware: "auto",
  hardwareDecode: true,
  qualityPreset: "balanced",
  quality: 90,
  width: 0,
  height: 0,
  matte: "#ffffff",
  videoCodec: "h264",
  crf: 23,
  videoBitrate: 0,
  videoHeight: 0,
  fps: 0,
  audioBitrate: 192,
  sampleRate: 0,
  channels: 0,
  pdfDpi: 144,
  pages: "",
  rotation: 0,
  split: false,
};
const glass = (opacity: number, blur: number, tint = "#141a25"): Material => ({
  opacity,
  blur,
  tint,
  border: 9,
  shadow: 24,
});
export const defaultAppearance: Appearance = {
  mode: "dark",
  background: "aurora",
  image: "",
  color: "#0b0f17",
  accent: "#4f8cff",
  imageOpacity: 100,
  brightness: 100,
  backgroundBlur: 0,
  overlay: 10,
  fit: "cover",
  positionX: 50,
  positionY: 50,
  scale: 100,
  nativeMica: false,
  materials: {
    sidebar: glass(78, 12, "#0e141f"),
    main: glass(8, 0, "#0b0f17"),
    card: glass(72, 10, "#141a25"),
    modal: glass(94, 18),
    toolbar: glass(88, 12),
    settings: glass(80, 12),
  },
};
export const defaults: Settings = {
  appearanceVersion: 2,
  appearance: defaultAppearance,
  presets: [],
  concurrency: 2,
  outputDir: "",
  defaults: defaultOptions,
  reducedMotion: false,
  sidebarCollapsed: false,
};
export const materialNames: Record<MaterialName, string> = {
  sidebar: "側邊導覽",
  main: "主工作區",
  card: "檔案卡片",
  modal: "對話視窗",
  toolbar: "浮動工具列",
  settings: "設定面板",
};
export function mergeSettings(raw: Partial<Settings>): Settings {
  const materials = Object.fromEntries(
    Object.entries(defaultAppearance.materials).map(([key, value]) => [
      key,
      { ...value, ...raw.appearance?.materials?.[key as MaterialName] },
    ]),
  ) as Appearance["materials"];
  // The workspace is a tint layer, never a backdrop blur over the whole image.
  materials.main.blur = 0;
  const legacy = !raw.appearanceVersion;
  if (legacy && raw.appearance?.materials?.main?.opacity === 38)
    materials.main.opacity = defaultAppearance.materials.main.opacity;
  return {
    ...defaults,
    ...raw,
    appearanceVersion: 2,
    defaults: { ...defaultOptions, ...raw.defaults },
    appearance: {
      ...defaultAppearance,
      ...raw.appearance,
      ...(legacy
        ? {
            imageOpacity:
              raw.appearance?.imageOpacity === 75
                ? 100
                : (raw.appearance?.imageOpacity ?? 100),
            brightness:
              raw.appearance?.brightness === 85
                ? 100
                : (raw.appearance?.brightness ?? 100),
            overlay:
              raw.appearance?.overlay === 25
                ? 10
                : (raw.appearance?.overlay ?? 10),
          }
        : {}),
      materials,
    },
  };
}

export function backgroundPreset(
  a: Appearance,
  kind: "clear" | "frosted",
): Appearance {
  return {
    ...a,
    imageOpacity: 100,
    brightness: kind === "clear" ? 100 : 95,
    backgroundBlur: kind === "clear" ? 0 : 12,
    overlay: kind === "clear" ? 10 : 15,
    materials: {
      ...structuredClone(defaultAppearance.materials),
      ...Object.fromEntries(
        Object.entries(a.materials).map(([key, value]) => [
          key,
          {
            ...value,
            opacity: defaultAppearance.materials[key as MaterialName].opacity,
            blur:
              key === "main"
                ? 0
                : kind === "clear"
                  ? defaultAppearance.materials[key as MaterialName].blur
                  : 16,
          },
        ]),
      ),
    },
  };
}
