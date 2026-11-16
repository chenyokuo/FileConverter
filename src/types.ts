export type Page = "dashboard" | "converter" | "history" | "settings";
export type MaterialName =
  "sidebar" | "main" | "card" | "modal" | "toolbar" | "settings";
export interface Material {
  opacity: number;
  blur: number;
  tint: string;
  border: number;
  shadow: number;
}
export interface Appearance {
  mode: "dark" | "light" | "system";
  background: "aurora" | "gradient" | "solid" | "image";
  image: string;
  color: string;
  accent: string;
  imageOpacity: number;
  brightness: number;
  backgroundBlur: number;
  overlay: number;
  fit: "cover" | "contain";
  positionX: number;
  positionY: number;
  scale: number;
  nativeMica: boolean;
  materials: Record<MaterialName, Material>;
}
export interface Settings {
  appearance: Appearance;
  presets: { name: string; appearance: Appearance }[];
  concurrency: number;
  outputDir: string;
  defaults: Options;
  reducedMotion: boolean;
}
export interface Options {
  quality: number;
  width: number;
  height: number;
  matte: string;
  videoCodec: string;
  crf: number;
  videoBitrate: number;
  videoHeight: number;
  fps: number;
  audioBitrate: number;
  sampleRate: number;
  channels: number;
  pdfDpi: number;
  pages: string;
  rotation: number;
  split: boolean;
}
export interface InputFile {
  path: string;
  name: string;
  size: number;
  extension: string;
  category: string;
  formats: string[];
  preview: string | null;
  dimensions: number[] | null;
  available: boolean;
}
export interface Draft extends InputFile {
  id: string;
  format: string;
  options: Options;
  selected: boolean;
}
export type Status =
  "queued" | "running" | "cancelling" | "completed" | "failed" | "cancelled";
export interface Job {
  id: string;
  sources: string[];
  name: string;
  category: string;
  format: string;
  outputDir: string;
  options: Options;
  status: Status;
  progress: number;
  created: number;
  started?: number;
  finished?: number;
  outputs: string[];
  error: string | null;
}
export interface Engines {
  ffmpeg: string | null;
  ffprobe: string | null;
  soffice: string | null;
}
export interface Snapshot {
  settings: Partial<Settings>;
  jobs: Job[];
  engines: Engines;
  dataDir: string;
}
