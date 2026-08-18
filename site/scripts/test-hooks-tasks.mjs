import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_HOOKS_TASKS_INPUT,
  HOOKS_TASKS_PRESETS,
  buildHooksTasksEvidence,
  createHooksTasksSession,
  recordHooksTasksObservation,
  simulateHooksTasks,
  updateHooksTasksSession,
} from "../src/lib/hooks-tasks.mjs";

test("safe default deterministically covers trigger, deduplication, recovery and stop", () => {
  const first = simulateHooksTasks(DEFAULT_HOOKS_TASKS_INPUT);
  const second = simulateHooksTasks(DEFAULT_HOOKS_TASKS_INPUT);
  assert.deepEqual(first, second);
  assert.equal(first.run.triggered, true);
  assert.equal(first.run.deduplicated, 1);
  assert.equal(first.run.permission, "blocked");
  assert.equal(first.run.sideEffect, false);
  assert.equal(first.run.failureInjected, true);
  assert.equal(first.run.recovered, true);
  assert.equal(first.run.stopped, true);
  assert.equal(first.run.explicitTask, true);
});

test("schedule and background are not silently treated as automatic hooks", () => {
  for (const name of ["schedule", "background"]) {
    const result = simulateHooksTasks(HOOKS_TASKS_PRESETS[name]).run;
    assert.equal(result.triggered, false);
    assert.equal(result.sideEffect, false);
    assert.equal(name === "schedule", result.scheduleArmed);
    assert.equal(name === "background", result.backgroundStarted);
  }
});

test("permission and failure presets expose risk and stopping branches", () => {
  const allowed = simulateHooksTasks(HOOKS_TASKS_PRESETS.permission).run;
  assert.equal(allowed.permission, "allowed");
  assert.equal(allowed.sideEffect, true);

  const persistent = simulateHooksTasks(HOOKS_TASKS_PRESETS.failure).run;
  assert.equal(persistent.failureUnresolved, true);
  assert.equal(persistent.recovered, false);
  assert.equal(persistent.stopped, true);
  assert.equal(persistent.stopReason, "step-budget");
});

test("evidence contains stable states only and reaches passed with the safe run", () => {
  let session = createHooksTasksSession(DEFAULT_HOOKS_TASKS_INPUT);
  session = recordHooksTasksObservation(session);
  const evidence = buildHooksTasksEvidence(session, {
    courseVersion: "3.0.0",
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.lesson_id, "t21-hooks-tasks");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.anonymous, true);
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    [
      "trigger-observed",
      "deduplication-observed",
      "permission-boundary",
      "stop-condition",
      "failure-recovered",
      "side-effect-not-triggered",
      "explicit-task-recorded",
      "offline-deterministic",
    ],
  );
  assert.equal("event" in evidence.experiment.runs[0], false);
  assert.equal("command" in evidence.experiment, false);
});

test("recorded observations survive input changes", () => {
  let session = createHooksTasksSession(DEFAULT_HOOKS_TASKS_INPUT);
  session = recordHooksTasksObservation(session);
  session = updateHooksTasksSession(session, HOOKS_TASKS_PRESETS.explicitTask);
  assert.equal(session.runs.length, 1);
  session = recordHooksTasksObservation(session);
  assert.equal(session.runs.length, 2);
  assert.equal(session.runs[1].taskCreated, true);
});

test("invalid input and unsafe evidence boundaries are rejected", () => {
  assert.throws(
    () => simulateHooksTasks({ ...DEFAULT_HOOKS_TASKS_INPUT, maxSteps: 0 }),
    (error) => error.code === "invalid-maxSteps",
  );
  assert.throws(
    () => simulateHooksTasks({ ...DEFAULT_HOOKS_TASKS_INPUT, mode: "unknown" }),
    (error) => error.code === "invalid-mode",
  );
});
