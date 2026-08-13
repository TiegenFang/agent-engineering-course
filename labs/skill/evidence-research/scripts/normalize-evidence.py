"""Normalize the synthetic evidence fixture used by the Skill lesson.

This script is intentionally dependency-free and offline. It reads one
explicit JSON input and emits stable statuses; it never contacts a service,
executes a command from the input, or includes a filesystem path in output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SCRIPT_VERSION = "1"


class FixtureError(ValueError):
    """Raised when the local synthetic fixture violates its small contract."""


def identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise FixtureError(f"{label} must be a lowercase identifier")
    return value


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FixtureError("input fixture was not found") from exc
    except json.JSONDecodeError as exc:
        raise FixtureError(f"input fixture is invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict) or value.get("fixture_version") != SCRIPT_VERSION:
        raise FixtureError("fixture_version must be 1")
    if not isinstance(value.get("claims"), list) or not value["claims"]:
        raise FixtureError("claims must be a non-empty list")
    if not isinstance(value.get("sources"), list) or not value["sources"]:
        raise FixtureError("sources must be a non-empty list")
    return value


def normalize(value: dict[str, Any]) -> dict[str, Any]:
    claim_ids: list[str] = []
    for index, claim in enumerate(value["claims"]):
        if not isinstance(claim, dict):
            raise FixtureError(f"claim {index} must be an object")
        claim_id = identifier(claim.get("id"), f"claim {index}.id")
        if claim_id in claim_ids:
            raise FixtureError(f"duplicate claim id: {claim_id}")
        claim_ids.append(claim_id)

    source_ids: set[str] = set()
    support_map = {claim_id: 0 for claim_id in claim_ids}
    for index, source in enumerate(value["sources"]):
        if not isinstance(source, dict):
            raise FixtureError(f"source {index} must be an object")
        source_id = identifier(source.get("id"), f"source {index}.id")
        if source_id in source_ids:
            raise FixtureError(f"duplicate source id: {source_id}")
        source_ids.add(source_id)
        supports = source.get("supports")
        if not isinstance(supports, list) or not supports:
            raise FixtureError(f"source {source_id}.supports must be a non-empty list")
        if len(supports) != len(set(supports)):
            raise FixtureError(f"source {source_id}.supports repeats a claim")
        for claim_id in supports:
            if claim_id not in support_map:
                raise FixtureError(f"source {source_id} references an unknown claim")
            support_map[claim_id] += 1

    claims = [
        {
            "id": claim_id,
            "status": "supported" if support_map[claim_id] else "needs-source",
            "source_count": support_map[claim_id],
        }
        for claim_id in claim_ids
    ]
    checks = [
        {
            "id": "claims-normalized",
            "result": "passed" if claims else "failed",
        },
        {
            "id": "sources-linked",
            "result": "passed" if all(item["source_count"] > 0 for item in claims) else "failed",
        },
    ]
    return {
        "contract": "evidence-research/v1",
        "skill_id": "evidence-research",
        "fixture_version": SCRIPT_VERSION,
        "claims": claims,
        "checks": checks,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize the offline Skill evidence fixture")
    default_input = Path(__file__).resolve().parents[1] / "assets" / "telemetry-sample.json"
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = normalize(load_fixture(args.input.resolve()))
    except (FixtureError, OSError) as exc:
        print(f"Skill fixture validation failed: {exc}", file=sys.stderr)
        return 1
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.resolve().write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
