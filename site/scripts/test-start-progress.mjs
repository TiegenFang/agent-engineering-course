import assert from "node:assert/strict";
import test from "node:test";

import {
  START_PROGRESS_STORAGE_KEY,
  markStartLessonComplete,
  readStartProgress,
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

test("共享进度模块使用唯一课程起步进度键", () => {
  assert.equal(START_PROGRESS_STORAGE_KEY, "course-start-progress");
});

test("标记课节完成会合并写入且保留其他课节的既有进度", () => {
  const storage = memoryStorage();
  storage.map.set(START_PROGRESS_STORAGE_KEY, JSON.stringify({ "start-1": true }));

  assert.equal(markStartLessonComplete("start-2", storage), true);
  assert.deepEqual(readStartProgress(storage), { "start-1": true, "start-2": true });
  // 落盘形状保持 { lessonId: boolean }，旧版本写入的记录原样生效
  assert.equal(storage.map.get(START_PROGRESS_STORAGE_KEY), '{"start-1":true,"start-2":true}');

  markStartLessonComplete("start-4", storage);
  assert.deepEqual(readStartProgress(storage), {
    "start-1": true,
    "start-2": true,
    "start-4": true,
  });
});

test("读取缺失、空串或损坏的存量值时按空进度处理且不抛错", () => {
  const missing = memoryStorage();
  assert.deepEqual(readStartProgress(missing), {});

  const empty = memoryStorage();
  empty.map.set(START_PROGRESS_STORAGE_KEY, "");
  assert.deepEqual(readStartProgress(empty), {});

  const corrupt = memoryStorage();
  corrupt.map.set(START_PROGRESS_STORAGE_KEY, "{not-json");
  assert.deepEqual(readStartProgress(corrupt), {});
  // 损坏值不阻塞后续写入：下一次合并写入会以合法 JSON 覆盖
  assert.equal(markStartLessonComplete("start-3", corrupt), true);
  assert.deepEqual(readStartProgress(corrupt), { "start-3": true });

  const nonObject = memoryStorage();
  nonObject.map.set(START_PROGRESS_STORAGE_KEY, JSON.stringify([1, 2]));
  assert.deepEqual(readStartProgress(nonObject), {});
});

test("读取时过滤不符合 { lessonId: boolean } 形状的字段", () => {
  const storage = memoryStorage();
  storage.map.set(
    START_PROGRESS_STORAGE_KEY,
    JSON.stringify({ "start-1": true, "start-2": "yes", count: 3, "start-4": false }),
  );
  assert.deepEqual(readStartProgress(storage), { "start-1": true, "start-4": false });
});

test("存储不可用（隐私模式等）时静默降级，不抛错", () => {
  const denied = deniedStorage();
  assert.deepEqual(readStartProgress(denied), {});
  assert.equal(markStartLessonComplete("start-1", denied), false);

  assert.deepEqual(readStartProgress(null), {});
  assert.equal(markStartLessonComplete("start-1", null), false);
});

test("访问全局 localStorage 本身抛错时静默降级", () => {
  const original = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  let installed = true;
  try {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      get() {
        throw new Error("SecurityError");
      },
    });
  } catch {
    installed = false;
  }

  try {
    if (installed) {
      assert.deepEqual(readStartProgress(), {});
      assert.equal(markStartLessonComplete("start-1"), false);
    }
  } finally {
    if (installed) {
      if (original) {
        Object.defineProperty(globalThis, "localStorage", original);
      } else {
        delete globalThis.localStorage;
      }
    }
  }
});

test("非法课节 id 不写入任何内容", () => {
  const storage = memoryStorage();
  assert.equal(markStartLessonComplete("", storage), false);
  assert.equal(markStartLessonComplete(null, storage), false);
  assert.equal(markStartLessonComplete(42, storage), false);
  assert.equal(storage.map.has(START_PROGRESS_STORAGE_KEY), false);
});
