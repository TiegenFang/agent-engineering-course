import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import test from "node:test";

const siteRoot = resolve(import.meta.dirname, "..");
const workspaceRoot = resolve(siteRoot, "..");
const read = (relativePath) => readFileSync(join(workspaceRoot, relativePath), "utf8");

test("T26 中文课程页公开离线 Agent Application loop 与边界", () => {
  const page = read("site/src/content/docs/module-11-agent-loop.mdx");
  const component = read("site/src/components/OfflineAgentLoop.astro");
  const readme = read("labs/api-agent-loop/README.md");

  assert.match(page, /模块 11A：离线最小 Agent loop/);
  assert.match(page, /真实问题/);
  assert.match(page, /操作前预测/);
  assert.match(page, /故障注入与恢复/);
  assert.match(page, /迁移挑战/);
  assert.match(page, /Codex 和 Claude Code/);
  assert.match(page, /EvidenceLoop lessonId="t26-offline-agent-loop"/);
  assert.match(component, /data-offline-agent-loop/);
  assert.match(component, /tool_call/);
  assert.match(component, /state_refill/);
  assert.match(component, /结构化输出/);
  assert.match(component, /max_steps/);
  assert.match(readme, /Python 标准库/);
  assert.match(readme, /tool-failure/);
  assert.match(readme, /invalid-args/);
  assert.match(readme, /retry-recovery/);
  assert.match(readme, /不会.*网络请求/);
});

test("T26 runner 保持标准库实现和五个固定 scenario", () => {
  const implementation = read("labs/api-agent-loop/agent_loop.py");
  const runner = read("labs/api-agent-loop/run.py");

  assert.match(implementation, /IMPLEMENTATION = "python-stdlib"/);
  assert.match(implementation, /FRAMEWORK = "none"/);
  for (const scenario of ["success", "tool-failure", "invalid-args", "budget-stop", "retry-recovery"]) {
    assert.match(implementation, new RegExp(`"${scenario}"`));
  }
  assert.match(implementation, /validate_structured_output/);
  assert.match(implementation, /max_steps/);
  assert.match(implementation, /state_refill/);
  assert.match(runner, /from agent_loop import main/);
});

test("T26 metadata and source ledger are linked", () => {
  const contract = read("docs/contracts/content-contract.json");
  const sources = read("docs/sources/source-ledger.json");

  assert.match(contract, /"id": "t26-offline-agent-loop"/);
  assert.match(contract, /"course-offline-agent-loop-original"/);
  assert.match(sources, /"id": "course-offline-agent-loop-original"/);
  assert.match(sources, /"id": "openai-responses-function-calling-t26"/);
  assert.match(sources, /"id": "anthropic-tool-use-t26"/);
});
