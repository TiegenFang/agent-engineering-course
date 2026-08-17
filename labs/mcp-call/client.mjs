import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { dirname, isAbsolute, join, resolve } from 'node:path';

import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';

const PROTOCOL_VERSION = '2026-07-28';
const LESSON_ID = 't20-mcp-call';
const TOOL_NAMES = ['telemetry.read', 'report.publish'];
const FAULTS = new Set(['none', 'transport', 'tool', 'data', 'protocol']);

function parseArgs(argv) {
  const options = {
    mode: 'live',
    fault: 'none',
    approve: false,
    inspector: false,
    output: null,
    keepOutput: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--offline') options.mode = 'offline-fallback';
    else if (arg === '--live') options.mode = 'live';
    else if (arg === '--approve') options.approve = true;
    else if (arg === '--inspector') options.inspector = true;
    else if (arg === '--keep-output') options.keepOutput = true;
    else if (arg === '--fault') options.fault = argv[++index] ?? '';
    else if (arg === '--output') options.output = argv[++index] ?? '';
    else if (arg === '--help') options.help = true;
    else throw new Error(`unknown option: ${arg}`);
  }
  if (!FAULTS.has(options.fault)) throw new Error('fault must be none, transport, tool, data, or protocol');
  if (options.output && !isAbsolute(resolve(options.output))) {
    throw new Error('output must be an explicit absolute path');
  }
  return options;
}

function printHelp() {
  console.log(
    [
      'T20 MCP call lab',
      '  node labs/mcp-call/client.mjs --live --approve --fault tool',
      '  node labs/mcp-call/client.mjs --offline',
      '  --approve       allow the bounded report.publish local write',
      '  --inspector     run the pinned official Inspector CLI tools/list check',
      '  --fault         inject transport|tool|data|protocol and recover',
      '  --output        write anonymous evidence JSON to an explicit path',
      '  --keep-output   keep the isolated local report directory for inspection',
    ].join('\n'),
  );
}

function stableFault(fault, observed, recovered) {
  return { id: fault, observed, recovered };
}

function classifyChecks(checks) {
  const results = checks.map((check) => check.result);
  if (results.every((result) => result === 'passed')) return 'passed';
  if (results.every((result) => result === 'failed')) return 'failed';
  if (results.every((result) => result === 'passed' || result === 'alternative') && results.includes('alternative')) {
    return 'alternative';
  }
  return 'partial';
}

function summaryForResult(result) {
  return {
    passed: '所有必需证据均已通过。',
    partial: '部分证据已通过，仍有证据需要补齐。',
    failed: '证据未通过，请根据本地检查结果恢复后重试。',
    alternative: '检测到满足验收目标的替代实现。',
  }[result];
}

function buildChecks(experiment) {
  const live = experiment.mode === 'live' && experiment.formal_mcp === true;
  const allTools = TOOL_NAMES.every((name) => experiment.tools_observed.includes(name));
  const faultRecovered = experiment.faults.some((item) => item.observed && item.recovered);
  const fallback = experiment.mode === 'offline-fallback';
  return [
    { id: 'transport-connected', result: live && experiment.transport === 'stdio' ? 'passed' : fallback ? 'alternative' : 'failed' },
    { id: 'discovery-bridge', result: live && experiment.discovery_source === 't19-tool-catalog-v1' && allTools ? 'passed' : fallback ? 'alternative' : 'failed' },
    { id: 'permission-confirmed', result: experiment.permission === 'confirmed' ? 'passed' : fallback ? 'passed' : 'failed' },
    { id: 'tool-called', result: live && experiment.call_completed ? 'passed' : fallback ? 'alternative' : 'failed' },
    { id: 'side-effect-bounded', result: ['bounded-local-write', 'none', 'blocked'].includes(experiment.side_effect) ? (fallback ? 'passed' : experiment.side_effect === 'blocked' ? 'failed' : 'passed') : 'failed' },
    { id: 'fault-observed', result: faultRecovered ? 'passed' : fallback ? 'alternative' : 'failed' },
    { id: 'fault-recovered', result: faultRecovered ? 'passed' : fallback ? 'alternative' : 'failed' },
    { id: 'no-sensitive-output', result: experiment.no_sensitive_output === true ? 'passed' : 'failed' },
    { id: 'inspector-checked', result: experiment.inspector === 'passed' ? 'passed' : fallback ? 'failed' : 'failed' },
    { id: 'fallback-explicit', result: fallback || live ? 'passed' : 'failed' },
  ];
}

function buildOfflineEvidence() {
  return {
    contract: 'agent-engineering-course/evidence',
    contract_version: '1',
    course_version: '2.0.0',
    lesson_id: LESSON_ID,
    result: 'partial',
    anonymous: true,
    checked_on: new Date().toISOString().slice(0, 10),
    summary: '部分证据已通过，仍有证据需要补齐。',
    evidence: [
      { id: 'transport-connected', result: 'alternative' },
      { id: 'discovery-bridge', result: 'alternative' },
      { id: 'permission-confirmed', result: 'passed' },
      { id: 'tool-called', result: 'alternative' },
      { id: 'side-effect-bounded', result: 'passed' },
      { id: 'fault-observed', result: 'alternative' },
      { id: 'fault-recovered', result: 'alternative' },
      { id: 'no-sensitive-output', result: 'passed' },
      { id: 'inspector-checked', result: 'failed' },
      { id: 'fallback-explicit', result: 'passed' },
    ],
    experiment: {
      version: '1',
      mode: 'offline-fallback',
      formal_mcp: false,
      protocol: 'offline-fixture-v1',
      transport: 'not-used',
      discovery_source: 'offline-tool-catalog',
      tools_observed: TOOL_NAMES,
      permission: 'not-requested',
      call_completed: false,
      side_effect: 'none',
      faults: [],
      inspector: 'not-run',
      no_sensitive_output: true,
    },
  };
}

function resultIsError(result) {
  return Boolean(result?.isError);
}

async function closeClient(client) {
  if (!client) return;
  try {
    await client.close();
  } catch {
    // A transport fault is already being classified; do not leak its message.
  }
}

async function connectAttempt({ fault, outputRoot }) {
  const serverPath = resolve(dirname(fileURLToPath(import.meta.url)), 'server.mjs');
  const client = new Client(
    { name: 'agent-course-t20-client', version: '2.0.0' },
    { versionNegotiation: { mode: { pin: PROTOCOL_VERSION } } },
  );
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [serverPath],
    cwd: resolve(dirname(serverPath), '..', '..'),
    env: {
      MCP_FAULT: fault,
      MCP_OUTPUT_ROOT: outputRoot,
    },
    stderr: 'ignore',
  });
  await client.connect(transport);
  return client;
}

async function callRead(client, fault) {
  const result = await client.callTool({
    name: 'telemetry.read',
    arguments: { deviceId: 'pump-01' },
  });
  if (resultIsError(result)) throw new Error('tool-failure');
  return result;
}

async function runLive(options, outputRoot) {
  const faults = [];
  let client;
  let readResult;
  let connected = false;
  let discovery = [];
  let recovered = options.fault === 'none' || options.fault === 'protocol';
  try {
    client = await connectAttempt({ fault: options.fault, outputRoot });
    connected = true;
    const listed = await client.listTools();
    discovery = listed.tools.map((tool) => tool.name).filter((name) => TOOL_NAMES.includes(name));
    if (options.fault === 'protocol') {
      let invalidObserved = false;
      try {
        const invalid = await client.callTool({ name: 'telemetry.read', arguments: {} });
        invalidObserved = resultIsError(invalid);
      } catch {
        invalidObserved = true;
      }
      if (invalidObserved) faults.push(stableFault('protocol', true, true));
      readResult = await callRead(client, 'none');
    } else if (options.fault !== 'none') {
      try {
        readResult = await callRead(client, options.fault);
      } catch {
        faults.push(stableFault(options.fault, true, false));
        await closeClient(client);
        client = await connectAttempt({ fault: 'none', outputRoot });
        readResult = await callRead(client, 'none');
        recovered = true;
        faults[faults.length - 1] = stableFault(options.fault, true, true);
      }
    } else {
      readResult = await callRead(client, 'none');
    }
  } catch (error) {
    if (options.fault !== 'none' && !faults.length) {
      faults.push(stableFault(options.fault, true, false));
    }
    await closeClient(client);
    if (!faults.length) throw error;
    client = await connectAttempt({ fault: 'none', outputRoot });
    const listed = await client.listTools();
    discovery = listed.tools.map((tool) => tool.name).filter((name) => TOOL_NAMES.includes(name));
    readResult = await callRead(client, 'none');
    recovered = true;
    faults[faults.length - 1] = stableFault(options.fault, true, true);
  }

  let permission = options.approve ? 'confirmed' : 'blocked';
  let sideEffect = options.approve ? 'bounded-local-write' : 'blocked';
  let callCompleted = Boolean(readResult) && !resultIsError(readResult);
  if (options.approve) {
    const published = await client.callTool({
      name: 'report.publish',
      arguments: { deviceId: 'pump-01', confirmed: true },
    });
    if (resultIsError(published)) throw new Error('publish-failure');
  } else {
    // The host refuses to send a side-effecting call until the human has
    // confirmed its bounded target and write semantics.
    permission = 'blocked';
    sideEffect = 'blocked';
  }
  const inspectorPassed = options.inspector ? runInspector() : false;
  await closeClient(client);
  const experiment = {
    version: '1',
    mode: 'live',
    formal_mcp: true,
    protocol: PROTOCOL_VERSION,
    transport: 'stdio',
    discovery_source: 't19-tool-catalog-v1',
    tools_observed: discovery.sort(),
    permission,
    call_completed: callCompleted,
    side_effect: sideEffect,
    faults,
    inspector: inspectorPassed ? 'passed' : 'not-run',
    no_sensitive_output: true,
  };
  const checks = buildChecks(experiment);
  return {
    contract: 'agent-engineering-course/evidence',
    contract_version: '1',
    course_version: '2.0.0',
    lesson_id: LESSON_ID,
    result: classifyChecks(checks),
    anonymous: true,
    checked_on: new Date().toISOString().slice(0, 10),
    summary: summaryForResult(classifyChecks(checks)),
    evidence: checks,
    experiment,
  };
}

function runInspector() {
  const scriptPath = fileURLToPath(new URL('./inspect.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [scriptPath], {
    cwd: resolve(dirname(scriptPath), '..', '..'),
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  });
  return !result.error && result.status === 0;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return 0;
  }
  if (options.mode === 'offline-fallback') {
    const evidence = buildOfflineEvidence();
    if (options.output) await writeEvidence(options.output, evidence);
    console.log(JSON.stringify(evidence, null, 2));
    return 0;
  }

  const temporaryRoot = await mkdtemp(join(tmpdir(), 'agent-course-t20-'));
  const outputRoot = options.output ? join(temporaryRoot, 'report') : temporaryRoot;
  let evidence;
  try {
    evidence = await runLive(options, outputRoot);
    if (options.output) await writeEvidence(options.output, evidence);
    console.log(JSON.stringify(evidence, null, 2));
    return 0;
  } finally {
    if (!options.keepOutput) await rm(temporaryRoot, { recursive: true, force: true });
  }
}

async function writeEvidence(path, evidence) {
  // Only the stable status document crosses the checker/browser seam. The
  // output path itself is never embedded in the document.
  const text = JSON.stringify(evidence, null, 2) + '\n';
  const target = resolve(path);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, text, { encoding: 'utf8' });
}

main().catch((error) => {
  const category = error instanceof Error && typeof error.name === 'string' ? error.name : 'UnknownError';
  console.error(`T20 MCP lab failed: ${category}`);
  process.exitCode = 1;
});
