import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const workspaceRoot = path.resolve(siteRoot, "..");
const baseUrl = process.env.T03_PREVIEW_URL || "http://127.0.0.1:4321/agent-engineering-course";
const outputDir = process.env.T03_SCREENSHOT_DIR || path.resolve(workspaceRoot, "artifacts", "t03-screenshots");
const directions = ["index", "quiet-grid", "editorial-manual", "evidence-console"];
const viewports = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 390, height: 844 },
};
const results = [];
let previewServer;

const requireFromProject = createRequire(path.join(siteRoot, "package.json"));
const playwrightPackage = requireFromProject("playwright/package.json");

const fail = (message) => {
  throw new Error(`Design directions browser verification failed: ${message}`);
};

const waitForPreview = async (url, timeoutMs = 30_000) => {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The preview process is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  fail(`local static server did not become ready at ${url}`);
};

const startPreviewIfNeeded = async () => {
  if (process.env.T03_PREVIEW_URL) return;
  const distRoot = path.resolve(siteRoot, "dist");
  await access(path.join(distRoot, "t03", "index.html")).catch(() => fail(`built T03 pages are missing at ${distRoot}; run npm run build first`));
  const previewPort = new URL(baseUrl).port || "4321";
  const basePath = new URL(baseUrl).pathname.replace(/\/$/, "");
  const contentTypes = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".xml": "application/xml; charset=utf-8",
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
  await waitForPreview(`${baseUrl}/t03/`);
};

const stopPreview = async () => {
  if (!previewServer) return;
  await new Promise((resolve) => previewServer.close(resolve));
  previewServer = undefined;
};

const sha256 = async (filePath) => {
  const digest = createHash("sha256").update(await readFile(filePath)).digest("hex");
  return digest;
};

const assertCommonLayout = async (page, direction, viewportName) => {
  const layout = await page.evaluate(() => ({
    title: document.title,
    width: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
    main: Boolean(document.querySelector("main")),
    skipLabel: document.querySelector("a.skip-link")?.getAttribute("aria-label"),
    reducedMotionActive: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    reducedMotionRule: [...document.styleSheets].some((sheet) => {
      try {
        return [...sheet.cssRules].some((rule) => rule.cssText.includes("prefers-reduced-motion"));
      } catch {
        return false;
      }
    }),
  }));
  if (layout.width > layout.viewport + 1) fail(`${direction}/${viewportName}: horizontal overflow ${layout.width}px > ${layout.viewport}px`);
  if (!layout.main || layout.skipLabel !== "跳到主要内容") fail(`${direction}/${viewportName}: main/skip-link contract failed`);
  if (!layout.reducedMotionRule) fail(`${direction}/${viewportName}: reduced-motion rule missing`);
  if (viewportName === "mobile" && !layout.reducedMotionActive) fail(`${direction}/${viewportName}: reduced-motion emulation not active`);
  return layout;
};

const assertAccessibleStyles = async (page, direction) => {
  await page.keyboard.press("Tab");
  const result = await page.evaluate(() => {
    const parseRgb = (value) => {
      if (value.startsWith("#")) {
        const hex = value.slice(1);
        const expanded = hex.length === 3 ? hex.split("").map((channel) => channel + channel).join("") : hex;
        if (/^[0-9a-f]{6}$/i.test(expanded)) return [0, 2, 4].map((offset) => Number.parseInt(expanded.slice(offset, offset + 2), 16));
      }
      const match = value.match(/rgba?\(([^)]+)\)/);
      if (!match) return null;
      const channels = match[1].split(",").slice(0, 3).map((channel) => Number.parseFloat(channel.trim()));
      return channels.length === 3 && channels.every(Number.isFinite) ? channels : null;
    };
    const luminance = (value) => {
      const rgb = parseRgb(value);
      if (!rgb) return null;
      const channels = rgb.map((channel) => {
        const normalized = channel / 255;
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    };
    const contrast = (foreground, background) => {
      const fg = luminance(foreground);
      const bg = luminance(background);
      if (fg === null || bg === null) return null;
      return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
    };
    const bodyStyle = getComputedStyle(document.body);
    const bodyBackground = bodyStyle.backgroundColor;
    const normalSelector = document.body.classList.contains("editorial-page")
      ? ".article-label"
      : document.body.classList.contains("quiet-page")
        ? ".eyebrow"
        : document.body.classList.contains("console-page")
          ? ".console-kicker"
          : ".eyebrow";
    const normalElement = document.querySelector(normalSelector);
    const normalColor = normalElement ? getComputedStyle(normalElement).color : "";
    const focusTarget = document.activeElement?.matches("a[href], button, summary") ? document.activeElement : document.querySelector("button, a[href], summary");
    const focusStyle = focusTarget ? getComputedStyle(focusTarget) : null;
    const focusRule = [...document.styleSheets].flatMap((sheet) => {
      try { return [...sheet.cssRules]; } catch { return []; }
    }).find((rule) => rule.selectorText?.includes(":focus-visible") && rule.style?.outline);
    const focusColor = focusRule?.style?.outlineColor || focusStyle?.outlineColor || "";
    const focusBackground = focusTarget ? getComputedStyle(focusTarget.parentElement || document.body).backgroundColor : bodyBackground;
    const riskElement = document.querySelector(".risk-note p");
    const riskColor = riskElement ? getComputedStyle(riskElement).color : "";
    const riskBackground = riskElement ? getComputedStyle(riskElement.parentElement || document.body).backgroundColor : "";
    const targetDetails = [...document.querySelectorAll("a[href], button, summary")]
      .filter((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return !element.hidden && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
      })
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return { selector: element.getAttribute("data-layer-index") || element.textContent?.trim().slice(0, 32), width: rect.width, height: rect.height };
      });
    return {
      normalContrast: contrast(normalColor, bodyBackground),
      focusContrast: contrast(focusColor, focusBackground),
      focusContrastBody: contrast(focusColor, bodyBackground),
      riskContrast: riskElement ? contrast(riskColor, riskBackground) : null,
      under44: targetDetails.filter((target) => target.width < 44 || target.height < 44),
      normalSelector,
      normalColor,
      bodyBackground,
      focusColor,
      focusBackground,
      focusElement: focusTarget ? { tag: focusTarget.tagName, className: focusTarget.className, outlineStyle: focusStyle?.outlineStyle, outlineWidth: focusStyle?.outlineWidth } : null,
    };
  });
  if ((result.normalContrast ?? 0) < 4.5) fail(`${direction}: normal label contrast ${result.normalContrast} < 4.5 (${result.normalSelector})`);
  if ((result.focusContrast ?? 0) < 3 || (result.focusContrastBody ?? 0) < 3) fail(`${direction}: focus contrast is below 3 (${JSON.stringify(result)})`);
  if (result.riskContrast !== null && result.riskContrast < 4.5) fail(`${direction}: risk-note contrast ${result.riskContrast} < 4.5`);
  if (result.under44.length) fail(`${direction}: interactive targets below 44px ${JSON.stringify(result.under44)}`);
  return result;
};

const assertIndexInteraction = async (page, viewportName) => {
  const route = page.locator(".route").first();
  if (await route.count() !== 1) fail(`index/${viewportName}: expected direction route cards`);
  let focused = false;
  for (let index = 0; index < 12; index += 1) {
    await page.keyboard.press("Tab");
    focused = await page.evaluate(() => document.activeElement?.matches(".route") ?? false);
    if (focused) break;
  }
  if (!focused) fail(`index/${viewportName}: keyboard focus did not reach the first direction route`);

  const readRouteState = async () => page.evaluate(() => {
    const parseRgb = (value) => {
      const match = value.match(/rgba?\(([^)]+)\)/);
      if (!match) return null;
      const channels = match[1].split(",").slice(0, 3).map((channel) => Number.parseFloat(channel.trim()));
      return channels.length === 3 && channels.every(Number.isFinite) ? channels : null;
    };
    const luminance = (value) => {
      const rgb = parseRgb(value);
      if (!rgb) return null;
      const channels = rgb.map((channel) => {
        const normalized = channel / 255;
        return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    };
    const contrast = (foreground, background) => {
      const fg = luminance(foreground);
      const bg = luminance(background);
      if (fg === null || bg === null) return null;
      return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
    };
    const route = document.querySelector(".route");
    const label = route?.querySelector(".route-label");
    const routeStyle = route ? getComputedStyle(route) : null;
    const labelStyle = label ? getComputedStyle(label) : null;
    return {
      background: routeStyle?.backgroundColor || "",
      color: labelStyle?.color || "",
      contrast: routeStyle && labelStyle ? contrast(labelStyle.color, routeStyle.backgroundColor) : null,
      focusVisible: route?.matches(":focus-visible") ?? false,
    };
  });

  await route.hover();
  const hoverState = await readRouteState();
  if ((hoverState.contrast ?? 0) < 4.5) fail(`index/${viewportName}: route hover contrast ${hoverState.contrast} < 4.5`);
  await page.mouse.move(0, 0);
  const focusState = await readRouteState();
  if (!focusState.focusVisible) fail(`index/${viewportName}: route keyboard focus is not focus-visible`);
  if ((focusState.contrast ?? 0) < 4.5) fail(`index/${viewportName}: route focus contrast ${focusState.contrast} < 4.5`);
  return { hover: hoverState, focus: focusState };
};

const assertQuietInteraction = async (page) => {
  await page.locator("#expand-map").focus();
  await page.keyboard.press("Enter");
  const openCount = await page.locator(".map-list details[open]").count();
  if (openCount !== 8) fail(`quiet-grid: expected 8 expanded map entries, got ${openCount}`);
};

const assertEditorialInteraction = async (page) => {
  const tabs = page.locator('[role="tab"]');
  if (await tabs.count() !== 2) fail("editorial-manual: expected two tabs");
  await tabs.nth(0).focus();
  await page.keyboard.press("ArrowRight");
  if (await tabs.nth(1).getAttribute("aria-selected") !== "true") fail("editorial-manual: ArrowRight did not select second tab");
  if (await tabs.nth(1).getAttribute("tabindex") !== "0") fail("editorial-manual: roving tabindex did not move to second tab");
  await page.keyboard.press("End");
  await page.keyboard.press("Home");
  if (await tabs.nth(0).getAttribute("aria-selected") !== "true") fail("editorial-manual: Home did not return to first tab");
  const panels = page.locator('[role="tabpanel"]');
  for (let index = 0; index < await panels.count(); index += 1) {
    const panel = panels.nth(index);
    const labelledBy = await panel.getAttribute("aria-labelledby");
    if (!labelledBy || !(await page.locator(`#${labelledBy}`).count())) fail(`editorial-manual: panel ${index} lacks aria-labelledby target`);
  }
};

const assertEvidenceInteraction = async (page) => {
  const options = page.locator('[role="option"]');
  if (await options.count() !== 8) fail("evidence-console: expected eight listbox options");
  await options.nth(0).focus();
  await page.keyboard.press("ArrowDown");
  if (await options.nth(1).getAttribute("aria-selected") !== "true") fail("evidence-console: ArrowDown did not select second option");
  await page.keyboard.press("End");
  if (await options.nth(7).getAttribute("aria-selected") !== "true") fail("evidence-console: End did not select last option");
  await page.keyboard.press("Home");
  if (await options.nth(0).getAttribute("aria-selected") !== "true") fail("evidence-console: Home did not select first option");
  await page.locator('[data-layer-index="4"]').click();
  await page.locator('[data-mode="verify"]').focus();
  await page.keyboard.press("Enter");
  if (await page.locator("body").getAttribute("data-mode") !== "verify") fail("evidence-console: verify mode keyboard interaction failed");
};

const runDirection = async (browser, direction) => {
  const routePath = direction === "index" ? "t03" : `t03/${direction}`;
  const screenshotPrefix = direction === "index" ? "t03-index" : direction;
  const url = `${baseUrl}/${routePath}/`;
  const consoleErrors = [];
  const pageErrors = [];
  const desktop = await browser.newPage({ viewport: viewports.desktop, deviceScaleFactor: 1 });
  desktop.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  desktop.on("pageerror", (error) => pageErrors.push(error.message));
  await desktop.goto(url, { waitUntil: "networkidle" });
  const desktopLayout = await assertCommonLayout(desktop, direction, "desktop");
  const desktopStyles = await assertAccessibleStyles(desktop, direction);
  await desktop.reload({ waitUntil: "networkidle" });
  const desktopScreenshot = path.join(outputDir, `${screenshotPrefix}-desktop.png`);
  await desktop.screenshot({ path: desktopScreenshot, fullPage: true });
  await desktop.keyboard.press("Tab");
  if (!(await desktop.evaluate(() => document.activeElement?.classList.contains("skip-link")))) fail(`${direction}/desktop: first Tab did not reach skip link`);
  let desktopInteraction = null;
  if (direction === "index") desktopInteraction = await assertIndexInteraction(desktop, "desktop");
  if (direction === "quiet-grid") await assertQuietInteraction(desktop);
  if (direction === "editorial-manual") await assertEditorialInteraction(desktop);
  if (direction === "evidence-console") await assertEvidenceInteraction(desktop);
  await desktop.close();

  const mobile = await browser.newPage({ viewport: viewports.mobile, deviceScaleFactor: 1 });
  await mobile.emulateMedia({ reducedMotion: "reduce" });
  mobile.on("console", (message) => { if (message.type() === "error") consoleErrors.push(`mobile: ${message.text()}`); });
  mobile.on("pageerror", (error) => pageErrors.push(`mobile: ${error.message}`));
  await mobile.goto(url, { waitUntil: "networkidle" });
  const mobileLayout = await assertCommonLayout(mobile, direction, "mobile");
  const mobileStyles = await assertAccessibleStyles(mobile, direction);
  await mobile.reload({ waitUntil: "networkidle" });
  const mobileScreenshot = path.join(outputDir, `${screenshotPrefix}-mobile.png`);
  await mobile.screenshot({ path: mobileScreenshot, fullPage: true });
  let mobileInteraction = null;
  if (direction === "index") mobileInteraction = await assertIndexInteraction(mobile, "mobile");
  if (direction === "evidence-console") {
    if (await mobile.locator("#layer-listbox").getAttribute("aria-orientation") !== "horizontal") fail("evidence-console/mobile: listbox orientation was not updated");
    await mobile.locator('[data-layer-index="0"]').focus();
    await mobile.keyboard.press("ArrowRight");
    if (await mobile.locator('[data-layer-index="1"]').getAttribute("aria-selected") !== "true") fail("evidence-console/mobile: ArrowRight did not select second option");
  }
  await mobile.close();
  if (consoleErrors.length || pageErrors.length) fail(`${direction}: browser errors ${[...consoleErrors, ...pageErrors].join(" | ")}`);
  return {
    direction,
    desktop: { ...desktopLayout, styles: desktopStyles, interaction: desktopInteraction, screenshot: path.basename(desktopScreenshot), sha256: await sha256(desktopScreenshot) },
    mobile: { ...mobileLayout, styles: mobileStyles, interaction: mobileInteraction, screenshot: path.basename(mobileScreenshot), sha256: await sha256(mobileScreenshot) },
    consoleErrors,
    pageErrors,
  };
};

await mkdir(outputDir, { recursive: true });
let browser;
try {
  await startPreviewIfNeeded();
  browser = await chromium.launch({ headless: true });
  for (const direction of directions) results.push(await runDirection(browser, direction));
  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    runtime: { node: process.version, playwright: playwrightPackage.version, browser: { name: "chromium", version: browser.version() } },
    preview: { baseUrl, managedByVerifier: !process.env.T03_PREVIEW_URL },
    viewports,
    directions: results,
  };
  await writeFile(path.join(outputDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(manifest, null, 2));
} finally {
  await browser?.close();
  await stopPreview();
}
