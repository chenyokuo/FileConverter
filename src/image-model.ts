export interface ImageLayer {
  id: string;
  type: "image" | "text" | "rect" | "ellipse" | "brush" | "eraser" | "mosaic";
  name: string;
  source?: string;
  visible: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  opacity: number;
  flipH: boolean;
  flipV: boolean;
  brightness: number;
  contrast: number;
  saturation: number;
  warmth: number;
  blur: number;
  sharpen: number;
  filter: string;
  fontSize: number;
  text: string;
  color: string;
  stroke: number;
  mosaicSize: number;
  points: number[][];
}
export interface ImageProject {
  type: "fcimage";
  version: 1;
  width: number;
  height: number;
  crop: number[];
  outputWidth: number;
  outputHeight: number;
  quality: number;
  matte: string;
  layers: ImageLayer[];
}
export const makeLayer = (
  type: ImageLayer["type"],
  patch: Partial<ImageLayer> = {},
): ImageLayer => ({
  id: crypto.randomUUID(),
  type,
  name: type,
  visible: true,
  x: 0,
  y: 0,
  width: 200,
  height: 100,
  rotation: 0,
  opacity: 1,
  flipH: false,
  flipV: false,
  brightness: 1,
  contrast: 1,
  saturation: 1,
  warmth: 0,
  blur: 0,
  sharpen: 0,
  filter: "none",
  fontSize: 40,
  text: "文字",
  color: "white",
  stroke: 8,
  mosaicSize: 12,
  points: [],
  ...patch,
});
export const blankImage = (): ImageProject => ({
  type: "fcimage",
  version: 1,
  width: 1024,
  height: 768,
  crop: [0, 0, 1024, 768],
  outputWidth: 0,
  outputHeight: 0,
  quality: 90,
  matte: "white",
  layers: [],
});
