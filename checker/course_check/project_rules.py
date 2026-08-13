"""Behavioral checker seam for the project-rules lesson.

The local PowerShell lab may inspect rule files, but only an ordered sequence
of boolean observations crosses into the anonymous evidence document.  The
checker derives the public checks from those observations so a learner cannot
claim a successful scope or recovery by submitting a hand-written list of
``passed`` values.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence import EvidenceError, _reject_sensitive_unknown_fields, _require_identifier


PROJECT_RULES_LESSON_ID = "t04-project-rules"
PROJECT_RULES_CHECK_IDS = (
    "safe-lab-boundary",
    "codex-scope-observed",
    "claude-scope-observed",
    "nested-conflict-diagnosed",
    "recovery-rechecked",
    "cross-tool-migration",
)
PROJECT_RULES_STAGE_IDS = (
    "safe-boundary",
    "codex-observation",
    "claude-observation",
    "conflict-diagnosis",
    "recovery",
    "migration",
)
PROJECT_RULES_STAGE_OBSERVATIONS = {
    "safe-boundary": frozenset({"new_target", "not_repo", "new_output"}),
    "codex-observation": frozenset(
        {"root_rule_seen", "nested_override_seen", "nested_regular_skipped", "nearest_last"}
    ),
    "claude-observation": frozenset(
        {
            "ancestor_rule_seen",
            "nested_rule_seen",
            "agent_import_seen",
            "scoped_rule_seen",
            "ancestor_before_nested",
        }
    ),
    "conflict-diagnosis": frozenset(
        {"codex_conflict_seen", "claude_conflict_seen", "difference_logged", "conflict_isolated"}
    ),
    "recovery": frozenset(
        {"override_removed", "regular_rechecked", "project_rule_kept", "recheck_complete"}
    ),
    "migration": frozenset({"comparison_done", "goal_unchanged", "difference_noted"}),
}


def _read_fixture(evidence_file: Path) -> dict[str, Any]:
    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Project rules fixture must be a JSON object")
    _reject_sensitive_unknown_fields(value, "Project rules fixture")
    if value.get("lesson_id") != PROJECT_RULES_LESSON_ID:
        raise EvidenceError("Project rules fixture lesson_id does not match the requested lesson")
    return value


def _validate_platform(value: dict[str, Any]) -> None:
    platform = value.get("platform")
    shell = value.get("shell")
    if platform != "windows":
        raise EvidenceError("Project rules fixture platform must be windows")
    if shell != "powershell":
        raise EvidenceError("Project rules fixture shell must be powershell")


def _validate_stage(
    raw_stage: Any,
    *,
    expected_id: str,
    expected_sequence: int,
) -> tuple[str, dict[str, bool]]:
    if not isinstance(raw_stage, dict):
        raise EvidenceError("Project rules journey stages must contain objects")
    _reject_sensitive_unknown_fields(raw_stage, f"Project rules stage {expected_id}")
    required = {"id", "sequence", "result", "observations"}
    missing = sorted(required - set(raw_stage))
    if missing:
        raise EvidenceError(
            f"Project rules stage {expected_id} is missing: {', '.join(missing)}"
        )
    if raw_stage["id"] != expected_id or raw_stage["sequence"] != expected_sequence:
        raise EvidenceError("Project rules journey stages are out of order")
    if raw_stage["result"] not in {"passed", "failed"}:
        raise EvidenceError("Project rules stage result must be passed or failed")
    observations = raw_stage["observations"]
    if not isinstance(observations, dict):
        raise EvidenceError(f"Project rules stage {expected_id}.observations must be an object")
    _reject_sensitive_unknown_fields(observations, f"Project rules stage {expected_id}.observations")
    expected_observations = PROJECT_RULES_STAGE_OBSERVATIONS[expected_id]
    actual_observations = set(observations)
    if actual_observations != expected_observations:
        missing_observations = sorted(expected_observations - actual_observations)
        unknown_observations = sorted(actual_observations - expected_observations)
        details: list[str] = []
        if missing_observations:
            details.append("missing: " + ", ".join(missing_observations))
        if unknown_observations:
            details.append("unknown: " + ", ".join(unknown_observations))
        raise EvidenceError(
            f"Project rules stage {expected_id}.observations are incomplete or unexpected ("
            + "; ".join(details)
            + ")"
        )
    if any(not isinstance(item, bool) for item in observations.values()):
        raise EvidenceError(f"Project rules stage {expected_id}.observations must be booleans")
    computed_result = "passed" if all(observations.values()) else "failed"
    if raw_stage["result"] != computed_result:
        raise EvidenceError(f"Project rules stage {expected_id}.result does not match observations")
    return raw_stage["result"], observations


def _derive_checks(stage_results: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"id": "safe-lab-boundary", "result": stage_results["safe-boundary"]},
        {"id": "codex-scope-observed", "result": stage_results["codex-observation"]},
        {"id": "claude-scope-observed", "result": stage_results["claude-observation"]},
        {"id": "nested-conflict-diagnosed", "result": stage_results["conflict-diagnosis"]},
        {"id": "recovery-rechecked", "result": stage_results["recovery"]},
        {"id": "cross-tool-migration", "result": stage_results["migration"]},
    ]


def load_project_rules_checks(
    evidence_file: Path,
    *,
    expected_course_version: str,
) -> list[dict[str, str]]:
    """Validate a local journey and derive anonymous project-rules checks."""

    value = _read_fixture(evidence_file)
    _validate_platform(value)
    if "course_version" in value and value["course_version"] != expected_course_version:
        raise EvidenceError("Project rules fixture course_version does not match the current course")

    journey = value.get("journey")
    if not isinstance(journey, dict):
        raise EvidenceError("Project rules fixture requires an ordered journey")
    _reject_sensitive_unknown_fields(journey, "Project rules journey")
    required_journey_fields = {"trace_version", "trace_id", "stages"}
    missing_journey_fields = sorted(required_journey_fields - set(journey))
    if missing_journey_fields:
        raise EvidenceError(
            "Project rules journey is missing: " + ", ".join(missing_journey_fields)
        )
    if journey["trace_version"] != "1":
        raise EvidenceError("Unsupported project rules journey version")
    _require_identifier(journey["trace_id"], "Project rules journey.trace_id")

    stages = journey["stages"]
    if not isinstance(stages, list) or len(stages) != len(PROJECT_RULES_STAGE_IDS):
        raise EvidenceError("Project rules journey must contain the complete ordered stage sequence")
    stage_results: dict[str, str] = {}
    for sequence, expected_id in enumerate(PROJECT_RULES_STAGE_IDS, start=1):
        result, _ = _validate_stage(
            stages[sequence - 1], expected_id=expected_id, expected_sequence=sequence
        )
        stage_results[expected_id] = result

    checks = value.get("checks")
    if not isinstance(checks, list) or len(checks) != len(PROJECT_RULES_CHECK_IDS):
        raise EvidenceError("Project rules fixture checks are incomplete or unexpected")
    supplied: dict[str, str] = {}
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise EvidenceError(f"Project rules check {index} must be an object")
        _reject_sensitive_unknown_fields(check, f"Project rules check {index}")
        if set(check) != {"id", "result"}:
            raise EvidenceError("Project rules checks must contain only id and result")
        check_id = check["id"]
        if check_id not in PROJECT_RULES_CHECK_IDS:
            raise EvidenceError(f"Unknown project rules check id: {check_id}")
        if check_id in supplied:
            raise EvidenceError(f"Project rules check ID repeated: {check_id}")
        if check["result"] not in {"passed", "failed"}:
            raise EvidenceError("Project rules check result must be passed or failed")
        supplied[check_id] = check["result"]
    if set(supplied) != set(PROJECT_RULES_CHECK_IDS):
        raise EvidenceError("Project rules checks are incomplete or unexpected")

    derived = _derive_checks(stage_results)
    derived_map = {check["id"]: check["result"] for check in derived}
    if supplied != derived_map:
        raise EvidenceError("Project rules checks do not match the recorded journey")
    return derived
