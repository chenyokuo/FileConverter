import type { Draft, Registry } from "./types";
export function conversionIssue(file: Draft, registry: Registry) {
  if (file.expectedSource && file.extension !== file.expectedSource)
    return `指定來源為 ${file.expectedSource.toUpperCase()}；實際內容為 ${file.extension.toUpperCase() || "未知"}。切回自動辨識或重新指定來源。`;
  if (!file.available)
    return (
      file.reason ||
      (file.category === "office"
        ? "需要本機 LibreOffice"
        : "所需轉檔引擎不可用")
    );
  if (!file.format) return "請選擇輸出格式";
  const edge = registry.edges.find(
    (e) => e.source === file.extension && e.target === file.format,
  );
  if (!edge) return "此來源與目標組合尚未支援";
  if (!edge.available) return edge.reason;
  if (
    edge.operationRequired &&
    !(file.options.pages.trim() || file.options.rotation || file.options.split)
  )
    return "PDF → PDF 請設定頁碼、旋轉或分割；合併請使用下方「合併 PDF」。";
  return "";
}
