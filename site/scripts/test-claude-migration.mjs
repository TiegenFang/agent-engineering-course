import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = resolve(siteRoot, "..");
const checkerRoot = join(workspaceRoot, "checker");
const read = (relativePath) => readFileSync(join(workspaceRoot, relativePath), "utf8");

test("模块 3 页面公开变化输入、Claude-only/双工具路径和官方边界", () => {
  const page = read("site/src/content/docs/module-3-claude-migration.mdx");
  const task = read("labs/module-3/claude-starter/TASK.md");
  const sources = read("labs/module-3/claude-starter/worklog/official-sources.md");
  const script = read("labs/module-3/claude-migration.ps1");

  assert.match(page, /<EvidenceLoop\s+lessonId="t04-claude-migration"\s*\/>/);
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
  for (const token of [
    "pressure-night",
    "kPa",
    "psi",
    "bar",
    "claude-only",
    "dual-tool",
    "live_call = not-verified",
    "https://code.claude.com/docs/en/installation",
    "https://code.claude.com/docs/en/permissions",
    "https://code.claude.com/docs/en/checkpointing",
    "https://code.claude.com/docs/en/costs",
  ]) {
    assert.match(page, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(task, /pressure-report-v1/);
  assert.match(task, /不修改 `tests\/`/);
  assert.match(task, /不把本地 checker 的状态记录写成“Claude 已经被调用”的证明/);
  assert.match(sources, /2026-08-13/);
  assert.match(sources, /not-verified/);
  for (const stage of [
    "baseline",
    "clarify",
    "plan",
    "official-facts",
    "failure-observed",
    "change",
    "recovery",
    "review",
    "delivery",
  ]) {
    assert.match(script, new RegExp(`"${stage}"`));
  }
  assert.match(script, /OutputPath must be directly below/);
  assert.match(script, /live_call_not_claimed/);
  assert.doesNotMatch(script, /Start-Process\s+claude|\(&\s*claude|claude\s+-p/);
});

test("T10 内容契约和来源账本引用可解析的官方条目", () => {
  const content = JSON.parse(read("docs/contracts/content-contract.json"));
  const ledger = JSON.parse(read("docs/sources/source-ledger.json"));
  const lesson = content.lessons.find((item) => item.id === "t04-claude-migration");
  assert.ok(lesson, "T10 lesson metadata missing");
  assert.equal(lesson.verified_on, "2026-08-13");
  assert.deepEqual(lesson.prerequisites, ["t04-codex-repository-task"]);
  assert.deepEqual(lesson.sources, [
    "anthropic-claude-code-installation-t10",
    "anthropic-claude-code-workflows-t10",
    "anthropic-claude-code-permissions-t10",
    "anthropic-claude-code-checkpointing-t10",
    "anthropic-claude-code-costs-t10",
    "course-claude-migration-original",
  ]);
  const sourceIds = new Set(ledger.entries.map((entry) => entry.id));
  for (const sourceId of lesson.sources) assert.ok(sourceIds.has(sourceId), sourceId);
  assert.equal(ledger.entries.find((entry) => entry.id === "anthropic-claude-code-permissions-t10").url, "https://code.claude.com/docs/en/permissions");
});

test("Node seam 可以调用 T10 checker 的结构检查", () => {
  const result = spawnSync(
    process.env.PYTHON ?? "python",
    ["-m", "course_check", "check", "t04-claude-migration", "--root", workspaceRoot, "--json"],
    {
      cwd: checkerRoot,
      env: { ...process.env, PYTHONPATH: checkerRoot },
      encoding: "utf8",
    },
  );
  assert.equal(result.status, 0, result.stderr);
  const document = JSON.parse(result.stdout);
  assert.equal(document.lesson_id, "t04-claude-migration");
  assert.equal(document.result, "partial");
  assert.deepEqual(
    document.evidence.map((item) => item.id),
    [
      "claude-migration-page",
      "claude-migration-powershell",
      "claude-migration-starter",
      "claude-migration-official-facts",
      "claude-migration-evidence-executed",
    ],
  );
});
