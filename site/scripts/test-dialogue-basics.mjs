import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("改写练习组件保持零网络与无障碍契约", () => {
  const component = read("src/components/DialogueRewrite.astro");

  // 零网络：组件不得发起任何网络请求
  assert.doesNotMatch(component, /\bfetch\b|XMLHttpRequest/);
  // 无障碍：参考展示与完成提示使用礼貌 live 区，且有无脚本降级
  assert.match(component, /aria-live="polite"/);
  assert.match(component, /<noscript>/);
  assert.match(component, /role="status"/);
  assert.match(component, /fieldset/);
  // 交互目标满足 44px 触摸基线
  assert.match(component, /min-height: 44px/);
  // 减少动态效果偏好下不播放动画
  assert.match(component, /prefers-reduced-motion/);
});

test("localStorage 只用于本地完成进度", () => {
  const component = read("src/components/DialogueRewrite.astro");

  // 仅允许读写 course-start-progress 进度键，不允许清除或挪作他用
  assert.match(component, /localStorage\.(getItem|setItem)\("course-start-progress"/);
  assert.doesNotMatch(component, /localStorage\.(removeItem|clear)\b/);
  // 完成状态按课节 id 隔离写入
  assert.match(component, /start-2/);
});

test("W2 课页挂载改写练习并讲清四要素", () => {
  const lesson = read("src/content/docs/start-2-dialogue-basics.mdx");

  assert.match(lesson, /import DialogueRewrite from '\.\.\/\.\.\/components\/DialogueRewrite\.astro';/);
  assert.match(lesson, /<DialogueRewrite \/>/);
  // 四要素关键词：目标、上下文、约束、验收
  assert.match(lesson, /目标/);
  assert.match(lesson, /上下文/);
  assert.match(lesson, /约束/);
  assert.match(lesson, /验收/);
  // 预告模块 2 是进阶线完整版
  assert.match(lesson, /\/module-2-agent-instruction\//);
  // 版本与来源卡片在场：原创、无费用、完成状态存浏览器本地
  assert.match(lesson, /版本与来源卡片/);
  assert.match(lesson, /原创/);
  assert.match(lesson, /无费用/);
  assert.match(lesson, /localStorage/);
});
