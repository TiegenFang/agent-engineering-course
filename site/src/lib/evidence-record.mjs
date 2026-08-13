/**
 * Browser-side contract for importing checker evidence.
 *
 * The checker document is intentionally copied into a smaller learning-record
 * envelope.  Every import is canonicalized first, so unknown future fields
 * cannot become persistent user data and the website never needs a server.
 */

export const EVIDENCE_CONTRACT = "agent-engineering-course/evidence";
export const LEARNING_RECORD_CONTRACT = "agent-engineering-course/learning-record";
export const CONTRACT_VERSION = "1";

const CHECK_RESULTS = new Set(["passed", "failed", "alternative"]);
const DOCUMENT_RESULTS = new Set(["passed", "partial", "failed", "alternative"]);
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const SUMMARY_BY_RESULT = Object.freeze({
  passed: "所有必需证据均已通过。",
  partial: "部分证据已通过，仍有证据需要补齐。",
  failed: "证据未通过，请根据本地检查结果恢复后重试。",
  alternative: "检测到满足验收目标的替代实现。",
});

export class EvidenceRecordError extends Error {
  constructor(message, code = "invalid-evidence") {
    super(message);
    this.name = "EvidenceRecordError";
    this.code = code;
  }
}

function fail(message, code = "invalid-evidence") {
  throw new EvidenceRecordError(message, code);
}

function objectValue(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail(`${label} 必须是对象`);
  }
  return value;
}

function safeIdentifier(value, label) {
  if (typeof value !== "string" || !IDENTIFIER.test(value)) {
    fail(`${label} 不是安全标识符`);
  }
  return value;
}

function safeDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    fail("checked_on 必须是 YYYY-MM-DD");
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== value) {
    fail("checked_on 必须是有效日期");
  }
  return value;
}

function checkResult(value, label) {
  if (typeof value !== "string" || !CHECK_RESULTS.has(value)) {
    fail(`${label} 不是受支持的证据结果`);
  }
  return value;
}

function documentResult(value) {
  if (typeof value !== "string" || !DOCUMENT_RESULTS.has(value)) {
    fail("result 不是受支持的课程结果");
  }
  return value;
}

function classifyChecks(results) {
  if (results.length === 0) {
    fail("至少需要一条证据");
  }
  if (results.every((result) => result === "passed")) return "passed";
  if (results.every((result) => result === "failed")) return "failed";
  if (
    results.every((result) => result === "passed" || result === "alternative")
    && results.some((result) => result === "alternative")
  ) {
    return "alternative";
  }
  return "partial";
}

function canonicalEvidence(value, expectedCourseVersion) {
  const input = objectValue(value, "证据文档");
  if (input.contract !== EVIDENCE_CONTRACT) {
    fail("不是课程检查器证据文档", "unsupported-contract");
  }
  if (input.contract_version !== CONTRACT_VERSION) {
    fail("证据契约版本不受支持", "unsupported-contract-version");
  }
  if (input.course_version !== expectedCourseVersion) {
    fail("证据来自不兼容的课程版本", "incompatible-course-version");
  }
  if (input.anonymous !== true) {
    fail("证据文档必须标记为匿名");
  }

  const courseVersion = safeIdentifier(input.course_version, "course_version");
  const lessonId = safeIdentifier(input.lesson_id, "lesson_id");
  const result = documentResult(input.result);
  const checkedOn = safeDate(input.checked_on);
  if (input.summary !== SUMMARY_BY_RESULT[result]) {
    fail("证据摘要与结果不一致");
  }
  if (!Array.isArray(input.evidence) || input.evidence.length === 0) {
    fail("证据列表不能为空");
  }

  const seen = new Set();
  const evidence = input.evidence.map((item, index) => {
    const check = objectValue(item, `证据 ${index}`);
    const id = safeIdentifier(check.id, `证据 ${index}.id`);
    if (seen.has(id)) fail(`证据 ID 重复: ${id}`);
    seen.add(id);
    return { id, result: checkResult(check.result, `证据 ${id}.result`) };
  });
  if (classifyChecks(evidence.map((item) => item.result)) !== result) {
    fail("证据列表与课程结果不一致");
  }

  return {
    contract: EVIDENCE_CONTRACT,
    contract_version: CONTRACT_VERSION,
    course_version: courseVersion,
    lesson_id: lessonId,
    result,
    anonymous: true,
    checked_on: checkedOn,
    summary: SUMMARY_BY_RESULT[result],
    evidence,
  };
}

function canonicalRecord(value, expectedCourseVersion) {
  const input = objectValue(value, "学习记录");
  if (input.contract !== LEARNING_RECORD_CONTRACT) {
    fail("不是课程学习记录", "unsupported-contract");
  }
  if (input.contract_version !== CONTRACT_VERSION) {
    fail("学习记录契约版本不受支持", "unsupported-contract-version");
  }
  if (input.course_version !== expectedCourseVersion) {
    fail("学习记录来自不兼容的课程版本", "incompatible-course-version");
  }
  safeIdentifier(input.course_version, "course_version");
  if (!Array.isArray(input.results)) fail("学习记录 results 必须是数组");

  const results = [];
  const seen = new Set();
  for (const item of input.results) {
    const evidence = canonicalEvidence(item, expectedCourseVersion);
    if (seen.has(evidence.lesson_id)) {
      fail(`学习记录课节重复: ${evidence.lesson_id}`);
    }
    seen.add(evidence.lesson_id);
    results.push(evidence);
  }
  return {
    contract: LEARNING_RECORD_CONTRACT,
    contract_version: CONTRACT_VERSION,
    course_version: expectedCourseVersion,
    results,
  };
}

/** Return an empty, version-pinned local record. */
export function emptyLearningRecord(courseVersion) {
  safeIdentifier(courseVersion, "course_version");
  return {
    contract: LEARNING_RECORD_CONTRACT,
    contract_version: CONTRACT_VERSION,
    course_version: courseVersion,
    results: [],
  };
}

/** Parse either one checker result or a previously exported learning record. */
export function parseLearningInput(input, expectedCourseVersion) {
  safeIdentifier(expectedCourseVersion, "course_version");
  let value = input;
  if (typeof input === "string") {
    try {
      value = JSON.parse(input);
    } catch (error) {
      fail(`无法解析 JSON: ${error instanceof Error ? error.message : "格式错误"}`, "invalid-json");
    }
  }
  const object = objectValue(value, "导入内容");
  if (object.contract === EVIDENCE_CONTRACT) {
    const evidence = canonicalEvidence(object, expectedCourseVersion);
    return {
      contract: LEARNING_RECORD_CONTRACT,
      contract_version: CONTRACT_VERSION,
      course_version: expectedCourseVersion,
      results: [evidence],
    };
  }
  if (object.contract === LEARNING_RECORD_CONTRACT) {
    return canonicalRecord(object, expectedCourseVersion);
  }
  fail("无法识别导入内容的契约", "unsupported-contract");
}

/** Merge one parsed import into local state, replacing the same lesson. */
export function mergeEvidence(existing, incoming) {
  const current = canonicalRecord(existing, existing.course_version);
  const addition = canonicalRecord(incoming, current.course_version);
  const byLesson = new Map(current.results.map((item) => [item.lesson_id, item]));
  for (const item of addition.results) byLesson.set(item.lesson_id, item);
  return {
    ...current,
    results: [...byLesson.values()].sort((left, right) => left.lesson_id.localeCompare(right.lesson_id)),
  };
}

/** Serialize only the canonical, anonymous learning-record fields. */
export function serializeLearningRecord(record) {
  const canonical = canonicalRecord(record, record.course_version);
  return `${JSON.stringify(canonical, null, 2)}\n`;
}

/** Load a version-pinned record from a storage-like browser adapter. */
export function loadLearningRecord(storage, key, courseVersion) {
  const saved = storage.getItem(key);
  return saved
    ? parseLearningInput(saved, courseVersion)
    : emptyLearningRecord(courseVersion);
}

/** Persist only canonical learning-record fields in a storage-like adapter. */
export function saveLearningRecord(storage, key, record) {
  storage.setItem(key, serializeLearningRecord(record));
}

/** Remove the user-requested local record from a storage-like adapter. */
export function clearLearningRecord(storage, key) {
  storage.removeItem(key);
}
