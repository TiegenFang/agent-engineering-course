import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("BYO-key 组件保持浏览器直连安全契约", () => {
  const component = read("src/components/ByoKeyChat.astro");

  // 密钥不持久化：组件源中不得出现 localStorage/sessionStorage 写入（经共享模块的摘要除外）
  assert.doesNotMatch(component, /localStorage\.setItem|sessionStorage\.setItem/);
  // 密钥输入必须是 password 类型且关闭自动补全
  assert.match(component, /type="password"/);
  assert.match(component, /autocomplete="off"/);
  // 离线演示必须是默认模式，且不发网络请求
  assert.match(component, /value="offline" checked/);
  // 真实调用只允许直连两个官方端点：字面量 fetch 必须指向官方域；变量端点仅由上方两处官方赋值产生
  assert.match(component, /https:\/\/api\.anthropic\.com\/v1\/messages/);
  assert.match(component, /https:\/\/api\.openai\.com\/v1\/chat\/completions/);
  assert.doesNotMatch(component, /fetch\((["'`])(?!https:\/\/api\.)/);
  assert.doesNotMatch(component, /endpoint = (["'`])(?=[^"'`])(?!https:\/\/api\.)/);
  // Anthropic 浏览器直连许可头（ADR-0008 核验 2026-08-17）
  assert.match(component, /anthropic-dangerous-direct-browser-access/);
  assert.match(component, /anthropic-version/);
  // 无障碍与降级：live 区与 noscript
  assert.match(component, /aria-live="polite"/);
  assert.match(component, /<noscript>/);
  // 免费路径必须在场：离线模式明示零网络零费用
  assert.match(component, /零网络、零费用/);
});

test("W3 请求之旅：离线挂载真实样例并如实标注来源状态", () => {
  const component = read("src/components/ByoKeyChat.astro");

  // 样例数据来自仓内 JSON 文件，且离线模式明确「已记录样例，非此刻发出」
  assert.match(component, /w3-request-journey-sample\.json/);
  assert.match(component, /已记录样例，非此刻发出/);
  assert.match(component, /依据官方文档响应形状构造/);
  assert.match(component, /待现场采集核验/);
  // 预制玩笑串回复必须移除
  assert.doesNotMatch(component, /离线演示回复/);
  // 样例逐段注释在页面上可展开查看
  assert.match(component, /data-byo-json="openai"/);
  assert.match(component, /data-byo-json="anthropic"/);
  assert.match(component, /annotations/);
});

test("W3 请求之旅：分步推进动画与静态等价物", () => {
  const component = read("src/components/ByoKeyChat.astro");

  // 使用 V3-2 插画组件：包裹与带计费的钥匙配角（package 标签传真实记录数字）
  assert.match(component, /from "\.\/mascot\/Mascot\.astro"/);
  assert.match(component, /from "\.\/mascot\/Cast\.astro"/);
  assert.match(component, /role="package"/);
  assert.match(component, /role="key"/);
  // 分步数据驱动：aria-live 播报与分帧图注同源（同一 journeySteps 数据）
  assert.match(component, /data-journey-steps/);
  assert.match(component, /data-journey-errors/);
  assert.match(component, /data-journey-next/);
  assert.match(component, /data-j-caption/);
  // reduced-motion 下为静态分帧：过渡动画仅在 no-preference 时启用
  assert.match(component, /prefers-reduced-motion: no-preference/);
  // 7 个主帧 + 错误分支帧
  for (const frameId of ["compose", "pack", "tunnel", "checkpoint", "generate", "return", "unpack"]) {
    assert.match(component, new RegExp(`data-j-frame="${frameId}"`), `缺少主帧 ${frameId}`);
  }
  assert.match(component, /data-j-frame="err-key"/);
  assert.match(component, /data-j-frame="err-rate"/);
  assert.match(component, /data-j-frame="err-network"/);
});

test("W3 完成判定与匿名调用摘要经共享模块落盘", () => {
  const component = read("src/components/ByoKeyChat.astro");

  assert.match(component, /from "\.\.\/lib\/start-progress\.mjs"/);
  assert.match(component, /markStartLessonComplete\("start-3"\)/);
  // 摘要只传六个白名单字段；recordStartCallSummary 负责过滤密钥与消息正文
  assert.match(component, /recordStartCallSummary\(\{/);
  assert.match(component, /readStartCallSummary\(\)/);
  assert.match(component, /不含密钥与消息正文/);
});

test("W3 无密钥路径与普通话错误提示", () => {
  const component = read("src/components/ByoKeyChat.astro");

  // 无密钥学员有明确「以后再来」的继续路径与安全感提示（可撤销、能重来）
  assert.match(component, /暂时没有密钥/);
  assert.match(component, /撤销/);
  // 401/403 与 429 的普通话提示
  assert.match(component, /没复制完整或没权限/);
  assert.match(component, /请求太快或账户额度用完/);
  // 失败被框定为有价值的实验数据，错误分支动画「包裹被关卡退回」
  assert.match(component, /包裹被关卡退回/);
  assert.match(component, /有价值的实验数据/);
  // 账户创建可选侧栏（D8）：只外链官方页面 + 成本标注，折叠式不抢主路径
  assert.match(component, /platform\.openai\.com/);
  assert.match(component, /console\.anthropic\.com/);
  assert.match(component, /按你的账户计费/);
});

test("W3 样例数据文件结构与来源状态契约", () => {
  const bundle = JSON.parse(read("src/data/w3-request-journey-sample.json"));

  // 来源状态如实标注：构造自官方文档形状，待现场采集核验
  assert.match(bundle._meta.status, /constructed-from-official-docs-shape/);
  assert.match(bundle._meta.status, /live-capture-pending/);
  assert.equal(bundle._meta.constructed_from.length, 2);
  for (const source of bundle._meta.constructed_from) {
    assert.match(source.url, /^https:\/\/(platform\.openai\.com|platform\.claude\.com)\//);
    assert.match(source.verified_on, /2026-08-/);
  }

  const openai = bundle.samples.openai;
  const anthropic = bundle.samples.anthropic;

  // 请求端点为官方端点；逐段注释、用量与耗时齐备
  assert.equal(openai.endpoint, "https://api.openai.com/v1/chat/completions");
  assert.equal(anthropic.endpoint, "https://api.anthropic.com/v1/messages");
  for (const sample of [openai, anthropic]) {
    assert.ok(sample.usage.inputTokens > 0 && sample.usage.outputTokens > 0);
    assert.ok(sample.elapsedMs > 0);
    assert.ok(sample.annotations.length >= 5);
    assert.ok(sample.request.body.messages.length >= 1);
  }

  // 响应形状逐字段对照官方文档：OpenAI choices/usage、Anthropic content/usage
  assert.equal(openai.response.object, "chat.completion");
  assert.equal(typeof openai.response.choices[0].message.content, "string");
  assert.equal(typeof openai.response.usage.prompt_tokens, "number");
  assert.equal(typeof openai.response.usage.completion_tokens, "number");
  assert.equal(anthropic.response.type, "message");
  assert.equal(anthropic.response.content[0].type, "text");
  assert.equal(typeof anthropic.response.usage.input_tokens, "number");
  assert.equal(typeof anthropic.response.usage.output_tokens, "number");

  // 样例不含任何密钥或个人数据痕迹
  const raw = read("src/data/w3-request-journey-sample.json");
  assert.doesNotMatch(raw, /sk-[A-Za-z0-9]{16,}/);
});

test("起步章课页挂载交互组件并声明边界", () => {
  const w1 = read("src/content/docs/start-1-what-is-agent.mdx");
  const w3 = read("src/content/docs/start-3-api-key-chat.mdx");

  assert.match(w1, /<StartQuiz \/>/);
  assert.match(w1, /不办密钥|无需账号|无费用/);
  assert.match(w3, /<ByoKeyChat \/>/);
  assert.match(w3, /不办密钥也能完成本课/);
  assert.match(w3, /2026-08-17 核验/);
  assert.match(w3, /只存浏览器内存|只存在本页内存/);
  // V3-3：样例来源与匿名摘要边界必须写进正文
  assert.match(w3, /已记录样例/);
  assert.match(w3, /待现场采集核验/);
  assert.match(w3, /匿名调用摘要/);
  assert.match(w3, /绝不含密钥与消息正文/);
});

test("知识检查组件具备无障碍与本地完成状态", () => {
  const quiz = read("src/components/StartQuiz.astro");

  assert.match(quiz, /aria-live="polite"/);
  assert.match(quiz, /<noscript>/);
  assert.match(quiz, /role="status"/);
  assert.match(quiz, /fieldset/);
  // 交互目标满足 44px 触摸基线
  assert.match(quiz, /min-height: 44px/);
});

test("案例参考库只做导读与外链并标注许可证边界", () => {
  const cases = read("src/content/docs/case-library.mdx");

  assert.match(cases, /obra\/superpowers/);
  assert.match(cases, /mattpocock\/skills/);
  assert.match(cases, /anthropics\/skills/);
  assert.match(cases, /专有许可/);
  assert.match(cases, /不复制内容/);
  assert.match(cases, /2026-08-17/);
});
