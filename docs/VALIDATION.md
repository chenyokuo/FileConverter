最新版 1.1.0-rc.2 修復與實際封裝驗證請見 [RC2 修復驗收](REPAIRS_RC2.md)；前版記錄見 [Multimedia P5](MULTIMEDIA_P5.md)。以下保留 1.0.0-rc.1 歷史紀錄。

# P5 驗收紀錄 — 1.0.0-rc.1

2026-11-16，Windows x64 開發主機；所有素材由測試建立，RAR 使用 libarchive 官方 RAR5 stored 開源測試素材。沒有將使用者檔案上傳。P1–P4 只有相關測試和增量編譯，P5 才統一封裝。

| 驗證 | 實際結果 |
|---|---|
| 完整來源回歸 | 55 項，53 通過、2 當時跳過。之後以空 Runtime 實測 missing-LO：來源／凍結版均通過；建置 EXE 圖示另行驗證。新增影片預覽案例亦通過 |
| 直接轉換矩陣 | 305/305；圖片實際解碼、媒體試解碼、文件內文／儲存格／投影片 XML、舊 Office 渲染、PDF 頁面與文字、電子書內文及壓縮展開 |
| 凍結 Sidecar | 核心 23 項：22 通過、1 missing-LO 跳過；P2–P4 20/20 通過。Office 巨集／主動內容停用後受影響預覽案例再測通過 |
| 真實 GUI／IPC | 開發模式 22 組、實際 Portable 候選 23 組通過；外觀、六材質、佇列、真實轉檔、歷史、視窗、工作流程、預設、預覽、參數變更與鍵盤關閉 |
| 版面 | 1500×960 與常見桌面尺寸；125/150/200% renderer DPI 模擬通過。這不是 Windows 多螢幕實體 DPI 認證 |
| Windows 選用整合 | 實際 HKCU 專屬 shell 啟停／清理、第二次啟動轉送通過；測試後恢復原右鍵狀態，沒有修改預設關聯 |
| WebView2 | app-local 固定版 157.0.4341.60，Microsoft 簽章 Valid，CDP 回報同版 |
| 大來源 | 1,073,741,868 bytes WAV：實際辨識，串流裁切 2 秒 FLAC 並解碼驗證 |
| 大量 GUI | 250 個真實長中文／特殊字元檔名；匯入、批次 JPG 設定、清空與 1500×960 無水平溢出通過；逐項高成本動畫在大量檔案停用 |
| 取消與原檔 | 真實 worker／FFmpeg 程序樹結束，原檔雜湊、撞名另存、失敗不阻斷整批；已在來源與 frozen 核心回歸驗證 |
| 網址下載 | 自有本機 HTTP/HLS：720/1080 實際畫質、播放清單選單項目、字幕內容、四種音訊、取消後 Range 續傳、並行本機轉檔。未宣稱所有外部網站永久可用 |

矩陣驗證最初把 FFmpeg 測試參數寫成 `.25`，被本版 CLI 拒絕；修正為 `0.25` 後直接對已實際轉換出的 127 個媒體檔重新解碼，沒有為測試錯誤重新編碼其餘成功項目。最終逐方向結果在 `test-results/matrix.json`，成功方向列於 `engine/verified-capabilities.json`。

## 本機硬體量測

自製 1080p30、3 秒測試來源，H.264 fast、CRF/QP 23。CPU libx264：0.645 秒、139.43 wall FPS、SSIM 0.995061、2,274,349 bytes。AMD h264_amf：0.485 秒、185.70 wall FPS、SSIM 0.980053、3,938,577 bytes。CRF 與 QP 並非相同率控制，這是使用相同數值設定的實測；含初始化成本，單次樣本，不是普遍效能保證；GPU 較快但不代表更佳品質。AMD HEVC 在此機不可用，明確指定 AMD 時已驗證退回 libx265 並產生可讀 HEVC；此機 NVIDIA／Intel 實際探測失敗，僅驗證不可用與 CPU 備援，沒有宣稱在實體 NVIDIA／Intel 裝置完成輸出測試。

## 尚未通過的正式驗收閘門

目前未找到可用 Windows Sandbox／Hyper-V，使用者亦已確認沒有乾淨 VM／實機。已完成僅含 Windows 系統目錄 PATH 的凍結引擎 9 組代表功能與 Portable GUI；仍不能將同一開發主機測試宣稱為「無任何開發／引擎安裝的乾淨 Windows 電腦」驗收。實體多螢幕／不同 Windows OS DPI 亦未驗證。

對外散布的完整 corresponding-source 交付尚待完成，見 [散布要求](DISTRIBUTION.md)。候選包未簽署。這些項目未完成前，不標示 P5 正式通過、不清理舊版交付檔、不建立正式發行 Tag 或 Push main，以遵守使用者「最終整合驗收通過再同步」的要求。

Release／Installer／Portable、PE 圖示、安裝／移除、ZIP 全 CRC、Runtime 項目／雜湊及交付 SHA-256 檢查已通過；詳見 `docs/P5.md` 與 `docs/validation/release-verification.json`。只有乾淨 Windows／實體環境及散布閘門仍未完成。

P5 額外修正：Tauri 安裝版 verbatim 路徑不直接交給 C 引擎／右鍵登錄；Tesseract 於隔離 worker 以相對模型路徑載入，已驗證中文模型目錄與英文／繁中 OCR。繁中＋English 採繁中優先，仍有辨識錯字，不能宣稱完美還原。
