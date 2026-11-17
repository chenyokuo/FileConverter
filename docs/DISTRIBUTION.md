# 散布與授權驗收

應用程式採 AGPL-3.0-or-later，未取得 Artifex 或其他專有商業授權。外部 Runtime 與 DLL 保留各自授權。版本、來源、SHA-256 見 `engine-lock.json`；staged 檔案雜湊在候選包 `engines/payload-manifest.json`，授權文字和 build configuration 在 `licenses/`。

審核結果：LibreOffice 為 MPL-2.0 及其元件授權；FFmpeg 本版啟用 GPL（含 x264/x265），不能宣稱 LGPL-only；Calibre GPL-3.0-or-later；Pandoc GPL-2.0-or-later；Ghostscript／MuPDF AGPL；pdf2docx 本體 MIT，但不免除 MuPDF 依賴；OpenCV Apache-2.0 及 wheel notices；pillow-heif 本體 BSD，Windows wheel 含 LGPL-3.0 libheif/libde265 與 GPL-2.0-or-later x265。已查 x265 4.3 程式碼授權頭允許 later versions，避免誤把 wheel 當單純 BSD。7-Zip unRAR 限制保留，僅解 RAR。Deno MIT；yt-dlp Python 函式庫 Unlicense，依賴仍遵循各自條款。WebView2 Fixed Runtime 為 Microsoft 原始散布條款，已驗證 Microsoft 簽章，不修改系統 Runtime。

目前仍有對外散布閘門：完整應用程式來源與建置流程已在本機 Git，但私人 GitHub 不保證每位收件者可存取。尚未彙整每個外部 GPL/AGPL/LGPL 二進位建置的完整 corresponding-source 封存，尤其 Gyan FFmpeg 的所有 codec／建置依賴、Calibre 所帶元件及 linked codec libraries。上游 URL 和版本是盤點證據，不能宣稱它們已取代完整 source delivery。沒有代使用者承諾尚無履行安排的書面原始碼供應要約。

候選包供目前專案持有人開發與驗收；完成收件者來源提供方案並確認外部二進位相應來源完整可取得後，才可作為朋友／客戶散布版本。這不影響本機功能驗證，也不把成功建置等同授權驗收完成。
