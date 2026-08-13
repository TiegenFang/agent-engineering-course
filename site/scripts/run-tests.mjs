import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const testCommands = [
  ["--test", "scripts/test-course-shell.mjs"],
  ["--test", "scripts/test-agent-loop.mjs"],
  ["--test", "scripts/test-agent-instruction.mjs"],
  ["--test", "scripts/test-evidence-record.mjs"],
  ["scripts/assert-homepage.mjs"],
  ["scripts/assert-module-zero.mjs"],
];

for (const args of testCommands) {
  const result = spawnSync(process.execPath, args, {
    cwd: siteRoot,
    stdio: "inherit",
  });
  if (result.error) {
    console.error(`Site test process failed: ${result.error.message}`);
    process.exitCode = 1;
    break;
  }
  if (result.status !== 0) {
    process.exitCode = result.status ?? 1;
    break;
  }
}
