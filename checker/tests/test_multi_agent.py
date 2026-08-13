"""Public checker seam tests for the deterministic T22 multi-agent lesson."""

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
sys.path.insert(0, str(CHECKER))

from course_check.multi_agent import multi_agent_comparison_fixture


COURSE_VERSION = json.loads(
    (ROOT / "course-version.json").read_text(encoding="utf-8")
)["course_version"]


def passed_fixture() -> dict[str, object]:
    comparisons = [
        multi_agent_comparison_fixture("independent-review"),
        multi_agent_comparison_fixture("overlap-conflict"),
    ]
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t22-multi-agent",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [
            {"id": "same-goal-compared", "result": "passed"},
            {"id": "task-boundaries-declared", "result": "passed"},
            {"id": "time-usage-verification-compared", "result": "passed"},
            {"id": "conflict-recovered", "result": "passed"},
            {"id": "decision-supported", "result": "passed"},
            {"id": "offline-deterministic", "result": "passed"},
        ],
        "experiment": {
            "version": "1",
            "goal": "telemetry-report-v2",
            "comparisons": comparisons,
            "observed_modes": ["single", "subagents"],
            "observed_boundaries": [
                "acceptance-check",
                "input-validation",
                "report-summary",
                "summary-outline",
            ],
            "observed_conflicts": ["none", "shared-output-collision"],
            "observed_recoveries": ["not-required", "repartition-and-revalidate"],
            "model_calls": 0,
            "network_calls": 0,
        },
    }


class MultiAgentCheckerTests(unittest.TestCase):
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

    def test_structure_check_is_partial_without_learner_evidence(self) -> None:
        result = self.run_checker("check", "t22-multi-agent", "--root", str(ROOT), "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t22-multi-agent")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "multi-agent-page",
                "multi-agent-simulator",
                "multi-agent-contract",
                "multi-agent-sources",
                "multi-agent-evidence",
            ],
        )

    def test_checker_rederives_the_complete_controlled_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t22-multi-agent-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t22-multi-agent",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        experiment = document["experiment"]
        self.assertEqual(experiment["goal"], "telemetry-report-v2")
        self.assertEqual(experiment["model_calls"], 0)
        self.assertEqual(experiment["network_calls"], 0)
        self.assertNotIn(str(fixture), result.stdout)

    def test_checker_rejects_forged_cost_or_missing_recovery(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        comparisons = experiment["comparisons"]
        assert isinstance(comparisons, list)
        comparisons[1]["subagents"]["usage_units"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "forged.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t22-multi-agent", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("controlled fixture", result.stderr)

    def test_checker_rejects_sensitive_experiment_fields(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment["path"] = "C:\\private\\comparison"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t22-multi-agent", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr)

    def test_checker_rejects_boolean_numeric_and_boolean_status_forgery(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment["model_calls"] = False
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "boolean-forgery.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t22-multi-agent", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("offline", result.stderr)

        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        comparisons = experiment["comparisons"]
        assert isinstance(comparisons, list)
        comparisons[0]["subagents"]["accepted"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "boolean-status-forgery.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t22-multi-agent", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted must be a boolean", result.stderr)


if __name__ == "__main__":
    unittest.main()
