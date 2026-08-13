import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const labRoot = dirname(fileURLToPath(import.meta.url));
const client = resolve(labRoot, 'client.mjs');
const inspect = resolve(labRoot, 'inspect.mjs');

function run(script, args = []) {
  const result = spawnSync(process.execPath, [script, ...args], {
    cwd: resolve(labRoot, '..', '..'),
    encoding: 'utf8',
    windowsHide: true,
    timeout: 60000,
  });
  assert.equal(result.error, undefined, result.error?.message);
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

const offline = run(client, ['--offline']);
assert.equal(offline.lesson_id, 't20-mcp-call');
assert.equal(offline.experiment.formal_mcp, false);
assert.equal(offline.experiment.mode, 'offline-fallback');
assert.notEqual(offline.result, 'passed');

const live = run(client, ['--live', '--approve', '--fault', 'protocol', '--inspector']);
assert.equal(live.experiment.formal_mcp, true);
assert.equal(live.experiment.protocol, '2026-07-28');
assert.equal(live.experiment.transport, 'stdio');
assert.equal(live.experiment.permission, 'confirmed');
assert.equal(live.experiment.inspector, 'passed');
assert.deepEqual(live.experiment.tools_observed, ['report.publish', 'telemetry.read']);
assert.deepEqual(live.experiment.faults, [{ id: 'protocol', observed: true, recovered: true }]);

const inspectorEvidence = run(inspect);
assert.equal(inspectorEvidence.inspector, 'passed');
assert.deepEqual(inspectorEvidence.tools, ['report.publish', 'telemetry.read']);
console.log('MCP call Node transport, recovery, fallback, and Inspector tests passed');
