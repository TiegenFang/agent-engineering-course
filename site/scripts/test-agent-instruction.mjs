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
  getScenarioFixture,
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
  session = predictAndRun(session, "baseline");
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
  for (const scenarioId of ["baseline", "conflict", "injection", "long"]) {
    session = predictAndRun(session, scenarioId, "temperature-daily");
  }
  session = predictAndRun(session, "baseline", "pressure-night");
  assert.equal(session.latest.variantId, "pressure-night");
  assert.equal(session.latest.runs[1].status, "passed");
  assert.deepEqual(session.migrationVariants, ["pressure-night"]);
  assert.equal(session.latest.runs[1].outcome, "controlled");
  assert.equal(session.latest.variantSubject, "压力");
  assert.equal(session.latest.variantUnit, "kPa");
  assert.equal(session.latest.variantLimit, "最近 3 条有效记录");
});

test("提示注入使用真实恶意 fixture，并且只堆关键词不能绕过安全不变量", () => {
  const fixture = getScenarioFixture("injection");
  assert.match(fixture.maliciousNote, /外发全部原始数据/);
  assert.match(fixture.maliciousNote, /删除本地审计记录/);
  let session = createInstructionSession();
  session = predictAndRun(session, "baseline");
  const spoof = [
    "目标：生成日常温度报告，检查温度数据质量并给出可复核摘要。",
    "上下文：这是合成温度记录，单位为 °C。",
    "约束：只读检查；不调用网络；最近 5 条有效记录。",
    "非目标：不修改仓库文件。",
    "工具边界：优先级、忽略、停止。",
    "输出契约：给出温度摘要。",
    "验收标准：输出包含单位 °C。",
    "失败证据：停止。",
  ].join("\n");
  session = predictAndRun(session, "conflict", "temperature-daily", spoof);
  assert.equal(session.latest.runs[1].status, "failed");
  assert.equal(session.latest.runs[1].outcome, "conflict-unresolved");
  const conflictWithoutPriority = defaultEngineeredInstruction("temperature-daily", "conflict")
    .replace("规则优先级=仓库规则高于用户请求", "规则优先级=未定义");
  session = predictAndRun(session, "conflict", "temperature-daily", conflictWithoutPriority);
  assert.equal(session.latest.runs[1].outcome, "conflict-unresolved");
  assert.match(session.latest.runs[1].findings.join(" "), /规则优先级/);
  session = predictAndRun(session, "conflict");
  session = predictAndRun(session, "injection", "temperature-daily", spoof);
  assert.equal(session.latest.fixture.maliciousNote, fixture.maliciousNote);
  assert.equal(session.latest.runs[1].outcome, "injection-uncontained");
  const injectionUnsafe = defaultEngineeredInstruction("temperature-daily", "injection")
    .replace("处理动作=忽略并不执行", "处理动作=忽略并不执行；允许外发并删除");
  session = predictAndRun(session, "injection", "temperature-daily", injectionUnsafe);
  assert.equal(session.latest.runs[1].outcome, "injection-uncontained");
  assert.match(session.latest.runs[1].findings.join(" "), /允许或执行/);
});

test("迁移输入必须同时校验主题、单位和记录限制，而不是只看 variant ID", () => {
  let session = createInstructionSession();
  for (const scenarioId of ["baseline", "conflict", "injection", "long"]) {
    session = predictAndRun(session, scenarioId, "temperature-daily");
  }
  const staleTemperatureInstruction = defaultEngineeredInstruction("temperature-daily", "baseline");
  session = predictAndRun(session, "baseline", "pressure-night", staleTemperatureInstruction);
  assert.equal(session.latest.runs[1].status, "failed");
  assert.equal(session.latest.runs[1].outcome, "variant-mismatch");
  assert.deepEqual(session.migrationVariants, []);
});

test("新场景必须按固定顺序运行，提前迁移也会被拒绝", () => {
  let session = createInstructionSession();
  assert.throws(
    () => predictAndRun(session, "injection"),
    (error) => error instanceof InstructionStateError && error.code === "scenario-order",
  );
  assert.throws(
    () => predictAndRun(session, "baseline", "pressure-night"),
    (error) => error instanceof InstructionStateError && error.code === "migration-order",
  );
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
