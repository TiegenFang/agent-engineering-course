// Deterministic, browser-safe fixture for the T24 enterprise capstone.
// It models public workflow states only; it never reads files, calls a model,
// performs network requests, or writes to an enterprise repository.

export const ENTERPRISE_CAPSTONE_VERSION = "1";
export const ENTERPRISE_CAPSTONE_CHECK_IDS = [
  "issue-clarified",
  "context-recorded",
  "memory-governed",
  "skill-applied",
  "mcp-boundary",
  "change-evidence",
  "tests-evidence",
  "review-evidence",
  "delivery-evidence",
  "migration-complete",
  "rubric-complete",
  "offline-deterministic",
];

const INPUTS = Object.freeze({
  "feature-issue": Object.freeze({
    label: "功能 Issue",
    kind: "feature",
    title: "报告中增加夜班摘要",
  }),
  "bug-fix": Object.freeze({
    label: "缺陷 Issue",
    kind: "bug",
    title: "修复压力单位换算",
  }),
});

const BASELINE = Object.freeze({
  input: "feature-issue",
  context: true,
  memory: true,
  skill: true,
  mcp: true,
  change: true,
  tests: true,
  review: true,
  delivery: true,
  evidence: true,
  migration: false,
  rubric: false,
  offline: true,
  fault: "none",
});

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
export function inputContract(input = "feature-issue") {
  return clone(INPUTS[input] || INPUTS["feature-issue"]);
}

export function buildEnterpriseRun(overrides = {}) {
  const run = { ...BASELINE, ...overrides };
  if (!Object.hasOwn(INPUTS, run.input)) run.input = "feature-issue";
  const safeFaults = new Set([
    "none",
    "ambiguous-issue",
    "test-failure",
    "review-requested",
    "mcp-denied",
  ]);
  if (!safeFaults.has(run.fault)) run.fault = "none";
  if (run.fault === "ambiguous-issue") {
    run.context = false;
    run.change = false;
    run.tests = false;
    run.review = false;
    run.delivery = false;
    run.migration = false;
  }
  if (run.fault === "test-failure") {
    run.tests = false;
    run.delivery = false;
  }
  if (run.fault === "review-requested") {
    run.review = false;
    run.delivery = false;
  }
  if (run.fault === "mcp-denied") {
    run.mcp = false;
    run.delivery = false;
  }
  if (run.input === "bug-fix" && run.fault !== "ambiguous-issue") {
    run.migration = true;
  }
  if (run.input === "bug-fix" && run.fault === "none") run.rubric = true;

  const checks = [
    ["issue-clarified", run.context],
    ["context-recorded", run.context],
    ["memory-governed", run.memory],
    ["skill-applied", run.skill],
    ["mcp-boundary", run.mcp],
    ["change-evidence", run.change],
    ["tests-evidence", run.tests],
    ["review-evidence", run.review],
    ["delivery-evidence", run.delivery],
    ["migration-complete", run.migration],
    ["rubric-complete", run.rubric],
    ["offline-deterministic", run.offline],
  ].map(([id, passed]) => ({ id, result: passed ? "passed" : "failed" }));

  return {
    version: ENTERPRISE_CAPSTONE_VERSION,
    id: "enterprise-run",
    input: run.input,
    variant: inputContract(run.input),
    fault: run.fault,
    context: Boolean(run.context),
    memory: Boolean(run.memory),
    skill: Boolean(run.skill),
    mcp: Boolean(run.mcp),
    artifacts: {
      change: Boolean(run.change),
      tests: Boolean(run.tests),
      review: Boolean(run.review),
      delivery: Boolean(run.delivery),
      evidence: Boolean(run.evidence),
    },
    migration: Boolean(run.migration),
    rubric: Boolean(run.rubric),
    offline: Boolean(run.offline),
    checks,
  };
}

export function summarizeEnterpriseRun(run) {
  const checks = Array.isArray(run?.checks) ? run.checks : [];
  const passed = checks.filter((check) => check.result === "passed").length;
  return {
    passed,
    total: ENTERPRISE_CAPSTONE_CHECK_IDS.length,
    result: passed === ENTERPRISE_CAPSTONE_CHECK_IDS.length ? "passed" : "partial",
    label: `${passed}/${ENTERPRISE_CAPSTONE_CHECK_IDS.length} 项证据`,
  };
}

export function buildEnterpriseEvidence(run = buildEnterpriseRun()) {
  const normalized = run?.version === ENTERPRISE_CAPSTONE_VERSION
    ? run
    : buildEnterpriseRun(run);
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: "3.0.0",
    lesson_id: "t24-enterprise-capstone",
    result: summarizeEnterpriseRun(normalized).result,
    anonymous: true,
    checked_on: "2026-08-13",
    summary: summarizeEnterpriseRun(normalized).result === "passed"
      ? "所有必需证据均已通过。"
      : "部分证据已通过，仍有证据需要补齐。",
    evidence: normalized.checks,
    experiment: {
      version: ENTERPRISE_CAPSTONE_VERSION,
      baseline_id: "telemetry-report-issue-v1",
      input: normalized.input,
      context: normalized.context,
      memory: normalized.memory,
      skill: normalized.skill,
      mcp: normalized.mcp,
      artifacts: normalized.artifacts,
      migration: normalized.migration,
      rubric: normalized.rubric,
      offline: normalized.offline,
      fault: normalized.fault,
    },
  };
}
