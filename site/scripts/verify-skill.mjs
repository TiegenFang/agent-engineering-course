import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.T17_PREVIEW_URL;
const baseUrl = previewOverride || "http://127.0.0.1:4323/agent-engineering-course";
const routeUrl = `${baseUrl}/module-7-skill/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-7-skill", "index.html"));
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
  const fallback = page.locator(".skill-lab__noscript");
  assert.equal(await fallback.isVisible(), true, "T17 no-JS fallback should be visible");
  assert.match(await fallback.textContent(), /不可信输入/);
  assert.match(await fallback.textContent(), /SKILL\.md/);
  await context.close();
};

const assertJavaScriptRoute = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });

  const root = page.locator("[data-skill-lab]");
  assert.equal(await root.count(), 1);
  assert.equal(await page.locator("#skill-lab-title").count(), 1);
  assert.equal(await root.getAttribute("aria-labelledby"), "skill-lab-title");
  assert.equal(await page.locator("label[for='skill-scenario']").count(), 1);
  assert.equal(await page.locator("#skill-scenario").evaluate((element) => element.labels?.length ?? 0), 1);
  assert.equal(await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches), true);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);

  const targets = await root.locator("button, select").evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return { tag: element.tagName, id: element.id, text: element.textContent?.trim(), width: rect.width, height: rect.height };
    })
    .filter((target) => target.width > 0 && target.height > 0));
  assert.equal(targets.every((target) => target.width >= 44 && target.height >= 44), true, JSON.stringify(targets));

  await page.locator("#skill-scenario").focus();
  assert.equal(await page.evaluate(() => document.activeElement?.id), "skill-scenario");
  await page.locator("#skill-prediction").selectOption("ready");
  await page.locator("[data-run-skill]").click();
  assert.match(await page.locator("[data-skill-finding]").textContent(), /可交付/);
  await page.locator("[data-record-skill]").click();

  for (const scenario of ["missing-source", "conflicting-evidence", "untrusted-instruction"]) {
    await page.locator(`[data-skill-preset='${scenario}']`).click();
    assert.equal(await page.locator(`[data-skill-primary][data-finding]`).count(), 1);
    await page.locator("[data-record-skill]").click();
  }

  await page.locator("[data-test-skill-triggers]").click();
  assert.equal(await page.locator("[data-skill-trigger-list] [data-trigger]").count(), 4);
  assert.match(await page.locator("[data-skill-trigger-list]").textContent(), /通过/);

  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-export-skill]").click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), "t17-skill-evidence.json");
  assert.match(await page.locator("[data-skill-evidence-status]").textContent(), /匿名证据/);
  assert.match(await page.locator("[data-evidence-results]").textContent(), /t17-skill/);
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
  console.log("Skill public route browser contract passed");
} finally {
  await stopPreview();
}
