/**
 * Browser-only deterministic fallback for the MCP discovery lesson.
 *
 * This is intentionally not an MCP transport or an in-process protocol
 * implementation.  It mirrors the evidence vocabulary so a learner without
 * the local SDK can rehearse discovery and recovery while the page labels the
 * result as partial.
 */

export const OFFLINE_MCP_CAPABILITIES = Object.freeze({
  tools: Object.freeze(["summarize_telemetry"]),
  resources: Object.freeze(["telemetry://demo/snapshot"]),
  prompts: Object.freeze(["review-telemetry"]),
});

export const MCP_FORMAL_CHECK_IDS = Object.freeze([
  "real-transport",
  "server-connected",
  "tools-discovered",
  "resources-discovered",
  "prompts-discovered",
  "tool-call-observed",
  "resource-read-observed",
  "prompt-retrieval-observed",
  "failure-recovered",
  "inspector-verified",
]);

export function runOfflineMcpDiscovery() {
  return {
    fixture_version: "1",
    lesson_id: "t19-mcp-discovery",
    mode: "offline-fallback",
    transport: "deterministic-in-memory",
    protocol_version: "conceptual-only",
    server: { name: "t19-discovery-server", version: "1.0.0" },
    capabilities: {
      tools: [...OFFLINE_MCP_CAPABILITIES.tools],
      resources: [...OFFLINE_MCP_CAPABILITIES.resources],
      prompts: [...OFFLINE_MCP_CAPABILITIES.prompts],
    },
    observations: {
      server_connected: true,
      tools_listed: true,
      resources_listed: true,
      prompts_listed: true,
      tool_called: true,
      resource_read: true,
      prompt_retrieved: true,
      failure_recovered: true,
    },
    inspector: { verified: false, methods: [] },
  };
}

export function offlineEvidenceDocument(courseVersion, checkedOn = new Date().toISOString().slice(0, 10)) {
  const checks = [
    { id: "offline-deterministic", result: "passed" },
    { id: "real-transport", result: "failed" },
    { id: "server-connected", result: "failed" },
    { id: "tools-discovered", result: "failed" },
    { id: "resources-discovered", result: "failed" },
    { id: "prompts-discovered", result: "failed" },
    { id: "tool-call-observed", result: "failed" },
    { id: "resource-read-observed", result: "failed" },
    { id: "prompt-retrieval-observed", result: "failed" },
    { id: "failure-recovered", result: "failed" },
    { id: "inspector-verified", result: "failed" },
  ];
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: courseVersion,
    lesson_id: "t19-mcp-discovery",
    result: "partial",
    anonymous: true,
    checked_on: checkedOn,
    summary: "部分证据已通过，仍有证据需要补齐。",
    evidence: checks,
    mcp_mode: "offline-fallback",
    transport: "deterministic-in-memory",
    capabilities: OFFLINE_MCP_CAPABILITIES,
  };
}
