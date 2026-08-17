import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

// V3-6 W4 分岔地图、四键校验与画风衔接的组件契约测试（静态源码检查；
// 浏览器级行为由 scripts/verify-start-lessons.mjs 的 W4 块覆盖）。

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("W4 分岔地图：四键完成判定读取共享进度模块", () => {
  const component = read("src/components/TerminalBridge.astro");

  // 三枚脚印对应 W1–W3 的本地完成键；完成判定 = 三键 + 本页确认
  assert.match(component, /"start-1"/);
  assert.match(component, /"start-2"/);
  assert.match(component, /"start-3"/);
  assert.match(component, /readStartProgress/);
  assert.match(component, /markStartLessonComplete/);
  assert.match(component, /START_PROGRESS_STORAGE_KEY/);
  // 缺键时明确缺哪几课并给出跳转链接
  assert.match(component, /先去完成/);
  assert.match(component, /start-2-dialogue-basics/);
  // 进度可刷新：页面加载 + 手动刷新 + 跨标签页 storage 事件三个入口
  assert.match(component, /data-fork-refresh/);
  assert.match(component, /addEventListener\("storage"/);
});

test("W4 清单修订：理解类计入判定、意愿类不计入", () => {
  const component = read("src/components/TerminalBridge.astro");

  assert.match(component, /data-bridge-kind="understanding"/);
  assert.match(component, /data-bridge-kind="willingness"/);
  assert.match(component, /理解检查（计入完成判定）/);
  assert.match(component, /意愿自评（不计入完成判定）/);
  // 完成判定只看理解类勾选，不看意愿类
  assert.match(component, /understandingChecks\.every/);
  // 理解类条目即四键中的「本页确认」
  assert.match(component, /本页确认/);
});

test("W4 分岔地图：无障碍基线（非颜色编码、aria-live、noscript 清单、键盘可达）", () => {
  const component = read("src/components/TerminalBridge.astro");

  // 点亮/开门状态不得只靠颜色：文字标签在场
  assert.match(component, /data-footprint-state/);
  assert.match(component, />[\s]*未点亮[\s]*</);
  assert.match(component, /data-door-state/);
  assert.match(component, /终端之门：未点亮/);
  // 状态变化播报
  assert.match(component, /data-fork-status/);
  assert.match(component, /data-bridge-status/);
  assert.match(component, /aria-live="polite"/);
  // noscript 退化为带链接的清单文字（W1–W3 与模块 0 链接不依赖脚本）
  assert.match(component, /<noscript>/);
  assert.match(component, /文字清单版/);
  assert.match(component, /module-0-environment\//);
  // 键盘可达的真实控件与 44px 触摸基线
  assert.match(component, /<button[^>]*type="button"[^>]*data-fork-refresh/);
  assert.match(component, /min-height: 44px/);
  assert.match(component, /focus-visible/);
});

test("W4 画风衔接：完成区切回 Editorial 编辑风，且全部状态切换为静态替换", () => {
  const component = read("src/components/TerminalBridge.astro");

  assert.match(component, /data-bridge-done/);
  // 叙事承接「风格随能力成长：小循把工具箱交给你」
  assert.match(component, /小循把工具箱交给了你/);
  assert.match(component, /编辑排版/);
  // 小循以 done 姿态在门前递工具箱（几何道具）
  assert.match(component, /Mascot pose="done"/);
  assert.match(component, /工具箱（课程原创几何示意道具）/);
  // 过渡不得用动画：组件不得携带任何 keyframes/animation/transition
  assert.doesNotMatch(component, /@keyframes/);
  assert.doesNotMatch(component, /animation\s*:/);
  assert.doesNotMatch(component, /transition\s*:/);
});

test("W4 课页正文改写且内容契约元数据完好", () => {
  const lesson = read("src/content/docs/start-4-web-to-terminal.mdx");

  assert.match(lesson, /<TerminalBridge \/>/);
  assert.match(lesson, /分岔地图/);
  assert.match(lesson, /四把钥匙/);
  assert.match(lesson, /理解检查/);
  assert.match(lesson, /意愿自评/);
  assert.match(lesson, /刷新脚印进度/);
  // 课节元数据与来源卡片保留
  assert.match(lesson, /版本与来源卡片/);
  assert.match(lesson, /\/module-0-environment\//);
  assert.match(lesson, /进阶线/);
  assert.match(lesson, /网页端起步/);
  assert.match(lesson, /W1–W4/);
});
