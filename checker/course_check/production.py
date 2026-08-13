"""Status-only validator for the T29 production evaluation seam."""

from __future__ import annotations

import math
from typing import Any

from .evidence import EvidenceError, _reject_sensitive_unknown_fields, _require_identifier


PRODUCTION_LESSON_ID = "t29-production"
PRODUCTION_EVALUATOR_VERSION = "production-evaluator-v1"
PRODUCTION_FIXTURE_VERSION = "1"
PRODUCTION_CHECK_IDS = (
    "success-case",
    "failure-case",
    "variant-input",
    "recovery-observed",
    "budget-gate",
    "log-redaction",
)
PRODUCTION_LOG_EVENTS = frozenset(
    {"evaluation-start", "case-result", "recovery", "budget-stop", "evaluation-end"}
)


def _checks(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) != len(PRODUCTION_CHECK_IDS):
        raise EvidenceError("T29 evidence checks must contain the complete fixed check list")
    normalized: list[dict[str, str]] = []
    actual: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EvidenceError(f"T29 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(item, f"T29 evidence check {index}")
        if set(item) != {"id", "result"}:
            raise EvidenceError(f"T29 evidence check {index} must contain only id and result")
        check_id = item.get("id")
        result = item.get("result")
        if not isinstance(check_id, str) or check_id not in PRODUCTION_CHECK_IDS:
            raise EvidenceError(f"T29 evidence check {index} has an unsupported id")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T29 evidence check {check_id} has an unsupported result")
        actual.append(check_id)
        normalized.append({"id": check_id, "result": result})
    if actual != list(PRODUCTION_CHECK_IDS):
        raise EvidenceError("T29 evidence IDs must be exactly " + ", ".join(PRODUCTION_CHECK_IDS))
    return normalized


def validate_production_evidence_checks(value: Any) -> list[dict[str, str]]:
    return _checks(value)


def validate_production_evaluation(
    value: Any, *, document_result: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate public aggregate evidence without accepting raw evaluation data."""

    if not isinstance(value, dict):
        raise EvidenceError("T29 evidence requires an evaluation object")
    # Aggregate token counts are deliberately allowed public metrics.  The
    # shared privacy guard rejects arbitrary token fields, so exempt only
    # these two fixed names; raw token values and credentials remain banned.
    _reject_sensitive_unknown_fields(
        {
            key: item
            for key, item in value.items()
            if key not in {"estimated_input_tokens", "estimated_output_tokens"}
        },
        "T29 evaluation",
    )
    expected = {
        "evaluator_version",
        "fixture_version",
        "input_id",
        "cases_total",
        "cases_passed",
        "success_case_passed",
        "failure_case_observed",
        "variant_input_passed",
        "recovery_observed",
        "failures_recovered",
        "estimated_input_tokens",
        "estimated_output_tokens",
        "estimated_cost_usd",
        "budget_usd",
        "budget_status",
        "provider",
        "model",
        "live_api_called",
    }
    if set(value) != expected:
        raise EvidenceError("T29 evaluation must contain exactly the status and aggregate fields")
    if value["evaluator_version"] != PRODUCTION_EVALUATOR_VERSION:
        raise EvidenceError("Unsupported T29 evaluator version")
    if value["fixture_version"] != PRODUCTION_FIXTURE_VERSION:
        raise EvidenceError("Unsupported T29 fixture version")
    for field in ("input_id", "provider", "model"):
        if not isinstance(value[field], str) or not value[field]:
            raise EvidenceError(f"T29 {field} must be a non-empty identifier")
        _require_identifier(value[field], f"T29 {field}")
    if value["provider"] != "offline-fixture":
        raise EvidenceError("T29 evaluator must use the offline fixture provider")
    if value["live_api_called"] is not False:
        raise EvidenceError("T29 evidence cannot claim a live API call")
    for field in (
        "cases_total",
        "cases_passed",
        "failures_recovered",
        "estimated_input_tokens",
        "estimated_output_tokens",
    ):
        number = value[field]
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            raise EvidenceError(f"T29 {field} must be a non-negative integer")
    for field in ("estimated_cost_usd", "budget_usd"):
        number = value[field]
        if (
            not isinstance(number, (int, float))
            or isinstance(number, bool)
            or not math.isfinite(number)
            or number < 0
        ):
            raise EvidenceError(f"T29 {field} must be a non-negative number")
    if value["cases_total"] != 3 or value["cases_passed"] > value["cases_total"]:
        raise EvidenceError("T29 case totals are inconsistent")
    if value["failures_recovered"] > 1:
        raise EvidenceError("T29 recovery count is inconsistent")
    if value["budget_status"] not in {"allowed", "stopped"}:
        raise EvidenceError("T29 budget status is unsupported")
    if value["budget_status"] == "allowed" and value["estimated_cost_usd"] > value["budget_usd"]:
        raise EvidenceError("T29 allowed budget status contradicts the estimated cost")
    for field in ("success_case_passed", "failure_case_observed", "variant_input_passed", "recovery_observed"):
        if not isinstance(value[field], bool):
            raise EvidenceError(f"T29 {field} must be boolean")
    if value["cases_passed"] != sum(
        int(value[field]) for field in ("success_case_passed", "failure_case_observed", "variant_input_passed")
    ):
        raise EvidenceError("T29 case count does not match case statuses")
    if value["recovery_observed"] != (value["failures_recovered"] == 1):
        raise EvidenceError("T29 recovery aggregate does not match its status")

    checks = _checks(value.get("checks")) if "checks" in value else None
    if checks is not None:
        raise EvidenceError("T29 checks belong at the evidence document level")
    if document_result == "passed":
        if value["cases_passed"] != 3 or value["failures_recovered"] != 1:
            raise EvidenceError("Completed T29 evidence must pass all cases and recovery")
        if value["budget_status"] != "allowed":
            raise EvidenceError("Completed T29 evidence must pass the budget gate")

    return [], {
        "evaluator_version": value["evaluator_version"],
        "fixture_version": value["fixture_version"],
        "input_id": value["input_id"],
        "cases_total": value["cases_total"],
        "cases_passed": value["cases_passed"],
        "success_case_passed": value["success_case_passed"],
        "failure_case_observed": value["failure_case_observed"],
        "variant_input_passed": value["variant_input_passed"],
        "recovery_observed": value["recovery_observed"],
        "failures_recovered": value["failures_recovered"],
        "estimated_input_tokens": value["estimated_input_tokens"],
        "estimated_output_tokens": value["estimated_output_tokens"],
        "estimated_cost_usd": round(float(value["estimated_cost_usd"]), 6),
        "budget_usd": round(float(value["budget_usd"]), 6),
        "budget_status": value["budget_status"],
        "provider": value["provider"],
        "model": value["model"],
        "live_api_called": False,
    }


def validate_production_logs(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("T29 evidence requires a logs summary")
    _reject_sensitive_unknown_fields(value, "T29 logs")
    if set(value) != {"event_count", "events"}:
        raise EvidenceError("T29 logs must contain only event_count and events")
    count = value["event_count"]
    events = value["events"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise EvidenceError("T29 log event_count must be positive")
    if not isinstance(events, list) or len(events) != count or any(
        not isinstance(event, str) or event not in PRODUCTION_LOG_EVENTS for event in events
    ):
        raise EvidenceError("T29 logs contain an unsupported event")
    if events[0] != "evaluation-start" or events[-1] != "evaluation-end":
        raise EvidenceError("T29 logs must have explicit start and end events")
    return {"event_count": count, "events": list(events)}


def validate_production_fixture(
    value: Any, *, document_result: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not isinstance(value, dict):
        raise EvidenceError("T29 evidence fixture must be an object")
    _reject_sensitive_unknown_fields(value, "T29 fixture")
    expected = {"evaluation", "logs"}
    if set(value) != expected:
        raise EvidenceError("T29 fixture must contain evaluation and logs only")
    _, evaluation = validate_production_evaluation(
        value["evaluation"], document_result=document_result
    )
    logs = validate_production_logs(value["logs"])
    passed = (
        evaluation["cases_passed"] == evaluation["cases_total"] == 3
        and evaluation["failures_recovered"] == 1
        and evaluation["budget_status"] == "allowed"
    )
    expected_checks = [
        {"id": "success-case", "result": "passed" if evaluation["success_case_passed"] else "failed"},
        {"id": "failure-case", "result": "passed" if evaluation["failure_case_observed"] else "failed"},
        {"id": "variant-input", "result": "passed" if evaluation["variant_input_passed"] else "failed"},
        {"id": "recovery-observed", "result": "passed" if evaluation["recovery_observed"] else "failed"},
        {"id": "budget-gate", "result": "passed" if evaluation["budget_status"] == "allowed" else "failed"},
        {"id": "log-redaction", "result": "passed" if logs["events"] else "failed"},
    ]
    if document_result == "passed" and not passed:
        raise EvidenceError("Completed T29 evidence is missing evaluation gates")
    return expected_checks, {"evaluation": evaluation, "logs": logs}
