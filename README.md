# File Converter

Windows 本機萬用轉檔器。深色玻璃介面、可保存的個人化外觀、真實轉檔佇列，所有使用者檔案留在本機。

![File Converter 實際桌面畫面](docs/dashboard.png)

**目前版本：0.3.0，P0 私人測試版。** 請閱讀 [驗收紀錄](docs/VALIDATION.md) 中已實測與尚待驗證的區別。此版本不是跨所有 Windows 版本完成驗收的正式商業發行版。

[P0 架構、雙模式操作、圖示與實際畫面](docs/P0.md)。

開發流程遵循 [AGENTS.md](AGENTS.md)：P0～P4 以開發模式、相關測試及增量編譯驗證，只有打包設定、Sidecar／Runtime 或必要安裝環境驗證才中途封裝。完整 Release／Installer／Portable 與正式驗收統一於 P5 進行。現有 P0 預覽包保留作圖示及部署驗證快照，不代表每次原始碼 Commit 都重新封裝。

## 功能

- 智慧自動辨識與指定來源／目標雙模式，共用後端 Conversion Registry；支援容器與實際內容辨識，副檔名不符會提示。
- PDF／圖片／影音／文件工具箱，能力表顯示引擎可用性、回歸測試覆蓋與品質限制。未整合的 P1–P4 功能明確停用。
- 啟動即進入轉檔工作區；檔案類型篩選、可收合輸出設定、轉換紀錄與設定頁。繁體中文介面及自訂標題列。
- 側邊欄、檔案面板、Modal、工具列、設定面板使用獨立玻璃材質；主工作區只調整底色／透明度，永不套用全域模糊。內文 16px，次要資訊與標籤至少 14px。
- JPG / PNG / WebP 全尺寸無損背景匯入，預設模糊 0px；清晰背景／毛玻璃背景預設、縮放／位置／裁切、獨立透明度／亮度／模糊／遮罩、深淺色與自訂配置持久化。
- 圖片轉 PNG / JPG / WebP / BMP / TIFF / PDF，尺寸、品質與透明區域底色設定。
- FFmpeg 影音轉檔、音軌擷取、CRF／bitrate／解析度／FPS／取樣率／聲道設定；NVENC 在編碼前實際檢測。FFmpeg 的 duration / out_time_us 提供真實進度。
- PDF 轉 PNG / JPG、圖片與 PDF 混合合併、頁碼擷取、逐頁分割、旋轉。
- LibreOffice 格式族群內的轉換與 Office → PDF；缺少 LibreOffice 時顯示未安裝，不會假裝成功。
- SQLite 本機歷史、搜尋／狀態篩選／重試、1–4 個並行任務、取消程序樹、同名檔自動編號、原檔保護。
- Motion 頁面／清單／Modal／通知動畫、Reduced Motion、離線字型與圖示、無追蹤及無 CDN。

完整格式矩陣見 [FORMATS.md](docs/FORMATS.md)。PDF → DOCX 尚未提供；整個應用程式視窗透明度尚未通過相容性驗證，因此沒有假滑桿。Windows Mica 為選用底層效果，CSS 玻璃是主要材質。單張圖片與 Office 引擎無法提供連續數值時顯示處理中，不生成假進度。

## 使用方式

1. 解壓縮整個 Portable 資料夾，開啟 `FileConverter.exe`；或執行 Windows 安裝程式。
2. 自動模式：拖入檔案／按「加入檔案」，再為每檔選擇輸出格式；預設不選目標。指定模式：先選來源 → 目標，再加入檔案；來源不符會阻擋提交。
3. 點選檔案，在右側調整參數，可套用至勾選的同類檔案。箭頭可以調整待轉檔順序。
4. 選擇輸出資料夾；未選擇時輸出至來源旁的 `File Converter Output`。
5. 按「開始轉換」。可取消／重試，在完成項目開啟輸出資料夾。
6. 合併圖片或 PDF：勾選至少兩個相容檔案，依清單順序按「合併 PDF」。
7. 設定 → 個人化外觀可即時預覽及儲存；關閉時會儲存最後的設定。

Portable 指免安裝的資料夾版本，設定仍存於 `%APPDATA%\studio.rai.converter`。需要 Windows 10/11 x64 與 WebView2 Runtime。Node / Python / Rust **不需要安裝在使用者電腦上**；Python Runtime、Pillow、MuPDF、FFmpeg / ffprobe 隨包部署。LibreOffice 是 **另行安裝的選用依賴**。安裝程式設定使用 WebView2 離線安裝包；Portable 需要系統已有 WebView2。

## 開發環境

- Node.js 24 LTS（目前已驗證 24.22.1）、npm。
- Rust stable 與 `x86_64-pc-windows-msvc`，目前已驗證 1.100.0。
- Visual Studio 2022「使用 C++ 的桌面開發」、Windows SDK、WebView2。
- Python 3.13 x64（目前已驗證 3.13.5）。

```powershell
npm ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r engine\requirements-lock.txt
.\.venv\Scripts\python.exe scripts\prepare.py
.\.venv\Scripts\python.exe scripts\icons.py
New-Item -ItemType Directory -Force src-tauri\binaries | Out-Null
npm run desktop
```

`npm run dev` 是瀏覽器外觀預覽，會明確標示本機轉檔與背景匯入需要桌面版本；不模擬轉檔。首次下載依賴需要網路，完成打包後執行不需網路。

若使用此工作區已準備好的專案內工具，可用 `node .tools/npm/package/bin/npm-cli.js` 取代 `npm`，並以 `scripts/build.ps1` 設定專案內 Rust PATH。`.tools/` 不會提交。

## 測試與建置

```powershell
npm run build
npm run test:appearance
cargo check --manifest-path src-tauri/Cargo.toml
.\.venv\Scripts\python.exe tests\test_engine.py
.\.venv\Scripts\python.exe scripts\freeze.py
$env:FILE_CONVERTER_TEST_FROZEN = "$PWD\src-tauri\binaries\FileConverterEngine\FileConverterEngine.exe"
.\.venv\Scripts\python.exe tests\test_engine.py
Remove-Item Env:FILE_CONVERTER_TEST_FROZEN
```

`scripts/verify_release.py` 額外需要 7-Zip CLI，以唯讀核對安裝包內容；7-Zip 不是此版應用的執行依賴。

測試只產生小型測試檔於忽略的 `.tools/`，不讀取使用者私人檔案，不連網。包含輸出內容檢查、原檔 SHA-256、250 筆匯入、失敗隔離、取消與非正常關閉時的程序清理。

完整 Windows EXE 與 NSIS 安裝包：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
# 只建立 EXE 與 Portable，不產生安裝程式：
powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -NoInstaller
# 完整發行包核對（含安裝包）：
.\.venv\Scripts\python.exe scripts\verify_release.py
```

建置流程：準備 FFmpeg → 凍結 Python → 執行原始及凍結引擎測試 → 收集授權 → Tauri release build → Portable ZIP。首次 NSIS 建置需要下載 NSIS 與 Microsoft WebView2 離線安裝包；不表示使用時需要網路。`-SkipTests` 僅適合已完成相同版本測試的本機重建。

輸出：

- `release/FileConverter-0.3.0-windows-x64-portable.zip`
- `release/File Converter_0.3.0_x64-setup.exe`（成功執行安裝包建置時）
- `release/SHA256SUMS.json`
- 原始 NSIS 產物位於 `src-tauri/target/release/bundle/nsis/`。

不可只複製 `FileConverter.exe`：必須連同 `binaries/FileConverterEngine/`、`engines/ffmpeg/` 與授權一起部署。EXE 與安裝程式尚未簽章；不要把未簽章的測試包宣稱為已通過 SmartScreen 驗證的正式產品。

原生 UI 回歸測試（只在本機測試時啟用除錯埠，正式使用不要設定）：

```powershell
.\.venv\Scripts\python.exe tests\make_ui_fixtures.py
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS='--remote-debugging-port=9222'
$env:WEBVIEW2_USER_DATA_FOLDER="$PWD\.tools\webview-ui-test"
& '.\release\FileConverter-0.3.0-Portable\FileConverter.exe'
npm test
Remove-Item Env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
Remove-Item Env:WEBVIEW2_USER_DATA_FOLDER
```

測試連接真正的 WebView2 與後端，僅原生選檔對話框回傳值由測試檔案取代。測試最後恢復原設定，初始無歷史紀錄時會清除自己建立的測試紀錄。這不是遠端服務，正式包沒有加入測試 hook。DPI 測試為 renderer 尺寸模擬，仍需實體螢幕驗收。

## 技術架構

```text
src/                     React / TypeScript / Tailwind / Motion UI
  components/            Radix Modal、設定、格式參數編輯器
src-tauri/src/main.rs     白名單 IPC、視窗生命週期、JSONL 橋接
src-tauri/capabilities/   最小視窗／選檔權限，無 Shell 插件
engine/service.py        SQLite、佇列、程序隔離、取消、檔名衝突
engine/worker.py         Pillow / MuPDF / FFmpeg / LibreOffice
engine/registry.py       共用能力表與 Conversion Graph
engine/detection.py      格式內容與容器辨識（原生 Rust infer 提供提示）
engine/adapters.py       可擴充引擎介面
engine/formats.py        舊 API 相容匯出
scripts/                 引擎部署、凍結、圖示、授權、Windows 打包
tests/                   實際 subprocess 轉檔整合測試
docs/                    架構、矩陣、驗收及透明度研究
vendor/                  忽略的外部影音執行檔
```

Rust 只允許明確列出的引擎命令。前端不能指定執行檔或任意命令；參數以陣列傳遞，`shell=True` 不使用。每個任務用獨立 subprocess 及 Windows Job Object，應用程式結束時清理所有子程序。FFmpeg 輸出先放在輸出資料夾內的暫存目錄，成功後以不覆寫方式發布。失敗／取消後清理暫存。異常關閉後原始檔安全保留，歷史中的執行中任務標為已取消；可能留下的 `.rai-*` 暫存資料夾可在確認無其他實例使用後移除。

## 授權

本專案採 **AGPL-3.0-or-later**。詳見 [LICENSE](LICENSE) 與 [第三方授權](THIRD_PARTY_NOTICES.md)。PyMuPDF 具有 AGPL／商業雙授權；本包未購買商業授權。FFmpeg 選用含 GPL 編碼器的 Gyan essentials build，**不是 LGPL-only**。對外散布前需提供相應原始碼與完整授權；私人 GitHub Repository 不會免除相關義務。離線轉檔不會進行授權驗證連線。

## GitHub

目標：私人 Repository `FileConverter`，描述：`A modern, customizable, offline universal file converter for Windows.`

本機程式碼、測試與建置檢查完成後才準備上傳，目前已存在私人 Repository `chenyokuo/FileConverter`。P0 在獨立分支開發，本輪只建立本機 Commit；最終整合驗收通過後才同步 GitHub。未登入時請在自己的終端執行 `gh auth login`，不要把密碼或 Token 貼進聊天。



`.gitignore` 排除環境檔、憑證、快取、引擎 EXE、測試檔、Python 環境與編譯產物。GitHub 原始碼不含大型二進位檔；交付包另外產生。
