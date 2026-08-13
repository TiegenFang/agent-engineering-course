import { parseLearningInput } from "./evidence-record.mjs";

/** @typedef {"response" | "tool-request" | "tool-execution" | "tool-result" | "stop"} AgentLoopStepKind */
/** @typedef {"ok" | "passed" | "error"} AgentLoopStepStatus */
/**
 * @typedef {Object} AgentLoopInput
 * @property {string} goal
 * @property {string} deviceId
 * @property {number} threshold
 * @property {"none" | "tool-error"} failureMode
 */
/**
 * @typedef {Object} AgentLoopStep
 * @property {string} id
 * @property {AgentLoopStepKind} kind
 * @property {string} actor
 * @property {string} title
 * @property {string} detail
 * @property {AgentLoopStepStatus} status
 */
/**
 * @typedef {Object} AgentLoopPrediction
 * @property {string} stepId
 * @property {string} selectedKind
 * @property {AgentLoopStepKind} expectedKind
 * @property {boolean} correct
 */
/**
 * @typedef {Object} AgentLoopTrace
 * @property {string} version
 * @property {AgentLoopInput} input
 * @property {{deviceId: string, value: number, unit: string, threshold: number, condition: string}} observation
 * @property {AgentLoopStep[]} steps
 */
/**
 * @typedef {Object} AgentLoopSession
 * @property {string} lessonId
 * @property {AgentLoopTrace} trace
 * @property {number} cursor
 * @property {AgentLoopStep[]} history
 * @property {AgentLoopPrediction[]} predictions
 * @property {AgentLoopPrediction | null} pendingPrediction
 * @property {"predicting" | "ready" | "complete"} status
 */
/**
 * @typedef {Object} AgentLoopEvidence
 * @property {string} contract
 * @property {string} contract_version
 * @property {string} course_version
 * @property {string} lesson_id
 * @property {"passed" | "partial" | "failed" | "alternative"} result
 * @property {true} anonymous
 * @property {string} checked_on
 * @property {string} summary
 * @property {{id: string, result: string}[]} evidence
 */

export const AGENT_LOOP_LESSON_ID = "t02-agent-loop";
export const LOOP_TRACE_VERSION = "1";

export const DEFAULT_LOOP_INPUT = Object.freeze({
  goal: "检查设备遥测并在异常时停止",
  deviceId: "device-17",
  threshold: 42,
  failureMode: "none",
});

export const FAILURE_MODES = Object.freeze(["none", "tool-error"]);
export const STEP_KINDS = Object.freeze([
  "response",
  "tool-request",
  "tool-execution",
  "tool-result",
  "stop",
]);

export const STEP_KIND_LABELS = Object.freeze({
  response: "模型响应",
  "tool-request": "工具请求",
  "tool-execution": "工具执行",
  "tool-result": "结果回填",
  stop: "停止条件",
});

const SAFE_IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$/;
const SUMMARY_BY_RESULT = Object.freeze({
  passed: "所有必需证据均已通过。",
  partial: "部分证据已通过，仍有证据需要补齐。",
  failed: "证据未通过，请根据本地检查结果恢复后重试。",
  alternative: "检测到满足验收目标的替代实现。",
});

export class AgentLoopInputError extends Error {
  constructor(message, code = "invalid-input") {
    super(message);
    this.name = "AgentLoopInputError";
    this.code = code;
  }
}

export class AgentLoopStateError extends Error {
  constructor(message, code = "invalid-state") {
    super(message);
    this.name = "AgentLoopStateError";
    this.code = code;
  }
}

function requireObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new AgentLoopInputError(`${label} 必须是对象`);
  }
  return value;
}

function requireIdentifier(value, label) {
  if (typeof value !== "string" || !SAFE_IDENTIFIER.test(value)) {
    throw new AgentLoopInputError(`${label} 必须是安全标识符`, "invalid-identifier");
  }
  return value;
}

function requireDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new AgentLoopInputError("checkedOn 必须是 YYYY-MM-DD", "invalid-date");
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== value) {
    throw new AgentLoopInputError("checkedOn 必须是有效日期", "invalid-date");
  }
  return value;
}

/** Normalize learner-controlled fields before they enter the deterministic trace. */
/** @param {unknown} value @returns {AgentLoopInput} */
export function normalizeLoopInput(value = DEFAULT_LOOP_INPUT) {
  const input = requireObject(value, "实验输入");
  const goal = typeof input.goal === "string" ? input.goal.trim() : "";
  if (!goal || goal.length > 160) {
    throw new AgentLoopInputError("目标需要是 1–160 个字符", "invalid-goal");
  }

  const deviceId = requireIdentifier(input.deviceId, "deviceId");
  const threshold = Number(input.threshold);
  if (!Number.isFinite(threshold) || threshold < 0 || threshold > 100) {
    throw new AgentLoopInputError("阈值需要是 0–100 之间的数字", "invalid-threshold");
  }

  const failureMode = input.failureMode ?? "none";
  if (!FAILURE_MODES.includes(failureMode)) {
    throw new AgentLoopInputError("不支持的故障模式", "invalid-failure-mode");
  }

  return { goal, deviceId, threshold, failureMode };
}

function deterministicReading(deviceId) {
  let hash = 17;
  for (const character of deviceId) {
    hash = (hash * 31 + character.charCodeAt(0)) % 1000;
  }
  return 25 + (hash % 35);
}

/** @param {string} id @param {AgentLoopStepKind} kind @param {string} actor @param {string} title @param {string} detail @param {AgentLoopStepStatus} [status] @returns {AgentLoopStep} */
function makeStep(id, kind, actor, title, detail, status = "ok") {
  return { id, kind, actor, title, detail, status };
}

/**
 * Build a vendor-neutral, deterministic teaching trace.
 *
 * This is a browser fixture, not a Codex, Claude Code, or model response.
 * Only learner-controlled values affect the trace; no network or secret is read.
 */
/** @param {unknown} value @returns {AgentLoopTrace} */
export function buildAgentLoopTrace(value = DEFAULT_LOOP_INPUT) {
  const input = normalizeLoopInput(value);
  const readingValue = deterministicReading(input.deviceId);
  const aboveThreshold = readingValue > input.threshold;
  const observation = {
    deviceId: input.deviceId,
    value: readingValue,
    unit: "°C",
    threshold: input.threshold,
    condition: aboveThreshold ? "threshold-exceeded" : "within-threshold",
  };
  const toolRequest = `read_telemetry({ device_id: "${input.deviceId}" })`;
  const steps = [
    makeStep(
      "response-1",
      "response",
      "model",
      "模型响应：拆出下一步",
      `模型先理解目标“${input.goal}”，决定需要读取 ${input.deviceId} 的遥测。`,
    ),
    makeStep(
      "tool-request-1",
      "tool-request",
      "harness",
      "工具请求：声明参数",
      `Harness 观察到工具请求 ${toolRequest}，尚未把它当作执行结果。`,
    ),
  ];

  if (input.failureMode === "tool-error") {
    steps.push(
      makeStep(
        "tool-execution-1",
        "tool-execution",
        "tool",
        "工具执行：注入可恢复错误",
        "模拟工具拒绝请求：设备暂时不可读。这里没有调用真实设备或网络。",
        "error",
      ),
      makeStep(
        "tool-result-1",
        "tool-result",
        "harness",
        "结果回填：错误回填",
        "Harness 把工具错误回填到当前上下文，模型可以据此停止，而不是假装拿到了数据。",
        "error",
      ),
      makeStep(
        "stop-1",
        "stop",
        "harness",
        "停止：错误恢复分支",
        "停止条件：工具返回错误；循环在边界内结束，等待人工恢复或稍后重试。",
        "error",
      ),
    );
  } else {
    steps.push(
      makeStep(
        "tool-execution-1",
        "tool-execution",
        "tool",
        "工具执行：读取模拟遥测",
        `确定性工具返回 ${input.deviceId} = ${readingValue} °C；该值由输入标识计算，不来自真实数据。`,
      ),
      makeStep(
        "tool-result-1",
        "tool-result",
        "harness",
        "结果回填：写回上下文",
        `结果回填：Harness 将 ${readingValue} °C 和阈值 ${input.threshold} 写回上下文，供下一次模型响应使用。`,
      ),
      makeStep(
        "response-2",
        "response",
        "model",
        "模型响应：解释观察",
        aboveThreshold
          ? `模型观察到 ${readingValue} °C 超过阈值 ${input.threshold}，选择报告异常。`
          : `模型观察到 ${readingValue} °C 未超过阈值 ${input.threshold}，选择安全结束。`,
      ),
      makeStep(
        "stop-1",
        "stop",
        "harness",
        "停止：满足停止条件",
        aboveThreshold
          ? "停止条件：目标已经得到可验证观察，异常已报告，不再重复调用工具。"
          : "停止条件：目标已经得到可验证观察，读数正常，不再重复调用工具。",
        "passed",
      ),
    );
  }

  return {
    version: LOOP_TRACE_VERSION,
    input,
    observation,
    steps,
  };
}

/** @param {unknown} value @returns {AgentLoopSession} */
export function createAgentLoopSession(value = DEFAULT_LOOP_INPUT) {
  const trace = buildAgentLoopTrace(value);
  return {
    lessonId: AGENT_LOOP_LESSON_ID,
    trace,
    cursor: 0,
    history: [],
    predictions: [],
    pendingPrediction: null,
    status: "predicting",
  };
}

function ensureSession(session) {
  if (session === null || typeof session !== "object" || !Array.isArray(session.history)) {
    throw new AgentLoopStateError("无效的 Agent loop session", "invalid-session");
  }
  return session;
}

/** Record a learner prediction for the next trace event without executing it. */
/** @param {AgentLoopSession} session @param {string} selectedKind @returns {AgentLoopSession} */
export function submitPrediction(session, selectedKind) {
  const current = ensureSession(session);
  if (current.status === "complete") {
    throw new AgentLoopStateError("该实验已经停止", "session-complete");
  }
  if (current.status !== "predicting") {
    throw new AgentLoopStateError("请先执行已记录的预测", "prediction-already-submitted");
  }
  if (!STEP_KINDS.includes(selectedKind)) {
    throw new AgentLoopStateError("预测步骤不受支持", "invalid-prediction");
  }

  const expectedStep = current.trace.steps[current.cursor];
  if (!expectedStep) {
    throw new AgentLoopStateError("没有可预测的下一步", "session-complete");
  }
  return {
    ...current,
    pendingPrediction: {
      stepId: expectedStep.id,
      selectedKind,
      expectedKind: expectedStep.kind,
      correct: selectedKind === expectedStep.kind,
    },
    status: "ready",
  };
}

/** Execute exactly one already-predicted event and return the next learner state. */
/** @param {AgentLoopSession} session @returns {AgentLoopSession} */
export function advanceAgentLoop(session) {
  const current = ensureSession(session);
  if (current.status === "complete") {
    throw new AgentLoopStateError("该实验已经停止", "session-complete");
  }
  if (current.status !== "ready" || current.pendingPrediction === null) {
    throw new AgentLoopStateError("请先预测下一步", "prediction-required");
  }

  const event = current.trace.steps[current.cursor];
  const history = [...current.history, event];
  const predictions = [...current.predictions, current.pendingPrediction];
  const cursor = current.cursor + 1;
  return {
    ...current,
    cursor,
    history,
    predictions,
    pendingPrediction: null,
    status: cursor >= current.trace.steps.length ? "complete" : "predicting",
  };
}

function classifyEvidence(results) {
  if (results.every((result) => result === "passed")) return "passed";
  if (results.every((result) => result === "failed")) return "failed";
  return "partial";
}

/** Build the same anonymous evidence envelope accepted by EvidenceLoop. */
/** @param {AgentLoopSession} session @param {{courseVersion: string, checkedOn?: string}} options @returns {AgentLoopEvidence} */
export function buildAgentLoopEvidence(session, options = {}) {
  const current = ensureSession(session);
  const courseVersion = options.courseVersion;
  requireIdentifier(courseVersion, "courseVersion");
  const checkedOn = options.checkedOn ?? new Date().toISOString().slice(0, 10);
  requireDate(checkedOn);

  const allPredictionsCorrect =
    current.predictions.length === current.trace.steps.length
    && current.predictions.every((prediction) => prediction.correct);
  const traceObserved = current.history.length === current.trace.steps.length;
  const stopObserved =
    current.status === "complete"
    && current.history.at(-1)?.kind === "stop";
  const checks = [
    { id: "prediction-recorded", result: allPredictionsCorrect ? "passed" : "failed" },
    { id: "trace-observed", result: traceObserved ? "passed" : "failed" },
    { id: "stop-condition-observed", result: stopObserved ? "passed" : "failed" },
  ];
  const result = classifyEvidence(checks.map((check) => check.result));
  const parsed = parseLearningInput(
    {
      contract: "agent-engineering-course/evidence",
      contract_version: "1",
      course_version: courseVersion,
      lesson_id: AGENT_LOOP_LESSON_ID,
      result,
      anonymous: true,
      checked_on: checkedOn,
      summary: SUMMARY_BY_RESULT[result],
      evidence: checks,
    },
    courseVersion,
  );
  return parsed.results[0];
}
