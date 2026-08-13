import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  AgentLoopStateError,
  advanceAgentLoop,
  buildAgentLoopEvidence,
  buildAgentLoopTrace,
  createAgentLoopSession,
  submitPrediction,
} from "../src/lib/agent-loop.mjs";

const COURSE_VERSION = "0.1.0-foundation";

test("模块 1 页面公开 Agent loop 实验并连接匿名证据入口", () => {
  const page = readFileSync(
    new URL("../src/content/docs/module-1-agent-loop.mdx", import.meta.url),
    "utf8",
  );

  assert.match(page, /<AgentLoop\s*\/>/);
  assert.match(page, /<EvidenceLoop\s+lessonId="t02-agent-loop"\s*\/>/);
});

const DEFAULT_INPUT = {
  goal: "检查设备遥测并在异常时停止",
  deviceId: "device-17",
  threshold: 42,
  failureMode: "none",
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

test("完成 trace 后可以生成版本锁定且匿名的 evidence", () => {
  const session = finishSession(createAgentLoopSession(DEFAULT_INPUT));
  const evidence = buildAgentLoopEvidence(session, {
    courseVersion: COURSE_VERSION,
    checkedOn: "2026-08-13",
  });

  assert.equal(evidence.contract, "agent-engineering-course/evidence");
  assert.equal(evidence.lesson_id, "t02-agent-loop");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.anonymous, true);
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    ["prediction-recorded", "trace-observed", "stop-condition-observed"],
  );
  assert.doesNotMatch(JSON.stringify(evidence), /device-17|C:\\\\Users|api_key|sk-/i);
});
