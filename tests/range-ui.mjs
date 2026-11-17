import { chromium, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
execFileSync(".venv/Scripts/python.exe", [
  "-X",
  "utf8",
  "tests/make_range_fixture.py",
]);
const browser = await chromium.launch({ channel: "msedge", headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1500, height: 960 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto("http://127.0.0.1:1420/tests/range-harness.html");
  const start = page.getByRole("textbox", { name: "起始時間", exact: true }),
    end = page.getByRole("textbox", { name: "結束時間", exact: true });
  await expect(end).toHaveValue("00:02:00");
  await start.fill("00:00:10");
  await start.press("Enter");
  await expect(page.getByRole("slider", { name: "起點把手" })).toHaveAttribute(
    "aria-valuenow",
    "10",
  );
  const handle = page.getByRole("slider", { name: "終點把手" });
  await handle.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(end).toHaveValue("00:01:59");
  const box = await page.locator(".range-track").boundingBox();
  const from = await page
    .getByRole("slider", { name: "起點把手" })
    .boundingBox();
  await page.mouse.move(from.x + from.width / 2, from.y + 40);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.25, box.y + 40, { steps: 15 });
  await page.mouse.up();
  await expect(start).toHaveValue("00:00:30");
  await end.fill("00:00:05");
  await end.press("Enter");
  await expect(end).toHaveValue("00:00:31");
  await start.fill("oops");
  await start.press("Enter");
  await expect(start).toHaveAttribute("aria-invalid", "true");
  await start.fill("00:00:10");
  await start.press("Enter");
  await page.getByRole("checkbox", { name: "只輸出所選片段" }).check();
  await page.getByRole("button", { name: "新增區間", exact: true }).click();
  await expect(page.locator("#value")).toContainText('"only":true');
  await expect(page.getByRole("button", { name: "移除片段 2" })).toBeVisible();
  await page.getByRole("button", { name: "重設區間" }).click();
  await expect(start).toHaveValue("00:00:00");
  await expect(end).toHaveValue("00:02:00");
  await page.locator("video").evaluate(async (v) => {
    await v.play();
  });
  await expect
    .poll(() => page.locator("video").evaluate((v) => v.currentTime))
    .toBeGreaterThan(0.1);
  await page.locator(".range-track").scrollIntoViewIfNeeded();
  const seekBox = await page.locator(".range-track").boundingBox();
  await page.mouse.click(seekBox.x + seekBox.width * 0.5, seekBox.y + 55);
  await expect
    .poll(() => page.locator("video").evaluate((v) => v.currentTime))
    .toBeGreaterThan(59);
  await page.locator("video").evaluate((v) => v.pause());
  await page.setViewportSize({ width: 1500, height: 1300 });
  await page.locator(".app").evaluate((e) => (e.scrollTop = 0));
  await page.screenshot({ path: "test-results/download-range-ui.png" });
  for (const width of [1000, 760]) {
    await page.setViewportSize({ width, height: 960 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }

  await page.goto("http://127.0.0.1:1420/tests/range-harness.html?duration=0");
  await expect(page.getByRole("slider", { name: "起點把手" })).toBeDisabled();
  await expect(
    page.getByRole("checkbox", { name: "只輸出所選片段" }),
  ).toBeDisabled();
  // Component boundary test: synthetic metadata only; real network/FFmpeg are tested in Python.
  await page.addInitScript(() => {
    window.isTauri = true;
    window.__TAURI_INTERNALS__ = {
      invoke: async (cmd, args) => {
        if (args.method === "analyze_url")
          return {
            analysisId: "fixture",
            title: "自有測試影片",
            duration: 120,
            playlist: false,
            entries: [
              {
                key: "1",
                id: "owned",
                title: "自有測試影片",
                url: "https://example.org/owned",
                duration: 120,
                previewUrl: "/.tools/range-preview.mp4",
                formats: [],
                subtitles: [],
                resolved: true,
              },
            ],
            page: 1,
            hasMore: false,
          };
        if (args.method === "enqueue_download") {
          window.__rangePayload = args.args;
          return [{ id: "fixture-job" }];
        }
        throw new Error("Unexpected test IPC");
      },
    };
  });
  await page.setViewportSize({ width: 1500, height: 960 });
  await page.goto("http://127.0.0.1:1420/tests/range-harness.html?page");
  await page
    .getByRole("textbox", { name: "影片網址" })
    .fill("https://example.org/owned");
  await page.getByRole("button", { name: "解析網址" }).click();
  await page
    .getByRole("textbox", { name: "起始時間", exact: true })
    .fill("00:00:15");
  await page
    .getByRole("textbox", { name: "起始時間", exact: true })
    .press("Enter");
  await page
    .getByRole("textbox", { name: "結束時間", exact: true })
    .fill("00:00:45");
  await page
    .getByRole("textbox", { name: "結束時間", exact: true })
    .press("Enter");
  await page.getByRole("checkbox", { name: "只輸出所選片段" }).check();
  await page.getByRole("button", { name: "下載所選片段 1" }).click();
  expect(
    await page.evaluate(() => window.__rangePayload.items[0].sections),
  ).toEqual([{ start: 15, end: 45 }]);
  await page.getByRole("checkbox", { name: "只輸出所選片段" }).uncheck();
  await page.getByRole("button", { name: "下載選取項目 1" }).click();
  expect(
    await page.evaluate(() => window.__rangePayload.items[0].sections),
  ).toEqual([]);
  expect(errors).toEqual([]);
  console.log(
    "PASS: actual pointer drag, keyboard, input validation/clamping, multi-ranges, reset, media playback/seek, responsive widths; no browser errors.",
  );
} finally {
  await browser.close();
}
