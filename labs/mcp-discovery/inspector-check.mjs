/**
 * Run the official MCP Inspector CLI against the real Python stdio server.
 *
 * This wrapper records only capability names, method IDs and exit status.  It
 * never stores Inspector's raw output, local paths, environment variables or
 * credentials in the evidence file.
 */

import assert from "node:assert/strict";
import { access, readFile, writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const serverPath = path.join(here, "mcp_server.py");
const inspectorVersion = "2.2.0";
const expected = {
  "tools/list": "summarize_telemetry",
  "resources/list": "telemetry://demo/snapshot",
  "prompts/list": "review-telemetry",
};

const parseArgs = () => {
  const args = process.argv.slice(2);
  const outputIndex = args.indexOf("--output");
  const pythonIndex = args.indexOf("--python");
  return {
    output: outputIndex >= 0 ? args[outputIndex + 1] : undefined,
    python: pythonIndex >= 0 ? args[pythonIndex + 1] : process.env.MCP_PYTHON || "python",
  };
};

const runInspector = (python, method) => new Promise((resolve, reject) => {
  // Spawning a .cmd shim directly can return EINVAL on some Windows Node
  // builds.  Invoke npm's npx entry point through the current Node binary so
  // the argument array remains shell-free and path-safe.
  const npxEntry = process.platform === "win32"
    ? path.join(path.dirname(process.execPath), "node_modules", "npm", "bin", "npx-cli.js")
    : "npx";
  const command = process.platform === "win32" ? process.execPath : npxEntry;
  const childArgs = [
    "--yes",
    `@modelcontextprotocol/inspector@${inspectorVersion}`,
    "--cli",
    python,
    serverPath,
    "--method",
    method,
    "--format",
    "json",
  ];
  const child = spawn(command, process.platform === "win32" ? [npxEntry, ...childArgs] : childArgs, {
    cwd: here,
    windowsHide: true,
  });
  let stdout = "";
  let stderr = "";
  const timer = setTimeout(() => {
    child.kill();
    reject(new Error(`${method} Inspector command timed out`));
  }, 45_000);
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  child.once("error", (error) => {
    clearTimeout(timer);
    reject(error);
  });
  child.once("close", (code) => {
    clearTimeout(timer);
    if (code !== 0) {
      reject(new Error(`${method} Inspector exited ${code}: ${stderr.slice(-500)}`));
      return;
    }
    try {
      resolve(JSON.parse(stdout));
    } catch (error) {
      reject(new Error(`${method} Inspector returned non-JSON output: ${error.message}`));
    }
  });
});

const extractNames = (method, payload) => {
  const result = payload?.result;
  if (!result || typeof result !== "object") return [];
  if (method === "tools/list") return (result.tools || []).map((item) => item.name).sort();
  if (method === "resources/list") return (result.resources || []).map((item) => item.uri).sort();
  if (method === "prompts/list") return (result.prompts || []).map((item) => item.name).sort();
  return [];
};

const main = async () => {
  const args = parseArgs();
  await access(serverPath);
  assert.equal(typeof args.python, "string");
  const methods = Object.keys(expected);
  const observations = {};
  for (const method of methods) {
    const payload = await runInspector(args.python, method);
    const names = extractNames(method, payload);
    observations[method] = {
      ok: names.includes(expected[method]),
      count: names.length,
      expected_name_found: names.includes(expected[method]),
    };
  }
  const value = {
    schema_version: "1",
    status: Object.values(observations).every((item) => item.ok) ? "passed" : "failed",
    inspector_version: inspectorVersion,
    transport: "stdio",
    methods,
    observations,
  };
  if (args.output) {
    await writeFile(path.resolve(args.output), `${JSON.stringify(value, null, 2)}\n`, "utf8");
  }
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
};

main().catch((error) => {
  process.stderr.write(`Inspector check failed: ${error.message}\n`);
  process.exitCode = 1;
});
