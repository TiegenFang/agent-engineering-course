"""Dependency-free pressure report used by the Claude Code migration lab."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Iterable


ALARM_THRESHOLD_KPA = 101.32


def _parse_row(row: dict[str, str]) -> float | None:
    """Return a kPa reading, or None for malformed/unsupported input.

    The psi and bar branches are intentionally defective in the starter task.
    """

    try:
        datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        value = float(row["pressure"])
    except (KeyError, TypeError, ValueError):
        return None
    unit = row.get("unit", "").strip().lower()
    if unit == "kpa":
        return value
    if unit == "psi":
        return value  # Intentional defect: convert psi to kPa.
    if unit == "bar":
        return value  # Intentional defect: convert bar to kPa.
    return None


def summarize(rows: Iterable[dict[str, str]]) -> dict[str, object]:
    readings = [value for row in rows if (value := _parse_row(row)) is not None]
    return {
        "schema": "pressure-report-v1",
        "valid_count": len(readings),
        "mean_kpa": round(fmean(readings), 3) if readings else None,
        "peak_kpa": round(max(readings), 3) if readings else None,
        "alarm_count": sum(value > ALARM_THRESHOLD_KPA for value in readings),
        "unit": "kPa",
    }


def build_report(input_path: Path) -> dict[str, object]:
    with input_path.open(newline="", encoding="utf-8") as handle:
        return summarize(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a safe pressure summary")
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
