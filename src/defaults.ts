import type {
  Appearance,
  Material,
  MaterialName,
  Options,
  Settings,
} from "./types";
export const defaultOptions: Options = {
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
  imageOpacity: 75,
  brightness: 85,
  backgroundBlur: 0,
  overlay: 25,
  fit: "cover",
  positionX: 50,
  positionY: 50,
  scale: 100,
  nativeMica: false,
  materials: {
    sidebar: glass(72, 24, "#0e141f"),
    main: glass(38, 20),
    card: glass(64, 18, "#192231"),
    modal: glass(94, 32),
    toolbar: glass(86, 24),
    settings: glass(70, 24),
  },
};
export const defaults: Settings = {
  appearance: defaultAppearance,
  presets: [],
  concurrency: 2,
  outputDir: "",
  defaults: defaultOptions,
  reducedMotion: false,
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
  return {
    ...defaults,
    ...raw,
    defaults: { ...defaultOptions, ...raw.defaults },
    appearance: {
      ...defaultAppearance,
      ...raw.appearance,
      materials: {
        ...defaultAppearance.materials,
        ...raw.appearance?.materials,
      },
    },
  };
}
