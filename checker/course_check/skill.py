"""Status-only evidence validation for the custom Skill lesson.

The lesson deliberately validates a deterministic fixture rather than calling
an agent client.  The public evidence seam keeps only scenario identifiers,
stable outcomes, trigger observations, and booleans about local validation;
input text, paths, source excerpts, and model output never cross it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidence import EvidenceError, _reject_sensitive_unknown_fields, _require_identifier


SKILL_LESSON_ID = "t17-skill"
SKILL_SIMULATION_VERSION = "1"
SKILL_FINDINGS = frozenset({"ready", "needs-source", "conflict", "untrusted-input"})
SKILL_SCENARIO_ORDER = (
    "complete",
    "missing-source",
    "conflicting-evidence",
    "untrusted-instruction",
)
SKILL_SCENARIO_EXPECTATIONS = {
    "complete": {"finding": "ready", "boundary": False},
    "missing-source": {"finding": "needs-source", "boundary": False},
    "conflicting-evidence": {"finding": "conflict", "boundary": True},
    "untrusted-instruction": {"finding": "untrusted-input", "boundary": True},
}
SKILL_TRIGGER_ORDER = (
    "research-evidence",
    "telemetry-summary",
    "generic-greeting",
    "one-line-calculation",
)
SKILL_TRIGGER_EXPECTATIONS = {
    "research-evidence": "activate",
    "telemetry-summary": "activate",
    "generic-greeting": "skip",
    "one-line-calculation": "skip",
}
SKILL_CHECK_IDS = (
    "skill-package-shaped",
    "trigger-boundary-tested",
    "evidence-scenarios-covered",
    "validation-script-passed",
    "security-boundary-tested",
    "offline-deterministic",
)
SKILL_PACKAGE_FILES = (
    "labs/skill/evidence-research/SKILL.md",
    "labs/skill/evidence-research/references/evidence-schema.md",
    "labs/skill/evidence-research/references/source-policy.md",
    "labs/skill/evidence-research/assets/telemetry-sample.json",
    "labs/skill/evidence-research/scripts/normalize-evidence.py",
)


def skill_package_result(root: Path) -> str:
    """Check the repository-owned Skill package without executing a client."""

    return (
        "passed"
        if all((root / relative).is_file() for relative in SKILL_PACKAGE_FILES)
        else "failed"
    )


def validate_skill_evidence_checks(value: Any) -> list[dict[str, str]]:
    """Require the fixed, learner-facing check list in order."""

    if not isinstance(value, list) or len(value) != len(SKILL_CHECK_IDS):
        raise EvidenceError("T17 Skill evidence checks must contain the complete fixed check list")

    normalized: list[dict[str, str]] = []
    actual_ids: list[str] = []
    seen: set[str] = set()
    for index, check in enumerate(value):
        if not isinstance(check, dict):
            raise EvidenceError(f"T17 Skill evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"T17 Skill evidence check {index}")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            raise EvidenceError(f"T17 Skill evidence check {index} needs an id")
        if check_id in seen:
            raise EvidenceError(f"T17 Skill evidence check ID repeated: {check_id}")
        seen.add(check_id)
        result = check.get("result")
        if result not in {"passed", "failed", "alternative"}:
            raise EvidenceError(f"T17 Skill evidence check {check_id}.result is not supported")
        actual_ids.append(check_id)
        normalized.append({"id": check_id, "result": result})

    if actual_ids != list(SKILL_CHECK_IDS):
        raise EvidenceError("T17 Skill evidence IDs must be exactly " + ", ".join(SKILL_CHECK_IDS))
    return normalized


def _expected_skill_checks(
    *,
    package_result: str,
    runs: list[dict[str, Any]],
    trigger_cases: list[dict[str, str]],
) -> list[dict[str, str]]:
    expected_triggers = all(
        case["observed"] == SKILL_TRIGGER_EXPECTATIONS[case["id"]]
        for case in trigger_cases
    ) and len(trigger_cases) == len(SKILL_TRIGGER_ORDER)
    observed_scenarios = {run["scenario"] for run in runs}
    all_scenarios = set(SKILL_SCENARIO_ORDER) <= observed_scenarios
    all_validated = bool(runs) and all(
        run["script"] == "passed" and run["deterministic"] is True for run in runs
    )
    security = any(
        run["scenario"] == "untrusted-instruction"
        and run["finding"] == "untrusted-input"
        and run["boundary"] is True
        and run["external_call"] is False
        for run in runs
    )
    offline = bool(runs) and all(
        run["deterministic"] is True and run["external_call"] is False for run in runs
    )
    return [
        {"id": "skill-package-shaped", "result": package_result},
        {
            "id": "trigger-boundary-tested",
            "result": "passed" if expected_triggers else "failed",
        },
        {
            "id": "evidence-scenarios-covered",
            "result": "passed" if all_scenarios else "failed",
        },
        {
            "id": "validation-script-passed",
            "result": "passed" if all_validated else "failed",
        },
        {
            "id": "security-boundary-tested",
            "result": "passed" if security else "failed",
        },
        {"id": "offline-deterministic", "result": "passed" if offline else "failed"},
    ]


def validate_skill_simulation(
    value: Any,
    *,
    document_result: str,
    package_result: str = "passed",
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate fixed scenario/trigger outcomes and derive public checks."""

    if not isinstance(value, dict):
        raise EvidenceError("T17 Skill evidence requires a simulation object")
    _reject_sensitive_unknown_fields(value, "T17 Skill simulation")
    if value.get("version") != SKILL_SIMULATION_VERSION:
        raise EvidenceError("Unsupported T17 Skill simulation version")

    raw_runs = value.get("runs")
    if not isinstance(raw_runs, list):
        raise EvidenceError("T17 Skill simulation runs must be a list")
    normalized_runs: list[dict[str, Any]] = []
    seen_run_ids: set[str] = set()
    for index, raw_run in enumerate(raw_runs):
        if not isinstance(raw_run, dict):
            raise EvidenceError(f"T17 Skill simulation run {index} must be an object")
        _reject_sensitive_unknown_fields(raw_run, f"T17 Skill simulation run {index}")
        required = {
            "id",
            "scenario",
            "finding",
            "boundary",
            "script",
            "deterministic",
            "external_call",
        }
        missing = sorted(required - set(raw_run))
        if missing:
            raise EvidenceError(
                f"T17 Skill simulation run {index} is missing: " + ", ".join(missing)
            )
        run_id = raw_run["id"]
        _require_identifier(run_id, f"T17 Skill simulation run {index}.id")
        if run_id in seen_run_ids:
            raise EvidenceError(f"T17 Skill simulation run id repeated: {run_id}")
        seen_run_ids.add(run_id)
        scenario = raw_run["scenario"]
        if scenario not in SKILL_SCENARIO_EXPECTATIONS:
            raise EvidenceError(f"T17 Skill simulation run {run_id}.scenario is not supported")
        expected = SKILL_SCENARIO_EXPECTATIONS[scenario]
        if raw_run["finding"] not in SKILL_FINDINGS:
            raise EvidenceError(f"T17 Skill simulation run {run_id}.finding is not supported")
        if raw_run["finding"] != expected["finding"]:
            raise EvidenceError(f"T17 Skill simulation run {run_id}.finding is not deterministic")
        if raw_run["boundary"] is not expected["boundary"]:
            raise EvidenceError(f"T17 Skill simulation run {run_id}.boundary is not deterministic")
        if raw_run["script"] not in {"passed", "not-run"}:
            raise EvidenceError(f"T17 Skill simulation run {run_id}.script is not supported")
        if not isinstance(raw_run["deterministic"], bool):
            raise EvidenceError(f"T17 Skill simulation run {run_id}.deterministic must be boolean")
        if not isinstance(raw_run["external_call"], bool):
            raise EvidenceError(f"T17 Skill simulation run {run_id}.external_call must be boolean")
        normalized_runs.append(
            {
                "id": run_id,
                "scenario": scenario,
                "finding": raw_run["finding"],
                "boundary": raw_run["boundary"],
                "script": raw_run["script"],
                "deterministic": raw_run["deterministic"],
                "external_call": raw_run["external_call"],
            }
        )

    raw_trigger_cases = value.get("trigger_cases")
    if not isinstance(raw_trigger_cases, list) or len(raw_trigger_cases) != len(SKILL_TRIGGER_ORDER):
        raise EvidenceError("T17 Skill simulation trigger_cases must contain the fixed trigger matrix")
    normalized_trigger_cases: list[dict[str, str]] = []
    for index, raw_case in enumerate(raw_trigger_cases):
        if not isinstance(raw_case, dict):
            raise EvidenceError(f"T17 Skill trigger case {index} must be an object")
        _reject_sensitive_unknown_fields(raw_case, f"T17 Skill trigger case {index}")
        if set(raw_case) != {"id", "observed"}:
            raise EvidenceError(f"T17 Skill trigger case {index} must contain only id and observed")
        expected_id = SKILL_TRIGGER_ORDER[index]
        if raw_case["id"] != expected_id:
            raise EvidenceError("T17 Skill trigger cases must follow the fixed order")
        observed = raw_case["observed"]
        if observed not in {"activate", "skip", "not-tested"}:
            raise EvidenceError(f"T17 Skill trigger case {expected_id}.observed is not supported")
        normalized_trigger_cases.append({"id": expected_id, "observed": observed})

    raw_observed = value.get("observed")
    if not isinstance(raw_observed, list) or any(item not in SKILL_FINDINGS for item in raw_observed):
        raise EvidenceError("T17 Skill simulation observed must list supported finding IDs")
    if len(raw_observed) != len(set(raw_observed)):
        raise EvidenceError("T17 Skill simulation observed must not repeat a finding")
    derived_observed = {run["finding"] for run in normalized_runs}
    if set(raw_observed) != derived_observed:
        raise EvidenceError("T17 Skill simulation observed does not match its runs")

    expected_checks = _expected_skill_checks(
        package_result=package_result,
        runs=normalized_runs,
        trigger_cases=normalized_trigger_cases,
    )
    if document_result in {"passed", "alternative"} and any(
        check["result"] != "passed" for check in expected_checks
    ):
        raise EvidenceError("Completed T17 Skill evidence is missing a required observation")
    return expected_checks, {
        "version": SKILL_SIMULATION_VERSION,
        "runs": normalized_runs,
        "trigger_cases": normalized_trigger_cases,
        "observed": sorted(derived_observed),
    }

