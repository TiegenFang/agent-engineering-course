/**
 * Playwright contract for the rendered T28 page.
 *
 * The surrounding browser runner supplies COURSE_SITE_URL after building and
 * serving the static site.  This script never contacts Anthropic.
 */

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { chromium } from "playwright";

const baseUrl = process.env.COURSE_SITE_URL ?? "http://127.0.0.1:4321";
const pageUrl = new URL("/module-11-anthropic-messages/", baseUrl).toString();
const orderedCases = [
  "offline-success",
  "invalid-arguments",
  "malformed-structured-output",
  "transport-error",
  "authentication-error",
];

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

async function expectVisible(page, selector) {
  const locator = page.locator(selector);
  await locator.waitFor({ state: "visible" });
  assert.equal(await locator.isVisible(), true, `${selector} should be visible`);
}
