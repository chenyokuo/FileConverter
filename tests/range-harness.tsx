import React, { useState } from "react";
import { DownloadPage } from "../src/components/DownloadPage";
import { createRoot } from "react-dom/client";
import { DownloadRange, defaultRanges } from "../src/components/DownloadRange";
import "@fontsource/inter/latin-400.css";
import "@fontsource/noto-sans-tc/400.css";
import "../src/styles.css";
import { defaults } from "../src/defaults";
function Harness() {
  const [value, setValue] = useState(defaultRanges());
  return (
    <div
      className="app theme-dark"
      style={
        {
          padding: 24,
          minHeight: "100vh",
          overflow: "auto",
          "--accent": defaults.appearance.accent,
          "--accent-rgb": defaults.appearance.accent
            .slice(1)
            .match(/../g)!
            .map((v) => parseInt(v, 16))
            .join(" "),
        } as React.CSSProperties
      }
    >
      <h1>網址下載</h1>
      <div style={{ maxWidth: 1000, margin: "auto" }}>
        {new URLSearchParams(location.search).has("page") ? (
          <DownloadPage
            disabled={false}
            outputDir="test-output"
            onDirectory={() => {}}
            notify={() => {}}
          />
        ) : (
          <DownloadRange
            duration={Number(
              new URLSearchParams(location.search).get("duration") ?? 120,
            )}
            previewUrl="/.tools/range-preview.mp4"
            loading={false}
            value={value}
            onChange={setValue}
          />
        )}
        <output id="value">{JSON.stringify(value)}</output>
      </div>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<Harness />);
