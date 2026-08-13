"""Public checker seam tests for T29 production evaluation."""

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
    "success-case",
    "failure-case",
    "variant-input",
    "recovery-observed",
    "budget-gate",
    "log-redaction",
]


def fixture() -> dict[str, object]:
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t29-production",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [{"id": check_id, "result": "passed"} for check_id in CHECK_IDS],
        "evaluation": {
            "evaluator_version": "production-evaluator-v1",
            "fixture_version": "1",
            "input_id": "baseline-pressure-v1",
            "cases_total": 3,
            "cases_passed": 3,
            "success_case_passed": True,
            "failure_case_observed": True,
            "variant_input_passed": True,
            "recovery_observed": True,
            "failures_recovered": 1,
            "estimated_input_tokens": 240,
            "estimated_output_tokens": 96,
            "estimated_cost_usd": 0.000432,
            "budget_usd": 0.01,
            "budget_status": "allowed",
            "provider": "offline-fixture",
            "model": "offline-model-v1",
            "live_api_called": False,
        },
        "logs": {
            "event_count": 4,
            "events": ["evaluation-start", "case-result", "recovery", "evaluation-end"],
        },
    }


class ProductionCheckerTests(unittest.TestCase):
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

    def test_offline_complete_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "t29.json"
            path.write_text(json.dumps(fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t29-production", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertFalse(document["evaluation"]["live_api_called"])
        self.assertNotIn(str(path), result.stdout)

    def test_budget_stop_is_partial_not_passed(self) -> None:
        value = fixture()
        value["result"] = "partial"
        value["summary"] = "部分证据已通过，仍有证据需要补齐。"
        value["evidence"] = [
            {"id": "success-case", "result": "failed"},
            {"id": "failure-case", "result": "passed"},
            {"id": "variant-input", "result": "passed"},
            {"id": "recovery-observed", "result": "failed"},
            {"id": "budget-gate", "result": "failed"},
            {"id": "log-redaction", "result": "passed"},
        ]
        evaluation = value["evaluation"]
        assert isinstance(evaluation, dict)
        evaluation.update({
            "cases_passed": 2,
            "success_case_passed": False,
            "failure_case_observed": True,
            "variant_input_passed": True,
            "recovery_observed": False,
            "failures_recovered": 0,
            "budget_status": "stopped",
        })
        value["logs"] = {"event_count": 4, "events": ["evaluation-start", "budget-stop", "case-result", "evaluation-end"]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "budget.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker("check", "t29-production", "--root", str(ROOT), "--evidence-file", str(path), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "partial")

    def test_sensitive_evaluation_field_is_rejected(self) -> None:
        value = fixture()
        evaluation = value["evaluation"]
        assert isinstance(evaluation, dict)
        evaluation["api_key"] = "must-not-cross"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker("check", "t29-production", "--root", str(ROOT), "--evidence-file", str(path), "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
