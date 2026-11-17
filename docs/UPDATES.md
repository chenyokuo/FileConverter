# 更新與發布

## 使用者

rc.3 起，在「設定 → 軟體更新」檢查版本。啟動時檢查、自動下載、自動安裝預設皆關閉，設定與原有外觀／歷史共用 SQLite 保存，不改資料識別碼 `studio.rai.converter`。

- Installer：下載完整 NSIS 安裝檔，驗證 Tauri 簽章及簽署版本後，於工作結束且監看暫停時安裝。官方 Windows Updater 以 NSIS `/UPDATE`、passive UI 及 `/R` 重啟；不以 Process Plugin 直接強制關閉忙碌的程式。
- Portable：使用獨立 manifest target 下載整份 ZIP，經相同簽章驗證後放在 `%APPDATA%/studio.rai.converter/updates/<version>/`。按「開啟下載資料夾」，完整解壓至新目錄，不覆寫正在使用的資料夾。
- RC 通道包含較新的候選版及正式版；正式通道排除 prerelease。版本以 SemVer 比較，`rc.10` 大於 `rc.9`，正式版大於同版 RC，不降版。
- rc.2 與更早版本未包含 Updater，首次必須手動安裝／解壓 rc.3。Tauri 更新簽章與 Authenticode 獨立，目前未購置 Windows 程式碼簽署憑證。

## GitHub 端點

不需要額外更新伺服器，也不在程式中放 Token。Rust 使用匿名 GitHub Releases API，從最近 100 個已發布 Release 中依通道選擇具有 `latest.json` 的最高 SemVer。Draft 不可見，無 manifest 的版本略過；一次使用者檢查只做必要 API／manifest 請求，受 GitHub 匿名 API 配額限制。

每版 manifest 直接附在該版 Release，例如：

`https://github.com/chenyokuo/FileConverter/releases/download/v1.1.0-rc.3/latest.json`

正式版的 `/releases/latest/download/latest.json` 不能用來尋找 RC，因為 GitHub Latest 排除 Prerelease。這裡不使用會被反覆移動的 RC Tag。`latest.json` 包含真正 `.sig` 內容，並指向該版 HTTPS Release 資產：

| Target | 資產 |
|---|---|
| `windows-x86_64`、`windows-x86_64-nsis` | NSIS Installer EXE（官方 v2 updater 本身就重用這個檔案） |
| `windows-x86_64-portable` | 完整 Portable ZIP |

Updater 2.14.1／Process 2.4.0 為這次查證的 Tauri 2 穩定版（MIT OR Apache-2.0，Rust ≥1.90）。依據 [官方 Updater](https://v2.tauri.app/plugin/updater/) 與 [官方 Process](https://v2.tauri.app/plugin/process/)；未採用 3.0 alpha。Rust／npm 鎖定實際版本。

## 安裝守門與驗證

前端沒有直接 Updater install／Process restart 權限。Rust 白名單更新指令固定讀取本專案的 GitHub Releases；正式二進位不接受任意 endpoint、公鑰、降版或略過驗證參數。

引擎事件追蹤所有 queued／running／cancelling 工作，包含未顯示於歷史的預覽；建立工作 RPC 也受原子守門保護。安裝期間拒絕新增工作，安裝前再檢查監看狀態。忙碌時維持 ready，顯示等待原因，自動模式稍後重試。僅簽章通過後寫出下載檔；安裝前官方 `Update.install()` 再次驗證，損毀檔案不得執行。快取再次使用時也會重驗。

`requireSignedVersion=true`，所有手動簽署使用 `--app-version`，官方 Tauri build 亦綁定版本。下載進度來自官方 `Update.download()` 的 chunk／Content-Length；未知總長度時顯示實際已下載大小及不定進度。所有更新完成後才允許 NSIS 啟動及 Sidecar 正常清理。尚未儲存的編輯專案請先存檔，自動安裝是明確選用功能。

## Setup 與金鑰

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

這層整合現有 `setup-dependencies.ps1`；支援 `-Offline`、`-DownloadCache`、`-WheelCache`、`-PythonExe`、`-NpmCli`。需要時可 `-SkipDependencies` 重用現有完整環境，沒有每次下載相同 Runtime。

第一個發布者在尚未設定公鑰時可使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -InitializeSigningKey
```

本專案已建立更新身分。公鑰在 `config/updater.pub` 與 Tauri 設定中；私鑰由 Windows DPAPI 以目前使用者保護，保存於 `%LOCALAPPDATA%/FileConverter/Signing/updater-private.dpapi`，不在 Git／快取／Release 中。目錄 ACL 限本人與 SYSTEM。只把公鑰提交 Git。

**必須安全備份私鑰與可解密的恢復方案。** DPAPI 檔不能當成可任意移機的明文金鑰；換機前由原 Windows 使用者解密後，存入自己的密碼管理器或安全祕密儲存庫。遺失原私鑰會使已安裝客戶端無法信任後續版本。已有公鑰時 setup 不自動產生新私鑰覆蓋身分；其他貢獻者可開發、編譯檢查和 dev mode，但不能冒用發布者簽章。

CI／其他建置機可在執行環境提供 `TAURI_SIGNING_PRIVATE_KEY` 與 `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`。不要放入 `.env`、指令紀錄、GitHub 附件或原始碼；腳本會在 finally 還原執行環境。GitHub 權限使用 `gh auth login` 的既有登入，不把 Token 放入應用程式。

## 發布指令

先提交來源與 `docs/releases/<version>.md`，將驗證過的 main 推送遠端。版本同步涵蓋 package／npm lock、Tauri、Cargo／Cargo lock。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/publish-release.ps1 -Version 1.1.0-rc.3
```

腳本沿用 `build.ps1`／NSIS／Runtime，產生 EXE、ZIP、各自 `.sig`、`latest.json`、`SHA256SUMS.json`／`.txt` 與 `BUILD-INFO.json`。以實際 EXE 的唯讀驗證指令檢查 minisign 公鑰、內容及綁定版本，才可建立 annotated Tag／草稿並上傳。所有附件就緒後公開；帶預發版字尾的版本為 Prerelease，不設為 Latest。來源工作區不乾淨、版本不一致、倉庫私人、錯誤 Tag 或已公開同版 Release 都會停止。

必要的相關測試與 build.ps1 的既有 frozen 邊界檢查會執行；預設不重跑 305 矩陣。要刻意執行完整舊回歸時加 `-RunFullRegression`。

若原開發 venv 存在不應封裝的可選套件，可用 `-PythonExe <既有乾淨 venv/Scripts/python.exe>` 指定另一個符合相同 hash lock 的已驗證建置環境；不修改原環境、不納入 LocalAI。

```powershell
# 最終驗收前先準備一次簽章產物，不發布
powershell -ExecutionPolicy Bypass -File scripts/publish-release.ps1 -PrepareOnly
# 使用同一份已準備、來源相容的產物接續發布，避免重複完整建置
powershell -ExecutionPolicy Bypass -File scripts/publish-release.ps1 -SkipBuild
# 上傳完成仍保留為草稿
powershell -ExecutionPolicy Bypass -File scripts/publish-release.ps1 -SkipBuild -DraftOnly
```

草稿中斷可接續上傳；已公開 Release 與既有不同指向 Tag 不覆蓋、不 Force Push。`BUILD-INFO.json` 分開記錄產品建置 Commit 與後續僅文件／驗收的發布 Commit；若產品或建置來源已變動，拒絕拿舊包發布。

## 本輪驗收紀錄

相關模型／Manifest／版本與設定遷移測試、Rust 活動守門與 SemVer 通道測試、TypeScript 檢查及原生更新設定頁測試已執行。最終實際 GitHub 下載、NSIS 更新、重啟與設定保留結果在封裝驗收後補入 `docs/validation/updater-*`。本節不把尚未發生的實機更新宣稱為已通過。

首版 rc.3 的升級路徑使用「具更新元件、原生版本 rc.2 的測試 bootstrap」驗證，因正式 rc.2 未帶 Updater。這是測試前一版客戶端的方式，不會發布 bootstrap，也不宣稱正式 rc.2 能自行檢查更新。最終 rc.3 本身仍須以真正 Installer／Portable 驗證正常啟動、通道與目前版本結果。
