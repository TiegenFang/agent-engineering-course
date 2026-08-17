import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("BYO-key 组件保持浏览器直连安全契约", () => {
  const component = read("src/components/ByoKeyChat.astro");

  // 密钥不持久化：组件源中不得出现 localStorage/sessionStorage 写入
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

test("起步章课页挂载交互组件并声明边界", () => {
  const w1 = read("src/content/docs/start-1-what-is-agent.mdx");
  const w3 = read("src/content/docs/start-3-api-key-chat.mdx");

  assert.match(w1, /<StartQuiz \/>/);
  assert.match(w1, /不办密钥|无需账号|无费用/);
  assert.match(w3, /<ByoKeyChat \/>/);
  assert.match(w3, /不办密钥也能完成本课/);
  assert.match(w3, /2026-08-17 核验/);
  assert.match(w3, /只存浏览器内存|只存在本页内存/);
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
