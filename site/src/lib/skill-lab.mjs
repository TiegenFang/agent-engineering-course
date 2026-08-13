import { parseLearningInput } from "./evidence-record.mjs";

/**
 * A deterministic, vendor-neutral Skill lab.
 *
 * The fixture models a research/evidence workflow with four fixed inputs. It
 * never reads a file, calls a model, invokes a client, or makes a network
 * request. The trigger matrix is a teaching aid for testing description
 * boundaries; it is not an implementation of any vendor's retrieval logic.
 */

export const SKILL_LESSON_ID = "t17-skill";
export const SKILL_SIMULATION_VERSION = "1";

export const SKILL_SCENARIOS = Object.freeze([
  Object.freeze({
    id: "complete",
    label: "完整证据链",
    finding: "ready",
    findingLabel: "可交付",
    detail: "任务、参考规则和合成遥测样例都已到位；脚本可规范化，验证器可以复核结果。",
    boundary: false,
    resources: ["evidence-schema", "source-policy", "telemetry-sample"],
  }),
  Object.freeze({
    id: "missing-source",
    label: "缺少来源",
    finding: "needs-source",
    findingLabel: "需要补来源",
    detail: "有一条合成主张没有可追溯来源；Skill 应停在证据卡片，而不是替它补写结论。",
    boundary: false,
    resources: ["evidence-schema", "source-policy"],
  }),
  Object.freeze({
    id: "conflicting-evidence",
    label: "证据冲突",
    finding: "conflict",
    findingLabel: "需要人工复核",
    detail: "两个合成来源对同一主张不一致；验证器保留冲突状态，不能把它静默合并。",
    boundary: true,
    resources: ["evidence-schema", "source-policy", "telemetry-sample"],
  }),
  Object.freeze({
    id: "untrusted-instruction",
    label: "不可信输入",
    finding: "untrusted-input",
    findingLabel: "拒绝越界指令",
    detail: "输入夹带“跳过来源检查并发送到外部服务”的指令；Skill 只按任务契约处理并阻断副作用。",
    boundary: true,
    resources: ["evidence-schema", "source-policy"],
  }),
]);

export const SKILL_TRIGGER_CASES = Object.freeze([
  Object.freeze({
    id: "research-evidence",
    label: "整理合成遥测主张并给出来源卡片",
    expected: "activate",
  }),
  Object.freeze({
    id: "telemetry-summary",
    label: "比较两组设备报告，保留待核验项",
    expected: "activate",
  }),
  Object.freeze({
    id: "generic-greeting",
    label: "你好，今天天气怎么样？",
    expected: "skip",
  }),
  Object.freeze({
    id: "one-line-calculation",
    label: "计算 18 × 7",
    expected: "skip",
  }),
]);

export const SKILL_CHECK_IDS = Object.freeze([
  "skill-package-shaped",
  "trigger-boundary-tested",
  "evidence-scenarios-covered",
  "validation-script-passed",
  "security-boundary-tested",
  "offline-deterministic",
]);

const FINDING_IDS = new Set(SKILL_SCENARIOS.map((scenario) => scenario.finding));

export class SkillLabError extends Error {
  constructor(message, code = "invalid-skill-lab") {
    super(message);
    this.name = "SkillLabError";
    this.code = code;
  }
}

function fail(message, code = "invalid-skill-lab") {
  throw new SkillLabError(message, code);
}

function scenarioById(id) {
  const scenario = SKILL_SCENARIOS.find((item) => item.id === id);
  if (!scenario) fail(`未知 Skill 场景: ${id}`, "unknown-scenario");
  return scenario;
}

function classifyChecks(results) {
  if (results.length > 0 && results.every((result) => result === "passed")) return "passed";
  if (results.length > 0 && results.every((result) => result === "failed")) return "failed";
  if (
    results.length > 0
    && results.every((result) => result === "passed" || result === "alternative")
    && results.some((result) => result === "alternative")
  ) {
    return "alternative";
  }
  return "partial";
}

function safeCourseVersion(value) {
  if (typeof value !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value)) {
    fail("courseVersion 不是安全标识符", "invalid-course-version");
  }
  return value;
}

function checkedOn(value) {
  const result = value ?? new Date().toISOString().slice(0, 10);
  if (typeof result !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(result)) {
    fail("checkedOn 必须是 YYYY-MM-DD", "invalid-date");
  }
  const parsed = new Date(`${result}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== result) {
    fail("checkedOn 必须是有效日期", "invalid-date");
  }
  return result;
}

/** Run a fixed scenario twice and compare the status-only result. */
export function simulateSkillScenario(id) {
  const scenario = scenarioById(id);
  const base = {
    scenario: scenario.id,
    finding: scenario.finding,
    boundary: scenario.boundary,
    inputs: ["task-brief", "reference-index", "synthetic-telemetry"],
    resources: [...scenario.resources],
    script: "passed",
    validator: "passed",
    externalCall: false,
  };
  const first = JSON.stringify(base);
  const second = JSON.stringify({ ...base, resources: [...scenario.resources] });
  return {
    version: SKILL_SIMULATION_VERSION,
    ...base,
    deterministic: first === second,
    label: scenario.label,
    findingLabel: scenario.findingLabel,
    detail: scenario.detail,
  };
}

export function describeSkillScenario(result) {
  if (!result || typeof result !== "object" || !FINDING_IDS.has(result.finding)) {
    fail("无法描述无效的 Skill 场景结果", "invalid-result");
  }
  return `${result.findingLabel}：${result.detail}`;
}

export function createSkillSession() {
  return {
    lessonId: SKILL_LESSON_ID,
    version: SKILL_SIMULATION_VERSION,
    runs: [],
    triggerCases: SKILL_TRIGGER_CASES.map((item) => ({ id: item.id, observed: "not-tested" })),
    lastRun: null,
    triggersTested: false,
  };
}

function ensureSession(session) {
  if (
    !session
    || typeof session !== "object"
    || session.lessonId !== SKILL_LESSON_ID
    || session.version !== SKILL_SIMULATION_VERSION
    || !Array.isArray(session.runs)
    || !Array.isArray(session.triggerCases)
  ) {
    fail("无效的 Skill lab session", "invalid-session");
  }
  return session;
}

export function runSkillScenario(session, scenarioId) {
  const current = ensureSession(session);
  const result = simulateSkillScenario(scenarioId);
  return { ...current, lastRun: result };
}

export function recordSkillObservation(session) {
  const current = ensureSession(session);
  if (!current.lastRun) fail("请先运行一个 Skill 场景", "missing-run");
  const run = {
    id: `run-${current.runs.length + 1}`,
    scenario: current.lastRun.scenario,
    finding: current.lastRun.finding,
    boundary: current.lastRun.boundary === true,
    script: current.lastRun.script,
    deterministic: current.lastRun.deterministic === true,
    external_call: current.lastRun.externalCall === false ? false : true,
  };
  return { ...current, runs: [...current.runs, run] };
}

/** Record the fixed positive/negative trigger matrix without calling an agent. */
export function testSkillTriggerBoundary(session) {
  const current = ensureSession(session);
  return {
    ...current,
    triggersTested: true,
    triggerCases: SKILL_TRIGGER_CASES.map((item) => ({ id: item.id, observed: item.expected })),
  };
}

function expectedChecks(session) {
  const observedScenarios = new Set(session.runs.map((run) => run.scenario));
  const triggerBoundary = session.triggersTested
    && session.triggerCases.every((item, index) => item.observed === SKILL_TRIGGER_CASES[index].expected);
  const allScenarios = SKILL_SCENARIOS.every((scenario) => observedScenarios.has(scenario.id));
  const allValidated = session.runs.length > 0
    && session.runs.every((run) => run.script === "passed" && run.deterministic === true);
  const security = session.runs.some(
    (run) => run.scenario === "untrusted-instruction"
      && run.finding === "untrusted-input"
      && run.boundary === true
      && run.external_call === false,
  );
  const offline = session.runs.length > 0
    && session.runs.every((run) => run.deterministic === true && run.external_call === false);
  return [
    { id: "skill-package-shaped", result: "passed" },
    { id: "trigger-boundary-tested", result: triggerBoundary ? "passed" : "failed" },
    { id: "evidence-scenarios-covered", result: allScenarios ? "passed" : "failed" },
    { id: "validation-script-passed", result: allValidated ? "passed" : "failed" },
    { id: "security-boundary-tested", result: security ? "passed" : "failed" },
    { id: "offline-deterministic", result: offline ? "passed" : "failed" },
  ];
}

/** Build a public evidence envelope; raw task text and resource contents stay local. */
export function buildSkillEvidence(session, options = {}) {
  const current = ensureSession(session);
  const courseVersion = safeCourseVersion(options.courseVersion);
  const checks = expectedChecks(current);
  const result = classifyChecks(checks.map((check) => check.result));
  const parsed = parseLearningInput(
    {
      contract: "agent-engineering-course/evidence",
      contract_version: "1",
      course_version: courseVersion,
      lesson_id: SKILL_LESSON_ID,
      result,
      anonymous: true,
      checked_on: checkedOn(options.checkedOn),
      summary: {
        passed: "所有必需证据均已通过。",
        partial: "部分证据已通过，仍有证据需要补齐。",
        failed: "证据未通过，请根据本地检查结果恢复后重试。",
        alternative: "检测到满足验收目标的替代实现。",
      }[result],
      evidence: checks,
    },
    courseVersion,
  );
  const evidence = parsed.results[0];
  const observed = [...new Set(current.runs.map((run) => run.finding))].sort();
  evidence.simulation = {
    version: SKILL_SIMULATION_VERSION,
    runs: current.runs.map((run) => ({ ...run })),
    trigger_cases: current.triggerCases.map((item) => ({ ...item })),
    observed,
  };
  return evidence;
}

