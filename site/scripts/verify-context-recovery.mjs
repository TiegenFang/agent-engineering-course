import assert from "node:assert/strict";
import { createServer } from "node:http";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.resolve(siteRoot, "dist");
const baseUrl = process.env.T15_PREVIEW_URL || "http://127.0.0.1:4323/agent-engineering-course";
const route = "/module-5-context-recovery/";
let previewServer;

const fail = (message) => {
  throw new Error(`Context recovery browser verification failed: ${message}`);
};

const waitForPreview = async (url, timeoutMs = 30_000) => {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Static server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  fail(`local static server did not become ready at ${url}`);
};

const startPreviewIfNeeded = async () => {
  if (process.env.T15_PREVIEW_URL) return;
  await access(path.join(distRoot, "module-5-context-recovery", "index.html")).catch(() => {
    fail(`built T15 page is missing at ${distRoot}; run npm run build first`);
  });
  const previewPort = new URL(baseUrl).port || "4323";
  const basePath = new URL(baseUrl).pathname.replace(/\/$/, "");
  const contentTypes = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
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
      if (request.method !== "HEAD") response.end(body);
      else response.end();
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise((resolve, reject) => {
    previewServer.once("error", reject);
    previewServer.listen(Number(previewPort), "127.0.0.1", resolve);
  });
  await waitForPreview(`${baseUrl}${route}`);
};

const stopPreview = async () => {
  if (!previewServer) return;
  await new Promise((resolve) => previewServer.close(resolve));
  previewServer = undefined;
};

const assertPageContract = async (page, viewportName) => {
  const layout = await page.evaluate(() => ({
    main: Boolean(document.querySelector("main")),
    skipLink: Boolean(document.querySelector("a.sl-skip-link")),
    lab: Boolean(document.querySelector("[data-context-recovery-lab]")),
    labelledBy: (() => {
      const lab = document.querySelector("[data-context-recovery-lab]");
      const id = lab?.getAttribute("aria-labelledby");
      return Boolean(id && document.getElementById(id));
    })(),
    liveStatus: Boolean(document.querySelector("[data-context-recovery-status][aria-live='polite']")),
    labels: [...document.querySelectorAll("label[for]")].every((label) => document.getElementById(label.htmlFor)),
    width: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
    reducedMotionRule: [...document.styleSheets].some((sheet) => {
      try {
        return [...sheet.cssRules].some((rule) => rule.cssText.includes("prefers-reduced-motion"));
      } catch {
        return false;
      }
    }),
  }));
  assert.equal(layout.main, true, `${viewportName}: main missing`);
  assert.equal(layout.skipLink, true, `${viewportName}: skip link missing`);
  assert.equal(layout.lab, true, `${viewportName}: context recovery lab missing`);
  assert.equal(layout.labelledBy, true, `${viewportName}: aria-labelledby target missing`);
  assert.equal(layout.liveStatus, true, `${viewportName}: live status missing`);
  assert.equal(layout.labels, true, `${viewportName}: label target missing`);
  assert.equal(layout.reducedMotionRule, true, `${viewportName}: reduced-motion rule missing`);
  assert.ok(layout.width <= layout.viewport + 1, `${viewportName}: horizontal overflow ${layout.width}px > ${layout.viewport}px`);
};

const recordAndRun = async (page, mode) => {
  await page.locator("#context-compression-mode").selectOption(mode);
  await page.locator("[data-context-record-prediction]").click();
  assert.equal(await page.locator("[data-context-run-compression]").isEnabled(), true);
  await page.locator("[data-context-run-compression]").click();
};

await startPreviewIfNeeded();
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const errors = [];
  const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  desktop.on("console", (message) => { if (message.type() === "error") errors.push(`console: ${message.text()}`); });
  desktop.on("pageerror", (error) => errors.push(`page: ${error.message}`));
  await desktop.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
  await assertPageContract(desktop, "desktop");
  await desktop.locator("a.sl-skip-link").focus();
  assert.match(await desktop.locator("a.sl-skip-link").textContent() || "", /Skip to content|跳转到内容|跳到主要内容/);

  await recordAndRun(desktop, "faithful");
  await recordAndRun(desktop, "distorted");
  await recordAndRun(desktop, "constraint-omitted");
  assert.equal(await desktop.locator("[data-context-comparison-list] article").count(), 3);
  assert.match(await desktop.locator("[data-context-comparison-list]").textContent(), /压缩失真|约束遗漏/);

  await desktop.locator("[data-context-run-polluted]").click();
  assert.match(await desktop.locator("[data-context-pollution-fixture]").textContent(), /不可信备注/);
  await desktop.locator("[data-context-recover-polluted]").click();
  assert.match(await desktop.locator("[data-context-pollution-fixture]").textContent(), /已恢复/);
  await desktop.locator("[data-context-generate-handoff]").click();
  assert.match(await desktop.locator("[data-context-handoff-fields]").textContent(), /ready-for-next-session/);
  assert.match(await desktop.locator("[data-context-handoff-json]").textContent(), /goal|next_steps/);
  assert.match(await desktop.locator("[data-context-evidence-status]").textContent(), /passed|通过/);
  await desktop.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.emulateMedia({ reducedMotion: "reduce" });
  await mobile.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
  await assertPageContract(mobile, "mobile");
  await mobile.close();

  const noJsContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const noJs = await noJsContext.newPage();
  await noJs.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
  assert.equal(await noJs.locator(".context-recovery-lab__noscript").isVisible(), true, "no-js fallback is hidden");
  assert.match(await noJs.locator(".context-recovery-lab__noscript").textContent(), /压缩失真/);
  assert.match(await noJs.locator(".context-recovery-lab__noscript").textContent(), /交接包/);
  await noJsContext.close();

  if (errors.length) fail(errors.join(" | "));
  console.log(JSON.stringify({
    route,
    checks: ["desktop keyboard and ARIA", "mobile no-overflow", "no-JS fallback", "compression/recovery/handoff journey"],
    errors: [],
  }, null, 2));
} finally {
  await browser?.close();
  await stopPreview();
}
