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
    // W1：预测作答 + 跑道跑一圈 + 知识检查全对后，完成判定三项齐活并落盘
    const w1 = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await w1.goto(`${baseUrl}/start-1-what-is-agent/`);
    await w1.waitForSelector("[data-start-quiz]");
    const questionCount = await w1.locator("[data-quiz-questions] fieldset").count();
    assert.equal(questionCount, 3, "W1 应渲染 3 道知识检查题");
    // 预测题：两题各选一项后提交（对错不设门槛，但必须作答）
    const predictCount = await w1.locator("[data-predict-questions] fieldset").count();
    assert.equal(predictCount, 2, "W1 应有 2 道跑前预测题");
    for (let i = 0; i < predictCount; i += 1) {
      await w1.locator("[data-predict-questions] fieldset").nth(i).locator("input").first().check();
    }
    await w1.click("[data-predict-submit]");
    await w1.waitForFunction(() =>
      document.querySelector("[data-predict-result]")?.textContent?.includes("跑道已解锁"),
    );
    // 跑道：点击推进，完整到达全部四站（1→2→3→4）
    for (let i = 0; i < 4; i += 1) {
      await w1.click("[data-track-next]");
    }
    await w1.waitForFunction(() =>
      document.querySelector("[data-track-status]")?.textContent?.includes("跑完一圈"),
    );
    // 知识检查：3 题全对后，三项完成条件满足
    const answers = ["1", "1", "1"];
    for (const [index, value] of answers.entries()) {
      await w1.locator(`[data-start-quiz] fieldset`).nth(index).locator(`input[value="${value}"]`).check();
    }
    await w1.click("[data-quiz-submit]");
    await w1.waitForFunction(() =>
      document.querySelector("[data-quiz-result]")?.textContent?.includes("全部正确"),
    );
    // 完成判定落盘：三项条件满足后 start-1 写入本地进度
    const stored = await w1.evaluate(() => localStorage.getItem("course-start-progress"));
    assert.match(stored ?? "", /"start-1":true/, "三项完成条件满足后应写入 start-1 完成记录");
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

    // W2：改写练习两轮自评后标记完成
    const w2 = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await w2.goto(`${baseUrl}/start-2-dialogue-basics/`);
    await w2.waitForSelector("[data-dialogue-rewrite]");
    const rewriteCount = await w2.locator("[data-dialogue-rewrite] textarea").count();
    assert.equal(rewriteCount, 2, "W2 应有 2 轮改写输入");
    for (let i = 0; i < rewriteCount; i += 1) {
      await w2.locator("[data-dialogue-rewrite] textarea").nth(i).fill("目标：整理摘要。上下文：三台温度传感器 CSV。约束：不推测故障。验收：数字与原始记录一致。");
      await w2.locator("[data-dialogue-reveal]").nth(i).click();
    }
    const checkCount = await w2.locator("[data-dialogue-check]").count();
    for (let i = 0; i < checkCount; i += 1) {
      await w2.locator("[data-dialogue-check]").nth(i).check();
    }
    await w2.waitForFunction(() =>
      document.querySelector("[data-dialogue-result]")?.textContent?.includes("标记为完成"),
    );
    await w2.close();

    // W4：全部勾选自评后出现起步章完成区
    const w4 = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await w4.goto(`${baseUrl}/start-4-web-to-terminal/`);
    await w4.waitForSelector("[data-terminal-bridge]");
    const bridgeChecks = await w4.locator("[data-bridge-check]").count();
    assert.ok(bridgeChecks >= 4, "W4 自评清单至少 4 项");
    for (let i = 0; i < bridgeChecks; i += 1) {
      await w4.locator("[data-bridge-check]").nth(i).check();
    }
    await w4.waitForFunction(() => {
      const done = document.querySelector("[data-bridge-done]");
      return !!done && done.textContent !== "" && !!(done.offsetParent || done.getClientRects().length);
    });
    await w4.close();

    // 首页：进度向导渲染且零网络
    const home = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const homeRequests = [];
    home.on("request", (request) => {
      const url = request.url();
      if (!url.startsWith(baseUrl)) homeRequests.push(url);
    });
    await home.goto(`${baseUrl}/`);
    await home.waitForSelector("[data-progress-wizard]");
    assert.ok(await home.locator("[data-progress-wizard]").isVisible());
    assert.equal(homeRequests.length, 0, "首页加载不得发出外部网络请求");
    await home.close();

    console.log("Start lessons browser verification passed: W1 predictions + loop track + quiz redo gate, offline BYO mode, case library, W2 rewrite, W4 bridge, progress wizard");
  } finally {
    await browser.close();
    await stopPreview();
  }
};

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
