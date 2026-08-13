/**
 * Deterministic context recovery fixture for module 5B.
 *
 * The fixture models a small working set for the synthetic telemetry report
 * task.  It deliberately does not call a model, read a file, or use a real
 * product session.  The public evidence builder exports identifiers and
 * result states only; the explanatory text stays in the local simulator.
 */

export const CONTEXT_RECOVERY_LESSON_ID = "t15-context-recovery";
export const CONTEXT_RECOVERY_VERSION = "1";
export const CONTEXT_RECOVERY_BASELINE_ID = "telemetry-report-v1";

export const COMPRESSION_MODES = Object.freeze({
  FAITHFUL: "faithful",
  DISTORTED: "distorted",
  CONSTRAINT_OMITTED: "constraint-omitted",
});

export const POLLUTION_MODES = Object.freeze({
  CLEAN: "clean",
  POLLUTED: "polluted",
});

export const PREDICTION_OPTIONS = Object.freeze([
  "压缩后仍保留目标、约束和证据",
  "压缩会改变或遗漏至少一条约束",
  "历史会自动变成长期 Memory",
]);

export const CHECK_IDS = Object.freeze([
  "compression-compared",
  "distortion-detected",
  "constraint-omission-detected",
  "pollution-recovered",
  "handoff-complete",
  "layers-distinguished",
]);

// Compatibility aliases make the fixture easier to use from lesson tests
// without creating a second contract.  The canonical values above are what
// cross the checker/browser seam.
export const CONTEXT_RECOVERY_CHECK_IDS = CHECK_IDS;
export const T15_CHECK_IDS = CHECK_IDS;

const SUMMARY_BY_RESULT = Object.freeze({
  passed: "所有必需证据均已通过。",
  partial: "部分证据已通过，仍有证据需要补齐。",
  failed: "证据未通过，请根据本地检查结果恢复后重试。",
  alternative: "检测到满足验收目标的替代实现。",
});

const MODE_ALIASES = Object.freeze({
  faithful: COMPRESSION_MODES.FAITHFUL,
  exact: COMPRESSION_MODES.FAITHFUL,
  distorted: COMPRESSION_MODES.DISTORTED,
  distortion: COMPRESSION_MODES.DISTORTED,
  "compression-distortion": COMPRESSION_MODES.DISTORTED,
  omitted: COMPRESSION_MODES.CONSTRAINT_OMITTED,
  omission: COMPRESSION_MODES.CONSTRAINT_OMITTED,
  "constraint-omitted": COMPRESSION_MODES.CONSTRAINT_OMITTED,
  "constraint-omission": COMPRESSION_MODES.CONSTRAINT_OMITTED,
});

const POLLUTION_ALIASES = Object.freeze({
  clean: POLLUTION_MODES.CLEAN,
  none: POLLUTION_MODES.CLEAN,
  polluted: POLLUTION_MODES.POLLUTED,
  contamination: POLLUTION_MODES.POLLUTED,
  contaminated: POLLUTION_MODES.POLLUTED,
});

const BASE_CONTEXT = Object.freeze({
  goalId: "report-task",
  constraintIds: Object.freeze(["read-only", "no-network", "preserve-evidence"]),
  evidenceIds: Object.freeze(["input-checked", "summary-reviewable"]),
});

const LAYER_DEFINITIONS = Object.freeze([
  Object.freeze({
    id: "context",
    label: "上下文（Context）",
    owner: "当前任务",
    lifetime: "本轮工作集",
    rule: "只放当前决策需要的目标、约束、工具结果和证据。",
  }),
  Object.freeze({
    id: "history",
    label: "历史（History）",
    owner: "会话记录",
    lifetime: "可回看但不必全部装入工作集",
    rule: "记录发生过什么；历史不是当前约束，也不会自动获得指令权限。",
  }),
  Object.freeze({
    id: "memory",
    label: "Memory",
    owner: "长期存储策略",
    lifetime: "跨会话且有寿命",
    rule: "只有经过筛选、标注来源和寿命的知识才可保存；不是聊天全文。",
  }),
]);

const MODE_LABELS = Object.freeze({
  [COMPRESSION_MODES.FAITHFUL]: "保真压缩",
  [COMPRESSION_MODES.DISTORTED]: "压缩失真",
  [COMPRESSION_MODES.CONSTRAINT_OMITTED]: "约束遗漏",
});

const POLLUTION_FIXTURE_ID = "untrusted-note";

export class ContextRecoveryInputError extends Error {
  constructor(message, code = "invalid-input") {
    super(message);
    this.name = "ContextRecoveryInputError";
    this.code = code;
  }
}

export class ContextRecoveryStateError extends Error {
  constructor(message, code = "invalid-state") {
    super(message);
    this.name = "ContextRecoveryStateError";
    this.code = code;
  }
}

function requireObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new ContextRecoveryInputError(`${label} 必须是对象`);
  }
  return value;
}

function requireIdentifier(value, label) {
  if (typeof value !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(value)) {
    throw new ContextRecoveryInputError(`${label} 不是安全标识符`, "invalid-identifier");
  }
  return value;
}

function requireDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new ContextRecoveryInputError("checkedOn 必须是 YYYY-MM-DD", "invalid-date");
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== value) {
    throw new ContextRecoveryInputError("checkedOn 必须是有效日期", "invalid-date");
  }
  return value;
}

function normalizeMode(value) {
  const mode = MODE_ALIASES[value ?? COMPRESSION_MODES.FAITHFUL];
  if (!mode) throw new ContextRecoveryInputError("不支持的压缩模式", "invalid-compression-mode");
  return mode;
}

function normalizePollution(value) {
  const mode = POLLUTION_ALIASES[value ?? POLLUTION_MODES.CLEAN];
  if (!mode) throw new ContextRecoveryInputError("不支持的污染模式", "invalid-pollution-mode");
  return mode;
}

function normalizePrediction(value) {
  if (!PREDICTION_OPTIONS.includes(value)) {
    throw new ContextRecoveryStateError("请选择一个操作前预测", "invalid-prediction");
  }
  return value;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function expectedPrediction(mode) {
  return mode === COMPRESSION_MODES.FAITHFUL
    ? PREDICTION_OPTIONS[0]
    : PREDICTION_OPTIONS[1];
}

function buildBeforeState() {
  return {
    status: "passed",
    outcome: "report-ready",
    goal_id: BASE_CONTEXT.goalId,
    constraint_ids: [...BASE_CONTEXT.constraintIds],
    evidence_ids: [...BASE_CONTEXT.evidenceIds],
  };
}

function buildAfterState(mode) {
  const before = buildBeforeState();
  if (mode === COMPRESSION_MODES.FAITHFUL) {
    return {
      ...before,
      outcome: "faithful",
      retained_constraint_ids: [...before.constraint_ids],
      omitted_constraint_ids: [],
      changed_constraint_ids: [],
      evidence_ids: [...before.evidence_ids],
    };
  }
  if (mode === COMPRESSION_MODES.DISTORTED) {
    return {
      ...before,
      status: "failed",
      outcome: "distorted",
      retained_constraint_ids: ["read-only", "no-network"],
      omitted_constraint_ids: [],
      changed_constraint_ids: ["preserve-evidence"],
      evidence_ids: ["input-checked"],
    };
  }
  return {
    ...before,
    status: "failed",
    outcome: "constraint-omitted",
    retained_constraint_ids: ["read-only", "preserve-evidence"],
    omitted_constraint_ids: ["no-network"],
    changed_constraint_ids: [],
    evidence_ids: ["input-checked", "summary-reviewable"],
  };
}

function buildComparison(mode) {
  const normalizedMode = normalizeMode(mode);
  const before = buildBeforeState();
  const after = buildAfterState(normalizedMode);
  const distortionDetected = normalizedMode === COMPRESSION_MODES.DISTORTED
    && after.changed_constraint_ids.length > 0;
  const omissionDetected = normalizedMode === COMPRESSION_MODES.CONSTRAINT_OMITTED
    && after.omitted_constraint_ids.length > 0;
  return {
    version: CONTEXT_RECOVERY_VERSION,
    baseline_id: CONTEXT_RECOVERY_BASELINE_ID,
    mode: normalizedMode,
    mode_label: MODE_LABELS[normalizedMode],
    before,
    after,
    diagnostics: {
      before_after_observed: true,
      distortion_detected: distortionDetected,
      constraint_omission_detected: omissionDetected,
      constraints_preserved: normalizedMode === COMPRESSION_MODES.FAITHFUL,
    },
    difference: normalizedMode === COMPRESSION_MODES.FAITHFUL
      ? "压缩保留了目标、约束和证据。"
      : normalizedMode === COMPRESSION_MODES.DISTORTED
        ? "压缩改变了证据约束；必须回看压缩前的工作集。"
        : "压缩遗漏了不外发约束；不能把压缩结果直接当成完整任务合同。",
  };
}

function ensureSession(session) {
  if (
    session === null
    || typeof session !== "object"
    || session.lessonId !== CONTEXT_RECOVERY_LESSON_ID
    || session.version !== CONTEXT_RECOVERY_VERSION
    || !Array.isArray(session.comparisons)
  ) {
    throw new ContextRecoveryStateError("无效的上下文恢复实验 session", "invalid-session");
  }
  return session;
}

function currentInput(value = {}) {
  const input = requireObject(value, "实验输入");
  const compressionMode = normalizeMode(input.compressionMode ?? input.mode);
  const pollutionMode = normalizePollution(
    input.pollutionMode
      ?? input.contaminationMode
      ?? (input.polluted === true ? POLLUTION_MODES.POLLUTED : POLLUTION_MODES.CLEAN),
  );
  return { compressionMode, pollutionMode };
}

export function getLayerDefinitions() {
  return clone(LAYER_DEFINITIONS);
}

export function describeContextHistoryMemory() {
  return {
    version: CONTEXT_RECOVERY_VERSION,
    layers: getLayerDefinitions(),
    invariants: {
      context_is_current_working_set: true,
      history_is_record_not_instruction: true,
      memory_requires_owner_and_lifetime: true,
    },
  };
}

export function createContextRecoverySession(value = {}) {
  const input = currentInput(value);
  return {
    lessonId: CONTEXT_RECOVERY_LESSON_ID,
    version: CONTEXT_RECOVERY_VERSION,
    baselineId: CONTEXT_RECOVERY_BASELINE_ID,
    compressionMode: input.compressionMode,
    pollutionMode: input.pollutionMode,
    predictions: [],
    status: "predicting",
    comparisons: [],
    pollution: {
      mode: input.pollutionMode,
      injected: false,
      observed: false,
      recovered: false,
    },
    handoff: null,
    layers: describeContextHistoryMemory().invariants,
  };
}

/** Select a new fixture while retaining previous comparisons for evidence. */
export function selectContextRecoveryInput(session, value = {}) {
  const current = ensureSession(session);
  const input = currentInput({
    compressionMode: value.compressionMode ?? value.mode ?? current.compressionMode,
    pollutionMode: value.pollutionMode
      ?? value.contaminationMode
      ?? (value.polluted === undefined ? current.pollutionMode : value.polluted ? "polluted" : "clean"),
  });
  return {
    ...current,
    compressionMode: input.compressionMode,
    pollutionMode: input.pollutionMode,
    pollution: {
      ...current.pollution,
      mode: input.pollutionMode,
    },
    status: "predicting",
  };
}

export function submitContextPrediction(session, prediction) {
  const current = ensureSession(session);
  const selected = normalizePrediction(prediction);
  return {
    ...current,
    predictions: [
      ...current.predictions,
      {
        mode: current.compressionMode,
        prediction: selected,
        correct: selected === expectedPrediction(current.compressionMode),
      },
    ],
    status: "ready",
  };
}

/** Compare a single compression mode without invoking a model. */
export function runCompressionComparison(session, value = {}) {
  const current = ensureSession(session);
  if (current.status !== "ready") {
    throw new ContextRecoveryStateError("请先记录当前压缩模式的操作前预测", "prediction-required");
  }
  const mode = normalizeMode(value.compressionMode ?? value.mode ?? current.compressionMode);
  if (!current.predictions.some((item) => item.mode === mode)) {
    throw new ContextRecoveryStateError("请先记录当前压缩模式的操作前预测", "prediction-required");
  }
  const comparison = buildComparison(mode);
  const comparisons = current.comparisons.filter((item) => item.mode !== mode);
  comparisons.push(comparison);
  return {
    ...current,
    compressionMode: mode,
    comparisons,
    status: "comparison-complete",
  };
}

export const compareCompression = (mode) => buildComparison(mode);
export const buildCompressionComparison = (mode) => buildComparison(mode);

/** Inject the fixed untrusted note so the learner can observe contamination. */
export function runPollutedTask(session) {
  const current = ensureSession(session);
  if (current.status === "predicting" || current.status === "ready") {
    throw new ContextRecoveryStateError("先完成一次压缩前后对照，再注入污染任务", "comparison-required");
  }
  return {
    ...current,
    pollutionMode: POLLUTION_MODES.POLLUTED,
    pollution: {
      mode: POLLUTION_MODES.POLLUTED,
      fixture_id: POLLUTION_FIXTURE_ID,
      injected: true,
      observed: true,
      recovered: false,
      outcome: "polluted",
    },
    status: "polluted",
  };
}

export const injectContextPollution = runPollutedTask;
export const injectPollution = runPollutedTask;

/** Restore the canonical working set after the untrusted note is quarantined. */
export function recoverPollutedTask(session) {
  const current = ensureSession(session);
  if (!current.pollution?.injected) {
    throw new ContextRecoveryStateError("还没有可恢复的污染任务", "pollution-required");
  }
  return {
    ...current,
    pollution: {
      ...current.pollution,
      recovered: true,
      outcome: "recovered",
      restored_constraint_ids: [...BASE_CONTEXT.constraintIds],
      recovery_steps: ["detect", "quarantine", "restore", "revalidate"],
    },
    status: "recovered",
  };
}

export const recoverContextPollution = recoverPollutedTask;
export const recoverContaminatedTask = recoverPollutedTask;

function handoffFieldsComplete(handoff) {
  return Boolean(
    handoff
      && typeof handoff.goal === "string"
      && handoff.goal.length > 0
      && typeof handoff.status === "string"
      && handoff.status === "ready-for-next-session"
      && Array.isArray(handoff.evidence)
      && handoff.evidence.length > 0
      && Array.isArray(handoff.risks)
      && handoff.risks.length > 0
      && Array.isArray(handoff.next_steps)
      && handoff.next_steps.length > 0,
  );
}

export function buildHandoffPackage(session) {
  const current = ensureSession(session);
  const faithful = current.comparisons.some((item) => item.mode === COMPRESSION_MODES.FAITHFUL);
  const distorted = current.comparisons.some((item) => item.mode === COMPRESSION_MODES.DISTORTED);
  const omitted = current.comparisons.some((item) => item.mode === COMPRESSION_MODES.CONSTRAINT_OMITTED);
  const recovered = current.pollution?.recovered === true;
  const ready = faithful && distorted && omitted && recovered;
  const handoff = {
    version: CONTEXT_RECOVERY_VERSION,
    goal: BASE_CONTEXT.goalId,
    status: ready ? "ready-for-next-session" : "blocked",
    evidence: [
      "compression-before-after",
      ...(distorted ? ["compression-distortion-diagnosed"] : []),
      ...(omitted ? ["constraint-omission-diagnosed"] : []),
      ...(recovered ? ["pollution-recovered"] : []),
    ],
    risks: [
      "compressed-context-may-be-lossy",
      "history-is-not-a-current-constraint",
      "memory-promotion-requires-owner-and-lifetime",
    ],
    next_steps: ready
      ? ["重新载入本交接包", "核对三条约束", "从本地证据继续报告"]
      : ["完成保真、失真和约束遗漏三种对照", "恢复污染任务", "再次生成交接包"],
    layers: ["context", "history", "memory"],
  };
  return handoff;
}

export const createHandoffPackage = buildHandoffPackage;

/** Attach the current handoff to a session without changing prior evidence. */
export function generateHandoffPackage(session) {
  const current = ensureSession(session);
  return {
    ...current,
    handoff: buildHandoffPackage(current),
    status: "handoff-generated",
  };
}

export const attachHandoffPackage = generateHandoffPackage;

export function importHandoffPackage(value) {
  const handoff = requireObject(value, "交接包");
  if (handoff.version !== CONTEXT_RECOVERY_VERSION) {
    throw new ContextRecoveryInputError("不支持的交接包版本", "unsupported-handoff-version");
  }
  if (!handoffFieldsComplete(handoff)) {
    throw new ContextRecoveryInputError("交接包必须包含目标、状态、证据、风险和下一步", "incomplete-handoff");
  }
  if (JSON.stringify(handoff.layers ?? []) !== JSON.stringify(["context", "history", "memory"])) {
    throw new ContextRecoveryInputError("交接包必须区分上下文、历史和 Memory", "layers-missing");
  }
  return {
    version: CONTEXT_RECOVERY_VERSION,
    goal: handoff.goal,
    status: handoff.status,
    evidence: [...handoff.evidence],
    risks: [...handoff.risks],
    next_steps: [...handoff.next_steps],
    layers: ["context", "history", "memory"],
  };
}

export const resumeFromHandoff = importHandoffPackage;

function buildLayerEvidence() {
  return {
    context: "current-working-set",
    history: "record-only",
    memory: "owned-and-expiring",
  };
}

function classify(results) {
  if (results.every((result) => result === "passed")) return "passed";
  if (results.every((result) => result === "failed")) return "failed";
  if (
    results.every((result) => result === "passed" || result === "alternative")
    && results.some((result) => result === "alternative")
  ) return "alternative";
  return "partial";
}

function evidenceChecks(session) {
  const distorted = session.comparisons.find((item) => item.mode === COMPRESSION_MODES.DISTORTED);
  const omitted = session.comparisons.find((item) => item.mode === COMPRESSION_MODES.CONSTRAINT_OMITTED);
  const handoff = session.handoff;
  return [
    {
      id: "compression-compared",
      result: session.comparisons.length > 0 ? "passed" : "failed",
    },
    {
      id: "distortion-detected",
      result: distorted?.diagnostics.distortion_detected === true ? "passed" : "failed",
    },
    {
      id: "constraint-omission-detected",
      result: omitted?.diagnostics.constraint_omission_detected === true ? "passed" : "failed",
    },
    {
      id: "pollution-recovered",
      result: session.pollution?.recovered === true ? "passed" : "failed",
    },
    {
      id: "handoff-complete",
      result: handoffFieldsComplete(handoff) ? "passed" : "failed",
    },
    {
      id: "layers-distinguished",
      result: session.layers?.context_is_current_working_set
        && session.layers?.history_is_record_not_instruction
        && session.layers?.memory_requires_owner_and_lifetime
        ? "passed"
        : "failed",
    },
  ];
}

/** Build the anonymous browser/checker interchange document. */
export function buildContextRecoveryEvidence(session, options = {}) {
  const current = ensureSession(session);
  const courseVersion = requireIdentifier(options.courseVersion, "courseVersion");
  const checkedOn = requireDate(options.checkedOn ?? new Date().toISOString().slice(0, 10));
  const checks = evidenceChecks(current);
  const result = classify(checks.map((check) => check.result));
  const handoff = current.handoff ?? {
    ...buildHandoffPackage(current),
    status: "blocked",
    evidence: [],
    next_steps: ["完成实验并生成交接包"],
  };
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: courseVersion,
    lesson_id: CONTEXT_RECOVERY_LESSON_ID,
    result,
    anonymous: true,
    checked_on: checkedOn,
    summary: SUMMARY_BY_RESULT[result],
    evidence: checks,
    experiment: {
      version: CONTEXT_RECOVERY_VERSION,
      baseline_id: CONTEXT_RECOVERY_BASELINE_ID,
      compression_modes: current.comparisons.map((item) => item.mode),
      comparisons: current.comparisons.map((item) => ({
        mode: item.mode,
        before_outcome: item.before.outcome,
        after_outcome: item.after.outcome,
        distortion_detected: item.diagnostics.distortion_detected,
        constraint_omission_detected: item.diagnostics.constraint_omission_detected,
      })),
      pollution: {
        injected: current.pollution?.injected === true,
        observed: current.pollution?.observed === true,
        recovered: current.pollution?.recovered === true,
        outcome: current.pollution?.outcome ?? "not-run",
      },
      handoff: {
        goal: handoff.goal,
        status: handoff.status,
        evidence: [...handoff.evidence],
        risks: [...handoff.risks],
        next_steps: [...handoff.next_steps],
      },
      layers: buildLayerEvidence(),
    },
  };
}

export const buildRecoveryEvidence = buildContextRecoveryEvidence;

export function describeContextRecoverySession(session) {
  const current = ensureSession(session);
  const latest = current.comparisons.at(-1);
  const handoff = current.handoff ?? buildHandoffPackage(current);
  return {
    status: current.status,
    latestMode: latest?.mode ?? null,
    latestOutcome: latest?.after.outcome ?? null,
    compressionCount: current.comparisons.length,
    pollution: current.pollution?.outcome ?? "not-run",
    handoffStatus: handoff.status,
    evidence: evidenceChecks(current),
  };
}
