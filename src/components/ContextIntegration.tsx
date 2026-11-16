import { useEffect, useState } from "react";
import { call, desktop } from "../api";
import { Button } from "./ui";
export function ContextIntegration({
  notify,
}: {
  notify: (s: string, error?: boolean) => void;
}) {
  const [status, setStatus] = useState({
      available: false,
      enabled: false,
      reason: "",
    }),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (desktop)
      void call<typeof status>("context_menu")
        .then(setStatus)
        .catch((e) => notify(String(e), true));
  }, []);
  return (
    <section className="settings-card glass" data-material="settings">
      <h3>檔案總管右鍵整合</h3>
      <p>
        新增 File Converter 獨立選單；依合法來源提供 PDF、JPG 或 MP3。Windows 11
        可在「顯示其他選項」查看。
      </p>
      <Button
        disabled={!status.available || busy}
        onClick={async () => {
          setBusy(true);
          try {
            setStatus(await call("context_menu", { enabled: !status.enabled }));
            notify(
              status.enabled
                ? "已移除 File Converter 右鍵項目"
                : "已加入 File Converter 右鍵項目",
            );
          } catch (e) {
            notify(String(e), true);
          } finally {
            setBusy(false);
          }
        }}
      >
        {status.enabled ? "停用並移除右鍵項目" : "啟用右鍵項目"}
      </Button>
      <p className="hint">
        {status.reason ||
          "只更新目前使用者的專屬 shell 項目，不變更預設開啟程式或檔案類型圖示。"}
      </p>
    </section>
  );
}
