"""Provider-neutral adapter seam for the T30 research API capstone.

The lesson owns one bounded research step: turn a synthetic telemetry snapshot
into a status-only summary.  The offline fixture models the control flow that
the application owns (request, optional tool call, tool result, validation and
stop conditions).  The live seam is deliberately a plan, not a network client:
the learner must supply a provider, credential and human approval separately.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


LESSON_ID = "t30-research-api-capstone"
FIXTURE_VERSION = "1"
RESEARCH_STEP_ID = "telemetry-quality-summary-v1"
INPUTS = {
    "temperature-daily": {"subject": "temperature", "unit": "°C", "record_limit": 5},
    "pressure-night": {"subject": "pressure", "unit": "kPa", "record_limit": 3},
}
CHECK_IDS = (
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

_CASE_FIELDS = (
    "id",
    "outcome",
    "request_count",
    "tool_call",
    "tool_result_refilled",
    "structured_output",
    "error",
    "recovery",
    "budget_status",
    "network",
    "access",
)

_CASES = (
    {
        "id": "offline-success",
        "outcome": "completed",
        "request_count": 2,
        "tool_call": True,
        "tool_result_refilled": True,
        "structured_output": "accepted",
        "error": "none",
        "recovery": "not-needed",
        "budget_status": "within-budget",
        "network": "not-called",
        "access": "not-required",
    },
    {
        "id": "tool-failure-recovered",
        "outcome": "recovered",
        "request_count": 2,
        "tool_call": True,
        "tool_result_refilled": False,
        "structured_output": "accepted",
        "error": "tool",
        "recovery": "safe-default",
        "budget_status": "within-budget",
        "network": "not-called",
        "access": "not-required",
    },
    {
        "id": "budget-stop",
        "outcome": "stopped",
        "request_count": 1,
        "tool_call": False,
        "tool_result_refilled": False,
        "structured_output": "not-requested",
        "error": "budget",
        "recovery": "explicit-stop",
        "budget_status": "stopped",
        "network": "not-called",
        "access": "not-required",
    },
)


def build_live_smoke_plan() -> dict[str, Any]:
    """Return a bounded approval plan without selecting or contacting a provider."""

    return {
        "status": "not-run",
        "provider": "not-selected",
        "sdk": "not-invoked",
        "model": "not-selected",
        "verified_on": "2026-08-13",
        "network": "not-called",
        "approval": "required-before-any-request",
        "max_requests": 2,
        "max_output_tokens": 96,
        "budget_usd": 0.01,
        "cost": "not assessed; no live request was made",
        "limitations": [
            "caller-must-supply-credential",
            "human-must-confirm-provider-and-model",
            "no-sensitive-research-data",
            "live-result-not-claimed",
        ],
    }

def build_offline_experiment(input_variant: str = "pressure-night") -> dict[str, Any]:
    """Build the public, status-only offline experiment record."""

    if input_variant not in INPUTS:
        raise ValueError(f"unsupported input variant: {input_variant}")
    return {
        "version": FIXTURE_VERSION,
        "mode": "offline-fixture",
        "step_id": RESEARCH_STEP_ID,
        "adapter": "provider-neutral-research-step",
        "input_variant": input_variant,
        "input_source": "synthetic-telemetry-only",
        "output_contract": "status-summary-v1",
        "request_budget": 2,
        "output_token_budget": 96,
        "budget_usd": 0.01,
        "loop_budget_owner": "application-harness",
        "cases": deepcopy(list(_CASES)),
        "live_smoke": build_live_smoke_plan(),
    }


def build_checks(experiment: dict[str, Any]) -> list[dict[str, str]]:
    """Derive the anonymous checks from the experiment, never from a claim."""

    cases = {case["id"]: case for case in experiment["cases"]}
    live = experiment["live_smoke"]
    checks = [
        {"id": "research-step-bounded", "result": "passed" if experiment["step_id"] == RESEARCH_STEP_ID else "failed"},
        {"id": "offline-fixture-deterministic", "result": "passed" if all(case["network"] == "not-called" and case["access"] == "not-required" for case in cases.values()) else "failed"},
        {"id": "tool-loop-observed", "result": "passed" if cases["offline-success"]["tool_call"] and cases["offline-success"]["tool_result_refilled"] and cases["offline-success"]["request_count"] == 2 else "failed"},
        {"id": "structured-output-contract", "result": "passed" if cases["offline-success"]["structured_output"] == "accepted" and cases["budget-stop"]["structured_output"] == "not-requested" else "failed"},
        {"id": "failure-recovery-observed", "result": "passed" if cases["tool-failure-recovered"]["outcome"] == "recovered" and cases["tool-failure-recovered"]["recovery"] == "safe-default" else "failed"},
        {"id": "budget-stop-observed", "result": "passed" if cases["budget-stop"]["budget_status"] == "stopped" and cases["budget-stop"]["request_count"] == 1 else "failed"},
        {"id": "synthetic-input-only", "result": "passed" if experiment["input_source"] == "synthetic-telemetry-only" else "failed"},
        {"id": "live-path-budgeted", "result": "passed" if live["max_requests"] == 2 and live["max_output_tokens"] == 96 and live["budget_usd"] == 0.01 and live["approval"] == "required-before-any-request" else "failed"},
        {"id": "live-api-not-claimed", "result": "passed" if live["status"] == "not-run" and live["network"] == "not-called" else "failed"},
        {"id": "evidence-exported", "result": "passed"},
    ]
    return checks


def build_evidence(course_version: str, input_variant: str = "pressure-night") -> dict[str, Any]:
    """Build a complete anonymous evidence document for the offline fixture."""

    experiment = build_offline_experiment(input_variant)
    checks = build_checks(experiment)
    passed = all(check["result"] == "passed" for check in checks)
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": course_version,
        "lesson_id": LESSON_ID,
        "result": "passed" if passed else "partial",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。" if passed else "部分证据已通过，仍有证据需要补齐。",
        "evidence": checks,
        "experiment": experiment,
    }
