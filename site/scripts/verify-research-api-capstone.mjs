import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const distRoot = path.join(siteRoot, 'dist');
const route = '/agent-engineering-course/module-12-research-api-capstone/';
const contentTypes = { '.css': 'text/css; charset=utf-8', '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml' };
const server = createServer(async (request, response) => {
  try {
    const requestUrl = new URL(request.url || '/', 'http://127.0.0.1');
    if (!requestUrl.pathname.startsWith('/agent-engineering-course/')) return response.writeHead(404).end();
    let relative = requestUrl.pathname.replace('/agent-engineering-course', '') || '/';
    if (relative.endsWith('/')) relative += 'index.html';
    const filePath = path.resolve(distRoot, `.${relative}`);
    if (!filePath.startsWith(`${distRoot}${path.sep}`)) return response.writeHead(403).end();
    response.writeHead(200, { 'Content-Type': contentTypes[path.extname(filePath)] || 'application/octet-stream' });
    response.end(await readFile(filePath));
  } catch { response.writeHead(404).end(); }
});

let browser;
try {
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const address = server.address();
  assert.ok(address && typeof address !== 'string');
  browser = await chromium.launch({ headless: true });
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const page = await browser.newPage({ viewport });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${address.port}${route}`, { waitUntil: 'networkidle' });
    assert.match(await page.locator('body').textContent(), /科研进阶 API 结课/);
    await page.getByRole('button', { name: '运行离线步骤' }).click();
    assert.match(await page.locator('[data-research-api-summary]').textContent(), /10\/10/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log('Research API capstone browser verification passed for desktop and mobile paths');
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
