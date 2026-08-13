import assert from 'node:assert/strict';
import test from 'node:test';

import {
  RESEARCH_CAPSTONE_CHECK_IDS,
  buildResearchEvidence,
  buildResearchRun,
  summarizeResearchRun,
} from '../src/lib/research-capstone.mjs';

test('T23 baseline is a deterministic partial run until migration/rubric are supplied', () => {
  const run = buildResearchRun({ input: 'temperature-daily', fault: 'none' });
  assert.equal(run.version, '1');
  assert.equal(run.offline, true);
  assert.equal(run.migration, false);
  assert.equal(summarizeResearchRun(run).result, 'partial');
  assert.deepEqual(run.checks.map((check) => check.id), RESEARCH_CAPSTONE_CHECK_IDS);
});
test('T23 pressure migration can complete the shared rubric offline', () => {
  const run = buildResearchRun({ input: 'pressure-night', fault: 'none' });
  const evidence = buildResearchEvidence(run);
  assert.equal(summarizeResearchRun(run).result, 'passed');
  assert.equal(evidence.lesson_id, 't23-research-capstone');
  assert.equal(evidence.anonymous, true);
  assert.equal(evidence.experiment.input, 'pressure-night');
  assert.equal(evidence.experiment.offline, true);
});

test('T23 faults remain visible and do not become a forged pass', () => {
  for (const fault of ['missing-values', 'stale-memory', 'mcp-denied']) {
    const run = buildResearchRun({ input: 'pressure-night', fault });
    assert.equal(summarizeResearchRun(run).result, 'partial');
    assert.ok(run.checks.some((check) => check.result === 'failed'));
  }
});
