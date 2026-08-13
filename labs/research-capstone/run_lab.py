"""Offline T23 research capstone lab using only the Python standard library."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


COURSE_VERSION = json.loads(
    (Path(__file__).resolve().parents[2] / "course-version.json").read_text(encoding="utf-8")
)["course_version"]
CHECK_IDS = [
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
]
VARIANTS = {
    "temperature-daily": {"subject": "temperature", "unit": "°C", "limit": 5},
    "pressure-night": {"subject": "pressure", "unit": "kPa", "limit": 3},
}


def build_run(variant: str, fault: str) -> dict[str, object]:
    if variant not in VARIANTS:
        raise ValueError(f"unsupported variant: {variant}")
    if fault not in {"none", "missing-values", "stale-memory", "mcp-denied"}:
        raise ValueError(f"unsupported fault: {fault}")
    flags = {
        "context": True,
        "memory": fault != "stale-memory",
        "skill": True,
        "mcp": fault != "mcp-denied",
        "script": True,
        "figure": fault != "missing-values",
        "record": True,
        "report": fault == "none",
        "evidence": True,
        "migration": variant == "pressure-night",
        "rubric": fault == "none" and variant == "pressure-night",
        "offline": True,
    }
    checks = []
    for check_id, field in [
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
    ]:
        checks.append({"id": check_id, "result": "passed" if flags[field] else "failed"})
    return {
        "version": "1",
        "baseline_id": "telemetry-research-v1",
        "input": variant,
        "contract": VARIANTS[variant],
        **flags,
        "fault": fault,
        "checks": checks,
    }


def write_outputs(output: Path, run: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    checks = run["checks"]
    assert isinstance(checks, list)
    passed = sum(check["result"] == "passed" for check in checks)
    result = "passed" if passed == len(CHECK_IDS) else "partial"
    (output / "analysis.py").write_text(
        "# Re-run this synthetic analysis with Python 3.11+; no external data is read.\n"
        "result = {'subject': '" + str(run["contract"]["subject"]) + "', 'limit': "
        + str(run["contract"]["limit"]) + "}\n",
        encoding="utf-8",
    )
    (output / "figure.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="160" role="img" '
        'aria-label="Synthetic telemetry summary"><rect width="480" height="160" fill="#13243a"/>'
        '<polyline points="24,120 100,80 176,96 252,56 328,72 404,36" fill="none" '
        'stroke="#7ee0c3" stroke-width="8"/><text x="24" y="148" fill="#fff">synthetic data</text></svg>\n',
        encoding="utf-8",
    )
    record = {
        "version": "1",
        "input": run["input"],
        "context": run["context"],
        "memory": run["memory"],
        "skill": run["skill"],
        "mcp": run["mcp"],
        "fault": run["fault"],
        "recovery": "safe-default-rerun" if run["fault"] != "none" else "not-needed",
    }
    (output / "experiment-record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "report.md").write_text(
        "# Synthetic research report\n\n"
        f"- input: `{run['input']}`\n- result: `{result}`\n"
        "- data: synthetic telemetry only\n- network/API: none\n\n"
        "The figure and script are reproducible from the fixed offline fixture.\n",
        encoding="utf-8",
    )
    evidence = {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t23-research-capstone",
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": (
            "所有必需证据均已通过。"
            if result == "passed"
            else "部分证据已通过，仍有证据需要补齐。"
        ),
        "evidence": checks,
        "experiment": {
            "version": "1",
            "baseline_id": "telemetry-research-v1",
            "input": run["input"],
            "context": run["context"],
            "memory": run["memory"],
            "skill": run["skill"],
            "mcp": run["mcp"],
            "artifacts": {
                "script": run["script"],
                "figure": run["figure"],
                "record": run["record"],
                "report": run["report"],
                "evidence": run["evidence"],
            },
            "migration": run["migration"],
            "rubric": run["rubric"],
            "offline": run["offline"],
            "fault": run["fault"],
        },
    }
    (output / "t23-research-capstone-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="temperature-daily")
    parser.add_argument("--fault", choices=["none", "missing-values", "stale-memory", "mcp-denied"], default="none")
    args = parser.parse_args()
    write_outputs(args.output.resolve(), build_run(args.variant, args.fault))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
