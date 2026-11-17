import { defaults } from "../src/defaults.ts";
// Actual Tauri/WebView2/Rust/Python; only the OS picker return is supplied.
import { chromium, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs/promises";
let browser;
for (let attempt = 0; attempt < 40; attempt++) {
  try {
    browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
    break;
  } catch (e) {
    if (attempt === 39) throw e;
    await new Promise((r) => setTimeout(r, 500));
  }
}
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
    { timeout: 20000 },
  )
  .toBe(true);
const page = context
  .pages()
  .find(
    (p) =>
      p.url().includes("tauri.localhost") ||
      p.url().startsWith("http://127.0.0.1:1420"),
  );
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
const invoke = (command, args = {}) =>
  page.evaluate(
    ({ command, args }) => window.__TAURI_INTERNALS__.invoke(command, args),
    { command, args },
  );
const rpc = (method, args = {}) => invoke("engine_call", { method, args });
let ids = [];
const before = await rpc("snapshot");
const known = new Set(before.jobs.map((j) => j.id));
const outputDir = path.join(process.cwd(), ".tools/native-editor-output");
try {
  await rpc("settings", {
    settings: { ...before.settings, appearance: defaults.appearance },
  });
  await expect(page.getByText("準備就緒", { exact: true })).toBeVisible({
    timeout: 20000,
  });
  await page.addInitScript(() => {
    window.__pickerValues = [];
    const original = window.fetch.bind(window);
    window.fetch = (request, options) => {
      const value = decodeURIComponent(String(request));
      if (
        value.includes("plugin:dialog|open") ||
        value.includes("plugin:dialog|save")
      )
        return Promise.resolve(
          new Response(JSON.stringify(window.__pickerValues.shift() ?? null), {
            status: 200,
            headers: {
              "Content-Type": "application/json",
              "Tauri-Response": "ok",
            },
          }),
        );
      return original(request, options);
    };
  });
  await page.reload();
  await expect(page.getByText("準備就緒", { exact: true })).toBeVisible({
    timeout: 20000,
  });
  const pick = (files) =>
    page.evaluate((files) => window.__pickerValues.push(files), files);
  await page.getByRole("button", { name: "影片編輯器", exact: true }).click();
  await pick([
    path.join(process.cwd(), ".tools/editor-ui/red.mp4"),
    path.join(process.cwd(), ".tools/editor-ui/blue.mp4"),
  ]);
  await page.getByRole("button", { name: "匯入素材", exact: true }).click();
  await expect(page.locator(".video-editor .editor-clip")).toHaveCount(2, {
    timeout: 30000,
  });
  await expect(page.locator(".video-editor video")).toBeVisible({
    timeout: 30000,
  });
  await expect
    .poll(
      () => page.locator(".video-editor video").evaluate((v) => v.readyState),
      { timeout: 20000 },
    )
    .toBeGreaterThanOrEqual(2);
  await page
    .locator(".video-editor video")
    .evaluate(async (v) => await v.play());
  await expect
    .poll(() =>
      page.locator(".video-editor video").evaluate((v) => v.currentTime),
    )
    .toBeGreaterThan(0.1);
  await page.locator(".video-editor video").evaluate((v) => {v.pause();v.currentTime=1;v.dispatchEvent(new Event('timeupdate'))});
  await page.getByRole('button',{name:'分割',exact:true}).click();await expect(page.locator('.video-editor .editor-clip')).toHaveCount(3);
  await pick(outputDir);
  await page
    .getByRole("button", { name: "選擇輸出資料夾", exact: true })
    .click();
  await page.getByRole("button", { name: "輸出完整作品", exact: true }).click();
  let video;
  await expect
    .poll(
      async () => {
        const s = await rpc("snapshot");
        video = s.jobs.find((j) => !known.has(j.id) && j.kind === "fcvideo");
        return video?.status;
      },
      { timeout: 90000 },
    )
    .toBe("completed");
  ids.push(video.id);
  await page.getByRole("button", { name: "圖片編輯器", exact: true }).click();
  await pick([path.join(process.cwd(), ".tools/editor-ui/alpha.png")]);
  await page.getByRole("button", { name: "開啟圖片／加入圖層" }).click();
  await expect(page.locator(".image-layer-list .row")).toHaveCount(1);
  await expect(page.locator(".image-stage>img")).toBeVisible({
    timeout: 20000,
  });
  await expect
    .poll(() =>
      page.locator(".image-stage>img").evaluate((i) => i.naturalWidth),
    )
    .toBeGreaterThan(0);
  await pick(outputDir);
  await page
    .getByRole("button", { name: "選擇輸出資料夾", exact: true })
    .click();
  await page.getByRole("button", { name: "匯出圖片", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "加入轉檔佇列", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  let image = (await rpc("snapshot")).jobs.find(
    (j) => !known.has(j.id) && j.kind === "fcimage",
  );
  expect(image.status).toBe("completed");
  ids.push(image.id);
  await page.getByRole("button", { name: "加入轉檔佇列", exact: true }).click();
  await expect(page.locator(".draft-row")).toHaveCount(1);
  const converted = await rpc("enqueue", {
    jobs: [
      {
        sources: [image.outputs[0]],
        format: "webp",
        outputDir,
        options: { quality: 90 },
      },
    ],
  });
  ids.push(converted[0].id);
  await expect
    .poll(
      async () =>
        (await rpc("snapshot")).jobs.find((j) => j.id === converted[0].id)
          ?.status,
      { timeout: 30000 },
    )
    .toBe("completed");
  await page.getByRole("button", { name: "影片編輯器", exact: true }).click();
  await expect(page.locator(".video-editor .editor-clip")).toHaveCount(3, {
    timeout: 30000,
  });
  await expect(page.locator(".video-editor video")).toBeVisible();
  await page.locator(".page-scroll").evaluate((e) => (e.scrollTop = 0));
  await page.screenshot({
    path:
      process.env.FILE_CONVERTER_NATIVE_SCREENSHOT ||
      "test-results/native-editor.png",
  });
  const initial = await page.evaluate(() => [innerWidth, innerHeight]);
  await invoke("plugin:window|toggle_maximize", { label: "main" });
  await expect.poll(() => page.evaluate(() => innerWidth)).not.toBe(initial[0]);
  await invoke("plugin:window|toggle_maximize", { label: "main" });
  expect(errors).toEqual([]);
  const report = {
    version: JSON.parse(await fs.readFile("package.json", "utf8")).version,
    actualNativeIPC: true,
    actualAssetProtocol: true,
    actualMediaPlayback: true,
    windowMaximizeRestore: true,
    pipelines: [
      "video import→preview→export",
      "image import→preview→export→converter webp",
      "page state retained",
    ],
    engines: before.engines,
    outputs: [
      ...video.outputs,
      ...image.outputs,
      ...(await rpc("snapshot")).jobs.find((j) => j.id === converted[0].id)
        .outputs,
    ],
    userHistoryBefore: before.jobs.length,
    ownJobIds: ids,
  };
  await fs.writeFile(
    process.env.FILE_CONVERTER_NATIVE_REPORT ||
      "test-results/native-editors.json",
    JSON.stringify(report, null, 2),
  );
  console.log(
    "PASS actual native media asset/CSP, playback, editing pipelines, state, maximize/restore.",
  );
} catch (e) {
  console.error("PRIMARY NATIVE FAILURE", String(e));
  console.error(
    await page
      .locator("video")
      .evaluateAll((list) =>
        list.map((v) => ({
          src: v.currentSrc,
          error: v.error?.message,
          ready: v.readyState,
        })),
      )
      .catch(() => []),
  );
  console.error(
    await page
      .locator("body")
      .innerText()
      .catch(() => "<closed>"),
  );
  await page
    .screenshot({ path: "test-results/native-editor-failure.png" })
    .catch(() => {});
  throw e;
} finally {
  const after = await rpc("snapshot").catch(() => null);
  if (after) {
    const own = after.jobs
      .filter((j) => !known.has(j.id) && j.outputDir === outputDir)
      .map((j) => j.id);
    for (const id of own) {
      const job = after.jobs.find((j) => j.id === id);
      if (["running", "queued"].includes(job.status))
        await rpc("cancel", { id });
    }
    await rpc("clear", { ids: own });
  }
  await rpc("settings", { settings: before.settings }).catch(() => {});
  await invoke("shutdown_app").catch(() => {});
  await browser.close().catch(() => {});
}
