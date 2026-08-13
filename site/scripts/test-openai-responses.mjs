import assert from "node:assert/strict";
import test from "node:test";

import {
  OPENAI_RESPONSES_CASE_ORDER,
  OPENAI_RESPONSES_CHECK_IDS,
  OpenAIResponsesFixtureError,
  buildOpenAIResponsesEvidence,
  createOpenAIResponsesSession,
  recordOpenAIResponsesCase,
  runOpenAIResponsesFixture,
  selectOpenAIResponsesCase,
} from "../src/lib/openai-responses.mjs";

test("Responses API browser fixtures are deterministic and offline", () => {
  const first = runOpenAIResponsesFixture("offline-success");
  const second = runOpenAIResponsesFixture("offline-success");

  assert.deepEqual(first, second);
  assert.equal(first.network, "not-called");
  assert.equal(first.access, "not-required");
  assert.equal(first.request.function_tool, "read_telemetry");
  assert.equal(first.request.structured_output, "json_schema");
  assert.equal(first.request.strict, true);
  assert.equal(first.request.store, false);
  assert.equal(JSON.stringify(first).includes("sk-"), false);
});
test("all four recorded fixture paths derive anonymous completed evidence", () => {
  let session = createOpenAIResponsesSession();
  for (const caseId of OPENAI_RESPONSES_CASE_ORDER) {
    session = selectOpenAIResponsesCase(session, caseId);
    session = recordOpenAIResponsesCase(session);
  }
  const evidence = buildOpenAIResponsesEvidence(session, {
    courseVersion: "0.1.0-alpha",
    checkedOn: "2026-08-13",
  });

  assert.equal(evidence.lesson_id, "t27-openai-responses");
  assert.equal(evidence.result, "passed");
  assert.deepEqual(evidence.evidence.map((check) => check.id), OPENAI_RESPONSES_CHECK_IDS);
  assert.equal(evidence.experiment.network, "not-called");
  assert.equal(evidence.experiment.access, "not-required");
  assert.equal(evidence.experiment.live_smoke.status, "not-run");
  assert.equal(JSON.stringify(evidence).includes("api_key"), false);
  assert.equal(JSON.stringify(evidence).includes("tool arguments"), false);
});

test("a browser learner cannot export partial or reordered evidence", () => {
  let session = createOpenAIResponsesSession();
  session = recordOpenAIResponsesCase(session);
  assert.throws(
    () => buildOpenAIResponsesEvidence(session, { courseVersion: "0.1.0-alpha" }),
    (error) => error instanceof OpenAIResponsesFixtureError && error.code === "incomplete-runs",
  );
  assert.throws(
    () => runOpenAIResponsesFixture("live-api"),
    (error) => error instanceof OpenAIResponsesFixtureError && error.code === "unknown-case",
  );
});
