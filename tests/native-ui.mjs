/** Runs against the real packaged WebView2 app via local CDP. Only the OS picker
 * return value is supplied by the test; all IPC, engines, files and persistence are real. */
import { chromium, expect } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
const root = process.cwd();
const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
const context = browser.contexts()[0];
const page = context.pages().find((p) => p.url().includes("tauri.localhost"));
if (!page)
  throw new Error(
    "Start the release app with WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222",
  );
const failures = [];
const network = [];
const results = [];
page.on("pageerror", (e) => failures.push(e.message));
page.on("request", (r) => {
  if (
    !r.url().startsWith("http://tauri.localhost") &&
    !r.url().startsWith("http://ipc.localhost") &&
    !r.url().startsWith("data:") &&
    !r.url().startsWith("blob:") &&
    !r.url().startsWith("ipc:")
  )
    network.push(r.url());
});
await fs.mkdir("test-results", { recursive: true });
const rpc = (method, args = {}) =>
  page.evaluate(
    ({ method, args }) =>
      window.__TAURI_INTERNALS__.invoke("engine_call", { method, args }),
    { method, args },
  );
const snapshot = await rpc("snapshot");
const slider = async (name, value) => {
  const el = page.getByRole("slider", { name, exact: true });
  await el.evaluate((node, value) => {
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    ).set.call(node, String(value));
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
  await expect(el).toHaveValue(String(value));
};
async function check(name, run) {
  try {
    await run();
    results.push({ name, status: "passed" });
    console.log("PASS", name);
  } catch (e) {
    results.push({ name, status: "failed", error: e.stack });
    throw e;
  }
}
try {
  await page.addInitScript(
    ({ image, source, out }) => {
      const original = window.fetch.bind(window);
      window.fetch = (request, options) => {
        if (
          decodeURIComponent(String(request)).includes("plugin:dialog|open")
        ) {
          const opts = JSON.parse(options.body).options || {};
          const result = opts.directory
            ? out
            : opts.filters?.length
              ? image
              : [source];
          return Promise.resolve(
            new Response(JSON.stringify(result), {
              status: 200,
              headers: {
                "Content-Type": "application/json",
                "Tauri-Response": "ok",
              },
            }),
          );
        }
        return original(request, options);
      };
    },
    {
      image: path.join(root, ".tools/ui-fixtures/玻璃背景 測試.png"),
      source: path.join(root, ".tools/ui-fixtures/中文 alpha & 測試.png"),
      out: path.join(root, "test-results/UI 輸出 & output"),
    },
  );
  await page.reload();
  await check("native background import and independent alpha", async () => {
    await page.getByRole("button", { name: "設定", exact: true }).click();
    await page.getByRole("button", { name: "匯入圖片", exact: true }).click();
    await expect(page.locator(".wallpaper")).toHaveClass(/wallpaper-image/);
    expect(
      await page.locator(".wallpaper").evaluate((e) => e.style.backgroundImage),
    ).toContain("data:image/webp;base64,");
    await slider("背景圖片透明度", 37);
    await expect(page.locator(".wallpaper")).toHaveCSS("opacity", "0.37");
    await expect(page.locator(".app")).toHaveCSS("opacity", "1");
    await slider("背景亮度", 112);
    await slider("背景模糊", 9);
    await slider("暗色遮罩", 32);
    await expect(page.locator(".wallpaper")).toHaveCSS(
      "filter",
      "brightness(1.12) blur(9px)",
    );
    await slider("圖片縮放", 125);
    await slider("水平位置", 62);
    await slider("垂直位置", 33);
  });
  await check(
    "all six glass materials have independent real styles",
    async () => {
      const names = {
        sidebar: "側邊導覽",
        main: "主工作區",
        card: "檔案卡片",
        modal: "對話視窗",
        toolbar: "浮動工具列",
        settings: "設定面板",
      };
      for (const [key, name] of Object.entries(names)) {
        await page.getByRole("button", { name, exact: true }).click();
        await slider("面板不透明度", 27);
        await slider("玻璃模糊", 31);
        expect(
          await page
            .locator(".app")
            .evaluate(
              (e, key) => e.style.getPropertyValue(`--${key}-alpha`),
              key,
            ),
        ).toBe("0.27");
        expect(
          await page
            .locator(".app")
            .evaluate(
              (e, key) => e.style.getPropertyValue(`--${key}-blur`),
              key,
            ),
        ).toBe("31px");
      }
      // Verify a mounted panel, rather than only reading the variables.
      const color = await page
        .locator(".sidebar")
        .evaluate((e) => getComputedStyle(e).backgroundColor);
      expect(color).toContain("0.27");
      await expect(page.locator(".sidebar")).toHaveCSS(
        "backdrop-filter",
        "blur(31px)",
      );
      await expect(page.locator(".sidebar nav")).toHaveCSS("opacity", "1");
    },
  );
  await check(
    "appearance preset save/apply and SQLite persistence",
    async () => {
      await page
        .getByRole("button", { name: "儲存目前外觀", exact: true })
        .click();
      await page.getByPlaceholder("例如：午夜工作室").fill("UI 驗收配置");
      await page.getByRole("button", { name: "儲存配置", exact: true }).click();
      await expect(
        page.getByText("UI 驗收配置", { exact: true }),
      ).toBeVisible();
      await expect
        .poll(
          async () => (await rpc("snapshot")).settings.appearance.imageOpacity,
        )
        .toBe(37);
      const saved = (await rpc("snapshot")).settings;
      expect(saved.appearance.materials.sidebar.blur).toBe(31);
      expect(saved.presets.some((p) => p.name === "UI 驗收配置")).toBe(true);
      await page.reload();
      await expect(page.locator(".wallpaper")).toHaveCSS("opacity", "0.37");
      await page.getByRole("button", { name: "設定", exact: true }).click();
      await expect(
        page.getByText("UI 驗收配置", { exact: true }),
      ).toBeVisible();
    },
  );
  await check("light/dark theme and reduced motion", async () => {
    await page.getByRole("button", { name: "淺色", exact: true }).click();
    await expect(page.locator(".app")).toHaveClass(/theme-light/);
    await page.getByRole("button", { name: "深色", exact: true }).click();
    await page.getByRole("button", { name: "效能", exact: true }).click();
    await page.getByRole("switch", { name: /減少動態效果/ }).check();
    await expect(page.locator(".app")).toHaveClass(/reduced-motion/);
  });
  // Restore default readable material levels before conversion and screenshots.
  await rpc("settings", {
    settings: {
      ...snapshot.settings,
      appearance: {
        ...snapshot.settings.appearance,
        background: "image",
        image: (await rpc("snapshot")).settings.appearance.image,
      },
    },
  });
  await page.reload();
  await check(
    "GUI file inspect, lawful format list and actual queued conversion",
    async () => {
      await page.getByRole("button", { name: "檔案轉換", exact: true }).click();
      await page.getByRole("button", { name: "加入檔案", exact: true }).click();
      await expect(page.locator(".draft-row")).toHaveCount(1);
      await expect(page.locator(".draft-row select option")).toHaveText([
        "PNG",
        "JPG",
        "WEBP",
        "BMP",
        "TIFF",
        "PDF",
      ]);
      await page.locator(".draft-row select").selectOption("png");
      await expect(
        page.getByRole("slider", { name: "圖片品質", exact: true }),
      ).toHaveCount(0);
      await page.locator(".draft-row select").selectOption("webp");
      await expect(
        page.getByRole("slider", { name: "圖片品質", exact: true }),
      ).toHaveCount(1);
      await page.getByRole("button", { name: /開始轉換/ }).click();
      await expect(page.locator(".job-row .status.completed")).toHaveCount(
        snapshot.jobs.filter((j) => j.status === "completed").length + 1,
        { timeout: 30000 },
      );
      const jobs = (await rpc("snapshot")).jobs;
      const job = jobs.find(
        (j) => !snapshot.jobs.some((old) => old.id === j.id),
      );
      expect(job.status).toBe("completed");
      expect(job.outputs[0]).toMatch(/\.webp$/);
      expect((await fs.stat(job.outputs[0])).size).toBeGreaterThan(10);
    },
  );
  await check("history search and real retry", async () => {
    await page.getByRole("button", { name: "轉換紀錄", exact: true }).click();
    await page
      .getByRole("textbox", { name: "搜尋轉換紀錄" })
      .fill("中文 alpha");
    await expect(page.locator(".history-list .job-row")).toHaveCount(1);
    await page.getByRole("button", { name: /重新轉換 中文 alpha/ }).click();
    await expect(page.locator(".history-list .status.completed")).toHaveCount(
      2,
      { timeout: 30000 },
    );
  });
  await check("maximize and restore native window", async () => {
    const before =
      page.viewportSize() ||
      (await page.evaluate(() => ({ width: innerWidth, height: innerHeight })));
    await page
      .getByRole("button", { name: "最大化或還原", exact: true })
      .click();
    await page.waitForTimeout(350);
    const max = await page.evaluate(() => ({
      width: innerWidth,
      height: innerHeight,
    }));
    expect(max.width).toBeGreaterThanOrEqual(before.width);
    await page
      .getByRole("button", { name: "最大化或還原", exact: true })
      .click();
  });
  await check("125 / 150 / 200 percent layout emulation", async () => {
    await page.getByRole("button", { name: "工作概覽", exact: true }).click();
    const cdp = await context.newCDPSession(page);
    for (const scale of [1.25, 1.5, 2]) {
      const width = Math.floor(1920 / scale),
        height = Math.floor(1080 / scale);
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width,
        height,
        deviceScaleFactor: scale,
        mobile: false,
      });
      await page.waitForTimeout(350);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await expect(
        page.getByRole("button", { name: "工作概覽", exact: true }),
      ).toBeVisible();
      await page.screenshot({ path: `test-results/layout-${scale * 100}.png` });
    }
    await cdp.send("Emulation.clearDeviceMetricsOverride");
  });
  await check("runtime makes no external network requests", async () => {
    expect(network).toEqual([]);
    expect(failures).toEqual([]);
  });
} finally {
  await fs.writeFile(
    "test-results/native-ui.json",
    JSON.stringify(
      {
        results,
        failures,
        network,
        notes:
          "Real release WebView2 and IPC. OS file picker result supplied by harness. DPI is renderer emulation, not multi-monitor OS DPI certification.",
      },
      null,
      2,
    ),
  );
  await rpc("settings", { settings: snapshot.settings });
  if (!snapshot.jobs.length) await rpc("clear");
  await page.reload();
  await browser.close();
}
