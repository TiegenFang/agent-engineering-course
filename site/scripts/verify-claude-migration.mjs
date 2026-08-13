import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const baseUrl = process.env.T10_PREVIEW_URL || "http://127.0.0.1:4324/agent-engineering-course";
const routeUrl = `${baseUrl}/module-3-claude-migration/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-3-claude-migration", "index.html"));
  if (process.env.T10_PREVIEW_URL) return;
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

const assertRoute = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });
  assert.ok(await page.locator("main h1").count() >= 1);
  assert.match(await page.locator("main h1").last().textContent(), /Claude Code.*迁移挑战/);
  assert.equal(await page.locator('[data-evidence-loop][data-lesson-id="t04-claude-migration"]').count(), 1);
  assert.equal(await page.locator('input[type="file"]').count(), 1);
  assert.equal(await page.locator("main").count(), 1);
  assert.equal(await page.locator("a.sl-skip-link").count(), 1);
  assert.equal(await page.locator('a[href="https://code.claude.com/docs/en/permissions"]').count(), 1);
  const layout = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
    reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  }));
  assert.equal(layout.reducedMotion, true);
  assert.ok(layout.width <= layout.viewport + 1, JSON.stringify(layout));
  assert.deepEqual(pageErrors, []);
  await context.close();
};

try {
  await serveDist();
  const browser = await chromium.launch({ headless: true });
  try {
    await assertRoute(browser, { width: 1280, height: 900 });
    await assertRoute(browser, { width: 390, height: 844 });
    const noJsContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const noJs = await noJsContext.newPage();
    await noJs.goto(routeUrl, { waitUntil: "networkidle" });
    assert.equal(await noJs.locator(".evidence-loop__noscript").isVisible(), true);
    assert.match(await noJs.locator(".evidence-loop__noscript").textContent(), /本地记录交互需要 JavaScript/);
    await noJsContext.close();
  } finally {
    await browser.close();
  }
  console.log("Claude migration public route browser contract passed");
} finally {
  await stopPreview();
}
