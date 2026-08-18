import assert from "node:assert/strict";
import test from "node:test";

import {
  MCP_FORMAL_CHECK_IDS,
  OFFLINE_MCP_CAPABILITIES,
  offlineEvidenceDocument,
  runOfflineMcpDiscovery,
} from "../src/lib/mcp-discovery.mjs";

test("offline MCP fixture is deterministic and explicitly non-formal", () => {
  const first = runOfflineMcpDiscovery();
  const second = runOfflineMcpDiscovery();

  assert.deepEqual(first, second);
  assert.equal(first.lesson_id, "t19-mcp-discovery");
  assert.equal(first.mode, "offline-fallback");
  assert.equal(first.transport, "deterministic-in-memory");
  assert.equal(first.protocol_version, "conceptual-only");
  assert.deepEqual(first.capabilities, {
    tools: ["summarize_telemetry"],
    resources: ["telemetry://demo/snapshot"],
    prompts: ["review-telemetry"],
  });
  assert.equal(first.inspector.verified, false);
});

test("offline evidence keeps formal checks failed and is browser-importable", () => {
  const evidence = offlineEvidenceDocument("3.0.0", "2026-08-13");

  assert.equal(evidence.contract, "agent-engineering-course/evidence");
  assert.equal(evidence.result, "partial");
  assert.equal(evidence.anonymous, true);
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    ["offline-deterministic", ...MCP_FORMAL_CHECK_IDS],
  );
  assert.equal(evidence.evidence.slice(1).every((check) => check.result === "failed"), true);
  assert.deepEqual(evidence.capabilities, OFFLINE_MCP_CAPABILITIES);
});
