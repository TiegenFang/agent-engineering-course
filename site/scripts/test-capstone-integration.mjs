import assert from 'node:assert/strict';
import test from 'node:test';

import {
  CAPSTONE_INTEGRATION_CHECK_IDS,
  buildCapstoneIntegrationEvidence,
  buildCapstoneIntegrationRun,
  summarizeCapstoneIntegrationRun,
} from '../src/lib/capstone-integration.mjs';

test('T25 both tracks use the same complete offline contract', () => {
  for (const track of ['research', 'enterprise']) {
    const run = buildCapstoneIntegrationRun({ track, fault: 'none' });
    assert.equal(summarizeCapstoneIntegrationRun(run).result, 'passed');
    assert.deepEqual(run.checks.map((check) => check.id), CAPSTONE_INTEGRATION_CHECK_IDS);
    const evidence = buildCapstoneIntegrationEvidence(run);
    assert.equal(evidence.lesson_id, 't25-capstone-integration');
    assert.equal(evidence.anonymous, true);
    assert.equal(evidence.experiment.track, track);
    assert.equal(evidence.experiment.offline, true);
  }
});
test('T25 faults remain partial and visible', () => {
  for (const fault of ['missing-core', 'unsafe-side-effect', 'incomplete-delivery']) {
    const run = buildCapstoneIntegrationRun({ track: 'enterprise', fault });
    assert.equal(summarizeCapstoneIntegrationRun(run).result, 'partial');
    assert.ok(run.checks.some((check) => check.result === 'failed'));
  }
});
