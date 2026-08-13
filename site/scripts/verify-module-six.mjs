import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.resolve(siteRoot, "dist");
const baseUrl = process.env.T16_PREVIEW_URL || "http://127.0.0.1:4324/agent-engineering-course";
const routeUrl = `${baseUrl}/module-6-memory/`;
let previewServer;

const fail = (message) => {
  throw new Error(`Memory lesson browser verification failed: ${message}`);
};

const startPreviewIfNeeded = async () => {
  if (process.env.T16_PREVIEW_URL) return;
  await access(path.join(distRoot, "module-6-memory", "index.html")).catch(() => {
    fail(`built module 6 page is missing at ${distRoot}; run npm run build first`);
  });
  const basePath = new URL(baseUrl).pathname.replace(/\/$/, "");
  const contentTypes = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
  };
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

const assertPageContract = async (page, label) => {
  const details = await page.evaluate(() => ({
    main: Boolean(document.querySelector("main")),
    skipLink: Boolean(document.querySelector("a.sl-skip-link")),
    lab: Boolean(document.querySelector("[data-memory-lab]")),
    labelled: Boolean(document.getElementById(document.querySelector("[data-memory-lab]")?.getAttribute("aria-labelledby") || "")),
    live: Boolean(document.querySelector("[data-memory-status][aria-live='polite']")),
    labels: [...document.querySelectorAll("label[for]")].every((label) => Boolean(document.getElementById(label.htmlFor))),
    width: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
    reducedMotion: [...document.styleSheets].some((sheet) => {
      try { return [...sheet.cssRules].some((rule) => rule.cssText.includes("prefers-reduced-motion")); } catch { return false; }
    }),
  }));
  assert.equal(details.main, true, `${label}: main missing`);
  assert.equal(details.skipLink, true, `${label}: skip link missing`);
  assert.equal(details.lab, true, `${label}: Memory lab missing`);
  assert.equal(details.labelled, true, `${label}: aria-labelledby target missing`);
  assert.equal(details.live, true, `${label}: live status missing`);
  assert.equal(details.labels, true, `${label}: labels invalid`);
  assert.equal(details.reducedMotion, true, `${label}: reduced-motion rule missing`);
  assert.ok(details.width <= details.viewport + 1, `${label}: horizontal overflow`);
};

const runExperiment = async (page) => {
  const action = (name) => page.locator(`[data-memory-action='${name}']`);
  await action("design").focus();
  await page.keyboard.press("Enter");
  for (const name of ["write", "recall", "stale-update"]) {
    await action(name).click();
  }
  assert.match(await page.locator("[data-memory-observation]").textContent(), /更新完成/);
  await action("inject-pollution").click();
  assert.match(await page.locator("[data-memory-status]").textContent(), /不可信备注/);
  await action("pollution").click();
  assert.match(await page.locator("[data-memory-observation]").textContent(), /恢复完成/);
  await action("delete").click();
  assert.match(await page.locator("[data-memory-status]").textContent(), /实验完成/);
  assert.equal(await page.locator("[data-export-memory-evidence]").isEnabled(), true);
  assert.equal(await page.locator("[data-memory-checklist] li[data-status='passed']").count(), 13);
};

await startPreviewIfNeeded();
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const errors = [];
  const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  desktop.on("pageerror", (error) => errors.push(error.message));
  desktop.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await desktop.goto(routeUrl, { waitUntil: "networkidle" });
  await assertPageContract(desktop, "desktop");
  await runExperiment(desktop);
  assert.deepEqual(errors, []);
  await desktop.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.emulateMedia({ reducedMotion: "reduce" });
  await mobile.goto(routeUrl, { waitUntil: "networkidle" });
  await assertPageContract(mobile, "mobile");
  await mobile.close();

  const noJsContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const noJs = await noJsContext.newPage();
  await noJs.goto(routeUrl, { waitUntil: "networkidle" });
  assert.equal(await noJs.locator(".memory-lab__noscript").isVisible(), true);
  assert.match(await noJs.locator("body").textContent(), /不调用真实模型/);
  await noJsContext.close();
  console.log("Module 6 public route browser contract passed");
} finally {
  await browser?.close();
  await stopPreview();
}
