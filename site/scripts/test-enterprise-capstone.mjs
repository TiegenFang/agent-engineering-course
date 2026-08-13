import test from "node:test";
import assert from "node:assert/strict";

import {
  buildEnterpriseEvidence,
  buildEnterpriseRun,
  ENTERPRISE_CAPSTONE_CHECK_IDS,
  summarizeEnterpriseRun,
} from "../src/lib/enterprise-capstone.mjs";

test("enterprise capstone keeps feature baseline partial until migration", () => {
  const run = buildEnterpriseRun();
  assert.equal(summarizeEnterpriseRun(run).label, "10/12 项证据");
  assert.equal(summarizeEnterpriseRun(run).result, "partial");
  assert.equal(run.checks.length, ENTERPRISE_CAPSTONE_CHECK_IDS.length);
});
test("enterprise capstone derives a complete bug migration evidence", () => {
  const run = buildEnterpriseRun({ input: "bug-fix" });
  const evidence = buildEnterpriseEvidence(run);
  assert.equal(summarizeEnterpriseRun(run).result, "passed");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.experiment.input, "bug-fix");
  assert.equal(evidence.experiment.artifacts.delivery, true);
});

test("enterprise capstone faults remain partial and never execute side effects", () => {
  for (const fault of ["ambiguous-issue", "test-failure", "review-requested", "mcp-denied"]) {
    const run = buildEnterpriseRun({ input: "feature-issue", fault });
    assert.equal(summarizeEnterpriseRun(run).result, "partial");
    assert.equal(run.offline, true);
    assert.equal(run.fault, fault);
  }
});
