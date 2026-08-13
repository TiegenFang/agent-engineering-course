"""Offline T24 enterprise Issue-to-PR capstone lab.

The runner uses only synthetic status fixtures and the Python standard
library. It never calls a Coding Agent, model API, MCP server, or external
repository.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COURSE_VERSION = json.loads((ROOT / "course-version.json").read_text(encoding="utf-8"))["course_version"]
CHECK_IDS = [
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
]
INPUTS = {
    "feature-issue": {"kind": "feature", "title": "报告中增加夜班摘要"},
    "bug-fix": {"kind": "bug", "title": "修复压力单位换算"},
}
FAULTS = {"none", "ambiguous-issue", "test-failure", "review-requested", "mcp-denied"}


def flags_for(variant: str, fault: str) -> dict[str, bool]:
    if variant not in INPUTS:
        raise ValueError(f"unsupported input: {variant}")
    if fault not in FAULTS:
        raise ValueError(f"unsupported fault: {fault}")
    ambiguous = fault == "ambiguous-issue"
    return {
        "context": not ambiguous,
        "memory": True,
        "skill": True,
        "mcp": fault != "mcp-denied",
        "change": not ambiguous,
        "tests": fault != "test-failure" and not ambiguous,
        "review": fault != "review-requested" and not ambiguous,
        "delivery": fault == "none",
        "evidence": True,
        "migration": variant == "bug-fix" and not ambiguous,
        "rubric": fault == "none" and variant == "bug-fix",
        "offline": True,
    }


def build_run(variant: str, fault: str) -> dict[str, object]:
    flags = flags_for(variant, fault)
    checks = []
    check_fields = [
        ("issue-clarified", "context"),
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
    ]
    for check_id, field in check_fields:
        checks.append({"id": check_id, "result": "passed" if flags[field] else "failed"})
    return {
        "version": "1",
        "baseline_id": "telemetry-report-issue-v1",
        "input": variant,
        **flags,
        "fault": fault,
        "checks": checks,
    }


def write_outputs(output: Path, run: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    checks = run["checks"]
    assert isinstance(checks, list)
    result = "passed" if all(check["result"] == "passed" for check in checks) else "partial"
    input_id = str(run["input"])
    fault = str(run["fault"])
    contract = INPUTS[input_id]
    flags = {key: bool(run[key]) for key in (
        "context", "memory", "skill", "mcp", "change", "tests", "review",
        "delivery", "evidence", "migration", "rubric", "offline",
    )}

    (output / "issue-clarification.md").write_text(
        "# Synthetic Issue clarification\n\n"
        f"- kind: `{contract['kind']}`\n"
        f"- title: `{contract['title']}`\n"
        "- non-goal: no production deployment or external data\n"
        "- acceptance: change, tests, review and delivery evidence\n",
        encoding="utf-8",
    )
    (output / "change-summary.md").write_text(
        "# Synthetic change evidence\n\n"
        f"- input: `{input_id}`\n- change evidence: `{flags['change']}`\n"
        "- owner: one coordinator\n- data: synthetic telemetry only\n",
        encoding="utf-8",
    )
    (output / "tests.txt").write_text(
        "Synthetic test command: python -m unittest\n"
        f"status: {'passed' if flags['tests'] else 'failed; recover and rerun'}\n",
        encoding="utf-8",
    )
    (output / "review.md").write_text(
        "# Synthetic review record\n\n"
        f"status: {'approved' if flags['review'] else 'changes-requested'}\n"
        "reviewer: designated human reviewer\n",
        encoding="utf-8",
    )
    (output / "delivery.md").write_text(
        "# Synthetic delivery note\n\n"
        f"status: {'ready-for-human-merge' if flags['delivery'] else 'blocked-until-recovery'}\n"
        "side effects: none; no remote push was performed\n",
        encoding="utf-8",
    )
    record = {
        "version": "1",
        "input": input_id,
        "fault": fault,
        "context": flags["context"],
        "memory": flags["memory"],
        "skill": flags["skill"],
        "mcp": flags["mcp"],
        "recovery": "safe-default-rerun" if fault != "none" else "not-needed",
    }
    (output / "enterprise-record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    evidence = {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t24-enterprise-capstone",
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。" if result == "passed" else "部分证据已通过，仍有证据需要补齐。",
        "evidence": checks,
        "experiment": {
            "version": "1",
            "baseline_id": "telemetry-report-issue-v1",
            "input": input_id,
            "context": flags["context"],
            "memory": flags["memory"],
            "skill": flags["skill"],
            "mcp": flags["mcp"],
            "artifacts": {
                field: flags[field]
                for field in ("change", "tests", "review", "delivery", "evidence")
            },
            "migration": flags["migration"],
            "rubric": flags["rubric"],
            "offline": flags["offline"],
            "fault": fault,
        },
    }
    (output / "t24-enterprise-capstone-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline T24 enterprise capstone fixture")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=sorted(INPUTS), default="feature-issue")
    parser.add_argument("--fault", choices=sorted(FAULTS), default="none")
    args = parser.parse_args()
    write_outputs(args.output.resolve(), build_run(args.variant, args.fault))
    print(f"Wrote T24 enterprise evidence to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
