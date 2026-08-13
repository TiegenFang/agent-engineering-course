"""Deterministic checker for the T25 dual-track capstone integration seam.

The integration lesson checks a status-only portfolio.  It deliberately does
not accept source files, issue text, prompts, paths, or model output: those
remain local learner artifacts.  The checker recomputes the public checks from
the selected track and fault so that a learner cannot turn a partial delivery
into a passing JSON document by editing the top-level result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence import (
    EvidenceError,
    _reject_sensitive_unknown_fields,
    validate_evidence_document,
)


CAPSTONE_INTEGRATION_LESSON_ID = "t25-capstone-integration"
CAPSTONE_INTEGRATION_VERSION = "1"
CAPSTONE_INTEGRATION_BASELINE_ID = "telemetry-capstone-integration-v1"
CAPSTONE_INTEGRATION_TRACKS = frozenset({"research", "enterprise"})
CAPSTONE_INTEGRATION_FAULTS = frozenset(
    {"none", "missing-core", "unsafe-side-effect", "incomplete-delivery"}
)
CAPSTONE_INTEGRATION_CHECK_IDS = (
    "track-selected",
    "problem-scoped",
    "context-memory-linked",
    "skill-mcp-bounded",
    "core-evidence-linked",
    "validation-recorded",
    "migration-recorded",
    "delivery-reviewed",
    "privacy-safe",
    "version-locked",
    "portfolio-exported",
    "offline-deterministic",
)


def _expected_flags(track: str, fault: str) -> dict[str, bool]:
    """Return the externally observable result for a fixture state."""

    # Both tracks share the same acceptance dimensions.  The selected track
    # only changes the delivery checklist; it must not weaken the common
    # evidence, safety, migration, or privacy gate.
    return {
        "track": track in CAPSTONE_INTEGRATION_TRACKS,
        "problem": True,
        "context_memory": fault != "missing-core",
        "skill_mcp": fault != "unsafe-side-effect",
        "core": fault != "missing-core",
        "validation": fault != "incomplete-delivery",
        "migration": True,
        "delivery": fault != "incomplete-delivery",
        "privacy": fault != "unsafe-side-effect",
        "version": True,
        "portfolio": fault != "incomplete-delivery",
        "offline": True,
    }


def _checks(flags: dict[str, bool]) -> list[dict[str, str]]:
    fields = (
        ("track-selected", "track"),
        ("problem-scoped", "problem"),
        ("context-memory-linked", "context_memory"),
        ("skill-mcp-bounded", "skill_mcp"),
        ("core-evidence-linked", "core"),
        ("validation-recorded", "validation"),
        ("migration-recorded", "migration"),
        ("delivery-reviewed", "delivery"),
        ("privacy-safe", "privacy"),
        ("version-locked", "version"),
        ("portfolio-exported", "portfolio"),
        ("offline-deterministic", "offline"),
    )
    return [
        {"id": check_id, "result": "passed" if flags[field] else "failed"}
        for check_id, field in fields
    ]


def _normalize_summary(value: dict[str, Any]) -> None:
    """Accept the UI's count label while validating the shared JSON contract."""

    if value.get("result") == "passed":
        value["summary"] = "所有必需证据均已通过。"
    elif value.get("result") == "partial":
        value["summary"] = "部分证据已通过，仍有证据需要补齐。"


def load_capstone_integration_checks(
    evidence_file: Path,
    *,
    expected_course_version: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate a T25 evidence JSON and return derived checks plus safe trace."""

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(
            f"Capstone integration evidence fixture not found: {evidence_file.name}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid capstone integration JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Capstone integration evidence must be a JSON object")
    _normalize_summary(value)
    document = validate_evidence_document(value)
    if document["lesson_id"] != CAPSTONE_INTEGRATION_LESSON_ID:
        raise EvidenceError("Capstone integration fixture lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("Capstone integration fixture course_version does not match the current course")

    experiment = value.get("experiment")
    if not isinstance(experiment, dict):
        raise EvidenceError("Capstone integration evidence requires an experiment object")
    _reject_sensitive_unknown_fields(experiment, "Capstone integration experiment")
    if "issue_body" in experiment:
        raise EvidenceError("Capstone integration experiment contains a sensitive field: issue_body")
    expected_fields = {
        "version",
        "baseline_id",
        "track",
        "fault",
        "problem",
        "context_memory",
        "skill_mcp",
        "core",
        "validation",
        "migration",
        "delivery",
        "privacy",
        "version_lock",
        "portfolio",
        "offline",
    }
    if set(experiment) != expected_fields:
        raise EvidenceError("Capstone integration experiment fields are invalid")
    if experiment["version"] != CAPSTONE_INTEGRATION_VERSION:
        raise EvidenceError("Unsupported capstone integration experiment version")
    if experiment["baseline_id"] != CAPSTONE_INTEGRATION_BASELINE_ID:
        raise EvidenceError("Capstone integration baseline_id is unsupported")
    track = experiment["track"]
    fault = experiment["fault"]
    if track not in CAPSTONE_INTEGRATION_TRACKS:
        raise EvidenceError("Capstone integration track is unsupported")
    if fault not in CAPSTONE_INTEGRATION_FAULTS:
        raise EvidenceError("Capstone integration fault is unsupported")
    bool_fields = expected_fields - {"version", "baseline_id", "track", "fault"}
    if any(not isinstance(experiment[field], bool) for field in bool_fields):
        raise EvidenceError("Capstone integration experiment flags must be booleans")

    expected = _expected_flags(track, fault)
    actual = {
        "track": experiment["track"] in CAPSTONE_INTEGRATION_TRACKS,
        "problem": experiment["problem"],
        "context_memory": experiment["context_memory"],
        "skill_mcp": experiment["skill_mcp"],
        "core": experiment["core"],
        "validation": experiment["validation"],
        "migration": experiment["migration"],
        "delivery": experiment["delivery"],
        "privacy": experiment["privacy"],
        "version": experiment["version_lock"],
        "portfolio": experiment["portfolio"],
        "offline": experiment["offline"],
    }
    if actual != expected:
        raise EvidenceError("Capstone integration checks do not match the recorded experiment")

    derived = _checks(actual)
    supplied = document["evidence"]
    if [check["id"] for check in supplied] != list(CAPSTONE_INTEGRATION_CHECK_IDS):
        raise EvidenceError("Capstone integration evidence IDs are invalid")
    if supplied != derived:
        raise EvidenceError("Capstone integration checks do not match the recorded experiment")
    expected_result = "passed" if all(check["result"] == "passed" for check in derived) else "partial"
    if document["result"] != expected_result:
        raise EvidenceError("Capstone integration result does not match its evidence")

    return derived, {
        "version": CAPSTONE_INTEGRATION_VERSION,
        "baseline_id": CAPSTONE_INTEGRATION_BASELINE_ID,
        "track": track,
        "fault": fault,
        "problem": actual["problem"],
        "context_memory": actual["context_memory"],
        "skill_mcp": actual["skill_mcp"],
        "core": actual["core"],
        "validation": actual["validation"],
        "migration": actual["migration"],
        "delivery": actual["delivery"],
        "privacy": actual["privacy"],
        "version_lock": actual["version"],
        "portfolio": actual["portfolio"],
        "offline": actual["offline"],
    }
