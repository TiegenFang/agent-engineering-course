import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.T14_PREVIEW_URL;
const baseUrl = previewOverride || "http://127.0.0.1:4323/agent-engineering-course";
const routeUrl = `${baseUrl}/module-5-context-budget/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-5-context-budget", "index.html"));
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
  const port = Number(new URL(baseUrl).port || 4323);
  await new Promise((resolve, reject) => {
    previewServer.once("error", reject);
    previewServer.listen(port, "127.0.0.1", resolve);
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
  const fallback = page.locator(".context-budget-lab__noscript");
  assert.equal(await fallback.isVisible(), true, "T14 no-JS fallback should be visible");
  assert.match(await fallback.textContent(), /上下文不足/);
  assert.match(await fallback.textContent(), /Memory/);
  await context.close();
};

const assertJavaScriptRoute = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });

  const root = page.locator("[data-context-budget]");
  assert.equal(await root.count(), 1);
  assert.equal(await page.locator("#context-budget-title").count(), 1);
  assert.equal(await root.getAttribute("aria-labelledby"), "context-budget-title");
  assert.equal(await page.locator("label[for='context-budget-capacity']").count(), 1);
  assert.equal(await page.locator("#context-budget-capacity").evaluate((element) => element.labels?.length ?? 0), 1);
  assert.equal(await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches), true);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);

  const targets = await root.locator("button, input[type='number'], select").evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return { tag: element.tagName, id: element.id, text: element.textContent?.trim(), width: rect.width, height: rect.height };
    })
    .filter((target) => target.width > 0 && target.height > 0));
  assert.equal(targets.every((target) => target.width >= 44 && target.height >= 44), true, JSON.stringify(targets));

  await page.locator("#context-budget-capacity").focus();
  assert.equal(await page.evaluate(() => document.activeElement?.id), "context-budget-capacity");
  await page.locator("#context-budget-prediction").selectOption("ready");
  await page.locator("[data-run-context-budget]").click();
  assert.match(await page.locator("[data-context-budget-status]").textContent(), /工作集可用/);
  assert.match(await page.locator("[data-context-budget-findings]").textContent(), /工作集可用/);

  await page.locator("[data-context-budget-preset='pollution']").click();
  await page.locator("#context-budget-prediction").selectOption("pollution");
  await page.locator("[data-run-context-budget]").click();
  assert.equal(await page.locator("[data-context-budget-findings] [data-finding='pollution']").count(), 1);
  await page.locator("[data-record-context-budget]").click();

  await page.locator("[data-context-budget-preset='insufficient']").click();
  assert.equal(await page.locator("[data-context-budget-findings] [data-finding='insufficient']").count(), 1);
  await page.locator("[data-record-context-budget]").click();

  await page.locator("[data-context-budget-preset='crowding']").click();
  assert.equal(await page.locator("[data-context-budget-findings] [data-finding='crowding']").count(), 1);
  await page.locator("[data-record-context-budget]").click();

  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-export-context-budget]").click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), "t14-context-budget-evidence.json");
  assert.match(await page.locator("[data-context-budget-evidence-status]").textContent(), /匿名证据/);
  assert.match(await page.locator("[data-evidence-results]").textContent(), /t14-context-budget/);
  assert.match(await page.locator("[data-context-budget-findings]").textContent(), /相关内容被挤占/);
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
  console.log("Context budget public route browser contract passed");
} finally {
  await stopPreview();
}
