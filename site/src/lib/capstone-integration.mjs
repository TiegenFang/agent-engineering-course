// Deterministic browser fixture for T25's shared capstone integration seam.
// It models evidence states only and never calls a model, network, filesystem,
// Coding Agent, GitHub, or MCP server.

export const CAPSTONE_INTEGRATION_VERSION = "1";
export const CAPSTONE_INTEGRATION_CHECK_IDS = [
  "track-selected",
  "problem-scoped",
  "context-memory-linked",
  "skill-mcp-bounded",
  "core-evidence-linked",
  "validation-recorded",
  "migration-recorded",
  "delivery-reviewed",
  "privacy-safe",
  "version-locked",
  "portfolio-exported",
  "offline-deterministic",
];

const TRACKS = Object.freeze({
  research: Object.freeze({ label: "科研结课轨道", delivery: "可复现研究工作流" }),
  enterprise: Object.freeze({ label: "企业结课轨道", delivery: "Issue-to-PR 工程工作流" }),
});
const FAULTS = new Set(["none", "missing-core", "unsafe-side-effect", "incomplete-delivery"]);

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
export function trackContract(track = "enterprise") {
  return clone(TRACKS[track] || TRACKS.enterprise);
}

export function buildCapstoneIntegrationRun(overrides = {}) {
  const run = {
    version: CAPSTONE_INTEGRATION_VERSION,
    track: "enterprise",
    fault: "none",
    problem: true,
    contextMemory: true,
    skillMcp: true,
    core: true,
    validation: true,
    migration: true,
    delivery: true,
    privacy: true,
    versionLock: true,
    portfolio: true,
    offline: true,
    ...overrides,
  };
  if (!TRACKS[run.track]) run.track = "enterprise";
  if (!FAULTS.has(run.fault)) run.fault = "none";
  if (run.fault === "missing-core") {
    run.contextMemory = false;
    run.core = false;
  }
  if (run.fault === "unsafe-side-effect") {
    run.skillMcp = false;
    run.privacy = false;
  }
  if (run.fault === "incomplete-delivery") {
    run.validation = false;
    run.delivery = false;
    run.portfolio = false;
  }
  const checks = [
    ["track-selected", Boolean(TRACKS[run.track])],
    ["problem-scoped", Boolean(run.problem)],
    ["context-memory-linked", Boolean(run.contextMemory)],
    ["skill-mcp-bounded", Boolean(run.skillMcp)],
    ["core-evidence-linked", Boolean(run.core)],
    ["validation-recorded", Boolean(run.validation)],
    ["migration-recorded", Boolean(run.migration)],
    ["delivery-reviewed", Boolean(run.delivery)],
    ["privacy-safe", Boolean(run.privacy)],
    ["version-locked", Boolean(run.versionLock)],
    ["portfolio-exported", Boolean(run.portfolio)],
    ["offline-deterministic", Boolean(run.offline)],
  ].map(([id, passed]) => ({ id, result: passed ? "passed" : "failed" }));
  return {
    version: run.version,
    id: "capstone-integration-run",
    track: run.track,
    trackContract: trackContract(run.track),
    fault: run.fault,
    problem: Boolean(run.problem),
    contextMemory: Boolean(run.contextMemory),
    skillMcp: Boolean(run.skillMcp),
    core: Boolean(run.core),
    validation: Boolean(run.validation),
    migration: Boolean(run.migration),
    delivery: Boolean(run.delivery),
    privacy: Boolean(run.privacy),
    versionLock: Boolean(run.versionLock),
    portfolio: Boolean(run.portfolio),
    offline: Boolean(run.offline),
    checks,
  };
}

export function summarizeCapstoneIntegrationRun(run) {
  const checks = Array.isArray(run?.checks) ? run.checks : [];
  const passed = checks.filter((check) => check.result === "passed").length;
  return {
    passed,
    total: CAPSTONE_INTEGRATION_CHECK_IDS.length,
    result: passed === CAPSTONE_INTEGRATION_CHECK_IDS.length ? "passed" : "partial",
    label: `${passed}/${CAPSTONE_INTEGRATION_CHECK_IDS.length} 项证据`,
  };
}

export function buildCapstoneIntegrationEvidence(run = buildCapstoneIntegrationRun()) {
  const normalized = run?.version === CAPSTONE_INTEGRATION_VERSION
    ? run
    : buildCapstoneIntegrationRun(run);
  const result = summarizeCapstoneIntegrationRun(normalized).result;
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    lesson_id: "t25-capstone-integration",
    result,
    anonymous: true,
    checked_on: "2026-08-13",
    summary: result === "passed" ? "所有必需证据均已通过。" : "部分证据已通过，仍有证据需要补齐。",
    evidence: normalized.checks,
    experiment: {
      version: CAPSTONE_INTEGRATION_VERSION,
      baseline_id: "telemetry-capstone-integration-v1",
      track: normalized.track,
      fault: normalized.fault,
      problem: normalized.problem,
      context_memory: normalized.contextMemory,
      skill_mcp: normalized.skillMcp,
      core: normalized.core,
      validation: normalized.validation,
      migration: normalized.migration,
      delivery: normalized.delivery,
      privacy: normalized.privacy,
      version_lock: normalized.versionLock,
      portfolio: normalized.portfolio,
      offline: normalized.offline,
    },
  };
}
