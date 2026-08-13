/**
 * Browser-only fixture for T28.  This module deliberately contains no SDK
 * import, credential lookup, fetch, or network transport.
 */

export const ANTHROPIC_MESSAGES_CASE_ORDER = Object.freeze([
  "offline-success",
  "invalid-arguments",
  "malformed-structured-output",
  "transport-error",
  "authentication-error",
]);

export const ANTHROPIC_MESSAGES_CHECK_IDS = Object.freeze([
  "messages-request-shaped",
  "offline-no-credential",
  "tool-use-round-trip",
  "message-history-owned-by-app",
  "structured-output-validated",
  "budget-owned-by-loop",
  "errors-contained",
  "agent-sdk-boundary-recorded",
  "live-smoke-metadata-recorded",
  "live-api-not-claimed",
]);

const MODEL = "claude-sonnet-4-5";
const CASES = Object.freeze({
  "offline-success": Object.freeze({
    id: "offline-success",
    outcome: "completed",
    request_count: 2,
    tool_use: true,
    tool_result_refilled: true,
    history_replayed: true,
    structured_output: "accepted",
    error: "none",
  }),
  "invalid-arguments": Object.freeze({
    id: "invalid-arguments",
    outcome: "invalid-arguments-contained",
    request_count: 2,
    tool_use: true,
    tool_result_refilled: true,
    history_replayed: true,
    structured_output: "accepted",
    error: "invalid-arguments",
  }),
  "malformed-structured-output": Object.freeze({
    id: "malformed-structured-output",
    outcome: "structured-output-rejected",
    request_count: 2,
    tool_use: true,
    tool_result_refilled: true,
    history_replayed: true,
    structured_output: "rejected",
    error: "protocol",
  }),
  "transport-error": Object.freeze({
    id: "transport-error",
    outcome: "transport-error-contained",
    request_count: 1,
    tool_use: false,
    tool_result_refilled: false,
    history_replayed: false,
    structured_output: "not-requested",
    error: "connection",
  }),
  "authentication-error": Object.freeze({
    id: "authentication-error",
    outcome: "authentication-error-contained",
    request_count: 1,
    tool_use: false,
    tool_result_refilled: false,
    history_replayed: false,
    structured_output: "not-requested",
    error: "authentication",
  }),
});

const REQUEST_SHAPE = Object.freeze({
  model: MODEL,
  tool_name: "read_telemetry",
  tool_schema: "input_schema",
  tool_result_reference: "tool_use_id",
  structured_output: "json_schema",
  max_tokens: 256,
  state_owner: "application-message-history",
  network: "not-called",
  access: "not-required",
});

export class AnthropicMessagesFixtureError extends Error {
  constructor(message) {
    super(message);
    this.name = "AnthropicMessagesFixtureError";
  }
}

function requireKnownCase(caseId) {
  if (!Object.hasOwn(CASES, caseId)) {
    throw new AnthropicMessagesFixtureError(`Unknown offline fixture case: ${String(caseId)}`);
  }
  return CASES[caseId];
}

function frozenSession(selectedCaseId, recordedCaseIds) {
  return Object.freeze({
    selectedCaseId,
    recordedCaseIds: Object.freeze([...recordedCaseIds]),
  });
}

function publicCase(caseId) {
  const fixture = requireKnownCase(caseId);
  return Object.freeze({
    ...fixture,
    network: "not-called",
    access: "not-required",
  });
}

export function createAnthropicMessagesSession() {
  return frozenSession(ANTHROPIC_MESSAGES_CASE_ORDER[0], []);
}

export function selectAnthropicMessagesCase(session, caseId) {
  if (!session || !Array.isArray(session.recordedCaseIds)) {
    throw new AnthropicMessagesFixtureError("A fixture session is required.");
  }
  requireKnownCase(caseId);
  return frozenSession(caseId, session.recordedCaseIds);
}

export function runAnthropicMessagesFixture(caseId) {
  const fixture = publicCase(caseId);
  return Object.freeze({
    ...fixture,
    request: REQUEST_SHAPE,
    tool_protocol: fixture.tool_use
      ? Object.freeze({
        assistant_content_type: "tool_use",
        tool_use_id: "toolu_offline_1",
        user_content_type: "tool_result",
        refill_role: "user",
      })
      : Object.freeze({
        assistant_content_type: "not-received",
        tool_use_id: "not-applicable",
        user_content_type: "not-sent",
        refill_role: "not-applicable",
      }),
  });
}

export function recordAnthropicMessagesCase(session, caseId = session?.selectedCaseId) {
  if (!session || !Array.isArray(session.recordedCaseIds)) {
    throw new AnthropicMessagesFixtureError("A fixture session is required.");
  }
  requireKnownCase(caseId);
  const expected = ANTHROPIC_MESSAGES_CASE_ORDER[session.recordedCaseIds.length];
  if (!expected) {
    throw new AnthropicMessagesFixtureError("All fixture cases have already been recorded.");
  }
  if (caseId !== expected) {
    throw new AnthropicMessagesFixtureError(`Record cases in order; next required case is ${expected}.`);
  }
  return frozenSession(caseId, [...session.recordedCaseIds, caseId]);
}

function derivedChecks(recordedCaseIds) {
  const cases = Object.fromEntries(recordedCaseIds.map((caseId) => [caseId, publicCase(caseId)]));
  const completed = recordedCaseIds.length === ANTHROPIC_MESSAGES_CASE_ORDER.length;
  const passed = {
    "messages-request-shaped": completed && REQUEST_SHAPE.max_tokens === 256,
    "offline-no-credential": completed && REQUEST_SHAPE.network === "not-called" && REQUEST_SHAPE.access === "not-required",
    "tool-use-round-trip": completed && cases["offline-success"].tool_use && cases["offline-success"].tool_result_refilled,
    "message-history-owned-by-app": completed && cases["offline-success"].history_replayed,
    "structured-output-validated": completed && cases["offline-success"].structured_output === "accepted" && cases["malformed-structured-output"].structured_output === "rejected",
    "budget-owned-by-loop": completed,
    "errors-contained": completed && cases["invalid-arguments"].error === "invalid-arguments" && cases["transport-error"].error === "connection" && cases["authentication-error"].error === "authentication",
    "agent-sdk-boundary-recorded": completed,
    "live-smoke-metadata-recorded": completed,
    "live-api-not-claimed": completed,
  };
  return ANTHROPIC_MESSAGES_CHECK_IDS.map((id) => Object.freeze({ id, result: passed[id] ? "passed" : "failed" }));
}

export function buildAnthropicMessagesEvidence(session, {
  courseVersion = "development",
  recordedAt = new Date().toISOString(),
} = {}) {
  if (!session || !Array.isArray(session.recordedCaseIds)) {
    throw new AnthropicMessagesFixtureError("A fixture session is required.");
  }
  if (session.recordedCaseIds.length !== ANTHROPIC_MESSAGES_CASE_ORDER.length) {
    throw new AnthropicMessagesFixtureError("Record all five offline cases before exporting evidence.");
  }
  const cases = session.recordedCaseIds.map(publicCase);
  return Object.freeze({
    lesson_id: "t28-anthropic-messages",
    course_version: courseVersion,
    recorded_at: recordedAt,
    experiment: Object.freeze({
      version: "1",
      mode: "offline-fixture",
      adapter: "anthropic-messages-response-source",
      model: MODEL,
      network: "not-called",
      access: "not-required",
      request_max_tokens: 256,
      loop_budget_owner: "t26-agent-loop",
      state_owner: "application-message-history",
      request: REQUEST_SHAPE,
      agent_sdk: Object.freeze({
        surface: "Claude Agent SDK",
        status: "comparison-only-not-invoked",
        messages_api_state: "application-replays-message-history",
        t26_loop_state: "harness-owned",
        sdk_runtime: "verify-current-session-permission-and-tool-behavior-before-use",
        budget: "do-not-infer-a-shared-budget-from-this-fixture",
      }),
      cases: Object.freeze(cases),
      live_smoke: Object.freeze({
        status: "not-run",
        sdk: "anthropic-python-not-imported",
        model: MODEL,
        verified_on: "not-run",
        cost: "not-incurred",
        limitations: "offline fixture only; no credential and no network call",
      }),
    }),
    checks: Object.freeze(derivedChecks(session.recordedCaseIds)),
  });
}
