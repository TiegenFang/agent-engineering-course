import assert from "node:assert/strict";
import { access, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
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

    // W3：离线样例模式的请求之旅——推进全部帧后完成标记落盘，且页面零网络请求
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
    // 离线展示已记录样例（标注来源状态），不再是预制玩笑串
    const bannerText = await w3.locator("[data-byo-source-banner]").innerText();
    assert.match(bannerText, /已记录样例/);
    assert.match(bannerText, /待现场采集核验/);
    const replyText = await w3.locator("[data-byo-reply]").innerText();
    assert.ok(replyText.includes("模型"), "离线模式应展示样例回复正文");
    assert.ok(!replyText.includes("离线演示回复"), "预制玩笑串回复必须移除");
    // 分步推进全部 7 帧（学员点击驱动，非自动播放）
    const nextButton = w3.locator("[data-journey-next]");
    for (let i = 0; i < 12; i += 1) {
      if (await nextButton.isDisabled()) break;
      await nextButton.click();
    }
    await w3.waitForFunction(() =>
      document.querySelector("[data-byo-status]")?.textContent?.includes("样例旅程看完"),
    );
    // 看完真实样例即标记 start-3 完成（经共享进度模块落盘）
    const startProgress = await w3.evaluate(() => localStorage.getItem("course-start-progress"));
    assert.match(startProgress, /"start-3":true/);
    assert.equal(externalRequests.length, 0, "离线样例模式不得发出任何外部网络请求");
    // 切换到真实模式显示密钥输入；无密钥路径与账户侧栏在场
    await w3.check('input[name="byo-mode"][value="live"]');
    assert.ok(await w3.locator("[data-byo-live-controls]").isVisible());
    assert.ok(await w3.locator("[data-byo-key]").isVisible());
    assert.ok(await w3.locator("[data-byo-last-summary]").count() === 1);
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

    // W2：小剧场在场；热身配对全对解锁两轮，两轮四要素引用完成后标记完成
    const w2 = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await w2.goto(`${baseUrl}/start-2-dialogue-basics/`);
    await w2.waitForSelector("[data-dialogue-rewrite]");
    // 指令小剧场双分镜在场且可重放
    assert.equal(await w2.locator("[data-instruction-theater] [data-act]").count(), 2, "小剧场应有两幕");
    assert.ok(
      (await w2.locator("[data-instruction-theater] [data-theater-replay]").count()) >= 2,
      "两幕都应可重放",
    );
    // 热身未完成前两轮改写保持隐藏
    assert.ok(await w2.locator("[data-rounds]").isHidden(), "热身全对前不应显示两轮改写");
    for (const element of ["context", "acceptance", "goal", "constraint"]) {
      await w2.click(`[data-match-card="${element}"]`);
      await w2.click(`[data-slot-place="${element}"]`);
    }
    await w2.waitForFunction(() => {
      const warmup = document.querySelector("[data-warmup]");
      return !!warmup && warmup.dataset.warmupComplete === "1";
    });
    assert.ok(await w2.locator("[data-rounds]").isVisible(), "热身全对后应解锁两轮改写");
    // 两轮改写：写改写 → 生成句子条目 → 四要素各引用一句 → 显示 4/4
    const rewriteCount = await w2.locator("[data-dialogue-rewrite] textarea").count();
    assert.equal(rewriteCount, 2, "W2 应有 2 轮改写输入");
    const elementOrder = ["goal", "context", "constraint", "acceptance"];
    for (let i = 0; i < rewriteCount; i += 1) {
      const round = w2.locator("[data-dialogue-rewrite] fieldset.round").nth(i);
      await round.locator("textarea").fill(
        "目标：整理成一页摘要表。上下文：三台温度传感器过去 7 天的导出 CSV。约束：不改任何原始读数。验收：最高与最低读数和原始记录一致。",
      );
      await round.locator("[data-quote-split]").click();
      const sentenceCount = await round.locator("[data-sentence]").count();
      assert.ok(sentenceCount >= 4, "句子条目应至少覆盖四要素");
      for (const [index, element] of elementOrder.entries()) {
        await round.locator("[data-sentence]").nth(index).click();
        await round.locator(`[data-element-assign="${element}"]`).click();
      }
      await w2.waitForFunction(
        (roundIndex) =>
          document
            .querySelectorAll("[data-round-progress]")
            [roundIndex]?.textContent?.includes("4/4"),
        i,
      );
      await round.locator("[data-dialogue-reveal]").click();
    }
    await w2.waitForFunction(() =>
      document.querySelector("[data-dialogue-result]")?.textContent?.includes("标记为完成"),
    );
    await w2.close();

    // W4：分岔地图四键校验——先清空进度，只勾理解类条目断言不落盘；
    // 再预置 start-1/2/3 后断言脚印点亮、门打开、start-4 落盘、完成区出现
    const w4 = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await w4.goto(`${baseUrl}/start-4-web-to-terminal/`);
    await w4.waitForSelector("[data-terminal-bridge]");
    await w4.evaluate(() => localStorage.removeItem("course-start-progress"));
    await w4.click("[data-fork-refresh]");
    const understanding = w4.locator('[data-bridge-check][data-bridge-kind="understanding"]');
    const willingness = w4.locator('[data-bridge-check][data-bridge-kind="willingness"]');
    assert.equal(await understanding.count(), 3, "W4 理解类条目应为 3 项");
    assert.equal(await willingness.count(), 3, "W4 意愿类条目应为 3 项（不计入完成）");
    for (let i = 0; i < 3; i += 1) {
      await understanding.nth(i).check();
    }
    await w4.waitForFunction(() =>
      document.querySelector("[data-bridge-status]")?.textContent?.includes("还差"),
    );
    let w4Stored = await w4.evaluate(() => localStorage.getItem("course-start-progress"));
    assert.equal(w4Stored, null, "缺 W1–W3 完成钥匙时，勾选理解类条目不得落盘 start-4");
    // 预置 start-1 与 start-3（缺 W2）：明确提示缺哪课并附「先去完成 W2」跳转链接
    await w4.evaluate(() =>
      localStorage.setItem("course-start-progress", JSON.stringify({ "start-1": true, "start-3": true })),
    );
    await w4.click("[data-fork-refresh]");
    await w4.waitForFunction(() =>
      document.querySelector("[data-door-missing]")?.textContent?.includes("W2"),
    );
    assert.ok(
      (await w4.locator('[data-door-missing] a[href*="start-2"]').count()) >= 1,
      "缺 W2 时应提供「先去完成 W2」跳转链接",
    );
    w4Stored = await w4.evaluate(() => localStorage.getItem("course-start-progress"));
    assert.doesNotMatch(w4Stored ?? "", /"start-4"/, "仍缺 W2 钥匙时不得落盘 start-4");
    // 三键齐全：脚印全部点亮、终端之门打开、start-4 落盘、完成区可见
    await w4.evaluate(() =>
      localStorage.setItem(
        "course-start-progress",
        JSON.stringify({ "start-1": true, "start-2": true, "start-3": true }),
      ),
    );
    await w4.click("[data-fork-refresh]");
    await w4.waitForFunction(() =>
      document.querySelector("[data-door-state]")?.textContent?.includes("已打开"),
    );
    const footprintStates = await w4.locator("[data-footprint-state]").allTextContents();
    assert.equal(footprintStates.length, 3, "分岔地图应有 W1–W3 三枚脚印");
    assert.ok(footprintStates.every((text) => text.includes("已点亮")), "三键齐全后脚印应全部点亮");
    w4Stored = await w4.evaluate(() => localStorage.getItem("course-start-progress"));
    assert.match(w4Stored ?? "", /"start-4":true/, "四键齐全后应写入 start-4 完成记录");
    assert.ok(await w4.locator("[data-bridge-done]").isVisible(), "完成后应显示画风衔接完成区");
    await w4.close();

    // 首页：进度向导渲染且零网络；第 0 步包含起步章衔接语
    const home = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const homeRequests = [];
    home.on("request", (request) => {
      const url = request.url();
      if (!url.startsWith(baseUrl)) homeRequests.push(url);
    });
    await home.goto(`${baseUrl}/`);
    await home.waitForSelector("[data-progress-wizard]");
    assert.ok(await home.locator("[data-progress-wizard]").isVisible());
    const stepZeroText = await home.locator('[data-wizard-step="0"]').innerText();
    assert.match(stepZeroText, /W1–W4 网页端起步章/, "向导第 0 步应包含起步章衔接语");
    assert.match(stepZeroText, /先回首页完成起步章/);
    assert.equal(homeRequests.length, 0, "首页加载不得发出外部网络请求");
    await home.close();

    // 首页：统一「我的进度」视图——起步章面板与 EvidenceLoop 同区呈现；
    // 并走完导出 → 清空 → 导入 → 状态恢复的完整携带往返。
    // storage 事件断言需要两个标签页共享同一浏览器上下文（各自 newPage 会落入独立 context）。
    const progressContext = await browser.newContext();
    const progress = await progressContext.newPage();
    await progress.goto(`${baseUrl}/`);
    await progress.waitForSelector("[data-start-progress-panel]");
    await progress.waitForSelector("[data-evidence-loop]");
    // 未开始：四课未完成 + 「从 W1 开始」引导可见
    assert.equal(
      await progress.locator("[data-start-state][data-state='todo']").count(),
      4,
      "空进度时四课应全部显示未完成",
    );
    assert.ok(await progress.locator("[data-start-guidance]").isVisible(), "空进度时应显示从 W1 开始引导");
    // 预置四课进度与匿名摘要后刷新页面：页面加载即反映 localStorage
    await progress.evaluate(() => {
      localStorage.setItem(
        "course-start-progress",
        JSON.stringify({ "start-1": true, "start-2": true, "start-3": true, "start-4": true }),
      );
      localStorage.setItem(
        "course-start-call-summary",
        JSON.stringify({
          provider: "openai",
          model: "gpt-4o-mini",
          inputTokens: 52,
          outputTokens: 64,
          elapsedMs: 1240,
          at: 1786838400000,
        }),
      );
    });
    await progress.reload();
    await progress.waitForSelector("[data-start-progress-panel]");
    await progress.waitForFunction(() =>
      document.querySelector("[data-start-panel-status]")?.textContent?.includes("4/4"),
    );
    assert.equal(
      await progress.locator("[data-start-state][data-state='done']").count(),
      4,
      "四课完成后应全部显示已完成",
    );
    assert.ok(await progress.locator("[data-start-guidance]").isHidden(), "已有进度时引导应隐藏");
    const summaryHint = await progress.locator("[data-start-summary-hint]").innerText();
    assert.match(summaryHint, /最近一次真实调用：openai · gpt-4o-mini · 2026-08-16/);
    // storage 事件：另一标签页清掉进度后，本页无需刷新即回到未完成
    const otherTab = await progressContext.newPage();
    await otherTab.goto(`${baseUrl}/`);
    await otherTab.waitForSelector("[data-start-progress-panel]");
    await otherTab.evaluate(() => localStorage.removeItem("course-start-progress"));
    await progress.waitForFunction(
      () => document.querySelector('[data-start-state="start-1"]')?.textContent?.includes("未完成"),
      undefined,
      { timeout: 5000 },
    );
    await otherTab.evaluate(() =>
      localStorage.setItem(
        "course-start-progress",
        JSON.stringify({ "start-1": true, "start-2": true, "start-3": true, "start-4": true }),
      ),
    );
    await progress.waitForFunction(
      () => document.querySelector('[data-start-state="start-1"]')?.textContent?.includes("已完成"),
      undefined,
      { timeout: 5000 },
    );
    await otherTab.close();
    // 导出：下载 JSON 文件并核对其形状（只有契约、版本、课节布尔值与摘要六字段）
    const downloadPromise = progress.waitForEvent("download");
    await progress.click("[data-export-start]");
    const download = await downloadPromise;
    assert.equal(download.suggestedFilename(), "agent-engineering-course-start-progress.json");
    const exportPath = path.join(tmpdir(), download.suggestedFilename());
    await download.saveAs(exportPath);
    const exported = JSON.parse(await readFile(exportPath, "utf8"));
    assert.equal(exported.contract, "agent-engineering-course/start-progress");
    assert.equal(exported.contract_version, "1");
    assert.ok(/^[0-9]+\.[0-9]+\.[0-9]+$/.test(exported.course_version), "导出文件应带课程版本字段");
    assert.deepEqual(exported.lessons, {
      "start-1": true,
      "start-2": true,
      "start-3": true,
      "start-4": true,
    });
    assert.deepEqual(
      Object.keys(exported.call_summary).sort(),
      ["at", "elapsedMs", "inputTokens", "model", "outputTokens", "provider"],
    );
    const exportedRaw = await readFile(exportPath, "utf8");
    assert.ok(!exportedRaw.includes("sk-"), "导出文件不得包含密钥形状内容");
    assert.ok(!exportedRaw.includes("message"), "导出文件不得包含消息正文字段");
    // 清空：原生 confirm 确认后两个本地键都消失、界面回到未开始
    progress.once("dialog", (dialog) => dialog.accept());
    await progress.click("[data-clear-start]");
    await progress.waitForFunction(() =>
      document.querySelector("[data-start-panel-status]")?.textContent?.includes("已清空"),
    );
    const clearedKeys = await progress.evaluate(() => [
      localStorage.getItem("course-start-progress"),
      localStorage.getItem("course-start-call-summary"),
    ]);
    assert.deepEqual(clearedKeys, [null, null], "清空后两个本地存储键都应为空");
    assert.ok(await progress.locator("[data-start-guidance]").isVisible(), "清空后应回到从 W1 开始引导");
    // 导入：导出的文件完整恢复四课状态与匿名摘要
    await progress.setInputFiles("#start-progress-file", exportPath);
    await progress.click("[data-import-start]");
    await progress.waitForFunction(() =>
      document.querySelector("[data-start-panel-status]")?.textContent?.includes("已导入起步章进度：4/4"),
    );
    const restored = await progress.evaluate(() => ({
      lessons: JSON.parse(localStorage.getItem("course-start-progress") ?? "{}"),
      summary: JSON.parse(localStorage.getItem("course-start-call-summary") ?? "null"),
    }));
    assert.deepEqual(restored.lessons, {
      "start-1": true,
      "start-2": true,
      "start-3": true,
      "start-4": true,
    });
    assert.equal(restored.summary.provider, "openai");
    assert.equal(restored.summary.at, 1786838400000);
    assert.equal(
      await progress.locator("[data-start-state][data-state='done']").count(),
      4,
      "导入后四课状态应恢复",
    );
    assert.match(
      await progress.locator("[data-start-summary-hint]").innerText(),
      /最近一次真实调用：openai · gpt-4o-mini · 2026-08-16/,
    );
    // 版本不匹配：篡改 course_version 的文件被拒绝，本地状态保持不变
    const mismatched = { ...exported, course_version: "0.0.0-mismatch" };
    const mismatchPath = path.join(tmpdir(), "agent-engineering-course-start-progress-mismatch.json");
    await writeFile(mismatchPath, JSON.stringify(mismatched), "utf8");
    await progress.setInputFiles("#start-progress-file", mismatchPath);
    await progress.click("[data-import-start]");
    await progress.waitForFunction(() =>
      document.querySelector("[data-start-panel-status]")?.textContent?.includes("拒绝导入"),
    );
    assert.match(
      await progress.locator("[data-start-panel-status]").innerText(),
      /不兼容的课程版本/,
    );
    const afterRefusal = await progress.evaluate(() =>
      localStorage.getItem("course-start-progress"),
    );
    assert.match(afterRefusal ?? "", /"start-1":true/, "版本不匹配被拒后本地进度不得被改动");
    await progress.close();
    await progressContext.close();

    console.log("Start lessons browser verification passed: W1 predictions + loop track + quiz redo gate, W3 request journey (offline sample + completion), case library, W2 rewrite, W4 fork map four-key gate, progress wizard, unified progress view with export/clear/import round trip");
  } finally {
    await browser.close();
    await stopPreview();
  }
};

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
