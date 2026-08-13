/**
 * Browser-side deterministic mirror of the T29 production evaluator.
 *
 * This module intentionally has no provider SDK, fetch call, or credential
 * access. It demonstrates the evaluation control plane before a learner is
 * allowed to spend money on a live API.
 */

export const PRODUCTION_EVALUATOR_VERSION = "production-evaluator-v1";
export const PRODUCTION_CHECK_IDS = Object.freeze([
  "success-case",
  "failure-case",
  "variant-input",
  "recovery-observed",
  "budget-gate",
  "log-redaction",
]);

export function estimateCostUsd({ inputTokens, outputTokens, inputRate = 0.001, outputRate = 0.002 }) {
  if (!Number.isInteger(inputTokens) || inputTokens < 0 || !Number.isInteger(outputTokens) || outputTokens < 0) {
    throw new Error("token counts must be non-negative integers");
  }
  return Number(((inputTokens / 1000) * inputRate + (outputTokens / 1000) * outputRate).toFixed(6));
}

export function evaluateProductionFixture({
  inputId = "baseline-pressure-v1",
  device = "synthetic-device-a",
  records = 6,
  changedInput = true,
  injectFailure = true,
  promptTokens = 240,
  maxOutputTokens = 160,
  budgetUsd = 0.01,
} = {}) {
  const outputTokens = Math.min(maxOutputTokens, 96);
  const estimatedCostUsd = estimateCostUsd({ inputTokens: promptTokens, outputTokens });
  const budgetAllowed = estimatedCostUsd <= budgetUsd;
  const failureObserved = injectFailure === true;
  const recoveryObserved = failureObserved && budgetAllowed;
  const checks = [
    { id: "success-case", result: budgetAllowed && records >= 1 ? "passed" : "failed" },
    { id: "failure-case", result: failureObserved ? "passed" : "failed" },
    { id: "variant-input", result: changedInput && device !== "baseline-device" ? "passed" : "failed" },
    { id: "recovery-observed", result: recoveryObserved ? "passed" : "failed" },
    { id: "budget-gate", result: budgetAllowed ? "passed" : "failed" },
    { id: "log-redaction", result: "passed" },
  ];
  const events = ["evaluation-start"];
  if (!budgetAllowed) events.push("budget-stop");
  events.push("case-result");
  if (recoveryObserved) events.push("recovery");
  events.push("evaluation-end");
  return {
    evaluatorVersion: PRODUCTION_EVALUATOR_VERSION,
    inputId,
    checks,
    estimatedCostUsd,
    budgetUsd,
    budgetStatus: budgetAllowed ? "allowed" : "stopped",
    logs: { eventCount: events.length, events },
    liveApiCalled: false,
  };
}
