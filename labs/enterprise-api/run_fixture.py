"""Run the offline T31 enterprise API capstone fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LESSON_ID = "t31-enterprise-api"
COURSE_CONTRACT = "agent-engineering-course/evidence"
COURSE_CONTRACT_VERSION = "1"
COURSE_VERSION = "1.0.0"
CHECK_IDS = (
    "scope-bounded",
    "approval-gated",
    "structured-output",
    "budget-enforced",
    "recovery-observed",
    "evidence-redacted",
    "offline-deterministic",
)


def experiment_for(scenario: str) -> dict[str, object]:
    if scenario == "budget-stop":
        return {
            "version": "1",
            "baseline_id": "issue-to-pr-api-v1",
            "input_id": "issue-telemetry-validation-budget-v1",
            "requested_action": "draft-validation-plan",
            "high_impact_action": "merge-or-push",
            "approval_required": True,
            "approval_granted": False,
            "high_impact_executed": False,
            "side_effect": "none",
            "structured_output_valid": True,
            "output_schema_version": "issue-plan-v1",
            "failure_injected": False,
            "failure_class": "tool-timeout",
            "recovered": False,
            "recovery_action": "bounded-retry",
            "budget_usd": 0.0001,
            "estimated_cost_usd": 0.00045,
            "budget_status": "stopped",
            "model_call_started": False,
            "provider": "offline-fixture",
            "model": "offline-model-v1",
            "live_api_called": False,
            "public_summary_only": True,
            "runner_version": "enterprise-api-runner-v1",
        }
    if scenario != "baseline":
        raise ValueError(f"Unsupported T31 scenario: {scenario}")
    return {
        "version": "1",
        "baseline_id": "issue-to-pr-api-v1",
        "input_id": "issue-telemetry-validation-v1",
        "requested_action": "draft-validation-plan",
        "high_impact_action": "merge-or-push",
        "approval_required": True,
        "approval_granted": False,
        "high_impact_executed": False,
        "side_effect": "none",
        "structured_output_valid": True,
        "output_schema_version": "issue-plan-v1",
        "failure_injected": True,
        "failure_class": "tool-timeout",
        "recovered": True,
        "recovery_action": "bounded-retry",
        "budget_usd": 0.01,
        "estimated_cost_usd": 0.00045,
        "budget_status": "allowed",
        "model_call_started": True,
        "provider": "offline-fixture",
        "model": "offline-model-v1",
        "live_api_called": False,
        "public_summary_only": True,
        "runner_version": "enterprise-api-runner-v1",
    }


def document_for(scenario: str) -> dict[str, object]:
    experiment = experiment_for(scenario)
    passed = scenario == "baseline"
    results = ["passed" if passed else "failed"] * len(CHECK_IDS)
    if not passed:
        results[0] = "passed"
        results[1] = "passed"
        results[2] = "passed"
        results[5] = "passed"
        results[6] = "passed"
    result = "passed" if passed else "partial"
    summary = "所有必需证据均已通过。" if passed else "部分证据已通过，仍有证据需要补齐。"
    return {
        "contract": COURSE_CONTRACT,
        "contract_version": COURSE_CONTRACT_VERSION,
        "course_version": COURSE_VERSION,
        "lesson_id": LESSON_ID,
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": summary,
        "evidence": [
            {"id": check_id, "result": check_result}
            for check_id, check_result in zip(CHECK_IDS, results, strict=True)
        ],
        "experiment": experiment,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("baseline", "budget-stop"), default="baseline")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.resolve().write_text(
        json.dumps(document_for(args.scenario), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
