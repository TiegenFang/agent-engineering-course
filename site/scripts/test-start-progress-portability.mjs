import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  START_CALL_SUMMARY_STORAGE_KEY,
  START_PROGRESS_EXPORT_CONTRACT,
  START_PROGRESS_EXPORT_CONTRACT_VERSION,
  START_PROGRESS_EXPORT_FILENAME,
  START_PROGRESS_STORAGE_KEY,
  StartProgressPortabilityError,
  buildStartProgressExport,
  clearStartProgress,
  markStartLessonComplete,
  parseStartProgressImport,
  readStartCallSummary,
  readStartProgress,
  recordStartCallSummary,
  restoreStartProgress,
} from "../src/lib/start-progress.mjs";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFileSync(join(siteRoot, relativePath), "utf8").replace(/\r/g, "");

const memoryStorage = () => {
  const map = new Map();
  return {
    map,
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => {
      map.set(key, String(value));
    },
    removeItem: (key) => {
      map.delete(key);
    },
  };
};

const deniedStorage = () => ({
  getItem: () => {
    throw new Error("SecurityError");
  },
  setItem: () => {
    throw new Error("QuotaExceededError");
  },
  removeItem: () => {
    throw new Error("SecurityError");
  },
});

const courseVersion = "9.9.9-test";
const validSummary = {
  provider: "openai",
  model: "gpt-4o-mini",
  inputTokens: 52,
  outputTokens: 64,
  elapsedMs: 1240,
  at: 1755379200000,
};

const seedStorage = () => {
  const storage = memoryStorage();
  storage.map.set(
    START_PROGRESS_STORAGE_KEY,
    JSON.stringify({ "start-1": true, "start-2": true, "start-3": true, "start-4": true }),
  );
  storage.map.set(START_CALL_SUMMARY_STORAGE_KEY, JSON.stringify(validSummary));
  return storage;
};

const importError = (input, version = courseVersion) => {
  try {
    parseStartProgressImport(input, version);
  } catch (error) {
    if (error instanceof StartProgressPortabilityError) return error;
    throw error;
  }
  return null;
};

test("导出契约标记与下载文件名保持稳定", () => {
  assert.equal(START_PROGRESS_EXPORT_CONTRACT, "agent-engineering-course/start-progress");
  assert.equal(START_PROGRESS_EXPORT_CONTRACT_VERSION, "1");
  assert.equal(START_PROGRESS_EXPORT_FILENAME, "agent-engineering-course-start-progress.json");
});

test("导出封套只含契约、版本、课节布尔值与匿名摘要六字段", () => {
  const payload = buildStartProgressExport(courseVersion, seedStorage());
  assert.deepEqual(Object.keys(payload).sort(), [
    "call_summary",
    "contract",
    "contract_version",
    "course_version",
    "lessons",
  ]);
  assert.equal(payload.contract, START_PROGRESS_EXPORT_CONTRACT);
  assert.equal(payload.contract_version, START_PROGRESS_EXPORT_CONTRACT_VERSION);
  assert.equal(payload.course_version, courseVersion);
  assert.deepEqual(payload.lessons, {
    "start-1": true,
    "start-2": true,
    "start-3": true,
    "start-4": true,
  });
  assert.deepEqual(payload.call_summary, validSummary);
  const serialized = JSON.stringify(payload);
  assert.ok(!serialized.includes("sk-"), "导出绝不能携带密钥形状的字段");
  // 摘要六字段白名单原样保留
  assert.deepEqual(
    Object.keys(payload.call_summary).sort(),
    ["at", "elapsedMs", "inputTokens", "model", "outputTokens", "provider"],
  );
});

test("空进度导出为合法封套：lessons 为空对象、call_summary 为 null", () => {
  const payload = buildStartProgressExport(courseVersion, memoryStorage());
  assert.deepEqual(payload.lessons, {});
  assert.equal(payload.call_summary, null);
});

test("存储不可用（隐私模式等）时导出静默降级，不抛错", () => {
  const payload = buildStartProgressExport(courseVersion, deniedStorage());
  assert.deepEqual(payload.lessons, {});
  assert.equal(payload.call_summary, null);
  assert.deepEqual(buildStartProgressExport(courseVersion, null).lessons, {});
});

test("导出 → 导入在另一浏览器完整恢复课节状态与匿名摘要", () => {
  const source = seedStorage();
  const file = JSON.stringify(buildStartProgressExport(courseVersion, source));
  const target = memoryStorage();

  const parsed = parseStartProgressImport(file, courseVersion);
  assert.equal(restoreStartProgress(parsed, target), true);
  assert.deepEqual(readStartProgress(target), {
    "start-1": true,
    "start-2": true,
    "start-3": true,
    "start-4": true,
  });
  assert.deepEqual(readStartCallSummary(target), validSummary);
  // 恢复后的记录可以继续被既有 API 合并写入（向后兼容）
  assert.equal(markStartLessonComplete("start-4", target), true);
});

test("导入无摘要的文件会清掉目标浏览器里的旧摘要（完整往返语义）", () => {
  const target = memoryStorage();
  target.map.set(START_PROGRESS_STORAGE_KEY, JSON.stringify({ "start-1": true }));
  recordStartCallSummary(validSummary, target);

  const file = JSON.stringify({
    contract: START_PROGRESS_EXPORT_CONTRACT,
    contract_version: START_PROGRESS_EXPORT_CONTRACT_VERSION,
    course_version: courseVersion,
    lessons: { "start-2": true },
    call_summary: null,
  });
  const parsed = parseStartProgressImport(file, courseVersion);
  assert.equal(restoreStartProgress(parsed, target), true);
  assert.deepEqual(readStartProgress(target), { "start-2": true });
  assert.equal(readStartCallSummary(target), null);
  // call_summary 字段缺省时同样按 null 处理
  const parsedMissing = parseStartProgressImport(
    JSON.stringify({
      contract: START_PROGRESS_EXPORT_CONTRACT,
      contract_version: START_PROGRESS_EXPORT_CONTRACT_VERSION,
      course_version: courseVersion,
      lessons: { "start-3": true },
    }),
    courseVersion,
  );
  assert.equal(parsedMissing.callSummary, null);
});

test("课程版本不匹配的文件被拒绝且不触碰本地存储", () => {
  const file = JSON.stringify(buildStartProgressExport(courseVersion, seedStorage()));
  const error = importError(file, "0.0.1-other");
  assert.ok(error, "版本不匹配必须抛错");
  assert.equal(error.code, "incompatible-course-version");

  const target = seedStorage();
  const before = target.map.get(START_PROGRESS_STORAGE_KEY);
  const summaryBefore = target.map.get(START_CALL_SUMMARY_STORAGE_KEY);
  assert.throws(() => parseStartProgressImport(file, "0.0.1-other"));
  assert.equal(target.map.get(START_PROGRESS_STORAGE_KEY), before);
  assert.equal(target.map.get(START_CALL_SUMMARY_STORAGE_KEY), summaryBefore);
});

test("契约不符、契约版本不符与损坏 JSON 分别给出独立错误码", () => {
  assert.equal(importError("{not-json").code, "invalid-json");
  // 合法 JSON 但不是对象（数字、null）同样按导入形状错误处理
  assert.equal(importError("42").code, "invalid-import");
  assert.equal(importError(null).code, "invalid-import");
  assert.equal(importError("[]").code, "invalid-import");
  assert.equal(
    importError(
      JSON.stringify({
        contract: "agent-engineering-course/learning-record",
        contract_version: START_PROGRESS_EXPORT_CONTRACT_VERSION,
        course_version: courseVersion,
        lessons: {},
      }),
    ).code,
    "unsupported-contract",
  );
  assert.equal(
    importError(
      JSON.stringify({
        contract: START_PROGRESS_EXPORT_CONTRACT,
        contract_version: "2",
        course_version: courseVersion,
        lessons: {},
      }),
    ).code,
    "unsupported-contract-version",
  );
});

test("lessons 非对象或超量条目被拒绝，形状不符的条目被静默过滤", () => {
  const base = {
    contract: START_PROGRESS_EXPORT_CONTRACT,
    contract_version: START_PROGRESS_EXPORT_CONTRACT_VERSION,
    course_version: courseVersion,
  };
  assert.equal(importError(JSON.stringify({ ...base, lessons: "yes" })).code, "invalid-import");
  assert.equal(importError(JSON.stringify({ ...base, lessons: [1, 2] })).code, "invalid-import");
  assert.equal(importError(JSON.stringify({ ...base })).code, "invalid-import");

  const flooded = {};
  for (let i = 0; i < 80; i += 1) flooded[`lesson-${i}`] = true;
  assert.equal(importError(JSON.stringify({ ...base, lessons: flooded })).code, "invalid-import");

  const parsed = parseStartProgressImport(
    JSON.stringify({
      ...base,
      lessons: { "start-1": true, "start-2": "yes", "start-3": false, count: 3 },
    }),
    courseVersion,
  );
  assert.deepEqual(parsed.lessons, { "start-1": true, "start-3": false });
});

test("夹带密钥或消息正文的伪造摘要被拒绝，绝不进入本地存储", () => {
  const base = {
    contract: START_PROGRESS_EXPORT_CONTRACT,
    contract_version: START_PROGRESS_EXPORT_CONTRACT_VERSION,
    course_version: courseVersion,
    lessons: { "start-1": true },
  };
  const error = importError(JSON.stringify({ ...base, call_summary: { provider: "x", leak: "sk-1" } }));
  assert.equal(error.code, "invalid-call-summary");

  const storage = memoryStorage();
  assert.throws(() => parseStartProgressImport("nope", courseVersion));
  assert.equal(storage.map.has(START_PROGRESS_STORAGE_KEY), false);
});

test("清空同时移除课节进度与匿名摘要两个键", () => {
  const storage = seedStorage();
  assert.equal(clearStartProgress(storage), true);
  assert.equal(storage.map.has(START_PROGRESS_STORAGE_KEY), false);
  assert.equal(storage.map.has(START_CALL_SUMMARY_STORAGE_KEY), false);
  assert.deepEqual(readStartProgress(storage), {});
  assert.equal(readStartCallSummary(storage), null);

  assert.equal(clearStartProgress(deniedStorage()), false);
  assert.equal(clearStartProgress(null), false);
});

test("恢复写入失败（存储不可用）时返回 false 且不抛错", () => {
  const parsed = { lessons: { "start-1": true }, callSummary: validSummary };
  assert.equal(restoreStartProgress(parsed, deniedStorage()), false);
  assert.equal(restoreStartProgress(parsed, null), false);
  assert.equal(restoreStartProgress(null, memoryStorage()), false);
});

test("首页面板：统一视图挂载在本地学习记录区域，与 EvidenceLoop 并列", () => {
  const shell = read("src/components/CourseShell.astro");
  const panel = read("src/components/StartProgressPanel.astro");

  assert.ok(shell.indexOf("<StartProgressPanel />") > -1, "CourseShell 应挂载起步章进度面板");
  assert.ok(
    shell.indexOf("<StartProgressPanel />") < shell.indexOf("<EvidenceLoop"),
    "起步章面板应与 EvidenceLoop 并列出现在 record-section",
  );
  assert.match(shell, /我的进度：两段旅程，一处可见/);

  // 四课状态、匿名摘要提示与「从 W1 开始」引导都在面板静态骨架里
  assert.equal((panel.match(/id: "start-\d"/g) ?? []).length, 4, "面板应定义 W1–W4 四课条目");
  assert.match(panel, /data-start-state=\{lesson\.id\}/);
  assert.match(panel, /data-start-summary-hint/);
  assert.match(panel, /data-start-guidance/);
  assert.match(panel, /从 W1 开始/);
  assert.match(panel, /最近一次真实调用/);
});

test("首页面板：导出/导入/清空可键盘操作，导入结果有 aria-live 播报", () => {
  const panel = read("src/components/StartProgressPanel.astro");

  // 原生 button/input 天然键盘可操作；状态播报复用 evidence-loop 的 role=status 模式
  assert.match(panel, /role="status"/);
  assert.match(panel, /aria-live="polite"/);
  assert.match(panel, /<button type="button" data-import-start>/);
  assert.match(panel, /<button type="button" data-export-start>/);
  assert.match(panel, /<button type="button" data-clear-start>/);
  // 清空使用原生 confirm（明确允许），全程禁用 alert
  assert.match(panel, /window\.confirm\(/);
  assert.doesNotMatch(panel, /\balert\s*\(/);
  // 零网络：面板不发起任何请求
  assert.doesNotMatch(panel, /\bfetch\s*\(/);
  assert.doesNotMatch(panel, /XMLHttpRequest/);
  assert.doesNotMatch(panel, /sendBeacon/);
});

test("首页面板：noscript 说明导入导出需要 JavaScript，课文阅读不受影响", () => {
  const panel = read("src/components/StartProgressPanel.astro");
  assert.match(panel, /<noscript>/);
  assert.match(panel, /导出、导入与清空按钮不会执行/);
  assert.match(panel, /阅读不受影响/);
});

test("首页面板：监听 storage 事件让状态实时反映其他标签页的进度变化", () => {
  const panel = read("src/components/StartProgressPanel.astro");
  assert.match(panel, /addEventListener\("storage"/);
  assert.match(panel, /START_PROGRESS_STORAGE_KEY/);
  assert.match(panel, /START_CALL_SUMMARY_STORAGE_KEY/);
});

test("进度向导第 0 步补起步章衔接语，其余步骤保持不变", () => {
  const wizard = read("src/components/ProgressWizard.astro");
  const stepZero = wizard.slice(
    wizard.indexOf('data-wizard-step="0"'),
    wizard.indexOf('data-wizard-step="1"'),
  );
  assert.match(stepZero, /W1–W4 网页端起步章/);
  assert.match(stepZero, /先回首页完成起步章/);
  assert.match(stepZero, /再来跑这里的命令/);
  // 既有步骤内容未被删动
  assert.match(wizard, /第 1 步 · 我该跑哪条命令？/);
  assert.match(wizard, /第 2 步 · 导入文件/);
  assert.match(wizard, /第 3 步 · 没成功？/);
  assert.match(wizard, /为什么要这么麻烦？/);
});
