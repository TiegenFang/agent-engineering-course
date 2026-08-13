import { parseLearningInput } from "./evidence-record.mjs";

/**
 * Deterministic, vendor-neutral fixture for the Hooks and Tasks lesson.
 *
 * The fixture models lifecycle triggers, explicit task creation, a duplicate
 * hook definition, a permission gate, one recoverable failure and a stop
 * budget. It never calls a model, a client, a process, a file, a network or a
 * real side-effecting command. Product facts are taught on the page from
 * official docs; this module is only the observable teaching seam.
 */

export const HOOKS_TASKS_LESSON_ID = "t21-hooks-tasks";
export const HOOKS_TASKS_VERSION = "1";

export const HOOK_EVENTS = Object.freeze(["PostToolUse", "Stop", "TaskCreated"]);
export const ORCHESTRATION_MODES = Object.freeze(["hook", "task", "schedule", "background"]);
export const FAILURE_MODES = Object.freeze(["none", "once", "persistent"]);
export const PERMISSION_STATES = Object.freeze(["blocked", "allowed"]);

export const DEFAULT_HOOKS_TASKS_INPUT = Object.freeze({
  mode: "hook",
  event: "PostToolUse",
  triggerCount: 2,
  duplicateDefinition: true,
  taskRequested: true,
  permissionState: "blocked",
  failureMode: "once",
  maxSteps: 4,
});

export const HOOKS_TASKS_PRESETS = Object.freeze({
  safe: Object.freeze({ ...DEFAULT_HOOKS_TASKS_INPUT }),
  permission: Object.freeze({
    ...DEFAULT_HOOKS_TASKS_INPUT,
    permissionState: "allowed",
    failureMode: "none",
  }),
  failure: Object.freeze({
    ...DEFAULT_HOOKS_TASKS_INPUT,
    failureMode: "persistent",
    maxSteps: 4,
  }),
  stop: Object.freeze({
    ...DEFAULT_HOOKS_TASKS_INPUT,
    failureMode: "none",
    maxSteps: 1,
  }),
  explicitTask: Object.freeze({
    ...DEFAULT_HOOKS_TASKS_INPUT,
    mode: "task",
    taskRequested: true,
    triggerCount: 0,
    duplicateDefinition: false,
    failureMode: "none",
  }),
  schedule: Object.freeze({
    ...DEFAULT_HOOKS_TASKS_INPUT,
    mode: "schedule",
    taskRequested: false,
    triggerCount: 0,
    duplicateDefinition: false,
    failureMode: "none",
  }),
  background: Object.freeze({
    ...DEFAULT_HOOKS_TASKS_INPUT,
    mode: "background",
    taskRequested: false,
    triggerCount: 0,
    duplicateDefinition: false,
    failureMode: "none",
  }),
});

const SUMMARY_BY_RESULT = Object.freeze({
  passed: "所有必需证据均已通过。",
  partial: "部分证据已通过，仍有证据需要补齐。",
  failed: "证据未通过，请根据本地检查结果恢复后重试。",
  alternative: "检测到满足验收目标的替代实现。",
});

const FINDING_IDS = Object.freeze([
  "trigger",
  "deduplication",
  "permission",
  "stop",
  "failure-recovery",
  "side-effect-guard",
  "explicit-task",
]);

export class HooksTasksInputError extends Error {
  constructor(message, code = "invalid-input") {
    super(message);
    this.name = "HooksTasksInputError";
    this.code = code;
  }
}

export class HooksTasksStateError extends Error {
  constructor(message, code = "invalid-state") {
    super(message);
    this.name = "HooksTasksStateError";
    this.code = code;
  }
}

function requireObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new HooksTasksInputError(`${label} 必须是对象`);
  }
  return value;
}

function boundedInteger(value, key, min, max) {
  const number = Number(value);
  if (!Number.isInteger(number) || number < min || number > max) {
    throw new HooksTasksInputError(`${key} 需要是 ${min}–${max} 之间的整数`, `invalid-${key}`);
  }
  return number;
}

function oneOf(value, values, label) {
  if (!values.includes(value)) {
    throw new HooksTasksInputError(`${label} 不在支持的枚举中`, `invalid-${label}`);
  }
  return value;
}

export function normalizeHooksTasksInput(value = DEFAULT_HOOKS_TASKS_INPUT) {
  const input = requireObject(value, "实验输入");
  return {
    mode: oneOf(input.mode ?? DEFAULT_HOOKS_TASKS_INPUT.mode, ORCHESTRATION_MODES, "mode"),
    event: oneOf(input.event ?? DEFAULT_HOOKS_TASKS_INPUT.event, HOOK_EVENTS, "event"),
    triggerCount: boundedInteger(input.triggerCount ?? DEFAULT_HOOKS_TASKS_INPUT.triggerCount, "triggerCount", 0, 3),
    duplicateDefinition: input.duplicateDefinition ?? DEFAULT_HOOKS_TASKS_INPUT.duplicateDefinition,
    taskRequested: input.taskRequested ?? DEFAULT_HOOKS_TASKS_INPUT.taskRequested,
    permissionState: oneOf(
      input.permissionState ?? DEFAULT_HOOKS_TASKS_INPUT.permissionState,
      PERMISSION_STATES,
      "permissionState",
    ),
    failureMode: oneOf(input.failureMode ?? DEFAULT_HOOKS_TASKS_INPUT.failureMode, FAILURE_MODES, "failureMode"),
    maxSteps: boundedInteger(input.maxSteps ?? DEFAULT_HOOKS_TASKS_INPUT.maxSteps, "maxSteps", 1, 8),
  };
}

function classifyRun(input) {
  const automatic = input.mode === "hook";
  const triggerCount = automatic ? input.triggerCount : 0;
  const deduplicated = automatic && input.duplicateDefinition ? Math.max(0, triggerCount - 1) : 0;
  const triggered = triggerCount > 0;
  const explicitTask = Boolean(input.taskRequested);
  const permission = input.permissionState;
  const sideEffect = permission === "allowed" && triggered;

  const failureInjected = input.failureMode !== "none";
  const recovered = input.failureMode === "once" && input.maxSteps >= 3;
  const failureUnresolved = input.failureMode === "persistent" || (failureInjected && !recovered);
  const stepsUsed = Math.min(
    input.maxSteps,
    (triggered ? 1 : 0) + (explicitTask ? 1 : 0) + (failureInjected ? 2 : 0),
  );
  const stopped = stepsUsed >= input.maxSteps || (!failureUnresolved && (triggered || explicitTask));
  const stopReason = stepsUsed >= input.maxSteps ? "step-budget" : stopped ? "done" : "awaiting-input";

  const findings = [];
  if (triggered) findings.push("trigger");
  if (deduplicated > 0) findings.push("deduplication");
  if (permission === "blocked") findings.push("permission");
  if (stopped) findings.push("stop");
  if (recovered) findings.push("failure-recovery");
  if (!sideEffect) findings.push("side-effect-guard");
  if (explicitTask) findings.push("explicit-task");

  return {
    mode: input.mode,
    event: input.event,
    triggered,
    triggerCount,
    deduplicated,
    explicitTask,
    permission,
    sideEffect,
    failureInjected,
    recovered,
    failureUnresolved,
    stopped,
    stopReason,
    stepsUsed,
    findings,
    automatic: automatic && triggered,
    scheduleArmed: input.mode === "schedule",
    backgroundStarted: input.mode === "background",
  };
}

/** Simulate one complete, deterministic observation without any side effect. */
export function simulateHooksTasks(value = DEFAULT_HOOKS_TASKS_INPUT) {
  const input = normalizeHooksTasksInput(value);
  const run = classifyRun(input);
  return { version: HOOKS_TASKS_VERSION, input, run };
}

function ensureSession(session) {
  if (
    session === null
    || typeof session !== "object"
    || session.lessonId !== HOOKS_TASKS_LESSON_ID
    || session.version !== HOOKS_TASKS_VERSION
    || !Array.isArray(session.runs)
  ) {
    throw new HooksTasksStateError("无效的 Hooks/Tasks session", "invalid-session");
  }
  return session;
}

export function createHooksTasksSession(value = DEFAULT_HOOKS_TASKS_INPUT) {
  const simulation = simulateHooksTasks(value);
  return {
    lessonId: HOOKS_TASKS_LESSON_ID,
    version: HOOKS_TASKS_VERSION,
    input: simulation.input,
    result: simulation.run,
    runs: [],
  };
}

export function updateHooksTasksSession(session, value = DEFAULT_HOOKS_TASKS_INPUT) {
  const current = ensureSession(session);
  const next = createHooksTasksSession(value);
  return { ...next, runs: [...current.runs] };
}

export function recordHooksTasksObservation(session) {
  const current = ensureSession(session);
  const result = current.result;
  const observation = {
    id: `run-${current.runs.length + 1}`,
    mode: result.mode,
    trigger: result.triggered,
    deduplicated: result.deduplicated > 0,
    permission: result.permission,
    stopped: result.stopped,
    failed: result.failureInjected,
    recovered: result.recovered,
    taskCreated: result.explicitTask,
    sideEffect: result.sideEffect,
    scheduleArmed: result.scheduleArmed,
    backgroundStarted: result.backgroundStarted,
  };
  return { ...current, runs: [...current.runs, observation], lastRun: observation };
}

function classifyEvidence(results) {
  if (results.every((result) => result === "passed")) return "passed";
  if (results.every((result) => result === "failed")) return "failed";
  if (results.every((result) => result === "passed" || result === "alternative") && results.some((result) => result === "alternative")) {
    return "alternative";
  }
  return "partial";
}

function checkedOn(value) {
  const date = value ?? new Date().toISOString().slice(0, 10);
  if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    throw new HooksTasksInputError("checkedOn 必须是 YYYY-MM-DD", "invalid-date");
  }
  const parsed = new Date(`${date}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== date) {
    throw new HooksTasksInputError("checkedOn 必须是有效日期", "invalid-date");
  }
  return date;
}

/** Build an anonymous evidence document. Inputs and raw event details never leave this function. */
export function buildHooksTasksEvidence(session, options = {}) {
  const current = ensureSession(session);
  const courseVersion = options.courseVersion;
  if (typeof courseVersion !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(courseVersion)) {
    throw new HooksTasksInputError("courseVersion 不是安全标识符", "invalid-course-version");
  }
  const runs = current.runs;
  const checks = [
    { id: "trigger-observed", result: runs.some((run) => run.trigger) ? "passed" : "failed" },
    { id: "deduplication-observed", result: runs.some((run) => run.deduplicated) ? "passed" : "failed" },
    { id: "permission-boundary", result: runs.some((run) => run.permission === "blocked") ? "passed" : "failed" },
    { id: "stop-condition", result: runs.some((run) => run.stopped) ? "passed" : "failed" },
    { id: "failure-recovered", result: runs.some((run) => run.recovered) ? "passed" : "failed" },
    { id: "side-effect-not-triggered", result: runs.length > 0 && runs.every((run) => run.sideEffect === false) ? "passed" : "failed" },
    { id: "explicit-task-recorded", result: runs.some((run) => run.taskCreated) ? "passed" : "failed" },
    { id: "offline-deterministic", result: runs.length > 0 && runs.every((run) => typeof run.id === "string") ? "passed" : "failed" },
  ];
  const result = classifyEvidence(checks.map((check) => check.result));
  const parsed = parseLearningInput(
    {
      contract: "agent-engineering-course/evidence",
      contract_version: "1",
      course_version: courseVersion,
      lesson_id: HOOKS_TASKS_LESSON_ID,
      result,
      anonymous: true,
      checked_on: checkedOn(options.checkedOn),
      summary: SUMMARY_BY_RESULT[result],
      evidence: checks,
    },
    courseVersion,
  );
  const evidence = parsed.results[0];
  evidence.experiment = {
    version: HOOKS_TASKS_VERSION,
    runs: runs.map((run) => ({ ...run })),
    observed: [...new Set(runs.flatMap((run) => [
      ...(run.trigger ? ["trigger"] : []),
      ...(run.deduplicated ? ["deduplication"] : []),
      ...(run.permission === "blocked" ? ["permission"] : []),
      ...(run.stopped ? ["stop"] : []),
      ...(run.recovered ? ["failure-recovery"] : []),
      ...(run.sideEffect === false ? ["side-effect-guard"] : []),
      ...(run.taskCreated ? ["explicit-task"] : []),
    ]))].sort(),
  };
  return evidence;
}

export { FINDING_IDS };
