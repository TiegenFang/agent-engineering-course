import { spawnSync } from "node:child_process";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  EvidenceRecordError,
  emptyLearningRecord,
  clearLearningRecord,
  loadLearningRecord,
  mergeEvidence,
  parseLearningInput,
  saveLearningRecord,
  serializeLearningRecord,
} from "../src/lib/evidence-record.mjs";

const COURSE_VERSION = "0.1.0-foundation";
const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = resolve(siteRoot, "..");
const checkerRoot = join(workspaceRoot, "checker");

function evidence(result = "passed", lessonId = "t01-foundation") {
  const checksByResult = {
    passed: [
      { id: "course-version-lock", result: "passed" },
      { id: "foundation-contract", result: "passed" },
    ],
    partial: [
      { id: "course-version-lock", result: "passed" },
      { id: "foundation-contract", result: "failed" },
    ],
    failed: [
      { id: "course-version-lock", result: "failed" },
      { id: "foundation-contract", result: "failed" },
    ],
    alternative: [
      { id: "course-version-lock", result: "alternative" },
      { id: "foundation-contract", result: "passed" },
    ],
  };
  const checks = checksByResult[result];
  assert.ok(checks, `unknown fixture result: ${result}`);
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: COURSE_VERSION,
    lesson_id: lessonId,
    result,
    anonymous: true,
    checked_on: "2026-08-13",
    summary: {
      passed: "所有必需证据均已通过。",
      partial: "部分证据已通过，仍有证据需要补齐。",
      failed: "证据未通过，请根据本地检查结果恢复后重试。",
      alternative: "检测到满足验收目标的替代实现。",
    }[result],
    evidence: checks,
  };
}

function runPythonChecker(checks) {
  const temporaryRoot = mkdtempSync(join(tmpdir(), "agent-course-evidence-"));
  const fixturePath = join(temporaryRoot, "fixture.json");
  writeFileSync(
    fixturePath,
    JSON.stringify({
      lesson_id: "t01-foundation",
      checks,
      source_path: "C:\\Users\\Ada\\private.py",
      api_key: "sk-test-only",
      raw_data: { temperature: [1, 2, 3] },
    }),
    "utf8",
  );
  try {
    const result = spawnSync(
      process.env.PYTHON ?? "python",
      [
        "-m",
        "course_check",
        "check",
        "t01-foundation",
        "--root",
        "..",
        "--evidence-file",
        fixturePath,
        "--json",
      ],
      {
        cwd: checkerRoot,
        encoding: "utf8",
        env: {
          ...process.env,
          PYTHONIOENCODING: "utf-8",
          PYTHONPATH: checkerRoot,
        },
      },
    );
    assert.equal(result.error, undefined, result.error?.message);
    assert.equal(result.status, 0, result.stderr);
    return result.stdout;
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
}

test("学员可以导入匿名 checker 结果并忽略未知字段", () => {
  const input = { ...evidence(), future_field: "ignored" };
  input.evidence[0].future_detail = "ignored";

  const record = parseLearningInput(input, COURSE_VERSION);

  assert.equal(record.contract, "agent-engineering-course/learning-record");
  assert.equal(record.course_version, COURSE_VERSION);
  assert.equal(record.results.length, 1);
  assert.equal(record.results[0].lesson_id, "t01-foundation");
  assert.equal("future_field" in record, false);
  assert.equal("future_detail" in record.results[0].evidence[0], false);
});

test("网页明确拒绝不兼容课程版本", () => {
  assert.throws(
    () => parseLearningInput({ ...evidence(), course_version: "0.2.0" }, COURSE_VERSION),
    (error) => error instanceof EvidenceRecordError
      && error.code === "incompatible-course-version",
  );
});

test("网页接受合法的部分完成和替代实现结果", () => {
  const partial = parseLearningInput(evidence("partial"), COURSE_VERSION);
  const alternative = parseLearningInput(evidence("alternative"), COURSE_VERSION);

  assert.equal(partial.results[0].result, "partial");
  assert.equal(alternative.results[0].result, "alternative");
});

test("本地记录可以合并、覆盖同一课节并导出后重新导入", () => {
  let record = emptyLearningRecord(COURSE_VERSION);
  record = mergeEvidence(record, parseLearningInput(evidence(), COURSE_VERSION));
  record = mergeEvidence(
    record,
    parseLearningInput(evidence("failed", "t02-instructions"), COURSE_VERSION),
  );
  record = mergeEvidence(record, parseLearningInput(evidence("failed"), COURSE_VERSION));

  assert.equal(record.results.length, 2);
  assert.equal(record.results.find((item) => item.lesson_id === "t01-foundation").result, "failed");

  const exported = serializeLearningRecord(record);
  const imported = parseLearningInput(JSON.parse(exported), COURSE_VERSION);
  assert.deepEqual(imported, record);
});

test("本地导出不携带路径、密钥或未知原始数据", () => {
  const input = evidence();
  input.secret = "sk-test-only";
  input.absolute_path = "C:\\Users\\Ada\\notes.txt";
  input.raw_data = { temperature: [1, 2, 3] };

  const exported = serializeLearningRecord(parseLearningInput(input, COURSE_VERSION));

  assert.equal(exported.includes("sk-test-only"), false);
  assert.equal(exported.includes("C:\\\\Users"), false);
  assert.equal(exported.includes("temperature"), false);
});

test("localStorage 适配器可以持久化、恢复和清除本地记录", () => {
  const values = new Map();
  const storage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
  const key = "agent-engineering-course:learning-record:0.1.0-foundation";
  const original = mergeEvidence(
    emptyLearningRecord(COURSE_VERSION),
    parseLearningInput(evidence(), COURSE_VERSION),
  );

  saveLearningRecord(storage, key, original);
  assert.deepEqual(loadLearningRecord(storage, key, COURSE_VERSION), original);
  clearLearningRecord(storage, key);
  assert.deepEqual(loadLearningRecord(storage, key, COURSE_VERSION), emptyLearningRecord(COURSE_VERSION));
});

test("Python checker 的原样 JSON 可导入网页并覆盖四种结果状态", () => {
  const cases = [
    ["passed", evidence("passed").evidence],
    ["partial", evidence("partial").evidence],
    ["failed", evidence("failed").evidence],
    ["alternative", evidence("alternative").evidence],
  ];

  for (const [expectedResult, checks] of cases) {
    const checkerJson = runPythonChecker(checks);
    const record = parseLearningInput(checkerJson, COURSE_VERSION);

    assert.equal(record.results[0].result, expectedResult);
    assert.equal(record.results[0].course_version, COURSE_VERSION);
    for (const forbidden of [
      "C:\\Users\\Ada\\private.py",
      "sk-test-only",
      "temperature",
    ]) {
      assert.equal(checkerJson.includes(forbidden), false, `leaked ${forbidden}`);
      assert.equal(serializeLearningRecord(record).includes(forbidden), false, `persisted ${forbidden}`);
    }
  }
});
