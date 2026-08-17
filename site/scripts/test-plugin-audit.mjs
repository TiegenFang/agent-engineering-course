import assert from "node:assert/strict";
import test from "node:test";

import {
  PLUGIN_AUDIT_FIELDS,
  PLUGIN_COMPONENT_TYPES,
  PLUGIN_LIFECYCLE_ACTIONS,
  auditPluginPackage,
  buildPluginAuditEvidence,
  createPluginAuditSession,
  recordPluginAuditObservation,
  updatePluginAuditSession,
} from "../src/lib/plugin-audit.mjs";

const setOf = (values) => new Set(values);

test("plugin audit fixtures are deterministic and inspect metadata only", () => {
  const first = auditPluginPackage("needs-review");
  const second = auditPluginPackage("needs-review");

  assert.deepEqual(first, second);
  assert.equal(first.status, "do-not-install");
  assert.deepEqual(setOf(first.components), setOf(PLUGIN_COMPONENT_TYPES));
  assert.deepEqual(setOf(first.inspected), setOf(PLUGIN_AUDIT_FIELDS));
  assert.deepEqual(setOf(first.lifecycle), setOf(PLUGIN_LIFECYCLE_ACTIONS));
  assert.equal(first.offline, true);
  assert.equal(first.executed, false);
  assert.ok(first.findings.includes("license-unknown"));
  assert.ok(first.findings.includes("network-enabled"));
  assert.ok(first.findings.includes("install-script"));
});

test("community directory shape is not treated as quality proof", () => {
  const result = auditPluginPackage("community-shape");

  assert.equal(result.status, "needs-review");
  assert.ok(result.findings.includes("license-unknown"));
  assert.ok(result.findings.includes("provenance-unpinned"));
  assert.ok(result.findings.includes("dependency-unpinned"));
  assert.deepEqual(result.components, ["skill", "command"]);
});

test("three recorded observations produce complete anonymous evidence", () => {
  let session = createPluginAuditSession("reviewable");
  for (const profile of ["reviewable", "community-shape", "needs-review"]) {
    session = updatePluginAuditSession(session, profile);
    session = recordPluginAuditObservation(session);
  }

  const evidence = buildPluginAuditEvidence(session, {
    courseVersion: "2.0.0",
    checkedOn: "2026-08-13",
  });
  assert.equal(evidence.lesson_id, "t18-plugin-audit");
  assert.equal(evidence.result, "passed");
  assert.equal(evidence.anonymous, true);
  assert.deepEqual(
    evidence.evidence.map((check) => check.id),
    [
      "manifest-reviewed",
      "component-composition-mapped",
      "supply-chain-fields-audited",
      "unsafe-package-contained",
      "lifecycle-reviewed",
      "offline-no-install",
    ],
  );
  assert.deepEqual(evidence.audit.observed_components, ["command", "hook", "mcp", "skill"]);
  assert.deepEqual(evidence.audit.observed_lifecycle, ["rollback", "uninstall", "upgrade"]);
  assert.equal("manifest" in evidence.audit, false);
  assert.equal(JSON.stringify(evidence).includes("example.invalid"), false);
});

test("unknown profiles cannot be audited", () => {
  assert.throws(
    () => auditPluginPackage("untrusted-download"),
    (error) => error.code === "unknown-profile",
  );
});
