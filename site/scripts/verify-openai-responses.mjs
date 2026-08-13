import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.T27_PREVIEW_URL;
const baseUrl = previewOverride || "http://127.0.0.1:4325/agent-engineering-course";
const routeUrl = `${baseUrl}/module-11-openai-responses/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-11-openai-responses", "index.html"));
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
  const port = Number(new URL(baseUrl).port || 4325);
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

const readDownload = async (download) => {
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
};

const assertNoJavaScriptFallback = async (browser) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(routeUrl, { waitUntil: "networkidle" });
  const fallback = page.locator(".openai-responses-lab .plugin-audit-lab__noscript");
  assert.equal(await fallback.isVisible(), true, "T27 no-JS boundary must remain readable");
  assert.match(await fallback.textContent(), /不会调用 OpenAI API/);
  assert.match(await fallback.textContent(), /未执行/);
  await context.close();
};

const assertJavaScriptRoute = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  const nonLocalRequests = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) nonLocalRequests.push(request.url());
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });

  const root = page.locator("[data-openai-responses]");
  assert.equal(await root.count(), 1);
  assert.equal(await page.locator("#openai-responses-title").count(), 1);
  assert.equal(await root.getAttribute("aria-labelledby"), "openai-responses-title");
  assert.equal(await page.locator("#openai-responses-case").evaluate((element) => element.labels?.length ?? 0), 1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);
  const targets = await root.locator("button, select").evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return { text: element.textContent?.trim(), width: rect.width, height: rect.height };
    })
    .filter((target) => target.width > 0 && target.height > 0));
  assert.equal(targets.every((target) => target.width >= 44 && target.height >= 44), true, JSON.stringify(targets));

  for (const caseId of ["offline-success", "invalid-arguments", "malformed-structured-output", "transport-error"]) {
    await page.locator(`[data-openai-responses-preset='${caseId}']`).click();
    await page.locator("[data-record-openai-responses]").click();
  }
  assert.match(await page.locator("[data-openai-responses-evidence]").textContent(), /4 \/ 4/);
  assert.match(await page.locator("[data-openai-responses-outcome]").textContent(), /transport-error-contained/);

  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-export-openai-responses]").click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), "t27-openai-responses-evidence.json");
  const evidence = JSON.parse(await readDownload(download));
  assert.equal(evidence.lesson_id, "t27-openai-responses");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.experiment.network, "not-called");
  assert.equal(evidence.experiment.access, "not-required");
  assert.equal(evidence.experiment.live_smoke.status, "not-run");
  assert.match(await page.locator("[data-evidence-results]").textContent(), /t27-openai-responses/);
  assert.deepEqual(nonLocalRequests, []);
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
  console.log("OpenAI Responses adapter public route browser contract passed");
} finally {
  await stopPreview();
}
