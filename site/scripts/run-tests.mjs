import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const testCommands = [
  ["--test", "scripts/test-course-shell.mjs"],
  ["--test", "scripts/test-agent-loop.mjs"],
  ["--test", "scripts/test-offline-agent-loop.mjs"],
  ["--test", "scripts/test-agent-instruction.mjs"],
  ["--test", "scripts/test-context-budget.mjs"],
  ["--test", "scripts/test-hooks-tasks.mjs"],
  ["--test", "scripts/test-codex-task.mjs"],
  ["--test", "scripts/test-claude-migration.mjs"],
  ["--test", "scripts/test-context-recovery.mjs"],
  ["--test", "scripts/test-skill.mjs"],
  ["--test", "scripts/test-plugin-audit.mjs"],
  ["../labs/mcp-call/test-mcp-call.mjs"],
  ["--test", "scripts/test-openai-responses.mjs"],
  ["--test", "scripts/test-research-capstone.mjs"],
  ["--test", "scripts/test-anthropic-messages.mjs"],
  ["--test", "scripts/test-production-evaluation.mjs"],
  ["--test", "scripts/test-multi-agent.mjs"],
  ["--test", "scripts/test-research-api-capstone.mjs"],
  ["--test", "scripts/test-enterprise-api.mjs"],
  ["--test", "scripts/test-enterprise-capstone.mjs"],
  ["--test", "scripts/test-capstone-integration.mjs"],
  ["--test", "scripts/test-evidence-record.mjs"],
  ["--test", "scripts/test-project-rules.mjs"],
  ["--test", "scripts/test-mcp-discovery.mjs"],
  ["scripts/assert-homepage.mjs"],
  ["scripts/assert-module-zero.mjs"],
  ["scripts/assert-module-four.mjs"],
  ["--test", "scripts/test-memory.mjs"],
  ["--test", "scripts/test-byo-key.mjs"],
  ["--test", "scripts/test-start-progress.mjs"],
  ["--test", "scripts/test-loop-track.mjs"],
  ["--test", "scripts/test-start-call-summary.mjs"],
  ["--test", "scripts/test-dialogue-basics.mjs"],
  ["--test", "scripts/test-terminal-bridge.mjs"],
  ["--test", "scripts/test-progress-wizard.mjs"],
  ["--test", "scripts/test-research-capstone.mjs"],
  ["scripts/assert-module-six.mjs"],
  ["scripts/assert-module-seven.mjs"],
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
