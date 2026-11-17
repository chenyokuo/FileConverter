# 架構與實作順序

1. 完成離線前端、六種 Glass Material、背景與設定保存。
2. 建立白名單 Rust IPC 與 Python JSONL sidecar，SQLite 保存狀態。
3. 實作 1–4 並行的工作程序佇列、取消／錯誤／重試、原檔保護與不覆寫輸出。
4. 依相容矩陣實作 Pillow、MuPDF、FFmpeg、LibreOffice adapter。
5. 原始與凍結 sidecar 都執行生成檔案測試；實際 Windows GUI 檢查。
6. 建立 release EXE、Portable 與 NSIS 安裝包，記錄已驗收及待驗證事項。
7. 完成敏感檔與產物排除檢查，建立本機 main commit；使用者確認後才建立私人 GitHub Repository 與 Push。

## IPC

WebView → `engine_call(method,args)` → Rust 固定命令白名單 → JSONL stdin → Python Service → subprocess Worker → 真實引擎。

Service stdout 為 JSONL response / job event；Rust 以 request ID 配對回應，事件透過 Tauri `engine-job` 推送。stderr 獨立排空，避免引擎錯誤填滿 pipe 阻塞佇列。Rust IPC 於 blocking task 等待回應，主 UI thread 不被轉檔阻塞。

使用者輸入檔與輸出目錄是本機選檔／拖放的路徑。前端無 Shell 與任意指令權限。Python 只執行附帶或檢測的引擎，以參數陣列傳遞；輸出檔先在同磁碟暫存，Windows 使用不覆寫的 rename，遇到短暫索引／防毒鎖定會有限重試。每個檔案建立後不會替換原始檔；同名輸出自動加編號。

## 持久化

`%APPDATA%/studio.rai.converter/history.sqlite3` 保存設定與 jobs。背景依 EXIF 方向解碼後，以原尺寸、保留 alpha 的無損 WebP 保存，設定中保存本機 data URI，因此移動來源圖片不會失效。外觀預設也保存完整外觀。關閉視窗先保存最後一次設定，再銷毀視窗。程式退出終止 sidecar；Windows Job Object 清理全部子程序。重新啟動會將中斷任務標為取消，避免無聲重新執行。

## 材質

每種材質獨立 CSS 變數：rgb / alpha / blur / border / shadow；主工作區固定 blur=0，CSS 明確為 backdrop-filter:none。`background` 與 `backdrop-filter` 只套用在面板，絕不使用面板容器 `opacity` 讓文字淡化。背景獨立圖層處理 opacity、brightness、blur、position、scale；遮罩為獨立圖層。Motion 120–350ms 動畫，清單數量較大時停用 layout animation。

## 已知邊界

P0 由 Rust infer 提供 16 KiB 檔頭提示，Python 依 Pillow 解碼器、PDF、OOXML/ODF ZIP、OLE CFB 串流目錄、RTF、FFprobe 與容器標頭辨識實際內容。副檔名只供交叉檢查；工作程序轉檔前再次驗證。250 筆匯入已測試，數千筆列表仍需虛擬化與效能量測。單檔設定與同類批次設定皆實作，既有執行任務不能重排；待提交清單可重排。ETA 只有執行中任務進度足夠、沒有等待任務時才顯示。

Office adapter 已實作，沒有安裝 LibreOffice 的測試機不能宣稱已驗證所有 Office 組合。PDF → DOCX 未實作且無可點的假操作。未加入非必要動畫套件、網路服務、登入功能或追蹤。


v0.2.0 以 ConversionWorkspace 元件重構轉檔首頁，移除 Dashboard 宣傳內容。外觀 schema version 2 遷移舊版預設，保留自訂背景與使用者參數；主工作區的歷史 blur 值一律停用。所有轉檔命令、格式矩陣、SQLite 與 subprocess 佇列架構沿用。

## P0 統一能力與雙模式

`registry.py` 是唯一相容矩陣，`formats.py` 僅保留相容匯出。每條 edge 包含來源、目標、Adapter、引擎可用性、回歸案例覆蓋、損失風險、輸出設定、品質提示與中介資訊。`snapshot`、`registry` 供兩種 UI 模式及工具箱共用。worker 執行前使用同一個 `validate`，不信任前端格式選擇。`ConversionGraph.path` 以 BFS 規劃可用路徑；P0 僅執行直接 edge，不把跨格式鏈結當成已完成的轉檔能力。

Adapter 介面拆出 `adapters.py`，實際 Pillow / MuPDF / FFmpeg / LibreOffice 處理沿用並分成獨立函式。自動模式目標為空；指定模式記錄預期來源，來源不符必須取消勾選或重新設定。PDF → PDF 必須明確指定頁碼、旋轉、分割或多檔合併。

產品／主程式更名為 File Converter / FileConverter.exe，但 `studio.rai.converter`、SQLite schema 與舊瀏覽器外觀 key 保留，維持既有設定／歷史相容。原圖保存在圖示來源目錄，打包只包含新版 FileConverterEngine。未加入 Windows 檔案關聯或全系統圖示變更。
