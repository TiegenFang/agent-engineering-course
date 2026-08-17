/**
 * Offline, deterministic Plugin package audit fixture.
 *
 * The fixture describes metadata only.  It never downloads a marketplace,
 * invokes a hook, starts an MCP server, or runs an install script.  The
 * resulting evidence keeps only stable identifiers and audit decisions.
 */

export const PLUGIN_AUDIT_LESSON_ID = "t18-plugin-audit";
export const PLUGIN_AUDIT_VERSION = "1";

export const PLUGIN_COMPONENT_TYPES = Object.freeze([
  "skill",
  "command",
  "hook",
  "mcp",
]);

export const PLUGIN_AUDIT_FIELDS = Object.freeze([
  "origin",
  "version",
  "license",
  "permissions",
  "network",
  "dependencies",
  "lifecycle",
  "execution",
]);

export const PLUGIN_LIFECYCLE_ACTIONS = Object.freeze([
  "upgrade",
  "rollback",
  "uninstall",
]);

export const PLUGIN_AUDIT_FINDINGS = Object.freeze([
  "license-unknown",
  "version-unpinned",
  "provenance-unpinned",
  "permission-broad",
  "network-enabled",
  "dependency-unpinned",
  "install-script",
  "lifecycle-gap",
]);

const clone = (value) => JSON.parse(JSON.stringify(value));

/**
 * These are teaching fixtures, not copies of a third-party plugin.  The
 * paths and commands are inert strings shown for inspection only.
 */
export const PLUGIN_AUDIT_PROFILES = Object.freeze({
  reviewable: {
    id: "reviewable",
    label: "可审计的本地样包",
    description: "固定版本、已知许可证、无安装脚本的离线演示包。",
    manifestPath: ".claude-plugin/plugin.json",
    manifest: {
      name: "telemetry-review",
      version: "1.2.0",
      description: "Review synthetic telemetry reports",
      license: "MIT",
    },
    provenance: {
      registry: "course-fixture",
      revision: "v1.2.0",
      digest: "sha256:fixture-reviewable-v1",
    },
    components: [
      { type: "skill", name: "report-review", location: "skills/report-review/SKILL.md" },
      { type: "command", name: "audit-report", location: "commands/audit-report.md" },
      { type: "hook", name: "preflight", event: "PreToolUse", action: "node ./hooks/preflight.mjs" },
      {
        type: "mcp",
        name: "telemetry-readonly",
        transport: "stdio",
        command: "python",
        args: ["-m", "synthetic_telemetry_mcp"],
      },
    ],
    permissions: ["read-project-files"],
    network: { install: false, runtime: false },
    dependencies: [
      { name: "python", version: ">=3.11", pinned: true },
      { name: "synthetic-telemetry-schema", version: "2.0.0", pinned: true },
    ],
    installScripts: false,
    lifecycle: {
      upgrade: "review manifest, digest and release notes before replacing",
      rollback: "retain the previous cache version until the new one is verified",
      uninstall: "remove the selected scope, then reload the client",
    },
  },
  "community-shape": {
    id: "community-shape",
    label: "社区目录形状（仅读）",
    description: "模拟参考仓库常见的 skills/commands 目录；缺少完整 provenance 时必须停在审计。",
    manifestPath: ".claude-plugin/plugin.json",
    manifest: {
      name: "community-report-tools",
      version: "0.4.0",
      description: "Community report workflows",
      license: "UNKNOWN",
    },
    provenance: {
      registry: "community-catalog",
      revision: "main",
      digest: null,
    },
    components: [
      { type: "skill", name: "report-review", location: "skills/report-review/SKILL.md" },
      { type: "command", name: "report-check", location: "commands/report-check.md" },
    ],
    permissions: ["read-project-files"],
    network: { install: false, runtime: false },
    dependencies: [{ name: "report-cli", version: "latest", pinned: false }],
    installScripts: false,
    lifecycle: {
      upgrade: "pause and compare a signed release before update",
      rollback: "keep a known-good version outside the active scope",
      uninstall: "remove only the selected scope and verify no settings remain",
    },
  },
  "needs-review": {
    id: "needs-review",
    label: "高风险包（拒绝安装）",
    description: "模拟未声明许可证、宽权限、运行时网络和安装脚本；只查看元数据。",
    manifestPath: ".claude-plugin/plugin.json",
    manifest: {
      name: "nightly-helper",
      version: "0.0.0",
      description: "Nightly automation helper",
      license: "UNDECLARED",
    },
    provenance: {
      registry: "unknown-marketplace",
      revision: "main",
      digest: null,
    },
    components: [
      { type: "skill", name: "nightly-summary", location: "skills/nightly-summary/SKILL.md" },
      { type: "command", name: "run-nightly", location: "commands/run-nightly.md" },
      { type: "hook", name: "post-edit", event: "PostToolUse", action: "pwsh -File ./hooks/post-edit.ps1" },
      {
        type: "mcp",
        name: "remote-helper",
        transport: "sse",
        command: "https://example.invalid/mcp",
        args: [],
      },
    ],
    permissions: ["read-project-files", "shell", "network"],
    network: { install: true, runtime: true },
    dependencies: [{ name: "nightly-cli", version: "latest", pinned: false }],
    installScripts: true,
    lifecycle: {
      upgrade: "not documented",
      rollback: "not documented",
      uninstall: "not documented",
    },
  },
});

const safeProfile = (profileId) => {
  const profile = PLUGIN_AUDIT_PROFILES[profileId];
  if (!profile) {
    const error = new Error(`Unknown plugin audit profile: ${profileId}`);
    error.code = "unknown-profile";
    throw error;
  }
  return profile;
};

const hasPinnedRevision = (profile) =>
  /^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(profile.provenance.revision)
  && typeof profile.provenance.digest === "string"
  && profile.provenance.digest.startsWith("sha256:");

const hasKnownLicense = (profile) =>
  typeof profile.manifest.license === "string"
  && !["UNKNOWN", "UNDECLARED", ""].includes(profile.manifest.license);

const componentTypes = (profile) => [...new Set(profile.components.map((component) => component.type))];

const dependencyIsPinned = (dependency) => dependency.pinned === true && dependency.version !== "latest";

/** Inspect a fixture without executing any component. */
export function auditPluginPackage(profileId = "reviewable") {
  const profile = safeProfile(profileId);
  const findings = [];
  if (!hasKnownLicense(profile)) findings.push("license-unknown");
  if (!/^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(profile.manifest.version)) {
    findings.push("version-unpinned");
  }
  if (!hasPinnedRevision(profile)) findings.push("provenance-unpinned");
  if (profile.permissions.some((permission) => ["shell", "network", "write-system"].includes(permission))) {
    findings.push("permission-broad");
  }
  if (profile.network.install || profile.network.runtime) findings.push("network-enabled");
  if (profile.dependencies.some((dependency) => !dependencyIsPinned(dependency))) {
    findings.push("dependency-unpinned");
  }
  if (profile.installScripts) findings.push("install-script");
  if (PLUGIN_LIFECYCLE_ACTIONS.some((action) => profile.lifecycle[action] === "not documented")) {
    findings.push("lifecycle-gap");
  }

  const status = findings.length === 0
    ? "reviewable"
    : (findings.includes("install-script") && findings.includes("network-enabled")
      ? "do-not-install"
      : "needs-review");

  return {
    profile: profile.id,
    label: profile.label,
    status,
    findings,
    components: componentTypes(profile),
    inspected: [...PLUGIN_AUDIT_FIELDS],
    lifecycle: [...PLUGIN_LIFECYCLE_ACTIONS],
    offline: true,
    executed: false,
    manifest: clone(profile.manifest),
    manifestPath: profile.manifestPath,
    provenance: clone(profile.provenance),
    permissions: [...profile.permissions],
    network: clone(profile.network),
    dependencies: clone(profile.dependencies),
    installScripts: profile.installScripts,
    componentDetails: clone(profile.components),
    lifecycleDetails: clone(profile.lifecycle),
  };
}

const summarizeRun = (run, id) => ({
  id,
  fixture: run.profile,
  status: run.status,
  findings: [...run.findings],
  components: [...run.components],
  inspected: [...run.inspected],
  lifecycle: [...run.lifecycle],
  offline: run.offline,
  executed: run.executed,
});

export function createPluginAuditSession(profileId = "reviewable") {
  const current = auditPluginPackage(profileId);
  return { version: PLUGIN_AUDIT_VERSION, current, runs: [], lastRun: null };
}

export function updatePluginAuditSession(session, profileId) {
  if (!session || session.version !== PLUGIN_AUDIT_VERSION || !Array.isArray(session.runs)) {
    const error = new Error("Invalid plugin audit session");
    error.code = "invalid-session";
    throw error;
  }
  return { ...session, current: auditPluginPackage(profileId), lastRun: null };
}

export function recordPluginAuditObservation(session) {
  if (!session || !session.current || session.version !== PLUGIN_AUDIT_VERSION) {
    const error = new Error("No plugin audit result is ready to record");
    error.code = "invalid-session";
    throw error;
  }
  const id = `run-${session.runs.length + 1}`;
  const run = summarizeRun(session.current, id);
  return { ...session, runs: [...session.runs, run], lastRun: run };
}

const classify = (checks) => {
  if (checks.every((check) => check.result === "passed")) return "passed";
  if (checks.every((check) => check.result === "failed")) return "failed";
  return "partial";
};

export function derivePluginAuditChecks(session) {
  const runs = Array.isArray(session?.runs) ? session.runs : [];
  const components = new Set(runs.flatMap((run) => run.components));
  const inspected = new Set(runs.flatMap((run) => run.inspected));
  const lifecycle = new Set(runs.flatMap((run) => run.lifecycle));
  const hasRiskyPackage = runs.some((run) => run.status !== "reviewable" && run.findings.length > 0);
  return [
    { id: "manifest-reviewed", result: runs.length > 0 ? "passed" : "failed" },
    {
      id: "component-composition-mapped",
      result: PLUGIN_COMPONENT_TYPES.every((type) => components.has(type)) ? "passed" : "failed",
    },
    {
      id: "supply-chain-fields-audited",
      result: PLUGIN_AUDIT_FIELDS.every((field) => inspected.has(field)) ? "passed" : "failed",
    },
    { id: "unsafe-package-contained", result: hasRiskyPackage ? "passed" : "failed" },
    {
      id: "lifecycle-reviewed",
      result: PLUGIN_LIFECYCLE_ACTIONS.every((action) => lifecycle.has(action)) ? "passed" : "failed",
    },
    {
      id: "offline-no-install",
      result: runs.length > 0 && runs.every((run) => run.offline === true && run.executed === false)
        ? "passed"
        : "failed",
    },
  ];
}

export function buildPluginAuditEvidence(session, { courseVersion, checkedOn } = {}) {
  if (typeof courseVersion !== "string" || !courseVersion) {
    const error = new Error("courseVersion is required");
    error.code = "invalid-course-version";
    throw error;
  }
  const checks = derivePluginAuditChecks(session);
  const result = classify(checks);
  const runs = Array.isArray(session?.runs) ? session.runs : [];
  return {
    contract: "agent-engineering-course/evidence",
    contract_version: "1",
    course_version: courseVersion,
    lesson_id: PLUGIN_AUDIT_LESSON_ID,
    result,
    anonymous: true,
    checked_on: checkedOn ?? new Date().toISOString().slice(0, 10),
    summary: {
      passed: "所有必需证据均已通过。",
      partial: "部分证据已通过，仍有证据需要补齐。",
      failed: "证据未通过，请根据本地检查结果恢复后重试。",
    }[result],
    evidence: checks,
    audit: {
      version: PLUGIN_AUDIT_VERSION,
      runs: runs.map((run) => ({
        id: run.id,
        fixture: run.profile,
        status: run.status,
        findings: [...run.findings],
        components: [...run.components],
        inspected: [...run.inspected],
        lifecycle: [...run.lifecycle],
        offline: run.offline,
        executed: run.executed,
      })),
      observed_findings: [...new Set(runs.flatMap((run) => run.findings))].sort(),
      observed_components: [...new Set(runs.flatMap((run) => run.components))].sort(),
      observed_fields: [...new Set(runs.flatMap((run) => run.inspected))].sort(),
      observed_lifecycle: [...new Set(runs.flatMap((run) => run.lifecycle))].sort(),
    },
  };
}

export const findingLabels = Object.freeze({
  "license-unknown": "许可证未声明或无法确认",
  "version-unpinned": "包版本不满足可追踪格式",
  "provenance-unpinned": "来源 revision/digest 未固定",
  "permission-broad": "请求 shell、network 或系统写权限",
  "network-enabled": "安装或运行时需要网络",
  "dependency-unpinned": "依赖版本未固定",
  "install-script": "声明了安装脚本",
  "lifecycle-gap": "升级、回滚或卸载说明缺失",
});

export const statusLabels = Object.freeze({
  reviewable: "可继续人工复核",
  "needs-review": "需要补充审计",
  "do-not-install": "拒绝安装",
});
