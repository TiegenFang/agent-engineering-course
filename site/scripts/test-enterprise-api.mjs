import test from "node:test";
import assert from "node:assert/strict";
import {
  ENTERPRISE_API_CHECK_IDS,
  estimateEnterpriseCost,
  evaluateEnterpriseFixture,
} from "../src/lib/enterprise-api.mjs";

test("T31 baseline keeps one bounded, recoverable, offline step", () => {
  assert.equal(estimateEnterpriseCost(), 0.00045);
  const result = evaluateEnterpriseFixture();
  assert.deepEqual(result.checks.map((check) => check.id), ENTERPRISE_API_CHECK_IDS);
  assert.ok(result.checks.every((check) => check.result === "passed"));
  assert.equal(result.experiment.requested_action, "draft-validation-plan");
  assert.equal(result.experiment.high_impact_executed, false);
  assert.equal(result.experiment.approval_required, true);
  assert.equal(result.experiment.live_api_called, false);
});

test("T31 budget stop happens before the model call", () => {
  const result = evaluateEnterpriseFixture({ scenario: "budget-stop" });
  assert.equal(result.budgetStatus, "stopped");
  assert.equal(result.experiment.model_call_started, false);
  assert.equal(result.checks.find((check) => check.id === "budget-enforced")?.result, "passed");
  assert.equal(result.checks.find((check) => check.id === "recovery-observed")?.result, "failed");
  assert.equal(result.liveApiCalled, false);
});
