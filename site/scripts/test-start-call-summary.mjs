import assert from "node:assert/strict";
import test from "node:test";

import {
  START_CALL_SUMMARY_STORAGE_KEY,
  START_PROGRESS_STORAGE_KEY,
  markStartLessonComplete,
  readStartCallSummary,
  recordStartCallSummary,
} from "../src/lib/start-progress.mjs";

const memoryStorage = () => {
  const map = new Map();
  return {
    map,
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => {
      map.set(key, String(value));
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
});

const validSummary = {
  provider: "openai",
  model: "gpt-4o-mini",
  inputTokens: 52,
  outputTokens: 64,
  elapsedMs: 1240,
  at: 1755379200000,
};

test("匿名调用摘要使用独立存储键，不与课节进度混存", () => {
  assert.equal(START_CALL_SUMMARY_STORAGE_KEY, "course-start-call-summary");
  assert.notEqual(START_CALL_SUMMARY_STORAGE_KEY, START_PROGRESS_STORAGE_KEY);
});

test("成功调用摘要落盘后可读回且仅含六个白名单字段", () => {
  const storage = memoryStorage();
  assert.equal(recordStartCallSummary(validSummary, storage), true);
  assert.deepEqual(readStartCallSummary(storage), validSummary);
  const persisted = JSON.parse(storage.map.get(START_CALL_SUMMARY_STORAGE_KEY));
  assert.deepEqual(
    Object.keys(persisted).sort(),
    ["at", "elapsedMs", "inputTokens", "model", "outputTokens", "provider"],
  );
});

test("传入的密钥、消息正文等额外字段被静默丢弃，绝不落盘", () => {
  const storage = memoryStorage();
  recordStartCallSummary(
    { ...validSummary, key: "sk-secret-value", message: "你好，模型", apiKey: "sk-leak" },
    storage,
  );
  const raw = storage.map.get(START_CALL_SUMMARY_STORAGE_KEY) ?? "";
  assert.ok(!raw.includes("sk-secret-value"));
  assert.ok(!raw.includes("sk-leak"));
  assert.ok(!raw.includes("你好"));
  assert.deepEqual(readStartCallSummary(storage), validSummary);
});

test("缺字段或非数字用量时拒绝写入且不产生任何存储内容", () => {
  const storage = memoryStorage();
  const bad = [
    null,
    {},
    { ...validSummary, provider: "" },
    { ...validSummary, model: 42 },
    { ...validSummary, inputTokens: "many" },
    { ...validSummary, outputTokens: -1 },
    { ...validSummary, elapsedMs: Number.NaN },
    { ...validSummary, at: 0 },
    { ...validSummary, at: Number.POSITIVE_INFINITY },
  ];
  for (const candidate of bad) {
    assert.equal(recordStartCallSummary(candidate, storage), false);
  }
  assert.equal(storage.map.has(START_CALL_SUMMARY_STORAGE_KEY), false);
  assert.equal(readStartCallSummary(storage), null);
});

test("摘要写入不触碰课节进度记录（向后兼容）", () => {
  const storage = memoryStorage();
  markStartLessonComplete("start-1", storage);
  recordStartCallSummary({ ...validSummary, provider: "anthropic" }, storage);
  const progress = JSON.parse(storage.map.get(START_PROGRESS_STORAGE_KEY));
  assert.deepEqual(progress, { "start-1": true });
  assert.equal(readStartCallSummary(storage).provider, "anthropic");
});

test("读取损坏或形状不符的存量摘要时返回 null 且不抛错", () => {
  const corrupt = memoryStorage();
  corrupt.map.set(START_CALL_SUMMARY_STORAGE_KEY, "{not-json");
  assert.equal(readStartCallSummary(corrupt), null);

  const shape = memoryStorage();
  shape.map.set(START_CALL_SUMMARY_STORAGE_KEY, JSON.stringify({ provider: "x", leak: "sk-1" }));
  assert.equal(readStartCallSummary(shape), null);

  const empty = memoryStorage();
  empty.map.set(START_CALL_SUMMARY_STORAGE_KEY, "");
  assert.equal(readStartCallSummary(empty), null);
});

test("存储不可用（隐私模式等）时静默降级，不抛错", () => {
  const denied = deniedStorage();
  assert.equal(recordStartCallSummary(validSummary, denied), false);
  assert.equal(readStartCallSummary(denied), null);

  assert.equal(recordStartCallSummary(validSummary, null), false);
  assert.equal(recordStartCallSummary(validSummary, undefined), false);
  assert.equal(readStartCallSummary(undefined), null);
  assert.equal(recordStartCallSummary(null, memoryStorage()), false);
});

test("数字字段做取整归一，非整数输入不会写入小数", () => {
  const storage = memoryStorage();
  recordStartCallSummary({ ...validSummary, inputTokens: 52.4, elapsedMs: 1240.9 }, storage);
  const stored = JSON.parse(storage.map.get(START_CALL_SUMMARY_STORAGE_KEY));
  assert.equal(stored.inputTokens, 52);
  assert.equal(stored.elapsedMs, 1241);
});
