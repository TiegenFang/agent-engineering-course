import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const playwrightRoot = process.env.PLAYWRIGHT_MODULE_ROOT;
if (!playwrightRoot) {
  throw new Error("PLAYWRIGHT_MODULE_ROOT must point to the locally installed Playwright package");
}

const requireFromPlaywright = createRequire(path.join(playwrightRoot, "package.json"));
const { chromium } = requireFromPlaywright("playwright");

const baseUrl = process.env.T03_PREVIEW_URL || "http://127.0.0.1:4321/agent-engineering-course";
const outputDir = process.env.T03_SCREENSHOT_DIR || path.resolve("artifacts/t03-screenshots");
const directions = ["quiet-grid", "editorial-manual", "evidence-console"];
const results = [];

await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
  for (const direction of directions) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    const consoleErrors = [];
    const pageErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => pageErrors.push(error.message));

    const url = `${baseUrl}/t03/${direction}/`;
    await page.goto(url, { waitUntil: "networkidle" });
    await page.screenshot({
      path: path.join(outputDir, `${direction}-desktop.png`),
      fullPage: true,
    });
    const desktop = await page.evaluate(() => ({
      title: document.title,
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      main: Boolean(document.querySelector("main")),
      skipLabel: document.querySelector("a.skip-link")?.getAttribute("aria-label"),
    }));
    if (desktop.width > desktop.viewport + 1) {
      throw new Error(`${direction}: desktop horizontal overflow ${desktop.width}px > ${desktop.viewport}px`);
    }

    await page.keyboard.press("Tab");
    const focusedSkip = await page.evaluate(() => document.activeElement?.classList.contains("skip-link"));
    if (!focusedSkip) throw new Error(`${direction}: first Tab did not reach the skip link`);

    if (direction === "quiet-grid") {
      await page.locator("#expand-map").focus();
      await page.keyboard.press("Enter");
      const openCount = await page.locator(".map-list details[open]").count();
      if (openCount !== 8) throw new Error(`${direction}: expected 8 expanded map entries, got ${openCount}`);
    } else if (direction === "editorial-manual") {
      await page.locator('button[data-view-target="evidence-view"]').focus();
      await page.keyboard.press("Enter");
      const evidenceVisible = await page.locator("#evidence-view").isVisible();
      const layersHidden = await page.locator("#layers-view").evaluate((element) => element.hidden);
      if (!evidenceVisible || !layersHidden) throw new Error(`${direction}: evidence tab keyboard interaction failed`);
    } else {
      await page.locator('[data-layer-index="4"]').focus();
      await page.keyboard.press("Enter");
      const activeLayer = await page.locator('[data-layer-index="4"]').getAttribute("aria-selected");
      if (activeLayer !== "true") throw new Error(`${direction}: layer keyboard interaction failed`);
      await page.locator('[data-mode="verify"]').focus();
      await page.keyboard.press("Enter");
      const mode = await page.locator("body").getAttribute("data-mode");
      if (mode !== "verify") throw new Error(`${direction}: verify mode keyboard interaction failed`);
    }

    await page.close();

    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
    await mobile.emulateMedia({ reducedMotion: "reduce" });
    mobile.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(`mobile: ${message.text()}`);
    });
    mobile.on("pageerror", (error) => pageErrors.push(`mobile: ${error.message}`));
    await mobile.goto(url, { waitUntil: "networkidle" });
    await mobile.screenshot({
      path: path.join(outputDir, `${direction}-mobile.png`),
      fullPage: true,
    });
    const mobileLayout = await mobile.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      reducedMotionActive: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      reducedMotionRule: [...document.styleSheets].some((sheet) => {
        try {
          return [...sheet.cssRules].some((rule) => rule.cssText.includes("prefers-reduced-motion"));
        } catch {
          return false;
        }
      }),
    }));
    if (mobileLayout.width > mobileLayout.viewport + 1) {
      throw new Error(`${direction}: mobile horizontal overflow ${mobileLayout.width}px > ${mobileLayout.viewport}px`);
    }
    if (!mobileLayout.reducedMotionRule) {
      throw new Error(`${direction}: reduced-motion rule was not found in the loaded styles`);
    }
    if (!mobileLayout.reducedMotionActive) {
      throw new Error(`${direction}: browser did not activate reduced-motion emulation`);
    }
    if (consoleErrors.length || pageErrors.length) {
      throw new Error(`${direction}: browser errors: ${[...consoleErrors, ...pageErrors].join(" | ")}`);
    }
    results.push({ direction, desktop, mobile: mobileLayout, focusedSkip, consoleErrors, pageErrors });
    await mobile.close();
  }
} finally {
  await browser.close();
}

console.log(JSON.stringify({ outputDir, results }, null, 2));
