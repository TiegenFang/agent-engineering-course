"""Run the deterministic T30 research API fixture without a provider SDK."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_api_adapter import build_evidence


def main() -> int:
    parser = argparse.ArgumentParser(prog="t30-research-api-fixture")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("temperature-daily", "pressure-night"), default="pressure-night")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    course_version = json.loads((root / "course-version.json").read_text(encoding="utf-8"))["course_version"]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence(course_version, args.variant)
    (output / "t30-research-api-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "t30-live-smoke-plan.json").write_text(
        json.dumps(evidence["experiment"]["live_smoke"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"lesson_id": evidence["lesson_id"], "result": evidence["result"], "output": "t30-research-api-evidence.json"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
