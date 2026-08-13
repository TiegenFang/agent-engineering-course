/**
 * Deterministic browser fixture for the T27 OpenAI Responses API adapter.
 *
 * It represents only adapter-level status categories.  It never imports an
 * SDK, reads browser storage, reaches the network, or contains prompts, tool
 * arguments, raw tool values, API keys, or model text.
 */

export const OPENAI_RESPONSES_LESSON_ID = "t27-openai-responses";
export const OPENAI_RESPONSES_VERSION = "1";
export const OPENAI_RESPONSES_MODEL = "gpt-5.6";
export const OPENAI_RESPONSES_CASE_ORDER = Object.freeze([
  "offline-success",
  "invalid-arguments",
  "malformed-structured-output",
  "transport-error",
]);
export const OPENAI_RESPONSES_CHECK_IDS = Object.freeze([
  "adapter-request-shaped",
  "offline-no-credential",
  "function-call-round-trip",
  "structured-output-validated",
  "budget-owned-by-loop",
  "errors-contained",
  "live-smoke-metadata-recorded",
  "live-api-not-claimed",
]);

const CASES = Object.freeze({
  "offline-success": Object.freeze({
    label: "成功：function call 回填后得到结构化结果",
    outcome: "completed",
    request_count: 2,
    function_call: true,
    tool_output_refilled: true,
    structured_output: "accepted",
    error: "none",
    observation: "第二个录制响应仅在合成 tool output 回填后出现；没有真实请求。",
  }),
  "invalid-arguments": Object.freeze({
    label: "故障：工具参数在 T26 边界被拒绝",
    outcome: "invalid-arguments-contained",
    request_count: 2,
    function_call: true,
    tool_output_refilled: true,
    structured_output: "accepted",
    error: "invalid-arguments",
    observation: "适配器只传递已解析对象；T26 保留参数验证与安全停止权。",
  }),
  "malformed-structured-output": Object.freeze({
    label: "故障：最终文本不符合 JSON Schema",
    outcome: "structured-output-rejected",
    request_count: 2,
    function_call: true,
    tool_output_refilled: true,
    structured_output: "rejected",
    error: "protocol",
    observation: "不传播原始文本；适配器给 T26 一个无效标记，由既有输出校验器停止。",
  }),
  "transport-error": Object.freeze({
    label: "故障：SDK 风格连接错误被分类",
    outcome: "transport-error-contained",
    request_count: 1,
    function_call: false,
    tool_output_refilled: false,
    structured_output: "not-requested",
    error: "connection",
    observation: "夹具只模拟异常类型名称；没有 DNS、HTTP、凭据或重试请求。",
  }),
});

export class OpenAIResponsesFixtureError extends Error {
  constructor(message, code = "invalid-fixture") {
    super(message);
    this.name = "OpenAIResponsesFixtureError";
    this.code = code;
  }
}

function requireCase(caseId) {
  if (typeof caseId !== "string" || !(caseId in CASES)) {
    throw new OpenAIResponsesFixtureError("未知的 Responses API 离线夹具。", "unknown-case");
  }
  return caseId;
}

function copyCase(caseId) {
  const profile = CASES[requireCase(caseId)];
  return {
    id: caseId,
    outcome: profile.outcome,
    request_count: profile.request_count,
    function_call: profile.function_call,
    tool_output_refilled: profile.tool_output_refilled,
    structured_output: profile.structured_output,
    error: profile.error,
    network: "not-called",
    access: "not-required",
  };
}
export function runOpenAIResponsesFixture(caseId) {
  return Object.freeze({
    ...copyCase(caseId),
    label: CASES[caseId].label,
    observation: CASES[caseId].observation,
    request: Object.freeze({
      model: OPENAI_RESPONSES_MODEL,
      function_tool: "read_telemetry",
      structured_output: "json_schema",
      strict: true,
      max_output_tokens: 256,
      store: false,
    }),
  });
}

export function createOpenAIResponsesSession(initialCase = "offline-success") {
  return {
    current: runOpenAIResponsesFixture(initialCase),
    runs: [],
  };
}

export function selectOpenAIResponsesCase(session, caseId) {
  if (!session || typeof session !== "object" || !Array.isArray(session.runs)) {
    throw new OpenAIResponsesFixtureError("离线实验会话无效。", "invalid-session");
  }
  return { ...session, current: runOpenAIResponsesFixture(caseId) };
}

export function recordOpenAIResponsesCase(session) {
  if (!session?.current || !Array.isArray(session.runs)) {
    throw new OpenAIResponsesFixtureError("请先选择一个离线夹具。", "no-current-case");
  }
  if (session.runs.some((run) => run.id === session.current.id)) {
    throw new OpenAIResponsesFixtureError("该离线夹具已经记录。", "duplicate-case");
  }
  const { label, observation, request, ...publicRun } = session.current;
  return { ...session, runs: [...session.runs, publicRun] };
}

function expectedCases(runs) {
  if (!Array.isArray(runs) || runs.length !== OPENAI_RESPONSES_CASE_ORDER.length) {
    return false;
  }
  return runs.every((run, index) => {
    const expected = copyCase(OPENAI_RESPONSES_CASE_ORDER[index]);
    return JSON.stringify(run) === JSON.stringify(expected);
  });
}

export function deriveOpenAIResponsesChecks(runs) {
  const byId = new Map((runs ?? []).map((run) => [run.id, run]));
  const success = byId.get("offline-success") ?? {};
  const invalid = byId.get("invalid-arguments") ?? {};
  const malformed = byId.get("malformed-structured-output") ?? {};
  const transport = byId.get("transport-error") ?? {};
  const offline = OPENAI_RESPONSES_CASE_ORDER.every((caseId) => {
    const run = byId.get(caseId);
    return run?.network === "not-called" && run?.access === "not-required";
  });
  return [
    { id: "adapter-request-shaped", result: "passed" },
    { id: "offline-no-credential", result: offline ? "passed" : "failed" },
    {
      id: "function-call-round-trip",
      result: success.function_call === true && success.tool_output_refilled === true && success.request_count === 2
        ? "passed"
        : "failed",
    },
    {
      id: "structured-output-validated",
      result: success.structured_output === "accepted" && malformed.structured_output === "rejected"
        ? "passed"
        : "failed",
    },
    { id: "budget-owned-by-loop", result: "passed" },
    {
      id: "errors-contained",
      result: invalid.outcome === "invalid-arguments-contained" && transport.outcome === "transport-error-contained"
        ? "passed"
        : "failed",
    },
    { id: "live-smoke-metadata-recorded", result: "passed" },
    { id: "live-api-not-claimed", result: "passed" },
  ];
}

export function buildOpenAIResponsesEvidence(session, {
  courseVersion,
  checkedOn = "2026-08-13",
} = {}) {
  if (!expectedCases(session?.runs)) {
    throw new OpenAIResponsesFixtureError("请按固定顺序记录四条离线路径后再导出。", "incomplete-runs");
  }
  if (typeof courseVersion !== "string" || !courseVersion) {
    throw new OpenAIResponsesFixtureError("课程版本缺失。", "missing-course-version");
  }
  const checks = deriveOpenAIResponsesChecks(session.runs);
  const result = checks.every((check) => check.result === "passed") ? "passed" : "partial";
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: courseVersion,
    lesson_id: OPENAI_RESPONSES_LESSON_ID,
    result,
    anonymous: true,
    checked_on: checkedOn,
    summary: result === "passed" ? "所有必需证据均已通过。" : "部分证据已通过，仍有证据需要补齐。",
    evidence: checks,
    experiment: {
      version: OPENAI_RESPONSES_VERSION,
      mode: "offline-fixture",
      adapter: "responses-api-sdk-boundary",
      model: OPENAI_RESPONSES_MODEL,
      network: "not-called",
      access: "not-required",
      request_budget: 256,
      loop_budget_owner: "t26-run-agent-loop",
      cases: session.runs,
      live_smoke: {
        status: "not-run",
        sdk: "openai Python SDK not invoked",
        model: OPENAI_RESPONSES_MODEL,
        verified_on: checkedOn,
        cost: "not assessed; no live request was made",
        limitations: ["no-api-key-read", "no-network-request", "not-a-live-api-result"],
      },
    },
  };
}
