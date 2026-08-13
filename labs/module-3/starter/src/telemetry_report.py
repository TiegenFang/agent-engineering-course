"""Small, dependency-free report tool used by the Codex repository lab."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Iterable


def _parse_row(row: dict[str, str]) -> float | None:
    """Return a Celsius reading, or None for a malformed/unsupported row.

    The Fahrenheit branch is intentionally defective in the starter task.  A
    learner should fix it without changing the public report schema.
    """

    try:
        datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        value = float(row["value"])
    except (KeyError, TypeError, ValueError):
        return None
    unit = row.get("unit", "").strip().upper()
    if unit == "C":
        return value
    if unit == "F":
        return value  # Intentional starter defect: convert Fahrenheit to Celsius.
    return None


def summarize(rows: Iterable[dict[str, str]]) -> dict[str, object]:
    readings = [value for row in rows if (value := _parse_row(row)) is not None]
    return {
        "schema": "telemetry-report-v1",
        "valid_count": len(readings),
        "mean_celsius": round(fmean(readings), 3) if readings else None,
        "unit": "C",
    }


def build_report(input_path: Path) -> dict[str, object]:
    with input_path.open(newline="", encoding="utf-8") as handle:
        return summarize(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a safe telemetry summary")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
