import assert from "node:assert/strict";
import { readFileSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  InstructionStateError,
  PREDICTION_OPTIONS,
  buildInstructionEvidence,
  createInstructionSession,
  defaultEngineeredInstruction,
  ambiguousInstruction,
  runInstructionComparison,
  selectInstructionInput,
  submitInstructionPrediction,
} from "../src/lib/instruction-engine.mjs";

const COURSE_VERSION = "0.1.0-foundation";
const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = resolve(siteRoot, "..");
const checkerRoot = join(workspaceRoot, "checker");

const predictAndRun = (session, scenarioId, variantId = "temperature-daily", instruction) => {
  let current = selectInstructionInput(session, {
    scenarioId,
    variantId,
    engineeredInstruction: instruction ?? defaultEngineeredInstruction(variantId, scenarioId),
  });
  current = submitInstructionPrediction(current, PREDICTION_OPTIONS[0]);
  return runInstructionComparison(current);
};

test("模块 2 页面公开同基线对照、故障场景和匿名 evidence 入口", () => {
  const page = readFileSync(
    new URL("../src/content/docs/module-2-agent-instruction.mdx", import.meta.url),
    "utf8",
  );
  const component = readFileSync(
    new URL("../src/components/InstructionLab.astro", import.meta.url),
    "utf8",
  );

  assert.match(page, /<InstructionLab\s*\/>/);
  assert.match(page, /<EvidenceLoop\s+lessonId="t03-agent-instruction"\s*\/>/);
  assert.match(component, /<noscript>/);
  assert.match(component, /规则冲突/);
  assert.match(component, /提示注入/);
  assert.match(component, /过长指令/);
  assert.match(component, /aria-live="polite"/);
});

test("同一基线产生可比较的模糊/工程化结果", () => {
  let session = createInstructionSession();
  session = predictAndRun(session, "baseline");
  assert.equal(session.latest.baselineId, "telemetry-report-v1");
  assert.deepEqual(session.latest.runs.map((run) => run.id), ["ambiguous", "engineered"]);
  assert.equal(session.latest.runs[0].status, "failed");
  assert.equal(session.latest.runs[0].outcome, "under-specified");
  assert.equal(session.latest.runs[1].status, "passed");
  assert.equal(session.latest.runs[1].outcome, "controlled");
  assert.match(session.latest.difference, /明确的目标/);
});

test("冲突、提示注入和过长指令各自产生可解释失败证据", () => {
  let session = createInstructionSession();
  session = predictAndRun(session, "conflict");
  assert.equal(session.latest.runs[0].outcome, "conflict-unresolved");
  assert.equal(session.latest.runs[1].outcome, "conflict-contained");
  session = predictAndRun(session, "injection");
  assert.equal(session.latest.runs[0].outcome, "injection-followed");
  assert.equal(session.latest.runs[1].outcome, "injection-contained");
  session = predictAndRun(session, "long");
  assert.equal(session.latest.runs[0].outcome, "overloaded");
  assert.equal(session.latest.runs[1].outcome, "scoped");
  assert.ok(ambiguousInstruction("temperature-daily", "long").length > 720);
});

test("删掉工程化字段会留下失败而不被伪装成通过", () => {
  let session = createInstructionSession();
  const incomplete = defaultEngineeredInstruction().replace("验收标准：", "");
  session = predictAndRun(session, "baseline", "temperature-daily", incomplete);
  const engineered = session.latest.runs.find((run) => run.id === "engineered");
  assert.equal(engineered.status, "failed");
  assert.equal(engineered.outcome, "incomplete");
  assert.match(engineered.findings[0], /验收标准/);
});

test("必须先预测，迁移挑战使用变化输入和约束", () => {
  let session = createInstructionSession();
  assert.throws(
    () => runInstructionComparison(session),
    (error) => error instanceof InstructionStateError && error.code === "prediction-required",
  );
  session = predictAndRun(session, "baseline", "temperature-daily");
  session = predictAndRun(session, "baseline", "pressure-night");
  assert.equal(session.latest.variantId, "pressure-night");
  assert.equal(session.latest.runs[1].status, "passed");
  assert.deepEqual(session.migrationVariants, ["pressure-night"]);
  assert.equal(session.latest.runs[1].outcome, "controlled");
});

test("完成四个场景和变化输入后，evidence 只保留匿名稳定状态", () => {
  let session = createInstructionSession();
  for (const scenarioId of ["baseline", "conflict", "injection", "long"]) {
    session = predictAndRun(session, scenarioId);
  }
  session = predictAndRun(session, "baseline", "pressure-night");
  const evidence = buildInstructionEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.lesson_id, "t03-agent-instruction");
  assert.equal(evidence.result, "passed");
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    [
      "prediction-recorded",
      "baseline-compared",
      "conflict-contained",
      "injection-contained",
      "long-instruction-diagnosed",
      "migration-completed",
    ],
  );
  assert.deepEqual(evidence.experiment.completed_scenarios, ["baseline", "conflict", "injection", "long"]);
  assert.deepEqual(evidence.experiment.migration_variants, ["pressure-night"]);
  const encoded = JSON.stringify(evidence);
  assert.doesNotMatch(encoded, /目标：|工具边界：|telemetry-report-v1.*帮我/i);
  assert.doesNotMatch(encoded, /C:\\\\Users|api_key|sk-secret/i);
});

test("浏览器 evidence 可以通过 Python checker 的公开 seam", () => {
  let session = createInstructionSession();
  for (const scenarioId of ["baseline", "conflict", "injection", "long"]) {
    session = predictAndRun(session, scenarioId);
  }
  session = predictAndRun(session, "baseline", "pressure-night");
  const evidence = buildInstructionEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });
  const temporaryRoot = mkdtempSync(join(tmpdir(), "agent-instruction-"));
  const evidencePath = join(temporaryRoot, "t03-agent-instruction-evidence.json");
  writeFileSync(evidencePath, `${JSON.stringify(evidence)}\n`, "utf8");
  try {
    const result = spawnSync(
      process.env.PYTHON ?? "python",
      [
        "-m",
        "course_check",
        "check",
        "t03-agent-instruction",
        "--root",
        workspaceRoot,
        "--evidence-file",
        evidencePath,
        "--json",
      ],
      {
        cwd: checkerRoot,
        encoding: "utf8",
        env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: checkerRoot },
      },
    );
    assert.equal(result.error, undefined, result.error?.message);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).result, "passed");
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});
