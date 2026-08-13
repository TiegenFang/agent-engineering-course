import { spawnSync } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const labRoot = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(labRoot, '..', '..');
const inspector = join(
  repoRoot,
  'node_modules',
  '@modelcontextprotocol',
  'inspector',
  'clients',
  'launcher',
  'build',
  'index.js',
);
const serverPath = join(labRoot, 'server.mjs');

const temporaryRoot = await mkdtemp(join(tmpdir(), 'agent-course-t20-inspector-'));
const configPath = join(temporaryRoot, 'mcp.json');
await writeFile(
  configPath,
  JSON.stringify({
    mcpServers: {
      t20: {
        command: process.execPath,
        args: [serverPath],
        env: { MCP_FAULT: 'none', MCP_OUTPUT_ROOT: '' },
        protocolEra: 'modern',
      },
    },
  }),
  { encoding: 'utf8' },
);

try {
  const result = spawnSync(
    process.execPath,
    [
      inspector,
      '--cli',
      '--config',
      configPath,
      '--server',
      't20',
      '--method',
      'tools/list',
      '--format',
      'json',
    ],
    {
      cwd: repoRoot,
      encoding: 'utf8',
      windowsHide: true,
      timeout: 30000,
    },
  );

  if (result.error || result.status !== 0) {
    console.error('MCP Inspector check failed: local CLI did not complete.');
    process.exitCode = 1;
  } else {
    let parsed;
    try {
      parsed = JSON.parse(result.stdout);
    } catch {
      console.error('MCP Inspector check failed: CLI output was not JSON.');
      process.exitCode = 1;
    }
    const payload = parsed?.result ?? parsed;
    const names = Array.isArray(payload?.tools)
      ? payload.tools.map((tool) => tool?.name).filter((name) => typeof name === 'string')
      : [];
    if (!names.includes('telemetry.read') || !names.includes('report.publish')) {
      console.error('MCP Inspector check failed: expected tools were not listed.');
      process.exitCode = 1;
    } else {
      console.log(JSON.stringify({ inspector: 'passed', tools: names.sort() }));
    }
  }
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}
