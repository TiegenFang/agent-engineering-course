import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

// V3-5：W2 指令小剧场、四要素拖拽配对与引用式自证的独立断言。
// 共享的 test-dialogue-basics.mjs 继续覆盖零网络、本地进度与课页挂载契约；本文件只补本 ticket 新增行为。

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8");

test("指令小剧场：双分镜、点击推进、可重放、零网络", () => {
  const theater = read("src/components/InstructionTheater.astro");

  // 双分镜：模糊幕与结构化幕
  assert.match(theater, /data-act=/);
  assert.match(theater, /id: "vague"/);
  assert.match(theater, /id: "structured"/);
  // 模糊幕沿用第 1 轮练习的模糊原文（小剧场与练习共用同一句指令）
  assert.ok(
    theater.includes("帮我把这份传感器数据周报的结论部分改得更清楚些。"),
    "小剧场应沿用 r1 模糊原文",
  );
  // 小循姿态：模糊幕 puzzled，结构化幕 insight
  assert.match(theater, /pose="puzzled"/);
  assert.match(theater, /pose="insight"/);
  // 三份互相矛盾的结果示意（原创内容）
  assert.match(theater, /结果一 · 扩写版/);
  assert.match(theater, /结果二 · 压缩版/);
  assert.match(theater, /结果三 · 顺手版/);
  // 四格抽屉：目标/上下文/约束/验收标准
  for (const element of ["目标", "上下文", "约束", "验收标准"]) {
    assert.ok(theater.includes(element), `小剧场应包含要素「${element}」`);
  }
  // 点击推进（不自动播放）与可重放
  assert.match(theater, /data-theater-next/);
  assert.match(theater, /data-theater-replay/);
  assert.doesNotMatch(theater, /setInterval|requestAnimationFrame|autoplay/);
  // aria-live 播报与 noscript 静态等价物
  assert.match(theater, /aria-live="polite"/);
  assert.match(theater, /<noscript>/);
  // reduced-motion 静态分帧：循环动效只允许出现在 no-preference 分支
  assert.match(theater, /prefers-reduced-motion: no-preference/);
  assert.match(theater, /animation-iteration-count|infinite/);
  // 零网络
  assert.doesNotMatch(theater, /\bfetch\b|XMLHttpRequest/);
});

test("拖拽配对热身：键盘等价、即时反馈、全对才解锁两轮", () => {
  const component = read("src/components/DialogueRewrite.astro");

  // 热身使用与两轮不同的新模糊指令
  assert.ok(component.includes("帮我把这批传感器数据整理下。"));
  assert.equal(
    (component.match(/vague: "/g) ?? []).length,
    2,
    "两轮改写保持 2 条模糊指令数据",
  );
  // 卡片与改写位都是真实 button：键盘「选择 → 放置」路径完整
  assert.match(component, /data-match-card=/);
  assert.match(component, /data-slot-place=/);
  assert.match(component, /aria-pressed="false"/);
  assert.match(component, /draggable="true"/);
  // 放置后可撤回
  assert.match(component, /data-slot-retract/);
  // 即时反馈（对/错 + 一句为什么）经 aria-live 播报
  assert.match(component, /data-warmup-feedback/);
  assert.match(component, /data-why=/);
  // 热身全对前两轮保持隐藏，全对后解锁
  assert.match(component, /<div class="rounds" data-rounds hidden>/);
  assert.match(component, /data-warmup-complete/);
});

test("引用式自证：按句切分呈现、四要素最少一句、不做文本启发式判定", () => {
  const component = read("src/components/DialogueRewrite.astro");

  // 句切分：按 。！？； 与换行，且只作为呈现手段（正则在组件内一处定义）
  assert.ok(component.includes("(?<=[。！？；])"), "句切分应按 。！？； 断句");
  assert.ok(component.includes("\\n+"), "句切分应包含换行分支");
  // 句子条目与要素指认控件在场
  assert.match(component, /data-quote-split/);
  assert.match(component, /data-sentences/);
  assert.match(component, /data-sentence=/);
  assert.match(component, /data-element-assign/);
  assert.match(component, /data-element-clear/);
  // 每轮 0/4 要素引用进度对学员可见
  assert.match(component, /本轮要素引用 0\/4/);
  assert.match(component, /data-round-progress/);
  // 不引入任何文本启发式判分：组件内不得出现对学员文字内容的自动评价实现
  assert.doesNotMatch(component, /关键词|命中|得分|评分|正确率|score|heuristic/i);
  // 完成门槛：热身全对 + 两轮各 4/4 引用后才写入共享进度
  assert.match(component, /markStartLessonComplete/);
  assert.match(component, /counts\.every\(\(count\) => count === 4\)/);
});

test("W2 课页挂载小剧场与三层交互叙述", () => {
  const lesson = read("src/content/docs/start-2-dialogue-basics.mdx");

  assert.match(
    lesson,
    /import InstructionTheater from '\.\.\/\.\.\/components\/InstructionTheater\.astro';/,
  );
  assert.match(lesson, /<InstructionTheater \/>/);
  // 叙述覆盖三层交互与完成判定
  assert.match(lesson, /小剧场/);
  assert.match(lesson, /配对热身/);
  assert.match(lesson, /引用式自证/);
  assert.match(lesson, /切分只是呈现手段，不判分/);
  // 小剧场插画边界声明与正文一致（ADR-0009：不模拟产品界面）
  assert.match(lesson, /不模拟任何真实产品界面/);
});

test("小剧场与第 1 轮练习共用同一句模糊指令", () => {
  const theater = read("src/components/InstructionTheater.astro");
  const component = read("src/components/DialogueRewrite.astro");
  const shared = "帮我把这份传感器数据周报的结论部分改得更清楚些。";

  assert.ok(
    theater.includes(shared),
    "小剧场模糊幕应沿用第 1 轮练习的模糊原文",
  );
  assert.ok(component.includes(shared), "第 1 轮练习应保留该模糊指令");
  assert.ok(
    !theater.includes("帮我把这批传感器数据整理下。"),
    "热身指令不得提前出现在小剧场里",
  );
});
