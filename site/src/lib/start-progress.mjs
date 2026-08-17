/**
 * Shared browser-side progress store for the on-ramp chapter (W1-W4).
 *
 * Every on-ramp component reads and writes lesson completion through this
 * module so the storage key and the record shape live in exactly one place.
 * The record is a plain `{ lessonId: boolean }` map stored under a single
 * localStorage key, and it stays backward compatible with entries written by
 * earlier course versions.  Storage failures (private mode, storage blocked,
 * corrupt payloads) degrade silently: no exported call ever throws.
 */

export const START_PROGRESS_STORAGE_KEY = "course-start-progress";

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
