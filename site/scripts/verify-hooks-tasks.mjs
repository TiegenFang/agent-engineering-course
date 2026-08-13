import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const baseUrl = "http://127.0.0.1:4324/agent-engineering-course";
const routeUrl = `${baseUrl}/module-10-hooks-tasks/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-10-hooks-tasks", "index.html"));
  const basePath = new URL(baseUrl).pathname.replace(/\/$/, "");
  previewServer = createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url || "/", "http://127.0.0.1");
      if (requestUrl.pathname !== basePath && !requestUrl.pathname.startsWith(`${basePath}/`)) {
        response.writeHead(404).end();
        return;
      }
      let relativePath = decodeURIComponent(requestUrl.pathname.slice(basePath.length) || "/");
      if (relativePath.endsWith("/")) relativePath += "index.html";
      const filePath = path.resolve(distRoot, `.${relativePath}`);
      if (!filePath.startsWith(`${distRoot}${path.sep}`)) {
        response.writeHead(403).end();
        return;
      }
      const body = await readFile(filePath);
      response.writeHead(200, { "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream" });
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise((resolve, reject) => {
    previewServer.once("error", reject);
    previewServer.listen(4324, "127.0.0.1", resolve);
  });
};

const stopPreview = async () => {
  if (!previewServer) return;
  await new Promise((resolve) => previewServer.close(resolve));
  previewServer = undefined;
};

const assertNoJavaScriptFallback = async (browser) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(routeUrl, { waitUntil: "networkidle" });
  const fallback = page.locator(".hooks-tasks-lab__noscript");
  assert.equal(await fallback.isVisible(), true, "T21 no-JS fallback should be visible");
  assert.match(await fallback.textContent(), /Hook/);
  assert.match(await fallback.textContent(), /Task\/Todo/);
  assert.match(await fallback.textContent(), /停止条件/);
  await context.close();
};

const assertJavaScriptRoute = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });

  const root = page.locator("[data-hooks-tasks]");
  assert.equal(await root.count(), 1);
  assert.equal(await root.getAttribute("aria-labelledby"), "hooks-tasks-title");
  assert.equal(await page.locator("#hooks-tasks-title").count(), 1);
  const scrollMetrics = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  if (viewport.width < 800) {
    assert.equal(scrollMetrics.scrollWidth <= scrollMetrics.innerWidth + 1, true, JSON.stringify(scrollMetrics));
  }

  const targets = await root.locator("button, input[type='number'], select").evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return { id: element.id, width: rect.width, height: rect.height };
    })
    .filter((target) => target.width > 0 && target.height > 0));
  assert.equal(targets.every((target) => target.width >= 44 && target.height >= 44), true, JSON.stringify(targets));

  await page.locator("[data-hooks-tasks-preset='safe']").click();
  assert.match(await page.locator("[data-hooks-tasks-status]").textContent(), /夹具运行完成/);
  assert.equal(await page.locator("[data-hooks-tasks-findings] [data-finding='deduplication']").count(), 1);
  assert.equal(await page.locator("[data-hooks-tasks-findings] [data-finding='permission']").count(), 1);
  assert.equal(await page.locator("[data-hooks-tasks-findings] [data-finding='failure-recovery']").count(), 1);
  assert.equal(await page.locator("[data-hooks-tasks-findings] [data-finding='side-effect-guard']").count(), 1);
  await page.locator("[data-hooks-tasks-record]").click();
  assert.match(await page.locator("[data-hooks-tasks-evidence-status]").textContent(), /7 \/ 7/);

  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-hooks-tasks-export]").click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), "t21-hooks-tasks-evidence.json");
  assert.match(await page.locator("[data-hooks-tasks-evidence-status]").textContent(), /匿名证据/);
  assert.match(await page.locator("[data-evidence-results]").textContent(), /t21-hooks-tasks/);

  await page.locator("[data-hooks-tasks-preset='failure']").click();
  assert.match(await page.locator("[data-hooks-tasks-status]").textContent(), /持续失败|停止/);
  assert.deepEqual(pageErrors, []);
  await context.close();
};

try {
  await serveDist();
  const browser = await chromium.launch({ headless: true });
  try {
    await assertNoJavaScriptFallback(browser);
    await assertJavaScriptRoute(browser, { width: 1440, height: 900 });
    await assertJavaScriptRoute(browser, { width: 390, height: 844 });
  } finally {
    await browser.close();
  }
  console.log("Hooks and Tasks public route browser contract passed");
} finally {
  await stopPreview();
}
