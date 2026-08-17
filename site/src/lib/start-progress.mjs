/**
 * Shared browser-side progress store for the on-ramp chapter (W1-W4).
 *
 * Every on-ramp component reads and writes lesson completion through this
 * module so the storage key and the record shape live in exactly one place.
 * The record is a plain `{ lessonId: boolean }` map stored under a single
 * localStorage key, and it stays backward compatible with entries written by
 * earlier course versions.  Storage failures (private mode, storage blocked,
 * corrupt payloads) degrade silently: no exported call ever throws.
 *
 * V3-3 adds the anonymous call summary: when a real BYO-key call succeeds,
 * W3 persists `{ provider, model, inputTokens, outputTokens, elapsedMs, at }`
 * under a separate key.  The summary is strictly whitelisted to those six
 * fields so API keys and message bodies can never leak into it.
 *
 * V3-7 adds portability on top of the same keys: the on-ramp progress plus
 * the summary can be exported into one versioned JSON envelope, imported in
 * another browser (same course version only), and cleared on demand.  The
 * export whitelist is identical to the storage whitelist, and every portability
 * call degrades silently instead of throwing.
 */

export const START_PROGRESS_STORAGE_KEY = "course-start-progress";

export const START_CALL_SUMMARY_STORAGE_KEY = "course-start-call-summary";

const getStorage = () => {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
};

const parseRecord = (raw) => {
  if (typeof raw !== "string" || raw.trim() === "") return {};
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return {};
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return {};
  const record = {};
  for (const [lessonId, completed] of Object.entries(parsed)) {
    if (typeof completed === "boolean") {
      record[lessonId] = completed;
    }
  }
  return record;
};

/**
 * Read the on-ramp progress map.  Returns `{}` when storage is unavailable,
 * the payload is missing, or the payload is corrupt.
 */
export function readStartProgress(storage = getStorage()) {
  if (!storage) return {};
  try {
    return parseRecord(storage.getItem(START_PROGRESS_STORAGE_KEY));
  } catch {
    return {};
  }
}

/**
 * Mark one on-ramp lesson as completed, merging into the existing record so
 * progress from other lessons survives.  Returns whether the merged record
 * was actually persisted; `false` means storage was unavailable and the call
 * degraded silently (the caller's in-page feedback still applies).
 */
export function markStartLessonComplete(lessonId, storage = getStorage()) {
  if (typeof lessonId !== "string" || lessonId === "") return false;
  if (!storage) return false;
  try {
    const record = parseRecord(storage.getItem(START_PROGRESS_STORAGE_KEY));
    record[lessonId] = true;
    storage.setItem(START_PROGRESS_STORAGE_KEY, JSON.stringify(record));
    return true;
  } catch {
    return false;
  }
}

/** Summary fields kept in localStorage; anything else passed by a caller is dropped. */
const SUMMARY_STRING_LIMITS = { provider: 64, model: 200 };

const toNonNegativeInt = (value) => {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.round(parsed);
};

/**
 * Build the sanitized summary record or `null` when the input does not match
 * the anonymous shape.  Only the six whitelisted fields survive; key material,
 * message bodies, and any other extra properties are silently discarded.
 */
const sanitizeStartCallSummary = (summary) => {
  if (summary === null || typeof summary !== "object" || Array.isArray(summary)) return null;
  const provider = typeof summary.provider === "string" ? summary.provider.trim() : "";
  const model = typeof summary.model === "string" ? summary.model.trim() : "";
  if (provider === "" || model === "") return null;
  if (provider.length > SUMMARY_STRING_LIMITS.provider) return null;
  if (model.length > SUMMARY_STRING_LIMITS.model) return null;
  const inputTokens = toNonNegativeInt(summary.inputTokens);
  const outputTokens = toNonNegativeInt(summary.outputTokens);
  const elapsedMs = toNonNegativeInt(summary.elapsedMs);
  const at = toNonNegativeInt(summary.at);
  if (inputTokens === null || outputTokens === null || elapsedMs === null || at === null || at === 0) return null;
  return { provider, model, inputTokens, outputTokens, elapsedMs, at };
};

/**
 * Read the latest anonymous call summary written by the W3 BYO-key experiment,
 * or `null` when storage is unavailable, missing, or corrupt.  The returned
 * object never contains a key or message body.
 */
export function readStartCallSummary(storage = getStorage()) {
  if (!storage) return null;
  let raw;
  try {
    raw = storage.getItem(START_CALL_SUMMARY_STORAGE_KEY);
  } catch {
    return null;
  }
  if (typeof raw !== "string" || raw.trim() === "") return null;
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  return sanitizeStartCallSummary(parsed);
}

/**
 * Persist the anonymous summary of one successful real call
 * (`{ provider, model, inputTokens, outputTokens, elapsedMs, at }`).
 * The payload is whitelisted to exactly those fields, so callers cannot
 * persist secrets or message content even by accident.  Returns whether the
 * summary was actually persisted; `false` means the input was malformed or
 * storage was unavailable, and the call degrades silently.
 */
export function recordStartCallSummary(summary, storage = getStorage()) {
  const sanitized = sanitizeStartCallSummary(summary);
  if (!sanitized || !storage) return false;
  try {
    storage.setItem(START_CALL_SUMMARY_STORAGE_KEY, JSON.stringify(sanitized));
    return true;
  } catch {
    return false;
  }
}

/*
 * ---------------------------------------------------------------------------
 * V3-7 portability: export / import / clear for the on-ramp chapter.
 *
 * The export file is a versioned envelope that carries only (1) the lesson
 * completion booleans and (2) the anonymous call summary.  It is the same
 * privacy whitelist as localStorage: no keys, no message bodies, no personal
 * data.  Imports are validated against the current course version exactly
 * like checker evidence (`evidence-record.mjs`): a mismatched version is
 * rejected with `incompatible-course-version` and storage stays untouched.
 * ---------------------------------------------------------------------------
 */

/** Contract marker written into every on-ramp progress export. */
export const START_PROGRESS_EXPORT_CONTRACT = "agent-engineering-course/start-progress";

/** Version of the export envelope shape; bumped on breaking changes. */
export const START_PROGRESS_EXPORT_CONTRACT_VERSION = "1";

/** Download filename used by the homepage panel. */
export const START_PROGRESS_EXPORT_FILENAME = "agent-engineering-course-start-progress.json";

/** Guard rails so a hostile file cannot flood localStorage with entries. */
const EXPORT_LESSON_ID_LIMIT = 64;
const EXPORT_LESSON_COUNT_LIMIT = 64;

/** Error thrown by `parseStartProgressImport`; `code` explains the failure. */
export class StartProgressPortabilityError extends Error {
  /**
   * @param {string} message
   * @param {string} code
   */
  constructor(message, code = "invalid-import") {
    super(message);
    this.name = "StartProgressPortabilityError";
    this.code = code;
  }
}

const portabilityFail = (message, code) => {
  throw new StartProgressPortabilityError(message, code);
};

/**
 * Build the portable export payload from local storage.
 * Returns `{ contract, contract_version, course_version, lessons, call_summary }`;
 * `lessons` is `{}` and `call_summary` is `null` when storage is unavailable,
 * missing, or corrupt (silent degradation, same as every reader above).
 */
export function buildStartProgressExport(courseVersion, storage = getStorage()) {
  const lessons = readStartProgress(storage);
  const callSummary = readStartCallSummary(storage);
  return {
    contract: START_PROGRESS_EXPORT_CONTRACT,
    contract_version: START_PROGRESS_EXPORT_CONTRACT_VERSION,
    course_version: courseVersion,
    lessons,
    call_summary: callSummary,
  };
}

/**
 * Parse and validate an imported on-ramp progress file (string or pre-parsed
 * object).  Returns `{ lessons, callSummary }` where `lessons` keeps only
 * `{ lessonId: boolean }` entries and `callSummary` is either the sanitized
 * six-field summary or `null`.  Throws {@link StartProgressPortabilityError}
 * with codes `invalid-json`, `unsupported-contract`,
 * `unsupported-contract-version`, `incompatible-course-version`,
 * `invalid-import`, or `invalid-call-summary`; storage is never touched here.
 */
export function parseStartProgressImport(input, expectedCourseVersion) {
  let value = input;
  if (typeof value === "string") {
    try {
      value = JSON.parse(value);
    } catch (error) {
      portabilityFail(
        `无法解析 JSON: ${error instanceof Error ? error.message : "格式错误"}`,
        "invalid-json",
      );
    }
  }
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    portabilityFail("导入内容必须是对象", "invalid-import");
  }
  if (value.contract !== START_PROGRESS_EXPORT_CONTRACT) {
    portabilityFail("不是课程起步章进度文件", "unsupported-contract");
  }
  if (value.contract_version !== START_PROGRESS_EXPORT_CONTRACT_VERSION) {
    portabilityFail("进度文件契约版本不受支持", "unsupported-contract-version");
  }
  if (value.course_version !== expectedCourseVersion) {
    portabilityFail("进度文件来自不兼容的课程版本", "incompatible-course-version");
  }
  const rawLessons = value.lessons;
  if (rawLessons === null || typeof rawLessons !== "object" || Array.isArray(rawLessons)) {
    portabilityFail("lessons 必须是 { 课节ID: 布尔值 } 对象", "invalid-import");
  }
  const entries = Object.entries(rawLessons);
  if (entries.length > EXPORT_LESSON_COUNT_LIMIT) {
    portabilityFail(`进度文件包含超过 ${EXPORT_LESSON_COUNT_LIMIT} 条课节记录`, "invalid-import");
  }
  const lessons = {};
  for (const [lessonId, completed] of entries) {
    if (typeof completed !== "boolean") continue;
    if (lessonId === "" || lessonId.length > EXPORT_LESSON_ID_LIMIT) continue;
    lessons[lessonId] = completed;
  }
  let callSummary = null;
  if (value.call_summary !== null && value.call_summary !== undefined) {
    callSummary = sanitizeStartCallSummary(value.call_summary);
    if (!callSummary) {
      portabilityFail("匿名调用摘要字段不符合白名单形状", "invalid-call-summary");
    }
  }
  return { lessons, callSummary };
}

/**
 * Restore a parsed import into local storage, overwriting the on-ramp
 * progress record and the anonymous summary so the round trip through
 * export → clear → import is exact.  Returns whether both writes were
 * persisted; `false` means storage was unavailable (silent degradation).
 */
export function restoreStartProgress(parsed, storage = getStorage()) {
  if (!parsed || typeof parsed !== "object") return false;
  if (!storage) return false;
  try {
    storage.setItem(START_PROGRESS_STORAGE_KEY, JSON.stringify(parsed.lessons));
    if (parsed.callSummary) {
      storage.setItem(START_CALL_SUMMARY_STORAGE_KEY, JSON.stringify(parsed.callSummary));
    } else {
      storage.removeItem(START_CALL_SUMMARY_STORAGE_KEY);
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Remove the on-ramp progress record and the anonymous call summary from
 * local storage (the user-confirmed "clear my on-ramp progress" action).
 * Returns whether the removal was persisted.
 */
export function clearStartProgress(storage = getStorage()) {
  if (!storage) return false;
  try {
    storage.removeItem(START_PROGRESS_STORAGE_KEY);
    storage.removeItem(START_CALL_SUMMARY_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}
