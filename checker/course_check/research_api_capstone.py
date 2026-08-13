"""Anonymous evidence validator for the T30 research API capstone."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .evidence import EvidenceError, _reject_sensitive_unknown_fields, validate_evidence_document


RESEARCH_API_LESSON_ID = "t30-research-api-capstone"
RESEARCH_API_VERSION = "1"
RESEARCH_API_CHECK_IDS = (
    "research-step-bounded",
    "offline-fixture-deterministic",
    "tool-loop-observed",
    "structured-output-contract",
    "failure-recovery-observed",
    "budget-stop-observed",
    "synthetic-input-only",
    "live-path-budgeted",
    "live-api-not-claimed",
    "evidence-exported",
)
RESEARCH_API_INPUTS = {"temperature-daily", "pressure-night"}
PACKAGE_FILES = (
    "labs/research-api-capstone/research_api_adapter.py",
    "labs/research-api-capstone/run_fixture.py",
    "labs/research-api-capstone/README.md",
    "site/src/content/docs/module-12-research-api-capstone.mdx",
    "site/src/lib/research-api-capstone.mjs",
    "site/src/components/ResearchApiCapstoneLab.astro",
    "site/scripts/test-research-api-capstone.mjs",
    "site/scripts/verify-research-api-capstone.mjs",
    "checker/tests/test_research_api_capstone.py",
    "docs/research/t30-research-api-sources.md",
)

_PUBLIC_FIELDS = {
    "contract", "contract_version", "course_version", "lesson_id", "result",
    "anonymous", "checked_on", "summary", "evidence",
}
_EXPERIMENT_FIELDS = {
    "version", "mode", "step_id", "adapter", "input_variant", "input_source",
    "output_contract", "request_budget", "output_token_budget", "budget_usd",
    "loop_budget_owner", "cases", "live_smoke",
}
_CASE_FIELDS = {
    "id", "outcome", "request_count", "tool_call", "tool_result_refilled",
    "structured_output", "error", "recovery", "budget_status", "network", "access",
}
_LIVE_FIELDS = {
    "status", "provider", "sdk", "model", "verified_on", "network", "approval",
    "max_requests", "max_output_tokens", "budget_usd", "cost", "limitations",
}
_CASE_ORDER = ("offline-success", "tool-failure-recovered", "budget-stop")
_EXPECTED_CASES: dict[str, dict[str, Any]] = {
    "offline-success": {
        "outcome": "completed", "request_count": 2, "tool_call": True,
        "tool_result_refilled": True, "structured_output": "accepted", "error": "none",
        "recovery": "not-needed", "budget_status": "within-budget",
    },
    "tool-failure-recovered": {
        "outcome": "recovered", "request_count": 2, "tool_call": True,
        "tool_result_refilled": False, "structured_output": "accepted", "error": "tool",
        "recovery": "safe-default", "budget_status": "within-budget",
    },
    "budget-stop": {
        "outcome": "stopped", "request_count": 1, "tool_call": False,
        "tool_result_refilled": False, "structured_output": "not-requested", "error": "budget",
        "recovery": "explicit-stop", "budget_status": "stopped",
    },
}


def package_result(root: Path) -> str:
    return "passed" if all((root / relative).is_file() for relative in PACKAGE_FILES) else "failed"


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceError(f"{label} must be an object")
    return value


def _exact(mapping: Mapping[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields - set(mapping))
    unexpected = sorted(set(mapping) - fields)
    if missing:
        raise EvidenceError(f"{label} is missing: {', '.join(missing)}")
    if unexpected:
        sensitive_tokens = ("path", "file", "source", "secret", "token", "password", "credential", "api_key", "raw", "payload", "content", "prompt")
        sensitive = [field for field in unexpected if any(token in str(field).lower() for token in sensitive_tokens)]
        if sensitive:
            raise EvidenceError(f"{label} contains a sensitive field: {', '.join(map(str, sensitive))}")
        raise EvidenceError(f"{label} has unexpected fields: {', '.join(unexpected)}")


def _checks(experiment: Mapping[str, Any]) -> list[dict[str, str]]:
    cases = {case["id"]: case for case in experiment["cases"]}
    live = experiment["live_smoke"]
    return [
        {"id": "research-step-bounded", "result": "passed" if experiment["step_id"] == "telemetry-quality-summary-v1" else "failed"},
        {"id": "offline-fixture-deterministic", "result": "passed" if all(case["network"] == "not-called" and case["access"] == "not-required" for case in cases.values()) else "failed"},
        {"id": "tool-loop-observed", "result": "passed" if cases["offline-success"]["tool_call"] and cases["offline-success"]["tool_result_refilled"] else "failed"},
        {"id": "structured-output-contract", "result": "passed" if cases["offline-success"]["structured_output"] == "accepted" and cases["budget-stop"]["structured_output"] == "not-requested" else "failed"},
        {"id": "failure-recovery-observed", "result": "passed" if cases["tool-failure-recovered"]["outcome"] == "recovered" and cases["tool-failure-recovered"]["recovery"] == "safe-default" else "failed"},
        {"id": "budget-stop-observed", "result": "passed" if cases["budget-stop"]["budget_status"] == "stopped" and cases["budget-stop"]["request_count"] == 1 else "failed"},
        {"id": "synthetic-input-only", "result": "passed" if experiment["input_source"] == "synthetic-telemetry-only" else "failed"},
        {"id": "live-path-budgeted", "result": "passed" if live["max_requests"] == 2 and live["max_output_tokens"] == 96 and live["budget_usd"] == 0.01 and live["approval"] == "required-before-any-request" else "failed"},
        {"id": "live-api-not-claimed", "result": "passed" if live["status"] == "not-run" and live["network"] == "not-called" else "failed"},
        {"id": "evidence-exported", "result": "passed"},
    ]


def load_research_api_checks(evidence_file: Path, *, expected_course_version: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"T30 evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid T30 evidence JSON: {exc.msg}") from exc
    top = _mapping(value, "T30 evidence document")
    _exact(top, _PUBLIC_FIELDS | {"experiment"}, "T30 evidence document")
    public = {field: top[field] for field in _PUBLIC_FIELDS}
    document = validate_evidence_document(public)
    if document["lesson_id"] != RESEARCH_API_LESSON_ID:
        raise EvidenceError("T30 evidence lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("T30 evidence course_version does not match the current course")
    experiment = _mapping(top["experiment"], "T30 experiment")
    _exact(experiment, _EXPERIMENT_FIELDS, "T30 experiment")
    if experiment["version"] != RESEARCH_API_VERSION or experiment["mode"] != "offline-fixture":
        raise EvidenceError("T30 fixture version or mode is unsupported")
    if experiment["step_id"] != "telemetry-quality-summary-v1" or experiment["adapter"] != "provider-neutral-research-step":
        raise EvidenceError("T30 research step identity is unsupported")
    if experiment["input_variant"] not in RESEARCH_API_INPUTS or experiment["input_source"] != "synthetic-telemetry-only":
        raise EvidenceError("T30 input boundary is unsupported")
    if experiment["output_contract"] != "status-summary-v1":
        raise EvidenceError("T30 output contract is unsupported")
    if experiment["request_budget"] != 2 or experiment["output_token_budget"] != 96 or experiment["budget_usd"] != 0.01 or experiment["loop_budget_owner"] != "application-harness":
        raise EvidenceError("T30 budget must remain owned by the application harness")
    raw_cases = experiment["cases"]
    if not isinstance(raw_cases, list) or len(raw_cases) != len(_CASE_ORDER):
        raise EvidenceError("T30 fixture must contain the complete fixed case list")
    normalized_cases: list[dict[str, Any]] = []
    for index, raw_case in enumerate(raw_cases):
        case = _mapping(raw_case, f"T30 case {index}")
        _exact(case, _CASE_FIELDS, f"T30 case {index}")
        if case["id"] != _CASE_ORDER[index]:
            raise EvidenceError("T30 cases must appear in the fixed order")
        expected = _EXPECTED_CASES[case["id"]]
        for key, expected_value in expected.items():
            if case[key] != expected_value:
                raise EvidenceError(f"T30 case {case['id']}.{key} does not match its fixture")
        if case["network"] != "not-called" or case["access"] != "not-required":
            raise EvidenceError("T30 offline cases must not use network or credentials")
        normalized_cases.append({field: case[field] for field in sorted(_CASE_FIELDS)})
    live = _mapping(experiment["live_smoke"], "T30 live_smoke")
    _exact(live, _LIVE_FIELDS, "T30 live_smoke")
    if live["status"] != "not-run" or live["provider"] != "not-selected" or live["sdk"] != "not-invoked" or live["model"] != "not-selected":
        raise EvidenceError("T30 fixture cannot claim a live API result")
    if live["network"] != "not-called" or live["approval"] != "required-before-any-request":
        raise EvidenceError("T30 live seam must remain approval-gated and offline")
    if live["max_requests"] != 2 or live["max_output_tokens"] != 96 or live["budget_usd"] != 0.01:
        raise EvidenceError("T30 live seam budget is invalid")
    if live["verified_on"] != document["checked_on"] or live["cost"] != "not assessed; no live request was made":
        raise EvidenceError("T30 live seam date or cost boundary is invalid")
    if live["limitations"] != ["caller-must-supply-credential", "human-must-confirm-provider-and-model", "no-sensitive-research-data", "live-result-not-claimed"]:
        raise EvidenceError("T30 live seam limitations are invalid")
    checks = _checks(experiment)
    if document["evidence"] != checks:
        raise EvidenceError("T30 evidence checks do not match the recorded experiment")
    expected_result = "passed" if all(check["result"] == "passed" for check in checks) else "partial"
    if document["result"] != expected_result:
        raise EvidenceError("T30 evidence result does not match its checks")
    return checks, {
        "version": experiment["version"],
        "mode": experiment["mode"],
        "step_id": experiment["step_id"],
        "adapter": experiment["adapter"],
        "input_variant": experiment["input_variant"],
        "input_source": experiment["input_source"],
        "request_budget": experiment["request_budget"],
        "output_token_budget": experiment["output_token_budget"],
        "budget_usd": experiment["budget_usd"],
        "case_ids": list(_CASE_ORDER),
        "live_smoke": dict(live),
    }
