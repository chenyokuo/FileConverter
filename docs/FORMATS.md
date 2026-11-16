# 轉換相容矩陣

矩陣真實來源為 `engine/registry.py`（`formats.py` 保留舊呼叫相容性）。同副檔名允許重新編碼或處理，不會覆寫輸入。

| 輸入 | 允許輸出 | 引擎 / 限制 |
|---|---|---|
| MP4, MOV, MKV, AVI, WebM, M4V | MP4, MOV, MKV, AVI, WebM；MP3, WAV, FLAC, AAC, OGG, M4A, Opus | FFmpeg；音訊輸出需要來源音軌；WebM 強制 VP9 / Opus，AVI 強制 MPEG-4 |
| MP3, WAV, FLAC, AAC, OGG, M4A, Opus | MP3, WAV, FLAC, AAC, OGG, M4A, Opus | FFmpeg；不將音訊假裝轉成影片 |
| JPG, JPEG, PNG, WebP, BMP, TIF, TIFF | PNG, JPG, WebP, BMP, TIFF, PDF | Pillow；動畫與多頁 TIFF 目前僅處理第一畫格／第一頁 |
| PDF | PNG, JPG | MuPDF；每頁一張圖片，36–600 DPI |
| PDF | PDF | MuPDF；必須明確指定頁碼擷取、逐頁分割或 90/180/270° 旋轉，不接受空操作 |
| 多份圖片 / PDF | PDF | MuPDF；依 GUI 清單順序合併，可混合圖片與 PDF |
| DOCX, ODT, DOC, RTF | PDF, DOCX, ODT, RTF, TXT（依下列精確限制） | LibreOffice；僅文字文件族群 |
| XLSX, ODS, XLS | PDF, XLSX, ODS, CSV | LibreOffice；CSV 不保留多工作表與樣式 |
| PPTX, ODP, PPT | PDF, PPTX, ODP | LibreOffice；僅簡報族群 |

RTF 不提供 RTF→RTF，DOC 不提供 DOC→DOC；其餘依程式矩陣。加密 PDF 需先解密。Office 轉檔使用獨立使用者設定目錄，避免干擾正在使用的 LibreOffice。缺少來源字型時排版可能變化。

影片選項：CPU H.264 / H.265、WebM VP9、NVIDIA H.264 NVENC；CRF 或 kbps、目標高度、FPS。NVENC 先執行小型編碼測試，無可用硬體／驅動會失敗並提供錯誤，使用者可選 CPU 重試。來源影音的解碼支援依附帶的 FFmpeg build，損毀檔與不相容參數會顯示真實錯誤。

圖片設定為單張輸出，保留 EXIF 方向但不承諾保留所有中繼資料／ICC／HDR。JPEG / BMP 輸出將透明區域鋪上指定底色。尺寸 0 為自動；寬高都指定時使用指定尺寸。

沒有上傳、外部雲端 API 或人為檔案大小上限。Pillow 對解壓縮炸彈的內建像素安全檢查仍生效；實際處理受儲存、記憶體及引擎限制。


P0 的 UI 兩種模式與工具箱均讀取 Registry，而不是各自保存格式清單。實際內容經 Rust infer 提示、解碼器／容器解析後，才交叉檢查副檔名。JPEG／TIF／M4V 分別正規化為 JPG／TIFF／MP4。每個 worker 會再次辨識，避免來源在匯入後遭替換時使用錯誤引擎。

Registry 的測試狀態只代表目前整合測試有對應來源／目標案例，不代表所有選項、輸入內容與編碼器皆已驗證。Office 能力仍取決於外部 LibreOffice，尚未通過完整配對驗收。Graph 可查詢中介路徑，但 P0 不執行間接轉換；例如 PDF → PNG → WebP 的規劃不會讓 PDF → WebP 出現在直接輸出選單。
