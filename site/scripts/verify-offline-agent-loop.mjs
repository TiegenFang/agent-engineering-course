import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.T26_PREVIEW_URL;
const baseUrl = previewOverride || "http://127.0.0.1:4324/agent-engineering-course";
const routeUrl = `${baseUrl}/module-11-agent-loop/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-11-agent-loop", "index.html"));
  if (previewOverride) return;
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
    previewServer.listen(Number(new URL(baseUrl).port || 4324), "127.0.0.1", resolve);
  });
};

const stopPreview = async () => {
  if (!previewServer) return;
  await new Promise((resolve) => previewServer.close(resolve));
  previewServer = undefined;
};

const assertPageText = async (page, text) => {
  assert.match(await page.locator("body").textContent(), new RegExp(text));
};

const assertNoJavaScript = async (browser) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(routeUrl, { waitUntil: "networkidle" });
  assert.equal(await page.locator("[data-offline-agent-loop]").count(), 1);
  assert.equal(await page.locator("[data-offline-agent-loop]").isVisible(), true);
  await assertPageText(page, "本页的控制流图是静态 HTML");
  await assertPageText(page, "不连接真实模型");
  await context.close();
};

const assertRoute = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });

  const root = page.locator("[data-offline-agent-loop]");
  assert.equal(await root.count(), 1);
  assert.equal(await page.locator("#offline-agent-loop-title").count(), 1);
  assert.equal(await root.getAttribute("aria-labelledby"), "offline-agent-loop-title");
  assert.equal(await page.locator("ol[data-offline-trace]").count(), 1);
  assert.equal(await page.locator("[data-offline-trace] [data-event-kind='response']").count(), 1);
  assert.equal(await page.locator("[data-offline-trace] [data-event-kind='tool_call']").count(), 1);
  assert.equal(await page.locator("[data-offline-trace] [data-event-kind='state_refill']").count(), 1);
  assert.equal(await page.locator("[data-offline-scenarios] tbody tr").count(), 5);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);
  assert.equal(await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches), true);
  await assertPageText(page, "t26-offline-agent-loop");
  await assertPageText(page, "Coding Agent");
  assert.deepEqual(pageErrors, []);
  await context.close();
};

try {
  await serveDist();
  const browser = await chromium.launch({ headless: true });
  try {
    await assertNoJavaScript(browser);
    await assertRoute(browser, { width: 1440, height: 900 });
    await assertRoute(browser, { width: 390, height: 844 });
  } finally {
    await browser.close();
  }
  console.log("T26 offline Agent loop public route browser contract passed");
} finally {
  await stopPreview();
}
