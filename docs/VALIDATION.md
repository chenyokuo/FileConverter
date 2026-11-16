# 驗收紀錄 — 0.1.0

日期：2026-11-16；Windows 11 x64 10.0.26200，WebView2，Node 24.22.1，Rust 1.100.0，Python 3.13.5。這是可執行的私人測試版本，未宣稱跨所有 Windows 環境通過正式發行驗收。

## 已實際執行並通過

- `npm run build`：TypeScript 檢查與 Vite production build。
- `cargo check`：Windows 原生 Rust / Tauri 橋接。
- Tauri release EXE 編譯；真實桌面視窗已開啟並檢視 Dashboard / Appearance。
- Python 原始引擎 **17 / 17** subprocess 整合測試通過。
- PyInstaller 凍結引擎 **17 / 17** 相同測試通過。
- 自包含 Portable 版本實際啟動，真正 WebView2 / Rust IPC / frozen engine 的 **9 / 9** GUI 測試群組通過。
- Windows Mica 的原生 apply / clear 呼叫已成功執行，介面切換 native-mica 樣式；CSS 材質持續可用。
- Windows NSIS 安裝包成功產生，設定內嵌 Microsoft WebView2 離線安裝包。

### 17 項引擎測試

1. 合法相容矩陣與不支援格式。
2. 中文／空白／`&`／方括號路徑、圖片縮放、alpha→白底、同名衝突、原始 SHA-256 不變。
3. PNG / WebP / BMP / TIFF 實際產出。
4. 圖片與 PDF 混合合併、指定頁碼擷取、逐頁分割、旋轉角度與內容。
5. PDF→PNG / JPG 頁數與像素尺寸。
6. 損毀圖片失敗時其他任務仍完成。
7. 背景解碼、持久化 WebP、設定重啟後一致。
8. 歷史重啟、重試及清除不刪除輸出。
9. MP4→WebM、音軌→MP3、解析度／聲道／取樣率、真實 FFmpeg 非零進度。
10. 執行中取消，worker 與 FFmpeg 都結束；不發布結果、不留下該任務暫存。
11. 單並行佇列與取消尚未執行任務。
12. 拒絕無效轉換、任意 Shell 命令與無效並行設定。
13. 250 筆圖片匯入與預覽資料。
14. 本機 FFmpeg / ffprobe 部署檢測。
15. 非正常終止服務後清理子程序、重啟紀錄標記取消。

16. 所有 12 種影音輸出容器皆產生有效檔案，ffprobe 驗證時長與 streams。
17. 缺少 LibreOffice 時 Office→PDF 提供明確依賴錯誤。

測試請求使用真正 UTF-8 非 ASCII JSON，涵蓋 Rust 發送中文資料的編碼條件。曾發現 Windows 預設 CP950 解碼問題，已在凍結 sidecar 明確設定 UTF-8。輸出發布改用 Windows 不覆寫 rename，並有限重試短暫索引／防毒鎖定。

### 9 組 GUI 測試

1. 匯入背景與獨立圖片 alpha，亮度／模糊／遮罩／縮放／位置。
2. 六種材質獨立 alpha / blur；實際計算 sidebar 背景、blur 與文字 opacity。
3. 外觀配置、SQLite 保存、頁面重載後恢復。
4. 深色／淺色與減少動態效果。
5. GUI 加檔、合法格式清單、真正 WebP 轉檔及檔案存在。
6. 歷史搜尋與真正重試。
7. 自訂按鈕最大化／還原。
8. 125 / 150 / 200% renderer DPI 版面模擬，無水平溢出；高度不足可捲動。
9. 未發生外部網路請求，無前端執行錯誤。

原生檔案對話框已實際開啟。自動化測試用自己的路徑回傳值替代 OS picker，後續解碼、複製、SQLite、轉檔全部呼叫真實服務，不模擬轉檔。圖片與影音進度都是引擎回報，無定時假進度。

## 尚待環境驗收／已知限制

- 沒有在移除 Python / Node / Rust 的全新 VM 上安裝；Portable 包確實含 Python Runtime、Pillow、MuPDF 與 FFmpeg，已在本機使用 frozen 版本驗證。安裝／解除安裝、檔案關聯與乾淨機器測試仍需 VM。
- 沒有實體切換 Windows 10 / 多台 Windows 11，也沒有多螢幕跨 DPI 拖曳驗收；renderer 模擬不能替代 OS 實測。
- 沒有安裝 LibreOffice，因此 Office adapter 的完整格式組合仍未實測；介面明確顯示缺少依賴，不能啟用這類待轉檔。安裝最新版 LibreOffice 後重新匯入檔案可使用。
- NVENC 未在可用 NVIDIA GPU 上驗收；實際執行前會測試編碼能力，失敗時顯示錯誤，使用者可用 CPU 重試。
- 未實際斷開整台電腦網路；程式碼無雲端路徑，打包資源本機化，執行測試未觀察到外部請求。
- 未提供整個 OS 視窗透明度控制；研究與待驗證事項見 WINDOW_TRANSPARENCY.md。
- PDF→DOCX 未提供。動畫圖片／多頁 TIFF 只處理第一畫格／頁。格式偵測初始依副檔名，解碼器再驗證內容。
- 250 筆匯入已測試，數千筆列表尚待虛擬化與效能測試；沒有新增人為檔案大小上限。
- 輸出檔名衝突保護已測試；突然斷電可能保留 `.rai-*` 暫存資料夾，需在確認無其他實例使用時清理。
- 未簽章；對外散布前仍需完成授權原始碼提供、程式碼簽章、乾淨 VM 與跨 Windows 驗收。

詳細機器產生的記錄與 DPI 截圖在忽略的 `test-results/`，避免測試檔與環境資料進入 Git。README 圖片為實際應用程式截圖。
