/** Runs against the real packaged WebView2 app via local CDP. Only the OS picker
 * return value is supplied by the test; all IPC, engines, files and persistence are real. */
import { chromium, expect } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
const root = process.cwd();
const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
const context = browser.contexts()[0];
await expect
  .poll(
    () =>
      context
        .pages()
        .some(
          (p) =>
            p.url().includes("tauri.localhost") ||
            p.url().startsWith("http://127.0.0.1:1420"),
        ),
    { timeout: 15000 },
  )
  .toBe(true);
const page = context
  .pages()
  .find(
    (p) =>
      p.url().includes("tauri.localhost") ||
      p.url().startsWith("http://127.0.0.1:1420"),
  );
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
    !r.url().startsWith("http://127.0.0.1:1420") &&
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
const backgroundPath = path.join(snapshot.dataDir, "background.webp");
const originalBackground = await fs.readFile(backgroundPath).catch(() => null);
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
      window.__fileConverterPickerFiles = [source];
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
              : window.__fileConverterPickerFiles;
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
  await check(
    "home opens directly on conversion and uses readable typography",
    async () => {
      await expect(
        page.getByRole("heading", { name: "File Converter", exact: true }),
      ).toBeVisible();
      await expect(
        page.locator(".hero,.category-grid,.privacy-card"),
      ).toHaveCount(0);
      await expect(page.locator(".sidebar nav button")).toHaveCount(6);
      const metrics = await page.evaluate(() => ({
        body: parseFloat(
          getComputedStyle(document.querySelector(".app")).fontSize,
        ),
        nav: parseFloat(
          getComputedStyle(document.querySelector(".nav-item")).fontSize,
        ),
        button: parseFloat(
          getComputedStyle(document.querySelector(".start-conversion"))
            .fontSize,
        ),
        secondary: parseFloat(
          getComputedStyle(document.querySelector(".drop-subtitle")).fontSize,
        ),
        mainBlur: getComputedStyle(document.querySelector(".main-panel"))
          .backdropFilter,
        mainFilter: getComputedStyle(document.querySelector(".main-panel"))
          .filter,
      }));
      expect(metrics.body).toBe(16);
      expect(metrics.nav).toBeGreaterThanOrEqual(15);
      expect(metrics.button).toBeGreaterThanOrEqual(15);
      expect(metrics.secondary).toBeGreaterThanOrEqual(14);
      expect(metrics.mainBlur).toBe("none");
      expect(metrics.mainFilter).toBe("none");
    },
  );
  await check("native background import and independent alpha", async () => {
    await page.getByRole("button", { name: "設定", exact: true }).click();
    await page.getByRole("button", { name: "匯入圖片", exact: true }).click();
    await expect(page.locator(".wallpaper")).toHaveClass(/wallpaper-image/);
    await expect(
      page.getByRole("slider", { name: "背景模糊", exact: true }),
    ).toHaveValue("0");
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
        if (key !== "main") await slider("玻璃模糊", 31);
        else
          await expect(
            page.getByRole("slider", { name: "玻璃模糊", exact: true }),
          ).toHaveCount(0);
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
        ).toBe(key === "main" ? "0px" : "31px");
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
  await check(
    "clear / frosted background presets preserve the image and workspace sharpness",
    async () => {
      await page
        .getByRole("button", { name: "個人化外觀", exact: true })
        .click();
      const image = await page
        .locator(".wallpaper")
        .evaluate((e) => e.style.backgroundImage);
      await page
        .getByRole("button", { name: "毛玻璃背景", exact: true })
        .click();
      await expect(page.locator(".wallpaper")).toHaveCSS(
        "filter",
        "brightness(0.95) blur(12px)",
      );
      await expect(page.locator(".main-panel")).toHaveCSS(
        "backdrop-filter",
        "none",
      );
      await page.getByRole("button", { name: "清晰背景", exact: true }).click();
      await expect(page.locator(".wallpaper")).toHaveCSS("filter", "none");
      await expect(page.locator(".wallpaper")).toHaveCSS("opacity", "1");
      expect(
        await page
          .locator(".wallpaper")
          .evaluate((e) => e.style.backgroundImage),
      ).toBe(image);
      await expect
        .poll(
          async () =>
            (await rpc("snapshot")).settings.appearance.backgroundBlur,
        )
        .toBe(0);
      await page.reload();
      await expect(page.locator(".wallpaper")).toHaveCSS("filter", "none");
    },
  );
  await check(
    "mixed queue filtering, reordering and batch options remain functional",
    async () => {
      await page.getByRole("button", { name: "轉換檔案", exact: true }).click();
      await page.evaluate(
        (paths) => {
          window.__fileConverterPickerFiles = paths;
        },
        [
          path.join(root, ".tools/ui-fixtures/中文 alpha & 測試.png"),
          path.join(root, ".tools/ui-fixtures/產品圖片.jpg"),
          path.join(root, ".tools/ui-fixtures/使用說明.pdf"),
        ],
      );
      await page.getByRole("button", { name: "加入檔案", exact: true }).click();
      await expect(page.locator(".draft-row")).toHaveCount(3);
      await page
        .getByRole("button", { name: "中文 alpha & 測試.png", exact: true })
        .click();
      await page
        .locator(".draft-row")
        .first()
        .locator("select")
        .selectOption("webp");
      await slider("圖片品質", 78);
      await page
        .getByRole("button", { name: "套用至勾選的同類檔案", exact: true })
        .click();
      await page
        .getByRole("button", { name: "產品圖片.jpg", exact: true })
        .click();
      await expect(
        page.getByRole("slider", { name: "圖片品質", exact: true }),
      ).toHaveValue("78");
      await page
        .getByRole("button", { name: "上移 產品圖片.jpg", exact: true })
        .click();
      await expect(page.locator(".draft-name").first()).toHaveText(
        "產品圖片.jpg",
      );
      await page
        .locator(".type-filters button")
        .filter({ hasText: /^PDF/ })
        .click();
      await expect(page.locator(".draft-row")).toHaveCount(1);
      await page.getByRole("button", { name: "全選", exact: true }).click();
      await expect(
        page.getByRole("checkbox", { name: "選擇 使用說明.pdf", exact: true }),
      ).not.toBeChecked();
      await page
        .locator(".type-filters button")
        .filter({ hasText: /^全部/ })
        .click();
      await expect(page.locator(".draft-row")).toHaveCount(3);
      await page.getByRole("button", { name: "合併 PDF", exact: true }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await expect(page.locator(".merge-list li")).toHaveCount(2);
      await page.getByRole("button", { name: "關閉", exact: true }).click();
      await page
        .getByRole("button", { name: "清空待轉換檔案", exact: true })
        .click();
      await expect(page.locator(".draft-row")).toHaveCount(0);
    },
  );
  // Retain the imported fixture, but use the new clear profile for conversion screenshots.
  await rpc("settings", {
    settings: {
      ...snapshot.settings,
      appearance: {
        ...snapshot.settings.appearance,
        background: "image",
        ...(await rpc("snapshot")).settings.appearance,
      },
    },
  });
  await page.reload();
  await check(
    "GUI file inspect, lawful format list and actual queued conversion",
    async () => {
      await page.getByRole("button", { name: "轉換檔案", exact: true }).click();
      await page.getByRole("button", { name: "加入檔案", exact: true }).click();
      await expect(page.locator(".draft-row")).toHaveCount(1);
      await expect(page.locator(".draft-row select option")).toHaveText([
        "請選擇輸出格式",
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
  await check(
    "1500x960 and common desktop layouts keep primary controls on screen",
    async () => {
      const cdp = await context.newCDPSession(page);
      for (const [width, height] of [
        [1500, 960],
        [1360, 900],
        [1280, 720],
        [1024, 768],
        [760, 480],
      ]) {
        await cdp.send("Emulation.setDeviceMetricsOverride", {
          width,
          height,
          deviceScaleFactor: 1,
          mobile: false,
        });
        await page.waitForTimeout(200);
        await page.locator(".page-scroll").evaluate((e) => e.scrollTo(0, 0));
        for (const selector of [
          ".dropzone",
          ".draft-panel",
          ".conversion-toolbar",
          ".start-conversion",
        ]) {
          const bounds = await page.locator(selector).boundingBox();
          expect(bounds).not.toBeNull();
          expect(
            bounds.x,
            JSON.stringify({
              width,
              height,
              selector,
              bounds,
              scroll: await page
                .locator(".page-scroll")
                .evaluate((e) => [e.scrollLeft, e.scrollTop]),
            }),
          ).toBeGreaterThanOrEqual(0);
          expect(bounds.x + bounds.width).toBeLessThanOrEqual(width + 1);
          if (selector !== ".draft-panel") {
            expect(bounds.y).toBeGreaterThanOrEqual(0);
            expect(bounds.y + bounds.height).toBeLessThanOrEqual(height + 1);
          }
        }
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        if (width === 1500)
          await page.screenshot({ path: "test-results/ui-home-1500x960.png" });
      }
      await cdp.send("Emulation.clearDeviceMetricsOverride");
    },
  );
  await check("history search and real retry", async () => {
    await page.getByRole("button", { name: "歷史紀錄", exact: true }).click();
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
    await page.getByRole("button", { name: "轉換檔案", exact: true }).click();
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
        page.getByRole("button", { name: "轉換檔案", exact: true }),
      ).toBeVisible();
      const controls = await page.locator(".conversion-toolbar").boundingBox();
      expect(controls.y + controls.height).toBeLessThanOrEqual(height + 1);
      await page.screenshot({ path: `test-results/layout-${scale * 100}.png` });
    }
    await cdp.send("Emulation.clearDeviceMetricsOverride");
  });
  const fixture = (name) => path.join(root, ".tools/ui-fixtures", name);
  const choose = async (names) => {
    await page.evaluate((paths) => {
      window.__fileConverterPickerFiles = paths;
    }, names.map(fixture));
  };
  const clearDrafts = async () => {
    await page
      .getByRole("button", { name: "清空待轉換檔案", exact: true })
      .click();
  };
  await check(
    "P0 navigation, scoped application icons and persistent sidebar collapse",
    async () => {
      await expect(
        page.getByRole("button", { name: "網址下載", exact: true }),
      ).toBeDisabled();
      await expect(
        page.getByRole("button", { name: "自動化工作流程", exact: true }),
      ).toBeDisabled();
      await expect(page.locator(".sidebar .app-icon")).toHaveJSProperty(
        "naturalWidth",
        32,
      );
      const originalCollapsed =
        (await rpc("snapshot")).settings.sidebarCollapsed || false;
      const collapse = page.getByRole("button", {
        name: "收合側邊欄",
        exact: true,
      });
      if (await collapse.count()) await collapse.click();
      await expect(page.locator(".app")).toHaveClass(/sidebar-collapsed/);
      await expect
        .poll(async () => (await rpc("snapshot")).settings.sidebarCollapsed)
        .toBe(true);
      await page.reload();
      await expect(page.locator(".app")).toHaveClass(/sidebar-collapsed/);
      await page
        .getByRole("button", { name: "展開側邊欄", exact: true })
        .click();
      await expect
        .poll(async () => (await rpc("snapshot")).settings.sidebarCollapsed)
        .toBe(false);
      expect(originalCollapsed === true || originalCollapsed === false).toBe(
        true,
      );
    },
  );
  await check(
    "P0 automatic mode starts unassigned and blocks meaningless PDF passthrough",
    async () => {
      await choose(["中文 alpha & 測試.png", "使用說明.pdf"]);
      await page.getByRole("button", { name: "加入檔案", exact: true }).click();
      await expect(page.locator(".draft-row")).toHaveCount(2);
      for (const select of await page.locator(".draft-row select").all())
        await expect(select).toHaveValue("");
      await expect(
        page.getByRole("button", { name: /開始轉換/ }),
      ).toBeDisabled();
      const infos = await rpc("inspect", {
        paths: [fixture("中文 alpha & 測試.png")],
      });
      expect(infos[0].detection.native.mime).toBe("image/png");
      const pdf = page.locator(".draft-row").filter({
        has: page.getByRole("button", { name: "使用說明.pdf", exact: true }),
      });
      const png = page.locator(".draft-row").filter({
        has: page.getByRole("button", {
          name: "中文 alpha & 測試.png",
          exact: true,
        }),
      });
      await png.locator("select").selectOption("webp");
      await pdf.locator("select").selectOption("pdf");
      await expect(pdf.locator(".error-text")).toContainText("設定頁碼");
      await expect(
        page.getByRole("button", { name: /開始轉換/ }),
      ).toBeDisabled();
      await pdf
        .getByRole("button", { name: "使用說明.pdf", exact: true })
        .click();
      await page
        .getByRole("combobox", { name: "順時針旋轉", exact: true })
        .selectOption("90");
      await expect(
        page.getByRole("button", { name: /開始轉換/ }),
      ).toBeEnabled();
      await clearDrafts();
    },
  );
  await check(
    "P0 specified mode detects mismatches and executes a real matching conversion",
    async () => {
      await page
        .getByRole("button", { name: "指定格式轉換", exact: true })
        .click();
      await page
        .getByRole("combobox", { name: "指定來源格式", exact: true })
        .selectOption("png");
      await page
        .getByRole("combobox", { name: "指定目標格式", exact: true })
        .selectOption("jpg");
      await choose(["中文 alpha & 測試.png", "產品圖片.jpg"]);
      await page.getByRole("button", { name: "加入檔案", exact: true }).click();
      await expect(page.locator(".draft-row")).toHaveCount(2);
      await expect(page.locator(".draft-row .error-text")).toContainText(
        "指定來源為 PNG",
      );
      await expect(
        page.getByRole("button", { name: /開始轉換/ }),
      ).toBeDisabled();
      await page
        .getByRole("checkbox", { name: "選擇 產品圖片.jpg", exact: true })
        .uncheck();
      const before = new Set((await rpc("snapshot")).jobs.map((j) => j.id));
      await page.getByRole("button", { name: /開始轉換/ }).click();
      await expect
        .poll(
          async () =>
            (await rpc("snapshot")).jobs
              .filter((j) => !before.has(j.id))
              .map((j) => j.status),
          { timeout: 30000 },
        )
        .toEqual(["completed"]);
      const created = (await rpc("snapshot")).jobs.find(
        (j) => !before.has(j.id),
      );
      expect(created.format).toBe("jpg");
      expect((await fs.stat(created.outputs[0])).size).toBeGreaterThan(50);
      await clearDrafts();
      await page
        .getByRole("combobox", { name: "指定來源格式", exact: true })
        .selectOption("pdf");
      const targets = await page
        .getByRole("combobox", { name: "指定目標格式", exact: true })
        .locator("option")
        .evaluateAll((nodes) => nodes.map((n) => n.value));
      expect(targets).not.toContain("docx");
      expect(targets).not.toContain("mp4");
      await page
        .getByRole("button", { name: "智慧自動辨識", exact: true })
        .click();
    },
  );
  await check(
    "P0 toolbox executes PDF splitting through the existing queue",
    async () => {
      await page.getByRole("button", { name: "工具箱", exact: true }).click();
      await expect(page.locator(".toolbox-tabs button")).toHaveCount(9);
      await choose(["使用說明.pdf"]);
      await page.getByRole("button", { name: /^分割 PDF/ }).click();
      await expect(
        page.getByRole("switch", { name: "逐頁分割 PDF", exact: true }),
      ).toBeChecked();
      const before = new Set((await rpc("snapshot")).jobs.map((j) => j.id));
      await page.getByRole("button", { name: /開始轉換/ }).click();
      await expect
        .poll(
          async () =>
            (await rpc("snapshot")).jobs
              .filter((j) => !before.has(j.id))
              .map((j) => j.status),
          { timeout: 30000 },
        )
        .toEqual(["completed"]);
      const job = (await rpc("snapshot")).jobs.find((j) => !before.has(j.id));
      expect(job.outputs.length).toBe(2);
      for (const file of job.outputs)
        expect((await fs.stat(file)).size).toBeGreaterThan(50);
    },
  );
  await check(
    "P0 toolbox phases and registry show real engine availability",
    async () => {
      await page.getByRole("button", { name: "工具箱", exact: true }).click();
      await expect(
        page.getByRole("button", { name: /PDF 轉 DOCX/ }),
      ).toBeDisabled();
      for (const category of [
        "壓縮工具",
        "電子書工具",
        "去浮水印／物件修復工具",
      ]) {
        await page.getByRole("button", { name: category, exact: true }).click();
        await expect(page.locator(".tool-card")).toBeDisabled();
        await expect(page.locator(".tool-card")).toContainText("P2");
      }
      await page
        .getByRole("button", { name: "轉換能力表", exact: true })
        .click();
      await page
        .getByRole("textbox", { name: "搜尋轉換能力", exact: true })
        .fill("docx");
      expect(
        await page.locator(".registry-panel tbody tr").count(),
      ).toBeGreaterThan(0);
      if (!snapshot.engines.soffice)
        await expect(
          page.locator(".registry-panel tbody").first(),
        ).toContainText("需要本機 LibreOffice");
      await page
        .getByRole("textbox", { name: "搜尋轉換能力", exact: true })
        .fill("");
      await page.getByRole("button", { name: "PDF工具", exact: true }).click();
      await page.waitForTimeout(350);
      await page.screenshot({ path: "test-results/p0-toolbox.png" });
    },
  );
  await check(
    "P0 populated workspace at desktop and DPI sizes, and About uses new branding",
    async () => {
      await page.getByRole("button", { name: "轉換檔案", exact: true }).click();
      await choose(["中文 alpha & 測試.png", "產品圖片.jpg", "使用說明.pdf"]);
      await page.getByRole("button", { name: "加入檔案", exact: true }).click();
      await expect(page.locator(".draft-row")).toHaveCount(3);
      const cdp = await context.newCDPSession(page);
      for (const scale of [1, 1.25, 1.5, 2]) {
        const width = scale === 1 ? 1500 : Math.floor(1920 / scale),
          height = scale === 1 ? 960 : Math.floor(1080 / scale);
        await cdp.send("Emulation.setDeviceMetricsOverride", {
          width,
          height,
          deviceScaleFactor: scale,
          mobile: false,
        });
        await page.waitForTimeout(220);
        expect(
          await page
            .locator(".draft-list")
            .evaluate((e) => e.scrollWidth <= e.clientWidth + 1),
        ).toBe(true);
        const toolbar = await page.locator(".conversion-toolbar").boundingBox();
        expect(toolbar.y + toolbar.height).toBeLessThanOrEqual(height + 1);
        if (scale === 1) {
          await page
            .locator(".toast-stack button")
            .click()
            .catch(() => {});
          await expect(page.locator(".activity-panel")).toHaveClass(
            /compact-activity/,
          );
          await page
            .getByRole("button", { name: "展開轉換進度", exact: true })
            .click();
          await expect(page.locator(".activity-list")).toBeVisible();
          await page
            .getByRole("button", { name: "收合轉換進度", exact: true })
            .click();
          await page.waitForTimeout(350);
          await page.screenshot({ path: "test-results/p0-home.png" });
        }
      }
      await cdp.send("Emulation.clearDeviceMetricsOverride");
      await page.getByRole("button", { name: "設定", exact: true }).click();
      await page
        .getByRole("button", { name: "關於 File Converter", exact: true })
        .click();
      await expect(page.locator(".about-card h2")).toHaveText("File Converter");
      await expect(page.locator(".about-card .app-icon")).toBeVisible();
      await expect(page.locator(".app")).not.toContainText(
        /RAI Converter|RAI Studio|關於 RAI/,
      );
      await page.waitForTimeout(350);
      await page.screenshot({ path: "test-results/p0-about.png" });
    },
  );
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
  const ownJobs = (await rpc("snapshot")).jobs.filter(
    (j) => !snapshot.jobs.some((old) => old.id === j.id),
  );
  await rpc("clear", { ids: ownJobs.map((j) => j.id) });
  if (originalBackground)
    await fs.writeFile(backgroundPath, originalBackground);
  else await fs.unlink(backgroundPath).catch(() => {});
  await page.reload();
  await browser.close();
}
