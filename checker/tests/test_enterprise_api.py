"""Public checker seam tests for T31 enterprise API capstone."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "checker"
COURSE_VERSION = json.loads((ROOT / "course-version.json").read_text(encoding="utf-8"))["course_version"]
CHECK_IDS = [
    "scope-bounded",
    "approval-gated",
    "structured-output",
    "budget-enforced",
    "recovery-observed",
    "evidence-redacted",
    "offline-deterministic",
]


def fixture() -> dict[str, object]:
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t31-enterprise-api",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [{"id": check_id, "result": "passed"} for check_id in CHECK_IDS],
        "experiment": {
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
        },
    }


class EnterpriseApiCheckerTests(unittest.TestCase):
    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(CHECKER)
        return subprocess.run(
            [sys.executable, "-m", "course_check", *args],
            cwd=CHECKER,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_bounded_offline_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "t31.json"
            path.write_text(json.dumps(fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t31-enterprise-api", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertFalse(document["experiment"]["live_api_called"])
        self.assertFalse(document["experiment"]["high_impact_executed"])
        self.assertNotIn(str(path), result.stdout)

    def test_budget_stop_is_partial_and_has_no_started_call(self) -> None:
        value = fixture()
        value["result"] = "partial"
        value["summary"] = "部分证据已通过，仍有证据需要补齐。"
        value["evidence"] = [
            {"id": "scope-bounded", "result": "passed"},
            {"id": "approval-gated", "result": "passed"},
            {"id": "structured-output", "result": "passed"},
            {"id": "budget-enforced", "result": "passed"},
            {"id": "recovery-observed", "result": "failed"},
            {"id": "evidence-redacted", "result": "passed"},
            {"id": "offline-deterministic", "result": "passed"},
        ]
        experiment = value["experiment"]
        assert isinstance(experiment, dict)
        experiment.update({
            "input_id": "issue-telemetry-validation-budget-v1",
            "failure_injected": False,
            "recovered": False,
            "budget_usd": 0.0001,
            "budget_status": "stopped",
            "model_call_started": False,
        })
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "budget.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t31-enterprise-api", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "partial")

    def test_high_impact_execution_without_approval_is_rejected(self) -> None:
        value = fixture()
        experiment = value["experiment"]
        assert isinstance(experiment, dict)
        experiment["high_impact_executed"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "unsafe.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t31-enterprise-api", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gates", result.stderr.lower())

    def test_sensitive_experiment_field_is_rejected(self) -> None:
        value = fixture()
        experiment = value["experiment"]
        assert isinstance(experiment, dict)
        experiment["api_key"] = "must-not-cross"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t31-enterprise-api", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
