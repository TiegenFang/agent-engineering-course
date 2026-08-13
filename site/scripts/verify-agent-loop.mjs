import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const baseUrl = process.env.T07_PREVIEW_URL || "http://127.0.0.1:4322/agent-engineering-course";
const routeUrl = `${baseUrl}/module-1-agent-loop/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-1-agent-loop", "index.html"));
  if (process.env.T07_PREVIEW_URL) return;
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
  const port = Number(new URL(baseUrl).port || 4322);
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
  const agentFallback = page.locator(".agent-loop-lab__noscript");
  const evidenceFallback = page.locator(".evidence-loop__noscript");
  await assertVisible(agentFallback, "AgentLoop no-JS fallback");
  await assertVisible(evidenceFallback, "EvidenceLoop no-JS fallback");
  await assertText(agentFallback, "交互控件需要 JavaScript");
  await assertText(agentFallback, "工具错误路径（error）");
  await assertText(evidenceFallback, "本地记录交互需要 JavaScript");
  await context.close();
};

const assertVisible = async (locator, label) => {
  assert.equal(await locator.isVisible(), true, `${label} should be visible`);
};

const assertText = async (locator, text) => {
  await assertVisible(locator, `text container for ${text}`);
  assert.match(await locator.textContent(), new RegExp(text));
};

const assertJavaScriptRoute = async (browser) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(routeUrl, { waitUntil: "networkidle" });

  const agent = page.locator("[data-agent-loop]");
  const evidence = page.locator("[data-evidence-loop]");
  await assertVisible(agent, "AgentLoop route");
  await assertVisible(evidence, "EvidenceLoop route");
  assert.equal(await page.locator("#agent-loop-title").count(), 1);
  assert.equal(await agent.getAttribute("aria-labelledby"), "agent-loop-title");
  assert.equal(
    await page.locator("#agent-loop-prediction").evaluate((element) => element.labels?.length ?? 0),
    1,
  );
  assert.equal(await page.locator('label[for="agent-loop-prediction"]').count(), 1);
  assert.equal(await page.locator('label[for="agent-loop-max-steps"]').count(), 1);
  assert.equal(await page.locator('[role="status"]').count() >= 3, true);
  assert.equal(await page.locator("ol[data-loop-trace]").count(), 1);
  assert.equal(await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches), true);
  assert.equal(await page.locator("[data-advance-loop]").isDisabled(), true);

  await page.locator("#agent-loop-prediction").focus();
  assert.equal(await page.evaluate(() => document.activeElement?.id), "agent-loop-prediction");
  await page.locator("[data-record-prediction]").click();
  await page.locator("[data-advance-loop]").click();
  assert.match(await page.locator("[data-loop-progress]").textContent(), /已观察 1 \/ 6/);

  await page.locator("#agent-loop-max-steps").evaluate((element) => element.removeAttribute("max"));
  await page.locator("#agent-loop-max-steps").fill("99");
  await page.locator("[data-reset-loop]").click();
  await assertText(agent.locator("[data-loop-status]"), "无法开始实验");

  await page.locator("#agent-loop-max-steps").fill("2");
  await page.locator("#agent-loop-max-steps").evaluate((element) => element.setAttribute("max", "6"));
  await page.locator("[data-reset-loop]").click();
  for (const prediction of ["response", "tool-request", "stop"]) {
    await page.locator("#agent-loop-prediction").selectOption(prediction);
    await page.locator("[data-record-prediction]").click();
    await page.locator("[data-advance-loop]").click();
  }
  await assertText(agent.locator("[data-loop-evidence-status]"), "alternative");
  await page.locator("#agent-loop-max-steps").fill("6");
  await page.locator("#agent-loop-failure").selectOption("tool-error");
  await page.locator("[data-reset-loop]").click();
  for (const prediction of ["response", "tool-request", "tool-execution", "tool-result", "stop"]) {
    await page.locator("#agent-loop-prediction").selectOption(prediction);
    await page.locator("[data-record-prediction]").click();
    await page.locator("[data-advance-loop]").click();
  }
  const observation = await page.locator("[data-loop-observation]").textContent();
  assert.match(observation, /没有可用遥测读数/);
  assert.doesNotMatch(observation, /本次模拟观察：/);
  assert.deepEqual(pageErrors, []);
  await context.close();
};

try {
  await serveDist();
  const browser = await chromium.launch({ headless: true });
  try {
    await assertNoJavaScriptFallback(browser);
    await assertJavaScriptRoute(browser);
  } finally {
    await browser.close();
  }
  console.log("Agent loop public route browser contract passed");
} finally {
  await stopPreview();
}
