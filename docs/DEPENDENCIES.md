# 可重建依賴與開發環境

Runtime 清單沿用 `engine-lock.json`，每項包含固定版本／SHA、官方來源、授權、架構、準備目的地與封裝資源路徑。FFmpeg/FFprobe、LibreOffice、Calibre、Pandoc、Ghostscript、7-Zip、Deno、OCR eng/chi_tra、Noto CJK 字型／OFL、Fixed WebView2 均納入。OCR 是 PyMuPDF 內建的 Tesseract API 加語言模型，不依賴系統 tesseract.exe。Python／yt-dlp／EJS／Pillow／OpenCV／PDF／Office 讀取元件與 PyInstaller 的 40 個明確依賴見 `engine/requirements-lock.txt`、`engine/requirements-hashes.txt`、`config/python-wheels.json`。前端與 Rust 分別由 npm/Cargo Lockfile 固定版本與 registry integrity。

開發機先安裝 CPython 3.13 x64、Node.js/npm、Rust MSVC 與 VS C++ Build Tools（Windows SDK）。這些是建置工具；最終使用者不需安裝。若 Codex runtime 只有 node 而沒有 npm，可傳 `-NpmCli <既有 npm-cli.js>`；本次驗證重用本機 SDK，不把開發工具一起放進 Git 或使用者 Installer。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-dependencies.ps1
```

腳本建立乾淨 venv，以 `--no-deps --require-hashes` 安裝明確的 Windows/Python 3.13 wheel 清單，執行 npm ci、cargo fetch --locked、Runtime 下載／SHA 校驗／解壓和實際核心匯入。7-Zip bootstrap 來自官方來源且固定 SHA，只解壓專案資料夾，不安裝到系統。LibreOffice/Calibre 使用 Windows MSI 的 `/a` 管理解壓，不做產品安裝／預設關聯；可能花數分鐘。既有下載有正確 SHA 即重用；缺失或不符會清楚報錯，絕不默默接受新版本。

可重用驗證快取：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-dependencies.ps1 -DownloadCache E:/cache/runtime -WheelCache E:/cache/wheels
```

加 `-Offline` 只允許既有 runtime/wheels/npm/Cargo 快取，缺項就報錯。每個解壓目錄的 `.fc-runtime-integrity.json` 記錄 archive 與重要 EXE 的雜湊；不進入發行包。`scripts/verify_dependencies.py` 驗證所有釘選來源快取、重要引擎、40 個 Python 版本、核心 API 和 AI 模組未安裝。

重要：PyMuPDF 2.1 的 PyPI dependency metadata 會引入本輪不使用的 layout/LLM/ONNX 元件。不要改用普通 `pip install -r` 自動擴張依賴樹；受支援的 setup 使用明確白名單，不安裝額外 AI 套件。官方 PyMuPDF wheel 本身亦帶有可選的 layout/LLM 目錄，因此 setup 在明確標記為自己新建的 venv 中移除這些未使用目錄，再驗證無 AI 模組／ONNX 模型；不修改現有使用者 venv 或官方快取 wheel。預覽／PDF/OCR 採經實測的 classic API；PyInstaller 另有排除條件，發行包也驗證不含 AI 模組。首次準備時辨識到的不需要 wheel 已從本專案快取移除，未安裝到新環境或納入封裝。

建置：`scripts/build.ps1`。P1–P4 不執行它；P5 已完成相同回歸才可用 `-SkipTests` 避免重測。完整打包前執行 `scripts/verify_dependencies.py`；打包後執行 `scripts/verify_release.py`、真實 EXE/Installer 驗證。來源還原、SDK／新目錄驗證與正式產物結果另記於 `MULTIMEDIA_P5.md`；乾淨目錄並不等於乾淨 Windows VM。

外部 GPL/AGPL/LGPL 相應來源提供仍需符合 `DISTRIBUTION.md` 的收件者來源安排；只有 registry 連結、版本或成功建置不代表已完成該義務。正式簽署憑證、Windows 10／實體 DPI／其他 GPU 都不會由腳本假造驗收。
