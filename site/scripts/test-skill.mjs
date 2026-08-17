import assert from "node:assert/strict";
import test from "node:test";

import {
  SKILL_SCENARIOS,
  SKILL_TRIGGER_CASES,
  buildSkillEvidence,
  createSkillSession,
  recordSkillObservation,
  runSkillScenario,
  simulateSkillScenario,
  testSkillTriggerBoundary,
} from "../src/lib/skill-lab.mjs";

test("skill scenarios are deterministic and expose the four expected states", () => {
  for (const scenario of SKILL_SCENARIOS) {
    const first = simulateSkillScenario(scenario.id);
    const second = simulateSkillScenario(scenario.id);
    assert.deepEqual(first, second);
    assert.equal(first.deterministic, true);
    assert.equal(first.externalCall, false);
    assert.equal(first.finding, scenario.finding);
  }
});

test("a complete session records trigger positives and negatives", () => {
  let session = createSkillSession();
  for (const scenario of SKILL_SCENARIOS) {
    session = runSkillScenario(session, scenario.id);
    session = recordSkillObservation(session);
  }
  session = testSkillTriggerBoundary(session);

  const evidence = buildSkillEvidence(session, {
    courseVersion: "2.0.0",
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.lesson_id, "t17-skill");
  assert.equal(evidence.result, "passed");
  assert.deepEqual(evidence.simulation.observed, ["conflict", "needs-source", "ready", "untrusted-input"]);
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    [
      "skill-package-shaped",
      "trigger-boundary-tested",
      "evidence-scenarios-covered",
      "validation-script-passed",
      "security-boundary-tested",
      "offline-deterministic",
    ],
  );
  assert.deepEqual(
    evidence.simulation.trigger_cases.map((item) => item.observed),
    SKILL_TRIGGER_CASES.map((item) => item.expected),
  );
});

test("partial session remains valid evidence and identifies missing work", () => {
  let session = createSkillSession();
  session = runSkillScenario(session, "missing-source");
  session = recordSkillObservation(session);
  const evidence = buildSkillEvidence(session, { courseVersion: "2.0.0", checkedOn: "2026-08-13" });

  assert.equal(evidence.result, "partial");
  assert.equal(evidence.evidence.find((check) => check.id === "trigger-boundary-tested")?.result, "failed");
  assert.equal(evidence.simulation.runs[0].finding, "needs-source");
});

test("invalid scenarios and unsafe course versions are rejected", () => {
  assert.throws(() => simulateSkillScenario("send-to-network"), (error) => error.code === "unknown-scenario");
  assert.throws(
    () => buildSkillEvidence(createSkillSession(), { courseVersion: "C:\\private" }),
    (error) => error.code === "invalid-course-version",
  );
});
