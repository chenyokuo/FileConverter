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

草稿中斷可接續上傳，已上傳且 GitHub SHA-256／大小皆相符的附件直接重用。草稿查詢使用 GitHub 的數字 Release ID，預覽的 `untagged-*` 網址在公開後再核對正式 URL。附件使用無空格檔名，避免 GitHub 將空格轉為句點。

已公開 Release 不覆蓋、不 Force Push。既有 Tag 永不移動；草稿接續時，若只有發布流程／文件／驗收改變而產品來源相同，可保留原 Tag 繼續；若產品來源改變，必須選新版本。`BUILD-INFO.json` 分開記錄產品建置 Commit 與後續發布 Commit。原始建置來源為 8b60c81；rc.3 Tag 為 d4ba0ee（相同產品來源，增加驗收工具），main 另有發布流程修正與最終證據。

## 本輪驗收紀錄

2026-11-18，本輪已完成下列實測；證據在 `docs/validation/updater-*`：

| 檢查 | 實際結果 |
|---|---|
| 相關增量 | TypeScript／PowerShell 語法、Manifest／版本／舊設定遷移測試，以及 2 項 Rust 通道與工作守門測試通過 |
| 簽章負例 | 官方 Tauri signer 產生的真實簽章可驗證；內容損毀、錯誤簽署版本皆拒絕。另以官方 `Update.install()` 驗證被修改的完整安裝檔，拒絕且程式不退出 |
| 一次集中封裝 | 重用已驗證且無 AI 套件的 venv／Runtime 快取，13 組既有 frozen 邊界檢查及 4 項實際圖示資源測試通過；未重跑 305 格式矩陣 |
| GitHub 發布 | 真正公開 Prerelease，8 個資產皆 uploaded；GitHub SHA-256 與本機相符，匿名取得 Manifest，所有平台 URL 與正式資產相符 |
| Installer 下載 | 實際 1,573,815,378 bytes，92 個不同下載數值；官方驗證通過，快取重驗亦通過 |
| 工作／監看 | 真正 CPU 影片匯出進行中延後安裝，啟用中的真實監看同樣延後；測試自己的工作取消／監看停止後才允許更新 |
| 自動安裝 | 開啟自動安裝選項後，官方 Updater 啟動真正 NSIS，更新後 EXE 符合 Installer payload SHA，實際原生視窗重新啟動、使用 app-local frozen Sidecar，更新偏好及原有外觀／轉檔設定保留 |
| 最終 Installer | 更新後真正 rc.3 再測更新偏好保存、正式通道排除 RC、直接外掛生命週期指令被阻擋；system-only PATH 與 app-local Fixed WebView2，正常退出 |
| Portable | 自動下載真正 GitHub ZIP 1,588,289,380 bytes、92 個進度數值，官方簽章驗證與整份 ZIP SHA 相符；完整解壓後實際啟動原生版本 rc.3，沒有按檢查按鈕即可由啟動選項取得最新版本 |
| 正常啟動 | 真正下載解壓版另以無 CDP、system-only PATH 啟動與關閉，沒有殘留 Sidecar |
| 資料／清理 | 移除隔離的 QA 安裝後，settings／jobs／automation 語意雜湊相同，原有 92 個本程式右鍵 keys 逐值比較相同；只還原 QA 偏好，不清除使用者資料 |
| 發布不可覆蓋 | 再執行同版發布會在建置前拒絕，沒有移動 Tag 或覆寫公開資產 |

實測抓到的 GitHub 檔名正規化、草稿按 Tag 查詢 404 與 `untagged-*` 預覽 URL 差異，均於草稿階段修正；接續重用已驗證的大型附件，未因此重建應用程式或 Runtime。簽章、Manifest 等小型中繼資料重新產生後，才公開並進行真正客戶端升級測試。

首版 rc.3 的升級路徑使用「具更新元件、原生版本 rc.2 的測試 bootstrap」驗證，因正式 rc.2 未帶 Updater。這是測試前一版客戶端的方式，不會發布 bootstrap，也不宣稱正式 rc.2 能自行檢查更新。最終 rc.3 本身仍須以真正 Installer／Portable 驗證正常啟動、通道與目前版本結果。

上述真正 Installer 與下載解壓的 Portable 均已完成驗證。測試用 bootstrap 需要完整相鄰資源，不作為單檔 Portable 交付。候選包中的文件為建置時快照，最終證據及發布流程修正以本文件／main 為準，不只為文件再次封裝。

下載：[Installer](https://github.com/chenyokuo/FileConverter/releases/download/v1.1.0-rc.3/FileConverter_1.1.0-rc.3_x64-setup.exe) · [Portable](https://github.com/chenyokuo/FileConverter/releases/download/v1.1.0-rc.3/FileConverter-1.1.0-rc.3-windows-x64-portable.zip) · [SHA-256](https://github.com/chenyokuo/FileConverter/releases/download/v1.1.0-rc.3/SHA256SUMS.txt)。

本輪不宣稱乾淨 Windows VM、Windows 10、其他 GPU／實體多螢幕 DPI 已驗收。程式仍未 Authenticode 簽署；外部元件完整相應來源的散布要求見 [DISTRIBUTION](DISTRIBUTION.md)。這些是既有外部驗收／散布範圍，與這次已完成的更新路徑測試分開記錄。
