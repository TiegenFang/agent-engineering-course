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


def load_evidence_checks(
    evidence_file: Path, *, expected_lesson_id: str, expected_course_version: str
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
        document = validate_evidence_document(value)
        if expected_lesson_id == "t02-agent-loop":
            checks = validate_t02_evidence_checks(document["evidence"])
            trace = validate_t02_trace(value.get("trace"), document_result=document["result"])
            validate_t02_check_semantics(checks, trace, document_result=document["result"])
            return checks, trace
        return document["evidence"], None
    checks = value.get("checks")
    if not isinstance(checks, list):
        raise EvidenceError("Evidence fixture checks must be a list")
    if expected_lesson_id == "t02-agent-loop":
        checks = validate_t02_evidence_checks(checks)
        result = classify_checks([check["result"] for check in checks])
        trace = validate_t02_trace(value.get("trace"), document_result=result)
        validate_t02_check_semantics(checks, trace, document_result=result)
        return checks, trace
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
    else:
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
        document["trace"] = trace
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
