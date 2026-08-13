// Deterministic, browser-safe fixture for the T23 research capstone.
// It models evidence states only; it never reads a file, calls a model, or
// performs network/file-system side effects.

export const RESEARCH_CAPSTONE_VERSION = "1";
export const RESEARCH_CAPSTONE_CHECK_IDS = [
  "context-recorded",
  "memory-governed",
  "skill-applied",
  "mcp-boundary",
  "script-reproducible",
  "figure-produced",
  "record-complete",
  "report-complete",
  "evidence-exported",
  "migration-complete",
  "rubric-complete",
  "offline-deterministic",
];

const BASELINE = Object.freeze({
  input: "temperature-daily",
  context: true,
  memory: true,
  skill: true,
  mcp: true,
  script: true,
  figure: true,
  record: true,
  report: true,
  evidence: true,
  migration: false,
  rubric: false,
  offline: true,
  fault: "none",
});

const VARIANTS = Object.freeze({
  "temperature-daily": Object.freeze({
    label: "日间温度",
    subject: "temperature",
    unit: "°C",
    limit: 5,
  }),
  "pressure-night": Object.freeze({
    label: "夜班压力",
    subject: "pressure",
    unit: "kPa",
    limit: 3,
  }),
});

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function variantContract(input = "temperature-daily") {
  return clone(VARIANTS[input] || VARIANTS["temperature-daily"]);
}

export function buildResearchRun(overrides = {}) {
  const run = { ...BASELINE, ...overrides };
  const variant = variantContract(run.input);
  const safeFaults = new Set(["none", "missing-values", "stale-memory", "mcp-denied"]);
  if (!safeFaults.has(run.fault)) run.fault = "none";
  run.migration = run.input === "pressure-night";
  run.rubric = run.input === "pressure-night" && run.fault === "none";
  if (run.fault !== "none") run.report = false;
  if (run.fault === "missing-values") run.figure = false;
  if (run.fault === "stale-memory") run.memory = false;
  if (run.fault === "mcp-denied") run.mcp = false;
  const checks = [
    ["context-recorded", run.context],
    ["memory-governed", run.memory],
    ["skill-applied", run.skill],
    ["mcp-boundary", run.mcp],
    ["script-reproducible", run.script],
    ["figure-produced", run.figure],
    ["record-complete", run.record],
    ["report-complete", run.report],
    ["evidence-exported", run.evidence],
    ["migration-complete", run.migration],
    ["rubric-complete", run.rubric],
    ["offline-deterministic", run.offline],
  ].map(([id, passed]) => ({ id, result: passed ? "passed" : "failed" }));
  return {
    version: RESEARCH_CAPSTONE_VERSION,
    id: "research-run",
    input: run.input,
    variant,
    fault: run.fault,
    context: Boolean(run.context),
    memory: Boolean(run.memory),
    skill: Boolean(run.skill),
    mcp: Boolean(run.mcp),
    artifacts: {
      script: Boolean(run.script),
      figure: Boolean(run.figure),
      record: Boolean(run.record),
      report: Boolean(run.report),
      evidence: Boolean(run.evidence),
    },
    migration: Boolean(run.migration),
    rubric: Boolean(run.rubric),
    offline: Boolean(run.offline),
    checks,
  };
}

export function summarizeResearchRun(run) {
  const checks = Array.isArray(run?.checks) ? run.checks : [];
  const passed = checks.filter((check) => check.result === "passed").length;
  return {
    passed,
    total: RESEARCH_CAPSTONE_CHECK_IDS.length,
    result: passed === RESEARCH_CAPSTONE_CHECK_IDS.length ? "passed" : "partial",
    label: `${passed}/${RESEARCH_CAPSTONE_CHECK_IDS.length} 项证据`,
  };
}

export function buildResearchEvidence(run = buildResearchRun()) {
  const normalized = run?.version === RESEARCH_CAPSTONE_VERSION ? run : buildResearchRun(run);
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    lesson_id: "t23-research-capstone",
    result: summarizeResearchRun(normalized).result,
    anonymous: true,
    checked_on: "2026-08-13",
    summary: summarizeResearchRun(normalized).result === "passed"
      ? "所有必需证据均已通过。"
      : "部分证据已通过，仍有证据需要补齐。",
    evidence: normalized.checks,
    experiment: {
      version: RESEARCH_CAPSTONE_VERSION,
      baseline_id: "telemetry-research-v1",
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
