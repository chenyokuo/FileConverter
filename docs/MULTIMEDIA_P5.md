# Multimedia P5 — 1.1.0-rc.1

2026-11-17，本輪 P1/P3/P4 已完成相關簡測並提交；P2 保留並擴充真實網站驗證。沒有在 P1–P4 打包。

已完成完整來源回歸 68 項，67 通過、1 個 PE 資源項待最終實際 EXE/Installer 測試。其餘測試包含原有 PDF/OCR/Office/下載/檔案/自動化和新編輯器。305 格式矩陣本輪以新目錄執行，結果另記。

YouTube 真實網站：Big Buck Bunny 官方 Blender Foundation 來源成功解析 61 格式、635 秒，使用含音訊 360p format 18 精確下載 1–2.5 秒，FFprobe 輸出 1.509002 秒。未使用 Cookie/帳密或存取繞過。第一次最佳分離來源曾無進度，修正 app-local FFmpeg 網路讀取逾時和已含音訊格式不重複追加音訊後通過；不保證所有網站／地區／帳號限制均可下載。

完整 Runtime 準備腳本已實際執行並校驗既有快取；新增新目錄 Git 來源還原與無 AI 的乾淨 venv、npm/Cargo 重建驗證，進度與最終結果將追加於本文件。最終來源 hash、產物 hash、真正執行檔／Installer 結果另列，不能用開發模式測試代替。

依然沒有乾淨 Windows VM／第二台實機，這項限制不會被新目錄測試取代。保留原有 1.0.0-rc.1，沒有刪舊版、Force Push 或自動建立 GitHub Release。相應來源散布與未簽署限制見 DISTRIBUTION.md。


乾淨來源驗證結果：從不含 vendor/venv/node_modules/sidecar 的 Git export 實際還原全部 Runtime，重新安裝 hash-locked Python 和 npm 依賴，重用 SDK/下載快取；重要引擎雜湊、40 個 Python 版本及無 AI 模組檢查通過。官方 PyMuPDF wheel 內含可選 layout/LLM 目錄，初次檢查正確阻擋；加入僅作用於 setup 自有新 venv 的經保護裁減後，整個命令重跑成功。該新環境中 8 組編輯器實際輸出與 3 組 PDF/OCR/Office 流程亦通過。不是複製原本 venv/vendor 冒充重建；重用的是已驗證來源 archive/wheels/npm/Cargo 快取。Cargo target 透過 workspace 內接合重用編譯快取，避免重編所有 Rust 相依套件。

本輪格式矩陣 305/305 通過；下載器網站修正後只重測相關 8 組案例，全部通過。Appearance 預設／遷移／持久化設定檢查通過。真正 YouTube 檢查已通過，仍保留網站限制說明。

真正 Tauri Debug/WebView2/Rust/Python 原生驗證通過：修正 `$APPDATA` 已包含應用識別碼導致預覽 ACL 多一層的問題，僅開放 `$APPDATA/previews/**`；原生影片播放、圖片預覽、兩種編輯輸出、圖片→轉檔、跨頁狀態、最大化／還原均通過。新增 Windows 根 Job 管理 Python redirector 與整個側車程序樹，原生視窗正常退出，不把測試 picker 誤當 engine mock。測試只替換 OS picker 回傳路徑，所有引擎與 IPC 真實。

正式來源程式版本為 1.1.0-rc.1。P5 的 Release／Installer／Portable 正在最後集中封裝；其產物與正式 EXE 的驗證結果將追加，未通過前不宣稱完整正式驗收。
