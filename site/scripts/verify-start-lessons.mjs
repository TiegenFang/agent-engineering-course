import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(scriptDirectory, "..");
const distRoot = path.join(siteRoot, "dist");
const previewOverride = process.env.V2_PREVIEW_URL;
const baseUrl = previewOverride || "http://127.0.0.1:4340/agent-engineering-course";
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

let previewServer;

const serveDist = async () => {
  await access(path.join(distRoot, "start-1-what-is-agent", "index.html"));
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
  const port = Number(new URL(baseUrl).port || 4340);
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

const run = async () => {
  await serveDist();
  const browser = await chromium.launch();

  try {
    // W1：知识检查全对后给出完成反馈
    const w1 = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await w1.goto(`${baseUrl}/start-1-what-is-agent/`);
    await w1.waitForSelector("[data-start-quiz]");
    const questionCount = await w1.locator("[data-quiz-questions] fieldset").count();
    assert.equal(questionCount, 3, "W1 应渲染 3 道知识检查题");
    const answers = ["1", "1", "1"];
    for (const [index, value] of answers.entries()) {
      await w1.locator(`[data-start-quiz] fieldset`).nth(index).locator(`input[value="${value}"]`).check();
    }
    await w1.click("[data-quiz-submit]");
    await w1.waitForFunction(() =>
      document.querySelector("[data-quiz-result]")?.textContent?.includes("全部正确"),
    );
    await w1.close();

    // W3：离线演示模式发送后返回本地预置回复，且页面零网络请求
    const w3 = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const externalRequests = [];
    w3.on("request", (request) => {
      const url = request.url();
      if (!url.startsWith(baseUrl)) externalRequests.push(url);
    });
    await w3.goto(`${baseUrl}/start-3-api-key-chat/`);
    await w3.waitForSelector("[data-byo-key-chat]");
    // 真实调用控件默认隐藏
    assert.ok(await w3.locator("[data-byo-live-controls]").isHidden(), "默认离线模式应隐藏密钥输入");
    await w3.click("[data-byo-send]");
    await w3.waitForFunction(() =>
      document.querySelector("[data-byo-reply]")?.textContent?.includes("离线演示回复"),
    );
    assert.equal(externalRequests.length, 0, "离线演示模式不得发出任何外部网络请求");
    // 切换到真实模式显示密钥输入与安全说明
    await w3.check('input[name="byo-mode"][value="live"]');
    assert.ok(await w3.locator("[data-byo-live-controls]").isVisible());
    assert.ok(await w3.locator("[data-byo-key]").isVisible());
    await w3.close();

    // 案例参考库渲染三组案例
    const cases = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await cases.goto(`${baseUrl}/case-library/`);
    await cases.waitForSelector("main");
    const bodyText = await cases.locator("main").innerText();
    assert.match(bodyText, /superpowers/);
    assert.match(bodyText, /mattpocock/);
    assert.match(bodyText, /anthropics\/skills/);
    await cases.close();

    console.log("Start lessons browser verification passed: quiz, offline BYO mode, case library");
  } finally {
    await browser.close();
    await stopPreview();
  }
};

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
