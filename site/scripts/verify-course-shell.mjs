import { createServer } from "node:http";
import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const distRoot = path.resolve(siteRoot, "dist");
const basePath = "/agent-engineering-course";
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".xml": "application/xml; charset=utf-8",
};

const fail = (message) => {
  throw new Error(`Course shell browser verification failed: ${message}`);
};

await access(path.join(distRoot, "index.html")).catch(() => fail(`built homepage is missing at ${distRoot}`));

const server = createServer(async (request, response) => {
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

let browser;
try {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") fail("local static server did not expose a port");
  const baseUrl = `http://127.0.0.1:${address.port}${basePath}`;
  browser = await chromium.launch({ headless: true });

  for (const viewport of [
    { name: "desktop", width: 1440, height: 900, reducedMotion: "no-preference" },
    { name: "mobile", width: 390, height: 844, reducedMotion: "reduce" },
  ]) {
    const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
    await page.emulateMedia({ reducedMotion: viewport.reducedMotion });
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") pageErrors.push(message.text());
    });
    await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });

    const layout = await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      mainCount: document.querySelectorAll("main").length,
      hasShell: Boolean(document.querySelector("[data-course-shell]")),
      hasSearch: Boolean(document.querySelector("site-search")),
      hasReducedMotionRule: [...document.styleSheets].some((sheet) => {
        try {
          return [...sheet.cssRules].some((rule) => rule.cssText.includes("prefers-reduced-motion"));
        } catch {
          return false;
        }
      }),
    }));
    if (layout.width > layout.viewport + 1) fail(`${viewport.name}: horizontal overflow ${layout.width}px > ${layout.viewport}px`);
    if (layout.mainCount !== 1 || !layout.hasShell || !layout.hasSearch) fail(`${viewport.name}: main/course shell/search contract failed (${JSON.stringify(layout)})`);
    if (!layout.hasReducedMotionRule) fail(`${viewport.name}: reduced-motion rule missing`);
    if (viewport.name === "mobile" && !await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches)) {
      fail("mobile: reduced-motion emulation is not active");
    }

    const requiredLinks = ["module-0-environment", "module-0-git-safety", "module-1-agent-loop"];
    for (const route of requiredLinks) {
      if (await page.locator(`a[href*="${route}"]`).count() === 0) fail(`${viewport.name}: missing learning-path link ${route}`);
    }

    const modeButtons = page.locator("[data-capability-map] [data-mode]");
    if (await modeButtons.count() !== 2) fail(`${viewport.name}: READ/VERIFY mode buttons missing`);
    await page.locator('[data-capability-map] [data-mode="verify"]').click();
    const verifyState = await page.locator("[data-capability-map]").evaluate((element) => ({
      mode: element.dataset.mode,
      pressed: element.querySelector('[data-mode="verify"]')?.getAttribute("aria-pressed"),
      verifyVisible: Boolean(element.querySelector(".layer-output-item.is-active .verify-copy")
        && getComputedStyle(element.querySelector(".layer-output-item.is-active .verify-copy")).display !== "none"),
    }));
    if (verifyState.mode !== "verify" || verifyState.pressed !== "true" || !verifyState.verifyVisible) {
      fail(`${viewport.name}: VERIFY mode did not expose evidence (${JSON.stringify(verifyState)})`);
    }

    const firstLayer = page.locator('[data-capability-map] [data-layer-index]').first();
    await firstLayer.focus();
    await page.keyboard.press(viewport.name === "mobile" ? "ArrowRight" : "ArrowDown");
    const selectedCount = await page.locator('[data-capability-map] [data-layer-index][aria-selected="true"]').count();
    if (selectedCount !== 1) fail(`${viewport.name}: capability layer keyboard selection is not roving`);

    await page.keyboard.press("Tab");
    const focusState = await page.evaluate(() => {
      const target = document.activeElement;
      if (!(target instanceof HTMLElement)) return { interactive: false, outline: "none" };
      const style = getComputedStyle(target);
      return { interactive: target.matches("a[href],button,input,select,summary"), outline: style.outlineStyle };
    });
    if (!focusState.interactive || focusState.outline === "none") fail(`${viewport.name}: visible keyboard focus is missing`);
    if (pageErrors.length > 0) fail(`${viewport.name}: browser errors ${pageErrors.join(" | ")}`);
    await page.close();
  }

  console.log("Course shell browser verification passed for desktop and mobile paths.");
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
