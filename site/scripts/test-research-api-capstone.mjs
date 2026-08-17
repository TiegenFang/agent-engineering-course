import assert from 'node:assert/strict';
import test from 'node:test';

import {
  RESEARCH_API_CHECK_IDS,
  buildResearchApiEvidence,
  buildResearchApiRun,
  summarizeResearchApiRun,
} from '../src/lib/research-api-capstone.mjs';

test('T30 offline fixture covers the bounded research step and all controls', () => {
  const run = buildResearchApiRun('pressure-night');
  assert.equal(run.experiment.mode, 'offline-fixture');
  assert.equal(run.experiment.input_source, 'synthetic-telemetry-only');
  assert.equal(run.experiment.live_smoke.status, 'not-run');
  assert.equal(summarizeResearchApiRun(run).result, 'passed');
  assert.deepEqual(run.checks.map((check) => check.id), RESEARCH_API_CHECK_IDS);
});
test('T30 keeps the budget and failure-recovery cases visible', () => {
  const run = buildResearchApiRun('temperature-daily');
  assert.equal(run.experiment.cases[1].recovery, 'safe-default');
  assert.equal(run.experiment.cases[2].budget_status, 'stopped');
  const evidence = buildResearchApiEvidence(run, '2.0.0');
  assert.equal(evidence.anonymous, true);
  assert.equal(evidence.experiment.live_smoke.network, 'not-called');
});
