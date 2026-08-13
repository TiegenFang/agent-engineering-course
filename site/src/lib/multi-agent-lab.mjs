/**
 * Deterministic fixture for the controlled single-agent / subagent comparison.
 *
 * The figures are deliberately fixed teaching inputs, not measurements from a
 * model provider. This lets learners inspect the trade-offs without calling a
 * model, reading a project, or exposing a real usage log in the public JSON.
 */

export const MULTI_AGENT_LESSON_ID = "t22-multi-agent";
export const MULTI_AGENT_VERSION = "1";
export const MULTI_AGENT_GOAL = "telemetry-report-v2";
export const MULTI_AGENT_ACCEPTANCE = Object.freeze([
  "valid-records-counted",
  "units-normalized",
  "report-produced",
  "verification-passed",
]);
export const MULTI_AGENT_SCENARIOS = Object.freeze([
  "independent-review",
  "overlap-conflict",
]);

const SHARED_CONTEXT = Object.freeze([
  "goal",
  "input-contract",
  "acceptance-contract",
]);

const comparisonProfiles = Object.freeze({
  "independent-review": Object.freeze({
    id: "comparison-independent-review",
    label: "边界清晰的并行复核",
    summary: "子任务不写同一输出；并行缩短墙钟时间，但使用和验证成本上升。",
    boundaries: Object.freeze([
      Object.freeze({ id: "quality-scan", owns: "input-validation" }),
      Object.freeze({ id: "report-outline", owns: "summary-outline" }),
      Object.freeze({ id: "acceptance-review", owns: "acceptance-check" }),
    ]),
    merge: "coordinator-verifies",
    conflict: "none",
    recovery: "not-required",
    recommendation: "consider-bounded-parallel",
    single: Object.freeze({ elapsed_seconds: 18, usage_units: 90, verification_units: 2 }),
    subagents: Object.freeze({ elapsed_seconds: 12, usage_units: 158, verification_units: 3 }),
  }),
  "overlap-conflict": Object.freeze({
    id: "comparison-overlap-conflict",
    label: "故意重叠写入并恢复",
    summary: "两个子代理争抢同一摘要输出；协调者重新分区、复核后仍达标，但不应采用该编排。",
    boundaries: Object.freeze([
      Object.freeze({ id: "draft-a", owns: "report-summary" }),
      Object.freeze({ id: "draft-b", owns: "report-summary" }),
      Object.freeze({ id: "acceptance-review", owns: "acceptance-check" }),
    ]),
    merge: "coordinator-repartitions",
    conflict: "shared-output-collision",
    recovery: "repartition-and-revalidate",
    recommendation: "do-not-adopt",
    single: Object.freeze({ elapsed_seconds: 18, usage_units: 90, verification_units: 2 }),
    subagents: Object.freeze({ elapsed_seconds: 31, usage_units: 225, verification_units: 5 }),
  }),
});

const expectedScenario = (scenario) => {
  const profile = comparisonProfiles[scenario];
  if (!profile) {
    const error = new Error(`Unknown controlled comparison scenario: ${scenario}`);
    error.code = "unknown-scenario";
    throw error;
  }
  return profile;
};

const cloneMetrics = (metrics, mode) => ({
  mode,
  accepted: true,
  elapsed_seconds: metrics.elapsed_seconds,
  usage_units: metrics.usage_units,
  verification_units: metrics.verification_units,
});

export const runControlledComparison = (scenario) => {
  const profile = expectedScenario(scenario);
  return {
    id: profile.id,
    scenario,
    label: profile.label,
    summary: profile.summary,
    goal: MULTI_AGENT_GOAL,
    acceptance: [...MULTI_AGENT_ACCEPTANCE],
    single: cloneMetrics(profile.single, "single"),
    subagents: cloneMetrics(profile.subagents, "subagents"),
    boundaries: profile.boundaries.map((boundary) => ({ ...boundary })),
    shared_context: [...SHARED_CONTEXT],
    merge: profile.merge,
    conflict: profile.conflict,
    recovery: profile.recovery,
    recommendation: profile.recommendation,
    offline: true,
    model_calls: 0,
    network_calls: 0,
  };
};

export const createMultiAgentSession = (scenario = "independent-review") => ({
  current: runControlledComparison(scenario),
  comparisons: [],
  lastComparison: null,
});

export const updateMultiAgentSession = (session, scenario) => ({
  ...session,
  current: runControlledComparison(scenario),
  lastComparison: null,
});

export const recordMultiAgentComparison = (session) => {
  if (!session?.current) {
    const error = new Error("Run a controlled comparison before recording it");
    error.code = "missing-comparison";
    throw error;
  }
  const comparison = session.current;
  if (session.comparisons.some((item) => item.scenario === comparison.scenario)) {
    const error = new Error("Each controlled scenario can be recorded once");
    error.code = "duplicate-scenario";
    throw error;
  }
  return {
    ...session,
    comparisons: [...session.comparisons, comparison],
    lastComparison: comparison,
  };
};

const check = (id, result) => ({ id, result: result ? "passed" : "failed" });

export const deriveMultiAgentChecks = (session) => {
  const comparisons = Array.isArray(session?.comparisons) ? session.comparisons : [];
  const hasSameGoal = comparisons.length > 0 && comparisons.every((comparison) => (
    comparison.goal === MULTI_AGENT_GOAL
    && JSON.stringify(comparison.acceptance) === JSON.stringify(MULTI_AGENT_ACCEPTANCE)
    && comparison.single.accepted
    && comparison.subagents.accepted
  ));
  const hasBoundaries = comparisons.every((comparison) => (
    comparison.boundaries.length > 0
    && JSON.stringify(comparison.shared_context) === JSON.stringify(SHARED_CONTEXT)
    && typeof comparison.merge === "string"
  ));
  const hasCosts = comparisons.every((comparison) => (
    [comparison.single, comparison.subagents].every((run) => (
      Number.isInteger(run.elapsed_seconds)
      && Number.isInteger(run.usage_units)
      && Number.isInteger(run.verification_units)
      && run.elapsed_seconds > 0
      && run.usage_units > 0
      && run.verification_units > 0
    ))
  ));
  const hasRecoveredConflict = comparisons.some((comparison) => (
    comparison.conflict === "shared-output-collision"
    && comparison.recovery === "repartition-and-revalidate"
    && comparison.subagents.accepted
  ));
  const hasDecision = comparisons.some((comparison) => comparison.recommendation === "do-not-adopt")
    && comparisons.every((comparison) => (
      comparison.recommendation === "consider-bounded-parallel"
      || comparison.recommendation === "do-not-adopt"
    ));
  const isOffline = comparisons.every((comparison) => (
    comparison.offline && comparison.model_calls === 0 && comparison.network_calls === 0
  ));

  return [
    check("same-goal-compared", hasSameGoal),
    check("task-boundaries-declared", hasBoundaries),
    check("time-usage-verification-compared", hasCosts),
    check("conflict-recovered", hasRecoveredConflict),
    check("decision-supported", hasDecision),
    check("offline-deterministic", isOffline),
  ];
};

const classify = (checks) => {
  if (checks.every((item) => item.result === "passed")) return "passed";
  if (checks.every((item) => item.result === "failed")) return "failed";
  return "partial";
};

export const buildMultiAgentEvidence = (session, { courseVersion, checkedOn } = {}) => {
  if (!courseVersion || typeof courseVersion !== "string") {
    const error = new Error("courseVersion is required");
    error.code = "invalid-course-version";
    throw error;
  }
  const checks = deriveMultiAgentChecks(session);
  const comparisons = Array.isArray(session?.comparisons) ? session.comparisons : [];
  const result = classify(checks);
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: courseVersion,
    lesson_id: MULTI_AGENT_LESSON_ID,
    result,
    anonymous: true,
    checked_on: checkedOn ?? new Date().toISOString().slice(0, 10),
    summary: {
      passed: "所有必需证据均已通过。",
      partial: "部分证据已通过，仍有证据需要补齐。",
      failed: "证据未通过，请根据本地检查结果恢复后重试。",
    }[result],
    evidence: checks,
    experiment: {
      version: MULTI_AGENT_VERSION,
      goal: MULTI_AGENT_GOAL,
      comparisons: comparisons.map((comparison) => ({
        id: comparison.id,
        scenario: comparison.scenario,
        goal: comparison.goal,
        acceptance: [...comparison.acceptance],
        single: { ...comparison.single },
        subagents: { ...comparison.subagents },
        boundaries: comparison.boundaries.map((boundary) => ({ ...boundary })),
        shared_context: [...comparison.shared_context],
        merge: comparison.merge,
        conflict: comparison.conflict,
        recovery: comparison.recovery,
        recommendation: comparison.recommendation,
        offline: comparison.offline,
      })),
      observed_modes: ["single", "subagents"],
      observed_boundaries: [...new Set(comparisons.flatMap((comparison) => comparison.boundaries.map((boundary) => boundary.owns)))].sort(),
      observed_conflicts: [...new Set(comparisons.map((comparison) => comparison.conflict))].sort(),
      observed_recoveries: [...new Set(comparisons.map((comparison) => comparison.recovery))].sort(),
      model_calls: 0,
      network_calls: 0,
    },
  };
};

export const scenarioLabels = Object.freeze(Object.fromEntries(
  MULTI_AGENT_SCENARIOS.map((scenario) => [scenario, comparisonProfiles[scenario].label]),
));

export const recommendationLabels = Object.freeze({
  "consider-bounded-parallel": "可在独立只读任务中继续比较",
  "do-not-adopt": "不采用多 Agent：保留单 Agent 基线",
});
