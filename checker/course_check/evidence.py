"""The anonymous evidence document exchanged with the course website.

This module is deliberately small and dependency-free.  The checker may look
at local files while it is running, but the public document only contains
stable identifiers, result states, and a short generated summary.  No local
path, source text, credential, or raw experiment data is copied across the
browser boundary.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
import re
from typing import Any


EVIDENCE_CONTRACT = "agent-engineering-course/evidence"
EVIDENCE_CONTRACT_VERSION = "1"
CHECK_RESULTS = frozenset({"passed", "failed", "alternative"})
DOCUMENT_RESULTS = frozenset({"passed", "partial", "failed", "alternative"})

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SENSITIVE_NAME = re.compile(
    r"(?:path|file|source|secret|token|password|credential|api[_-]?key|raw|payload|content|cwd|home|user|email)",
    re.IGNORECASE,
)
_DOCUMENT_FIELDS = {
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
_SUMMARY_BY_RESULT = {
    "passed": "所有必需证据均已通过。",
    "partial": "部分证据已通过，仍有证据需要补齐。",
    "failed": "证据未通过，请根据本地检查结果恢复后重试。",
    "alternative": "检测到满足验收目标的替代实现。",
}


class EvidenceError(ValueError):
    """Raised when an evidence document cannot cross the public seam."""


def _require_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or not _IDENTIFIER.fullmatch(value):
        raise EvidenceError(f"{label} must be a safe identifier")
    return value


def _require_result(value: Any, label: str, allowed: Iterable[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise EvidenceError(f"{label} must be one of: {choices}")
    return value


def _require_iso_date(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise EvidenceError(f"{label} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceError(f"{label} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise EvidenceError(f"{label} must be an ISO date")
    return value


def _reject_sensitive_unknown_fields(value: Mapping[str, Any], label: str) -> None:
    """Reject fields that could smuggle private data through an output seam.

    Unknown non-sensitive fields are ignored by the validator for forward
    compatibility.  Names that clearly describe private data are rejected so
    a caller cannot accidentally treat this contract as a source-data
    transport.
    """

    for field in value:
        if _SENSITIVE_NAME.search(str(field)):
            raise EvidenceError(f"{label} contains a sensitive field: {field}")


def classify_checks(results: Sequence[str]) -> str:
    """Classify check outcomes into the four learner-visible result states."""

    if not results:
        raise EvidenceError("At least one evidence check is required")
    normalized = [
        _require_result(result, "check result", CHECK_RESULTS) for result in results
    ]
    if all(result == "passed" for result in normalized):
        return "passed"
    if all(result == "failed" for result in normalized):
        return "failed"
    if all(result in {"passed", "alternative"} for result in normalized) and any(
        result == "alternative" for result in normalized
    ):
        return "alternative"
    return "partial"


def _normalize_checks(checks: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)):
        raise EvidenceError("evidence checks must be a list")
    if not checks:
        raise EvidenceError("At least one evidence check is required")

    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, raw_check in enumerate(checks):
        if not isinstance(raw_check, Mapping):
            raise EvidenceError(f"evidence check {index} must be an object")
        _reject_sensitive_unknown_fields(raw_check, f"evidence check {index}")
        if "id" not in raw_check or "result" not in raw_check:
            raise EvidenceError(f"evidence check {index} needs id and result")
        check_id = _require_identifier(raw_check["id"], f"evidence check {index}.id")
        if check_id in seen_ids:
            raise EvidenceError(f"Duplicate evidence check id: {check_id}")
        seen_ids.add(check_id)
        result = _require_result(
            raw_check["result"], f"evidence check {check_id}.result", CHECK_RESULTS
        )
        normalized.append({"id": check_id, "result": result})
    return normalized


def build_evidence_document(
    *,
    course_version: str,
    lesson_id: str,
    checks: Sequence[Mapping[str, Any]],
    checked_on: str | None = None,
) -> dict[str, Any]:
    """Build a versioned, anonymous document suitable for website import."""

    safe_course_version = _require_identifier(course_version, "course_version")
    safe_lesson_id = _require_identifier(lesson_id, "lesson_id")
    normalized_checks = _normalize_checks(checks)
    result = classify_checks([check["result"] for check in normalized_checks])
    safe_checked_on = (
        _require_iso_date(checked_on, "checked_on")
        if checked_on is not None
        else date.today().isoformat()
    )
    return {
        "contract": EVIDENCE_CONTRACT,
        "contract_version": EVIDENCE_CONTRACT_VERSION,
        "course_version": safe_course_version,
        "lesson_id": safe_lesson_id,
        "result": result,
        "anonymous": True,
        "checked_on": safe_checked_on,
        "summary": _SUMMARY_BY_RESULT[result],
        "evidence": normalized_checks,
    }


def validate_evidence_document(value: Any) -> dict[str, Any]:
    """Validate and canonicalize a document received at the public seam.

    Unknown non-sensitive fields are intentionally ignored to allow additive
    checker versions.  The return value contains only the stable contract
    fields, which keeps export deterministic and prevents unknown input from
    being persisted by callers.
    """

    if not isinstance(value, Mapping):
        raise EvidenceError("Evidence document must be an object")
    _reject_sensitive_unknown_fields(value, "evidence document")
    missing = sorted(_DOCUMENT_FIELDS - set(value))
    if missing:
        raise EvidenceError(f"Evidence document is missing: {', '.join(missing)}")
    if value["contract"] != EVIDENCE_CONTRACT:
        raise EvidenceError("Unsupported evidence contract")
    if value["contract_version"] != EVIDENCE_CONTRACT_VERSION:
        raise EvidenceError("Unsupported evidence contract version")
    if value["anonymous"] is not True:
        raise EvidenceError("Evidence document must be anonymous")

    course_version = _require_identifier(value["course_version"], "course_version")
    lesson_id = _require_identifier(value["lesson_id"], "lesson_id")
    result = _require_result(value["result"], "result", DOCUMENT_RESULTS)
    checked_on = _require_iso_date(value["checked_on"], "checked_on")
    summary = value["summary"]
    if summary != _SUMMARY_BY_RESULT[result]:
        raise EvidenceError("Evidence summary does not match result")
    evidence = value["evidence"]
    normalized_checks = _normalize_checks(evidence)
    if classify_checks([check["result"] for check in normalized_checks]) != result:
        raise EvidenceError("Evidence result does not match its checks")
    return {
        "contract": EVIDENCE_CONTRACT,
        "contract_version": EVIDENCE_CONTRACT_VERSION,
        "course_version": course_version,
        "lesson_id": lesson_id,
        "result": result,
        "anonymous": True,
        "checked_on": checked_on,
        "summary": summary,
        "evidence": normalized_checks,
    }
