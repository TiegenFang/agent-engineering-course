"""Public command-line entry point for the local course checker."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .evidence import (
    EvidenceError,
    _require_identifier,
    _reject_sensitive_unknown_fields,
    build_evidence_document,
    classify_checks,
    validate_evidence_document,
)
from .project_rules import PROJECT_RULES_LESSON_ID, load_project_rules_checks
from .openai_responses import (
    OPENAI_RESPONSES_LESSON_ID,
    adapter_package_result,
    load_openai_responses_checks,
)
from .research_capstone import (
    RESEARCH_CAPSTONE_LESSON_ID,
    load_research_capstone_checks as load_research_capstone_checks_external,
)
from .anthropic_messages import (
    ANTHROPIC_MESSAGES_LESSON_ID,
    adapter_package_result as anthropic_messages_package_result,
    load_anthropic_messages_checks,
)
from .multi_agent import (
    MULTI_AGENT_LESSON_ID,
    validate_multi_agent_evidence_checks,
    validate_multi_agent_experiment,
)
from .production import (
    PRODUCTION_CHECK_IDS,
    PRODUCTION_LESSON_ID,
    validate_production_evidence_checks,
    validate_production_fixture,
)
from .skill import (
    SKILL_LESSON_ID,
    skill_package_result,
    validate_skill_evidence_checks,
    validate_skill_simulation,
)


EXPECTED_BOUNDARIES = {
    "site": "site",
    "labs": "labs",
    "checker": "checker",
    "docs": "docs",
}
ENVIRONMENT_LESSON_ID = "t05-environment"
ENVIRONMENT_CHECK_IDS = frozenset(
    {
        "powershell-7",
        "editor-command",
        "python-on-path",
        "python-version",
        "git-on-path",
        "git-version",
        "github-account",
        "coding-agent-account",
    }
)
ENVIRONMENT_PLATFORM_SHELLS = {
    "windows": frozenset({"powershell"}),
    "macos": frozenset({"powershell", "zsh"}),
    "linux": frozenset({"powershell", "bash"}),
}
GIT_SAFETY_LESSON_ID = "t06-git-safety"
GIT_SAFETY_CHECK_IDS = frozenset(
    {
        "status-baseline",
        "diff-reviewed",
        "selective-stage",
        "intentional-commit",
        "branch-inspected",
        "history-inspected",
        "secret-ignored",
        "recovery-complete",
    }
)
GIT_SAFETY_STAGE_IDS = (
    "baseline",
    "branch-history",
    "change-created",
    "selective-stage",
    "first-commit-decision",
    "first-commit-recorded",
    "secret-before",
    "secret-ignored",
    "secret-commit-decision",
    "secret-commit-recorded",
    "recovery-before",
    "recovery-recorded",
    "final",
)
GIT_SAFETY_STAGE_OBSERVATIONS = {
    "baseline": frozenset({"repo", "clean", "head", "branch", "history"}),
    "branch-history": frozenset({"branch", "history"}),
    "change-created": frozenset({"tracked_change", "untracked_change", "diff"}),
    "selective-stage": frozenset(
        {"staged_change", "unstaged_change", "staged_diff", "diff"}
    ),
    "first-commit-decision": frozenset(
        {"staged_change", "secret_untracked", "approval"}
    ),
    "first-commit-recorded": frozenset({"head_changed", "clean"}),
    "secret-before": frozenset({"secret_absent", "ignore_absent"}),
    "secret-ignored": frozenset(
        {"secret_present", "ignored", "untracked", "ignore_unstaged"}
    ),
    "secret-commit-decision": frozenset(
        {"staged_ignore", "secret_untracked", "approval"}
    ),
    "secret-commit-recorded": frozenset({"head_changed", "clean"}),
    "recovery-before": frozenset({"tracked_change", "diff"}),
    "recovery-recorded": frozenset({"clean", "matches_head"}),
    "final": frozenset({"clean", "secret_untracked"}),
}

LESSON_REQUIRED_FIELDS = {
    "id",
    "title",
    "stage",
    "duration_minutes",
    "prerequisites",
    "outcomes",
    "artifacts",
    "primary_tool",
    "migration_tool",
    "platforms",
    "versions",
    "verified_on",
    "access",
    "risk",
    "sources",
    "licenses",
}

COURSE_REQUIRED_FIELDS = {
    "name",
    "subtitle",
    "positioning",
    "core_duration",
    "advanced_duration",
}

CONTRACT_REQUIRED_FIELDS = {"content", "lesson_schema", "sources"}
PLATFORM_REQUIRED_FIELDS = {"primary", "secondary"}
VERSION_REQUIRED_FIELDS = {"client", "sdk", "model", "protocol"}
ACCESS_REQUIRED_FIELDS = {"accounts", "cost", "network"}
RISK_REQUIRED_FIELDS = {"permissions", "side_effects", "staleness"}
SOURCE_REQUIRED_FIELDS = {
    "id",
    "title",
    "url",
    "source_role",
    "pinned_version",
    "usage",
    "license_or_terms",
    "copied_assets",
}

T02_TRACE_CHECK_IDS = (
    "prediction-recorded",
    "trace-observed",
    "stop-condition-observed",
)
T02_TRACE_VERSION = "1"
T02_MAX_STEPS = 6
T02_TRACE_CONTRACTS = {
    "success": (
        ("prediction-1", "prediction"),
        ("response-1", "response"),
        ("tool-request-1", "tool-request"),
        ("tool-execution-1", "tool-execution"),
        ("tool-result-1", "tool-result"),
        ("response-2", "response"),
        ("stop-1", "stop"),
    ),
    "error": (
        ("prediction-1", "prediction"),
        ("response-1", "response"),
        ("tool-request-1", "tool-request"),
        ("tool-execution-1", "tool-execution"),
        ("tool-result-1", "tool-result"),
        ("stop-1", "stop"),
    ),
}
T02_TRACE_EVENT_CONTRACT = T02_TRACE_CONTRACTS["success"][1:-1]

T03_INSTRUCTION_CHECK_IDS = (
    "prediction-recorded",
    "baseline-compared",
    "conflict-contained",
    "injection-contained",
    "long-instruction-diagnosed",
    "migration-completed",
)
T03_INSTRUCTION_VERSION = "2"
T03_BASELINE_ID = "telemetry-report-v1"
T03_SCENARIO_ORDER = ("baseline", "conflict", "injection", "long")
T03_SCENARIOS = set(T03_SCENARIO_ORDER)
T03_VARIANT_CONTRACTS = {
    "temperature-daily": {"subject": "温度", "unit": "°C", "limit": "最近 5 条有效记录"},
    "pressure-night": {"subject": "压力", "unit": "kPa", "limit": "最近 3 条有效记录"},
}
T03_VARIANTS = set(T03_VARIANT_CONTRACTS)
T03_AMBIGUOUS_OUTCOMES = {
    "under-specified",
    "conflict-unresolved",
    "injection-followed",
    "overloaded",
}
T03_ENGINEERED_OUTCOMES = {
    "controlled",
    "conflict-contained",
    "injection-contained",
    "scoped",
    "incomplete",
    "overlong",
    "conflict-unresolved",
    "injection-uncontained",
    "variant-mismatch",
}
CONTEXT_BUDGET_LESSON_ID = "t14-context-budget"
CONTEXT_BUDGET_SIMULATION_VERSION = "1"
CONTEXT_BUDGET_FINDINGS = frozenset({"insufficient", "pollution", "crowding", "ready"})
CONTEXT_BUDGET_REQUIRED_FINDINGS = frozenset({"insufficient", "pollution", "crowding"})
CONTEXT_BUDGET_CHECK_IDS = (
    "working-set-selected",
    "risk-signals-observed",
    "boundary-tested",
    "offline-deterministic",
)
HOOKS_TASKS_LESSON_ID = "t21-hooks-tasks"
HOOKS_TASKS_EXPERIMENT_VERSION = "1"
HOOKS_TASKS_MODES = frozenset({"hook", "task", "schedule", "background"})
HOOKS_TASKS_PERMISSIONS = frozenset({"blocked", "allowed"})
HOOKS_TASKS_CHECK_IDS = (
    "trigger-observed",
    "deduplication-observed",
    "permission-boundary",
    "stop-condition",
    "failure-recovered",
    "side-effect-not-triggered",
    "explicit-task-recorded",
    "offline-deterministic",
)

MCP_CALL_LESSON_ID = "t20-mcp-call"
MCP_CALL_EXPERIMENT_VERSION = "1"
MCP_CALL_PROTOCOL_VERSION = "2026-07-28"
MCP_CALL_TOOL_NAMES = ("telemetry.read", "report.publish")
MCP_CALL_FAULT_IDS = frozenset({"transport", "tool", "data", "protocol"})
MCP_CALL_CHECK_IDS = (
    "transport-connected",
    "discovery-bridge",
    "permission-confirmed",
    "tool-called",
    "side-effect-bounded",
    "fault-observed",
    "fault-recovered",
    "no-sensitive-output",
    "inspector-checked",
    "fallback-explicit",
)
CODEX_TASK_LESSON_ID = "t04-codex-repository-task"
CODEX_TASK_TRACE_VERSION = "1"
CODEX_TASK_ID = "telemetry-report-v1"
CODEX_TASK_STAGE_IDS = (
    "baseline",
    "clarify",
    "plan",
    "failure-observed",
    "change",
    "recovery",
    "review",
    "delivery",
)
CODEX_TASK_STAGE_OBSERVATIONS = {
    "baseline": frozenset({"repo", "clean", "head", "branch"}),
    "clarify": frozenset({"goal", "non_goal", "acceptance"}),
    "plan": frozenset({"files", "commands", "permissions", "stop", "approval"}),
    "failure-observed": frozenset({"expected_failure", "error_classified"}),
    "change": frozenset({"source_changed", "diff", "approval"}),
    "recovery": frozenset({"tests_passed", "report_generated"}),
    "review": frozenset({"diff_reviewed", "scope_clean", "no_secrets"}),
    "delivery": frozenset({"handoff", "evidence_ready", "human_approved"}),
}
CODEX_TASK_CHECK_IDS = (
    "clarification-recorded",
    "plan-recorded",
    "failure-recovered",
    "scoped-change",
    "tests-passed",
    "diff-reviewed",
    "report-generated",
    "delivery-recorded",
)

CLAUDE_MIGRATION_LESSON_ID = "t04-claude-migration"
CLAUDE_MIGRATION_TRACE_VERSION = "1"
CLAUDE_MIGRATION_TASK_ID = "pressure-report-v1"
CLAUDE_MIGRATION_STAGE_IDS = (
    "baseline",
    "clarify",
    "plan",
    "official-facts",
    "failure-observed",
    "change",
    "recovery",
    "review",
    "delivery",
)
CLAUDE_MIGRATION_STAGE_OBSERVATIONS = {
    "baseline": frozenset({"repo", "clean", "head", "branch", "path_declared"}),
    "clarify": frozenset({"goal", "non_goal", "acceptance", "migration"}),
    "plan": frozenset({"files", "commands", "permissions", "stop", "approval"}),
    "official-facts": frozenset(
        {"installation", "operation", "permissions", "cost", "date", "no_live_claim"}
    ),
    "failure-observed": frozenset(
        {"expected_failure", "error_classified", "no_fake_result"}
    ),
    "change": frozenset({"source_changed", "diff", "approval", "variant_changed"}),
    "recovery": frozenset({"tests_passed", "report_generated", "summary_only"}),
    "review": frozenset(
        {"diff_reviewed", "scope_clean", "no_secrets", "path_complete"}
    ),
    "delivery": frozenset(
        {"handoff", "evidence_ready", "human_approved", "live_call_not_claimed"}
    ),
}
CLAUDE_MIGRATION_CHECK_IDS = (
    "clarification-recorded",
    "plan-recorded",
    "official-facts-recorded",
    "migration-input-changed",
    "failure-recovered",
    "tests-passed",
    "permission-cost-compared",
    "path-completed",
    "live-claude-not-claimed",
    "report-generated",
    "delivery-recorded",
)
CLAUDE_MIGRATION_VARIANT = {
    "id": "pressure-night",
    "subject": "pressure",
    "units": ("kPa", "psi", "bar"),
    "record_limit": "recent-3-valid",
    "outputs": ("mean_kpa", "peak_kpa", "alarm_count"),
}

T15_CONTEXT_RECOVERY_LESSON_ID = "t15-context-recovery"
T15_CONTEXT_RECOVERY_VERSION = "1"
T15_CONTEXT_RECOVERY_BASELINE_ID = "telemetry-report-v1"
T15_CONTEXT_RECOVERY_CHECK_IDS = (
    "compression-compared",
    "distortion-detected",
    "constraint-omission-detected",
    "pollution-recovered",
    "handoff-complete",
    "layers-distinguished",
)
T15_CONTEXT_RECOVERY_MODES = (
    "faithful",
    "distorted",
    "constraint-omitted",
)
T15_CONTEXT_RECOVERY_AFTER_OUTCOMES = {
    "faithful": "faithful",
    "distorted": "distorted",
    "constraint-omitted": "constraint-omitted",
}
T15_CONTEXT_RECOVERY_LAYER_VALUES = {
    "context": "current-working-set",
    "history": "record-only",
    "memory": "owned-and-expiring",
}
T15_CONTEXT_RECOVERY_RISKS = {
    "compressed-context-may-be-lossy",
    "history-is-not-a-current-constraint",
    "memory-promotion-requires-owner-and-lifetime",
}
MCP_DISCOVERY_LESSON_ID = "t19-mcp-discovery"
MCP_DISCOVERY_FIXTURE_VERSION = "1"
MCP_DISCOVERY_PROTOCOL_VERSION = "2026-07-28"
MCP_DISCOVERY_FORMAL_CHECK_IDS = (
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
)
MCP_DISCOVERY_CAPABILITIES = {
    "tools": ("summarize_telemetry",),
    "resources": ("telemetry://demo/snapshot",),
    "prompts": ("review-telemetry",),
}
MCP_DISCOVERY_INSPECTOR_METHODS = frozenset(
    {"tools/list", "resources/list", "prompts/list"}
)

MEMORY_LESSON_ID = "t16-memory"
MEMORY_EXPERIMENT_VERSION = "1"
MEMORY_BASELINE_ID = "memory-ledger-v1"
MEMORY_STAGE_IDS = (
    "design",
    "write",
    "recall",
    "stale-update",
    "pollution",
    "delete",
)
MEMORY_STAGE_OBSERVATIONS = {
    "design": frozenset({"purpose", "owner", "lifetime", "deletion", "types"}),
    "write": frozenset({"record_created", "metadata_complete", "sensitive_excluded"}),
    "recall": frozenset({"context_window", "summary", "retrieval", "injection", "correct_recall"}),
    "stale-update": frozenset({"stale_detected", "replacement_confirmed", "old_not_retrieved"}),
    "pollution": frozenset({"untrusted_quarantined", "trusted_boundary_restored", "revalidated"}),
    "delete": frozenset({"deletion_requested", "deletion_confirmed", "record_absent"}),
}
MEMORY_TYPES = ("short-term", "long-term", "external")
MEMORY_CONTEXT_MODES = ("window-budget", "summary", "retrieval", "injection")
MEMORY_CHECK_IDS = (
    "purpose-defined",
    "owner-defined",
    "lifetime-defined",
    "deletion-defined",
    "memory-types-separated",
    "context-window-managed",
    "summary-retrieval-injection",
    "correct-recall",
    "stale-memory-corrected",
    "pollution-contained",
    "sensitive-excluded",
    "deletion-confirmed",
    "offline-deterministic",
)

PLUGIN_AUDIT_LESSON_ID = "t18-plugin-audit"
PLUGIN_AUDIT_VERSION = "1"
PLUGIN_COMPONENT_TYPES = ("skill", "command", "hook", "mcp")
PLUGIN_AUDIT_FIELDS = (
    "origin",
    "version",
    "license",
    "permissions",
    "network",
    "dependencies",
    "lifecycle",
    "execution",
)
PLUGIN_LIFECYCLE_ACTIONS = ("upgrade", "rollback", "uninstall")
PLUGIN_AUDIT_PROFILES = frozenset({"reviewable", "community-shape", "needs-review"})
PLUGIN_AUDIT_STATUSES = frozenset({"reviewable", "needs-review", "do-not-install"})
PLUGIN_AUDIT_FINDINGS = frozenset(
    {
        "license-unknown",
        "version-unpinned",
        "provenance-unpinned",
        "permission-broad",
        "network-enabled",
        "dependency-unpinned",
        "install-script",
        "lifecycle-gap",
    }
)
PLUGIN_AUDIT_CHECK_IDS = (
    "manifest-reviewed",
    "component-composition-mapped",
    "supply-chain-fields-audited",
    "unsafe-package-contained",
    "lifecycle-reviewed",
    "offline-no-install",
)

RESEARCH_CAPSTONE_LESSON_ID = "t23-research-capstone"
RESEARCH_CAPSTONE_VERSION = "1"
RESEARCH_CAPSTONE_BASELINE_ID = "telemetry-research-v1"
RESEARCH_CAPSTONE_INPUTS = {
    "temperature-daily": {"subject": "temperature", "unit": "°C", "limit": 5},
    "pressure-night": {"subject": "pressure", "unit": "kPa", "limit": 3},
}
RESEARCH_CAPSTONE_FAULTS = frozenset(
    {"none", "missing-values", "stale-memory", "mcp-denied"}
)
RESEARCH_CAPSTONE_CHECK_IDS = (
    "context-recorded",
    "memory-governed",
    "skill-applied",
    "mcp-boundary",
    "script-reproducible",
    "figure-produced",
    "record-complete",
    "report-complete",
    "evidence-exported",
    "migration-complete",
    "rubric-complete",
    "offline-deterministic",
)
T26_OFFLINE_AGENT_LOOP_LESSON_ID = "t26-offline-agent-loop"
T26_OFFLINE_AGENT_LOOP_VERSION = "1"
T26_OFFLINE_AGENT_LOOP_IMPLEMENTATION = "python-stdlib"
T26_OFFLINE_AGENT_LOOP_FRAMEWORK = "none"
T26_OFFLINE_AGENT_LOOP_SCENARIOS = (
    "success",
    "tool-failure",
    "invalid-args",
    "budget-stop",
    "retry-recovery",
)
T26_OFFLINE_AGENT_LOOP_CHECK_IDS = (
    "deterministic-fixture",
    "response-tool-loop",
    "state-refill",
    "structured-output",
    "tool-failure-stop",
    "invalid-arguments-recovery",
    "budget-stop",
    "retry-recovery",
    "framework-free",
)
T26_OFFLINE_AGENT_LOOP_EVENT_KINDS = {
    "response",
    "tool_call",
    "tool_execution",
    "state_refill",
    "structured_output",
    "stop",
}
T26_OFFLINE_AGENT_LOOP_ALLOWED_OUTCOMES = {
    "success",
    "failure",
    "invalid-args",
    "budget-stop",
    "retry-recovery",
}


class ContractError(ValueError):
    """Raised when the public Foundation contract is incomplete."""


def load_json(root: Path, relative_path: str) -> dict[str, Any]:
    relative = Path(relative_path)
    if not relative_path or relative.is_absolute() or ".." in relative.parts:
        raise ContractError(f"Unsafe contract path: {relative_path or '<empty>'}")
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"Missing contract file: {relative_path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON in {relative_path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Contract must be a JSON object: {relative_path}")
    return value


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object")
    return value


def require_fields(
    value: dict[str, Any], required: set[str], label: str, *, exact: bool = True
) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ContractError(f"{label} is missing: {', '.join(missing)}")
    if exact:
        unexpected = sorted(set(value) - required)
        if unexpected:
            raise ContractError(f"{label} has unexpected fields: {', '.join(unexpected)}")


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value


def require_string_list(
    value: Any, label: str, *, allow_empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "a" if allow_empty else "a non-empty"
        raise ContractError(f"{label} must be {qualifier} list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContractError(f"{label} must contain only non-empty strings")
    return value


def require_iso_date(value: Any, label: str) -> str:
    raw = require_string(value, label)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ContractError(f"{label} must be an ISO date (YYYY-MM-DD)") from exc
    if parsed.isoformat() != raw:
        raise ContractError(f"{label} must be an ISO date (YYYY-MM-DD)")
    return raw


def validate_named_string_object(
    value: Any, required: set[str], label: str
) -> dict[str, Any]:
    item = require_object(value, label)
    require_fields(item, required, label)
    for field in required:
        require_string(item[field], f"{label}.{field}")
    return item


def validate_lesson_schema(schema: dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise ContractError("Lesson schema type must be object")
    required = schema.get("required")
    if not isinstance(required, list) or set(required) != LESSON_REQUIRED_FIELDS:
        raise ContractError("Lesson schema required fields do not match the content contract")
    if schema.get("additionalProperties") is not False:
        raise ContractError("Lesson schema must reject additional properties")


def validate_lesson(value: Any, index: int) -> dict[str, Any]:
    lesson = require_object(value, f"Lesson at index {index}")
    lesson_label = f"Lesson {lesson.get('id', '<unknown>')}"
    require_fields(lesson, LESSON_REQUIRED_FIELDS, lesson_label)

    require_string(lesson["id"], f"{lesson_label}.id")
    require_string(lesson["title"], f"{lesson_label}.title")
    require_string(lesson["stage"], f"{lesson_label}.stage")
    duration = lesson["duration_minutes"]
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
        raise ContractError(f"{lesson_label}.duration_minutes must be a positive integer")

    require_string_list(
        lesson["prerequisites"], f"{lesson_label}.prerequisites", allow_empty=True
    )
    for field in ("outcomes", "artifacts", "sources", "licenses"):
        require_string_list(lesson[field], f"{lesson_label}.{field}")
    require_string(lesson["primary_tool"], f"{lesson_label}.primary_tool")
    require_string(lesson["migration_tool"], f"{lesson_label}.migration_tool")

    platforms = require_object(lesson["platforms"], f"{lesson_label}.platforms")
    require_fields(platforms, PLATFORM_REQUIRED_FIELDS, f"{lesson_label}.platforms")
    require_string(platforms["primary"], f"{lesson_label}.platforms.primary")
    require_string_list(
        platforms["secondary"],
        f"{lesson_label}.platforms.secondary",
        allow_empty=True,
    )

    validate_named_string_object(
        lesson["versions"], VERSION_REQUIRED_FIELDS, f"{lesson_label}.versions"
    )

    access = require_object(lesson["access"], f"{lesson_label}.access")
    require_fields(access, ACCESS_REQUIRED_FIELDS, f"{lesson_label}.access")
    require_string_list(
        access["accounts"], f"{lesson_label}.access.accounts", allow_empty=True
    )
    require_string(access["cost"], f"{lesson_label}.access.cost")
    require_string(access["network"], f"{lesson_label}.access.network")

    validate_named_string_object(
        lesson["risk"], RISK_REQUIRED_FIELDS, f"{lesson_label}.risk"
    )
    require_iso_date(lesson["verified_on"], f"{lesson_label}.verified_on")
    return lesson


def validate_source_entries(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    if sources.get("ledger_version") != "1":
        raise ContractError("Unsupported source ledger version")
    require_iso_date(sources.get("verified_on"), "Source ledger verified_on")
    entries = sources.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ContractError("Source ledger must contain at least one entry")

    validated: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for index, value in enumerate(entries):
        entry = require_object(value, f"Source entry at index {index}")
        label = f"Source entry {entry.get('id', '<unknown>')}"
        require_fields(entry, SOURCE_REQUIRED_FIELDS, label, exact=False)
        for field in SOURCE_REQUIRED_FIELDS - {"copied_assets"}:
            require_string(entry[field], f"{label}.{field}")
        if not isinstance(entry["copied_assets"], bool):
            raise ContractError(f"{label}.copied_assets must be a boolean")
        source_id = entry["id"]
        if source_id in source_ids:
            raise ContractError(f"Duplicate source id: {source_id}")
        source_ids.add(source_id)
        validated.append(entry)
    return validated, source_ids


def validate_foundation(root: Path) -> str:
    contract = load_json(root, "course-version.json")
    version = require_string(contract.get("course_version"), "course_version")
    require_iso_date(contract.get("released_on"), "released_on")
    validate_named_string_object(contract.get("course"), COURSE_REQUIRED_FIELDS, "course")

    if contract.get("boundaries") != EXPECTED_BOUNDARIES:
        raise ContractError("Workspace boundaries do not match the course contract")
    for relative_path in EXPECTED_BOUNDARIES.values():
        if not (root / relative_path).is_dir():
            raise ContractError(f"Missing workspace boundary: {relative_path}")

    contracts = require_object(contract.get("contracts"), "contracts")
    require_fields(contracts, CONTRACT_REQUIRED_FIELDS, "contracts")
    for field in CONTRACT_REQUIRED_FIELDS:
        require_string(contracts[field], f"contracts.{field}")

    lesson_schema = load_json(root, contracts["lesson_schema"])
    validate_lesson_schema(lesson_schema)

    content = load_json(root, contracts["content"])
    if content.get("contract_version") != "1":
        raise ContractError("Unsupported content contract version")
    lessons = content.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        raise ContractError("Content contract must contain at least one lesson")
    validated_lessons = [validate_lesson(lesson, index) for index, lesson in enumerate(lessons)]
    lesson_ids = [lesson["id"] for lesson in validated_lessons]
    if len(lesson_ids) != len(set(lesson_ids)):
        raise ContractError("Lesson ids must be unique")
    known_lesson_ids = set(lesson_ids)
    for lesson in validated_lessons:
        prerequisite_ids = set(lesson["prerequisites"])
        if lesson["id"] in prerequisite_ids:
            raise ContractError(f"Lesson {lesson['id']} cannot require itself")
        unknown_prerequisites = sorted(prerequisite_ids - known_lesson_ids)
        if unknown_prerequisites:
            raise ContractError(
                f"Lesson {lesson['id']} references unknown prerequisites: "
                + ", ".join(unknown_prerequisites)
            )

    sources = load_json(root, contracts["sources"])
    _, source_ids = validate_source_entries(sources)
    for lesson in validated_lessons:
        unknown_sources = sorted(set(lesson["sources"]) - source_ids)
        if unknown_sources:
            raise ContractError(
                f"Lesson {lesson['id']} references unknown sources: "
                + ", ".join(unknown_sources)
            )

    return version


def validate_t02_evidence_checks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise EvidenceError("T02 trace evidence checks must be a non-empty list")

    seen: set[str] = set()
    actual_ids: list[str] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T02 trace evidence check {index} must be an object")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T02 trace evidence check {index} needs an id")
        if check.get("result") not in {"passed", "failed", "alternative"}:
            raise EvidenceError(
                f"T02 trace evidence check {check_id}.result is not supported"
            )
        if check_id in seen:
            raise EvidenceError(f"T02 trace evidence check ID repeated: {check_id}")
        seen.add(check_id)
        actual_ids.append(check_id)

    expected_ids = list(T02_TRACE_CHECK_IDS)
    if actual_ids != expected_ids:
        missing = [check_id for check_id in expected_ids if check_id not in seen]
        unknown = [check_id for check_id in actual_ids if check_id not in expected_ids]
        raise EvidenceError(
            "T02 trace evidence IDs must be exactly "
            + ", ".join(expected_ids)
            + (f"; missing: {', '.join(missing)}" if missing else "")
            + (f"; unknown: {', '.join(unknown)}" if unknown else "")
        )
    return value


def validate_t02_trace(trace: Any, *, document_result: str) -> dict[str, Any]:
    if not isinstance(trace, dict):
        raise EvidenceError("T02 completed evidence must include a trace object")
    if trace.get("version") != T02_TRACE_VERSION:
        raise EvidenceError("Unsupported T02 trace version")
    outcome = trace.get("outcome")
    if outcome not in {"success", "error", "budget-stop"}:
        raise EvidenceError("T02 trace outcome must be success, error, or budget-stop")
    max_steps = trace.get("max_steps")
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or not 1 <= max_steps <= T02_MAX_STEPS:
        raise EvidenceError(f"T02 trace max_steps must be an integer from 1 to {T02_MAX_STEPS}")
    if outcome == "budget-stop" and max_steps >= len(T02_TRACE_CONTRACTS["success"]) - 1:
        raise EvidenceError("budget-stop T02 trace must stop before the natural stop step")
    steps = trace.get("steps")
    if not isinstance(steps, list):
        raise EvidenceError("T02 trace steps must be a list")

    if outcome == "budget-stop":
        expected = (
            ("prediction-1", "prediction"),
            *T02_TRACE_EVENT_CONTRACT[:max_steps],
            ("budget-stop-1", "stop"),
        )
    else:
        expected = T02_TRACE_CONTRACTS[outcome]
        minimum_steps = len(expected) - 1
        if max_steps < minimum_steps:
            raise EvidenceError(
                f"T02 {outcome} trace needs max_steps >= {minimum_steps}"
            )
    expected_ids = [step_id for step_id, _ in expected]
    expected_kinds = dict(expected)
    if not steps:
        if document_result in {"failed", "partial"}:
            return {
                "version": T02_TRACE_VERSION,
                "outcome": outcome,
                "max_steps": max_steps,
                "steps": [],
            }
        raise EvidenceError("Completed T02 evidence must include trace steps")
    seen: set[str] = set()
    actual_ids: list[str] = []
    normalized_steps: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise EvidenceError(f"T02 trace step {index} must be an object")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise EvidenceError(f"T02 trace step {index} needs an id")
        if step_id not in expected_kinds:
            raise EvidenceError(f"Unknown T02 trace step ID: {step_id}")
        if step_id in seen:
            raise EvidenceError(f"T02 trace step ID repeated: {step_id}")
        seen.add(step_id)
        actual_ids.append(step_id)

        step_result = step.get("result")
        allowed_results = {"passed", "failed", "alternative"}
        if step_result not in allowed_results:
            raise EvidenceError(
                f"T02 trace step {step_id}.result must be passed or failed"
            )
        kind = step.get("kind")
        if kind != expected_kinds[step_id]:
            raise EvidenceError(
                f"T02 trace step {step_id}.kind does not match the fixed trace contract"
            )
        status = step.get("status")
        if status is not None and status not in {"ok", "passed", "error", "budget"}:
            raise EvidenceError(f"T02 trace step {step_id}.status is not supported")

        if step_id == "prediction-1":
            if status is not None:
                raise EvidenceError("T02 prediction-1 must not have a status")
            if step_result not in {"passed", "failed"}:
                raise EvidenceError("T02 prediction-1 result must be passed or failed")
        elif status is None:
            raise EvidenceError(f"T02 trace step {step_id} needs a status")
        elif status == "budget" and step_id != "budget-stop-1":
            raise EvidenceError("Only budget-stop-1 may have budget status")
        elif step_id == "budget-stop-1" and (status != "budget" or step_result != "alternative"):
            raise EvidenceError("budget-stop-1 must have alternative result and budget status")
        elif step_id != "budget-stop-1" and status == "budget":
            raise EvidenceError("Only budget-stop-1 may have budget status")
        elif status in {"ok", "passed", "error"} and step_result != "passed":
            raise EvidenceError(
                f"T02 trace step {step_id} result must be passed when status is {status}"
            )

        normalized: dict[str, Any] = {
            "id": step_id,
            "kind": expected_kinds[step_id],
            "result": step_result,
        }
        if status is not None:
            normalized["status"] = status
        normalized_steps.append(normalized)

    prefix = expected_ids[: len(actual_ids)]
    if actual_ids != prefix:
        raise EvidenceError("T02 trace step IDs must follow the fixed order")
    if document_result in {"passed", "alternative"} and actual_ids != expected_ids:
        missing = expected_ids[len(actual_ids) :]
        raise EvidenceError(
            "Completed T02 evidence is missing trace steps: " + ", ".join(missing)
        )

    if outcome == "budget-stop" and any(
        step.get("status") == "error" for step in normalized_steps
    ):
        raise EvidenceError(
            "budget-stop T02 trace cannot contain an error status; use outcome error"
        )

    if outcome == "success":
        if any(step.get("status") in {"error", "budget"} for step in normalized_steps):
            raise EvidenceError("Success T02 trace cannot contain error or budget statuses")
        stop = normalized_steps[-1] if actual_ids == expected_ids else None
        if stop is not None and stop.get("status") != "passed":
            raise EvidenceError("Success T02 trace must end with a passed stop")
    elif outcome == "error":
        required_error_steps = {"tool-execution-1", "tool-result-1", "stop-1"}
        by_id = {step["id"]: step for step in normalized_steps}
        if actual_ids == expected_ids and any(
            by_id[step_id].get("status") != "error" for step_id in required_error_steps
        ):
            raise EvidenceError("Error T02 trace must mark execution, result, and stop as error")
        if any(
            step.get("status") == "error" and step["id"] not in required_error_steps
            for step in normalized_steps
        ):
            raise EvidenceError("Only execution, result, and stop may be error in an error trace")
    elif actual_ids == expected_ids and document_result not in {"alternative", "partial"}:
        raise EvidenceError("Completed budget-stop evidence must be alternative")

    if document_result == "passed" and any(
        step["result"] != "passed" for step in normalized_steps
    ):
        raise EvidenceError("Passed T02 evidence cannot contain failed or alternative trace steps")

    return {
        "version": T02_TRACE_VERSION,
        "outcome": outcome,
        "max_steps": max_steps,
        "steps": normalized_steps,
    }


def validate_t02_check_semantics(
    checks: list[dict[str, Any]], trace: dict[str, Any], *, document_result: str
) -> None:
    """Keep the three public check states aligned with the executed trace."""

    check_results = {check["id"]: check["result"] for check in checks}
    steps = trace["steps"]
    outcome = trace["outcome"]
    if outcome == "budget-stop":
        expected_ids = [
            "prediction-1",
            *[step_id for step_id, _ in T02_TRACE_EVENT_CONTRACT[: trace["max_steps"]]],
            "budget-stop-1",
        ]
    else:
        expected_ids = [step_id for step_id, _ in T02_TRACE_CONTRACTS[outcome]]
    complete = [step["id"] for step in steps] == expected_ids
    prediction_result = next(
        (step["result"] for step in steps if step["id"] == "prediction-1"),
        "failed",
    )
    expected_trace_result = "passed" if complete else "failed"
    expected_stop_result = (
        "alternative"
        if complete and outcome == "budget-stop"
        else "passed"
        if complete
        else "failed"
    )
    expected_checks = {
        "prediction-recorded": prediction_result,
        "trace-observed": expected_trace_result,
        "stop-condition-observed": expected_stop_result,
    }
    for check_id, expected in expected_checks.items():
        if check_results[check_id] != expected:
            raise EvidenceError(
                f"T02 evidence check {check_id} does not match trace semantics"
            )
    if document_result == "alternative" and outcome != "budget-stop":
        raise EvidenceError("Alternative T02 evidence requires a budget-stop trace")


def validate_t03_evidence_checks(value: Any) -> list[dict[str, Any]]:
    """Validate the stable learner-facing checks for the instruction lesson."""

    if not isinstance(value, list) or not value:
        raise EvidenceError("T03 instruction evidence checks must be a non-empty list")

    seen: set[str] = set()
    actual_ids: list[str] = []
    normalized: list[dict[str, Any]] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T03 instruction evidence check {index} must be an object")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T03 instruction evidence check {index} needs an id")
        if check_id in seen:
            raise EvidenceError(f"T03 instruction evidence check ID repeated: {check_id}")
        seen.add(check_id)
        actual_ids.append(check_id)
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(
                f"T03 instruction evidence check {check_id}.result is not supported"
            )
        normalized.append({"id": check_id, "result": result})

    expected_ids = list(T03_INSTRUCTION_CHECK_IDS)
    if actual_ids != expected_ids:
        missing = [check_id for check_id in expected_ids if check_id not in seen]
        unknown = [check_id for check_id in actual_ids if check_id not in expected_ids]
        raise EvidenceError(
            "T03 instruction evidence IDs must be exactly "
            + ", ".join(expected_ids)
            + (f"; missing: {', '.join(missing)}" if missing else "")
            + (f"; unknown: {', '.join(unknown)}" if unknown else "")
        )
    return normalized


def validate_t14_evidence_checks(value: Any) -> list[dict[str, Any]]:
    """Validate the stable public checks for the context-budget lesson."""

    if not isinstance(value, list) or len(value) != len(CONTEXT_BUDGET_CHECK_IDS):
        raise EvidenceError("T14 evidence checks must contain the complete fixed check list")
    actual_ids: list[str] = []
    normalized: list[dict[str, str]] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T14 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T14 evidence check {index}")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T14 evidence check {index} needs an id")
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T14 evidence check {check_id}.result is not supported")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})
    if actual_ids != list(CONTEXT_BUDGET_CHECK_IDS):
        raise EvidenceError(
            "T14 evidence IDs must be exactly " + ", ".join(CONTEXT_BUDGET_CHECK_IDS)
        )
    return normalized


def validate_hooks_tasks_checks(value: Any) -> list[dict[str, str]]:
    """Validate the fixed public check list for T21."""

    if not isinstance(value, list) or len(value) != len(HOOKS_TASKS_CHECK_IDS):
        raise EvidenceError("T21 evidence checks must contain the complete fixed check list")
    normalized: list[dict[str, str]] = []
    actual_ids: list[str] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T21 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T21 evidence check {index}")
        if set(check) != {"id", "result"}:
            raise EvidenceError(f"T21 evidence check {index} must contain only id and result")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T21 evidence check {index} needs an id")
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T21 evidence check {check_id}.result is not supported")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})
    if actual_ids != list(HOOKS_TASKS_CHECK_IDS):
        raise EvidenceError("T21 evidence IDs must be exactly " + ", ".join(HOOKS_TASKS_CHECK_IDS))
    return normalized


def validate_t03_experiment(
    experiment: Any,
    *,
    checks: list[dict[str, Any]],
    document_result: str,
) -> dict[str, Any]:
    """Validate only stable experiment enums; discard prompts and raw findings."""

    if not isinstance(experiment, dict):
        raise EvidenceError("T03 completed evidence must include an experiment object")
    unexpected = sorted(
        set(experiment)
        - {
            "version",
            "baseline_id",
            "completed_scenarios",
            "migration_variants",
            "migration_contracts",
            "latest",
        }
    )
    if unexpected:
        raise EvidenceError(
            "T03 experiment contains unsupported fields: " + ", ".join(unexpected)
        )
    if experiment.get("version") != T03_INSTRUCTION_VERSION:
        raise EvidenceError("Unsupported T03 instruction experiment version")
    if experiment.get("baseline_id") != T03_BASELINE_ID:
        raise EvidenceError("T03 instruction evidence has an unknown baseline")

    completed = experiment.get("completed_scenarios")
    if not isinstance(completed, list) or any(
        not isinstance(item, str) or item not in T03_SCENARIOS for item in completed
    ):
        raise EvidenceError("T03 completed_scenarios must contain known scenario IDs")
    if len(completed) != len(set(completed)):
        raise EvidenceError("T03 completed_scenarios must not repeat IDs")
    expected_prefix = list(T03_SCENARIO_ORDER[: len(completed)])
    if completed != expected_prefix:
        raise EvidenceError(
            "T03 completed_scenarios must follow fixed order: "
            + " -> ".join(T03_SCENARIO_ORDER)
        )

    migration = experiment.get("migration_variants")
    if not isinstance(migration, list) or any(
        not isinstance(item, str) or item not in T03_VARIANTS for item in migration
    ):
        raise EvidenceError("T03 migration_variants must contain known input IDs")
    if len(migration) != len(set(migration)):
        raise EvidenceError("T03 migration_variants must not repeat IDs")
    migration_contracts = experiment.get("migration_contracts")
    if not isinstance(migration_contracts, list):
        raise EvidenceError("T03 migration_contracts must be a list")
    normalized_contracts: list[dict[str, str]] = []
    for index, value in enumerate(migration_contracts):
        if not isinstance(value, dict):
            raise EvidenceError(f"T03 migration_contracts[{index}] must be an object")
        unexpected_contract = sorted(set(value) - {"id", "subject", "unit", "limit"})
        if unexpected_contract:
            raise EvidenceError(
                "T03 migration contract contains unsupported fields: "
                + ", ".join(unexpected_contract)
            )
        if set(value) != {"id", "subject", "unit", "limit"}:
            raise EvidenceError("T03 migration contract must include id, subject, unit and limit")
        if any(not isinstance(value[field], str) or not value[field].strip() for field in value):
            raise EvidenceError("T03 migration contract fields must be non-empty strings")
        variant_id = value["id"]
        if variant_id not in T03_VARIANTS:
            raise EvidenceError("T03 migration contract has an unknown input ID")
        expected_contract = T03_VARIANT_CONTRACTS[variant_id]
        actual_contract = {
            "subject": value["subject"],
            "unit": value["unit"],
            "limit": value["limit"],
        }
        if actual_contract != expected_contract:
            raise EvidenceError(f"T03 migration contract does not match variant {variant_id}")
        normalized_contracts.append(
            {"id": variant_id, **expected_contract}
        )
    if [contract["id"] for contract in normalized_contracts] != migration:
        raise EvidenceError("T03 migration_contracts must match migration_variants in order")
    if migration and completed != list(T03_SCENARIO_ORDER):
        raise EvidenceError("T03 migration evidence requires all scenarios in fixed order")

    check_by_id = {check["id"]: check["result"] for check in checks}
    if check_by_id["baseline-compared"] in {"passed", "alternative"} and "baseline" not in completed:
        raise EvidenceError("T03 baseline evidence is passed without a baseline run")
    if check_by_id["conflict-contained"] in {"passed", "alternative"} and "conflict" not in completed:
        raise EvidenceError("T03 conflict evidence is passed without a conflict run")
    if check_by_id["injection-contained"] in {"passed", "alternative"} and "injection" not in completed:
        raise EvidenceError("T03 injection evidence is passed without an injection run")
    if check_by_id["long-instruction-diagnosed"] in {"passed", "alternative"} and "long" not in completed:
        raise EvidenceError("T03 long-instruction evidence is passed without a long run")
    if check_by_id["migration-completed"] in {"passed", "alternative"} and "pressure-night" not in migration:
        raise EvidenceError("T03 migration evidence is passed without the changed input")
    if (
        check_by_id["migration-completed"] in {"passed", "alternative"}
        and not any(contract["id"] == "pressure-night" for contract in normalized_contracts)
    ):
        raise EvidenceError("T03 migration evidence is passed without the pressure-night contract")

    if document_result in {"passed", "alternative"}:
        missing_scenarios = sorted(T03_SCENARIOS - set(completed))
        if missing_scenarios:
            raise EvidenceError(
                "Completed T03 evidence is missing scenarios: " + ", ".join(missing_scenarios)
            )
        if "pressure-night" not in migration:
            raise EvidenceError("Completed T03 evidence is missing the pressure-night migration")
        if experiment.get("latest") is None:
            raise EvidenceError("Completed T03 evidence is missing its latest comparison")

    latest = experiment.get("latest")
    normalized_latest: dict[str, str] | None = None
    if latest is not None:
        if not isinstance(latest, dict):
            raise EvidenceError("T03 latest comparison must be an object or null")
        unexpected_latest = sorted(
            set(latest)
            - {
                "scenario_id",
                "variant_id",
                "variant_subject",
                "variant_unit",
                "variant_limit",
                "ambiguous_outcome",
                "engineered_outcome",
            }
        )
        if unexpected_latest:
            raise EvidenceError(
                "T03 latest comparison contains unsupported fields: "
                + ", ".join(unexpected_latest)
            )
        scenario_id = latest.get("scenario_id")
        variant_id = latest.get("variant_id")
        variant_subject = latest.get("variant_subject")
        variant_unit = latest.get("variant_unit")
        variant_limit = latest.get("variant_limit")
        ambiguous_outcome = latest.get("ambiguous_outcome")
        engineered_outcome = latest.get("engineered_outcome")
        if (
            not isinstance(scenario_id, str)
            or not isinstance(variant_id, str)
            or scenario_id not in T03_SCENARIOS
            or variant_id not in T03_VARIANTS
        ):
            raise EvidenceError("T03 latest comparison has an unknown scenario or input")
        expected_contract = T03_VARIANT_CONTRACTS[variant_id]
        if {
            "subject": variant_subject,
            "unit": variant_unit,
            "limit": variant_limit,
        } != expected_contract:
            raise EvidenceError("T03 latest comparison does not match its variant contract")
        if ambiguous_outcome not in T03_AMBIGUOUS_OUTCOMES:
            raise EvidenceError("T03 latest comparison has an unknown ambiguous outcome")
        if engineered_outcome not in T03_ENGINEERED_OUTCOMES:
            raise EvidenceError("T03 latest comparison has an unknown engineered outcome")
        normalized_latest = {
            "scenario_id": scenario_id,
            "variant_id": variant_id,
            "variant_subject": variant_subject,
            "variant_unit": variant_unit,
            "variant_limit": variant_limit,
            "ambiguous_outcome": ambiguous_outcome,
            "engineered_outcome": engineered_outcome,
        }

    return {
        "version": T03_INSTRUCTION_VERSION,
        "baseline_id": T03_BASELINE_ID,
        "completed_scenarios": completed,
        "migration_variants": migration,
        "migration_contracts": normalized_contracts,
        "latest": normalized_latest,
    }


def validate_t14_simulation(
    value: Any,
    *,
    document_result: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate a status-only simulation and derive its public checks.

    Raw input values are intentionally not part of this contract.  A learner
    can prove that the three risk classes and a boundary were observed without
    exporting their local prompts, paths, files, or experiment data.
    """

    if not isinstance(value, dict):
        raise EvidenceError("T14 evidence requires a simulation object")
    _reject_sensitive_unknown_fields(value, "T14 simulation")
    if value.get("version") != CONTEXT_BUDGET_SIMULATION_VERSION:
        raise EvidenceError("Unsupported T14 simulation version")
    runs = value.get("runs")
    if not isinstance(runs, list):
        raise EvidenceError("T14 simulation runs must be a list")

    seen_ids: set[str] = set()
    observed: set[str] = set()
    normalized_runs: list[dict[str, Any]] = []
    for index, raw_run in enumerate(runs):
        if not isinstance(raw_run, dict):
            raise EvidenceError(f"T14 simulation run {index} must be an object")
        _reject_sensitive_unknown_fields(raw_run, f"T14 simulation run {index}")
        required = {"id", "finding", "findings", "boundary"}
        missing = sorted(required - set(raw_run))
        if missing:
            raise EvidenceError(
                f"T14 simulation run {index} is missing: " + ", ".join(missing)
            )
        run_id = raw_run["id"]
        _require_identifier(run_id, f"T14 simulation run {index}.id")
        if run_id in seen_ids:
            raise EvidenceError(f"T14 simulation run id repeated: {run_id}")
        seen_ids.add(run_id)
        finding = raw_run["finding"]
        if finding not in CONTEXT_BUDGET_FINDINGS:
            raise EvidenceError(f"T14 simulation run {run_id}.finding is not supported")
        findings = raw_run["findings"]
        if not isinstance(findings, list) or any(item not in CONTEXT_BUDGET_FINDINGS for item in findings):
            raise EvidenceError(f"T14 simulation run {run_id}.findings is invalid")
        if len(findings) != len(set(findings)):
            raise EvidenceError(f"T14 simulation run {run_id}.findings repeat an id")
        if finding != "ready" and finding not in findings:
            raise EvidenceError(f"T14 simulation run {run_id}.finding is absent from findings")
        boundary = raw_run["boundary"]
        if not isinstance(boundary, bool):
            raise EvidenceError(f"T14 simulation run {run_id}.boundary must be boolean")
        observed.update(findings)
        normalized_runs.append(
            {
                "id": run_id,
                "finding": finding,
                "findings": list(findings),
                "boundary": boundary,
            }
        )

    supplied_observed = value.get("observed")
    if not isinstance(supplied_observed, list) or any(item not in CONTEXT_BUDGET_FINDINGS for item in supplied_observed):
        raise EvidenceError("T14 simulation observed must list supported finding IDs")
    if len(supplied_observed) != len(set(supplied_observed)):
        raise EvidenceError("T14 simulation observed must not repeat a finding")
    if set(supplied_observed) != observed:
        raise EvidenceError("T14 simulation observed does not match its runs")

    expected_checks = [
        {
            "id": "working-set-selected",
            "result": "passed" if normalized_runs else "failed",
        },
        {
            "id": "risk-signals-observed",
            "result": "passed"
            if CONTEXT_BUDGET_REQUIRED_FINDINGS <= observed
            else "failed",
        },
        {
            "id": "boundary-tested",
            "result": "passed"
            if any(run["boundary"] for run in normalized_runs)
            else "failed",
        },
        {
            "id": "offline-deterministic",
            "result": "passed" if normalized_runs else "failed",
        },
    ]
    if document_result in {"passed", "alternative"} and any(
        check["result"] != "passed" for check in expected_checks
    ):
        raise EvidenceError("Completed T14 evidence is missing a required simulation observation")
    return expected_checks, {
        "version": CONTEXT_BUDGET_SIMULATION_VERSION,
        "runs": normalized_runs,
        "observed": sorted(observed),
    }

def validate_t15_evidence_checks(value: Any) -> list[dict[str, Any]]:
    """Validate the stable public checks for context compression/recovery."""

    if not isinstance(value, list) or not value:
        raise EvidenceError("T15 context recovery evidence checks must be a non-empty list")
    seen: set[str] = set()
    actual_ids: list[str] = []
    normalized: list[dict[str, Any]] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T15 context recovery check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T15 context recovery check {index}")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T15 context recovery check {index} needs an id")
        if check_id in seen:
            raise EvidenceError(f"T15 context recovery check ID repeated: {check_id}")
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(
                f"T15 context recovery check {check_id}.result is not supported"
            )
        seen.add(check_id)
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})

    expected_ids = list(T15_CONTEXT_RECOVERY_CHECK_IDS)
    if actual_ids != expected_ids:
        missing = [check_id for check_id in expected_ids if check_id not in seen]
        unknown = [check_id for check_id in actual_ids if check_id not in expected_ids]
        raise EvidenceError(
            "T15 context recovery evidence IDs must be exactly "
            + ", ".join(expected_ids)
            + (f"; missing: {', '.join(missing)}" if missing else "")
            + (f"; unknown: {', '.join(unknown)}" if unknown else "")
        )
    return normalized


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise EvidenceError(f"{label} must be a boolean")
    return value


def _require_string_array(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise EvidenceError(f"{label} must be a non-empty list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise EvidenceError(f"{label} must contain only non-empty strings")
    return list(value)


def validate_t15_experiment(
    experiment: Any,
    *,
    checks: list[dict[str, Any]],
    document_result: str,
) -> dict[str, Any]:
    """Validate and minimize the T15 compression/recovery experiment.

    The fixture can contain explanatory details in the browser, but only the
    enumerated outcomes and handoff fields cross the public seam.  Check
    states are derived from the recorded modes and recovery state, so a hand
    written list of ``passed`` values cannot forge completion.
    """

    if not isinstance(experiment, dict):
        raise EvidenceError("T15 completed evidence must include an experiment object")
    _reject_sensitive_unknown_fields(experiment, "T15 context recovery experiment")
    allowed_fields = {
        "version",
        "baseline_id",
        "compression_modes",
        "comparisons",
        "pollution",
        "handoff",
        "layers",
    }
    unexpected = sorted(set(experiment) - allowed_fields)
    if unexpected:
        raise EvidenceError(
            "T15 context recovery experiment contains unsupported fields: "
            + ", ".join(unexpected)
        )
    if experiment.get("version") != T15_CONTEXT_RECOVERY_VERSION:
        raise EvidenceError("Unsupported T15 context recovery experiment version")
    if experiment.get("baseline_id") != T15_CONTEXT_RECOVERY_BASELINE_ID:
        raise EvidenceError("T15 context recovery evidence has an unknown baseline")

    modes = _require_string_array(experiment.get("compression_modes"), "T15 compression_modes", allow_empty=True)
    if len(modes) != len(set(modes)) or any(mode not in T15_CONTEXT_RECOVERY_MODES for mode in modes):
        raise EvidenceError("T15 compression_modes must contain unique known modes")

    comparisons = experiment.get("comparisons")
    if not isinstance(comparisons, list):
        raise EvidenceError("T15 comparisons must be a list")
    if len(comparisons) != len(modes):
        raise EvidenceError("T15 comparisons must match compression_modes")
    normalized_comparisons: list[dict[str, Any]] = []
    comparison_modes: list[str] = []
    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, dict):
            raise EvidenceError(f"T15 comparison {index} must be an object")
        _reject_sensitive_unknown_fields(comparison, f"T15 comparison {index}")
        required = {
            "mode",
            "before_outcome",
            "after_outcome",
            "distortion_detected",
            "constraint_omission_detected",
        }
        if set(comparison) != required:
            missing = sorted(required - set(comparison))
            unknown = sorted(set(comparison) - required)
            detail = []
            if missing:
                detail.append("missing: " + ", ".join(missing))
            if unknown:
                detail.append("unknown: " + ", ".join(unknown))
            raise EvidenceError(
                f"T15 comparison {index} fields are incomplete or unexpected ("
                + "; ".join(detail)
                + ")"
            )
        mode = comparison["mode"]
        if mode not in T15_CONTEXT_RECOVERY_MODES or mode in comparison_modes:
            raise EvidenceError("T15 comparison modes must be unique known modes")
        if mode not in modes or comparison["before_outcome"] != "report-ready":
            raise EvidenceError(f"T15 comparison {mode} does not match the fixed baseline")
        expected_after = T15_CONTEXT_RECOVERY_AFTER_OUTCOMES[mode]
        if comparison["after_outcome"] != expected_after:
            raise EvidenceError(f"T15 comparison {mode} has an unexpected after outcome")
        distortion_detected = _require_bool(
            comparison["distortion_detected"], f"T15 comparison {mode}.distortion_detected"
        )
        omission_detected = _require_bool(
            comparison["constraint_omission_detected"],
            f"T15 comparison {mode}.constraint_omission_detected",
        )
        if distortion_detected != (mode == "distorted"):
            raise EvidenceError("T15 distortion diagnostic does not match its mode")
        if omission_detected != (mode == "constraint-omitted"):
            raise EvidenceError("T15 omission diagnostic does not match its mode")
        comparison_modes.append(mode)
        normalized_comparisons.append(
            {
                "mode": mode,
                "before_outcome": "report-ready",
                "after_outcome": expected_after,
                "distortion_detected": distortion_detected,
                "constraint_omission_detected": omission_detected,
            }
        )
    if comparison_modes != modes:
        raise EvidenceError("T15 comparisons must follow compression_modes order")

    pollution = experiment.get("pollution")
    if not isinstance(pollution, dict):
        raise EvidenceError("T15 pollution must be an object")
    _reject_sensitive_unknown_fields(pollution, "T15 pollution")
    pollution_fields = {"injected", "observed", "recovered", "outcome"}
    if set(pollution) != pollution_fields:
        raise EvidenceError("T15 pollution fields must be injected, observed, recovered and outcome")
    injected = _require_bool(pollution["injected"], "T15 pollution.injected")
    observed = _require_bool(pollution["observed"], "T15 pollution.observed")
    recovered = _require_bool(pollution["recovered"], "T15 pollution.recovered")
    outcome = pollution["outcome"]
    if outcome not in {"not-run", "polluted", "recovered"}:
        raise EvidenceError("T15 pollution outcome is not supported")
    if outcome == "not-run" and (injected or observed or recovered):
        raise EvidenceError("T15 not-run pollution cannot have recovery flags")
    if outcome == "polluted" and (not injected or not observed or recovered):
        raise EvidenceError("T15 polluted outcome must be observed and unrecovered")
    if outcome == "recovered" and (not injected or not observed or not recovered):
        raise EvidenceError("T15 recovered outcome must include injection and observation")

    handoff = experiment.get("handoff")
    if not isinstance(handoff, dict):
        raise EvidenceError("T15 handoff must be an object")
    _reject_sensitive_unknown_fields(handoff, "T15 handoff")
    handoff_fields = {"goal", "status", "evidence", "risks", "next_steps"}
    if set(handoff) != handoff_fields:
        raise EvidenceError("T15 handoff must contain goal, status, evidence, risks and next_steps")
    goal = handoff["goal"]
    status = handoff["status"]
    if goal != "report-task":
        raise EvidenceError("T15 handoff goal does not match the fixed task")
    if status not in {"blocked", "ready-for-next-session"}:
        raise EvidenceError("T15 handoff status is not supported")
    handoff_evidence = _require_string_array(handoff["evidence"], "T15 handoff.evidence", allow_empty=True)
    handoff_risks = _require_string_array(handoff["risks"], "T15 handoff.risks")
    handoff_next_steps = _require_string_array(handoff["next_steps"], "T15 handoff.next_steps")
    if any(len(item) > 120 for item in handoff_evidence + handoff_risks + handoff_next_steps):
        raise EvidenceError("T15 handoff fields must contain short stable notes")
    if not set(handoff_risks).issubset(T15_CONTEXT_RECOVERY_RISKS):
        raise EvidenceError("T15 handoff.risks contains an unknown risk")
    if status == "ready-for-next-session":
        required_handoff_evidence = {
            "compression-before-after",
            "compression-distortion-diagnosed",
            "constraint-omission-diagnosed",
            "pollution-recovered",
        }
        if not required_handoff_evidence.issubset(set(handoff_evidence)):
            raise EvidenceError("T15 ready handoff is missing recovery evidence")
        if not recovered:
            raise EvidenceError("T15 ready handoff requires recovered pollution")

    layers = experiment.get("layers")
    if not isinstance(layers, dict) or set(layers) != set(T15_CONTEXT_RECOVERY_LAYER_VALUES):
        raise EvidenceError("T15 layers must distinguish context, history and memory")
    normalized_layers: dict[str, str] = {}
    for layer, expected in T15_CONTEXT_RECOVERY_LAYER_VALUES.items():
        if layers[layer] != expected:
            raise EvidenceError(f"T15 layer {layer} does not match its boundary")
        normalized_layers[layer] = expected

    check_results = {check["id"]: check["result"] for check in checks}
    expected_checks = {
        "compression-compared": "passed" if modes else "failed",
        "distortion-detected": "passed" if "distorted" in modes else "failed",
        "constraint-omission-detected": "passed" if "constraint-omitted" in modes else "failed",
        "pollution-recovered": "passed" if recovered else "failed",
        "handoff-complete": "passed" if status == "ready-for-next-session" else "failed",
        "layers-distinguished": "passed",
    }
    for check_id, expected in expected_checks.items():
        if check_results[check_id] != expected:
            raise EvidenceError(f"T15 evidence check {check_id} does not match the experiment")

    complete = set(modes) == set(T15_CONTEXT_RECOVERY_MODES) and recovered and status == "ready-for-next-session"
    if document_result in {"passed", "alternative"} and not complete:
        raise EvidenceError("Completed T15 evidence is missing a compression mode, recovery, or handoff")
    if document_result == "passed" and any(result != "passed" for result in check_results.values()):
        raise EvidenceError("Passed T15 evidence cannot contain failed or alternative checks")

    return {
        "version": T15_CONTEXT_RECOVERY_VERSION,
        "baseline_id": T15_CONTEXT_RECOVERY_BASELINE_ID,
        "compression_modes": modes,
        "comparisons": normalized_comparisons,
        "pollution": {
            "injected": injected,
            "observed": observed,
            "recovered": recovered,
            "outcome": outcome,
        },
        "handoff": {
            "goal": goal,
            "status": status,
            "evidence": handoff_evidence,
            "risks": handoff_risks,
            "next_steps": handoff_next_steps,
        },
        "layers": normalized_layers,
    }


def validate_t16_evidence_checks(value: Any) -> list[dict[str, str]]:
    """Validate the fixed learner-facing checks for controlled Memory."""

    if not isinstance(value, list) or len(value) != len(MEMORY_CHECK_IDS):
        raise EvidenceError("T16 evidence checks must contain the complete fixed check list")
    actual_ids: list[str] = []
    normalized: list[dict[str, str]] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T16 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T16 evidence check {index}")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T16 evidence check {index} needs an id")
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T16 evidence check {check_id}.result is not supported")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})
    if actual_ids != list(MEMORY_CHECK_IDS):
        raise EvidenceError(
            "T16 evidence IDs must be exactly " + ", ".join(MEMORY_CHECK_IDS)
        )
    return normalized


def validate_t26_evidence_checks(value: Any) -> list[dict[str, Any]]:
    """Validate the fixed public check list for the offline Python loop."""

    if not isinstance(value, list) or not value:
        raise EvidenceError("T26 offline Agent loop evidence checks must be a non-empty list")
    actual_ids: list[str] = []
    normalized: list[dict[str, Any]] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T26 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T26 evidence check {index}")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T26 evidence check {index} needs an id")
        if check_id in actual_ids:
            raise EvidenceError(f"T26 evidence check ID repeated: {check_id}")
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T26 evidence check {check_id}.result is not supported")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})
    expected_ids = list(T26_OFFLINE_AGENT_LOOP_CHECK_IDS)
    if actual_ids != expected_ids:
        missing = [check_id for check_id in expected_ids if check_id not in actual_ids]
        unknown = [check_id for check_id in actual_ids if check_id not in expected_ids]
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unknown:
            detail.append("unknown: " + ", ".join(unknown))
        raise EvidenceError(
            "T26 evidence IDs must be exactly "
            + ", ".join(expected_ids)
            + ("; " + "; ".join(detail) if detail else "")
        )
    return normalized


def validate_t16_experiment(
    value: Any,
    *,
    document_result: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate and reduce the status-only controlled Memory experiment.

    The browser fixture may contain local explanatory text while it runs, but
    the public contract accepts only stage IDs, booleans, and fixed enums. The
    check results are derived from stage observations rather than trusted from
    a caller-supplied summary.
    """

    if not isinstance(value, dict):
        raise EvidenceError("T16 evidence requires an experiment object")
    _reject_sensitive_unknown_fields(value, "T16 experiment")
    expected_fields = {
        "version",
        "baseline_id",
        "stages",
        "memory_types",
        "context_modes",
        "pollution_injected",
        "pollution_recovered",
        "model_calls",
        "network_calls",
    }
    missing = sorted(expected_fields - set(value))
    unexpected = sorted(set(value) - expected_fields)
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unexpected:
            details.append("unknown: " + ", ".join(unexpected))
        raise EvidenceError(
            "T16 experiment fields are incomplete or unexpected ("
            + "; ".join(details)
            + ")"
        )
    if value["version"] != MEMORY_EXPERIMENT_VERSION:
        raise EvidenceError("Unsupported T16 Memory experiment version")
    if value["baseline_id"] != MEMORY_BASELINE_ID:
        raise EvidenceError("T16 Memory evidence has an unknown baseline")

    for field, expected in (
        ("memory_types", list(MEMORY_TYPES)),
        ("context_modes", list(MEMORY_CONTEXT_MODES)),
    ):
        actual = value[field]
        if actual != expected:
            raise EvidenceError(f"T16 experiment {field} must match the fixed contract")

    for field in ("pollution_injected", "pollution_recovered"):
        if not isinstance(value[field], bool):
            raise EvidenceError(f"T16 experiment {field} must be boolean")
    for field in ("model_calls", "network_calls"):
        count = value[field]
        if isinstance(count, bool) or not isinstance(count, int) or count != 0:
            raise EvidenceError(
                f"T16 experiment {field} must be the integer 0 for the offline lab"
            )

    stages = value["stages"]
    if not isinstance(stages, list) or len(stages) > len(MEMORY_STAGE_IDS):
        raise EvidenceError("T16 experiment stages must be an ordered prefix of the fixed journey")
    normalized_stages: list[dict[str, Any]] = []
    stage_results: dict[str, bool] = {}
    for sequence, (expected_id, raw_stage) in enumerate(
        zip(MEMORY_STAGE_IDS, stages), start=1
    ):
        if not isinstance(raw_stage, dict):
            raise EvidenceError(f"T16 stage {expected_id} must be an object")
        _reject_sensitive_unknown_fields(raw_stage, f"T16 stage {expected_id}")
        expected_stage_fields = {"id", "sequence", "result", "observations"}
        if set(raw_stage) != expected_stage_fields:
            raise EvidenceError(
                f"T16 stage {expected_id} must contain only id, sequence, result and observations"
            )
        if raw_stage["id"] != expected_id or raw_stage["sequence"] != sequence:
            raise EvidenceError("T16 Memory stages are out of order")
        result = raw_stage["result"]
        if result not in {"passed", "failed"}:
            raise EvidenceError(f"T16 stage {expected_id}.result is not supported")
        observations = raw_stage["observations"]
        if not isinstance(observations, dict):
            raise EvidenceError(f"T16 stage {expected_id}.observations must be an object")
        expected_observations = MEMORY_STAGE_OBSERVATIONS[expected_id]
        if set(observations) != expected_observations:
            missing_observations = sorted(expected_observations - set(observations))
            unknown_observations = sorted(set(observations) - expected_observations)
            details = []
            if missing_observations:
                details.append("missing: " + ", ".join(missing_observations))
            if unknown_observations:
                details.append("unknown: " + ", ".join(unknown_observations))
            raise EvidenceError(
                f"T16 stage {expected_id}.observations are incomplete or unexpected ("
                + "; ".join(details)
                + ")"
            )
        if any(not isinstance(item, bool) for item in observations.values()):
            raise EvidenceError(f"T16 stage {expected_id}.observations must be booleans")
        computed_result = "passed" if all(observations.values()) else "failed"
        if result != computed_result:
            raise EvidenceError(f"T16 stage {expected_id}.result does not match observations")
        stage_results[expected_id] = result == "passed"
        normalized_stages.append(
            {
                "id": expected_id,
                "sequence": sequence,
                "result": result,
                "observations": {key: observations[key] for key in sorted(observations)},
            }
        )

    if any(stage["id"] == "pollution" for stage in normalized_stages) and not value[
        "pollution_injected"
    ]:
        raise EvidenceError("T16 pollution stage requires pollution_injected")
    pollution_recovered = bool(
        value["pollution_recovered"] and stage_results.get("pollution", False)
    )

    def passed(stage_id: str, *keys: str) -> bool:
        stage = next((item for item in normalized_stages if item["id"] == stage_id), None)
        return bool(stage and all(stage["observations"][key] for key in keys))

    expected_checks = [
        {"id": "purpose-defined", "result": "passed" if passed("design", "purpose") else "failed"},
        {"id": "owner-defined", "result": "passed" if passed("design", "owner") else "failed"},
        {"id": "lifetime-defined", "result": "passed" if passed("design", "lifetime") else "failed"},
        {"id": "deletion-defined", "result": "passed" if passed("design", "deletion") else "failed"},
        {"id": "memory-types-separated", "result": "passed" if passed("design", "types") else "failed"},
        {"id": "context-window-managed", "result": "passed" if passed("recall", "context_window") else "failed"},
        {
            "id": "summary-retrieval-injection",
            "result": "passed" if passed("recall", "summary", "retrieval", "injection") else "failed",
        },
        {"id": "correct-recall", "result": "passed" if passed("recall", "correct_recall") else "failed"},
        {
            "id": "stale-memory-corrected",
            "result": "passed"
            if passed("stale-update", "stale_detected", "replacement_confirmed", "old_not_retrieved")
            else "failed",
        },
        {
            "id": "pollution-contained",
            "result": "passed"
            if pollution_recovered
            and passed("pollution", "untrusted_quarantined", "trusted_boundary_restored", "revalidated")
            else "failed",
        },
        {"id": "sensitive-excluded", "result": "passed" if passed("write", "sensitive_excluded") else "failed"},
        {
            "id": "deletion-confirmed",
            "result": "passed"
            if passed("delete", "deletion_requested", "deletion_confirmed", "record_absent")
            else "failed",
        },
        {"id": "offline-deterministic", "result": "passed"},
    ]
    if document_result in {"passed", "alternative"}:
        if len(normalized_stages) != len(MEMORY_STAGE_IDS) or any(
            check["result"] != "passed" for check in expected_checks
        ):
            raise EvidenceError("Completed T16 evidence is missing a required Memory observation")
    return expected_checks, {
        "version": MEMORY_EXPERIMENT_VERSION,
        "baseline_id": MEMORY_BASELINE_ID,
        "memory_types": list(MEMORY_TYPES),
        "context_modes": list(MEMORY_CONTEXT_MODES),
        "pollution_injected": value["pollution_injected"],
        "pollution_recovered": pollution_recovered,
        "model_calls": 0,
        "network_calls": 0,
    }


def validate_t18_evidence_checks(value: Any) -> list[dict[str, Any]]:
    """Validate the fixed public checks for the Plugin audit lesson."""

    if not isinstance(value, list) or len(value) != len(PLUGIN_AUDIT_CHECK_IDS):
        raise EvidenceError("T18 Plugin audit evidence checks must contain the complete fixed check list")
    actual_ids: list[str] = []
    normalized: list[dict[str, str]] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T18 Plugin audit evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T18 Plugin audit evidence check {index}")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T18 Plugin audit evidence check {index} needs an id")
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T18 Plugin audit evidence check {check_id}.result is not supported")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})
    if actual_ids != list(PLUGIN_AUDIT_CHECK_IDS):
        raise EvidenceError(
            "T18 Plugin audit evidence IDs must be exactly "
            + ", ".join(PLUGIN_AUDIT_CHECK_IDS)
        )
    return normalized


def _expected_t18_profile(profile: str) -> tuple[str, set[str], set[str]]:
    """Return the inert fixture's status, component types and findings."""

    if profile == "reviewable":
        return "reviewable", set(PLUGIN_COMPONENT_TYPES), set()
    if profile == "community-shape":
        return (
            "needs-review",
            {"skill", "command"},
            {"license-unknown", "provenance-unpinned", "dependency-unpinned"},
        )
    if profile == "needs-review":
        return (
            "do-not-install",
            set(PLUGIN_COMPONENT_TYPES),
            {
                "license-unknown",
                "provenance-unpinned",
                "permission-broad",
                "network-enabled",
                "dependency-unpinned",
                "install-script",
                "lifecycle-gap",
            },
        )
    raise EvidenceError(f"T18 Plugin audit profile is unsupported: {profile}")


def validate_t18_audit(
    value: Any,
    *,
    document_result: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate status-only Plugin audit runs and derive public checks."""

    if not isinstance(value, dict):
        raise EvidenceError("T18 completed evidence must include an audit object")
    _reject_sensitive_unknown_fields(value, "T18 audit")
    required = {
        "version",
        "runs",
        "observed_findings",
        "observed_components",
        "observed_fields",
        "observed_lifecycle",
    }
    missing = sorted(required - set(value))
    if missing:
        raise EvidenceError("T18 audit is missing: " + ", ".join(missing))
    unexpected = sorted(set(value) - required)
    if unexpected:
        raise EvidenceError("T18 audit has unexpected fields: " + ", ".join(unexpected))
    if value["version"] != PLUGIN_AUDIT_VERSION:
        raise EvidenceError("Unsupported T18 Plugin audit version")

    runs = value["runs"]
    if not isinstance(runs, list) or not runs:
        raise EvidenceError("T18 audit runs must be a non-empty list")
    seen_ids: set[str] = set()
    normalized_runs: list[dict[str, Any]] = []
    observed_findings: set[str] = set()
    observed_components: set[str] = set()
    observed_fields: set[str] = set()
    observed_lifecycle: set[str] = set()
    expected_run_fields = {
        "id",
        "fixture",
        "status",
        "findings",
        "components",
        "inspected",
        "lifecycle",
        "offline",
        "executed",
    }

    for index, raw_run in enumerate(runs):
        if not isinstance(raw_run, dict):
            raise EvidenceError(f"T18 audit run {index} must be an object")
        _reject_sensitive_unknown_fields(raw_run, f"T18 audit run {index}")
        missing = sorted(expected_run_fields - set(raw_run))
        if missing:
            raise EvidenceError(f"T18 audit run {index} is missing: " + ", ".join(missing))
        unexpected = sorted(set(raw_run) - expected_run_fields)
        if unexpected:
            raise EvidenceError(
                f"T18 audit run {index} has unexpected fields: " + ", ".join(unexpected)
            )

        run_id = raw_run["id"]
        _require_identifier(run_id, f"T18 audit run {index}.id")
        if run_id in seen_ids:
            raise EvidenceError(f"T18 audit run id repeated: {run_id}")
        seen_ids.add(run_id)

        profile = raw_run["fixture"]
        if profile not in PLUGIN_AUDIT_PROFILES:
            raise EvidenceError(f"T18 audit run {run_id}.fixture is unsupported")
        expected_status, expected_components, expected_findings = _expected_t18_profile(profile)
        status = raw_run["status"]
        if status not in PLUGIN_AUDIT_STATUSES or status != expected_status:
            raise EvidenceError(f"T18 audit run {run_id}.status does not match its fixture profile")

        findings = raw_run["findings"]
        if not isinstance(findings, list) or any(item not in PLUGIN_AUDIT_FINDINGS for item in findings):
            raise EvidenceError(f"T18 audit run {run_id}.findings is invalid")
        if len(findings) != len(set(findings)) or set(findings) != expected_findings:
            raise EvidenceError(f"T18 audit run {run_id}.findings does not match its fixture profile")

        components = raw_run["components"]
        if not isinstance(components, list) or any(item not in PLUGIN_COMPONENT_TYPES for item in components):
            raise EvidenceError(f"T18 audit run {run_id}.components is invalid")
        if len(components) != len(set(components)) or set(components) != expected_components:
            raise EvidenceError(f"T18 audit run {run_id}.components does not match its fixture profile")

        inspected = raw_run["inspected"]
        if not isinstance(inspected, list) or any(item not in PLUGIN_AUDIT_FIELDS for item in inspected):
            raise EvidenceError(f"T18 audit run {run_id}.inspected is invalid")
        if set(inspected) != set(PLUGIN_AUDIT_FIELDS) or len(inspected) != len(set(inspected)):
            raise EvidenceError(f"T18 audit run {run_id}.inspected must cover all audit fields")

        lifecycle = raw_run["lifecycle"]
        if not isinstance(lifecycle, list) or any(item not in PLUGIN_LIFECYCLE_ACTIONS for item in lifecycle):
            raise EvidenceError(f"T18 audit run {run_id}.lifecycle is invalid")
        if set(lifecycle) != set(PLUGIN_LIFECYCLE_ACTIONS) or len(lifecycle) != len(set(lifecycle)):
            raise EvidenceError(f"T18 audit run {run_id}.lifecycle must cover all actions")

        if raw_run["offline"] is not True or raw_run["executed"] is not False:
            raise EvidenceError("T18 audit must remain offline and must not execute a package")

        observed_findings.update(findings)
        observed_components.update(components)
        observed_fields.update(inspected)
        observed_lifecycle.update(lifecycle)
        normalized_runs.append(
            {
                "id": run_id,
                "fixture": profile,
                "status": status,
                "findings": list(findings),
                "components": list(components),
                "inspected": list(inspected),
                "lifecycle": list(lifecycle),
                "offline": True,
                "executed": False,
            }
        )

    supplied_findings = value["observed_findings"]
    supplied_components = value["observed_components"]
    supplied_fields = value["observed_fields"]
    supplied_lifecycle = value["observed_lifecycle"]
    for label, supplied, allowed, observed in (
        ("findings", supplied_findings, PLUGIN_AUDIT_FINDINGS, observed_findings),
        ("components", supplied_components, set(PLUGIN_COMPONENT_TYPES), observed_components),
        ("fields", supplied_fields, set(PLUGIN_AUDIT_FIELDS), observed_fields),
        ("lifecycle", supplied_lifecycle, set(PLUGIN_LIFECYCLE_ACTIONS), observed_lifecycle),
    ):
        if not isinstance(supplied, list) or any(item not in allowed for item in supplied):
            raise EvidenceError(f"T18 audit observed_{label} is invalid")
        if len(supplied) != len(set(supplied)) or set(supplied) != observed:
            raise EvidenceError(f"T18 audit observed_{label} does not match its runs")

    derived_checks = [
        {"id": "manifest-reviewed", "result": "passed"},
        {
            "id": "component-composition-mapped",
            "result": "passed"
            if set(PLUGIN_COMPONENT_TYPES) <= observed_components
            else "failed",
        },
        {
            "id": "supply-chain-fields-audited",
            "result": "passed"
            if set(PLUGIN_AUDIT_FIELDS) <= observed_fields
            else "failed",
        },
        {
            "id": "unsafe-package-contained",
            "result": "passed"
            if any(
                run["status"] != "reviewable" and run["findings"] for run in normalized_runs
            )
            else "failed",
        },
        {
            "id": "lifecycle-reviewed",
            "result": "passed"
            if set(PLUGIN_LIFECYCLE_ACTIONS) <= observed_lifecycle
            else "failed",
        },
        {"id": "offline-no-install", "result": "passed"},
    ]
    if document_result in {"passed", "alternative"} and any(
        check["result"] != "passed" for check in derived_checks
    ):
        raise EvidenceError("Completed T18 evidence is missing a required audit observation")
    return derived_checks, {
        "version": PLUGIN_AUDIT_VERSION,
        "runs": normalized_runs,
        "observed_findings": sorted(observed_findings),
        "observed_components": sorted(observed_components),
        "observed_fields": sorted(observed_fields),
        "observed_lifecycle": sorted(observed_lifecycle),
    }

def _validate_t26_structured_output(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be an object")
    _reject_sensitive_unknown_fields(value, label)
    required = {"status", "summary", "reading", "anomaly", "attempts"}
    if set(value) != required:
        raise EvidenceError(f"{label} must contain exactly status, summary, reading, anomaly and attempts")
    if value["status"] not in {"completed", "failed"}:
        raise EvidenceError(f"{label}.status is not supported")
    if not isinstance(value["summary"], str) or not value["summary"].strip() or len(value["summary"]) > 240:
        raise EvidenceError(f"{label}.summary must be a short non-empty string")
    reading = value["reading"]
    if reading is not None and (
        isinstance(reading, bool) or not isinstance(reading, int) or not 0 <= reading <= 100
    ):
        raise EvidenceError(f"{label}.reading must be null or an integer from 0 to 100")
    if not isinstance(value["anomaly"], bool):
        raise EvidenceError(f"{label}.anomaly must be boolean")
    attempts = value["attempts"]
    if isinstance(attempts, bool) or not isinstance(attempts, int) or not 1 <= attempts <= 8:
        raise EvidenceError(f"{label}.attempts must be an integer from 1 to 8")
    if value["status"] == "completed" and reading is None:
        raise EvidenceError(f"{label} completed output needs a reading")
    if value["status"] == "failed" and reading is not None:
        raise EvidenceError(f"{label} failed output cannot claim a reading")
    return {
        "status": value["status"],
        "summary": value["summary"],
        "reading": reading,
        "anomaly": value["anomaly"],
        "attempts": attempts,
    }


def _t26_event_sequence(case: dict[str, Any], *, scenario: str) -> tuple[list[dict[str, Any]], list[str]]:
    events = case.get("events")
    if not isinstance(events, list) or not events:
        raise EvidenceError(f"T26 {scenario} case events must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise EvidenceError(f"T26 {scenario} event {index} must be an object")
        _reject_sensitive_unknown_fields(event, f"T26 {scenario} event {index}")
        required = {"id", "kind", "turn", "status", "result"}
        if set(event) != required:
            raise EvidenceError(f"T26 {scenario} event {index} fields are not public contract fields")
        event_id = event["id"]
        if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
            raise EvidenceError(f"T26 {scenario} event IDs must be unique non-empty strings")
        kind = event["kind"]
        if kind not in T26_OFFLINE_AGENT_LOOP_EVENT_KINDS:
            raise EvidenceError(f"T26 {scenario} event kind is unsupported: {kind}")
        turn = event["turn"]
        if isinstance(turn, bool) or not isinstance(turn, int) or not 1 <= turn <= 8:
            raise EvidenceError(f"T26 {scenario} event turn must be an integer from 1 to 8")
        status = event["status"]
        if status not in {"ok", "invalid-arguments", "error", "budget", "passed"}:
            raise EvidenceError(f"T26 {scenario} event status is unsupported: {status}")
        result = event["result"]
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T26 {scenario} event result is unsupported: {result}")
        seen_ids.add(event_id)
        normalized.append(
            {
                "id": event_id,
                "kind": kind,
                "turn": turn,
                "status": status,
                "result": result,
            }
        )
    return normalized, [event["kind"] for event in normalized]


def _t26_case_observed(case: dict[str, Any], scenario: str) -> bool:
    """Check one scenario's externally visible event grammar."""

    if case.get("scenario") != scenario or case.get("version") != T26_OFFLINE_AGENT_LOOP_VERSION:
        return False
    try:
        events, kinds = _t26_event_sequence(case, scenario=scenario)
    except EvidenceError:
        return False
    statuses = [event["status"] for event in events]
    if not {"response", "tool_call", "tool_execution", "state_refill", "stop"}.issubset(kinds):
        return False
    if kinds[-1] != "stop":
        return False
    output_valid = case.get("output_valid")
    if not isinstance(output_valid, bool):
        return False
    if scenario == "success":
        return (
            case.get("outcome") == "success"
            and case.get("stop_reason") == "completed"
            and output_valid
            and kinds[-3:] == ["response", "structured_output", "stop"]
        )
    if scenario == "tool-failure":
        return (
            case.get("outcome") == "failure"
            and case.get("stop_reason") == "tool_error"
            and output_valid
            and "error" in statuses
            and kinds[-3:] == ["response", "structured_output", "stop"]
        )
    if scenario == "invalid-args":
        return (
            case.get("outcome") == "invalid-args"
            and output_valid
            and "invalid-arguments" in statuses
            and kinds[-3:] == ["response", "structured_output", "stop"]
            and kinds.count("tool_call") >= 2
        )
    if scenario == "budget-stop":
        max_steps = case.get("max_steps")
        return (
            case.get("outcome") == "budget-stop"
            and case.get("stop_reason") == "max_steps"
            and output_valid is False
            and case.get("structured_output") is None
            and statuses[-1] == "budget"
            and "structured_output" not in kinds
            and kinds.count("response") == max_steps
        )
    if scenario == "retry-recovery":
        return (
            case.get("outcome") == "retry-recovery"
            and case.get("stop_reason") == "completed"
            and output_valid
            and int(case.get("retry_count", -1)) >= 1
            and "error" in statuses
            and kinds.count("tool_call") >= 2
            and kinds[-3:] == ["response", "structured_output", "stop"]
        )
    return False


def _derive_t26_checks(cases: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    success = cases.get("success", {})
    retry = cases.get("retry-recovery", {})
    state_refill = all(
        "state_refill"
        in [
            event.get("kind")
            for event in cases.get(scenario, {}).get("events", [])
            if isinstance(event, dict)
        ]
        for scenario in ("success", "tool-failure", "invalid-args", "retry-recovery")
    )
    all_cases = all(
        _t26_case_observed(cases.get(scenario, {}), scenario)
        for scenario in T26_OFFLINE_AGENT_LOOP_SCENARIOS
    )
    return [
        {"id": "deterministic-fixture", "result": "passed" if all_cases else "failed"},
        {"id": "response-tool-loop", "result": "passed" if _t26_case_observed(success, "success") else "failed"},
        {"id": "state-refill", "result": "passed" if state_refill else "failed"},
        {"id": "structured-output", "result": "passed" if _t26_case_observed(success, "success") and _t26_case_observed(retry, "retry-recovery") else "failed"},
        {"id": "tool-failure-stop", "result": "passed" if _t26_case_observed(cases.get("tool-failure", {}), "tool-failure") else "failed"},
        {"id": "invalid-arguments-recovery", "result": "passed" if _t26_case_observed(cases.get("invalid-args", {}), "invalid-args") else "failed"},
        {"id": "budget-stop", "result": "passed" if _t26_case_observed(cases.get("budget-stop", {}), "budget-stop") else "failed"},
        {"id": "retry-recovery", "result": "passed" if _t26_case_observed(retry, "retry-recovery") else "failed"},
        {"id": "framework-free", "result": "passed"},
    ]


def validate_t26_experiment(
    experiment: Any,
    *,
    checks: list[dict[str, Any]],
    document_result: str,
) -> dict[str, Any]:
    """Validate and minimize the T26 offline loop experiment.

    The runner may include synthetic output values for teaching, but this
    public seam only returns scenario names, event kinds, statuses and the
    structured-output status.  Prompt text, arguments, paths and raw payloads
    never cross the checker boundary.
    """

    if not isinstance(experiment, dict):
        raise EvidenceError("T26 completed evidence must include an experiment object")
    _reject_sensitive_unknown_fields(experiment, "T26 offline Agent loop experiment")
    allowed = {"version", "implementation", "framework", "scenarios", "cases"}
    unexpected = sorted(set(experiment) - allowed)
    if unexpected:
        raise EvidenceError("T26 experiment contains unsupported fields: " + ", ".join(unexpected))
    if experiment.get("version") != T26_OFFLINE_AGENT_LOOP_VERSION:
        raise EvidenceError("Unsupported T26 offline Agent loop experiment version")
    if experiment.get("implementation") != T26_OFFLINE_AGENT_LOOP_IMPLEMENTATION:
        raise EvidenceError("T26 experiment must identify the Python standard-library implementation")
    if experiment.get("framework") != T26_OFFLINE_AGENT_LOOP_FRAMEWORK:
        raise EvidenceError("T26 experiment must explicitly use no upper Agent framework")
    if experiment.get("scenarios") != list(T26_OFFLINE_AGENT_LOOP_SCENARIOS):
        raise EvidenceError("T26 experiment scenarios must follow the fixed fixture order")

    raw_cases = experiment.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise EvidenceError("T26 experiment cases must be a non-empty list")
    cases: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(raw_cases):
        if not isinstance(case, dict):
            raise EvidenceError(f"T26 case {index} must be an object")
        _reject_sensitive_unknown_fields(case, f"T26 case {index}")
        allowed_case = {
            "version",
            "scenario",
            "outcome",
            "max_steps",
            "stop_reason",
            "retry_count",
            "tool_attempts",
            "output_valid",
            "structured_output",
            "events",
        }
        unexpected_case = sorted(set(case) - allowed_case)
        if unexpected_case:
            raise EvidenceError(
                f"T26 case {index} contains unsupported fields: " + ", ".join(unexpected_case)
            )
        scenario = case.get("scenario")
        if scenario not in T26_OFFLINE_AGENT_LOOP_SCENARIOS or scenario in cases:
            raise EvidenceError("T26 case scenarios must be unique known fixture scenarios")
        if case.get("version") != T26_OFFLINE_AGENT_LOOP_VERSION:
            raise EvidenceError(f"T26 {scenario} case has an unsupported version")
        if case.get("outcome") not in T26_OFFLINE_AGENT_LOOP_ALLOWED_OUTCOMES:
            raise EvidenceError(f"T26 {scenario} case outcome is not supported")
        max_steps = case.get("max_steps")
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= 8:
            raise EvidenceError(f"T26 {scenario} max_steps must be an integer from 1 to 8")
        stop_reason = case.get("stop_reason")
        if stop_reason not in {"completed", "tool_error", "max_steps", "invalid-structured-output"}:
            raise EvidenceError(f"T26 {scenario} stop_reason is not supported")
        for field in ("retry_count", "tool_attempts"):
            value = case.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 8:
                raise EvidenceError(f"T26 {scenario} {field} must be an integer from 0 to 8")
        if not isinstance(case.get("output_valid"), bool):
            raise EvidenceError(f"T26 {scenario} output_valid must be boolean")
        if case["output_valid"]:
            output = _validate_t26_structured_output(case.get("structured_output"), f"T26 {scenario} structured_output")
            structured_status = output["status"]
        else:
            if case.get("structured_output") is not None:
                raise EvidenceError(f"T26 {scenario} invalid output must be null")
            structured_status = "none"
        events, event_kinds = _t26_event_sequence(case, scenario=scenario)
        if scenario == "budget-stop" and case.get("stop_reason") != "max_steps":
            raise EvidenceError("T26 budget-stop must have max_steps stop_reason")
        if scenario != "budget-stop" and case.get("stop_reason") == "max_steps":
            raise EvidenceError(f"T26 {scenario} cannot claim budget stop")
        cases[scenario] = case

    derived = _derive_t26_checks(cases)
    if checks != derived:
        raise EvidenceError("T26 evidence checks do not match the recorded scenario events")
    if document_result == "passed" and any(check["result"] != "passed" for check in derived):
        raise EvidenceError("Passed T26 evidence cannot contain failed or alternative checks")
    if document_result in {"passed", "alternative"} and not all(
        _t26_case_observed(cases.get(scenario, {}), scenario)
        for scenario in T26_OFFLINE_AGENT_LOOP_SCENARIOS
    ):
        raise EvidenceError("Completed T26 evidence is missing one or more scenario paths")

    public_cases = []
    for scenario in T26_OFFLINE_AGENT_LOOP_SCENARIOS:
        case = cases.get(scenario)
        if case is None:
            continue
        events, event_kinds = _t26_event_sequence(case, scenario=scenario)
        public_cases.append(
            {
                "scenario": scenario,
                "outcome": case["outcome"],
                "max_steps": case["max_steps"],
                "stop_reason": case["stop_reason"],
                "retry_count": case["retry_count"],
                "tool_attempts": case["tool_attempts"],
                "output_valid": case["output_valid"],
                "structured_status": "none"
                if case["structured_output"] is None
                else _validate_t26_structured_output(
                    case["structured_output"], f"T26 {scenario} structured_output"
                )["status"],
                "event_kinds": event_kinds,
                "event_statuses": [event["status"] for event in events],
            }
        )
    return {
        "version": T26_OFFLINE_AGENT_LOOP_VERSION,
        "implementation": T26_OFFLINE_AGENT_LOOP_IMPLEMENTATION,
        "framework": T26_OFFLINE_AGENT_LOOP_FRAMEWORK,
        "scenarios": list(T26_OFFLINE_AGENT_LOOP_SCENARIOS),
        "cases": public_cases,
    }


def validate_hooks_tasks_experiment(
    value: Any,
    *,
    document_result: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate T21's anonymous trigger/task observations and derive checks."""

    if not isinstance(value, dict):
        raise EvidenceError("T21 evidence requires an experiment object")
    _reject_sensitive_unknown_fields(value, "T21 experiment")
    if set(value) != {"version", "runs", "observed"}:
        raise EvidenceError("T21 experiment must contain only version, runs and observed")
    if value.get("version") != HOOKS_TASKS_EXPERIMENT_VERSION:
        raise EvidenceError("Unsupported T21 Hooks/Tasks experiment version")
    runs = value.get("runs")
    if not isinstance(runs, list):
        raise EvidenceError("T21 experiment runs must be a list")

    allowed_fields = {
        "id",
        "mode",
        "trigger",
        "deduplicated",
        "permission",
        "stopped",
        "failed",
        "recovered",
        "taskCreated",
        "sideEffect",
        "scheduleArmed",
        "backgroundStarted",
    }
    seen_ids: set[str] = set()
    normalized_runs: list[dict[str, Any]] = []
    for index, raw_run in enumerate(runs):
        if not isinstance(raw_run, dict):
            raise EvidenceError(f"T21 experiment run {index} must be an object")
        _reject_sensitive_unknown_fields(raw_run, f"T21 experiment run {index}")
        if set(raw_run) != allowed_fields:
            missing = sorted(allowed_fields - set(raw_run))
            unknown = sorted(set(raw_run) - allowed_fields)
            detail = []
            if missing:
                detail.append("missing: " + ", ".join(missing))
            if unknown:
                detail.append("unknown: " + ", ".join(unknown))
            raise EvidenceError("T21 experiment run fields invalid" + (" (" + "; ".join(detail) + ")" if detail else ""))
        run_id = raw_run["id"]
        _require_identifier(run_id, f"T21 experiment run {index}.id")
        if run_id in seen_ids:
            raise EvidenceError(f"T21 experiment run id repeated: {run_id}")
        seen_ids.add(run_id)
        mode = raw_run["mode"]
        if mode not in HOOKS_TASKS_MODES:
            raise EvidenceError(f"T21 experiment run {run_id}.mode is not supported")
        permission = raw_run["permission"]
        if permission not in HOOKS_TASKS_PERMISSIONS:
            raise EvidenceError(f"T21 experiment run {run_id}.permission is not supported")
        bool_fields = [
            "trigger",
            "deduplicated",
            "stopped",
            "failed",
            "recovered",
            "taskCreated",
            "sideEffect",
            "scheduleArmed",
            "backgroundStarted",
        ]
        if any(not isinstance(raw_run[field], bool) for field in bool_fields):
            raise EvidenceError(f"T21 experiment run {run_id} contains a non-boolean state")
        if raw_run["sideEffect"] and permission != "allowed":
            raise EvidenceError(f"T21 experiment run {run_id} reports side effect without allowed permission")
        if raw_run["recovered"] and not raw_run["failed"]:
            raise EvidenceError(f"T21 experiment run {run_id} reports recovery without failure")
        normalized_runs.append({field: raw_run[field] for field in ["id", *sorted(allowed_fields - {"id"})]})

    observed = value.get("observed")
    if not isinstance(observed, list) or any(item not in {
        "trigger",
        "deduplication",
        "permission",
        "stop",
        "failure-recovery",
        "side-effect-guard",
        "explicit-task",
    } for item in observed):
        raise EvidenceError("T21 experiment observed contains an unsupported finding")
    if len(observed) != len(set(observed)):
        raise EvidenceError("T21 experiment observed must not repeat a finding")

    derived_observed: set[str] = set()
    for run in normalized_runs:
        if run["trigger"]:
            derived_observed.add("trigger")
        if run["deduplicated"]:
            derived_observed.add("deduplication")
        if run["permission"] == "blocked":
            derived_observed.add("permission")
        if run["stopped"]:
            derived_observed.add("stop")
        if run["recovered"]:
            derived_observed.add("failure-recovery")
        if run["sideEffect"] is False:
            derived_observed.add("side-effect-guard")
        if run["taskCreated"]:
            derived_observed.add("explicit-task")
    if set(observed) != derived_observed:
        raise EvidenceError("T21 experiment observed does not match its runs")

    expected_checks = [
        {"id": "trigger-observed", "result": "passed" if any(run["trigger"] for run in normalized_runs) else "failed"},
        {"id": "deduplication-observed", "result": "passed" if any(run["deduplicated"] for run in normalized_runs) else "failed"},
        {"id": "permission-boundary", "result": "passed" if any(run["permission"] == "blocked" for run in normalized_runs) else "failed"},
        {"id": "stop-condition", "result": "passed" if any(run["stopped"] for run in normalized_runs) else "failed"},
        {"id": "failure-recovered", "result": "passed" if any(run["recovered"] for run in normalized_runs) else "failed"},
        {"id": "side-effect-not-triggered", "result": "passed" if normalized_runs and all(run["sideEffect"] is False for run in normalized_runs) else "failed"},
        {"id": "explicit-task-recorded", "result": "passed" if any(run["taskCreated"] for run in normalized_runs) else "failed"},
        {"id": "offline-deterministic", "result": "passed" if normalized_runs else "failed"},
    ]
    if document_result in {"passed", "alternative"} and any(check["result"] != "passed" for check in expected_checks):
        raise EvidenceError("Completed T21 evidence is missing a required trigger/task observation")
    return expected_checks, {
        "version": HOOKS_TASKS_EXPERIMENT_VERSION,
        "runs": normalized_runs,
        "observed": sorted(derived_observed),
    }


def _research_capstone_expected_flags(input_id: str, fault: str) -> dict[str, bool]:
    """Return the deterministic T23 flag contract for one safe fixture run."""

    return {
        "context": True,
        "memory": fault != "stale-memory",
        "skill": True,
        "mcp": fault != "mcp-denied",
        "script": True,
        "figure": fault != "missing-values",
        "record": True,
        "report": fault == "none",
        "evidence": True,
        "migration": input_id == "pressure-night",
        "rubric": fault == "none" and input_id == "pressure-night",
        "offline": True,
    }


def _research_capstone_checks(flags: dict[str, bool]) -> list[dict[str, str]]:
    fields = (
        ("context-recorded", "context"),
        ("memory-governed", "memory"),
        ("skill-applied", "skill"),
        ("mcp-boundary", "mcp"),
        ("script-reproducible", "script"),
        ("figure-produced", "figure"),
        ("record-complete", "record"),
        ("report-complete", "report"),
        ("evidence-exported", "evidence"),
        ("migration-complete", "migration"),
        ("rubric-complete", "rubric"),
        ("offline-deterministic", "offline"),
    )
    return [
        {"id": check_id, "result": "passed" if flags[field] else "failed"}
        for check_id, field in fields
    ]


def load_research_capstone_checks(
    evidence_file: Path,
    *,
    expected_course_version: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate T23's status-only research delivery and derive its checks.

    The checker accepts no raw telemetry, paths, prompts, model output, or
    client logs. It recomputes the learner-facing checks from the fixed
    synthetic input/fault contract so a hand-edited ``result`` cannot forge a
    completed research delivery.
    """

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(
            f"Research capstone evidence fixture not found: {evidence_file.name}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid research capstone JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Research capstone evidence must be a JSON object")

    document = validate_evidence_document(value)
    if document["lesson_id"] != RESEARCH_CAPSTONE_LESSON_ID:
        raise EvidenceError("Research capstone fixture lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("Research capstone fixture course_version does not match the current course")

    experiment = value.get("experiment")
    if not isinstance(experiment, dict):
        raise EvidenceError("Research capstone evidence requires an experiment object")
    _reject_sensitive_unknown_fields(experiment, "Research capstone experiment")
    expected_experiment_fields = {
        "version",
        "baseline_id",
        "input",
        "context",
        "memory",
        "skill",
        "mcp",
        "artifacts",
        "migration",
        "rubric",
        "offline",
        "fault",
    }
    if set(experiment) != expected_experiment_fields:
        missing = sorted(expected_experiment_fields - set(experiment))
        unknown = sorted(set(experiment) - expected_experiment_fields)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unknown:
            details.append("unknown: " + ", ".join(unknown))
        raise EvidenceError(
            "Research capstone experiment fields are invalid"
            + (" (" + "; ".join(details) + ")" if details else "")
        )
    if experiment["version"] != RESEARCH_CAPSTONE_VERSION:
        raise EvidenceError("Unsupported research capstone experiment version")
    if experiment["baseline_id"] != RESEARCH_CAPSTONE_BASELINE_ID:
        raise EvidenceError("Research capstone baseline_id is unsupported")
    input_id = experiment["input"]
    if input_id not in RESEARCH_CAPSTONE_INPUTS:
        raise EvidenceError("Research capstone input variant is unsupported")
    fault = experiment["fault"]
    if fault not in RESEARCH_CAPSTONE_FAULTS:
        raise EvidenceError("Research capstone fault is unsupported")

    bool_fields = {
        "context",
        "memory",
        "skill",
        "mcp",
        "migration",
        "rubric",
        "offline",
    }
    if any(not isinstance(experiment[field], bool) for field in bool_fields):
        raise EvidenceError("Research capstone experiment flags must be booleans")
    artifacts = experiment["artifacts"]
    if not isinstance(artifacts, dict):
        raise EvidenceError("Research capstone artifacts must be an object")
    _reject_sensitive_unknown_fields(artifacts, "Research capstone artifacts")
    expected_artifact_fields = {"script", "figure", "record", "report", "evidence"}
    if set(artifacts) != expected_artifact_fields:
        raise EvidenceError("Research capstone artifacts must cover script, figure, record, report and evidence")
    if any(not isinstance(artifacts[field], bool) for field in expected_artifact_fields):
        raise EvidenceError("Research capstone artifact flags must be booleans")

    expected_flags = _research_capstone_expected_flags(input_id, fault)
    actual_flags = {
        "context": experiment["context"],
        "memory": experiment["memory"],
        "skill": experiment["skill"],
        "mcp": experiment["mcp"],
        "script": artifacts["script"],
        "figure": artifacts["figure"],
        "record": artifacts["record"],
        "report": artifacts["report"],
        "evidence": artifacts["evidence"],
        "migration": experiment["migration"],
        "rubric": experiment["rubric"],
        "offline": experiment["offline"],
    }
    if actual_flags != expected_flags:
        raise EvidenceError("Research capstone flags do not match the selected input and fault")
    derived_checks = _research_capstone_checks(actual_flags)
    supplied_checks = document["evidence"]
    if [check["id"] for check in supplied_checks] != list(RESEARCH_CAPSTONE_CHECK_IDS):
        raise EvidenceError(
            "Research capstone evidence IDs must be exactly "
            + ", ".join(RESEARCH_CAPSTONE_CHECK_IDS)
        )
    if supplied_checks != derived_checks:
        raise EvidenceError("Research capstone checks do not match the recorded experiment")
    expected_result = "passed" if all(check["result"] == "passed" for check in derived_checks) else "partial"
    if document["result"] != expected_result:
        raise EvidenceError("Research capstone result does not match its evidence")
    return derived_checks, {
        "version": RESEARCH_CAPSTONE_VERSION,
        "baseline_id": RESEARCH_CAPSTONE_BASELINE_ID,
        "input": input_id,
        "context": actual_flags["context"],
        "memory": actual_flags["memory"],
        "skill": actual_flags["skill"],
        "mcp": actual_flags["mcp"],
        "artifacts": {
            field: actual_flags[field]
            for field in ("script", "figure", "record", "report", "evidence")
        },
        "migration": actual_flags["migration"],
        "rubric": actual_flags["rubric"],
        "offline": actual_flags["offline"],
        "fault": fault,
    }


def validate_claude_migration_checks(value: Any) -> list[dict[str, Any]]:
    """Validate the stable public checks for the Claude migration journey."""

    if not isinstance(value, list) or not value:
        raise EvidenceError("Claude migration evidence checks must be a non-empty list")

    actual_ids: list[str] = []
    normalized: list[dict[str, Any]] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(
                f"Claude migration evidence check {index} must be an object"
            )
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(
                f"Claude migration evidence check {index} needs an id"
            )
        if check_id in actual_ids:
            raise EvidenceError(
                f"Claude migration evidence check ID repeated: {check_id}"
            )
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(
                f"Claude migration evidence check {check_id}.result is not supported"
            )
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})

    expected_ids = list(CLAUDE_MIGRATION_CHECK_IDS)
    if actual_ids != expected_ids:
        missing = [check_id for check_id in expected_ids if check_id not in actual_ids]
        unknown = [check_id for check_id in actual_ids if check_id not in expected_ids]
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unknown:
            details.append("unknown: " + ", ".join(unknown))
        raise EvidenceError(
            "Claude migration evidence IDs must be exactly "
            + ", ".join(expected_ids)
            + ("; " + "; ".join(details) if details else "")
        )
    return normalized


def _require_string_tuple(value: Any, label: str, expected: tuple[str, ...]) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) for item in value
    ):
        raise EvidenceError(f"{label} must be a list of strings")
    if tuple(value) != expected:
        raise EvidenceError(f"{label} does not match the migration contract")


def validate_claude_migration_experiment(
    experiment: Any,
    *,
    checks: list[dict[str, Any]],
    document_result: str,
) -> dict[str, Any]:
    """Validate status-only migration metadata and derive stage consistency.

    This intentionally accepts only the changed-input contract and status
    enums.  It never accepts prompts, source text, paths, model output, or a
    claim that a live Claude Code/Codex call occurred.
    """

    if not isinstance(experiment, dict):
        raise EvidenceError(
            "Claude migration completed evidence must include an experiment object"
        )
    expected_fields = {
        "version",
        "mode",
        "migration_variant",
        "input_contract",
        "official_facts",
        "live_call",
        "codex_reference",
    }
    unexpected = sorted(set(experiment) - expected_fields)
    if unexpected:
        raise EvidenceError(
            "Claude migration experiment contains unsupported fields: "
            + ", ".join(unexpected)
        )
    if experiment.get("version") != CLAUDE_MIGRATION_TRACE_VERSION:
        raise EvidenceError("Unsupported Claude migration experiment version")

    mode = experiment.get("mode")
    if mode not in {"claude-only", "dual-tool"}:
        raise EvidenceError("Claude migration mode must be claude-only or dual-tool")
    if experiment.get("migration_variant") != CLAUDE_MIGRATION_VARIANT["id"]:
        raise EvidenceError("Claude migration evidence has an unknown input variant")

    input_contract = experiment.get("input_contract")
    if not isinstance(input_contract, dict):
        raise EvidenceError("Claude migration input_contract must be an object")
    expected_contract_fields = {"subject", "units", "record_limit", "outputs"}
    if set(input_contract) != expected_contract_fields:
        raise EvidenceError(
            "Claude migration input_contract must contain subject, units, record_limit and outputs"
        )
    if input_contract.get("subject") != CLAUDE_MIGRATION_VARIANT["subject"]:
        raise EvidenceError("Claude migration input subject does not differ contractually")
    _require_string_tuple(
        input_contract.get("units"),
        "Claude migration input_contract.units",
        CLAUDE_MIGRATION_VARIANT["units"],
    )
    if input_contract.get("record_limit") != CLAUDE_MIGRATION_VARIANT["record_limit"]:
        raise EvidenceError("Claude migration input record limit does not match contract")
    _require_string_tuple(
        input_contract.get("outputs"),
        "Claude migration input_contract.outputs",
        CLAUDE_MIGRATION_VARIANT["outputs"],
    )

    official_facts = experiment.get("official_facts")
    if not isinstance(official_facts, dict) or set(official_facts) != {
        "installation",
        "operation",
        "permissions",
        "cost",
    }:
        raise EvidenceError(
            "Claude migration official_facts must cover installation, operation, permissions and cost"
        )
    if any(value != "recorded" for value in official_facts.values()):
        raise EvidenceError("Claude migration official facts must be status-only recorded values")
    if experiment.get("live_call") != "not-verified":
        raise EvidenceError("Claude migration evidence must not claim a live Claude call")
    codex_reference = experiment.get("codex_reference")
    expected_reference = "not-required" if mode == "claude-only" else "status-only"
    if codex_reference != expected_reference:
        raise EvidenceError(
            "Claude migration Codex reference does not match the selected path"
        )

    journey = experiment.get("journey")
    if journey is not None:
        raise EvidenceError("Claude migration journey belongs to the public journey field")
    return {
        "version": CLAUDE_MIGRATION_TRACE_VERSION,
        "mode": mode,
        "migration_variant": CLAUDE_MIGRATION_VARIANT["id"],
        "input_contract": {
            "subject": CLAUDE_MIGRATION_VARIANT["subject"],
            "units": list(CLAUDE_MIGRATION_VARIANT["units"]),
            "record_limit": CLAUDE_MIGRATION_VARIANT["record_limit"],
            "outputs": list(CLAUDE_MIGRATION_VARIANT["outputs"]),
        },
        "official_facts": {
            "installation": "recorded",
            "operation": "recorded",
            "permissions": "recorded",
            "cost": "recorded",
        },
        "live_call": "not-verified",
        "codex_reference": codex_reference,
    }


def load_claude_migration_checks(
    evidence_file: Path,
    *,
    expected_course_version: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate the complete local Claude migration checkpoint document."""

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Claude migration fixture must be a JSON object")
    document = validate_evidence_document(value)
    if document["lesson_id"] != CLAUDE_MIGRATION_LESSON_ID:
        raise EvidenceError("Claude migration fixture lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("Claude migration fixture course_version does not match the current course")
    if value.get("task_id") != CLAUDE_MIGRATION_TASK_ID:
        raise EvidenceError("Claude migration fixture task_id is unsupported")
    if value.get("platform") != "windows" or value.get("shell") != "powershell":
        raise EvidenceError("Claude migration fixture must identify the Windows PowerShell path")

    journey = value.get("journey")
    if not isinstance(journey, dict):
        raise EvidenceError("Claude migration fixture requires a checkpoint journey")
    _reject_sensitive_unknown_fields(journey, "Claude migration journey")
    if set(journey) != {"trace_version", "trace_id", "stages"}:
        raise EvidenceError("Claude migration journey must contain trace_version, trace_id and stages")
    if journey["trace_version"] != CLAUDE_MIGRATION_TRACE_VERSION:
        raise EvidenceError("Unsupported Claude migration journey version")
    _require_identifier(journey["trace_id"], "Claude migration journey.trace_id")
    stages = journey["stages"]
    if not isinstance(stages, list) or len(stages) != len(CLAUDE_MIGRATION_STAGE_IDS):
        raise EvidenceError("Claude migration journey must contain the complete ordered stage sequence")

    stage_results: dict[str, bool] = {}
    path_modes: set[str] = set()
    for expected_sequence, (expected_id, raw_stage) in enumerate(
        zip(CLAUDE_MIGRATION_STAGE_IDS, stages, strict=True), start=1
    ):
        if not isinstance(raw_stage, dict):
            raise EvidenceError("Claude migration journey stages must contain objects")
        _reject_sensitive_unknown_fields(raw_stage, f"Claude migration stage {expected_id}")
        required_stage_fields = {"id", "sequence", "result", "observations"}
        allowed_stage_fields = required_stage_fields | {"mode"}
        missing = sorted(required_stage_fields - set(raw_stage))
        unexpected = sorted(set(raw_stage) - allowed_stage_fields)
        if missing or unexpected:
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unknown: " + ", ".join(unexpected))
            raise EvidenceError(
                f"Claude migration stage {expected_id} fields are invalid (" + "; ".join(details) + ")"
            )
        if raw_stage["id"] != expected_id or raw_stage["sequence"] != expected_sequence:
            raise EvidenceError("Claude migration journey stages are out of order")
        if raw_stage.get("mode") is not None:
            if raw_stage["mode"] not in {"claude-only", "dual-tool"}:
                raise EvidenceError("Claude migration stage mode is invalid")
            path_modes.add(raw_stage["mode"])
        result = raw_stage["result"]
        if result not in {"passed", "failed"}:
            raise EvidenceError("Claude migration stage result must be passed or failed")
        observations = raw_stage["observations"]
        if not isinstance(observations, dict):
            raise EvidenceError(f"Claude migration stage {expected_id}.observations must be an object")
        expected_observations = CLAUDE_MIGRATION_STAGE_OBSERVATIONS[expected_id]
        if set(observations) != expected_observations:
            missing_observations = sorted(expected_observations - set(observations))
            unknown_observations = sorted(set(observations) - expected_observations)
            details = []
            if missing_observations:
                details.append("missing: " + ", ".join(missing_observations))
            if unknown_observations:
                details.append("unknown: " + ", ".join(unknown_observations))
            raise EvidenceError(
                f"Claude migration stage {expected_id}.observations are incomplete or unexpected ("
                + "; ".join(details)
                + ")"
            )
        if any(not isinstance(item, bool) for item in observations.values()):
            raise EvidenceError(f"Claude migration stage {expected_id}.observations must be booleans")
        computed_result = "passed" if all(observations.values()) else "failed"
        if result != computed_result:
            raise EvidenceError(f"Claude migration stage {expected_id}.result does not match observations")
        stage_results[expected_id] = result == "passed"

    if len(path_modes) > 1:
        raise EvidenceError("Claude migration journey mixes path modes")

    checks = validate_claude_migration_checks(document["evidence"])
    check_by_id = {check["id"]: check["result"] for check in checks}
    derived_checks = [
        {"id": "clarification-recorded", "result": "passed" if stage_results["clarify"] else "failed"},
        {"id": "plan-recorded", "result": "passed" if stage_results["plan"] else "failed"},
        {"id": "official-facts-recorded", "result": "passed" if stage_results["official-facts"] else "failed"},
        {"id": "migration-input-changed", "result": "passed" if stage_results["change"] else "failed"},
        {
            "id": "failure-recovered",
            "result": "passed" if stage_results["failure-observed"] and stage_results["recovery"] else "failed",
        },
        {"id": "tests-passed", "result": "passed" if stage_results["recovery"] else "failed"},
        {"id": "permission-cost-compared", "result": "passed" if stage_results["official-facts"] else "failed"},
        {"id": "path-completed", "result": "passed" if stage_results["review"] else "failed"},
        {
            "id": "live-claude-not-claimed",
            "result": "passed" if stage_results["official-facts"] and stage_results["delivery"] else "failed",
        },
        {
            "id": "report-generated",
            "result": "passed" if stage_results["recovery"] and stage_results["delivery"] else "failed",
        },
        {"id": "delivery-recorded", "result": "passed" if stage_results["delivery"] else "failed"},
    ]
    if check_by_id != {check["id"]: check["result"] for check in derived_checks}:
        raise EvidenceError("Claude migration checks do not match the recorded checkpoint journey")
    experiment = validate_claude_migration_experiment(
        value.get("experiment"), checks=checks, document_result=document["result"]
    )
    if path_modes and experiment["mode"] not in path_modes:
        raise EvidenceError("Claude migration experiment mode does not match the journey")
    if document["result"] in {"passed", "alternative"} and not all(stage_results.values()):
        raise EvidenceError("Completed Claude migration evidence is missing a passed stage")
    return checks, experiment


def _mcp_expected_capabilities() -> dict[str, list[str]]:
    return {key: list(value) for key, value in MCP_DISCOVERY_CAPABILITIES.items()}


def validate_mcp_discovery(
    value: Any,
    *,
    document_result: str | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate status-only evidence for the real MCP discovery lab."""

    if not isinstance(value, dict):
        raise EvidenceError("MCP discovery evidence must be an object")
    _reject_sensitive_unknown_fields(value, "MCP discovery evidence")
    allowed = {
        "fixture_version", "lesson_id", "mode", "transport", "protocol_version",
        "server", "capabilities", "observations", "inspector",
    }
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise EvidenceError(
            "MCP discovery evidence contains unsupported fields: " + ", ".join(unexpected)
        )
    if value.get("fixture_version") != MCP_DISCOVERY_FIXTURE_VERSION:
        raise EvidenceError("Unsupported MCP discovery fixture version")
    if value.get("lesson_id") != MCP_DISCOVERY_LESSON_ID:
        raise EvidenceError("MCP discovery fixture has the wrong lesson_id")

    mode = value.get("mode")
    transport = value.get("transport")
    protocol_version = value.get("protocol_version")
    if mode not in {"real-stdio", "offline-fallback"}:
        raise EvidenceError("MCP discovery mode must be real-stdio or offline-fallback")
    if transport not in {"stdio", "deterministic-in-memory"}:
        raise EvidenceError("MCP discovery transport is unsupported")
    if mode == "real-stdio" and transport != "stdio":
        raise EvidenceError("Real MCP discovery must use stdio transport")
    if mode == "offline-fallback" and transport != "deterministic-in-memory":
        raise EvidenceError("Offline MCP discovery must use the deterministic fallback label")

    server = value.get("server")
    if isinstance(server, dict):
        _reject_sensitive_unknown_fields(server, "MCP server identity")
    if not isinstance(server, dict) or set(server) != {"name", "version"}:
        raise EvidenceError("MCP server identity must contain only name and version")
    if server != {"name": "t19-discovery-server", "version": "1.0.0"}:
        raise EvidenceError("MCP discovery server identity does not match the course fixture")

    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != {"tools", "resources", "prompts"}:
        raise EvidenceError("MCP capabilities must contain tools, resources and prompts")
    normalized_capabilities: dict[str, list[str]] = {}
    for category in MCP_DISCOVERY_CAPABILITIES:
        actual = capabilities.get(category)
        if not isinstance(actual, list) or any(not isinstance(item, str) for item in actual):
            raise EvidenceError(f"MCP {category} capability names must be a list of strings")
        if len(actual) != len(set(actual)):
            raise EvidenceError(f"MCP {category} capability names must not repeat")
        normalized_capabilities[category] = sorted(actual)

    observations = value.get("observations")
    expected_observations = {
        "server_connected", "tools_listed", "resources_listed", "prompts_listed",
        "tool_called", "resource_read", "prompt_retrieved", "failure_recovered",
    }
    if not isinstance(observations, dict) or set(observations) != expected_observations:
        raise EvidenceError("MCP observations must contain exactly the boolean status fields")
    if any(not isinstance(observations[key], bool) for key in expected_observations):
        raise EvidenceError("MCP observations must contain exactly the boolean status fields")

    inspector = value.get("inspector")
    if not isinstance(inspector, dict) or set(inspector) != {"verified", "methods"}:
        raise EvidenceError("MCP Inspector evidence must contain verified and methods")
    methods = inspector.get("methods")
    if not isinstance(methods, list) or any(not isinstance(item, str) for item in methods):
        raise EvidenceError("MCP Inspector methods must be a list of strings")
    if len(methods) != len(set(methods)) or not set(methods) <= MCP_DISCOVERY_INSPECTOR_METHODS:
        raise EvidenceError("MCP Inspector methods contain duplicates or unknown IDs")
    if not isinstance(inspector.get("verified"), bool):
        raise EvidenceError("MCP Inspector verified must be boolean")

    formal = (
        mode == "real-stdio"
        and protocol_version == MCP_DISCOVERY_PROTOCOL_VERSION
        and normalized_capabilities == _mcp_expected_capabilities()
        and all(observations.values())
        and inspector["verified"] is True
        and set(methods) == MCP_DISCOVERY_INSPECTOR_METHODS
    )
    checks = [
        {"id": "real-transport", "result": "passed" if mode == "real-stdio" and transport == "stdio" else "failed"},
        {"id": "server-connected", "result": "passed" if observations["server_connected"] and mode == "real-stdio" else "failed"},
        {"id": "tools-discovered", "result": "passed" if observations["tools_listed"] and normalized_capabilities["tools"] == list(MCP_DISCOVERY_CAPABILITIES["tools"]) else "failed"},
        {"id": "resources-discovered", "result": "passed" if observations["resources_listed"] and normalized_capabilities["resources"] == list(MCP_DISCOVERY_CAPABILITIES["resources"]) else "failed"},
        {"id": "prompts-discovered", "result": "passed" if observations["prompts_listed"] and normalized_capabilities["prompts"] == list(MCP_DISCOVERY_CAPABILITIES["prompts"]) else "failed"},
        {"id": "tool-call-observed", "result": "passed" if observations["tool_called"] else "failed"},
        {"id": "resource-read-observed", "result": "passed" if observations["resource_read"] else "failed"},
        {"id": "prompt-retrieval-observed", "result": "passed" if observations["prompt_retrieved"] else "failed"},
        {"id": "failure-recovered", "result": "passed" if observations["failure_recovered"] else "failed"},
        {"id": "inspector-verified", "result": "passed" if inspector["verified"] and set(methods) == MCP_DISCOVERY_INSPECTOR_METHODS else "failed"},
    ]
    if mode == "offline-fallback":
        checks.insert(0, {"id": "offline-deterministic", "result": "passed"})
    if formal and document_result in {"failed", "partial"}:
        raise EvidenceError("MCP fixture is complete but its document result is not complete")
    if document_result in {"passed", "alternative"} and not formal:
        raise EvidenceError("Completed MCP evidence is missing real transport or Inspector proof")
    return checks, {
        "fixture_version": MCP_DISCOVERY_FIXTURE_VERSION,
        "lesson_id": MCP_DISCOVERY_LESSON_ID,
        "mode": mode,
        "transport": transport,
        "protocol_version": protocol_version,
        "server": {"name": server["name"], "version": server["version"]},
        "capabilities": normalized_capabilities,
        "observations": {key: observations[key] for key in sorted(observations)},
        "inspector": {"verified": inspector["verified"], "methods": sorted(methods)},
    }

def validate_t20_evidence_checks(value: Any) -> list[dict[str, Any]]:
    """Validate the fixed, status-only public checks for the MCP call lab."""

    if not isinstance(value, list) or len(value) != len(MCP_CALL_CHECK_IDS):
        raise EvidenceError("T20 evidence checks must contain the complete fixed check list")
    normalized: list[dict[str, str]] = []
    actual_ids: list[str] = []
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T20 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T20 evidence check {index}")
        if set(check) != {"id", "result"}:
            raise EvidenceError(f"T20 evidence check {index} must contain only id and result")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T20 evidence check {index} needs an id")
        if check.get("result") not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T20 evidence check {check_id}.result is not supported")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": check["result"]})
    if actual_ids != list(MCP_CALL_CHECK_IDS):
        raise EvidenceError(
            "T20 evidence IDs must be exactly " + ", ".join(MCP_CALL_CHECK_IDS)
        )
    return normalized


def validate_t20_experiment(
    value: Any,
    *,
    document_result: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate MCP call evidence without exporting tool payloads or paths.

    A live completion is deliberately stricter than the offline fallback: it
    must carry the pinned protocol, a real stdio transport, a T19 catalog
    bridge, a human-confirmed bounded write, an Inspector result, and at least
    one observed-and-recovered fault. The offline fixture remains useful for
    rehearsal but can never be classified as formal MCP completion.
    """

    if not isinstance(value, dict):
        raise EvidenceError("T20 evidence requires an experiment object")
    # ``discovery_source`` is a deliberately bounded catalog identifier that
    # names the T19 seam; the generic privacy guard treats the word ``source``
    # as sensitive, so exclude only this exact public key from that name scan.
    _reject_sensitive_unknown_fields(
        {key: item for key, item in value.items() if key != "discovery_source"},
        "T20 experiment",
    )
    expected_fields = {
        "version",
        "mode",
        "formal_mcp",
        "protocol",
        "transport",
        "discovery_source",
        "tools_observed",
        "permission",
        "call_completed",
        "side_effect",
        "faults",
        "inspector",
        "no_sensitive_output",
    }
    unexpected = sorted(set(value) - expected_fields)
    if unexpected:
        raise EvidenceError("T20 experiment contains unsupported fields: " + ", ".join(unexpected))
    if value.get("version") != MCP_CALL_EXPERIMENT_VERSION:
        raise EvidenceError("Unsupported T20 MCP experiment version")

    mode = value.get("mode")
    if mode not in {"live", "offline-fallback"}:
        raise EvidenceError("T20 experiment mode is unsupported")
    formal_mcp = value.get("formal_mcp")
    if not isinstance(formal_mcp, bool) or formal_mcp != (mode == "live"):
        raise EvidenceError("T20 formal_mcp must agree with the experiment mode")
    protocol = value.get("protocol")
    if not isinstance(protocol, str) or not protocol:
        raise EvidenceError("T20 experiment protocol must be a non-empty string")
    if mode == "live" and protocol != MCP_CALL_PROTOCOL_VERSION:
        raise EvidenceError("T20 live evidence must pin MCP 2026-07-28")
    if mode == "offline-fallback" and protocol != "offline-fixture-v1":
        raise EvidenceError("T20 offline evidence must identify its fixture protocol")

    transport = value.get("transport")
    if transport not in {"stdio", "not-used"}:
        raise EvidenceError("T20 transport must be stdio or not-used")
    discovery_source = value.get("discovery_source")
    if discovery_source not in {"t19-tool-catalog-v1", "offline-tool-catalog"}:
        raise EvidenceError("T20 discovery source is unsupported")
    tools_observed = value.get("tools_observed")
    if (
        not isinstance(tools_observed, list)
        or any(item not in MCP_CALL_TOOL_NAMES for item in tools_observed)
        or len(tools_observed) != len(set(tools_observed))
    ):
        raise EvidenceError("T20 tools_observed must contain unique known tool names")
    if mode == "live" and discovery_source != "t19-tool-catalog-v1":
        raise EvidenceError("T20 live evidence must identify the T19 discovery seam")
    if mode == "offline-fallback" and discovery_source != "offline-tool-catalog":
        raise EvidenceError("T20 offline evidence must identify its fallback catalog")

    permission = value.get("permission")
    if permission not in {"confirmed", "blocked", "not-requested"}:
        raise EvidenceError("T20 permission state is unsupported")
    call_completed = value.get("call_completed")
    no_sensitive_output = value.get("no_sensitive_output")
    if not isinstance(call_completed, bool) or not isinstance(no_sensitive_output, bool):
        raise EvidenceError("T20 call_completed and no_sensitive_output must be boolean")
    side_effect = value.get("side_effect")
    if side_effect not in {"bounded-local-write", "none", "blocked"}:
        raise EvidenceError("T20 side_effect is unsupported")
    inspector = value.get("inspector")
    if inspector not in {"passed", "not-run"}:
        raise EvidenceError("T20 inspector state is unsupported")

    raw_faults = value.get("faults")
    if not isinstance(raw_faults, list):
        raise EvidenceError("T20 faults must be a list")
    faults: list[dict[str, Any]] = []
    seen_faults: set[str] = set()
    for index, raw_fault in enumerate(raw_faults):
        if not isinstance(raw_fault, dict):
            raise EvidenceError(f"T20 fault {index} must be an object")
        _reject_sensitive_unknown_fields(raw_fault, f"T20 fault {index}")
        if set(raw_fault) != {"id", "observed", "recovered"}:
            raise EvidenceError(f"T20 fault {index} must contain only id, observed and recovered")
        fault_id = raw_fault.get("id")
        if fault_id not in MCP_CALL_FAULT_IDS or fault_id in seen_faults:
            raise EvidenceError(f"T20 fault {index} has an unknown or repeated id")
        observed = raw_fault.get("observed")
        recovered = raw_fault.get("recovered")
        if not isinstance(observed, bool) or not isinstance(recovered, bool):
            raise EvidenceError(f"T20 fault {fault_id} states must be boolean")
        if recovered and not observed:
            raise EvidenceError(f"T20 fault {fault_id} cannot recover without observation")
        seen_faults.add(fault_id)
        faults.append({"id": fault_id, "observed": observed, "recovered": recovered})

    has_complete_fault = any(item["observed"] and item["recovered"] for item in faults)
    all_tools = set(tools_observed) == set(MCP_CALL_TOOL_NAMES)
    if mode == "offline-fallback":
        if formal_mcp or transport != "not-used" or inspector != "not-run":
            raise EvidenceError("Offline fallback must not claim formal transport or Inspector evidence")
        if document_result == "passed":
            raise EvidenceError("Offline fallback can never be formal MCP completion")
        expected_checks = [
            {"id": "transport-connected", "result": "alternative"},
            {"id": "discovery-bridge", "result": "alternative"},
            {"id": "permission-confirmed", "result": "passed"},
            {"id": "tool-called", "result": "alternative"},
            {"id": "side-effect-bounded", "result": "passed" if side_effect == "none" else "failed"},
            {"id": "fault-observed", "result": "alternative"},
            {"id": "fault-recovered", "result": "alternative"},
            {"id": "no-sensitive-output", "result": "passed" if no_sensitive_output else "failed"},
            {"id": "inspector-checked", "result": "failed"},
            {"id": "fallback-explicit", "result": "passed"},
        ]
    else:
        expected_checks = [
            {"id": "transport-connected", "result": "passed" if transport == "stdio" else "failed"},
            {"id": "discovery-bridge", "result": "passed" if discovery_source == "t19-tool-catalog-v1" and all_tools else "failed"},
            {"id": "permission-confirmed", "result": "passed" if permission == "confirmed" else "failed"},
            {"id": "tool-called", "result": "passed" if call_completed else "failed"},
            {"id": "side-effect-bounded", "result": "passed" if side_effect == "bounded-local-write" else "failed"},
            {"id": "fault-observed", "result": "passed" if any(item["observed"] for item in faults) else "failed"},
            {"id": "fault-recovered", "result": "passed" if has_complete_fault else "failed"},
            {"id": "no-sensitive-output", "result": "passed" if no_sensitive_output else "failed"},
            {"id": "inspector-checked", "result": "passed" if inspector == "passed" else "failed"},
            {"id": "fallback-explicit", "result": "passed"},
        ]
        if document_result == "passed" and not has_complete_fault:
            raise EvidenceError("Completed T20 evidence must include an observed and recovered fault")

    supplied_checks = value.get("checks", value.get("evidence", expected_checks))
    normalized_checks = validate_t20_evidence_checks(supplied_checks)
    if normalized_checks != expected_checks:
        raise EvidenceError("T20 evidence checks do not match the recorded MCP experiment")
    if classify_checks([check["result"] for check in expected_checks]) != document_result:
        raise EvidenceError("T20 evidence result does not match its checks")
    return normalized_checks, {
        "version": MCP_CALL_EXPERIMENT_VERSION,
        "mode": mode,
        "formal_mcp": formal_mcp,
        "protocol": protocol,
        "transport": transport,
        "discovery_source": discovery_source,
        "tools_observed": list(tools_observed),
        "permission": permission,
        "call_completed": call_completed,
        "side_effect": side_effect,
        "faults": faults,
        "inspector": inspector,
        "no_sensitive_output": no_sensitive_output,
    }


def load_evidence_checks(
    evidence_file: Path,
    *,
    expected_lesson_id: str,
    expected_course_version: str,
    skill_package_check: str = "passed",
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Read only public check states from a local evidence fixture.

    Fixture details are intentionally discarded.  This lets a learner check a
    local implementation while ensuring that the generated browser document
    cannot accidentally contain a path, source excerpt, or raw data value.
    """

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Evidence fixture must be a JSON object")
    fixture_lesson_id = value.get("lesson_id", expected_lesson_id)
    if fixture_lesson_id != expected_lesson_id:
        raise EvidenceError("Evidence fixture lesson_id does not match the requested lesson")
    if "course_version" in value and value["course_version"] != expected_course_version:
        raise EvidenceError("Evidence fixture course_version does not match the current course")
    if value.get("contract") == "agent-engineering-course/evidence":
        if expected_lesson_id == MEMORY_LESSON_ID:
            # A learner may accidentally leave private fields beside the
            # public document.  T16 drops those unknown top-level fields
            # before the shared validator; experiment fields still pass
            # through the dedicated status-only validator below.
            public_value = {
                field: value[field]
                for field in (
                    "contract",
                    "contract_version",
                    "course_version",
                    "lesson_id",
                    "result",
                    "anonymous",
                    "checked_on",
                    "summary",
                    "evidence",
                )
                if field in value
            }
            try:
                document = validate_evidence_document(public_value)
            except EvidenceError as exc:
                if str(exc) == "Evidence result does not match its checks":
                    raise EvidenceError(
                        "T16 evidence checks do not match the recorded Memory experiment"
                    ) from exc
                raise
        else:
            document = validate_evidence_document(value)
        if expected_lesson_id == MCP_DISCOVERY_LESSON_ID:
            mcp_fixture = value.get("mcp")
            if mcp_fixture is None:
                raise EvidenceError("T19 evidence requires its MCP fixture summary")
            checks, trace = validate_mcp_discovery(
                mcp_fixture,
                document_result=document["result"],
            )
            if document["evidence"] != checks:
                raise EvidenceError("T19 evidence checks do not match the MCP fixture")
            return checks, trace
        if expected_lesson_id == "t02-agent-loop":
            checks = validate_t02_evidence_checks(document["evidence"])
            trace = validate_t02_trace(value.get("trace"), document_result=document["result"])
            validate_t02_check_semantics(checks, trace, document_result=document["result"])
            return checks, trace
        if expected_lesson_id == "t03-agent-instruction":
            checks = validate_t03_evidence_checks(document["evidence"])
            experiment = validate_t03_experiment(
                value.get("experiment"),
                checks=checks,
                document_result=document["result"],
            )
            return checks, experiment
        if expected_lesson_id == CONTEXT_BUDGET_LESSON_ID:
            checks = validate_t14_evidence_checks(document["evidence"])
            expected_checks, simulation = validate_t14_simulation(
                value.get("simulation"), document_result=document["result"]
            )
            if checks != expected_checks:
                raise EvidenceError("T14 evidence checks do not match the recorded simulation")
            return checks, simulation
        if expected_lesson_id == HOOKS_TASKS_LESSON_ID:
            checks, experiment = validate_hooks_tasks_experiment(
                value.get("experiment"), document_result=document["result"]
            )
            supplied_checks = validate_hooks_tasks_checks(document["evidence"])
            if checks != supplied_checks:
                raise EvidenceError("T21 evidence checks do not match the recorded experiment")
            return checks, experiment
        if expected_lesson_id == CLAUDE_MIGRATION_LESSON_ID:
            return load_claude_migration_checks(
                evidence_file,
                expected_course_version=expected_course_version,
            )
        if expected_lesson_id == T15_CONTEXT_RECOVERY_LESSON_ID:
            checks = validate_t15_evidence_checks(document["evidence"])
            experiment = validate_t15_experiment(
                value.get("experiment"),
                checks=checks,
                document_result=document["result"],
            )
            return checks, experiment
        if expected_lesson_id == MEMORY_LESSON_ID:
            checks = validate_t16_evidence_checks(document["evidence"])
            expected_checks, experiment = validate_t16_experiment(
                value.get("experiment"), document_result=document["result"]
            )
            if checks != expected_checks:
                raise EvidenceError("T16 evidence checks do not match the recorded Memory experiment")
            return checks, experiment
        if expected_lesson_id == SKILL_LESSON_ID:
            checks = validate_skill_evidence_checks(document["evidence"])
            expected_checks, simulation = validate_skill_simulation(
                value.get("simulation"),
                document_result=document["result"],
                package_result=skill_package_check,
            )
            if checks != expected_checks:
                raise EvidenceError("T17 Skill evidence checks do not match the recorded simulation")
            return checks, simulation
        if expected_lesson_id == PLUGIN_AUDIT_LESSON_ID:
            checks = validate_t18_evidence_checks(document["evidence"])
            expected_checks, audit = validate_t18_audit(
                value.get("audit"), document_result=document["result"]
            )
            if checks != expected_checks:
                raise EvidenceError("T18 evidence checks do not match the recorded audit")
            return checks, audit
        if expected_lesson_id == MCP_CALL_LESSON_ID:
            checks, experiment = validate_t20_experiment(
                value.get("experiment"), document_result=document["result"]
            )
            return checks, experiment
        if expected_lesson_id == T26_OFFLINE_AGENT_LOOP_LESSON_ID:
            checks = validate_t26_evidence_checks(document["evidence"])
            experiment = validate_t26_experiment(
                value.get("experiment"),
                checks=checks,
                document_result=document["result"],
            )
            return checks, experiment
        if expected_lesson_id == MULTI_AGENT_LESSON_ID:
            checks = validate_multi_agent_evidence_checks(document["evidence"])
            expected_checks, experiment = validate_multi_agent_experiment(
                value.get("experiment"), document_result=document["result"]
            )
            if checks != expected_checks:
                raise EvidenceError("T22 evidence checks do not match the recorded comparison")
            return checks, experiment
        if expected_lesson_id == PRODUCTION_LESSON_ID:
            checks, experiment = validate_production_fixture(
                {
                    "evaluation": value.get("evaluation"),
                    "logs": value.get("logs"),
                },
                document_result=document["result"],
            )
            supplied_checks = validate_production_evidence_checks(document["evidence"])
            if checks != supplied_checks:
                raise EvidenceError("T29 evidence checks do not match the evaluation")
            return checks, experiment
        return document["evidence"], None
    if expected_lesson_id == MCP_DISCOVERY_LESSON_ID:
        return validate_mcp_discovery(value)
    checks = value.get("checks")
    if not isinstance(checks, list):
        raise EvidenceError("Evidence fixture checks must be a list")
    if expected_lesson_id == "t02-agent-loop":
        checks = validate_t02_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        trace = validate_t02_trace(value.get("trace"), document_result=result)
        validate_t02_check_semantics(checks, trace, document_result=result)
        return checks, trace
    if expected_lesson_id == "t03-agent-instruction":
        checks = validate_t03_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        return checks, validate_t03_experiment(
            value.get("experiment"),
            checks=checks,
            document_result=result,
        )
    if expected_lesson_id == CONTEXT_BUDGET_LESSON_ID:
        checks = validate_t14_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        expected_checks, simulation = validate_t14_simulation(
            value.get("simulation"), document_result=result
        )
        if checks != expected_checks:
            raise EvidenceError("T14 evidence checks do not match the recorded simulation")
        return checks, simulation
    if expected_lesson_id == HOOKS_TASKS_LESSON_ID:
        checks = validate_hooks_tasks_checks(checks)
        expected_checks, experiment = validate_hooks_tasks_experiment(
            value.get("experiment"),
            document_result=classify_checks([check["result"] for check in checks]),
        )
        if checks != expected_checks:
            raise EvidenceError("T21 evidence checks do not match the recorded experiment")
        return checks, experiment
    if expected_lesson_id == CLAUDE_MIGRATION_LESSON_ID:
        return load_claude_migration_checks(
            evidence_file,
            expected_course_version=expected_course_version,
        )
    if expected_lesson_id == T15_CONTEXT_RECOVERY_LESSON_ID:
        checks = validate_t15_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        return checks, validate_t15_experiment(
            value.get("experiment"),
            checks=checks,
            document_result=result,
        )
    if expected_lesson_id == MEMORY_LESSON_ID:
        checks = validate_t16_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        expected_checks, experiment = validate_t16_experiment(
            value.get("experiment"), document_result=result
        )
        if checks != expected_checks:
            raise EvidenceError("T16 evidence checks do not match the recorded Memory experiment")
        return checks, experiment
    if expected_lesson_id == SKILL_LESSON_ID:
        checks = validate_skill_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        expected_checks, simulation = validate_skill_simulation(
            value.get("simulation"),
            document_result=result,
            package_result=skill_package_check,
        )
        if checks != expected_checks:
            raise EvidenceError("T17 Skill evidence checks do not match the recorded simulation")
        return checks, simulation
    if expected_lesson_id == PLUGIN_AUDIT_LESSON_ID:
        checks = validate_t18_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        expected_checks, audit = validate_t18_audit(
            value.get("audit"), document_result=result
        )
        if checks != expected_checks:
            raise EvidenceError("T18 evidence checks do not match the recorded audit")
        return checks, audit
    if expected_lesson_id == MCP_CALL_LESSON_ID:
        result = classify_checks([check["result"] for check in checks])
        return validate_t20_experiment(value.get("experiment"), document_result=result)
    if expected_lesson_id == T26_OFFLINE_AGENT_LOOP_LESSON_ID:
        checks = validate_t26_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        return checks, validate_t26_experiment(
            value.get("experiment"),
            checks=checks,
            document_result=result,
        )
    if expected_lesson_id == MULTI_AGENT_LESSON_ID:
        checks = validate_multi_agent_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        expected_checks, experiment = validate_multi_agent_experiment(
            value.get("experiment"), document_result=result
        )
        if checks != expected_checks:
            raise EvidenceError("T22 evidence checks do not match the recorded comparison")
        return checks, experiment
    if expected_lesson_id == PRODUCTION_LESSON_ID:
        result = classify_checks([check["result"] for check in checks])
        expected_checks, experiment = validate_production_fixture(
            {
                "evaluation": value.get("evaluation"),
                "logs": value.get("logs"),
            },
            document_result=result,
        )
        supplied_checks = validate_production_evidence_checks(checks)
        if supplied_checks != expected_checks:
            raise EvidenceError("T29 evidence checks do not match the evaluation")
        return supplied_checks, experiment
    return checks, None


def load_environment_checks(
    evidence_file: Path,
) -> list[dict[str, Any]]:
    """Validate the complete, status-only environment diagnostic shape."""

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Evidence fixture must be a JSON object")

    if value.get("lesson_id") != ENVIRONMENT_LESSON_ID:
        raise EvidenceError("Environment fixture lesson_id does not match the requested lesson")
    platform = value.get("platform")
    shell = value.get("shell")
    if not isinstance(platform, str) or platform not in ENVIRONMENT_PLATFORM_SHELLS:
        raise EvidenceError("Environment fixture platform must be windows, macos, or linux")
    if not isinstance(shell, str) or shell not in ENVIRONMENT_PLATFORM_SHELLS[platform]:
        raise EvidenceError("Environment fixture shell does not match its platform")

    checks = value.get("checks")
    if not isinstance(checks, list):
        raise EvidenceError("Environment fixture checks must be a list")
    if any(not isinstance(check, dict) for check in checks):
        raise EvidenceError("Environment fixture checks must contain objects")
    check_ids = [check.get("id") for check in checks]
    if any(not isinstance(check_id, str) or not check_id for check_id in check_ids):
        raise EvidenceError("Environment fixture check ids must be non-empty strings")
    if len(check_ids) != len(set(check_ids)):
        raise EvidenceError("Environment fixture checks must not repeat an id")
    actual_ids = set(check_ids)
    missing = sorted(ENVIRONMENT_CHECK_IDS - actual_ids)
    unknown = sorted(actual_ids - ENVIRONMENT_CHECK_IDS)
    if missing or unknown or len(checks) != len(ENVIRONMENT_CHECK_IDS):
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unknown:
            details.append("unknown: " + ", ".join(str(item) for item in unknown))
        raise EvidenceError("Environment fixture checks are incomplete or unexpected (" + "; ".join(details) + ")")
    return checks


def load_git_safety_checks(
    evidence_file: Path,
) -> list[dict[str, Any]]:
    """Validate a stage trace produced by the read-only Git safety lab.

    A clean repository and a hand-written list of eight ``passed`` values are
    not sufficient evidence.  The local PowerShell script records a fixed,
    ordered sequence of observations while the learner moves through the
    disposable repository.  This function validates that sequence and derives
    the eight public checks from the stage outcomes instead of trusting a
    caller-supplied status summary.  Paths, hashes, commit messages and other
    local details never cross the browser seam.
    """

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Evidence fixture must be a JSON object")

    if value.get("lesson_id") != GIT_SAFETY_LESSON_ID:
        raise EvidenceError("Git safety fixture lesson_id does not match the requested lesson")
    platform = value.get("platform")
    shell = value.get("shell")
    if not isinstance(platform, str) or platform not in ENVIRONMENT_PLATFORM_SHELLS:
        raise EvidenceError("Git safety fixture platform must be windows, macos, or linux")
    if not isinstance(shell, str) or shell not in ENVIRONMENT_PLATFORM_SHELLS[platform]:
        raise EvidenceError("Git safety fixture shell does not match its platform")

    journey = value.get("journey")
    if not isinstance(journey, dict):
        raise EvidenceError(
            "Git safety fixture requires a stage journey; final repository state alone is insufficient"
        )
    _reject_sensitive_unknown_fields(journey, "Git safety journey")
    required_journey_fields = {"trace_version", "trace_id", "stages"}
    missing_journey_fields = sorted(required_journey_fields - set(journey))
    if missing_journey_fields:
        raise EvidenceError(
            "Git safety journey is missing: " + ", ".join(missing_journey_fields)
        )
    if journey["trace_version"] != "1":
        raise EvidenceError("Unsupported Git safety journey version")
    _require_identifier(journey["trace_id"], "Git safety journey.trace_id")

    stages = journey["stages"]
    if not isinstance(stages, list) or len(stages) != len(GIT_SAFETY_STAGE_IDS):
        raise EvidenceError(
            "Git safety journey must contain the complete ordered stage sequence"
        )
    stage_results: dict[str, bool] = {}
    for expected_sequence, (expected_id, raw_stage) in enumerate(
        zip(GIT_SAFETY_STAGE_IDS, stages, strict=True), start=1
    ):
        if not isinstance(raw_stage, dict):
            raise EvidenceError("Git safety journey stages must contain objects")
        _reject_sensitive_unknown_fields(raw_stage, f"Git safety stage {expected_id}")
        required_stage_fields = {"id", "sequence", "result", "observations"}
        missing_stage_fields = sorted(required_stage_fields - set(raw_stage))
        if missing_stage_fields:
            raise EvidenceError(
                f"Git safety stage {expected_id} is missing: "
                + ", ".join(missing_stage_fields)
            )
        if raw_stage["id"] != expected_id:
            raise EvidenceError("Git safety journey stages are out of order")
        if raw_stage["sequence"] != expected_sequence:
            raise EvidenceError("Git safety journey stage sequence is invalid")
        result = raw_stage["result"]
        if result not in {"passed", "failed"}:
            raise EvidenceError("Git safety stage result must be passed or failed")
        observations = raw_stage["observations"]
        if not isinstance(observations, dict):
            raise EvidenceError(f"Git safety stage {expected_id}.observations must be an object")
        expected_observations = GIT_SAFETY_STAGE_OBSERVATIONS[expected_id]
        actual_observations = set(observations)
        if actual_observations != expected_observations:
            missing = sorted(expected_observations - actual_observations)
            unknown = sorted(actual_observations - expected_observations)
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unknown:
                details.append("unknown: " + ", ".join(unknown))
            raise EvidenceError(
                f"Git safety stage {expected_id}.observations are incomplete or unexpected ("
                + "; ".join(details)
                + ")"
            )
        if any(not isinstance(item, bool) for item in observations.values()):
            raise EvidenceError(f"Git safety stage {expected_id}.observations must be booleans")
        computed_result = "passed" if all(observations.values()) else "failed"
        if result != computed_result:
            raise EvidenceError(f"Git safety stage {expected_id}.result does not match observations")
        stage_results[expected_id] = result == "passed"

    derived_checks = [
        {
            "id": "status-baseline",
            "result": "passed" if stage_results["baseline"] else "failed",
        },
        {
            "id": "diff-reviewed",
            "result": (
                "passed"
                if stage_results["change-created"] and stage_results["selective-stage"]
                else "failed"
            ),
        },
        {
            "id": "selective-stage",
            "result": "passed" if stage_results["selective-stage"] else "failed",
        },
        {
            "id": "intentional-commit",
            "result": (
                "passed"
                if all(
                    stage_results[stage_id]
                    for stage_id in (
                        "first-commit-decision",
                        "first-commit-recorded",
                        "secret-commit-decision",
                        "secret-commit-recorded",
                    )
                )
                else "failed"
            ),
        },
        {
            "id": "branch-inspected",
            "result": "passed" if stage_results["branch-history"] else "failed",
        },
        {
            "id": "history-inspected",
            "result": "passed" if stage_results["branch-history"] else "failed",
        },
        {
            "id": "secret-ignored",
            "result": (
                "passed"
                if stage_results["secret-before"] and stage_results["secret-ignored"]
                else "failed"
            ),
        },
        {
            "id": "recovery-complete",
            "result": (
                "passed"
                if all(
                    stage_results[stage_id]
                    for stage_id in ("recovery-before", "recovery-recorded", "final")
                )
                else "failed"
            ),
        },
    ]

    checks = value.get("checks")
    if not isinstance(checks, list):
        raise EvidenceError("Git safety fixture checks must be a list")
    if any(not isinstance(check, dict) for check in checks):
        raise EvidenceError("Git safety fixture checks must contain objects")
    for index, check in enumerate(checks):
        _reject_sensitive_unknown_fields(check, f"Git safety check {index}")
    check_ids = [check.get("id") for check in checks]
    if any(not isinstance(check_id, str) or not check_id for check_id in check_ids):
        raise EvidenceError("Git safety fixture check ids must be non-empty strings")
    if len(check_ids) != len(set(check_ids)):
        raise EvidenceError("Git safety fixture checks must not repeat an id")
    actual_ids = set(check_ids)
    if actual_ids != GIT_SAFETY_CHECK_IDS or len(checks) != len(GIT_SAFETY_CHECK_IDS):
        missing = sorted(GIT_SAFETY_CHECK_IDS - actual_ids)
        unknown = sorted(actual_ids - GIT_SAFETY_CHECK_IDS)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unknown:
            details.append("unknown: " + ", ".join(str(item) for item in unknown))
        raise EvidenceError(
            "Git safety fixture checks are incomplete or unexpected ("
            + "; ".join(details)
            + ")"
        )
    supplied_results = {check["id"]: check.get("result") for check in checks}
    derived_results = {check["id"]: check["result"] for check in derived_checks}
    if supplied_results != derived_results:
        raise EvidenceError("Git safety checks do not match the recorded stage journey")
    return derived_checks


def load_codex_task_checks(
    evidence_file: Path,
    *,
    expected_course_version: str,
) -> list[dict[str, Any]]:
    """Validate the ordered, status-only evidence for the Codex repository lab.

    The fixture records the learner's local checkpoint journey, but the public
    checker output keeps only stable check IDs and result states.  In
    particular, paths, hashes, command output, report contents, and any
    account or credential fields are never copied into the browser contract.
    """

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Codex task fixture must be a JSON object")

    document = validate_evidence_document(value)
    if document["lesson_id"] != CODEX_TASK_LESSON_ID:
        raise EvidenceError("Codex task fixture lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("Codex task fixture course_version does not match the current course")

    if value.get("task_id") != CODEX_TASK_ID:
        raise EvidenceError("Codex task fixture task_id is unsupported")
    if value.get("platform") != "windows" or value.get("shell") != "powershell":
        raise EvidenceError("Codex task fixture must identify the Windows PowerShell path")

    journey = value.get("journey")
    if not isinstance(journey, dict):
        raise EvidenceError("Codex task fixture requires a checkpoint journey")
    _reject_sensitive_unknown_fields(journey, "Codex task journey")
    required_journey_fields = {"trace_version", "trace_id", "stages"}
    missing_journey_fields = sorted(required_journey_fields - set(journey))
    if missing_journey_fields:
        raise EvidenceError(
            "Codex task journey is missing: " + ", ".join(missing_journey_fields)
        )
    if journey["trace_version"] != CODEX_TASK_TRACE_VERSION:
        raise EvidenceError("Unsupported Codex task journey version")
    _require_identifier(journey["trace_id"], "Codex task journey.trace_id")

    stages = journey["stages"]
    if not isinstance(stages, list) or len(stages) != len(CODEX_TASK_STAGE_IDS):
        raise EvidenceError("Codex task journey must contain the complete ordered stage sequence")
    stage_results: dict[str, bool] = {}
    for expected_sequence, (expected_id, raw_stage) in enumerate(
        zip(CODEX_TASK_STAGE_IDS, stages, strict=True), start=1
    ):
        if not isinstance(raw_stage, dict):
            raise EvidenceError("Codex task journey stages must contain objects")
        _reject_sensitive_unknown_fields(raw_stage, f"Codex task stage {expected_id}")
        required_stage_fields = {"id", "sequence", "result", "observations"}
        missing_stage_fields = sorted(required_stage_fields - set(raw_stage))
        if missing_stage_fields:
            raise EvidenceError(
                f"Codex task stage {expected_id} is missing: "
                + ", ".join(missing_stage_fields)
            )
        if raw_stage["id"] != expected_id:
            raise EvidenceError("Codex task journey stages are out of order")
        if raw_stage["sequence"] != expected_sequence:
            raise EvidenceError("Codex task journey stage sequence is invalid")
        result = raw_stage["result"]
        if result not in {"passed", "failed"}:
            raise EvidenceError("Codex task stage result must be passed or failed")
        observations = raw_stage["observations"]
        if not isinstance(observations, dict):
            raise EvidenceError(f"Codex task stage {expected_id}.observations must be an object")
        expected_observations = CODEX_TASK_STAGE_OBSERVATIONS[expected_id]
        actual_observations = set(observations)
        if actual_observations != expected_observations:
            missing = sorted(expected_observations - actual_observations)
            unknown = sorted(actual_observations - expected_observations)
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unknown:
                details.append("unknown: " + ", ".join(unknown))
            raise EvidenceError(
                f"Codex task stage {expected_id}.observations are incomplete or unexpected ("
                + "; ".join(details)
                + ")"
            )
        if any(not isinstance(item, bool) for item in observations.values()):
            raise EvidenceError(f"Codex task stage {expected_id}.observations must be booleans")
        computed_result = "passed" if all(observations.values()) else "failed"
        if result != computed_result:
            raise EvidenceError(f"Codex task stage {expected_id}.result does not match observations")
        stage_results[expected_id] = result == "passed"

    artifact = value.get("artifact")
    if not isinstance(artifact, dict):
        raise EvidenceError("Codex task fixture requires an artifact status object")
    _reject_sensitive_unknown_fields(artifact, "Codex task artifact")
    required_artifact_fields = {"version", "report", "tests", "delivery"}
    missing_artifact_fields = sorted(required_artifact_fields - set(artifact))
    if missing_artifact_fields:
        raise EvidenceError(
            "Codex task artifact is missing: " + ", ".join(missing_artifact_fields)
        )
    if artifact["version"] != "1":
        raise EvidenceError("Unsupported Codex task artifact version")
    expected_artifact = {
        "report": "passed" if stage_results["recovery"] else "failed",
        "tests": "passed" if stage_results["recovery"] else "failed",
        "delivery": "passed" if stage_results["delivery"] else "failed",
    }
    for field, expected in expected_artifact.items():
        if artifact[field] != expected:
            raise EvidenceError(f"Codex task artifact.{field} does not match the journey")

    derived_checks = [
        {
            "id": "clarification-recorded",
            "result": "passed" if stage_results["clarify"] else "failed",
        },
        {
            "id": "plan-recorded",
            "result": "passed" if stage_results["plan"] else "failed",
        },
        {
            "id": "failure-recovered",
            "result": (
                "passed"
                if stage_results["failure-observed"] and stage_results["recovery"]
                else "failed"
            ),
        },
        {
            "id": "scoped-change",
            "result": "passed" if stage_results["change"] and stage_results["review"] else "failed",
        },
        {
            "id": "tests-passed",
            "result": "passed" if stage_results["recovery"] else "failed",
        },
        {
            "id": "diff-reviewed",
            "result": "passed" if stage_results["review"] else "failed",
        },
        {
            "id": "report-generated",
            "result": (
                "passed"
                if stage_results["recovery"] and stage_results["delivery"]
                else "failed"
            ),
        },
        {
            "id": "delivery-recorded",
            "result": "passed" if stage_results["delivery"] else "failed",
        },
    ]
    supplied_checks = document["evidence"]
    actual_ids = [check["id"] for check in supplied_checks]
    if actual_ids != list(CODEX_TASK_CHECK_IDS):
        raise EvidenceError(
            "Codex task evidence IDs must be exactly " + ", ".join(CODEX_TASK_CHECK_IDS)
        )
    if supplied_checks != derived_checks:
        raise EvidenceError("Codex task checks do not match the recorded checkpoint journey")
    return derived_checks


def check_lesson(
    root: Path,
    lesson_id: str,
    *,
    evidence_file: Path | None = None,
) -> dict[str, Any]:
    """Run a public lesson check and build its anonymous result."""

    if lesson_id not in {
        "t01-foundation",
        ENVIRONMENT_LESSON_ID,
        GIT_SAFETY_LESSON_ID,
        "t02-agent-loop",
        "t03-agent-instruction",
        PROJECT_RULES_LESSON_ID,
        CONTEXT_BUDGET_LESSON_ID,
        HOOKS_TASKS_LESSON_ID,
        CODEX_TASK_LESSON_ID,
        CLAUDE_MIGRATION_LESSON_ID,
        T15_CONTEXT_RECOVERY_LESSON_ID,
        MEMORY_LESSON_ID,
        SKILL_LESSON_ID,
        PLUGIN_AUDIT_LESSON_ID,
        MCP_DISCOVERY_LESSON_ID,
        MCP_CALL_LESSON_ID,
        RESEARCH_CAPSTONE_LESSON_ID,
        T26_OFFLINE_AGENT_LOOP_LESSON_ID,
        OPENAI_RESPONSES_LESSON_ID,
        RESEARCH_CAPSTONE_LESSON_ID,
        ANTHROPIC_MESSAGES_LESSON_ID,
        MULTI_AGENT_LESSON_ID,
        PRODUCTION_LESSON_ID,
    }:
        raise ContractError(f"Unsupported evidence lesson: {lesson_id}")
    course_version = validate_foundation(root)
    trace: dict[str, Any] | None = None
    if lesson_id == "t01-foundation":
        checks: list[dict[str, Any]] = [
            {"id": "course-version-lock", "result": "passed"},
            {"id": "foundation-contract", "result": "passed"},
        ]
    elif lesson_id == ENVIRONMENT_LESSON_ID:
        if evidence_file is None:
            raise EvidenceError(
                "t05-environment requires --environment-file with the local diagnostic JSON"
            )
        checks = load_environment_checks(evidence_file)
    elif lesson_id == GIT_SAFETY_LESSON_ID:
        if evidence_file is None:
            raise EvidenceError(
                "t06-git-safety requires --evidence-file with the local Git safety JSON"
            )
        checks = load_git_safety_checks(evidence_file)
    elif lesson_id == CODEX_TASK_LESSON_ID:
        checks = [
            {
                "id": "codex-task-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-3-codex-task.mdx").is_file()
                else "failed",
            },
            {
                "id": "codex-task-powershell",
                "result": "passed"
                if (root / "labs/module-3/codex-task.ps1").is_file()
                else "failed",
            },
            {
                "id": "codex-task-starter",
                "result": "passed"
                if (root / "labs/module-3/starter/TASK.md").is_file()
                else "failed",
            },
            {"id": "codex-task-evidence-executed", "result": "failed"},
        ]
        if evidence_file is not None:
            checks = load_codex_task_checks(
                evidence_file,
                expected_course_version=course_version,
            )
    elif lesson_id == "t02-agent-loop":
        checks = [
            {
                "id": "agent-loop-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-1-agent-loop.mdx").is_file()
                else "failed",
            },
            {
                "id": "agent-loop-simulator",
                "result": "passed"
                if (root / "site/src/lib/agent-loop.mjs").is_file()
                else "failed",
            },
            {
                "id": "agent-loop-trace-contract",
                "result": "passed"
                if (root / "labs/agent-loop/README.md").is_file()
                else "failed",
            },
            {
                "id": "agent-loop-trace-executed",
                "result": "failed",
            },
        ]
        if evidence_file is not None:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == PROJECT_RULES_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "project-rules-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-4-project-rules.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "project-rules-lab",
                    "result": "passed"
                    if (root / "labs/project-rules/project-rules.ps1").is_file()
                    and (root / "labs/project-rules/README.md").is_file()
                    else "failed",
                },
                {
                    "id": "project-rules-contract",
                    "result": "passed"
                    if (root / "checker/course_check/project_rules.py").is_file()
                    else "failed",
                },
                {
                    "id": "project-rules-sources",
                    "result": "passed"
                    if (root / "docs/sources/source-ledger.json").is_file()
                    else "failed",
                },
                {"id": "project-rules-evidence-executed", "result": "failed"},
            ]
        else:
            checks = load_project_rules_checks(
                evidence_file,
                expected_course_version=course_version,
            )
    elif lesson_id == CONTEXT_BUDGET_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "context-budget-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-5-context-budget.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "context-budget-simulator",
                    "result": "passed"
                    if (root / "site/src/lib/context-budget.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "context-budget-contract",
                    "result": "passed"
                    if (root / "labs/context-budget/README.md").is_file()
                    else "failed",
                },
                {"id": "context-budget-evidence", "result": "failed"},
            ]
        else:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == HOOKS_TASKS_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "hooks-tasks-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-10-hooks-tasks.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "hooks-tasks-simulator",
                    "result": "passed"
                    if (root / "site/src/lib/hooks-tasks.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "hooks-tasks-contract",
                    "result": "passed"
                    if (root / "labs/hooks-tasks/README.md").is_file()
                    else "failed",
                },
                {
                    "id": "hooks-tasks-sources",
                    "result": "passed"
                    if (root / "docs/sources/source-ledger.json").is_file()
                    else "failed",
                },
                {"id": "hooks-tasks-evidence-executed", "result": "failed"},
            ]
        else:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == CLAUDE_MIGRATION_LESSON_ID:
        checks = [
            {
                "id": "claude-migration-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-3-claude-migration.mdx").is_file()
                else "failed",
            },
            {
                "id": "claude-migration-powershell",
                "result": "passed"
                if (root / "labs/module-3/claude-migration.ps1").is_file()
                else "failed",
            },
            {
                "id": "claude-migration-starter",
                "result": "passed"
                if (root / "labs/module-3/claude-starter/TASK.md").is_file()
                else "failed",
            },
            {
                "id": "claude-migration-official-facts",
                "result": "passed"
                if all(
                    token in (root / "labs/module-3/claude-starter/worklog/official-sources.md").read_text(
                        encoding="utf-8"
                    )
                    for token in (
                        "https://code.claude.com/docs/en/installation",
                        "https://code.claude.com/docs/en/permissions",
                        "https://code.claude.com/docs/en/costs",
                        "2026-08-13",
                        "not-verified",
                    )
                )
                else "failed",
            },
            {"id": "claude-migration-evidence-executed", "result": "failed"},
        ]
        if evidence_file is not None:
            checks, trace = load_claude_migration_checks(
                evidence_file,
                expected_course_version=course_version,
            )
    elif lesson_id == SKILL_LESSON_ID:
        package_check = skill_package_result(root)
        if evidence_file is None:
            checks = [
                {"id": "skill-package-shaped", "result": package_check},
                {"id": "trigger-boundary-tested", "result": "failed"},
                {"id": "evidence-scenarios-covered", "result": "failed"},
                {"id": "validation-script-passed", "result": "failed"},
                {"id": "security-boundary-tested", "result": "failed"},
                {"id": "offline-deterministic", "result": "failed"},
            ]
        else:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
                skill_package_check=package_check,
            )
    elif lesson_id == PLUGIN_AUDIT_LESSON_ID:
        checks = [
            {
                "id": "plugin-audit-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-8-plugin.mdx").is_file()
                else "failed",
            },
            {
                "id": "plugin-audit-simulator",
                "result": "passed"
                if (root / "site/src/lib/plugin-audit.mjs").is_file()
                else "failed",
            },
            {
                "id": "plugin-audit-contract",
                "result": "passed"
                if (root / "labs/plugin-audit/README.md").is_file()
                else "failed",
            },
            {
                "id": "plugin-audit-sources",
                "result": "passed"
                if (root / "docs/sources/source-ledger.json").is_file()
                else "failed",
            },
            {"id": "plugin-audit-evidence", "result": "failed"},
        ]
        if evidence_file is not None:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == MCP_DISCOVERY_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "mcp-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-9-mcp-discovery.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "mcp-server-client",
                    "result": "passed"
                    if all(
                        (root / relative).is_file()
                        for relative in (
                            "labs/mcp-discovery/mcp_server.py",
                            "labs/mcp-discovery/mcp_client.py",
                            "labs/mcp-discovery/requirements.lock",
                        )
                    )
                    else "failed",
                },
                {
                    "id": "mcp-inspector-script",
                    "result": "passed"
                    if (root / "labs/mcp-discovery/inspector-check.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "mcp-offline-fallback",
                    "result": "passed"
                    if (root / "site/src/lib/mcp-discovery.mjs").is_file()
                    and (root / "site/src/components/McpDiscoveryLab.astro").is_file()
                    else "failed",
                },
                {"id": "mcp-evidence-executed", "result": "failed"},
            ]
        else:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == MCP_CALL_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "mcp-call-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-9b-mcp-call.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "mcp-call-server",
                    "result": "passed"
                    if (root / "labs/mcp-call/server.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "mcp-call-client",
                    "result": "passed"
                    if (root / "labs/mcp-call/client.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "mcp-call-inspector",
                    "result": "passed"
                    if (root / "labs/mcp-call/inspect.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "mcp-call-contract",
                    "result": "passed"
                    if (root / "checker/tests/test_mcp_call.py").is_file()
                    else "failed",
                },
                {"id": "mcp-call-evidence", "result": "failed"},
            ]
        else:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == MULTI_AGENT_LESSON_ID:
        checks = [
            {
                "id": "multi-agent-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-10-multi-agent.mdx").is_file()
                else "failed",
            },
            {
                "id": "multi-agent-simulator",
                "result": "passed"
                if (root / "site/src/lib/multi-agent-lab.mjs").is_file()
                else "failed",
            },
            {
                "id": "multi-agent-contract",
                "result": "passed"
                if (root / "labs/multi-agent/README.md").is_file()
                else "failed",
            },
            {
                "id": "multi-agent-sources",
                "result": "passed"
                if (root / "docs/sources/source-ledger.json").is_file()
                else "failed",
            },
            {"id": "multi-agent-evidence", "result": "failed"},
        ]
        if evidence_file is not None:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == PRODUCTION_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "production-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-12-production.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "production-evaluator",
                    "result": "passed"
                    if (root / "labs/production-evaluation/evaluate.py").is_file()
                    and (root / "labs/production-evaluation/run-evaluation.ps1").is_file()
                    else "failed",
                },
                {
                    "id": "production-contract",
                    "result": "passed"
                    if (root / "labs/production-evaluation/README.md").is_file()
                    and (root / "labs/production-evaluation/rubric.json").is_file()
                    else "failed",
                },
                {
                    "id": "production-version-lock",
                    "result": "passed"
                    if (root / "course-version.json").is_file()
                    else "failed",
                },
                {"id": "production-evidence-executed", "result": "failed"},
            ]
        else:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == RESEARCH_CAPSTONE_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "research-capstone-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-12-research-capstone.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-simulator",
                    "result": "passed"
                    if (root / "site/src/lib/research-capstone.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-lab",
                    "result": "passed"
                    if (root / "labs/research-capstone/run_lab.py").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-contract",
                    "result": "passed"
                    if (root / "labs/research-capstone/README.md").is_file()
                    and (root / "checker/tests/test_research_capstone.py").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-sources",
                    "result": "passed"
                    if (root / "docs/sources/source-ledger.json").is_file()
                    else "failed",
                },
                {"id": "research-capstone-evidence", "result": "failed"},
            ]
        else:
            checks, trace = load_research_capstone_checks_external(
                evidence_file,
                expected_course_version=course_version,
            )
    elif lesson_id == OPENAI_RESPONSES_LESSON_ID:
        package_check = adapter_package_result(root)
        if evidence_file is None:
            checks = [
                {"id": "openai-responses-package", "result": package_check},
                {"id": "openai-responses-evidence-executed", "result": "failed"},
                {"id": "openai-responses-live-not-claimed", "result": "passed"},
            ]
        else:
            checks, trace = load_openai_responses_checks(
                evidence_file,
                expected_course_version=course_version,
            )
    elif lesson_id == ANTHROPIC_MESSAGES_LESSON_ID:
        package_check = anthropic_messages_package_result(root)
        if evidence_file is None:
            checks = [
                {"id": "anthropic-messages-package", "result": package_check},
                {"id": "anthropic-messages-evidence-executed", "result": "failed"},
                {"id": "anthropic-messages-live-not-claimed", "result": "passed"},
            ]
        else:
            checks, trace = load_anthropic_messages_checks(
                evidence_file,
                expected_course_version=course_version,
            )
    elif lesson_id == "t03-agent-instruction":
        checks = [
            {
                "id": "instruction-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-2-agent-instruction.mdx").is_file()
                else "failed",
            },
            {
                "id": "instruction-simulator",
                "result": "passed"
                if (root / "site/src/lib/instruction-engine.mjs").is_file()
                else "failed",
            },
            {
                "id": "instruction-contract",
                "result": "passed"
                if (root / "labs/agent-instructions/README.md").is_file()
                else "failed",
            },
            {
                "id": "instruction-scenarios",
                "result": "passed"
                if all(
                    token in (root / "site/src/lib/instruction-engine.mjs").read_text(
                        encoding="utf-8"
                    )
                    for token in ("conflict", "injection", "long", "pressure-night")
                )
                else "failed",
            },
            {"id": "instruction-evidence-executed", "result": "failed"},
            {"id": "instruction-migration-executed", "result": "failed"},
        ]
        if evidence_file is not None:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == T15_CONTEXT_RECOVERY_LESSON_ID:
        checks = [
            {
                "id": "context-recovery-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-5-context-recovery.mdx").is_file()
                else "failed",
            },
            {
                "id": "context-recovery-simulator",
                "result": "passed"
                if (root / "site/src/lib/context-recovery.mjs").is_file()
                else "failed",
            },
            {
                "id": "context-recovery-contract",
                "result": "passed"
                if (root / "labs/context-recovery/README.md").is_file()
                else "failed",
            },
            {
                "id": "context-recovery-scenarios",
                "result": "passed"
                if all(
                    token in (root / "site/src/lib/context-recovery.mjs").read_text(
                        encoding="utf-8"
                    )
                    for token in (
                        "distorted",
                        "constraint-omitted",
                        "recoverPollutedTask",
                        "buildHandoffPackage",
                    )
                )
                else "failed",
            },
            {"id": "context-recovery-evidence-executed", "result": "failed"},
            {"id": "context-recovery-handoff-executed", "result": "failed"},
        ]
        if evidence_file is not None:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == MEMORY_LESSON_ID:
        checks = [
            {
                "id": "memory-page",
                "result": "passed"
                if (root / "site/src/content/docs/module-6-memory.mdx").is_file()
                else "failed",
            },
            {
                "id": "memory-simulator",
                "result": "passed"
                if (root / "site/src/lib/memory-engine.mjs").is_file()
                else "failed",
            },
            {
                "id": "memory-contract",
                "result": "passed"
                if (root / "labs/memory/README.md").is_file()
                else "failed",
            },
            {
                "id": "memory-sources",
                "result": "passed"
                if (root / "docs/sources/source-ledger.json").is_file()
                else "failed",
            },
            {
                "id": "memory-evidence-executed",
                "result": "failed",
            },
        ]
        if evidence_file is not None:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == T26_OFFLINE_AGENT_LOOP_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "offline-agent-loop-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-11-agent-loop.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "offline-agent-loop-runner",
                    "result": "passed"
                    if (root / "labs/api-agent-loop/agent_loop.py").is_file()
                    and (root / "labs/api-agent-loop/run.py").is_file()
                    else "failed",
                },
                {
                    "id": "offline-agent-loop-contract",
                    "result": "passed"
                    if (root / "labs/api-agent-loop/README.md").is_file()
                    else "failed",
                },
                {
                    "id": "offline-agent-loop-checker",
                    "result": "passed"
                    if (root / "checker/tests/test_api_agent_loop.py").is_file()
                    else "failed",
                },
                {
                    "id": "offline-agent-loop-sources",
                    "result": "passed"
                    if (root / "docs/sources/source-ledger.json").is_file()
                    else "failed",
                },
                {"id": "offline-agent-loop-evidence-executed", "result": "failed"},
            ]
        else:
            checks, trace = load_evidence_checks(
                evidence_file,
                expected_lesson_id=lesson_id,
                expected_course_version=course_version,
            )
    elif lesson_id == RESEARCH_CAPSTONE_LESSON_ID:
        if evidence_file is None:
            checks = [
                {
                    "id": "research-capstone-page",
                    "result": "passed"
                    if (root / "site/src/content/docs/module-12-research-capstone.mdx").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-simulator",
                    "result": "passed"
                    if (root / "site/src/lib/research-capstone.mjs").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-lab",
                    "result": "passed"
                    if (root / "labs/research-capstone/run_lab.py").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-contract",
                    "result": "passed"
                    if (root / "labs/research-capstone/README.md").is_file()
                    and (root / "checker/tests/test_research_capstone.py").is_file()
                    else "failed",
                },
                {
                    "id": "research-capstone-sources",
                    "result": "passed"
                    if (root / "docs/sources/source-ledger.json").is_file()
                    else "failed",
                },
                {"id": "research-capstone-evidence", "result": "failed"},
            ]
        else:
            checks, trace = load_research_capstone_checks_external(
                evidence_file,
                expected_course_version=course_version,
            )
    if lesson_id == "t01-foundation" and evidence_file is not None:
        checks, trace = load_evidence_checks(
            evidence_file,
            expected_lesson_id=lesson_id,
            expected_course_version=course_version,
        )
    document = build_evidence_document(
        course_version=course_version,
        lesson_id=lesson_id,
        checks=checks,
    )
    if trace is not None:
        if lesson_id == "t02-agent-loop":
            document["trace"] = trace
        elif lesson_id == CONTEXT_BUDGET_LESSON_ID:
            document["simulation"] = trace
        elif lesson_id == SKILL_LESSON_ID:
            document["simulation"] = trace
        elif lesson_id == PLUGIN_AUDIT_LESSON_ID:
            document["audit"] = trace
        elif lesson_id == MCP_DISCOVERY_LESSON_ID:
            document["mcp"] = trace
        elif lesson_id == MCP_CALL_LESSON_ID:
            document["experiment"] = trace
        elif lesson_id == HOOKS_TASKS_LESSON_ID:
            document["experiment"] = trace
        elif lesson_id == PRODUCTION_LESSON_ID:
            document["evaluation"] = trace["evaluation"]
            document["logs"] = trace["logs"]
        else:
            document["experiment"] = trace
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="course_check")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate course contracts")
    validate.add_argument("--root", type=Path, required=True)
    check = subparsers.add_parser(
        "check", help="check a lesson and emit an anonymous evidence document"
    )
    check.add_argument("lesson_id")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument(
        "--evidence-file",
        "--environment-file",
        "--git-safety-file",
        "--git-file",
        dest="evidence_file",
        type=Path,
        help=(
            "local fixture containing lesson_id and check result states; "
            "use --environment-file for t05-environment or the Git safety fixture for t06-git-safety"
        ),
    )
    check.add_argument(
        "--output",
        type=Path,
        help="write the anonymous evidence JSON to this path",
    )
    check.add_argument(
        "--json",
        action="store_true",
        help="print the anonymous evidence JSON instead of only a human summary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # JSON evidence is a UTF-8 interchange contract.  Windows PowerShell
    # runners may expose a legacy cp1252 stdout, which cannot encode the
    # course's Chinese lesson labels.  Reconfigure the stream at the public
    # CLI boundary so ``--json`` behaves identically across platforms.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="strict")
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        try:
            version = validate_foundation(args.root.resolve())
        except ContractError as exc:
            print(f"Foundation validation failed: {exc}", file=sys.stderr)
            return 1
        print(f"Foundation validation passed: {version}")
        return 0
    if args.command == "check":
        try:
            document = check_lesson(
                args.root.resolve(),
                args.lesson_id,
                evidence_file=args.evidence_file.resolve()
                if args.evidence_file is not None
                else None,
            )
            encoded = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
            if args.output is not None:
                args.output.resolve().write_text(encoded, encoding="utf-8")
            if args.json:
                print(encoded, end="")
            else:
                print(
                    f"Evidence check {document['result']}: "
                    f"{document['lesson_id']} ({document['course_version']})"
                )
            return 0
        except (ContractError, EvidenceError, OSError) as exc:
            print(f"Evidence check failed: {exc}", file=sys.stderr)
            return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
