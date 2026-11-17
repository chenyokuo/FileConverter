import type { Options } from "./types";
export interface Clip {
  pairId?: string;
  linked?: boolean;
  videoOnly?: boolean;
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
  audioStart?: number;
  audioDuration?: number;
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

// Stable pair identity survives unlink/relink and project IO. Old clips remain combined.
export function importedClips(asset: Asset, track: string, at: number): Clip[] {
  const v = newClip(asset, track, at);
  if (asset.kind !== "video" || !asset.hasAudio || !track.startsWith("V")) return [v];
  const pairId = crypto.randomUUID();
  return [{...v, pairId, linked:true, videoOnly:true, mute:true},
    {...v, id:crypto.randomUUID(), pairId, linked:true, track:"A1", mute:false}];
}
export const related = (a: Clip,b: Clip) => a.id===b.id || Boolean(a.pairId && a.linked && b.linked && a.pairId===b.pairId);
export function patchClip(clips: Clip[], selected: Clip, patch: Partial<Clip>): Clip[] {
  const temporal = Object.fromEntries(Object.entries(patch).filter(([k])=>["at","in","out","speed","transition"].includes(k)));
  return clips.map(x=>x.id===selected.id ? {...x,...patch} : related(selected,x) ? {...x,...temporal} : x);
}
export function splitClips(clips: Clip[], selected: Clip, time: number): Clip[] {
  const rightPair = crypto.randomUUID();
  return clips.flatMap(x=> {
    if (!related(selected,x) || time<=x.at+.01 || time>=x.at+clipLength(x)-.01) return [x];
    const cut=x.in+(time-x.at)*x.speed;
    return [{...x,out:cut,fadeOut:0}, {...x,id:crypto.randomUUID(),pairId:x.pairId?rightPair:undefined,at:time,in:cut,fadeIn:0,transition:0}];
  });
}
