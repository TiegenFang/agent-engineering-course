import { chromium } from "playwright";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const basePath = "/agent-engineering-course";
const routePath = `${basePath}/module-12-production/`;
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

await access(path.join(distRoot, "module-12-production", "index.html"));
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
    response.end(body);
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
  if (!address || typeof address === "string") throw new Error("T29 static server did not expose a port");
  const pageUrl = `http://127.0.0.1:${address.port}${routePath}`;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.locator("[data-production-evaluation-lab]").scrollIntoViewIfNeeded();
  await page.locator("[data-production-run]").click();
  await page.locator("[data-production-result]").waitFor();
  const result = await page.locator("[data-production-result]").textContent();
  const live = await page.locator("[data-production-live]").textContent();
  if (result !== "passed" || !live?.includes("false")) throw new Error("T29 browser lab did not prove offline passed state");
  await page.screenshot({ path: "artifacts/t29-production-desktop.png", fullPage: true });
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
