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
