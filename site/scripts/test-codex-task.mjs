import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const workspaceRoot = resolve(siteRoot, "..");

const read = (relativePath) => readFileSync(resolve(workspaceRoot, relativePath), "utf8");

test("模块 3 页面公开真实仓库任务、官方来源和匿名证据入口", () => {
  const page = read("site/src/content/docs/module-3-codex-task.mdx");
  assert.match(page, /<EvidenceLoop\s+lessonId="t04-codex-repository-task"\s*\/>/);
  for (const heading of [
    "真实问题",
    "心智模型",
    "操作前预测",
    "主工具演示",
    "本地实验",
    "故障注入与恢复",
    "迁移挑战",
    "可核验成果",
    "风险、版本与来源卡片",
  ]) {
    assert.match(page, new RegExp(heading));
  }
  assert.match(page, /https:\/\/developers\.openai\.com\/codex\/cli\//);
  assert.match(page, /https:\/\/developers\.openai\.com\/codex\/agent-approvals-security/);
  assert.match(page, /不伪造 Codex、模型、账号或 API 结果/);
  assert.match(page, /未完成 live Codex 验收/);
  assert.match(page, /Initialize|initialize-codex-task\.ps1/);
});

test("模块 3 starter 把遥测输出和修改范围固定为可验收合同", () => {
  const task = read("labs/module-3/starter/TASK.md");
  const source = read("labs/module-3/starter/src/telemetry_report.py");
  const tests = read("labs/module-3/starter/tests/test_report.py");
  const script = read("labs/module-3/codex-task.ps1");
  assert.match(task, /F.*C/);
  assert.match(task, /不修改 `tests\/`/);
  assert.match(source, /telemetry-report-v1/);
  assert.match(tests, /20\.333/);
  for (const stage of ["baseline", "clarify", "plan", "failure-observed", "change", "recovery", "review", "delivery"]) {
    assert.match(script, new RegExp(`"${stage}"`));
  }
  assert.match(script, /api\[_-\]\?key/);
  assert.match(script, /OutputPath must be directly below/);
});
