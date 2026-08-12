import assert from "node:assert/strict";
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

function evidence(result = "passed", lessonId = "t01-foundation") {
  const checks = result === "failed"
    ? [{ id: "foundation-contract", result: "failed" }]
    : [{ id: "foundation-contract", result: "passed" }];
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
      failed: "证据未通过，请根据本地检查结果恢复后重试。",
    }[result] ?? "部分证据已通过，仍有证据需要补齐。",
    evidence: checks,
  };
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
