# Multimedia P5 — 1.1.0-rc.1

2026-11-17，本輪 P1/P3/P4 已完成相關簡測並提交；P2 保留並擴充真實網站驗證。沒有在 P1–P4 打包。

已完成完整來源回歸 68 項，67 通過、1 個 PE 資源項待最終實際 EXE/Installer 測試。其餘測試包含原有 PDF/OCR/Office/下載/檔案/自動化和新編輯器。305 格式矩陣本輪以新目錄執行，結果另記。

YouTube 真實網站：Big Buck Bunny 官方 Blender Foundation 來源成功解析 61 格式、635 秒，使用含音訊 360p format 18 精確下載 1–2.5 秒，FFprobe 輸出 1.509002 秒。未使用 Cookie/帳密或存取繞過。第一次最佳分離來源曾無進度，修正 app-local FFmpeg 網路讀取逾時和已含音訊格式不重複追加音訊後通過；不保證所有網站／地區／帳號限制均可下載。

完整 Runtime 準備腳本已實際執行並校驗既有快取；新增新目錄 Git 來源還原與無 AI 的乾淨 venv、npm/Cargo 重建驗證，進度與最終結果將追加於本文件。最終來源 hash、產物 hash、真正執行檔／Installer 結果另列，不能用開發模式測試代替。

依然沒有乾淨 Windows VM／第二台實機，這項限制不會被新目錄測試取代。保留原有 1.0.0-rc.1，沒有刪舊版、Force Push 或自動建立 GitHub Release。相應來源散布與未簽署限制見 DISTRIBUTION.md。
