import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  countGateDone,
  isGateSatisfied,
  missingGateItems,
  readStartGate,
  startGateLabels,
  START_GATE_EVENT,
} from "../src/lib/start-lesson-gate.mjs";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("完成判定模块：三项条件汇总为纯 DOM 读 + 纯函数", () => {
  assert.equal(START_GATE_EVENT, "start-gate-change");
  assert.deepEqual(Object.keys(startGateLabels), ["predict", "track", "quiz"]);

  // 用最小 stub 根模拟页面：data-done="1" / "0" / 缺失三种情形
  const stubRoot = (done) => ({
    querySelector: (selector) => {
      const kind = selector.match(/data-start-gate="(\w+)"/)?.[1];
      if (!kind || !(kind in done)) return null;
      return { getAttribute: (attr) => (attr === "data-done" && done[kind] ? "1" : "0") };
    },
  });

  const partial = readStartGate(stubRoot({ predict: true, track: false, quiz: true }));
  assert.deepEqual(partial, { predict: true, track: false, quiz: true });
  assert.equal(isGateSatisfied(partial), false);
  assert.equal(countGateDone(partial), 2);
  assert.deepEqual(missingGateItems(partial), [startGateLabels.track]);

  const all = readStartGate(stubRoot({ predict: true, track: true, quiz: true }));
  assert.equal(isGateSatisfied(all), true);
  assert.deepEqual(missingGateItems(all), []);

  // 某一区块根本不在页面上时按未满足处理，不得误判完成
  const missing = readStartGate(stubRoot({ predict: true, track: true }));
  assert.equal(missing.quiz, false);
  assert.equal(isGateSatisfied(missing), false);
});

test("循环跑道组件保持零网络、共享进度与插画层契约", () => {
  const component = read("src/components/AgentLoopTrack.astro");

  // 零网络：组件不得发起任何网络请求
  assert.doesNotMatch(component, /\bfetch\b|XMLHttpRequest/);
  // 插画层：跑道用 Cast track 配角，小循姿态随站点变化（ADR-0009 / v3 插画 spec）
  assert.match(component, /<Cast\s+role="track"/);
  assert.match(component, /<Mascot pose=\{station\.pose\}/);
  assert.match(component, /"puzzled"|"insight"|"effort"|"done"/);
  // 完成写入统一经共享进度模块；组件不得直接触碰存储
  assert.match(component, /from "\.\.\/lib\/start-progress\.mjs"/);
  assert.match(component, /markStartLessonComplete/);
  assert.doesNotMatch(component, /localStorage|sessionStorage/);
  // 三项完成判定经 gate 模块汇总，并有事件联动
  assert.match(component, /from "\.\.\/lib\/start-lesson-gate\.mjs"/);
  assert.match(component, /START_GATE_EVENT/);
  // 预测与跑道各自暴露 gate 旗标，供同页知识检查联动
  assert.match(component, /data-start-gate="predict"/);
  assert.match(component, /data-start-gate="track"/);
  // 四站锚点：知识检查错题「回跑道第 N 站」的跳转目标
  assert.match(component, /loop-station-\$\{station\.n\}/);
});

test("循环跑道组件满足无障碍与静态等价物要求", () => {
  const component = read("src/components/AgentLoopTrack.astro");

  // 无障碍：状态播报、fieldset 语义、无脚本降级、44px 触摸基线
  assert.match(component, /aria-live="polite"/);
  assert.match(component, /role="status"/);
  assert.match(component, /fieldset/);
  assert.match(component, /<noscript>/);
  assert.match(component, /min-height: 44px/);
  assert.match(component, /:focus-visible/);
  // 减少动态效果偏好下为静态分帧：动效只允许出现在 no-preference 分支
  assert.match(component, /prefers-reduced-motion: no-preference/);
  assert.match(component, /prefers-reduced-motion: reduce/);
  // 静态等价物：无 JS 时四站解释全部可见（服务端渲染，不靠脚本生成内容）
  assert.match(component, /loop-active-mode/);
  // 点击推进（非自动播放）：上一步/下一步为真实按钮
  assert.match(component, /data-track-prev/);
  assert.match(component, /data-track-next/);
});

test("知识检查支持重做、错题回顾与回跑道链接", () => {
  const quiz = read("src/components/StartQuiz.astro");

  // 重做与逐题回顾
  assert.match(quiz, /data-quiz-reset/);
  assert.match(quiz, /data-quiz-review/);
  // 错题跳转：跑道站点链接（data-goto-station 由跑道状态机监听）
  assert.match(quiz, /loop-station-4/);
  assert.match(quiz, /gotoStation/);
  // 完成判定只上报状态（gate 事件 + 旗标），落盘由跑道组件的完成条件清单执行
  assert.match(quiz, /data-start-gate="quiz"/);
  assert.match(quiz, /from "\.\.\/lib\/start-lesson-gate\.mjs"/);
  assert.doesNotMatch(quiz, /markStartLessonComplete/);
  assert.doesNotMatch(quiz, /localStorage|sessionStorage/);
  // 沿用既有无障碍契约
  assert.match(quiz, /aria-live="polite"/);
  assert.match(quiz, /<noscript>/);
  assert.match(quiz, /role="status"/);
  assert.match(quiz, /fieldset/);
  assert.match(quiz, /min-height: 44px/);
});

test("W1 课页挂载跑道与知识检查并保留来源卡片", () => {
  const lesson = read("src/content/docs/start-1-what-is-agent.mdx");

  assert.match(lesson, /import AgentLoopTrack from '\.\.\/\.\.\/components\/AgentLoopTrack\.astro';/);
  assert.match(lesson, /<AgentLoopTrack \/>/);
  assert.match(lesson, /<StartQuiz \/>/);
  // 先猜后看的叙述与四站概念在场
  assert.match(lesson, /预测/);
  assert.match(lesson, /收到输入/);
  assert.match(lesson, /生成输出/);
  assert.match(lesson, /调用工具/);
  assert.match(lesson, /观察结果/);
  // 知识检查错题回顾的页内锚点（API key 预告段）
  assert.match(lesson, /id="api-key-preview"/);
  // 版本与来源卡片在场：原创、无费用、本地完成状态
  assert.match(lesson, /版本与来源卡片/);
  assert.match(lesson, /原创/);
  assert.match(lesson, /无费用/);
  assert.match(lesson, /localStorage/);
});
