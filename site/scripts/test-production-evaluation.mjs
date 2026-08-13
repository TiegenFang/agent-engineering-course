import test from "node:test";
import assert from "node:assert/strict";
import { estimateCostUsd, evaluateProductionFixture, PRODUCTION_CHECK_IDS } from "../src/lib/production-evaluation.mjs";

test("T29 evaluator has stable cost estimate and all gates", () => {
  assert.equal(estimateCostUsd({ inputTokens: 240, outputTokens: 96 }), 0.000432);
  const result = evaluateProductionFixture();
  assert.deepEqual(result.checks.map((check) => check.id), PRODUCTION_CHECK_IDS);
  assert.ok(result.checks.every((check) => check.result === "passed"));
  assert.equal(result.budgetStatus, "allowed");
  assert.equal(result.liveApiCalled, false);
});

test("T29 evaluator changes input instead of copying baseline", () => {
  const result = evaluateProductionFixture({ inputId: "variant-temperature-v1", device: "synthetic-device-b" });
  assert.equal(result.inputId, "variant-temperature-v1");
  assert.equal(result.checks.find((check) => check.id === "variant-input")?.result, "passed");
});

test("T29 evaluator stops before a model call when budget is too small", () => {
  const result = evaluateProductionFixture({ budgetUsd: 0.0001 });
  assert.equal(result.budgetStatus, "stopped");
  assert.equal(result.liveApiCalled, false);
  assert.equal(result.logs.events.includes("budget-stop"), true);
  assert.equal(result.checks.find((check) => check.id === "budget-gate")?.result, "failed");
});
