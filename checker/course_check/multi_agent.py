"""Anonymous checker seam for the deterministic T22 multi-agent comparison."""

from __future__ import annotations

from typing import Any

from .evidence import EvidenceError, _reject_sensitive_unknown_fields, _require_identifier


MULTI_AGENT_LESSON_ID = "t22-multi-agent"
MULTI_AGENT_EXPERIMENT_VERSION = "1"
MULTI_AGENT_GOAL = "telemetry-report-v2"
MULTI_AGENT_ACCEPTANCE = (
    "valid-records-counted",
    "units-normalized",
    "report-produced",
    "verification-passed",
)
MULTI_AGENT_SCENARIOS = ("independent-review", "overlap-conflict")
MULTI_AGENT_SHARED_CONTEXT = ("goal", "input-contract", "acceptance-contract")
MULTI_AGENT_CHECK_IDS = (
    "same-goal-compared",
    "task-boundaries-declared",
    "time-usage-verification-compared",
    "conflict-recovered",
    "decision-supported",
    "offline-deterministic",
)


def multi_agent_comparison_fixture(scenario: str) -> dict[str, Any]:
    """Return one status-only teaching fixture, never a model measurement."""

    common = {
        "goal": MULTI_AGENT_GOAL,
        "acceptance": list(MULTI_AGENT_ACCEPTANCE),
        "shared_context": list(MULTI_AGENT_SHARED_CONTEXT),
        "offline": True,
    }
    if scenario == "independent-review":
        return {
            "id": "comparison-independent-review",
            "scenario": scenario,
            **common,
            "single": {
                "mode": "single",
                "accepted": True,
                "elapsed_seconds": 18,
                "usage_units": 90,
                "verification_units": 2,
            },
            "subagents": {
                "mode": "subagents",
                "accepted": True,
                "elapsed_seconds": 12,
                "usage_units": 158,
                "verification_units": 3,
            },
            "boundaries": [
                {"id": "quality-scan", "owns": "input-validation"},
                {"id": "report-outline", "owns": "summary-outline"},
                {"id": "acceptance-review", "owns": "acceptance-check"},
            ],
            "merge": "coordinator-verifies",
            "conflict": "none",
            "recovery": "not-required",
            "recommendation": "consider-bounded-parallel",
        }
    if scenario == "overlap-conflict":
        return {
            "id": "comparison-overlap-conflict",
            "scenario": scenario,
            **common,
            "single": {
                "mode": "single",
                "accepted": True,
                "elapsed_seconds": 18,
                "usage_units": 90,
                "verification_units": 2,
            },
            "subagents": {
                "mode": "subagents",
                "accepted": True,
                "elapsed_seconds": 31,
                "usage_units": 225,
                "verification_units": 5,
            },
            "boundaries": [
                {"id": "draft-a", "owns": "report-summary"},
                {"id": "draft-b", "owns": "report-summary"},
                {"id": "acceptance-review", "owns": "acceptance-check"},
            ],
            "merge": "coordinator-repartitions",
            "conflict": "shared-output-collision",
            "recovery": "repartition-and-revalidate",
            "recommendation": "do-not-adopt",
        }
    raise EvidenceError(f"T22 controlled comparison scenario is unsupported: {scenario}")


def validate_multi_agent_evidence_checks(value: Any) -> list[dict[str, str]]:
    """Validate the fixed public evidence IDs before rederiving their state."""

    if not isinstance(value, list) or len(value) != len(MULTI_AGENT_CHECK_IDS):
        raise EvidenceError("T22 evidence checks must contain the complete fixed check list")
    normalized: list[dict[str, str]] = []
    for index, raw_check in enumerate(value):
        if not isinstance(raw_check, dict):
            raise EvidenceError(f"T22 evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(raw_check, f"T22 evidence check {index}")
        if set(raw_check) != {"id", "result"}:
            raise EvidenceError(f"T22 evidence check {index} must contain only id and result")
        check_id = raw_check.get("id")
        result = raw_check.get("result")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T22 evidence check {index} needs an id")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T22 evidence check {check_id}.result is not supported")
        normalized.append({"id": check_id, "result": result})
    if [item["id"] for item in normalized] != list(MULTI_AGENT_CHECK_IDS):
        raise EvidenceError("T22 evidence IDs must be exactly " + ", ".join(MULTI_AGENT_CHECK_IDS))
    return normalized


def _require_exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be an object")
    _reject_sensitive_unknown_fields(value, label)
    missing = sorted(fields - set(value))
    unexpected = sorted(set(value) - fields)
    if missing or unexpected:
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if unexpected:
            detail.append("unexpected " + ", ".join(unexpected))
        raise EvidenceError(f"{label} has " + "; ".join(detail))
    return value


def _validate_metrics(value: Any, expected: dict[str, Any], label: str) -> dict[str, Any]:
    fields = {"mode", "accepted", "elapsed_seconds", "usage_units", "verification_units"}
    metrics = _require_exact_dict(value, fields, label)
    for key, expected_value in expected.items():
        actual = metrics[key]
        if key.endswith("_units") or key == "elapsed_seconds":
            if isinstance(actual, bool) or not isinstance(actual, int) or actual < 1:
                raise EvidenceError(f"{label}.{key} must be a positive integer")
        if key == "accepted" and not isinstance(actual, bool):
            raise EvidenceError(f"{label}.accepted must be a boolean")
        if actual != expected_value:
            raise EvidenceError(f"{label}.{key} does not match the controlled fixture")
    return {
        key: metrics[key]
        for key in ("mode", "accepted", "elapsed_seconds", "usage_units", "verification_units")
    }


def _validate_comparison(value: Any) -> dict[str, Any]:
    fields = {
        "id",
        "scenario",
        "goal",
        "acceptance",
        "single",
        "subagents",
        "boundaries",
        "shared_context",
        "merge",
        "conflict",
        "recovery",
        "recommendation",
        "offline",
    }
    comparison = _require_exact_dict(value, fields, "T22 comparison")
    scenario = comparison["scenario"]
    if scenario not in MULTI_AGENT_SCENARIOS:
        raise EvidenceError("T22 comparison.scenario is unsupported")
    expected = multi_agent_comparison_fixture(scenario)
    for field in (
        "id",
        "scenario",
        "goal",
        "merge",
        "conflict",
        "recovery",
        "recommendation",
        "offline",
    ):
        if comparison[field] != expected[field]:
            raise EvidenceError(f"T22 comparison.{field} does not match the controlled fixture")
    if comparison["acceptance"] != expected["acceptance"]:
        raise EvidenceError("T22 comparison.acceptance does not match the shared acceptance contract")
    if comparison["shared_context"] != expected["shared_context"]:
        raise EvidenceError("T22 comparison.shared_context does not match the controlled fixture")
    if not isinstance(comparison["boundaries"], list) or comparison["boundaries"] != expected["boundaries"]:
        raise EvidenceError("T22 comparison.boundaries does not match the controlled fixture")
    if not isinstance(comparison["offline"], bool):
        raise EvidenceError("T22 comparison.offline must be a boolean")
    for index, boundary in enumerate(comparison["boundaries"]):
        item = _require_exact_dict(boundary, {"id", "owns"}, f"T22 comparison.boundaries[{index}]")
        _require_identifier(item["id"], f"T22 comparison.boundaries[{index}].id")
        _require_identifier(item["owns"], f"T22 comparison.boundaries[{index}].owns")
    return {
        "id": comparison["id"],
        "scenario": scenario,
        "goal": comparison["goal"],
        "acceptance": list(comparison["acceptance"]),
        "single": _validate_metrics(comparison["single"], expected["single"], "T22 comparison.single"),
        "subagents": _validate_metrics(
            comparison["subagents"], expected["subagents"], "T22 comparison.subagents"
        ),
        "boundaries": [dict(item) for item in comparison["boundaries"]],
        "shared_context": list(comparison["shared_context"]),
        "merge": comparison["merge"],
        "conflict": comparison["conflict"],
        "recovery": comparison["recovery"],
        "recommendation": comparison["recommendation"],
        "offline": True,
    }


def validate_multi_agent_experiment(
    value: Any,
    *,
    document_result: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Rebuild T22 checks from status-only controlled comparison records."""

    fields = {
        "version",
        "goal",
        "comparisons",
        "observed_modes",
        "observed_boundaries",
        "observed_conflicts",
        "observed_recoveries",
        "model_calls",
        "network_calls",
    }
    experiment = _require_exact_dict(value, fields, "T22 experiment")
    if experiment["version"] != MULTI_AGENT_EXPERIMENT_VERSION:
        raise EvidenceError("Unsupported T22 controlled comparison version")
    if experiment["goal"] != MULTI_AGENT_GOAL:
        raise EvidenceError("T22 experiment.goal does not match the shared goal")
    if any(
        isinstance(experiment[field], bool)
        or not isinstance(experiment[field], int)
        or experiment[field] != 0
        for field in ("model_calls", "network_calls")
    ):
        raise EvidenceError("T22 experiment must remain offline with no model or network calls")
    comparisons = experiment["comparisons"]
    if not isinstance(comparisons, list) or not comparisons:
        raise EvidenceError("T22 experiment.comparisons must be a non-empty list")

    normalized: list[dict[str, Any]] = []
    seen_scenarios: set[str] = set()
    for raw_comparison in comparisons:
        comparison = _validate_comparison(raw_comparison)
        scenario = comparison["scenario"]
        if scenario in seen_scenarios:
            raise EvidenceError("T22 experiment repeats a controlled scenario")
        seen_scenarios.add(scenario)
        normalized.append(comparison)

    observed_boundaries = sorted(
        {boundary["owns"] for comparison in normalized for boundary in comparison["boundaries"]}
    )
    observed_conflicts = sorted({comparison["conflict"] for comparison in normalized})
    observed_recoveries = sorted({comparison["recovery"] for comparison in normalized})
    if experiment["observed_modes"] != ["single", "subagents"]:
        raise EvidenceError("T22 experiment.observed_modes must compare single and subagents")
    if experiment["observed_boundaries"] != observed_boundaries:
        raise EvidenceError("T22 experiment.observed_boundaries does not match its comparisons")
    if experiment["observed_conflicts"] != observed_conflicts:
        raise EvidenceError("T22 experiment.observed_conflicts does not match its comparisons")
    if experiment["observed_recoveries"] != observed_recoveries:
        raise EvidenceError("T22 experiment.observed_recoveries does not match its comparisons")

    has_all_scenarios = seen_scenarios == set(MULTI_AGENT_SCENARIOS)
    same_goal = all(
        comparison["goal"] == MULTI_AGENT_GOAL
        and comparison["acceptance"] == list(MULTI_AGENT_ACCEPTANCE)
        and comparison["single"]["accepted"]
        and comparison["subagents"]["accepted"]
        for comparison in normalized
    )
    boundaries_declared = all(
        comparison["boundaries"]
        and comparison["shared_context"] == list(MULTI_AGENT_SHARED_CONTEXT)
        and comparison["merge"]
        for comparison in normalized
    )
    costs_compared = all(
        all(run[key] > 0 for key in ("elapsed_seconds", "usage_units", "verification_units"))
        for comparison in normalized
        for run in (comparison["single"], comparison["subagents"])
    )
    conflict_recovered = any(
        comparison["conflict"] == "shared-output-collision"
        and comparison["recovery"] == "repartition-and-revalidate"
        and comparison["subagents"]["accepted"]
        for comparison in normalized
    )
    decision_supported = any(
        comparison["recommendation"] == "do-not-adopt" for comparison in normalized
    )
    offline = all(comparison["offline"] for comparison in normalized)
    derived_checks = [
        {"id": "same-goal-compared", "result": "passed" if same_goal else "failed"},
        {"id": "task-boundaries-declared", "result": "passed" if boundaries_declared else "failed"},
        {"id": "time-usage-verification-compared", "result": "passed" if costs_compared else "failed"},
        {"id": "conflict-recovered", "result": "passed" if conflict_recovered else "failed"},
        {
            "id": "decision-supported",
            "result": "passed" if decision_supported and has_all_scenarios else "failed",
        },
        {"id": "offline-deterministic", "result": "passed" if offline else "failed"},
    ]
    if document_result in {"passed", "alternative"} and any(
        check["result"] != "passed" for check in derived_checks
    ):
        raise EvidenceError("Completed T22 evidence is missing a required comparison observation")
    return derived_checks, {
        "version": MULTI_AGENT_EXPERIMENT_VERSION,
        "goal": MULTI_AGENT_GOAL,
        "comparisons": normalized,
        "observed_modes": ["single", "subagents"],
        "observed_boundaries": observed_boundaries,
        "observed_conflicts": observed_conflicts,
        "observed_recoveries": observed_recoveries,
        "model_calls": 0,
        "network_calls": 0,
    }
