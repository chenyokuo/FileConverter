# 網址下載區間選取

2026-11-17，分支 `feature/multimedia-editor`，以保留完整既有引擎的 `d0bd476` 為基礎。這份記錄只涵蓋本次補充的區間下載，不代表附件的影片多軌編輯器、圖片編輯器或其最終打包已完成。

## 實作

- 沿用 DownloadPage、下載佇列、歷史、取消／續傳及 yt-dlp Runtime；沒有新增套件或第二套下載引擎。
- 原生 HTML video 預覽、16:9 容器；共享 TimeRange 提供滑鼠 Pointer Capture 拖曳、獨立播放指標、鍵盤調整、HH:MM:SS 輸入與同步 Slider。
- 拖曳或編輯起訖不會重新載入影片；起點／終點限制在已知長度內。未知長度、直播或尚未載入時禁用區間控制；完整下載維持可用。
- 可重設、新增／刪除多個片段，依清單順序分別輸出或合併。取消「只輸出所選片段」時送出空 sections，走原本完整下載流程。
- 伺服器用解析紀錄中的 duration 驗證區間，重新取得來源時再次核對新長度；拒絕負數、NaN、Infinity、零長度及越界。
- yt-dlp `download_ranges` 是官方 `--download-sections` 的 Python API 對應；精確模式使用 `force_keyframes_at_cuts`，快速模式保留關鍵影格限制提示。處理與合併仍在既有隔離 Worker，取消時沿用 Windows Job Object 終止整個子程序樹。
- 修正 yt-dlp 靜態 FFmpegFD 探測：以 context-local ffmpeg_location 連接內附 FFmpeg，不依賴系統 PATH 或修改已安裝套件。
- 僅 media-src 開放 HTTP/HTTPS 供使用者解析的影片預覽；script/connect/frame 權限保持原範圍。選取介面全部沿用主題變數，不新增固定配色。清單只為選中來源建立播放器，避免同時預載 50 支影片。

## 實際驗證

- `cargo check --offline --manifest-path src-tauri/Cargo.toml`：增量檢查通過。先修正既有 debug 產物 2,083 個唯讀資源阻擋覆寫的屬性；只動到本專案 target/debug，不修改原始 Runtime 或 release。
- `node .tools/npm/package/bin/npm-cli.js run build`：TypeScript 與前端建置通過；既有大型 JS chunk 提醒仍存在，未冒充錯誤或新增套件。
- `python -X utf8 -m unittest discover -s tests -p test_download_ranges.py -v`：3 組通過。自有 localhost HTTP 影片經真正 yt-dlp/FFmpeg 下載快速／精確區間、影音合併、兩段分別 MP4 轉碼；FFprobe 驗證非關鍵影格精確切點的輸出時長（1.0s、0.5s，容許一個影格及音訊封裝誤差）。另測邊界及不可信請求。
- `python -X utf8 -m unittest discover -s tests -p test_p3.py -v`：既有 5 組下載回歸通過，含來源畫質、字幕、四種音訊、取消／Range 續傳與本機轉檔獨立性。
- 開發伺服器啟動後執行 `node tests/range-ui.mjs`：使用無頭 Edge 和實際本機 120 秒測試影片驗證滑鼠拖曳、鍵盤、手動時間、格式錯誤、越界夾限、多段／重設、播放與 Seek、未知長度禁用、760/1000/1500px；沒有頁面 JS 例外。完整 DownloadPage 的 IPC 邊界測試使用明確的測試 metadata，確認選段送出 15–45 秒、完整下載送出空區間；這一項不冒充網站或原生 Tauri 端到端測試。
- 圖片 `download-range-ui.png` 為共用元件在既有主題與本機字型下的自動化執行畫面（1500×1300），不是設計稿或正式安裝包畫面。

## 限制

- 尚未對第三方 YouTube 網站實測；使用自有媒體避免依賴網站、帳號或內容授權。來源需提供瀏覽器可直接播放的含音訊 MP4/WebM，才可在原生播放器預覽。簽名過期、需要特殊 Headers／Cookie、只有分離串流或瀏覽器不支援的來源會明確提示，下載不依賴播放器成功。
- 快速切點受關鍵影格限制；精確模式會重編碼。選取字幕時保留來源完整字幕時間軸並顯示提示，目前未實作片段字幕重設時間。
- 新控制項目前在開發原始碼；既有 `release/1.0.0-rc.1` 產物未被覆寫。沒有 Installer／Portable／Release Build，也沒有新增 AI 元件或改檔案關聯。
- 此次沒有取得所述參考截圖，依文字指定的上下布局、16:9、雙欄時間欄位與底部資訊操作實作。

## 執行元件驗證

先執行 `node node_modules/vite/bin/vite.js --host 127.0.0.1`，另一個終端執行 `node tests/range-ui.mjs`。測試會用既有 `.venv` 和內附 FFmpeg 產生 `.tools/range-preview.mp4`，需要本機 Edge。所有影片及暫存均留在忽略的目錄，不加入 Git。
