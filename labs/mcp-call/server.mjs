import { mkdir, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';

import { McpServer } from '@modelcontextprotocol/server';
import { serveStdio } from '@modelcontextprotocol/server/stdio';
import { z } from 'zod';

const PROTOCOL_VERSION = '2026-07-28';
const fault = process.env.MCP_FAULT ?? 'none';
const outputRoot = process.env.MCP_OUTPUT_ROOT ?? '';
let readCalls = 0;

function textResult(text, isError = false) {
  return {
    content: [{ type: 'text', text }],
    ...(isError ? { isError: true } : {}),
  };
}

function createServer() {
  const server = new McpServer(
    {
      name: 'agent-course-t20-telemetry',
      version: '1.0.0',
    },
    {
      capabilities: { tools: {} },
    },
  );

  server.registerTool(
    'telemetry.read',
    {
      title: 'Read synthetic telemetry',
      description: 'Read one synthetic device status; no file or network side effect.',
      inputSchema: z.object({
        deviceId: z.enum(['pump-01', 'pump-02']),
      }),
      outputSchema: z.object({
        deviceId: z.string(),
        status: z.string(),
        sampleCount: z.number(),
        unit: z.string(),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ deviceId }) => {
      readCalls += 1;
      if (fault === 'transport' && readCalls === 1) {
        // Deliberately end the child process. The client must classify this as
        // a transport failure and reconnect with a fresh, known command.
        console.error('T20 injected transport fault');
        process.exit(17);
      }
      if (fault === 'tool') {
        return textResult('T20 injected tool failure; no side effect occurred.', true);
      }
      if (fault === 'data') {
        // The declared output schema intentionally rejects this response.
        return {
          content: [{ type: 'text', text: 'T20 injected data-shape failure.' }],
          structuredContent: { deviceId, status: 'ok' },
        };
      }
      return {
        content: [{ type: 'text', text: `Synthetic telemetry ${deviceId}: nominal.` }],
        structuredContent: {
          deviceId,
          status: 'nominal',
          sampleCount: 24,
          unit: 'kPa',
        },
      };
    },
  );

  server.registerTool(
    'report.publish',
    {
      title: 'Publish bounded local report',
      description: 'Write one synthetic report under the explicitly supplied lab output directory.',
      inputSchema: z.object({
        deviceId: z.enum(['pump-01', 'pump-02']),
        confirmed: z.boolean(),
      }),
      outputSchema: z.object({
        deviceId: z.string(),
        artifact: z.string(),
        sideEffect: z.literal('bounded-local-write'),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: true,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ deviceId, confirmed }) => {
      if (!confirmed) {
        return textResult('permission_denied: human confirmation is required before writing.', true);
      }
      if (!outputRoot) {
        return textResult('configuration_error: no explicit lab output directory.', true);
      }
      const safeRoot = resolve(outputRoot);
      await mkdir(safeRoot, { recursive: true });
      const artifact = 'published-report.json';
      await writeFile(
        join(safeRoot, artifact),
        JSON.stringify(
          {
            deviceId,
            status: 'nominal',
            generatedBy: 'agent-course-t20',
            protocol: PROTOCOL_VERSION,
          },
          null,
          2,
        ) + '\n',
        { encoding: 'utf8', flag: 'wx' },
      );
      return {
        content: [{ type: 'text', text: 'bounded local report written.' }],
        structuredContent: {
          deviceId,
          artifact,
          sideEffect: 'bounded-local-write',
        },
      };
    },
  );

  return server;
}

const handle = serveStdio(createServer, {
  legacy: 'reject',
  onerror: () => {
    // Keep stderr generic: never echo environment variables, paths, arguments,
    // or tool payloads into the evidence stream.
    console.error('T20 MCP server error');
  },
});

process.once('SIGINT', () => void handle.close());
process.once('SIGTERM', () => void handle.close());
