import assert from "node:assert/strict";
import test from "node:test";

import {
  MULTI_AGENT_ACCEPTANCE,
  MULTI_AGENT_GOAL,
  buildMultiAgentEvidence,
  createMultiAgentSession,
  recordMultiAgentComparison,
  runControlledComparison,
  updateMultiAgentSession,
} from "../src/lib/multi-agent-lab.mjs";

test("single and subagent paths use the same deterministic acceptance goal", () => {
  const first = runControlledComparison("independent-review");
  const second = runControlledComparison("independent-review");

  assert.deepEqual(first, second);
  assert.equal(first.goal, MULTI_AGENT_GOAL);
  assert.deepEqual(first.acceptance, MULTI_AGENT_ACCEPTANCE);
  assert.equal(first.single.accepted, true);
  assert.equal(first.subagents.accepted, true);
  assert.equal(first.single.elapsed_seconds > first.subagents.elapsed_seconds, true);
  assert.equal(first.single.usage_units < first.subagents.usage_units, true);
  assert.equal(first.single.verification_units < first.subagents.verification_units, true);
  assert.equal(first.conflict, "none");
});

test("overlapping writes recover to the same acceptance goal without forcing adoption", () => {
  const result = runControlledComparison("overlap-conflict");

  assert.equal(result.goal, MULTI_AGENT_GOAL);
  assert.deepEqual(result.acceptance, MULTI_AGENT_ACCEPTANCE);
  assert.equal(result.conflict, "shared-output-collision");
  assert.equal(result.recovery, "repartition-and-revalidate");
  assert.equal(result.recommendation, "do-not-adopt");
  assert.equal(result.subagents.accepted, true);
  assert.equal(result.subagents.elapsed_seconds > result.single.elapsed_seconds, true);
  assert.equal(result.subagents.usage_units > result.single.usage_units, true);
  assert.equal(result.subagents.verification_units > result.single.verification_units, true);
  assert.equal(result.model_calls, 0);
  assert.equal(result.network_calls, 0);
});

test("recorded scenarios export a complete anonymous comparison envelope", () => {
  let session = createMultiAgentSession();
  for (const scenario of ["independent-review", "overlap-conflict"]) {
    session = updateMultiAgentSession(session, scenario);
    session = recordMultiAgentComparison(session);
  }

  const evidence = buildMultiAgentEvidence(session, {
    courseVersion: "0.1.0-alpha",
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.lesson_id, "t22-multi-agent");
  assert.equal(evidence.result, "passed");
  assert.deepEqual(evidence.evidence.map((check) => check.id), [
    "same-goal-compared",
    "task-boundaries-declared",
    "time-usage-verification-compared",
    "conflict-recovered",
    "decision-supported",
    "offline-deterministic",
  ]);
  assert.equal(evidence.experiment.comparisons.length, 2);
  assert.equal(evidence.experiment.model_calls, 0);
  assert.equal(evidence.experiment.network_calls, 0);
  assert.equal(JSON.stringify(evidence).includes("prompt"), false);
  assert.equal(JSON.stringify(evidence).includes("report-summary"), true);
});

test("unknown or duplicated scenarios are rejected", () => {
  assert.throws(
    () => runControlledComparison("parallel-download"),
    (error) => error.code === "unknown-scenario",
  );
  let session = createMultiAgentSession("independent-review");
  session = recordMultiAgentComparison(session);
  assert.throws(
    () => recordMultiAgentComparison(session),
    (error) => error.code === "duplicate-scenario",
  );
});
