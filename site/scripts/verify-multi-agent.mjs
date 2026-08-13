import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.T22_PREVIEW_URL;
const baseUrl = previewOverride || "http://127.0.0.1:4325/agent-engineering-course";
const routeUrl = `${baseUrl}/module-10-multi-agent/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "module-10-multi-agent", "index.html"));
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
      response.writeHead(200, {
        "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream",
      });
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

  const fallback = page.locator(".plugin-audit-lab__noscript");
  assert.equal(await fallback.isVisible(), true, "T22 no-JS fallback should be visible");
  assert.match(await fallback.textContent(), /不采用多 Agent/);
  assert.match(await fallback.textContent(), /共享写入/);
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

  const root = page.locator("[data-multi-agent-lab]");
  assert.equal(await root.count(), 1);
  assert.equal(await root.getAttribute("aria-labelledby"), "multi-agent-lab-title");
  assert.equal(
    await page.locator("#multi-agent-scenario").evaluate((element) => element.labels?.length ?? 0),
    1,
  );
  assert.equal(
    await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches),
    true,
  );
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);

  const targets = await root.locator("button, select").evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return { label: element.textContent?.trim(), width: rect.width, height: rect.height };
    })
    .filter((target) => target.width > 0 && target.height > 0));
  assert.equal(
    targets.every((target) => target.width >= 44 && target.height >= 44),
    true,
    JSON.stringify(targets),
  );

  await page.locator("[data-multi-agent-preset='independent-review']").click();
  assert.match(await page.locator("[data-multi-agent-recommendation]").textContent(), /继续比较/);
  assert.equal(await page.locator("[data-multi-agent-metrics] tr").count(), 2);
  assert.equal(
    await page.locator("[data-multi-agent-boundaries] [data-boundary='input-validation']").count(),
    1,
  );
  await page.locator("[data-record-multi-agent]").click();

  await page.locator("[data-multi-agent-preset='overlap-conflict']").click();
  assert.match(await page.locator("[data-multi-agent-recommendation]").textContent(), /不采用多 Agent/);
  assert.equal(
    await page.locator("[data-multi-agent-conflict][data-conflict='shared-output-collision']").count(),
    1,
  );
  assert.match(await page.locator("[data-multi-agent-recovery]").textContent(), /repartition-and-revalidate/);
  await page.locator("[data-record-multi-agent]").click();

  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-export-multi-agent]").click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), "t22-multi-agent-evidence.json");

  const evidence = JSON.parse(await readDownload(download));
  assert.equal(evidence.lesson_id, "t22-multi-agent");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.anonymous, true);
  assert.equal(evidence.experiment.comparisons.length, 2);
  assert.equal(evidence.experiment.model_calls, 0);
  assert.equal(evidence.experiment.network_calls, 0);
  assert.equal("prompt" in evidence.experiment, false);
  assert.match(await page.locator("[data-multi-agent-evidence-status]").textContent(), /匿名 evidence/);
  assert.match(await page.locator("[data-evidence-results]").textContent(), /t22-multi-agent/);
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
  console.log("Multi-agent public route browser contract passed");
} finally {
  await stopPreview();
}
