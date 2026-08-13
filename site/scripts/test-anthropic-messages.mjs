import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  ANTHROPIC_MESSAGES_CASE_ORDER,
  ANTHROPIC_MESSAGES_CHECK_IDS,
  AnthropicMessagesFixtureError,
  buildAnthropicMessagesEvidence,
  createAnthropicMessagesSession,
  recordAnthropicMessagesCase,
  runAnthropicMessagesFixture,
  selectAnthropicMessagesCase,
} from "../src/lib/anthropic-messages.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const siteRoot = resolve(scriptDirectory, "..");
const workspaceRoot = resolve(siteRoot, "..");

test("offline fixture records the five ordered cases and exports anonymous evidence", () => {
  let session = createAnthropicMessagesSession();
  for (const caseId of ANTHROPIC_MESSAGES_CASE_ORDER) {
    session = selectAnthropicMessagesCase(session, caseId);
    const result = runAnthropicMessagesFixture(caseId);
    assert.equal(result.network, "not-called");
    assert.equal(result.access, "not-required");
    session = recordAnthropicMessagesCase(session, caseId);
  }

  const evidence = buildAnthropicMessagesEvidence(session, {
    courseVersion: "test-course-version",
    recordedAt: "2026-08-13T00:00:00Z",
  });
  assert.equal(evidence.lesson_id, "t28-anthropic-messages");
  assert.equal(evidence.course_version, "test-course-version");
  assert.equal(evidence.experiment.request.tool_schema, "input_schema");
  assert.equal(evidence.experiment.request.tool_result_reference, "tool_use_id");
  assert.equal(evidence.experiment.request.structured_output, "json_schema");
  assert.equal(evidence.experiment.loop_budget_owner, "t26-agent-loop");
  assert.equal(evidence.experiment.state_owner, "application-message-history");
  assert.equal(evidence.experiment.live_smoke.status, "not-run");
  assert.equal(evidence.experiment.agent_sdk.status, "comparison-only-not-invoked");
  assert.deepEqual(evidence.experiment.cases.map((item) => item.id), ANTHROPIC_MESSAGES_CASE_ORDER);
  assert.deepEqual(evidence.checks.map((item) => item.id), ANTHROPIC_MESSAGES_CHECK_IDS);
  assert.ok(evidence.checks.every((item) => item.result === "passed"));
  assert.equal(JSON.stringify(evidence).toLowerCase().includes("api_key"), false);
});

test("fixture prevents an out-of-order evidence claim", () => {
  const session = createAnthropicMessagesSession();
  assert.throws(
    () => recordAnthropicMessagesCase(session, "transport-error"),
    AnthropicMessagesFixtureError,
  );
  assert.throws(
    () => buildAnthropicMessagesEvidence(session),
    AnthropicMessagesFixtureError,
  );
  assert.throws(
    () => runAnthropicMessagesFixture("live-api"),
    AnthropicMessagesFixtureError,
  );
});

test("page, source note, and no-network implementation boundary are present", async () => {
  const [page, lab, adapter, sources] = await Promise.all([
    readFile(resolve(siteRoot, "src/content/docs/module-11-anthropic-messages.mdx"), "utf8"),
    readFile(resolve(siteRoot, "src/components/AnthropicMessagesLab.astro"), "utf8"),
    readFile(resolve(workspaceRoot, "labs/anthropic-messages/anthropic_messages_adapter.py"), "utf8"),
    readFile(resolve(workspaceRoot, "docs/research/t28-anthropic-api-sources.md"), "utf8"),
  ]);
  for (const requiredHeading of ["真实问题", "操作前预测", "故障注入与恢复", "迁移挑战", "Claude Agent SDK"]) {
    assert.match(page, new RegExp(requiredHeading));
  }
  assert.match(page, /EvidenceLoop lessonId="t28-anthropic-messages"/);
  assert.match(lab, /data-anthropic-messages/);
  assert.match(lab, /data-export-anthropic-messages/);
  assert.match(adapter, /class MessagesResponseSource/);
  assert.match(adapter, /output_config/);
  assert.doesNotMatch(adapter, /os\.environ|os\.getenv|requests\.|httpx\.|urllib/);
  assert.match(sources, /platform\.claude\.com/);
  assert.match(sources, /tool_result/);
});
