import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("TerminalBridge 组件保持零网络与仅本地进度契约", () => {
  const component = read("src/components/TerminalBridge.astro");

  // 零网络：组件不得发起任何请求
  assert.doesNotMatch(component, /\bfetch\s*\(/);
  // localStorage 只允许写课程进度这一个键；不得使用 sessionStorage 或其他键
  assert.match(component, /localStorage\.setItem\(\s*"course-start-progress"/);
  assert.doesNotMatch(component, /localStorage\.setItem\(\s*(?!["`]course-start-progress)/);
  assert.doesNotMatch(component, /sessionStorage/);
});

test("TerminalBridge 组件具备无障碍与触控基线", () => {
  const component = read("src/components/TerminalBridge.astro");

  // live 区与 noscript 降级
  assert.match(component, /role="status"/);
  assert.match(component, /aria-live="polite"/);
  assert.match(component, /<noscript>/);
  // 交互目标满足 44px 触摸基线
  assert.match(component, /min-height: 44px/);
  // 动效只在用户未要求减少动态效果时启用
  assert.match(component, /prefers-reduced-motion: no-preference/);
});

test("W4 课页挂载 TerminalBridge 并桥接到模块 0", () => {
  const lesson = read("src/content/docs/start-4-web-to-terminal.mdx");

  assert.match(lesson, /<TerminalBridge \/>/);
  // 桥接目标：模块 0 是安装与诊断的正主
  assert.match(lesson, /\/module-0-environment\//);
  // 课页正文点明两条学习线与本章定位
  assert.match(lesson, /进阶线/);
  assert.match(lesson, /网页端起步/);
  assert.match(lesson, /W1–W4/);
});
