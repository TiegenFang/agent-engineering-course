import assert from "node:assert/strict";
import test from "node:test";

import {
  CONTEXT_BUDGET_PRESETS,
  DEFAULT_CONTEXT_BUDGET_INPUT,
  buildContextBudgetEvidence,
  createContextBudgetSession,
  recordContextBudgetObservation,
  simulateContextBudget,
  updateContextBudgetSession,
} from "../src/lib/context-budget.mjs";

test("context budget allocation is deterministic and reports the default as ready", () => {
  const first = simulateContextBudget(DEFAULT_CONTEXT_BUDGET_INPUT);
  const second = simulateContextBudget(DEFAULT_CONTEXT_BUDGET_INPUT);

  assert.deepEqual(first, second);
  assert.deepEqual(first.findings, []);
  assert.equal(first.primaryFinding, "ready");
  assert.equal(first.budget.inputBudget, 192);
  assert.equal(first.budget.droppedTotal, 0);
});

test("minimum boundary can exhaust all input while maximum boundary remains valid", () => {
  const minimum = simulateContextBudget({ ...DEFAULT_CONTEXT_BUDGET_INPUT, capacity: 64, outputReserve: 64 });
  const maximum = simulateContextBudget({ ...DEFAULT_CONTEXT_BUDGET_INPUT, capacity: 1024, outputReserve: 512 });

  assert.equal(minimum.boundary, true);
  assert.equal(minimum.budget.inputBudget, 0);
  assert.ok(minimum.findings.includes("insufficient"));
  assert.equal(maximum.boundary, true);
  assert.equal(maximum.budget.inputBudget, 512);
  assert.deepEqual(maximum.findings, []);
});

test("presets cover insufficient, pollution, and crowding as distinct findings", () => {
  const insufficient = simulateContextBudget(CONTEXT_BUDGET_PRESETS.insufficient);
  const pollution = simulateContextBudget(CONTEXT_BUDGET_PRESETS.pollution);
  const crowding = simulateContextBudget(CONTEXT_BUDGET_PRESETS.crowding);

  assert.ok(insufficient.findings.includes("insufficient"));
  assert.ok(pollution.findings.includes("pollution"));
  assert.equal(pollution.findings.includes("insufficient"), false);
  assert.ok(crowding.findings.includes("crowding"));
  assert.ok(crowding.segments.some((segment) => segment.dropped > 0));
});

test("session input changes preserve recorded observations and export only stable evidence", () => {
  let session = createContextBudgetSession(CONTEXT_BUDGET_PRESETS.normal);
  session = recordContextBudgetObservation(session);
  for (const name of ["insufficient", "pollution", "crowding"]) {
    session = updateContextBudgetSession(session, CONTEXT_BUDGET_PRESETS[name]);
    session = recordContextBudgetObservation(session);
  }

  const evidence = buildContextBudgetEvidence(session, {
    courseVersion: "2.0.0",
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.lesson_id, "t14-context-budget");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.anonymous, true);
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    ["working-set-selected", "risk-signals-observed", "boundary-tested", "offline-deterministic"],
  );
  assert.deepEqual(evidence.simulation.observed, ["crowding", "insufficient", "pollution"]);
  assert.equal("capacity" in evidence.simulation, false);
});

test("invalid and unsafe boundaries are rejected", () => {
  assert.throws(
    () => simulateContextBudget({ ...DEFAULT_CONTEXT_BUDGET_INPUT, capacity: 63 }),
    (error) => error.code === "invalid-capacity",
  );
  assert.throws(
    () => simulateContextBudget({ ...DEFAULT_CONTEXT_BUDGET_INPUT, outputReserve: 257, capacity: 256 }),
    (error) => error.code === "reserve-exceeds-capacity",
  );
});
