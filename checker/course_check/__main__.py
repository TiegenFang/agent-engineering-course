"""Public command-line entry point for the local course checker."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .evidence import EvidenceError, build_evidence_document


EXPECTED_BOUNDARIES = {
    "site": "site",
    "labs": "labs",
    "checker": "checker",
    "docs": "docs",
}
ENVIRONMENT_LESSON_ID = "t05-environment"
ENVIRONMENT_CHECK_IDS = frozenset(
    {
        "powershell-7",
        "editor-command",
        "python-on-path",
        "python-version",
        "git-on-path",
        "git-version",
        "github-account",
        "coding-agent-account",
    }
)
ENVIRONMENT_PLATFORM_SHELLS = {
    "windows": frozenset({"powershell"}),
    "macos": frozenset({"powershell", "zsh"}),
    "linux": frozenset({"powershell", "bash"}),
}

LESSON_REQUIRED_FIELDS = {
    "id",
    "title",
    "stage",
    "duration_minutes",
    "prerequisites",
    "outcomes",
    "artifacts",
    "primary_tool",
    "migration_tool",
    "platforms",
    "versions",
    "verified_on",
    "access",
    "risk",
    "sources",
    "licenses",
}

COURSE_REQUIRED_FIELDS = {
    "name",
    "subtitle",
    "positioning",
    "core_duration",
    "advanced_duration",
}

CONTRACT_REQUIRED_FIELDS = {"content", "lesson_schema", "sources"}
PLATFORM_REQUIRED_FIELDS = {"primary", "secondary"}
VERSION_REQUIRED_FIELDS = {"client", "sdk", "model", "protocol"}
ACCESS_REQUIRED_FIELDS = {"accounts", "cost", "network"}
RISK_REQUIRED_FIELDS = {"permissions", "side_effects", "staleness"}
SOURCE_REQUIRED_FIELDS = {
    "id",
    "title",
    "url",
    "source_role",
    "pinned_version",
    "usage",
    "license_or_terms",
    "copied_assets",
}


class ContractError(ValueError):
    """Raised when the public Foundation contract is incomplete."""


def load_json(root: Path, relative_path: str) -> dict[str, Any]:
    relative = Path(relative_path)
    if not relative_path or relative.is_absolute() or ".." in relative.parts:
        raise ContractError(f"Unsafe contract path: {relative_path or '<empty>'}")
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"Missing contract file: {relative_path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON in {relative_path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Contract must be a JSON object: {relative_path}")
    return value


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object")
    return value


def require_fields(
    value: dict[str, Any], required: set[str], label: str, *, exact: bool = True
) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ContractError(f"{label} is missing: {', '.join(missing)}")
    if exact:
        unexpected = sorted(set(value) - required)
        if unexpected:
            raise ContractError(f"{label} has unexpected fields: {', '.join(unexpected)}")


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value


def require_string_list(
    value: Any, label: str, *, allow_empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "a" if allow_empty else "a non-empty"
        raise ContractError(f"{label} must be {qualifier} list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContractError(f"{label} must contain only non-empty strings")
    return value


def require_iso_date(value: Any, label: str) -> str:
    raw = require_string(value, label)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ContractError(f"{label} must be an ISO date (YYYY-MM-DD)") from exc
    if parsed.isoformat() != raw:
        raise ContractError(f"{label} must be an ISO date (YYYY-MM-DD)")
    return raw


def validate_named_string_object(
    value: Any, required: set[str], label: str
) -> dict[str, Any]:
    item = require_object(value, label)
    require_fields(item, required, label)
    for field in required:
        require_string(item[field], f"{label}.{field}")
    return item


def validate_lesson_schema(schema: dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise ContractError("Lesson schema type must be object")
    required = schema.get("required")
    if not isinstance(required, list) or set(required) != LESSON_REQUIRED_FIELDS:
        raise ContractError("Lesson schema required fields do not match the content contract")
    if schema.get("additionalProperties") is not False:
        raise ContractError("Lesson schema must reject additional properties")


def validate_lesson(value: Any, index: int) -> dict[str, Any]:
    lesson = require_object(value, f"Lesson at index {index}")
    lesson_label = f"Lesson {lesson.get('id', '<unknown>')}"
    require_fields(lesson, LESSON_REQUIRED_FIELDS, lesson_label)

    require_string(lesson["id"], f"{lesson_label}.id")
    require_string(lesson["title"], f"{lesson_label}.title")
    require_string(lesson["stage"], f"{lesson_label}.stage")
    duration = lesson["duration_minutes"]
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
        raise ContractError(f"{lesson_label}.duration_minutes must be a positive integer")

    require_string_list(
        lesson["prerequisites"], f"{lesson_label}.prerequisites", allow_empty=True
    )
    for field in ("outcomes", "artifacts", "sources", "licenses"):
        require_string_list(lesson[field], f"{lesson_label}.{field}")
    require_string(lesson["primary_tool"], f"{lesson_label}.primary_tool")
    require_string(lesson["migration_tool"], f"{lesson_label}.migration_tool")

    platforms = require_object(lesson["platforms"], f"{lesson_label}.platforms")
    require_fields(platforms, PLATFORM_REQUIRED_FIELDS, f"{lesson_label}.platforms")
    require_string(platforms["primary"], f"{lesson_label}.platforms.primary")
    require_string_list(
        platforms["secondary"],
        f"{lesson_label}.platforms.secondary",
        allow_empty=True,
    )

    validate_named_string_object(
        lesson["versions"], VERSION_REQUIRED_FIELDS, f"{lesson_label}.versions"
    )

    access = require_object(lesson["access"], f"{lesson_label}.access")
    require_fields(access, ACCESS_REQUIRED_FIELDS, f"{lesson_label}.access")
    require_string_list(
        access["accounts"], f"{lesson_label}.access.accounts", allow_empty=True
    )
    require_string(access["cost"], f"{lesson_label}.access.cost")
    require_string(access["network"], f"{lesson_label}.access.network")

    validate_named_string_object(
        lesson["risk"], RISK_REQUIRED_FIELDS, f"{lesson_label}.risk"
    )
    require_iso_date(lesson["verified_on"], f"{lesson_label}.verified_on")
    return lesson


def validate_source_entries(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    if sources.get("ledger_version") != "1":
        raise ContractError("Unsupported source ledger version")
    require_iso_date(sources.get("verified_on"), "Source ledger verified_on")
    entries = sources.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ContractError("Source ledger must contain at least one entry")

    validated: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for index, value in enumerate(entries):
        entry = require_object(value, f"Source entry at index {index}")
        label = f"Source entry {entry.get('id', '<unknown>')}"
        require_fields(entry, SOURCE_REQUIRED_FIELDS, label, exact=False)
        for field in SOURCE_REQUIRED_FIELDS - {"copied_assets"}:
            require_string(entry[field], f"{label}.{field}")
        if not isinstance(entry["copied_assets"], bool):
            raise ContractError(f"{label}.copied_assets must be a boolean")
        source_id = entry["id"]
        if source_id in source_ids:
            raise ContractError(f"Duplicate source id: {source_id}")
        source_ids.add(source_id)
        validated.append(entry)
    return validated, source_ids


def validate_foundation(root: Path) -> str:
    contract = load_json(root, "course-version.json")
    version = require_string(contract.get("course_version"), "course_version")
    require_iso_date(contract.get("released_on"), "released_on")
    validate_named_string_object(contract.get("course"), COURSE_REQUIRED_FIELDS, "course")

    if contract.get("boundaries") != EXPECTED_BOUNDARIES:
        raise ContractError("Workspace boundaries do not match the course contract")
    for relative_path in EXPECTED_BOUNDARIES.values():
        if not (root / relative_path).is_dir():
            raise ContractError(f"Missing workspace boundary: {relative_path}")

    contracts = require_object(contract.get("contracts"), "contracts")
    require_fields(contracts, CONTRACT_REQUIRED_FIELDS, "contracts")
    for field in CONTRACT_REQUIRED_FIELDS:
        require_string(contracts[field], f"contracts.{field}")

    lesson_schema = load_json(root, contracts["lesson_schema"])
    validate_lesson_schema(lesson_schema)

    content = load_json(root, contracts["content"])
    if content.get("contract_version") != "1":
        raise ContractError("Unsupported content contract version")
    lessons = content.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        raise ContractError("Content contract must contain at least one lesson")
    validated_lessons = [validate_lesson(lesson, index) for index, lesson in enumerate(lessons)]
    lesson_ids = [lesson["id"] for lesson in validated_lessons]
    if len(lesson_ids) != len(set(lesson_ids)):
        raise ContractError("Lesson ids must be unique")
    known_lesson_ids = set(lesson_ids)
    for lesson in validated_lessons:
        prerequisite_ids = set(lesson["prerequisites"])
        if lesson["id"] in prerequisite_ids:
            raise ContractError(f"Lesson {lesson['id']} cannot require itself")
        unknown_prerequisites = sorted(prerequisite_ids - known_lesson_ids)
        if unknown_prerequisites:
            raise ContractError(
                f"Lesson {lesson['id']} references unknown prerequisites: "
                + ", ".join(unknown_prerequisites)
            )

    sources = load_json(root, contracts["sources"])
    _, source_ids = validate_source_entries(sources)
    for lesson in validated_lessons:
        unknown_sources = sorted(set(lesson["sources"]) - source_ids)
        if unknown_sources:
            raise ContractError(
                f"Lesson {lesson['id']} references unknown sources: "
                + ", ".join(unknown_sources)
            )

    return version


def load_evidence_checks(
    evidence_file: Path, *, expected_lesson_id: str
) -> list[dict[str, Any]]:
    """Read only public check states from a local evidence fixture.

    Fixture details are intentionally discarded.  This lets a learner check a
    local implementation while ensuring that the generated browser document
    cannot accidentally contain a path, source excerpt, or raw data value.
    """

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Evidence fixture must be a JSON object")
    fixture_lesson_id = value.get("lesson_id", expected_lesson_id)
    if fixture_lesson_id != expected_lesson_id:
        raise EvidenceError("Evidence fixture lesson_id does not match the requested lesson")
    checks = value.get("checks")
    if not isinstance(checks, list):
        raise EvidenceError("Evidence fixture checks must be a list")
    return checks


def load_environment_checks(
    evidence_file: Path,
) -> list[dict[str, Any]]:
    """Validate the complete, status-only environment diagnostic shape."""

    try:
        value = json.loads(evidence_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Evidence fixture not found: {evidence_file.name}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid evidence fixture JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("Evidence fixture must be a JSON object")

    if value.get("lesson_id") != ENVIRONMENT_LESSON_ID:
        raise EvidenceError("Environment fixture lesson_id does not match the requested lesson")
    platform = value.get("platform")
    shell = value.get("shell")
    if not isinstance(platform, str) or platform not in ENVIRONMENT_PLATFORM_SHELLS:
        raise EvidenceError("Environment fixture platform must be windows, macos, or linux")
    if not isinstance(shell, str) or shell not in ENVIRONMENT_PLATFORM_SHELLS[platform]:
        raise EvidenceError("Environment fixture shell does not match its platform")

    checks = value.get("checks")
    if not isinstance(checks, list):
        raise EvidenceError("Environment fixture checks must be a list")
    if any(not isinstance(check, dict) for check in checks):
        raise EvidenceError("Environment fixture checks must contain objects")
    check_ids = [check.get("id") for check in checks]
    if any(not isinstance(check_id, str) or not check_id for check_id in check_ids):
        raise EvidenceError("Environment fixture check ids must be non-empty strings")
    if len(check_ids) != len(set(check_ids)):
        raise EvidenceError("Environment fixture checks must not repeat an id")
    actual_ids = set(check_ids)
    missing = sorted(ENVIRONMENT_CHECK_IDS - actual_ids)
    unknown = sorted(actual_ids - ENVIRONMENT_CHECK_IDS)
    if missing or unknown or len(checks) != len(ENVIRONMENT_CHECK_IDS):
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unknown:
            details.append("unknown: " + ", ".join(str(item) for item in unknown))
        raise EvidenceError("Environment fixture checks are incomplete or unexpected (" + "; ".join(details) + ")")
    return checks


def check_lesson(
    root: Path,
    lesson_id: str,
    *,
    evidence_file: Path | None = None,
) -> dict[str, Any]:
    """Run a public lesson check and build its anonymous result."""

    if lesson_id not in {"t01-foundation", ENVIRONMENT_LESSON_ID}:
        raise ContractError(f"Unsupported evidence lesson: {lesson_id}")
    course_version = validate_foundation(root)
    if lesson_id == "t01-foundation":
        checks: list[dict[str, Any]] = [
            {"id": "course-version-lock", "result": "passed"},
            {"id": "foundation-contract", "result": "passed"},
        ]
        if evidence_file is not None:
            checks = load_evidence_checks(evidence_file, expected_lesson_id=lesson_id)
    else:
        if evidence_file is None:
            raise EvidenceError(
                "t05-environment requires --environment-file with the local diagnostic JSON"
            )
        checks = load_environment_checks(evidence_file)
    return build_evidence_document(
        course_version=course_version,
        lesson_id=lesson_id,
        checks=checks,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="course_check")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate course contracts")
    validate.add_argument("--root", type=Path, required=True)
    check = subparsers.add_parser(
        "check", help="check a lesson and emit an anonymous evidence document"
    )
    check.add_argument("lesson_id")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument(
        "--evidence-file",
        "--environment-file",
        dest="evidence_file",
        type=Path,
        help=(
            "local fixture containing lesson_id and check result states; "
            "use --environment-file for t05-environment"
        ),
    )
    check.add_argument(
        "--output",
        type=Path,
        help="write the anonymous evidence JSON to this path",
    )
    check.add_argument(
        "--json",
        action="store_true",
        help="print the anonymous evidence JSON instead of only a human summary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        try:
            version = validate_foundation(args.root.resolve())
        except ContractError as exc:
            print(f"Foundation validation failed: {exc}", file=sys.stderr)
            return 1
        print(f"Foundation validation passed: {version}")
        return 0
    if args.command == "check":
        try:
            document = check_lesson(
                args.root.resolve(),
                args.lesson_id,
                evidence_file=args.evidence_file.resolve()
                if args.evidence_file is not None
                else None,
            )
            encoded = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
            if args.output is not None:
                args.output.resolve().write_text(encoded, encoding="utf-8")
            if args.json:
                print(encoded, end="")
            else:
                print(
                    f"Evidence check {document['result']}: "
                    f"{document['lesson_id']} ({document['course_version']})"
                )
            return 0
        except (ContractError, EvidenceError, OSError) as exc:
            print(f"Evidence check failed: {exc}", file=sys.stderr)
            return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
