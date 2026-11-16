# Windows 視窗透明度研究

研究日期：2026-11-16。

背景圖片透明度、玻璃面板 alpha 與整個 OS 視窗 alpha 是三件獨立的事。前兩者已實作；整個 OS 視窗 alpha 暫不提供操作控制。

Windows 的 `WS_EX_LAYERED` + `SetLayeredWindowAttributes(..., LWA_ALPHA)` 可設定整個視窗 alpha，但整個視窗的文字與控制項也會一起變淡，與玻璃材質不同。[Microsoft Win32 說明](https://learn.microsoft.com/en-us/windows/win32/winmsg/window-features) 同時說明 layered window 的 hit testing 與 alpha=0 的滑鼠穿透行為。Tauri 的 transparent window 並不等同整個視窗的 alpha slider。

目前已編譯並採用 transparent frameless WebView2 視窗、CSS 玻璃與選用 Mica。Windows 11 的 Mica 用 Rust `window-vibrancy` 呼叫，不支援會回傳錯誤並保留 CSS 備援。Acrylic 不作預設，因 [Tauri 官方設定文件](https://v2.tauri.app/reference/config/) 與 [window-vibrancy README](https://github.com/tauri-apps/window-vibrancy) 記錄部分 Windows 10 / 11 的拖曳與大小調整效能問題。

尚未對 `SetLayeredWindowAttributes` 與此 WebView2 視窗的 DirectComposition、陰影、拖曳、縮放、最大化／還原及多螢幕 DPI 組合完成驗證，不能據此宣稱可正式使用。此功能沒有加入原生 API 或假滑桿；設定頁明確標示待驗證。後續若加入，必須提供 100% 一鍵恢復、避免不可操作的全透明，並完成 Windows 10、11、不同 WebView2 版本與硬體的驗收。
