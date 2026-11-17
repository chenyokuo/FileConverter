import type { Options } from "./types";
export interface Clip {
  id: string;
  source: string;
  track: string;
  kind: string;
  at: number;
  in: number;
  out: number;
  speed: number;
  volume: number;
  mute: boolean;
  fadeIn: number;
  fadeOut: number;
  transition: number;
  x: number;
  y: number;
  size: number;
}
export interface Title {
  text: string;
  start: number;
  end: number;
  x: number;
  y: number;
  size: number;
}
export interface VideoProject {
  type: "fcvideo";
  version: 1;
  width: number;
  height: number;
  fps: number;
  clips: Clip[];
  titles: Title[];
  subtitles: string;
  export: Options;
}
export interface Asset {
  path: string;
  name: string;
  kind: string;
  duration: number;
  poster?: string;
  waveform?: string;
  hasAudio?: boolean;
  width?: number;
  height?: number;
}
export const clipLength = (c: Clip) => (c.out - c.in) / c.speed;
export const timelineLength = (p: VideoProject) =>
  Math.max(
    0,
    ...p.clips.map((c) => c.at + clipLength(c)),
    ...p.titles.map((t) => t.end),
  );
export const newClip = (asset: Asset, track: string, at: number): Clip => ({
  id: crypto.randomUUID(),
  source: asset.path,
  track,
  kind: asset.kind,
  at,
  in: 0,
  out: asset.duration,
  speed: 1,
  volume: 1,
  mute: false,
  fadeIn: 0,
  fadeOut: 0,
  transition: 0,
  x: 0.65,
  y: 0.65,
  size: 0.3,
});
