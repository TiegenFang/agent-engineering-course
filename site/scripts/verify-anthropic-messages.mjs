/**
 * Playwright contract for the rendered T28 page.
 *
 * The surrounding browser runner supplies COURSE_SITE_URL after building and
 * serving the static site.  This script never contacts Anthropic.
 */

import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.T28_PREVIEW_URL;
const baseUrl = previewOverride || "http://127.0.0.1:4326/agent-engineering-course";
const pageUrl = `${baseUrl}/module-11-anthropic-messages/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};
const orderedCases = [
  "offline-success",
  "invalid-arguments",
  "malformed-structured-output",
  "transport-error",
  "authentication-error",
];

let previewServer;
const serveDist = async () => {
  await access(path.join(distRoot, "module-11-anthropic-messages", "index.html"));
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
  const port = Number(new URL(baseUrl).port || 4326);
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
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, acceptDownloads: true });
    await page.goto(pageUrl, { waitUntil: "networkidle" });
    await expectVisible(page, "#anthropic-messages-title");
    await expectVisible(page, "[data-anthropic-messages-form]");
    await expectVisible(page, "[data-anthropic-messages-status]");

    const noHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
    assert.equal(noHorizontalOverflow, true, "the narrow rendered lab must not horizontally overflow");

    const firstPreset = page.locator('[data-anthropic-messages-preset="offline-success"]');
    await firstPreset.focus();
    assert.equal(await page.evaluate(() => document.activeElement?.getAttribute("data-anthropic-messages-preset")), "offline-success");

    for (const caseId of orderedCases) {
      await page.locator(`[data-anthropic-messages-preset="${caseId}"]`).click();
      await page.locator("[data-record-anthropic-messages]").click();
    }

    const evidenceButton = page.locator("[data-export-anthropic-messages]");
    assert.equal(await evidenceButton.isEnabled(), true);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      evidenceButton.click(),
    ]);
    const downloadPath = await download.path();
    assert.ok(downloadPath, "the lab should export a browser download");
    const evidence = JSON.parse(await readFile(downloadPath, "utf8"));
    assert.equal(evidence.lesson_id, "t28-anthropic-messages");
    assert.equal(evidence.experiment.network, "not-called");
    assert.equal(evidence.experiment.access, "not-required");
    assert.equal(evidence.experiment.live_smoke.status, "not-run");
    assert.equal(evidence.experiment.agent_sdk.status, "comparison-only-not-invoked");
    assert.equal(JSON.stringify(evidence).toLowerCase().includes("api_key"), false);
    assert.deepEqual(evidence.experiment.cases.map((item) => item.id), orderedCases);
    assert.ok(evidence.checks.every((check) => check.result === "passed"));
  } finally {
    await browser.close();
  }
} finally {
  await stopPreview();
}

async function expectVisible(page, selector) {
  const locator = page.locator(selector);
  await locator.waitFor({ state: "visible" });
  assert.equal(await locator.isVisible(), true, `${selector} should be visible`);
}
