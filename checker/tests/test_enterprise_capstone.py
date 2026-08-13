"""Public checker seam tests for the T24 enterprise capstone."""

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


def passed_fixture() -> dict[str, object]:
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t24-enterprise-capstone",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [{"id": check_id, "result": "passed"} for check_id in CHECK_IDS],
        "experiment": {
            "version": "1",
            "baseline_id": "telemetry-report-issue-v1",
            "input": "bug-fix",
            "context": True,
            "memory": True,
            "skill": True,
            "mcp": True,
            "artifacts": {
                "change": True,
                "tests": True,
                "review": True,
                "delivery": True,
                "evidence": True,
            },
            "migration": True,
            "rubric": True,
            "offline": True,
            "fault": "none",
        },
    }


class EnterpriseCapstoneCheckerTests(unittest.TestCase):
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

    def test_structure_is_partial_without_learner_evidence(self) -> None:
        result = self.run_checker(
            "check", "t24-enterprise-capstone", "--root", str(ROOT), "--json"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t24-enterprise-capstone")

    def test_checker_derives_passed_bug_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t24-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t24-enterprise-capstone",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["experiment"]["input"], "bug-fix")
        self.assertTrue(document["anonymous"])
        self.assertNotIn(str(fixture), result.stdout)

    def test_test_failure_cannot_be_claimed_as_passed(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        artifacts = experiment["artifacts"]
        assert isinstance(artifacts, dict)
        experiment["fault"] = "test-failure"
        artifacts["tests"] = False
        fixture["result"] = "passed"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "partial.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t24-enterprise-capstone",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checks do not match", result.stderr)

    def test_sensitive_issue_payload_is_rejected(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment["issue_body"] = "confidential enterprise ticket"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t24-enterprise-capstone",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive field", result.stderr)


if __name__ == "__main__":
    unittest.main()
