# File Converter

Windows 11 x64 優先、兼顧 Windows 10 的本機轉檔桌面工具。清晰背景、分層玻璃、繁體中文操作；保留使用者資料識別碼 `studio.rai.converter`。

目前為 **1.0.0-rc.1 驗收候選版**。P1–P4 已實作，最終環境及散布驗收狀態見 [驗收紀錄](docs/VALIDATION.md) 與 [散布要求](docs/DISTRIBUTION.md)。候選檔案不代表所有實機驗收已通過。

## 功能

- 內容辨識／指定來源→目標兩種模式，混合批次、1–4 工作並行、真實進度、取消程序樹、重試、衝突另存與 SQLite 歷史。
- 影片／音訊、HEIC／AVIF／GIF 等圖片、Office／PDF、Markdown／HTML、電子書、向量及壓縮格式；共用 [305 個合法直接方向](docs/FORMATS.md)。
- 自動／NVIDIA／AMD／Intel／CPU 實際編碼探測、CPU 備援、H.264/H.265、CRF/bitrate/FPS、解析度與音訊選項。
- PDF OCR、頁面工具、已知授權密碼保護／解密、浮水印；圖片尺寸／裁切／壓縮／EXIF／非 AI 修補；影音裁切／合併／Remux／字幕／影格／音量標準化。
- ZIP/7Z/TAR/GZ、RAR 解壓、路徑與連結檢查、另存命名、SHA-256 與重複檔報告。
- 選用網址下載：實際來源格式、播放清單勾選、字幕語言、四種音訊後處理、速度／ETA、取消與 `.part` 續傳。僅此功能需網路；不提供 DRM／帳密／Cookie 繞過。
- 圖片／PDF／Office 預覽、影音試播、前後滑動比較、轉檔預設、多步驟工作流程與明確啟用的監看資料夾。
- 選用 Windows 右鍵整合，可安全停用；不變更預設程式、檔案關聯或其他應用程式圖示。
- 背景、亮度、透明度、模糊、遮罩與各玻璃面板獨立控制，立即預覽並保存。清晰背景 Blur=0；深／淺／系統主題、外觀配置與 Reduced Motion。

## 使用

解壓 Portable ZIP **全部內容**後啟動 `FileConverter.exe`，或執行 Windows Installer。保留 `binaries/`、`engines/`、`webview-runtime/` 與授權檔，不能只複製 EXE。Python、FFmpeg、LibreOffice、Pandoc、Calibre、Ghostscript、7-Zip、OCR 模型、Deno 與固定版 WebView2 均隨套件提供，不需另行安裝引擎。

拖入檔案→選擇合法格式→品質設定→輸出資料夾→開始轉換。首頁可展開轉檔預設；多步驟與監看位於「自動化工作流程」。監看只讀取明確指定資料夾的直接子檔案，來源／輸出不可重疊，重開程式後需重新啟用。右鍵在「設定→進階」啟用，Windows 11 可於「顯示其他選項」查看；移動 Portable 資料夾前先停用。

原始檔不直接覆蓋，撞名會另存。設定、背景與歷史保存在 `%APPDATA%\studio.rai.converter`。密碼只暫存在記憶體，重試需重新輸入。

## 架構與目錄

Tauri 2.12.5 + React 19.3.1 + TypeScript 7 + Vite 8 + Tailwind 4，Radix、Motion、Lucide。Rust 白名單 IPC→凍結 Python JSONL 服務→隔離 worker→本機引擎。沒有前端任意 Shell、CDN 字型、雲端轉檔或自建追蹤服務。

```text
src/                React GUI、玻璃、背景、轉檔／下載／工具／自動化
src-tauri/          Rust bridge、權限、圖示、NSIS 專屬清理 hooks
engine/             Registry、內容辨識、adapters、工具與佇列
scripts/            SHA 校驗依賴取得、Runtime staging、freeze、授權與封裝
tests/              真實內容、生命週期、格式矩陣與原生 CDP 驗收
docs/               格式表、階段紀錄、驗收、授權與限制
engine-lock.json    Runtime／模型／字型／WebView2 來源和 SHA-256
```

## 開發

開發機需 Node.js、Rust MSVC、VS C++ Build Tools、Python 3.13 與 7-Zip；使用者不需要。重用既有依賴快取。

```powershell
npm ci
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r engine\requirements-lock.txt
.venv\Scripts\python.exe -X utf8 scripts\prepare.py
.venv\Scripts\python.exe -X utf8 scripts\acquire_engines.py
npm run desktop
```

```powershell
npx tsc --noEmit
cargo check --manifest-path src-tauri/Cargo.toml
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p 'test_*.py' -v
.venv\Scripts\python.exe -X utf8 tests\matrix.py
```

P1–P4 只跑相關簡測和增量編譯。`tests/matrix.py --failed` 重試未通過方向。素材在忽略的 `.tools/` 產生，不提交私人檔案。`tests/native-ui.mjs` 連接真正 WebView2 的 localhost CDP，僅控制測試檔案選擇結果。

## P5 EXE／Installer／Portable

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

重用已校驗 Runtime，產生 PyInstaller onedir、Tauri Release／NSIS、Portable ZIP 與 SHA256SUMS。只有已完成相同 P5 回歸的工作可用 `-SkipTests` 避免重跑；`-NoInstaller` 供必要的局部修復建置。接著執行 `scripts\verify_release.py`、原生 GUI 與安裝驗證。沒有憑證時為未簽署候選版。

PDF→DOCX／OCR 需校對；融合像素修補不能還原原始畫面；有損壓縮不保證達指定大小；硬體加速不保證更好的畫質。實機與授權限制見文件。

## 授權

應用程式 AGPL-3.0-or-later；引擎含 GPL/AGPL/LGPL/MPL、7-Zip unRAR 限制與 Microsoft Runtime 條款。保留 [完整說明](THIRD_PARTY_NOTICES.md) 和套件 notices。私人儲存庫不免除向二進位收件者提供相應原始碼的義務；候選包尚非對外散布認證版本。
