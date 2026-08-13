import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const baseUrl = process.env.T13_PREVIEW_URL || "http://127.0.0.1:4323/agent-engineering-course";
const routeUrl = `${baseUrl}/module-4-project-rules/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-4-project-rules", "index.html"));
  if (process.env.T13_PREVIEW_URL) return;
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
      response.writeHead(200, {
        "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream",
      });
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

try {
  await serveDist();
  const browser = await chromium.launch({ headless: true });
  try {
    const noJsContext = await browser.newContext({ javaScriptEnabled: false });
    const noJsPage = await noJsContext.newPage();
    await noJsPage.goto(routeUrl, { waitUntil: "networkidle" });
    const fallback = noJsPage.locator(".evidence-loop__noscript");
    assert.equal(await fallback.isVisible(), true);
    assert.match(await noJsPage.locator("body").textContent(), /AGENTS\.md/);
    assert.match(await noJsPage.locator("body").textContent(), /CLAUDE\.md/);
    assert.match(await noJsPage.locator("body").textContent(), /PowerShell 7/);
    await noJsContext.close();

    const context = await browser.newContext();
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(routeUrl, { waitUntil: "networkidle" });
    assert.equal(await page.locator("[data-evidence-loop]").count(), 1);
    assert.equal(await page.locator("[data-evidence-loop]").getAttribute("data-lesson-id"), "t04-project-rules");
    assert.equal(await page.locator("#evidence-file").evaluate((element) => element.labels?.length ?? 0), 1);
    await page.locator("#evidence-file").focus();
    assert.equal(await page.evaluate(() => document.activeElement?.id), "evidence-file");
    assert.deepEqual(errors, []);
    await context.close();
  } finally {
    await browser.close();
  }
  console.log("Project rules public route browser contract passed");
} finally {
  await stopPreview();
}
