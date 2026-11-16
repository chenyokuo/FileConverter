import { invoke, isTauri } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
export const desktop = isTauri();
export async function call<T>(method: string, args: unknown = {}): Promise<T> {
  if (!desktop)
    throw new Error(
      "請使用 Windows 桌面版本執行本機轉檔。瀏覽器僅提供外觀預覽。",
    );
  return invoke<T>("engine_call", { method, args });
}
export async function pickFiles(background = false): Promise<string[]> {
  if (!desktop) throw new Error("本機檔案選取需使用桌面版本。");
  const result = await open({
    multiple: !background,
    filters: background
      ? [{ name: "Background", extensions: ["jpg", "jpeg", "png", "webp"] }]
      : undefined,
  });
  return result ? (Array.isArray(result) ? result : [result]) : [];
}
export async function pickFolder(): Promise<string | null> {
  return open({ directory: true, multiple: false });
}
