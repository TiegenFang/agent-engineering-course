"""Public checker seam tests for the T23 research capstone."""

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


def passed_fixture() -> dict[str, object]:
    checks = [{"id": check_id, "result": "passed"} for check_id in CHECK_IDS]
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t23-research-capstone",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": checks,
        "experiment": {
            "version": "1",
            "baseline_id": "telemetry-research-v1",
            "input": "pressure-night",
            "context": True,
            "memory": True,
            "skill": True,
            "mcp": True,
            "artifacts": {
                "script": True,
                "figure": True,
                "record": True,
                "report": True,
                "evidence": True,
            },
            "migration": True,
            "rubric": True,
            "offline": True,
            "fault": "none",
        },
    }


class ResearchCapstoneCheckerTests(unittest.TestCase):
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
        result = self.run_checker("check", "t23-research-capstone", "--root", str(ROOT), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t23-research-capstone")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "research-capstone-page",
                "research-capstone-simulator",
                "research-capstone-lab",
                "research-capstone-contract",
                "research-capstone-sources",
                "research-capstone-evidence",
            ],
        )

    def test_checker_derives_passed_pressure_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t23-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t23-research-capstone",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["experiment"]["input"], "pressure-night")
        self.assertTrue(document["anonymous"])
        self.assertNotIn(str(fixture), result.stdout)

    def test_fault_is_partial_even_when_top_level_claims_passed(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment["fault"] = "stale-memory"
        experiment["memory"] = False
        fixture["result"] = "passed"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "partial.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t23-research-capstone", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checks do not match", result.stderr)

    def test_sensitive_raw_payload_is_rejected(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment["raw_telemetry"] = "private research data"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t23-research-capstone", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
