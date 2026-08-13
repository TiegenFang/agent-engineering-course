import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  CHECK_IDS,
  COMPRESSION_MODES,
  ContextRecoveryStateError,
  PREDICTION_OPTIONS,
  buildContextRecoveryEvidence,
  buildHandoffPackage,
  compareCompression,
  createContextRecoverySession,
  describeContextHistoryMemory,
  generateHandoffPackage,
  importHandoffPackage,
  recoverPollutedTask,
  runCompressionComparison,
  runPollutedTask,
  selectContextRecoveryInput,
  submitContextPrediction,
} from "../src/lib/context-recovery.mjs";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = resolve(siteRoot, "..");
const checkerRoot = join(workspaceRoot, "checker");
const courseVersion = JSON.parse(
  readFileSync(join(workspaceRoot, "course-version.json"), "utf8"),
).course_version;

function runMode(session, mode, prediction = PREDICTION_OPTIONS[1]) {
  let current = selectContextRecoveryInput(session, { compressionMode: mode });
  current = submitContextPrediction(current, prediction);
  return runCompressionComparison(current);
}

function completeSession() {
  let session = createContextRecoverySession();
  session = runMode(session, COMPRESSION_MODES.FAITHFUL, PREDICTION_OPTIONS[0]);
  session = runMode(session, COMPRESSION_MODES.DISTORTED);
  session = runMode(session, COMPRESSION_MODES.CONSTRAINT_OMITTED);
  session = runPollutedTask(session);
  session = recoverPollutedTask(session);
  return generateHandoffPackage(session);
}

test("三种确定性压缩模式都提供压缩前/压缩后结果", () => {
  for (const [mode, outcome] of [
    [COMPRESSION_MODES.FAITHFUL, "faithful"],
    [COMPRESSION_MODES.DISTORTED, "distorted"],
    [COMPRESSION_MODES.CONSTRAINT_OMITTED, "constraint-omitted"],
  ]) {
    const comparison = compareCompression(mode);
    assert.equal(comparison.before.outcome, "report-ready");
    assert.equal(comparison.after.outcome, outcome);
    assert.equal(comparison.diagnostics.before_after_observed, true);
  }
});

test("压缩失真和约束遗漏留下不同的可解释诊断", () => {
  const distorted = compareCompression(COMPRESSION_MODES.DISTORTED);
  assert.deepEqual(distorted.after.changed_constraint_ids, ["preserve-evidence"]);
  assert.equal(distorted.diagnostics.distortion_detected, true);
  assert.equal(distorted.diagnostics.constraint_omission_detected, false);

  const omitted = compareCompression(COMPRESSION_MODES.CONSTRAINT_OMITTED);
  assert.deepEqual(omitted.after.omitted_constraint_ids, ["no-network"]);
  assert.equal(omitted.diagnostics.distortion_detected, false);
  assert.equal(omitted.diagnostics.constraint_omission_detected, true);
});

test("session 必须先预测再运行，并保留每种模式的比较", () => {
  let session = createContextRecoverySession();
  assert.throws(
    () => runCompressionComparison(session),
    (error) => error instanceof ContextRecoveryStateError && error.code === "prediction-required",
  );
  session = runMode(session, COMPRESSION_MODES.FAITHFUL, PREDICTION_OPTIONS[0]);
  session = runMode(session, COMPRESSION_MODES.DISTORTED);
  assert.deepEqual(
    session.comparisons.map((comparison) => comparison.mode),
    ["faithful", "distorted"],
  );
  assert.equal(session.predictions[0].correct, true);
  assert.equal(session.predictions[1].correct, true);
});

test("污染任务通过固定四步恢复，不能直接伪造恢复状态", () => {
  let session = createContextRecoverySession();
  session = runMode(session, COMPRESSION_MODES.FAITHFUL, PREDICTION_OPTIONS[0]);
  session = runPollutedTask(session);
  assert.equal(session.pollution.outcome, "polluted");
  assert.deepEqual(session.pollution.recovery_steps, undefined);
  session = recoverPollutedTask(session);
  assert.equal(session.pollution.outcome, "recovered");
  assert.deepEqual(session.pollution.recovery_steps, ["detect", "quarantine", "restore", "revalidate"]);
  assert.throws(
    () => recoverPollutedTask(createContextRecoverySession()),
    (error) => error instanceof ContextRecoveryStateError && error.code === "pollution-required",
  );
});

test("交接包包含目标、状态、证据、风险和下一步，并可在新会话导入", () => {
  const session = completeSession();
  const handoff = buildHandoffPackage(session);
  assert.equal(handoff.status, "ready-for-next-session");
  for (const field of ["goal", "status", "evidence", "risks", "next_steps"]) {
    assert.ok(handoff[field], `handoff.${field} missing`);
  }
  const imported = importHandoffPackage(handoff);
  assert.equal(imported.goal, "report-task");
  assert.deepEqual(imported.layers, ["context", "history", "memory"]);
  assert.throws(
    () => importHandoffPackage({ ...handoff, next_steps: [] }),
    /交接包必须包含目标、状态、证据、风险和下一步/,
  );
});

test("上下文、历史、Memory 由固定生命周期和权限边界区分", () => {
  const description = describeContextHistoryMemory();
  assert.equal(description.invariants.context_is_current_working_set, true);
  assert.equal(description.invariants.history_is_record_not_instruction, true);
  assert.equal(description.invariants.memory_requires_owner_and_lifetime, true);
  assert.deepEqual(description.layers.map((layer) => layer.id), ["context", "history", "memory"]);
});

test("完整 session 生成匿名 evidence，公开对象不含 fixture 文本或路径", () => {
  const evidence = buildContextRecoveryEvidence(completeSession(), {
    courseVersion,
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.lesson_id, "t15-context-recovery");
  assert.equal(evidence.result, "passed");
  assert.deepEqual(evidence.evidence.map((check) => check.id), CHECK_IDS);
  assert.deepEqual(evidence.experiment.compression_modes, ["faithful", "distorted", "constraint-omitted"]);
  assert.equal(evidence.experiment.pollution.recovered, true);
  assert.equal(evidence.experiment.handoff.status, "ready-for-next-session");
  const encoded = JSON.stringify(evidence);
  assert.doesNotMatch(encoded, /外发|删除本地|C:\\\\Users|api_key|sk-secret/i);
});

test("未显式生成交接包时保持 partial，而不是把候选包当完成证据", () => {
  let session = createContextRecoverySession();
  session = runMode(session, COMPRESSION_MODES.FAITHFUL, PREDICTION_OPTIONS[0]);
  session = runMode(session, COMPRESSION_MODES.DISTORTED);
  session = runMode(session, COMPRESSION_MODES.CONSTRAINT_OMITTED);
  session = recoverPollutedTask(runPollutedTask(session));
  const evidence = buildContextRecoveryEvidence(session, {
    courseVersion,
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.result, "partial");
  assert.equal(evidence.evidence.find((check) => check.id === "handoff-complete")?.result, "failed");
  assert.equal(evidence.experiment.handoff.status, "blocked");
});

test("页面与实验合同公开 no-JS、三种模式和交接字段", () => {
  const page = readFileSync(
    new URL("../src/content/docs/module-5-context-recovery.mdx", import.meta.url),
    "utf8",
  );
  const component = readFileSync(
    new URL("../src/components/ContextRecoveryLab.astro", import.meta.url),
    "utf8",
  );
  const contract = readFileSync(join(workspaceRoot, "labs/context-recovery/README.md"), "utf8");
  assert.match(page, /<ContextRecoveryLab\s*\/>/);
  assert.match(page, /上下文.*历史.*Memory/s);
  assert.match(component, /<noscript>/);
  assert.match(component, /data-context-run-polluted/);
  assert.match(component, /data-context-generate-handoff/);
  assert.match(component, /goal.*status.*evidence.*risks.*next_steps/s);
  assert.match(contract, /constraint-omission-detected/);
});

test("浏览器 evidence 可以通过 Python checker 的公开 seam", () => {
  const evidence = buildContextRecoveryEvidence(completeSession(), {
    courseVersion,
    checkedOn: "2026-08-13",
  });
  const temporaryRoot = mkdtempSync(join(tmpdir(), "context-recovery-"));
  const evidencePath = join(temporaryRoot, "t15-context-recovery-evidence.json");
  writeFileSync(evidencePath, `${JSON.stringify(evidence)}\n`, "utf8");
  try {
    const result = spawnSync(
      process.env.PYTHON ?? "python",
      [
        "-m",
        "course_check",
        "check",
        "t15-context-recovery",
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
