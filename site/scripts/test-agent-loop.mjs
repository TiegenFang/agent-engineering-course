import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  AgentLoopStateError,
  advanceAgentLoop,
  buildAgentLoopEvidence,
  buildAgentLoopTrace,
  createAgentLoopSession,
  describeAgentLoopObservation,
  submitPrediction,
} from "../src/lib/agent-loop.mjs";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = resolve(siteRoot, "..");
const checkerRoot = join(workspaceRoot, "checker");
const COURSE_VERSION = JSON.parse(
  readFileSync(join(workspaceRoot, "course-version.json"), "utf8"),
).course_version;

test("模块 1 页面公开 Agent loop 实验并连接匿名证据入口", () => {
  const page = readFileSync(
    new URL("../src/content/docs/module-1-agent-loop.mdx", import.meta.url),
    "utf8",
  );
  const component = readFileSync(
    new URL("../src/components/AgentLoop.astro", import.meta.url),
    "utf8",
  );
  const evidenceComponent = readFileSync(
    new URL("../src/components/EvidenceLoop.astro", import.meta.url),
    "utf8",
  );

  assert.match(page, /<AgentLoop\s*\/>/);
  assert.match(page, /<EvidenceLoop\s+lessonId="t02-agent-loop"\s*\/>/);
  assert.match(component, /<noscript>/);
  assert.match(component, /交互控件需要 JavaScript/);
  assert.match(component, /prediction-1/);
  assert.match(component, /工具错误路径（error）/);
  assert.match(component, /max_steps/);
  assert.match(component, /预测错误.*partial/);
  assert.match(evidenceComponent, /<noscript>/);
  assert.match(evidenceComponent, /本地记录交互需要 JavaScript/);
});

const DEFAULT_INPUT = {
  goal: "检查设备遥测并在异常时停止",
  deviceId: "device-17",
  threshold: 42,
  failureMode: "none",
  maxSteps: 6,
};

function finishSession(session) {
  let current = session;
  while (current.status !== "complete") {
    const expected = current.trace.steps[current.cursor].kind;
    current = advanceAgentLoop(submitPrediction(current, expected));
  }
  return current;
}

test("确定性 trace 显示完整的响应、工具和停止控制流", () => {
  const trace = buildAgentLoopTrace(DEFAULT_INPUT);

  assert.deepEqual(
    trace.steps.map((step) => step.kind),
    ["response", "tool-request", "tool-execution", "tool-result", "response", "stop"],
  );
  assert.equal(trace.steps[0].actor, "model");
  assert.equal(trace.steps[1].actor, "harness");
  assert.equal(trace.steps[2].actor, "tool");
  assert.equal(trace.steps[3].actor, "harness");
  assert.equal(trace.steps.at(-1).status, "passed");
  assert.match(trace.steps[3].detail, /结果回填/);
});

test("变化输入会改变模拟观察结果而不是复用固定答案", () => {
  const first = buildAgentLoopTrace(DEFAULT_INPUT);
  const second = buildAgentLoopTrace({ ...DEFAULT_INPUT, deviceId: "device-18", threshold: 30 });

  assert.notDeepEqual(first.observation, second.observation);
  assert.match(second.steps[0].detail, /device-18/);
});

test("学员必须先预测，才能逐步推进公共 session seam", () => {
  let session = createAgentLoopSession(DEFAULT_INPUT);

  assert.equal(session.status, "predicting");
  assert.equal(session.history.length, 0);
  assert.throws(
    () => advanceAgentLoop(session),
    (error) => error instanceof AgentLoopStateError && error.code === "prediction-required",
  );

  session = submitPrediction(session, "tool-request");
  assert.equal(session.pendingPrediction.correct, false);
  session = advanceAgentLoop(session);
  assert.equal(session.history[0].kind, "response");
  assert.equal(session.status, "predicting");
});

test("工具错误分支会回填错误并按停止条件停下", () => {
  const trace = buildAgentLoopTrace({ ...DEFAULT_INPUT, failureMode: "tool-error" });
  const execution = trace.steps.find((step) => step.kind === "tool-execution");
  const result = trace.steps.find((step) => step.kind === "tool-result");

  assert.equal(execution.status, "error");
  assert.equal(result.status, "error");
  assert.match(result.detail, /错误回填/);
  assert.equal(trace.steps.at(-1).kind, "stop");
  assert.equal(trace.steps.at(-1).status, "error");
});

test("工具错误结果不会被渲染成成功遥测读数", () => {
  const completed = finishSession(createAgentLoopSession({ ...DEFAULT_INPUT, failureMode: "tool-error" }));
  const observation = describeAgentLoopObservation(completed);

  assert.match(observation, /工具结果为错误/);
  assert.match(observation, /没有可用遥测读数/);
  assert.doesNotMatch(observation, /本次模拟观察：/);
});

test("max_steps 预算会以明确的 budget-stop 分支结束并导出替代证据", () => {
  const session = finishSession(createAgentLoopSession({ ...DEFAULT_INPUT, maxSteps: 2 }));
  const evidence = buildAgentLoopEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });

  assert.equal(evidence.result, "alternative");
  assert.equal(evidence.trace.outcome, "budget-stop");
  assert.equal(evidence.trace.max_steps, 2);
  assert.deepEqual(
    evidence.trace.steps.map((step) => step.id),
    ["prediction-1", "response-1", "tool-request-1", "budget-stop-1"],
  );
  assert.equal(evidence.trace.steps.at(-1).status, "budget");
  assert.equal(evidence.trace.steps.at(-1).result, "alternative");
  assert.match(describeAgentLoopObservation(session), /预算停止/);
  assert.equal(evidence.evidence.at(-1).result, "alternative");
});

test("错误预测完成全 trace 后保持 partial，并要求重新预测才能 passed", () => {
  let session = createAgentLoopSession(DEFAULT_INPUT);
  session = advanceAgentLoop(submitPrediction(session, "tool-request"));
  session = finishSession(session);
  const evidence = buildAgentLoopEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });

  assert.equal(evidence.result, "partial");
  assert.equal(evidence.evidence[0].result, "failed");
  assert.equal(evidence.trace.steps[0].result, "failed");
  assert.equal(evidence.evidence[1].result, "passed");
  assert.equal(evidence.evidence[2].result, "passed");
});

test("完成 trace 后可以生成版本锁定且匿名的 evidence", () => {
  const session = finishSession(createAgentLoopSession(DEFAULT_INPUT));
  const evidence = buildAgentLoopEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });

  assert.equal(evidence.contract, "agent-engineering-course/evidence");
  assert.equal(evidence.lesson_id, "t02-agent-loop");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.trace.version, "1");
  assert.equal(evidence.anonymous, true);
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    ["prediction-recorded", "trace-observed", "stop-condition-observed"],
  );
  assert.deepEqual(
    evidence.trace.steps.map((step) => step.id),
    [
      "prediction-1",
      "response-1",
      "tool-request-1",
      "tool-execution-1",
      "tool-result-1",
      "response-2",
      "stop-1",
    ],
  );
  assert.doesNotMatch(JSON.stringify(evidence), /device-17|C:\\\\Users|api_key|sk-/i);
});

test("错误路径导出固定的 error trace，而不是伪造成功读数", () => {
  const session = finishSession(createAgentLoopSession({ ...DEFAULT_INPUT, failureMode: "tool-error" }));
  const evidence = buildAgentLoopEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });

  assert.equal(evidence.result, "passed");
  assert.equal(evidence.trace.version, "1");
  assert.equal(evidence.trace.outcome, "error");
  assert.deepEqual(
    evidence.trace.steps.map((step) => step.id),
    ["prediction-1", "response-1", "tool-request-1", "tool-execution-1", "tool-result-1", "stop-1"],
  );
  assert.equal(evidence.trace.steps.at(-1).status, "error");
});

test("浏览器导出的成功 trace 可以直接通过 Python checker", () => {
  const session = finishSession(createAgentLoopSession(DEFAULT_INPUT));
  const evidence = buildAgentLoopEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });
  const temporaryRoot = mkdtempSync(join(tmpdir(), "agent-loop-trace-"));
  const evidencePath = join(temporaryRoot, "t02-agent-loop-evidence.json");
  writeFileSync(evidencePath, `${JSON.stringify(evidence)}\n`, "utf8");
  try {
    const result = spawnSync(
      process.env.PYTHON ?? "python",
      [
        "-m",
        "course_check",
        "check",
        "t02-agent-loop",
        "--root",
        workspaceRoot,
        "--evidence-file",
        evidencePath,
        "--json",
      ],
      {
        cwd: checkerRoot,
        encoding: "utf8",
        env: {
          ...process.env,
          PYTHONIOENCODING: "utf-8",
          PYTHONPATH: checkerRoot,
        },
      },
    );
    assert.equal(result.error, undefined, result.error?.message);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).result, "passed");
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});
