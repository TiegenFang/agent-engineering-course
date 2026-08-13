"""Deterministic, privacy-preserving checker for the T23 research capstone."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence import (
    EvidenceError,
    _reject_sensitive_unknown_fields,
    validate_evidence_document,
)

RESEARCH_CAPSTONE_LESSON_ID = "t23-research-capstone"
RESEARCH_CAPSTONE_VERSION = "1"
RESEARCH_CAPSTONE_BASELINE_ID = "telemetry-research-v1"
RESEARCH_CAPSTONE_INPUTS = {
    "temperature-daily": {"subject": "temperature", "unit": "°C", "limit": 5},
    "pressure-night": {"subject": "pressure", "unit": "kPa", "limit": 3},
}
RESEARCH_CAPSTONE_FAULTS = frozenset(
    {"none", "missing-values", "stale-memory", "mcp-denied"}
)
RESEARCH_CAPSTONE_CHECK_IDS = (
    "context-recorded",
    "memory-governed",
    "skill-applied",
    "mcp-boundary",
    "script-reproducible",
    "figure-produced",
    "record-complete",
    "report-complete",
    "evidence-exported",
    "migration-complete",
    "rubric-complete",
    "offline-deterministic",
)


def _expected_flags(input_id: str, fault: str) -> dict[str, bool]:
    return {
        "context": True,
        "memory": fault != "stale-memory",
        "skill": True,
        "mcp": fault != "mcp-denied",
        "script": True,
        "figure": fault != "missing-values",
        "record": True,
        "report": fault == "none",
        "evidence": True,
        "migration": input_id == "pressure-night",
        "rubric": fault == "none" and input_id == "pressure-night",
        "offline": True,
    }


def _checks(flags: dict[str, bool]) -> list[dict[str, str]]:
    fields = (
        ("context-recorded", "context"),
        ("memory-governed", "memory"),
        ("skill-applied", "skill"),
        ("mcp-boundary", "mcp"),
        ("script-reproducible", "script"),
        ("figure-produced", "figure"),
        ("record-complete", "record"),
        ("report-complete", "report"),
        ("evidence-exported", "evidence"),
        ("migration-complete", "migration"),
        ("rubric-complete", "rubric"),
        ("offline-deterministic", "offline"),
    )
    return [
        {"id": check_id, "result": "passed" if flags[field] else "failed"}
        for check_id, field in fields
    ]


def load_research_capstone_checks(
    evidence_file: Path,
    *,
    expected_course_version: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate status-only evidence and recompute its public result."""

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(
            f"Research capstone evidence fixture not found: {evidence_file.name}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid research capstone JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Research capstone evidence must be a JSON object")
    # The capstone UI may use a learner-friendly count summary (for example
    # ``12/12 项证据``).  The shared evidence contract deliberately keeps a
    # stable machine-facing summary, so normalize only this local parsed copy
    # before the common validator.  The result itself is still checked below.
    if value.get("result") == "passed":
        value["summary"] = "所有必需证据均已通过。"
    elif value.get("result") == "partial":
        value["summary"] = "部分证据已通过，仍有证据需要补齐。"
    document = validate_evidence_document(value)
    if document["lesson_id"] != RESEARCH_CAPSTONE_LESSON_ID:
        raise EvidenceError("Research capstone fixture lesson_id does not match the requested lesson")
    if document["course_version"] != expected_course_version:
        raise EvidenceError("Research capstone fixture course_version does not match the current course")
    experiment = value.get("experiment")
    if not isinstance(experiment, dict):
        raise EvidenceError("Research capstone evidence requires an experiment object")
    _reject_sensitive_unknown_fields(experiment, "Research capstone experiment")
    expected_fields = {
        "version", "baseline_id", "input", "context", "memory", "skill", "mcp",
        "artifacts", "migration", "rubric", "offline", "fault",
    }
    if set(experiment) != expected_fields:
        raise EvidenceError("Research capstone experiment fields are invalid")
    if experiment["version"] != RESEARCH_CAPSTONE_VERSION:
        raise EvidenceError("Unsupported research capstone experiment version")
    if experiment["baseline_id"] != RESEARCH_CAPSTONE_BASELINE_ID:
        raise EvidenceError("Research capstone baseline_id is unsupported")
    input_id = experiment["input"]
    fault = experiment["fault"]
    if input_id not in RESEARCH_CAPSTONE_INPUTS:
        raise EvidenceError("Research capstone input variant is unsupported")
    if fault not in RESEARCH_CAPSTONE_FAULTS:
        raise EvidenceError("Research capstone fault is unsupported")
    bool_fields = {"context", "memory", "skill", "mcp", "migration", "rubric", "offline"}
    if any(not isinstance(experiment[field], bool) for field in bool_fields):
        raise EvidenceError("Research capstone experiment flags must be booleans")
    artifacts = experiment["artifacts"]
    if not isinstance(artifacts, dict):
        raise EvidenceError("Research capstone artifacts must be an object")
    _reject_sensitive_unknown_fields(artifacts, "Research capstone artifacts")
    artifact_fields = {"script", "figure", "record", "report", "evidence"}
    if set(artifacts) != artifact_fields or any(
        not isinstance(artifacts[field], bool) for field in artifact_fields
    ):
        raise EvidenceError("Research capstone artifacts must cover boolean script, figure, record, report and evidence")
    expected = _expected_flags(input_id, fault)
    actual = {
        "context": experiment["context"], "memory": experiment["memory"],
        "skill": experiment["skill"], "mcp": experiment["mcp"],
        "script": artifacts["script"], "figure": artifacts["figure"],
        "record": artifacts["record"], "report": artifacts["report"],
        "evidence": artifacts["evidence"], "migration": experiment["migration"],
        "rubric": experiment["rubric"], "offline": experiment["offline"],
    }
    if actual != expected:
        raise EvidenceError("Research capstone checks do not match the recorded experiment")
    derived = _checks(actual)
    supplied = document["evidence"]
    if [check["id"] for check in supplied] != list(RESEARCH_CAPSTONE_CHECK_IDS):
        raise EvidenceError("Research capstone evidence IDs are invalid")
    if supplied != derived:
        raise EvidenceError("Research capstone checks do not match the recorded experiment")
    expected_result = "passed" if all(check["result"] == "passed" for check in derived) else "partial"
    if document["result"] != expected_result:
        raise EvidenceError("Research capstone result does not match its evidence")
    return derived, {
        "version": RESEARCH_CAPSTONE_VERSION,
        "baseline_id": RESEARCH_CAPSTONE_BASELINE_ID,
        "input": input_id,
        "context": actual["context"],
        "memory": actual["memory"],
        "skill": actual["skill"],
        "mcp": actual["mcp"],
        "artifacts": {field: actual[field] for field in ("script", "figure", "record", "report", "evidence")},
        "migration": actual["migration"],
        "rubric": actual["rubric"],
        "offline": actual["offline"],
        "fault": fault,
    }
