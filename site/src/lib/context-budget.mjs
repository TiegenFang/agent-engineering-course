import { parseLearningInput } from "./evidence-record.mjs";

/**
 * A deterministic, vendor-neutral context working-set simulator.
 *
 * The numbers are deliberately illustrative rather than a model or client
 * limit.  No network, model, file, or secret is read.  The allocator keeps
 * higher-priority segments first and reports what a lower-priority segment
 * could not retain.
 */

export const CONTEXT_BUDGET_LESSON_ID = "t14-context-budget";
export const CONTEXT_BUDGET_VERSION = "1";

export const INPUT_BOUNDS = Object.freeze({
  capacity: Object.freeze({ min: 64, max: 1024 }),
  outputReserve: Object.freeze({ min: 0, max: 512 }),
  instructions: Object.freeze({ min: 0, max: 512 }),
  task: Object.freeze({ min: 0, max: 512 }),
  history: Object.freeze({ min: 0, max: 512 }),
  memory: Object.freeze({ min: 0, max: 512 }),
  tools: Object.freeze({ min: 0, max: 512 }),
  noise: Object.freeze({ min: 0, max: 512 }),
});

export const FINDING_IDS = Object.freeze(["insufficient", "pollution", "crowding"]);

export const SEGMENT_DEFINITIONS = Object.freeze([
  Object.freeze({
    id: "instructions",
    label: "系统与规则",
    role: "约束与工具边界",
    priority: 5,
    required: true,
  }),
  Object.freeze({
    id: "task",
    label: "当前任务",
    role: "本轮目标与验收",
    priority: 5,
    required: true,
  }),
  Object.freeze({
    id: "memory",
    label: "Memory 摘要",
    role: "受控保留的跨任务信息",
    priority: 4,
    required: false,
  }),
  Object.freeze({
    id: "tools",
    label: "工具结果",
    role: "当前任务已取得的观察",
    priority: 3,
    required: false,
  }),
  Object.freeze({
    id: "history",
    label: "对话历史",
    role: "当前会话的先前轮次",
    priority: 2,
    required: false,
  }),
  Object.freeze({
    id: "noise",
    label: "无关或过期内容",
    role: "不应占用工作集的噪声",
    priority: 1,
    required: false,
  }),
]);

export const DEFAULT_CONTEXT_BUDGET_INPUT = Object.freeze({
  capacity: 256,
  outputReserve: 64,
  instructions: 24,
  task: 48,
  history: 64,
  memory: 32,
  tools: 16,
  noise: 0,
  includeHistory: true,
  includeMemory: true,
  includeTools: true,
  includeNoise: false,
});

export const CONTEXT_BUDGET_PRESETS = Object.freeze({
  normal: Object.freeze({ ...DEFAULT_CONTEXT_BUDGET_INPUT }),
  insufficient: Object.freeze({
    ...DEFAULT_CONTEXT_BUDGET_INPUT,
    capacity: 64,
    outputReserve: 64,
    history: 96,
    memory: 32,
    tools: 16,
  }),
  pollution: Object.freeze({
    ...DEFAULT_CONTEXT_BUDGET_INPUT,
    capacity: 512,
    outputReserve: 64,
    history: 32,
    noise: 160,
    includeNoise: true,
  }),
  crowding: Object.freeze({
    ...DEFAULT_CONTEXT_BUDGET_INPUT,
    capacity: 256,
    outputReserve: 64,
    history: 200,
    memory: 64,
    tools: 32,
  }),
});

const SUMMARY_BY_RESULT = Object.freeze({
  passed: "所有必需证据均已通过。",
  partial: "部分证据已通过，仍有证据需要补齐。",
  failed: "证据未通过，请根据本地检查结果恢复后重试。",
  alternative: "检测到满足验收目标的替代实现。",
});

export class ContextBudgetInputError extends Error {
  constructor(message, code = "invalid-input") {
    super(message);
    this.name = "ContextBudgetInputError";
    this.code = code;
  }
}

export class ContextBudgetStateError extends Error {
  constructor(message, code = "invalid-state") {
    super(message);
    this.name = "ContextBudgetStateError";
    this.code = code;
  }
}

function requireObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new ContextBudgetInputError(`${label} 必须是对象`);
  }
  return value;
}

function boundedInteger(value, key, label) {
  const number = Number(value);
  const bounds = INPUT_BOUNDS[key];
  if (!Number.isInteger(number) || number < bounds.min || number > bounds.max) {
    throw new ContextBudgetInputError(
      `${label} 需要是 ${bounds.min}–${bounds.max} 之间的整数`,
      `invalid-${key}`,
    );
  }
  return number;
}

function booleanValue(value, fallback, label) {
  const resolved = value === undefined ? fallback : value;
  if (typeof resolved !== "boolean") {
    throw new ContextBudgetInputError(`${label} 必须是布尔值`, "invalid-selection");
  }
  return resolved;
}

/** Normalize learner-controlled values and enforce every documented boundary. */
export function normalizeContextBudgetInput(value = DEFAULT_CONTEXT_BUDGET_INPUT) {
  const input = requireObject(value, "实验输入");
  const normalized = {
    capacity: boundedInteger(input.capacity ?? DEFAULT_CONTEXT_BUDGET_INPUT.capacity, "capacity", "上下文容量"),
    outputReserve: boundedInteger(
      input.outputReserve ?? DEFAULT_CONTEXT_BUDGET_INPUT.outputReserve,
      "outputReserve",
      "输出预留",
    ),
    instructions: boundedInteger(
      input.instructions ?? DEFAULT_CONTEXT_BUDGET_INPUT.instructions,
      "instructions",
      "系统与规则占用",
    ),
    task: boundedInteger(input.task ?? DEFAULT_CONTEXT_BUDGET_INPUT.task, "task", "当前任务占用"),
    history: boundedInteger(
      input.history ?? DEFAULT_CONTEXT_BUDGET_INPUT.history,
      "history",
      "对话历史占用",
    ),
    memory: boundedInteger(input.memory ?? DEFAULT_CONTEXT_BUDGET_INPUT.memory, "memory", "Memory 占用"),
    tools: boundedInteger(input.tools ?? DEFAULT_CONTEXT_BUDGET_INPUT.tools, "tools", "工具结果占用"),
    noise: boundedInteger(input.noise ?? DEFAULT_CONTEXT_BUDGET_INPUT.noise, "noise", "噪声占用"),
    includeHistory: booleanValue(
      input.includeHistory,
      DEFAULT_CONTEXT_BUDGET_INPUT.includeHistory,
      "是否纳入对话历史",
    ),
    includeMemory: booleanValue(
      input.includeMemory,
      DEFAULT_CONTEXT_BUDGET_INPUT.includeMemory,
      "是否纳入 Memory",
    ),
    includeTools: booleanValue(
      input.includeTools,
      DEFAULT_CONTEXT_BUDGET_INPUT.includeTools,
      "是否纳入工具结果",
    ),
    includeNoise: booleanValue(
      input.includeNoise,
      DEFAULT_CONTEXT_BUDGET_INPUT.includeNoise,
      "是否纳入噪声",
    ),
  };
  if (normalized.outputReserve > normalized.capacity) {
    throw new ContextBudgetInputError(
      "输出预留不能大于上下文容量",
      "reserve-exceeds-capacity",
    );
  }
  return normalized;
}

function selectedValues(input) {
  return {
    instructions: input.instructions,
    task: input.task,
    memory: input.includeMemory ? input.memory : 0,
    tools: input.includeTools ? input.tools : 0,
    history: input.includeHistory ? input.history : 0,
    noise: input.includeNoise ? input.noise : 0,
  };
}

function classifyFindings({ inputBudget, selectedTotal, selected, dropped, pollutionRatio }) {
  const findings = [];
  const insufficient = inputBudget <= 0 || selectedTotal > inputBudget;
  if (insufficient) findings.push("insufficient");

  if (selected.noise > 0 && pollutionRatio >= 20) findings.push("pollution");

  const optionalDropped = dropped.history + dropped.memory + dropped.tools + dropped.noise;
  const longTail = selected.history + selected.noise > Math.floor(inputBudget * 0.5);
  if (optionalDropped > 0 || longTail) findings.push("crowding");
  return findings;
}

function findingDetails({ findings, inputBudget, selectedTotal, retainedTotal, droppedTotal, pollutionRatio, selected, dropped }) {
  const details = [];
  if (findings.includes("insufficient")) {
    details.push({
      id: "insufficient",
      label: "上下文不足",
      detail: inputBudget <= 0
        ? "输出预留已经占满容量，本轮没有可用的输入工作集。"
        : `选入 ${selectedTotal}，输入预算只有 ${inputBudget}；至少有 ${droppedTotal} 未能保留。`,
    });
  }
  if (findings.includes("pollution")) {
    details.push({
      id: "pollution",
      label: "上下文污染",
      detail: `无关或过期内容占当前工作集约 ${pollutionRatio}%（${selected.noise} / ${selectedTotal}），会稀释相关信息。`,
    });
  }
  if (findings.includes("crowding")) {
    const droppedLabels = Object.entries(dropped)
      .filter(([, amount]) => amount > 0)
      .map(([id, amount]) => `${id} ${amount}`)
      .join("、");
    details.push({
      id: "crowding",
      label: "相关内容被挤占",
      detail: droppedLabels
        ? `低优先级片段未完整保留：${droppedLabels}；保留量 ${retainedTotal}。`
        : "对话历史与噪声占用了工作集的大半，建议压缩或刷新后再继续。",
    });
  }
  if (details.length === 0) {
    details.push({
      id: "ready",
      label: "工作集可用",
      detail: `选入 ${selectedTotal}，保留 ${retainedTotal}；当前没有触发三类风险信号。`,
    });
  }
  return details;
}

/**
 * Allocate a working set by priority and report every visible consequence.
 * This function is deterministic for the same normalized input.
 */
export function simulateContextBudget(value = DEFAULT_CONTEXT_BUDGET_INPUT) {
  const input = normalizeContextBudgetInput(value);
  const inputBudget = input.capacity - input.outputReserve;
  const selected = selectedValues(input);
  const selectedTotal = Object.values(selected).reduce((sum, amount) => sum + amount, 0);
  let remaining = inputBudget;
  const segments = SEGMENT_DEFINITIONS.map((definition) => {
    const requested = selected[definition.id];
    const kept = Math.min(requested, Math.max(0, remaining));
    remaining -= kept;
    return {
      id: definition.id,
      label: definition.label,
      role: definition.role,
      required: definition.required,
      selected: definition.id === "history"
        ? input.includeHistory
        : definition.id === "memory"
          ? input.includeMemory
          : definition.id === "tools"
            ? input.includeTools
            : definition.id === "noise"
              ? input.includeNoise
              : true,
      requested,
      kept,
      dropped: requested - kept,
    };
  });
  const retainedTotal = segments.reduce((sum, segment) => sum + segment.kept, 0);
  const dropped = Object.fromEntries(segments.map((segment) => [segment.id, segment.dropped]));
  const droppedTotal = segments.reduce((sum, segment) => sum + segment.dropped, 0);
  const pollutionRatio = selectedTotal === 0 ? 0 : Math.round((selected.noise / selectedTotal) * 100);
  const findings = classifyFindings({
    inputBudget,
    selectedTotal,
    selected,
    dropped,
    pollutionRatio,
  });
  const details = findingDetails({
    findings,
    inputBudget,
    selectedTotal,
    retainedTotal,
    droppedTotal,
    pollutionRatio,
    selected,
    dropped,
  });
  const boundary = Object.entries(INPUT_BOUNDS).some(([key, bounds]) => input[key] === bounds.min || input[key] === bounds.max)
    || input.outputReserve === input.capacity;

  return {
    version: CONTEXT_BUDGET_VERSION,
    input,
    budget: {
      capacity: input.capacity,
      outputReserve: input.outputReserve,
      inputBudget,
      selectedTotal,
      retainedTotal,
      droppedTotal,
      available: Math.max(0, remaining),
      utilizationPercent: inputBudget === 0 ? 100 : Math.round((retainedTotal / inputBudget) * 100),
    },
    segments,
    findings,
    findingDetails: details,
    primaryFinding: findings[0] ?? "ready",
    ratios: {
      pollutionPercent: pollutionRatio,
      relevancePercent: selectedTotal === 0 ? 0 : Math.round(((selectedTotal - selected.noise) / selectedTotal) * 100),
    },
    boundary,
  };
}

export function describeContextBudgetResult(result) {
  if (!result || typeof result !== "object" || !Array.isArray(result.findingDetails)) {
    throw new ContextBudgetStateError("无法描述无效的模拟结果", "invalid-result");
  }
  const primary = result.findingDetails[0];
  return `${primary.label}：${primary.detail}`;
}

export function createContextBudgetSession(value = DEFAULT_CONTEXT_BUDGET_INPUT) {
  const result = simulateContextBudget(value);
  return {
    lessonId: CONTEXT_BUDGET_LESSON_ID,
    version: CONTEXT_BUDGET_VERSION,
    input: result.input,
    result,
    runs: [],
  };
}

function ensureSession(session) {
  if (
    session === null
    || typeof session !== "object"
    || session.lessonId !== CONTEXT_BUDGET_LESSON_ID
    || !Array.isArray(session.runs)
    || !session.result
  ) {
    throw new ContextBudgetStateError("无效的上下文预算 session", "invalid-session");
  }
  return session;
}

/** Apply new controls while preserving observations already recorded in this session. */
export function updateContextBudgetSession(session, value = DEFAULT_CONTEXT_BUDGET_INPUT) {
  const current = ensureSession(session);
  const next = createContextBudgetSession(value);
  return { ...next, runs: [...current.runs] };
}

export function recordContextBudgetObservation(session) {
  const current = ensureSession(session);
  const run = {
    id: `run-${current.runs.length + 1}`,
    finding: current.result.primaryFinding,
    findings: [...current.result.findings],
    boundary: current.result.boundary,
  };
  return { ...current, runs: [...current.runs, run], lastRun: run };
}

function classifyEvidence(results) {
  if (results.every((result) => result === "passed")) return "passed";
  if (results.every((result) => result === "failed")) return "failed";
  if (results.every((result) => result === "passed" || result === "alternative") && results.some((result) => result === "alternative")) {
    return "alternative";
  }
  return "partial";
}

function validCheckedOn(value) {
  const checkedOn = value ?? new Date().toISOString().slice(0, 10);
  if (typeof checkedOn !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(checkedOn)) {
    throw new ContextBudgetInputError("checkedOn 必须是 YYYY-MM-DD", "invalid-date");
  }
  const parsed = new Date(`${checkedOn}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== checkedOn) {
    throw new ContextBudgetInputError("checkedOn 必须是有效日期", "invalid-date");
  }
  return checkedOn;
}

/** Build a public evidence envelope; raw input numbers never cross this seam. */
export function buildContextBudgetEvidence(session, options = {}) {
  const current = ensureSession(session);
  const courseVersion = options.courseVersion;
  if (typeof courseVersion !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(courseVersion)) {
    throw new ContextBudgetInputError("courseVersion 不是安全标识符", "invalid-course-version");
  }
  const checkedOn = validCheckedOn(options.checkedOn);
  const observed = new Set(current.runs.flatMap((run) => run.findings));
  const allRunsSafe = current.runs.every(
    (run) => Array.isArray(run.findings) && run.findings.every((finding) => [...FINDING_IDS, "ready"].includes(finding)),
  );
  const checks = [
    { id: "working-set-selected", result: current.runs.length > 0 ? "passed" : "failed" },
    {
      id: "risk-signals-observed",
      result: FINDING_IDS.every((finding) => observed.has(finding)) ? "passed" : "failed",
    },
    {
      id: "boundary-tested",
      result: current.runs.some((run) => run.boundary === true) ? "passed" : "failed",
    },
    { id: "offline-deterministic", result: allRunsSafe && current.runs.length > 0 ? "passed" : "failed" },
  ];
  const result = classifyEvidence(checks.map((check) => check.result));
  const parsed = parseLearningInput(
    {
      contract: "agent-engineering-course/evidence",
      contract_version: "1",
      course_version: courseVersion,
      lesson_id: CONTEXT_BUDGET_LESSON_ID,
      result,
      anonymous: true,
      checked_on: checkedOn,
      summary: SUMMARY_BY_RESULT[result],
      evidence: checks,
    },
    courseVersion,
  );
  const evidence = parsed.results[0];
  evidence.simulation = {
    version: CONTEXT_BUDGET_VERSION,
    runs: current.runs.map((run) => ({
      id: run.id,
      finding: run.finding,
      findings: [...run.findings],
      boundary: run.boundary === true,
    })),
    observed: [...observed].sort(),
  };
  return evidence;
}
