"""Status-only validation for the T27 OpenAI Responses adapter lesson.

The checker accepts only the deterministic, no-network fixture evidence.  It
does not import the OpenAI SDK, read credentials, or replay a request.  All
model text, tool arguments, tool values, request payloads, paths, and secrets
are deliberately outside this public evidence seam.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .evidence import (
    EvidenceError,
    _reject_sensitive_unknown_fields,
    _require_identifier,
    _require_iso_date,
    classify_checks,
    validate_evidence_document,
)


OPENAI_RESPONSES_LESSON_ID = "t27-openai-responses"
OPENAI_RESPONSES_VERSION = "1"
OPENAI_RESPONSES_MODEL = "gpt-5.6"
OPENAI_RESPONSES_MODE = "offline-fixture"
OPENAI_RESPONSES_CASE_ORDER = (
    "offline-success",
    "invalid-arguments",
    "malformed-structured-output",
    "transport-error",
)
OPENAI_RESPONSES_CHECK_IDS = (
    "adapter-request-shaped",
    "offline-no-credential",
    "function-call-round-trip",
    "structured-output-validated",
    "budget-owned-by-loop",
    "errors-contained",
    "live-smoke-metadata-recorded",
    "live-api-not-claimed",
)
OPENAI_RESPONSES_PACKAGE_FILES = (
    "labs/openai-responses/openai_responses_adapter.py",
    "labs/openai-responses/run_fixture.py",
    "labs/openai-responses/README.md",
    "site/src/content/docs/module-11-openai-responses.mdx",
    "site/src/lib/openai-responses.mjs",
    "site/src/components/OpenAIResponsesLab.astro",
)
_PUBLIC_DOCUMENT_FIELDS = {
    "contract",
    "contract_version",
    "course_version",
    "lesson_id",
    "result",
    "anonymous",
    "checked_on",
    "summary",
    "evidence",
}
_TOP_LEVEL_FIELDS = _PUBLIC_DOCUMENT_FIELDS | {"experiment"}
_EXPERIMENT_FIELDS = {
    "version",
    "mode",
    "adapter",
    "model",
    "network",
    "access",
    "request_budget",
    "loop_budget_owner",
    "cases",
    "live_smoke",
}
_CASE_FIELDS = {
    "id",
    "outcome",
    "request_count",
    "function_call",
    "tool_output_refilled",
    "structured_output",
    "error",
    "network",
    "access",
}
_LIVE_SMOKE_FIELDS = {"status", "sdk", "model", "verified_on", "cost", "limitations"}
_EXPECTED_CASES = {
    "offline-success": {
        "outcome": "completed",
        "request_count": 2,
        "function_call": True,
        "tool_output_refilled": True,
        "structured_output": "accepted",
        "error": "none",
    },
    "invalid-arguments": {
        "outcome": "invalid-arguments-contained",
        "request_count": 2,
        "function_call": True,
        "tool_output_refilled": True,
        "structured_output": "accepted",
        "error": "invalid-arguments",
    },
    "malformed-structured-output": {
        "outcome": "structured-output-rejected",
        "request_count": 2,
        "function_call": True,
        "tool_output_refilled": True,
        "structured_output": "rejected",
        "error": "protocol",
    },
    "transport-error": {
        "outcome": "transport-error-contained",
        "request_count": 1,
        "function_call": False,
        "tool_output_refilled": False,
        "structured_output": "not-requested",
        "error": "connection",
    },
}


def adapter_package_result(root: Path) -> str:
    """Check that the implementation, fixture, page, and browser lab exist."""

    return "passed" if all((root / relative).is_file() for relative in OPENAI_RESPONSES_PACKAGE_FILES) else "failed"


def _fixed_checks(cases: Mapping[str, Mapping[str, Any]]) -> list[dict[str, str]]:
    success = cases.get("offline-success", {})
    invalid = cases.get("invalid-arguments", {})
    malformed = cases.get("malformed-structured-output", {})
    transport = cases.get("transport-error", {})
    offline = all(
        cases.get(case_id, {}).get("network") == "not-called"
        and cases.get(case_id, {}).get("access") == "not-required"
        for case_id in OPENAI_RESPONSES_CASE_ORDER
    )
    return [
        {"id": "adapter-request-shaped", "result": "passed"},
        {"id": "offline-no-credential", "result": "passed" if offline else "failed"},
        {
            "id": "function-call-round-trip",
            "result": "passed"
            if success.get("function_call") is True
            and success.get("tool_output_refilled") is True
            and success.get("request_count") == 2
            else "failed",
        },
        {
            "id": "structured-output-validated",
            "result": "passed"
            if success.get("structured_output") == "accepted"
            and malformed.get("structured_output") == "rejected"
            else "failed",
        },
        {"id": "budget-owned-by-loop", "result": "passed"},
        {
            "id": "errors-contained",
            "result": "passed"
            if invalid.get("outcome") == "invalid-arguments-contained"
            and transport.get("outcome") == "transport-error-contained"
            else "failed",
        },
        {"id": "live-smoke-metadata-recorded", "result": "passed"},
        {"id": "live-api-not-claimed", "result": "passed"},
    ]


def _validate_checks(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) != len(OPENAI_RESPONSES_CHECK_IDS):
        raise EvidenceError("T27 evidence checks must contain the complete fixed check list")
    normalized: list[dict[str, str]] = []
    for index, raw_check in enumerate(value):
        if not isinstance(raw_check, Mapping):
            raise EvidenceError(f"T27 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(raw_check, f"T27 evidence check {index}")
        if set(raw_check) != {"id", "result"}:
            raise EvidenceError(f"T27 evidence check {index} must contain only id and result")
        check_id = raw_check["id"]
        if not isinstance(check_id, str):
            raise EvidenceError(f"T27 evidence check {index}.id must be a string")
        result = raw_check["result"]
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T27 evidence check {check_id}.result is unsupported")
        normalized.append({"id": check_id, "result": result})
    if [check["id"] for check in normalized] != list(OPENAI_RESPONSES_CHECK_IDS):
        raise EvidenceError("T27 evidence IDs must be exactly " + ", ".join(OPENAI_RESPONSES_CHECK_IDS))
    return normalized


def _strict_mapping(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceError(f"{label} must be an object")
    _reject_sensitive_unknown_fields(value, label)
    missing = sorted(fields - set(value))
    unexpected = sorted(set(value) - fields)
    if missing:
        raise EvidenceError(f"{label} is missing: " + ", ".join(missing))
    if unexpected:
        raise EvidenceError(f"{label} has unexpected fields: " + ", ".join(unexpected))
    return value


def validate_openai_responses_experiment(
    value: Any, *, document_result: str, checked_on: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate the deterministic fixture and rederive every public check."""

    experiment = _strict_mapping(value, _EXPERIMENT_FIELDS, "T27 experiment")
    if experiment["version"] != OPENAI_RESPONSES_VERSION:
        raise EvidenceError("Unsupported T27 experiment version")
    if experiment["mode"] != OPENAI_RESPONSES_MODE:
        raise EvidenceError("T27 evidence must be from the offline fixture mode")
    if experiment["adapter"] != "responses-api-sdk-boundary":
        raise EvidenceError("T27 adapter identity is unsupported")
    if experiment["model"] != OPENAI_RESPONSES_MODEL:
        raise EvidenceError("T27 model identifier does not match the verified adapter")
    if experiment["network"] != "not-called" or experiment["access"] != "not-required":
        raise EvidenceError("T27 offline fixture must not use network or credentials")
    if experiment["request_budget"] != 256 or experiment["loop_budget_owner"] != "t26-run-agent-loop":
        raise EvidenceError("T27 budget ownership does not match the adapter contract")

    raw_cases = experiment["cases"]
    if not isinstance(raw_cases, list) or len(raw_cases) != len(OPENAI_RESPONSES_CASE_ORDER):
        raise EvidenceError("T27 experiment must contain every fixed offline case")
    cases: dict[str, Mapping[str, Any]] = {}
    normalized_cases: list[dict[str, Any]] = []
    for index, raw_case in enumerate(raw_cases):
        case = _strict_mapping(raw_case, _CASE_FIELDS, f"T27 case {index}")
        case_id = _require_identifier(case["id"], f"T27 case {index}.id")
        if case_id not in _EXPECTED_CASES or case_id in cases:
            raise EvidenceError(f"T27 case {case_id} is unsupported or repeated")
        expected = _EXPECTED_CASES[case_id]
        for field, expected_value in expected.items():
            if case[field] != expected_value:
                raise EvidenceError(f"T27 case {case_id}.{field} does not match its fixture")
        if case["network"] != "not-called" or case["access"] != "not-required":
            raise EvidenceError(f"T27 case {case_id} must stay offline without credentials")
        cases[case_id] = case
        normalized_cases.append({field: case[field] for field in sorted(_CASE_FIELDS)})
    if tuple(cases) != OPENAI_RESPONSES_CASE_ORDER:
        raise EvidenceError("T27 cases must appear in the fixed fixture order")

    smoke = _strict_mapping(experiment["live_smoke"], _LIVE_SMOKE_FIELDS, "T27 live_smoke")
    if smoke["status"] != "not-run":
        raise EvidenceError("T27 fixture cannot claim that a live API smoke test ran")
    if smoke["sdk"] != "openai Python SDK not invoked" or smoke["model"] != OPENAI_RESPONSES_MODEL:
        raise EvidenceError("T27 live_smoke SDK or model metadata is unsupported")
    if _require_iso_date(smoke["verified_on"], "T27 live_smoke.verified_on") != checked_on:
        raise EvidenceError("T27 live_smoke date must match the evidence document")
    if smoke["cost"] != "not assessed; no live request was made":
        raise EvidenceError("T27 live_smoke cost must state the no-live-call boundary")
    if smoke["limitations"] != ["no-api-key-read", "no-network-request", "not-a-live-api-result"]:
        raise EvidenceError("T27 live_smoke limitations do not match the offline boundary")

    checks = _fixed_checks(cases)
    if document_result in {"passed", "alternative"} and any(
        check["result"] != "passed" for check in checks
    ):
        raise EvidenceError("Completed T27 evidence is missing a required offline observation")
    return checks, {
        "version": OPENAI_RESPONSES_VERSION,
        "mode": OPENAI_RESPONSES_MODE,
        "adapter": "responses-api-sdk-boundary",
        "model": OPENAI_RESPONSES_MODEL,
        "network": "not-called",
        "access": "not-required",
        "request_budget": 256,
        "loop_budget_owner": "t26-run-agent-loop",
        "cases": normalized_cases,
        "live_smoke": {field: smoke[field] for field in sorted(_LIVE_SMOKE_FIELDS)},
    }


def load_openai_responses_checks(
    evidence_file: Path, *, expected_course_version: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Read, canonicalize, and rederive a T27 fixture result."""

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    top_level = _strict_mapping(value, _TOP_LEVEL_FIELDS, "T27 evidence document")
    public_value = {field: top_level[field] for field in _PUBLIC_DOCUMENT_FIELDS}
    document = validate_evidence_document(public_value)
    if document["lesson_id"] != OPENAI_RESPONSES_LESSON_ID:
        raise EvidenceError("T27 evidence lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("T27 evidence course_version does not match the current course")
    supplied_checks = _validate_checks(document["evidence"])
    expected_checks, experiment = validate_openai_responses_experiment(
        top_level["experiment"],
        document_result=document["result"],
        checked_on=document["checked_on"],
    )
    if supplied_checks != expected_checks:
        raise EvidenceError("T27 evidence checks do not match the recorded offline fixture")
    if classify_checks([check["result"] for check in supplied_checks]) != document["result"]:
        raise EvidenceError("T27 evidence result does not match its checks")
    return supplied_checks, experiment
