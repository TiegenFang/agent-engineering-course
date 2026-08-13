"""Deterministic checker for the T31 enterprise API capstone.

The capstone models one bounded Issue-to-PR sub-step: an API Agent may draft a
validation plan, but it may not merge, push, publish, or otherwise mutate the
repository.  The fixture is intentionally provider-free and offline.  Its
public evidence contains only status and aggregate cost fields; it never
crosses prompts, tool payloads, paths, credentials, or source text.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .evidence import (
    EvidenceError,
    _reject_sensitive_unknown_fields,
    _require_identifier,
    classify_checks,
    validate_evidence_document,
)


ENTERPRISE_API_LESSON_ID = "t31-enterprise-api"
ENTERPRISE_API_VERSION = "1"
ENTERPRISE_API_BASELINE_ID = "issue-to-pr-api-v1"
ENTERPRISE_API_RUNNER_VERSION = "enterprise-api-runner-v1"
ENTERPRISE_API_CHECK_IDS = (
    "scope-bounded",
    "approval-gated",
    "structured-output",
    "budget-enforced",
    "recovery-observed",
    "evidence-redacted",
    "offline-deterministic",
)

_EXPERIMENT_FIELDS = {
    "version",
    "baseline_id",
    "input_id",
    "requested_action",
    "high_impact_action",
    "approval_required",
    "approval_granted",
    "high_impact_executed",
    "side_effect",
    "structured_output_valid",
    "output_schema_version",
    "failure_injected",
    "failure_class",
    "recovered",
    "recovery_action",
    "budget_usd",
    "estimated_cost_usd",
    "budget_status",
    "model_call_started",
    "provider",
    "model",
    "live_api_called",
    "public_summary_only",
    "runner_version",
}

_IDENTIFIER_FIELDS = {
    "baseline_id",
    "input_id",
    "output_schema_version",
    "provider",
    "model",
    "runner_version",
}


def _as_non_negative_number(value: Any, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        raise EvidenceError(f"T31 {field} must be a non-negative number")
    return float(value)


def _derive_checks(experiment: dict[str, Any]) -> list[dict[str, str]]:
    scope_bounded = (
        experiment["requested_action"] == "draft-validation-plan"
        and experiment["high_impact_action"] == "merge-or-push"
        and experiment["high_impact_executed"] is False
        and experiment["side_effect"] == "none"
    )
    approval_gated = (
        experiment["approval_required"] is True
        and (
            experiment["high_impact_executed"] is False
            or experiment["approval_granted"] is True
        )
    )
    structured = (
        experiment["structured_output_valid"] is True
        and experiment["output_schema_version"] == "issue-plan-v1"
    )
    estimate = float(experiment["estimated_cost_usd"])
    budget = float(experiment["budget_usd"])
    budget_enforced = (
        experiment["budget_status"] == "allowed"
        and estimate <= budget
        and experiment["model_call_started"] is True
    ) or (
        experiment["budget_status"] == "stopped"
        and estimate > budget
        and experiment["model_call_started"] is False
    )
    recovery = (
        experiment["failure_injected"] is True
        and experiment["failure_class"] in {"tool-timeout", "invalid-output"}
        and experiment["recovered"] is True
        and experiment["recovery_action"] == "bounded-retry"
    )
    redacted = (
        experiment["public_summary_only"] is True
        and experiment["live_api_called"] is False
    )
    offline = (
        experiment["provider"] == "offline-fixture"
        and experiment["model"] == "offline-model-v1"
        and experiment["live_api_called"] is False
    )
    flags = (
        scope_bounded,
        approval_gated,
        structured,
        budget_enforced,
        recovery,
        redacted,
        offline,
    )
    return [
        {"id": check_id, "result": "passed" if flag else "failed"}
        for check_id, flag in zip(ENTERPRISE_API_CHECK_IDS, flags, strict=True)
    ]


def validate_enterprise_api_experiment(
    value: Any, *, document_result: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate and recompute the public T31 experiment status."""

    if not isinstance(value, dict):
        raise EvidenceError("T31 evidence requires an experiment object")
    _reject_sensitive_unknown_fields(value, "T31 experiment")
    if set(value) != _EXPERIMENT_FIELDS:
        missing = sorted(_EXPERIMENT_FIELDS - set(value))
        unknown = sorted(set(value) - _EXPERIMENT_FIELDS)
        detail: list[str] = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unknown:
            detail.append("unknown: " + ", ".join(unknown))
        raise EvidenceError("T31 experiment fields are invalid (" + "; ".join(detail) + ")")
    if value["version"] != ENTERPRISE_API_VERSION:
        raise EvidenceError("Unsupported T31 experiment version")
    if value["baseline_id"] != ENTERPRISE_API_BASELINE_ID:
        raise EvidenceError("Unsupported T31 baseline_id")
    for field in _IDENTIFIER_FIELDS:
        identifier = value[field]
        if not isinstance(identifier, str) or not identifier:
            raise EvidenceError(f"T31 {field} must be a non-empty identifier")
        _require_identifier(identifier, f"T31 {field}")
    if value["requested_action"] != "draft-validation-plan":
        raise EvidenceError("T31 may only delegate the bounded draft-validation-plan step")
    if value["high_impact_action"] != "merge-or-push":
        raise EvidenceError("T31 high-impact action must remain merge-or-push")
    if value["side_effect"] not in {"none", "draft-only"}:
        raise EvidenceError("T31 side_effect is unsupported")
    for field in (
        "approval_required",
        "approval_granted",
        "high_impact_executed",
        "structured_output_valid",
        "failure_injected",
        "recovered",
        "model_call_started",
        "live_api_called",
        "public_summary_only",
    ):
        if not isinstance(value[field], bool):
            raise EvidenceError(f"T31 {field} must be boolean")
    if value["approval_required"] is not True:
        raise EvidenceError("T31 must require human approval for high-impact actions")
    if value["live_api_called"] is not False:
        raise EvidenceError("T31 offline evidence cannot claim a live API call")
    if value["failure_class"] not in {"tool-timeout", "invalid-output"}:
        raise EvidenceError("T31 failure_class must record a bounded recoverable fault")
    if value["recovery_action"] != "bounded-retry":
        raise EvidenceError("T31 recovery_action must be bounded-retry")
    for field in ("budget_usd", "estimated_cost_usd"):
        _as_non_negative_number(value[field], field)
    if value["budget_status"] not in {"allowed", "stopped"}:
        raise EvidenceError("T31 budget_status must be allowed or stopped")
    if value["provider"] != "offline-fixture" or value["model"] != "offline-model-v1":
        raise EvidenceError("T31 fixture provider/model are unsupported")
    if value["runner_version"] != ENTERPRISE_API_RUNNER_VERSION:
        raise EvidenceError("Unsupported T31 runner version")

    checks = _derive_checks(value)
    if document_result == "passed" and any(check["result"] != "passed" for check in checks):
        raise EvidenceError("Completed T31 evidence is missing one or more gates")
    return checks, {
        key: value[key]
        for key in sorted(_EXPERIMENT_FIELDS)
        if key not in {"estimated_cost_usd", "budget_usd"}
    } | {
        "budget_usd": round(float(value["budget_usd"]), 6),
        "estimated_cost_usd": round(float(value["estimated_cost_usd"]), 6),
    }


def validate_enterprise_api_evidence_checks(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) != len(ENTERPRISE_API_CHECK_IDS):
        raise EvidenceError("T31 evidence must contain the complete fixed check list")
    normalized: list[dict[str, str]] = []
    actual_ids: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EvidenceError(f"T31 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(item, f"T31 evidence check {index}")
        if set(item) != {"id", "result"}:
            raise EvidenceError(f"T31 evidence check {index} must contain only id and result")
        check_id = item["id"]
        result = item["result"]
        if check_id not in ENTERPRISE_API_CHECK_IDS:
            raise EvidenceError(f"T31 evidence check {index} has an unsupported id")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T31 evidence check {check_id} has an unsupported result")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})
    if actual_ids != list(ENTERPRISE_API_CHECK_IDS):
        raise EvidenceError("T31 evidence IDs must be in the fixed order")
    return normalized


def load_enterprise_api_checks(
    evidence_file: Path, *, expected_course_version: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"T31 evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid T31 evidence JSON: {exc.msg}") from exc
    document = validate_evidence_document(value)
    if document["lesson_id"] != ENTERPRISE_API_LESSON_ID:
        raise EvidenceError("T31 evidence lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("T31 evidence course_version does not match the current course")
    checks, experiment = validate_enterprise_api_experiment(
        value.get("experiment"), document_result=document["result"]
    )
    supplied = validate_enterprise_api_evidence_checks(document["evidence"])
    if supplied != checks:
        raise EvidenceError("T31 evidence checks do not match the experiment")
    expected_result = classify_checks([check["result"] for check in checks])
    if document["result"] != expected_result:
        raise EvidenceError("T31 evidence result does not match its checks")
    return checks, experiment
