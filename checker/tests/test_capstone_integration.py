"""Public checker seam tests for the T25 dual-track capstone integration."""

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
    "track-selected",
    "problem-scoped",
    "context-memory-linked",
    "skill-mcp-bounded",
    "core-evidence-linked",
    "validation-recorded",
    "migration-recorded",
    "delivery-reviewed",
    "privacy-safe",
    "version-locked",
    "portfolio-exported",
    "offline-deterministic",
]


def passed_fixture(track: str = "enterprise") -> dict[str, object]:
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t25-capstone-integration",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [{"id": check_id, "result": "passed"} for check_id in CHECK_IDS],
        "experiment": {
            "version": "1",
            "baseline_id": "telemetry-capstone-integration-v1",
            "track": track,
            "fault": "none",
            "problem": True,
            "context_memory": True,
            "skill_mcp": True,
            "core": True,
            "validation": True,
            "migration": True,
            "delivery": True,
            "privacy": True,
            "version_lock": True,
            "portfolio": True,
            "offline": True,
        },
    }


class CapstoneIntegrationCheckerTests(unittest.TestCase):
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
            "check", "t25-capstone-integration", "--root", str(ROOT), "--json"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t25-capstone-integration")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "capstone-integration-page",
                "capstone-integration-lab",
                "capstone-integration-checker",
                "capstone-integration-contract",
                "capstone-integration-sources",
                "capstone-integration-evidence",
            ],
        )

    def test_both_tracks_pass_the_same_common_contract(self) -> None:
        for track in ("research", "enterprise"):
            with self.subTest(track=track), tempfile.TemporaryDirectory() as temporary:
                fixture = Path(temporary) / "t25-evidence.json"
                fixture.write_text(
                    json.dumps(passed_fixture(track), ensure_ascii=False), encoding="utf-8"
                )
                result = self.run_checker(
                    "check",
                    "t25-capstone-integration",
                    "--root",
                    str(ROOT),
                    "--evidence-file",
                    str(fixture),
                    "--json",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                document = json.loads(result.stdout)
                self.assertEqual(document["result"], "passed")
                self.assertEqual(document["experiment"]["track"], track)
                self.assertNotIn(str(fixture), result.stdout)

    def test_fault_cannot_be_forged_as_pass(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment["fault"] = "unsafe-side-effect"
        experiment["skill_mcp"] = False
        experiment["privacy"] = False
        fixture["result"] = "passed"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "partial.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t25-capstone-integration",
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
        experiment["issue_body"] = "private enterprise text"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t25-capstone-integration",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
