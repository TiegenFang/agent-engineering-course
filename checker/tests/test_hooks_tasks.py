"""Public checker seam tests for the deterministic Hooks/Tasks lesson."""

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
COURSE_VERSION = json.loads(
    (ROOT / "course-version.json").read_text(encoding="utf-8")
)["course_version"]


def passed_fixture() -> dict[str, object]:
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t21-hooks-tasks",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [
            {"id": "trigger-observed", "result": "passed"},
            {"id": "deduplication-observed", "result": "passed"},
            {"id": "permission-boundary", "result": "passed"},
            {"id": "stop-condition", "result": "passed"},
            {"id": "failure-recovered", "result": "passed"},
            {"id": "side-effect-not-triggered", "result": "passed"},
            {"id": "explicit-task-recorded", "result": "passed"},
            {"id": "offline-deterministic", "result": "passed"},
        ],
        "experiment": {
            "version": "1",
            "runs": [
                {
                    "id": "run-1",
                    "mode": "hook",
                    "trigger": True,
                    "deduplicated": True,
                    "permission": "blocked",
                    "stopped": True,
                    "failed": True,
                    "recovered": True,
                    "taskCreated": True,
                    "sideEffect": False,
                    "scheduleArmed": False,
                    "backgroundStarted": False,
                }
            ],
            "observed": [
                "deduplication",
                "explicit-task",
                "failure-recovery",
                "permission",
                "side-effect-guard",
                "stop",
                "trigger",
            ],
        },
    }


class HooksTasksCheckerTests(unittest.TestCase):
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
        result = self.run_checker("check", "t21-hooks-tasks", "--root", str(ROOT), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t21-hooks-tasks")

    def test_checker_derives_passed_result_from_anonymous_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t21-hooks-tasks-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t21-hooks-tasks",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertNotIn(str(fixture), result.stdout)
        self.assertNotIn("command", result.stdout)

    def test_checker_rejects_forged_checks_that_do_not_match_runs(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        runs = experiment["runs"]
        assert isinstance(runs, list)
        runs[0]["recovered"] = False
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "forged.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t21-hooks-tasks",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("T21", result.stderr)

    def test_checker_rejects_side_effect_without_allowed_permission(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        runs = experiment["runs"]
        assert isinstance(runs, list)
        runs[0]["sideEffect"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "unsafe.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t21-hooks-tasks",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("side effect", result.stderr)


if __name__ == "__main__":
    unittest.main()
