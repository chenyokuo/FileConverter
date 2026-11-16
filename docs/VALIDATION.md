# 驗收紀錄 — File Converter 0.3.0 / P0

日期：2026-11-16。Windows 11 x64（10.0.26200）、WebView2、Node 24.22.1、Rust 1.100.0、Python 3.13.5。這是可執行的私人測試版，不等同跨所有 Windows 環境完成正式發行認證。

## 後端與建置

- TypeScript / Vite production build、Windows Rust / Tauri `cargo check` 與 release EXE 建置。
- 原始 Python 引擎 **23 / 23** subprocess 整合測試。
- PyInstaller 凍結引擎 **23 / 23** 相同整合測試；不依賴使用者安裝 Python。
- 外觀 Node assertions：清晰背景預設、舊版設定遷移、個人化參數保留與兩種背景配置。
- NSIS Installer 成功產生，內含 Microsoft WebView2 離線安裝程式；Portable 同時包含凍結 Python、Pillow、MuPDF、FFmpeg / FFprobe 及授權。LibreOffice 不在本版套件中。

23 項引擎案例覆蓋：合法矩陣、中文／空白／`&`／方括號路徑、alpha／圖片尺寸、各圖片與影音輸出容器、PDF 合併／旋轉／頁碼擷取／分割／影像 DPI、同名不覆寫與原始 SHA-256、背景原尺寸 RGBA 無損持久化、歷史重啟／重試／清除、250 筆匯入、真實 FFmpeg 進度、失敗隔離、有限並行、取消與程式異常結束後清理子程序、缺少 LibreOffice 的真實錯誤、內容與副檔名不符、損壞檔隔離、OOXML／OLE／影音容器辨識、Registry 欄位／Graph 直接與間接規劃、PDF 空操作阻擋，以及指定歷史清除不影響其他紀錄／輸出。

## 原生 UI

實際 Portable / Windows WebView2 的 **19 / 19** GUI 群組。測試透過本機 CDP 連接原生應用，只替換原生選檔對話框的回傳路徑；Rust IPC、SQL、背景匯入、引擎與輸出檔均是真實流程，沒有 mock 轉檔或假進度。

1. 啟動直接顯示操作區，16px 內文、15–16px 按鈕、至少 14px 次要資訊。
2. 原生背景匯入及獨立圖片透明度、亮度、模糊、遮罩、位置／縮放。
3. 六種材質獨立樣式；主工作區永不套用全域 blur；文字不隨面板 alpha 淡化。
4. 外觀配置儲存／套用及 SQLite 持久化。
5. 深淺主題與 Reduced Motion。
6. 清晰／毛玻璃背景配置、保存背景、主工作區保持清晰。
7. 混合檔案篩選、順序調整、同類批次品質與 PDF 合併確認。
8. 原生檔案辨識、合法格式清單、實際排程與圖片輸出。
9. 1500×960、1360×900、1280×720、1024×768、760×480 主要操作區可見性。
10. 歷史搜尋與實際重新轉檔。
11. 原生視窗最大化及還原。
12. 125 / 150 / 200% renderer DPI 尺寸模擬。
13. 六項新導覽、P3／P4 明確停用、新圖示、側欄收合與重載持久化。
14. 自動模式目標留空；native infer 提示；PDF 空操作阻擋與設定後啟用。
15. 指定模式來源不符、取消勾選後實際 PNG → JPG；能力表阻止不合法 PDF → DOCX／影片選項。
16. 工具箱實際逐頁分割兩頁 PDF，驗證兩個輸出檔。
17. 八類工具、未實作階段／缺少引擎標示、後端 Registry 搜尋。
18. 有檔案佇列的桌面與 DPI 排版、進度展開／收合、About 新圖示與名稱。
19. 觀察到的執行期外部網路請求為 0，無前端例外。

測試後恢復原設定及背景檔，只清除本次建立的歷史紀錄，保留使用者的其他歷史。實際畫面見 [P0.md](P0.md)。原生關閉動作已確認先儲存設定，再退出 FileConverter.exe；退出清理由 Rust / Windows Job Object 執行。

## Windows 圖示與部署

- 指定 Downloads PNG 可讀取，1254×1254，SHA-256 與專案保留副本一致，原檔未變更。
- 4 組圖示驗證通過：來源／SHA、等比例 PNG 與 ICO 尺寸、名稱與識別碼／封裝範圍、實際 PE 資源。
- FileConverter.exe、FileConverterEngine.exe、NSIS Installer 的 ICO frame 像素逐一比對一致，涵蓋 16／20／24／32／40／48／64／96／128／256px；32／64／128／256／512px UI PNG 同源且清晰。
- 唯讀 Win32 Shell 及目前應用視窗的 32px 圖示擷取，與來源像素平均差為 0。只檢查本應用，沒有清除全系統圖示快取。
- NSIS 實際生成腳本的 Installer／Uninstaller 圖示指向新 ICO；桌面與開始功能表捷徑指向 FileConverter.exe，解除安裝項目的 DisplayIcon 也指向本程式。
- Tauri 未設定 fileAssociations，生成安裝腳本沒有 APP_ASSOCIATE／APP_UNASSOCIATE 呼叫。未修改預設開啟程式、其他應用圖示或全系統檔案類型圖示。
- Portable ZIP 另外核對內含 EXE 與 release EXE 的 SHA-256；安裝包 EXE 與 Portable 僅差 Tauri 官方的三個 bundle-type 標記位元組（UNK → NSS），其他所有位元組一致。發行檔 SHA-256 位於 `release/SHA256SUMS.json`。

## 尚待後續階段／環境驗證

- P1：完整 LibreOffice Runtime 封裝、更多格式／OCR／PDF → DOCX 及硬體加速擴充。現有 Office Adapter 保留，但本機無 LibreOffice，不能宣稱全部 Office 配對已完成實測。
- P2–P4：壓縮、電子書、物件修復、下載與工作流程尚未實作，介面停用並標階段。
- 中介 Graph 僅提供規劃，P0 僅執行直接轉換。
- Windows 10、未安裝開發工具的乾淨機安裝／解除安裝、實體多螢幕 DPI、已釘選舊捷徑的 Shell cache 更新仍需環境驗收。
- Portable 需要已安裝 WebView2；Installer 附帶離線 WebView2 安裝包。兩者均未簽章。
- 整個 OS 視窗 alpha 尚未完成 WebView2 相容性驗證，因此不提供假滑桿；背景與面板透明度已獨立實作。
- NVENC 仍以現有實際編碼前測方式判斷；此機並未完成所有 GPU／驅動組合驗收。
- 數千筆清單、超大型檔案、ICC／HDR／動畫與多頁 TIFF 保真、損壞或加密文件的全部邊界仍需進一步量測。沒有新增人為檔案大小上限。

原始機器紀錄與測試產物在忽略的 `.tools/` 與 `test-results/`；Git 僅保留程式碼、報告與挑選的實際畫面。未上傳憑證、環境檔、快取、測試輸入或編譯產物。
