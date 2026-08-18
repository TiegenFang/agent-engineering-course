/**
 * Deterministic, browser-only Memory lab.
 *
 * The fixture teaches a method for designing, writing, retrieving, updating,
 * and deleting controlled memory. It never calls a model, reads a file, or
 * reaches the network. The exported evidence contains stable enums only.
 */

/** @typedef {{id: string, sequence: number, result: "passed"|"failed", observations: Record<string, boolean>}} MemoryStage */
/** @typedef {{version: string, baselineId: string, memoryTypes: string[], contextModes: string[], stages: MemoryStage[], pollutionInjected: boolean, pollutionRecovered: boolean, lastObservation: string, status: "ready"|"warning"|"success"|"complete"}} MemorySession */

export const MEMORY_EXPERIMENT_VERSION = "1";
export const MEMORY_BASELINE_ID = "memory-ledger-v1";
export const MEMORY_STAGE_IDS = ["design", "write", "recall", "stale-update", "pollution", "delete"];
export const MEMORY_CHECK_IDS = [
  "purpose-defined",
  "owner-defined",
  "lifetime-defined",
  "deletion-defined",
  "memory-types-separated",
  "context-window-managed",
  "summary-retrieval-injection",
  "correct-recall",
  "stale-memory-corrected",
  "pollution-contained",
  "sensitive-excluded",
  "deletion-confirmed",
  "offline-deterministic",
];

const MEMORY_TYPES = ["short-term", "long-term", "external"];
const CONTEXT_MODES = ["window-budget", "summary", "retrieval", "injection"];
const STAGE_ACTIONS = {
  design: "design",
  write: "write",
  recall: "recall",
  update: "stale-update",
  inject: "inject-pollution",
  recover: "pollution",
  delete: "delete",
};

const STAGE_OBSERVATIONS = {
  design: ["purpose", "owner", "lifetime", "deletion", "types"],
  write: ["record_created", "metadata_complete", "sensitive_excluded"],
  recall: ["context_window", "summary", "retrieval", "injection", "correct_recall"],
  "stale-update": ["stale_detected", "replacement_confirmed", "old_not_retrieved"],
  pollution: ["untrusted_quarantined", "trusted_boundary_restored", "revalidated"],
  delete: ["deletion_requested", "deletion_confirmed", "record_absent"],
};

const COMPLETE_OBSERVATIONS = Object.fromEntries(
  Object.entries(STAGE_OBSERVATIONS).map(([stageId, keys]) => [
    stageId,
    Object.fromEntries(keys.map((key) => [key, true])),
  ]),
);

export class MemoryStateError extends Error {
  constructor(message) {
    super(message);
    this.name = "MemoryStateError";
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

/** @param {Record<string, boolean>} observations */
function stageResult(observations) {
  return Object.values(observations).every(Boolean) ? "passed" : "failed";
}

/** @param {MemorySession} session @param {string} stageId */
function completedStage(session, stageId) {
  return session.stages.find((stage) => stage.id === stageId) ?? null;
}

/** @param {MemorySession} session @param {string} stageId @param {string} message */
function requireStage(session, stageId, message) {
  if (!completedStage(session, stageId)) throw new MemoryStateError(message);
}

/** @returns {MemorySession} */
export function createMemorySession() {
  return {
    version: MEMORY_EXPERIMENT_VERSION,
    baselineId: MEMORY_BASELINE_ID,
    memoryTypes: [...MEMORY_TYPES],
    contextModes: [...CONTEXT_MODES],
    stages: [],
    pollutionInjected: false,
    pollutionRecovered: false,
    lastObservation: "先设计记录的目的、所有者、寿命和删除条件。",
    status: "ready",
  };
}

/** @param {MemorySession} session @returns {MemorySession} */
export function injectMemoryPollution(session) {
  requireStage(session, "stale-update", "先完成陈旧记忆更新，再注入污染。");
  if (completedStage(session, "pollution")) {
    throw new MemoryStateError("污染恢复已经完成；可重置后再次注入。");
  }
  if (session.pollutionInjected) return clone(session);
  return {
    ...clone(session),
    pollutionInjected: true,
    lastObservation: "已注入不可信备注：它试图把数据提升为外发指令；备注仍是数据，不是规则。",
    status: "warning",
  };
}

/** @param {MemorySession} session @param {string} action @returns {MemorySession} */
export function runMemoryAction(session, action) {
  const current = clone(session);
  if (!current || current.version !== MEMORY_EXPERIMENT_VERSION) {
    throw new MemoryStateError("Memory 实验状态版本不受支持。");
  }
  if (action === STAGE_ACTIONS.inject) return injectMemoryPollution(current);

  const stageId = action === STAGE_ACTIONS.update ? "stale-update" : action;
  if (!MEMORY_STAGE_IDS.includes(stageId)) throw new MemoryStateError("未知的 Memory 实验动作。");
  if (completedStage(current, stageId)) throw new MemoryStateError("该步骤已经完成；可重置后重新观察。");

  const expectedIndex = current.stages.length;
  if (MEMORY_STAGE_IDS[expectedIndex] !== stageId) {
    throw new MemoryStateError(`请按顺序完成步骤：${MEMORY_STAGE_IDS[expectedIndex]}。`);
  }
  if (stageId === "pollution" && !current.pollutionInjected) {
    throw new MemoryStateError("先点击“注入污染”，再执行隔离与恢复。");
  }

  const observations = clone(COMPLETE_OBSERVATIONS[stageId]);
  const stage = {
    id: stageId,
    sequence: expectedIndex + 1,
    result: stageResult(observations),
    observations,
  };
  const next = {
    ...current,
    stages: [...current.stages, stage],
    pollutionRecovered: stageId === "pollution" ? true : current.pollutionRecovered,
    lastObservation: {
      design: "设计完成：三种 Memory 类型都有明确目的、所有者、寿命和删除条件。",
      write: "写入完成：只写入合成记录，并在写入边界排除敏感信息。",
      recall: "回忆完成：先在上下文窗口预留预算，再摘要、检索并显式注入相关条目。",
      "stale-update": "更新完成：检测到 °F 陈旧记录，确认 °C 新规则后停止检索旧版本。",
      pollution: "恢复完成：不可信备注已隔离，规则边界恢复，并重新核验不外发约束。",
      delete: "删除完成：删除请求、确认和不再回忆三项证据均已记录。",
    }[stageId],
    status: stageId === "pollution" ? "success" : "ready",
  };
  if (next.stages.length === MEMORY_STAGE_IDS.length) next.status = "complete";
  return next;
}

/** @returns {MemorySession} */
export function resetMemorySession() {
  return createMemorySession();
}

/** @returns {MemorySession} */
export function runCompleteMemorySession() {
  let session = createMemorySession();
  for (const action of ["design", "write", "recall", "stale-update"]) {
    session = runMemoryAction(session, action);
  }
  session = injectMemoryPollution(session);
  session = runMemoryAction(session, "pollution");
  session = runMemoryAction(session, "delete");
  return session;
}

function checkResult(session, stageId, ...observationKeys) {
  const stage = completedStage(session, stageId);
  return stage && observationKeys.every((key) => stage.observations[key] === true)
    ? "passed"
    : "failed";
}

export function buildMemoryEvidence(session, { courseVersion, checkedOn } = {}) {
  const safeCourseVersion = typeof courseVersion === "string" && courseVersion.trim()
    ? courseVersion
    : "3.0.0";
  const checks = [
    { id: "purpose-defined", result: checkResult(session, "design", "purpose") },
    { id: "owner-defined", result: checkResult(session, "design", "owner") },
    { id: "lifetime-defined", result: checkResult(session, "design", "lifetime") },
    { id: "deletion-defined", result: checkResult(session, "design", "deletion") },
    { id: "memory-types-separated", result: session.memoryTypes.join(",") === MEMORY_TYPES.join(",") ? checkResult(session, "design", "types") : "failed" },
    { id: "context-window-managed", result: checkResult(session, "recall", "context_window") },
    { id: "summary-retrieval-injection", result: checkResult(session, "recall", "summary", "retrieval", "injection") },
    { id: "correct-recall", result: checkResult(session, "recall", "correct_recall") },
    { id: "stale-memory-corrected", result: checkResult(session, "stale-update", "stale_detected", "replacement_confirmed", "old_not_retrieved") },
    { id: "pollution-contained", result: checkResult(session, "pollution", "untrusted_quarantined", "trusted_boundary_restored", "revalidated") },
    { id: "sensitive-excluded", result: checkResult(session, "write", "sensitive_excluded") },
    { id: "deletion-confirmed", result: checkResult(session, "delete", "deletion_requested", "deletion_confirmed", "record_absent") },
    { id: "offline-deterministic", result: session.version === MEMORY_EXPERIMENT_VERSION ? "passed" : "failed" },
  ];
  const results = checks.map((check) => check.result);
  const result = results.every((item) => item === "passed") ? "passed" : results.every((item) => item === "failed") ? "failed" : "partial";
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: safeCourseVersion,
    lesson_id: "t16-memory",
    result,
    anonymous: true,
    checked_on: checkedOn ?? new Date().toISOString().slice(0, 10),
    summary: {
      passed: "所有必需证据均已通过。",
      partial: "部分证据已通过，仍有证据需要补齐。",
      failed: "证据未通过，请根据本地检查结果恢复后重试。",
      alternative: "检测到满足验收目标的替代实现。",
    }[result],
    evidence: checks,
    experiment: {
      version: MEMORY_EXPERIMENT_VERSION,
      baseline_id: MEMORY_BASELINE_ID,
      stages: clone(session.stages),
      memory_types: [...session.memoryTypes],
      context_modes: [...session.contextModes],
      pollution_injected: session.pollutionInjected,
      pollution_recovered: session.pollutionRecovered,
      model_calls: 0,
      network_calls: 0,
    },
  };
}

export function stageActionMap() {
  return { ...STAGE_ACTIONS };
}
