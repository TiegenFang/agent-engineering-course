import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.T19_PREVIEW_URL;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;
let baseUrl = previewOverride;
let routeUrl;

const serveDist = async () => {
  await access(path.join(distRoot, "module-9-mcp-discovery", "index.html"));
  if (previewOverride) {
    routeUrl = `${baseUrl.replace(/\/$/, "")}/module-9-mcp-discovery/`;
    return;
  }

  const basePath = "/agent-engineering-course";
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
    previewServer.listen(0, "127.0.0.1", resolve);
  });
  const address = previewServer.address();
  assert.ok(address && typeof address === "object");
  baseUrl = `http://127.0.0.1:${address.port}${basePath}`;
  routeUrl = `${baseUrl}/module-9-mcp-discovery/`;
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
  const fallback = page.locator(".mcp-discovery-lab__noscript");
  assert.equal(await fallback.isVisible(), true, "T19 no-JS fallback should be visible");
  assert.match(await fallback.textContent(), /真实 MCP 实验/);
  assert.match(await page.locator("body").textContent(), /Host/);
  await context.close();
};

const assertJavaScriptRoute = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });

  const root = page.locator("[data-mcp-discovery-lab]");
  assert.equal(await root.count(), 1);
  assert.equal(await page.locator("#mcp-discovery-lab-title").count(), 1);
  assert.equal(await root.getAttribute("aria-labelledby"), "mcp-discovery-lab-title");
  assert.equal(await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches), true);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);

  const controls = await root.locator("button").evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return { text: element.textContent?.trim(), width: rect.width, height: rect.height };
    })
    .filter((target) => target.width > 0 && target.height > 0));
  assert.equal(controls.every((target) => target.width >= 44 && target.height >= 44), true, JSON.stringify(controls));

  await page.locator("[data-mcp-offline-run]").focus();
  assert.notEqual(
    await page.evaluate(() => document.activeElement?.getAttribute("data-mcp-offline-run")),
    null,
  );
  await page.locator("[data-mcp-offline-run]").click();
  assert.match(await page.locator("[data-mcp-offline-status]").textContent(), /partial/);
  assert.match(await page.locator("[data-mcp-offline-transport]").textContent(), /deterministic-in-memory/);
  assert.equal(await page.locator("[data-mcp-offline-output]").isVisible(), true);
  assert.match(await page.locator("[data-evidence-results]").textContent(), /t19-mcp-discovery/);

  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-mcp-offline-export]").click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), "t19-mcp-discovery-offline-evidence.json");
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
  console.log("MCP discovery public route browser contract passed");
} finally {
  await stopPreview();
}
