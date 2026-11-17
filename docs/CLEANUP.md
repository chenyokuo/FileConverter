# 交付清理紀錄

P5 正式驗收仍待乾淨 Windows 環境及散布閘門，依使用者規則 **未執行最終舊版交付清理**。

保留的舊版：File Converter 0.3.0 Installer／Portable、RAI 0.1.0／0.2.0 Installer／Portable 與既有舊 Portable 資料夾。沒有刪除 Git 歷史、舊 Tags、測試來源或使用者檔案。必要依賴與下載快取保留，避免下一次重複下載。

本輪僅從專案生成的 Runtime staging 移除 LibreOffice 自測 `.~lock.cl-test.ods#`，排除 MSI／抽取插件／`.ready`／暫存檔，並在專案 `.tools/` 保留上一份 Sidecar 供回復。測試安裝由其本身的 uninstaller 移除；設定、歷史及自動化資料逐表雜湊相同，未刪除個人資料。

正式驗收全部通過後，先確認最新 Installer、ZIP 與 SHA，建立正式回復 Tag，再僅清理專案 `release/` 中列出的過期交付物及已確認廢棄的建置產物。清理目標必須先解析並確認位於該資料夾內。
