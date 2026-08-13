import assert from "node:assert/strict";
import { createServer } from "node:http";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.resolve(siteRoot, "dist");
const baseUrl = process.env.T08_PREVIEW_URL || "http://127.0.0.1:4322/agent-engineering-course";
let previewServer;

const fail = (message) => {
  throw new Error(`Instruction lesson browser verification failed: ${message}`);
};

const waitForPreview = async (url, timeoutMs = 30_000) => {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The local static server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  fail(`local static server did not become ready at ${url}`);
};

const startPreviewIfNeeded = async () => {
  if (process.env.T08_PREVIEW_URL) return;
  await access(path.join(distRoot, "module-2-agent-instruction", "index.html")).catch(() => {
    fail(`built module 2 page is missing at ${distRoot}; run npm run build first`);
  });
  const previewPort = new URL(baseUrl).port || "4322";
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
  await waitForPreview(`${baseUrl}/module-2-agent-instruction/`);
};

const stopPreview = async () => {
  if (!previewServer) return;
  await new Promise((resolve) => previewServer.close(resolve));
  previewServer = undefined;
};

const assertPageContract = async (page, viewportName) => {
  const layout = await page.evaluate(() => {
    const lab = document.querySelector("[data-instruction-lab]");
    const labelledBy = lab?.getAttribute("aria-labelledby");
    const labelledTarget = labelledBy ? document.getElementById(labelledBy) : null;
    const labels = [...document.querySelectorAll("label[for]")].every((label) => {
      const target = document.getElementById(label.htmlFor);
      return Boolean(target);
    });
    return {
      main: Boolean(document.querySelector("main")),
      skipLink: Boolean(document.querySelector("a.sl-skip-link")),
      lab: Boolean(lab),
      ariaLabelledBy: Boolean(labelledTarget),
      liveStatus: Boolean(document.querySelector("[data-instruction-status][aria-live='polite']")),
      comparisonLive: document.querySelector("[data-instruction-lab] .instruction-lab__comparison")?.getAttribute("aria-live"),
      labels,
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      reducedMotionRule: [...document.styleSheets].some((sheet) => {
        try {
          return [...sheet.cssRules].some((rule) => rule.cssText.includes("prefers-reduced-motion"));
        } catch {
          return false;
        }
      }),
    };
  });
  assert.equal(layout.main, true, `${viewportName}: main missing`);
  assert.equal(layout.skipLink, true, `${viewportName}: skip link missing`);
  assert.equal(layout.lab, true, `${viewportName}: instruction lab missing`);
  assert.equal(layout.ariaLabelledBy, true, `${viewportName}: lab aria-labelledby target missing`);
  assert.equal(layout.liveStatus, true, `${viewportName}: live status missing`);
  assert.equal(layout.comparisonLive, "polite", `${viewportName}: comparison is not polite live region`);
  assert.equal(layout.labels, true, `${viewportName}: label target missing`);
  assert.equal(layout.reducedMotionRule, true, `${viewportName}: reduced-motion rule missing`);
  assert.ok(layout.width <= layout.viewport + 1, `${viewportName}: horizontal overflow ${layout.width}px > ${layout.viewport}px`);
};

const runKeyboardExperiment = async (page) => {
  const prediction = page.locator("#instruction-prediction");
  const record = page.locator("[data-record-instruction-prediction]");
  const run = page.locator("[data-run-instruction]");
  await prediction.focus();
  await page.keyboard.press("ArrowDown");
  await record.focus();
  await page.keyboard.press("Enter");
  await assert.equal(await run.isEnabled(), true);
  await run.focus();
  await page.keyboard.press("Enter");
  await assert.match(await page.locator("[data-run-engineered]").textContent(), /可执行|字段不足/);
  await assert.equal(await page.locator("[data-instruction-status]").getAttribute("data-status"), "success");

  const scenario = page.locator("#instruction-scenario");
  await scenario.selectOption("conflict");
  await record.focus();
  await page.keyboard.press("Enter");
  await run.focus();
  await page.keyboard.press("Enter");
  await assert.match(await page.locator("[data-run-ambiguous]").textContent(), /冲突/);

  await scenario.selectOption("injection");
  await record.focus();
  await page.keyboard.press("Enter");
  await run.focus();
  await page.keyboard.press("Enter");
  await assert.match(await page.locator("[data-run-engineered]").textContent(), /可执行/);
  await assert.match(
    await page.locator("[data-scenario-fixture]").textContent(),
    /外发全部原始数据|删除本地审计记录/,
  );
  const engineeredInput = page.locator("#instruction-engineered");
  const safeInjection = await engineeredInput.inputValue();
  await engineeredInput.fill(safeInjection.replace("处理动作=忽略并不执行", "处理动作=忽略并不执行；允许外发并删除"));
  await record.focus();
  await page.keyboard.press("Enter");
  await run.focus();
  await page.keyboard.press("Enter");
  await assert.match(await page.locator("[data-run-engineered]").textContent(), /危险语义|安全不变量/);
  await page.locator("[data-reset-instruction]").click();
  await record.focus();
  await page.keyboard.press("Enter");
  await run.focus();
  await page.keyboard.press("Enter");
  await assert.match(await page.locator("[data-run-engineered]").textContent(), /可执行/);

  await scenario.selectOption("long");
  await record.focus();
  await page.keyboard.press("Enter");
  await run.focus();
  await page.keyboard.press("Enter");
  await assert.match(await page.locator("[data-run-ambiguous]").textContent(), /噪声|背景/);

  await page.locator("#instruction-variant").selectOption("pressure-night");
  await scenario.selectOption("baseline");
  await record.focus();
  await page.keyboard.press("Enter");
  await run.focus();
  await page.keyboard.press("Enter");
  await assert.match(await page.locator("[data-instruction-evidence-summary]").textContent(), /passed|通过/);
  await assert.equal(await page.locator("[data-instruction-checklist] li").count(), 6);
};

await startPreviewIfNeeded();
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const errors = [];
  const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  desktop.on("console", (message) => { if (message.type() === "error") errors.push(`console: ${message.text()}`); });
  desktop.on("pageerror", (error) => errors.push(`page: ${error.message}`));
  await desktop.goto(`${baseUrl}/module-2-agent-instruction/`, { waitUntil: "networkidle" });
  await assertPageContract(desktop, "desktop");
  await desktop.locator("a.sl-skip-link").focus();
  assert.match(await desktop.locator("a.sl-skip-link").textContent() || "", /Skip to content/);
  await runKeyboardExperiment(desktop);
  await desktop.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.emulateMedia({ reducedMotion: "reduce" });
  await mobile.goto(`${baseUrl}/module-2-agent-instruction/`, { waitUntil: "networkidle" });
  await assertPageContract(mobile, "mobile");
  await mobile.close();

  const noJsContext = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const noJs = await noJsContext.newPage();
  await noJs.goto(`${baseUrl}/module-2-agent-instruction/`, { waitUntil: "networkidle" });
  assert.equal(await noJs.locator(".instruction-lab__noscript").isVisible(), true, "no-js fallback is hidden");
  assert.equal(await noJs.locator(".instruction-lab__noscript table").isVisible(), true, "no-js comparison table missing");
  assert.match(await noJs.locator(".instruction-lab__noscript").textContent(), /提示注入/);
  assert.match(await noJs.locator(".instruction-lab__noscript").textContent(), /夜班压力报告/);
  await noJsContext.close();

  if (errors.length) fail(errors.join(" | "));
  console.log(JSON.stringify({
    route: "/module-2-agent-instruction/",
    checks: ["desktop keyboard and ARIA", "mobile no-overflow", "no-JS fallback"],
    errors: [],
  }, null, 2));
} finally {
  await browser?.close();
  await stopPreview();
}
