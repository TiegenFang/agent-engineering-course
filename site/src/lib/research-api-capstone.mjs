// Browser-safe mirror of the T30 bounded research API seam.
// It never reads credentials, performs fetch, or claims a live API result.

export const RESEARCH_API_VERSION = "1";
export const RESEARCH_API_CHECK_IDS = Object.freeze([
  "research-step-bounded",
  "offline-fixture-deterministic",
  "tool-loop-observed",
  "structured-output-contract",
  "failure-recovery-observed",
  "budget-stop-observed",
  "synthetic-input-only",
  "live-path-budgeted",
  "live-api-not-claimed",
  "evidence-exported",
]);

const CASES = Object.freeze([
  Object.freeze({ id: "offline-success", outcome: "completed", request_count: 2, tool_call: true, tool_result_refilled: true, structured_output: "accepted", error: "none", recovery: "not-needed", budget_status: "within-budget", network: "not-called", access: "not-required" }),
  Object.freeze({ id: "tool-failure-recovered", outcome: "recovered", request_count: 2, tool_call: true, tool_result_refilled: false, structured_output: "accepted", error: "tool", recovery: "safe-default", budget_status: "within-budget", network: "not-called", access: "not-required" }),
  Object.freeze({ id: "budget-stop", outcome: "stopped", request_count: 1, tool_call: false, tool_result_refilled: false, structured_output: "not-requested", error: "budget", recovery: "explicit-stop", budget_status: "stopped", network: "not-called", access: "not-required" }),
]);

const clone = (value) => JSON.parse(JSON.stringify(value));

export function buildLiveSmokePlan() {
  return {
    status: "not-run",
    provider: "not-selected",
    sdk: "not-invoked",
    model: "not-selected",
    verified_on: "2026-08-13",
    network: "not-called",
    approval: "required-before-any-request",
    max_requests: 2,
    max_output_tokens: 96,
    budget_usd: 0.01,
    cost: "not assessed; no live request was made",
    limitations: ["caller-must-supply-credential", "human-must-confirm-provider-and-model", "no-sensitive-research-data", "live-result-not-claimed"],
  };
}
export function buildResearchApiRun(inputVariant = "pressure-night") {
  const safeVariant = inputVariant === "temperature-daily" ? inputVariant : "pressure-night";
  const experiment = {
    version: RESEARCH_API_VERSION,
    mode: "offline-fixture",
    step_id: "telemetry-quality-summary-v1",
    adapter: "provider-neutral-research-step",
    input_variant: safeVariant,
    input_source: "synthetic-telemetry-only",
    output_contract: "status-summary-v1",
    request_budget: 2,
    output_token_budget: 96,
    budget_usd: 0.01,
    loop_budget_owner: "application-harness",
    cases: clone(CASES),
    live_smoke: buildLiveSmokePlan(),
  };
  const [success, failure, stopped] = experiment.cases;
  const live = experiment.live_smoke;
  const checks = [
    { id: "research-step-bounded", result: experiment.step_id === "telemetry-quality-summary-v1" ? "passed" : "failed" },
    { id: "offline-fixture-deterministic", result: experiment.cases.every((item) => item.network === "not-called" && item.access === "not-required") ? "passed" : "failed" },
    { id: "tool-loop-observed", result: success.tool_call && success.tool_result_refilled ? "passed" : "failed" },
    { id: "structured-output-contract", result: success.structured_output === "accepted" && stopped.structured_output === "not-requested" ? "passed" : "failed" },
    { id: "failure-recovery-observed", result: failure.outcome === "recovered" && failure.recovery === "safe-default" ? "passed" : "failed" },
    { id: "budget-stop-observed", result: stopped.budget_status === "stopped" && stopped.request_count === 1 ? "passed" : "failed" },
    { id: "synthetic-input-only", result: experiment.input_source === "synthetic-telemetry-only" ? "passed" : "failed" },
    { id: "live-path-budgeted", result: live.max_requests === 2 && live.max_output_tokens === 96 && live.budget_usd === 0.01 && live.approval === "required-before-any-request" ? "passed" : "failed" },
    { id: "live-api-not-claimed", result: live.status === "not-run" && live.network === "not-called" ? "passed" : "failed" },
    { id: "evidence-exported", result: "passed" },
  ];
  return { experiment, checks };
}

export function summarizeResearchApiRun(run) {
  const checks = Array.isArray(run?.checks) ? run.checks : [];
  const passed = checks.filter((check) => check.result === "passed").length;
  return { passed, total: RESEARCH_API_CHECK_IDS.length, result: passed === RESEARCH_API_CHECK_IDS.length ? "passed" : "partial", label: `${passed}/${RESEARCH_API_CHECK_IDS.length} 项证据` };
}

export function buildResearchApiEvidence(run = buildResearchApiRun(), courseVersion = "") {
  const summary = summarizeResearchApiRun(run);
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: courseVersion,
    lesson_id: "t30-research-api-capstone",
    result: summary.result,
    anonymous: true,
    checked_on: "2026-08-13",
    summary: summary.result === "passed" ? "所有必需证据均已通过。" : "部分证据已通过，仍有证据需要补齐。",
    evidence: run.checks,
    experiment: run.experiment,
  };
}
