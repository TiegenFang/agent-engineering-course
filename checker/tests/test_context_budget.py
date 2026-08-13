"""Public checker seam tests for the deterministic context-budget lesson."""

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
        "lesson_id": "t14-context-budget",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [
            {"id": "working-set-selected", "result": "passed"},
            {"id": "risk-signals-observed", "result": "passed"},
            {"id": "boundary-tested", "result": "passed"},
            {"id": "offline-deterministic", "result": "passed"},
        ],
        "simulation": {
            "version": "1",
            "runs": [
                {
                    "id": "run-1",
                    "finding": "ready",
                    "findings": [],
                    "boundary": False,
                },
                {
                    "id": "run-2",
                    "finding": "insufficient",
                    "findings": ["insufficient", "crowding"],
                    "boundary": True,
                },
                {
                    "id": "run-3",
                    "finding": "pollution",
                    "findings": ["pollution"],
                    "boundary": False,
                },
                {
                    "id": "run-4",
                    "finding": "crowding",
                    "findings": ["crowding"],
                    "boundary": False,
                },
            ],
            "observed": ["crowding", "insufficient", "pollution"],
        },
    }


class ContextBudgetCheckerTests(unittest.TestCase):
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
        result = self.run_checker(
            "check",
            "t14-context-budget",
            "--root",
            str(ROOT),
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t14-context-budget")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "context-budget-page",
                "context-budget-simulator",
                "context-budget-contract",
                "context-budget-evidence",
            ],
        )

    def test_checker_derives_passed_result_from_anonymous_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t14-context-budget-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t14-context-budget",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["simulation"]["observed"], ["crowding", "insufficient", "pollution"])
        self.assertNotIn("capacity", json.dumps(document))
        self.assertNotIn(str(fixture), result.stdout)

    def test_checker_rejects_forged_checks_that_do_not_match_runs(self) -> None:
        fixture = passed_fixture()
        simulation = fixture["simulation"]
        assert isinstance(simulation, dict)
        simulation["runs"] = [simulation["runs"][0]]
        simulation["observed"] = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "forged.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t14-context-budget",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("simulation", result.stderr)

    def test_checker_rejects_sensitive_fields_in_simulation(self) -> None:
        fixture = passed_fixture()
        simulation = fixture["simulation"]
        assert isinstance(simulation, dict)
        simulation["path"] = "C:\\private\\prompt.txt"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t14-context-budget",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr)


if __name__ == "__main__":
    unittest.main()
