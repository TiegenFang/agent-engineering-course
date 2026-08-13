import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";

const siteRoot = fileURLToPath(new URL("..", import.meta.url));
const port = await new Promise((resolve, reject) => {
  const server = createServer();
  server.listen(0, "127.0.0.1", () => {
    const address = server.address();
    const value = typeof address === "object" && address ? address.port : 0;
    server.close(() => resolve(value));
  });
  server.on("error", reject);
});

const npmExecutable = process.platform === "win32" ? "npm.cmd" : "npm";
const preview = spawn(npmExecutable, ["run", "preview", "--", "--host", "127.0.0.1", "--port", String(port)], {
  cwd: siteRoot,
  shell: false,
  stdio: "ignore",
});
try {
  let ready = false;
  for (let attempt = 0; attempt < 30 && !ready; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/module-12-production/`);
      ready = response.ok;
      if (!ready) await new Promise((resolve) => setTimeout(resolve, 250));
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  if (!ready) throw new Error("T29 preview did not become ready");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(`http://127.0.0.1:${port}/module-12-production/`, { waitUntil: "networkidle" });
  await page.locator("[data-production-evaluation-lab]").scrollIntoViewIfNeeded();
  await page.locator("[data-production-run]").click();
  await page.locator("[data-production-result]").waitFor();
  const result = await page.locator("[data-production-result]").textContent();
  const live = await page.locator("[data-production-live]").textContent();
  if (result !== "passed" || !live?.includes("false")) throw new Error("T29 browser lab did not prove offline passed state");
  await page.screenshot({ path: "artifacts/t29-production-desktop.png", fullPage: true });
  await browser.close();
} finally {
  preview.kill();
}
