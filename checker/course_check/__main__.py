"""Public command-line entry point for the local course checker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_BOUNDARIES = {
    "site": "site",
    "labs": "labs",
    "checker": "checker",
    "docs": "docs",
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


class ContractError(ValueError):
    """Raised when the public Foundation contract is incomplete."""


def load_json(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"Missing contract file: {relative_path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON in {relative_path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Contract must be a JSON object: {relative_path}")
    return value


def validate_foundation(root: Path) -> str:
    contract = load_json(root, "course-version.json")
    version = contract.get("course_version")
    if not isinstance(version, str) or not version:
        raise ContractError("course_version must be a non-empty string")

    if contract.get("boundaries") != EXPECTED_BOUNDARIES:
        raise ContractError("Workspace boundaries do not match the course contract")
    for relative_path in EXPECTED_BOUNDARIES.values():
        if not (root / relative_path).is_dir():
            raise ContractError(f"Missing workspace boundary: {relative_path}")

    contracts = contract.get("contracts")
    if not isinstance(contracts, dict):
        raise ContractError("contracts must be a JSON object")

    content = load_json(root, str(contracts.get("content", "")))
    if content.get("contract_version") != "1":
        raise ContractError("Unsupported content contract version")
    lessons = content.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        raise ContractError("Content contract must contain at least one lesson")
    for lesson in lessons:
        if not isinstance(lesson, dict):
            raise ContractError("Every lesson must be a JSON object")
        missing = sorted(LESSON_REQUIRED_FIELDS - set(lesson))
        if missing:
            raise ContractError(
                f"Lesson {lesson.get('id', '<unknown>')} is missing: {', '.join(missing)}"
            )

    sources = load_json(root, str(contracts.get("sources", "")))
    entries = sources.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ContractError("Source ledger must contain at least one entry")
    source_ids = {entry.get("id") for entry in entries if isinstance(entry, dict)}
    for lesson in lessons:
        unknown_sources = sorted(set(lesson["sources"]) - source_ids)
        if unknown_sources:
            raise ContractError(
                f"Lesson {lesson['id']} references unknown sources: "
                + ", ".join(unknown_sources)
            )

    return version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="course_check")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate course contracts")
    validate.add_argument("--root", type=Path, required=True)
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

