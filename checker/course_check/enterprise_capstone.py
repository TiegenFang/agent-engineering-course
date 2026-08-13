"""Deterministic, privacy-preserving checker for the T24 enterprise capstone."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence import (
    EvidenceError,
    _reject_sensitive_unknown_fields,
    validate_evidence_document,
)


ENTERPRISE_CAPSTONE_LESSON_ID = "t24-enterprise-capstone"
ENTERPRISE_CAPSTONE_VERSION = "1"
ENTERPRISE_CAPSTONE_BASELINE_ID = "telemetry-report-issue-v1"
ENTERPRISE_CAPSTONE_INPUTS = {
    "feature-issue": {"kind": "feature", "title": "报告中增加夜班摘要"},
    "bug-fix": {"kind": "bug", "title": "修复压力单位换算"},
}
ENTERPRISE_CAPSTONE_FAULTS = frozenset(
    {"none", "ambiguous-issue", "test-failure", "review-requested", "mcp-denied"}
)
ENTERPRISE_CAPSTONE_CHECK_IDS = (
    "issue-clarified",
    "context-recorded",
    "memory-governed",
    "skill-applied",
    "mcp-boundary",
    "change-evidence",
    "tests-evidence",
    "review-evidence",
    "delivery-evidence",
    "migration-complete",
    "rubric-complete",
    "offline-deterministic",
)


def _expected_flags(input_id: str, fault: str) -> dict[str, bool]:
    """Return the fixed public status contract for one safe fixture run."""

    ambiguous = fault == "ambiguous-issue"
    return {
        "issue": not ambiguous,
        "context": not ambiguous,
        "memory": True,
        "skill": True,
        "mcp": fault != "mcp-denied",
        "change": not ambiguous,
        "tests": fault != "test-failure" and not ambiguous,
        "review": fault != "review-requested" and not ambiguous,
        "delivery": fault == "none",
        "evidence": True,
        "migration": input_id == "bug-fix" and not ambiguous,
        "rubric": fault == "none" and input_id == "bug-fix",
        "offline": True,
    }


def _checks(flags: dict[str, bool]) -> list[dict[str, str]]:
    fields = (
        ("issue-clarified", "issue"),
        ("context-recorded", "context"),
        ("memory-governed", "memory"),
        ("skill-applied", "skill"),
        ("mcp-boundary", "mcp"),
        ("change-evidence", "change"),
        ("tests-evidence", "tests"),
        ("review-evidence", "review"),
        ("delivery-evidence", "delivery"),
        ("migration-complete", "migration"),
        ("rubric-complete", "rubric"),
        ("offline-deterministic", "offline"),
    )
    return [
        {"id": check_id, "result": "passed" if flags[field] else "failed"}
        for check_id, field in fields
    ]


def load_enterprise_capstone_checks(
    evidence_file: Path,
    *,
    expected_course_version: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate status-only evidence and rederive its public result.

    The fixture deliberately carries no issue text, source diff, command log,
    account data, path, or model output.  The checker verifies only the
    stable enterprise workflow states and the fixed synthetic fault contract.
    """

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(
            f"Enterprise capstone evidence fixture not found: {evidence_file.name}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid enterprise capstone JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Enterprise capstone evidence must be a JSON object")

    # The browser lab may expose a count such as ``12/12 项证据``.  Normalize
    # only this parsed copy to the shared machine-facing evidence summary.
    if value.get("result") == "passed":
        value["summary"] = "所有必需证据均已通过。"
    elif value.get("result") == "partial":
        value["summary"] = "部分证据已通过，仍有证据需要补齐。"
    document = validate_evidence_document(value)
    if document["lesson_id"] != ENTERPRISE_CAPSTONE_LESSON_ID:
        raise EvidenceError(
            "Enterprise capstone fixture lesson_id does not match the requested lesson"
        )
    if document["course_version"] != expected_course_version:
        raise EvidenceError(
            "Enterprise capstone fixture course_version does not match the current course"
        )

    experiment = value.get("experiment")
    if not isinstance(experiment, dict):
        raise EvidenceError("Enterprise capstone evidence requires an experiment object")
    _reject_sensitive_unknown_fields(experiment, "Enterprise capstone experiment")
    if "issue_body" in experiment:
        raise EvidenceError("Enterprise capstone experiment contains a sensitive field: issue_body")
    expected_fields = {
        "version",
        "baseline_id",
        "input",
        "context",
        "memory",
        "skill",
        "mcp",
        "artifacts",
        "migration",
        "rubric",
        "offline",
        "fault",
    }
    if set(experiment) != expected_fields:
        raise EvidenceError("Enterprise capstone experiment fields are invalid")
    if experiment["version"] != ENTERPRISE_CAPSTONE_VERSION:
        raise EvidenceError("Unsupported enterprise capstone experiment version")
    if experiment["baseline_id"] != ENTERPRISE_CAPSTONE_BASELINE_ID:
        raise EvidenceError("Enterprise capstone baseline_id is unsupported")

    input_id = experiment["input"]
    fault = experiment["fault"]
    if input_id not in ENTERPRISE_CAPSTONE_INPUTS:
        raise EvidenceError("Enterprise capstone input variant is unsupported")
    if fault not in ENTERPRISE_CAPSTONE_FAULTS:
        raise EvidenceError("Enterprise capstone fault is unsupported")

    bool_fields = {"context", "memory", "skill", "mcp", "migration", "rubric", "offline"}
    if any(not isinstance(experiment[field], bool) for field in bool_fields):
        raise EvidenceError("Enterprise capstone experiment flags must be booleans")
    artifacts = experiment["artifacts"]
    if not isinstance(artifacts, dict):
        raise EvidenceError("Enterprise capstone artifacts must be an object")
    _reject_sensitive_unknown_fields(artifacts, "Enterprise capstone artifacts")
    artifact_fields = {"change", "tests", "review", "delivery", "evidence"}
    if set(artifacts) != artifact_fields or any(
        not isinstance(artifacts[field], bool) for field in artifact_fields
    ):
        raise EvidenceError(
            "Enterprise capstone artifacts must cover boolean change, tests, review, delivery and evidence"
        )

    expected = _expected_flags(input_id, fault)
    actual = {
        "issue": expected["issue"],
        "context": experiment["context"],
        "memory": experiment["memory"],
        "skill": experiment["skill"],
        "mcp": experiment["mcp"],
        "change": artifacts["change"],
        "tests": artifacts["tests"],
        "review": artifacts["review"],
        "delivery": artifacts["delivery"],
        "evidence": artifacts["evidence"],
        "migration": experiment["migration"],
        "rubric": experiment["rubric"],
        "offline": experiment["offline"],
    }
    if actual != expected:
        raise EvidenceError("Enterprise capstone checks do not match the recorded experiment")

    derived = _checks(actual)
    supplied = document["evidence"]
    if [check["id"] for check in supplied] != list(ENTERPRISE_CAPSTONE_CHECK_IDS):
        raise EvidenceError("Enterprise capstone evidence IDs are invalid")
    if supplied != derived:
        raise EvidenceError("Enterprise capstone checks do not match the recorded experiment")
    expected_result = (
        "passed" if all(check["result"] == "passed" for check in derived) else "partial"
    )
    if document["result"] != expected_result:
        raise EvidenceError("Enterprise capstone result does not match its evidence")
    return derived, {
        "version": ENTERPRISE_CAPSTONE_VERSION,
        "baseline_id": ENTERPRISE_CAPSTONE_BASELINE_ID,
        "input": input_id,
        "context": actual["context"],
        "memory": actual["memory"],
        "skill": actual["skill"],
        "mcp": actual["mcp"],
        "artifacts": {
            field: actual[field]
            for field in ("change", "tests", "review", "delivery", "evidence")
        },
        "migration": actual["migration"],
        "rubric": actual["rubric"],
        "offline": actual["offline"],
        "fault": fault,
    }
