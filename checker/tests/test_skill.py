"""Public checker and local-script tests for the custom Skill lesson."""

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
NORMALIZER = ROOT / "labs" / "skill" / "evidence-research" / "scripts" / "normalize-evidence.py"


def passed_fixture() -> dict[str, object]:
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t17-skill",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [
            {"id": "skill-package-shaped", "result": "passed"},
            {"id": "trigger-boundary-tested", "result": "passed"},
            {"id": "evidence-scenarios-covered", "result": "passed"},
            {"id": "validation-script-passed", "result": "passed"},
            {"id": "security-boundary-tested", "result": "passed"},
            {"id": "offline-deterministic", "result": "passed"},
        ],
        "simulation": {
            "version": "1",
            "runs": [
                {
                    "id": "run-1",
                    "scenario": "complete",
                    "finding": "ready",
                    "boundary": False,
                    "script": "passed",
                    "deterministic": True,
                    "external_call": False,
                },
                {
                    "id": "run-2",
                    "scenario": "missing-source",
                    "finding": "needs-source",
                    "boundary": False,
                    "script": "passed",
                    "deterministic": True,
                    "external_call": False,
                },
                {
                    "id": "run-3",
                    "scenario": "conflicting-evidence",
                    "finding": "conflict",
                    "boundary": True,
                    "script": "passed",
                    "deterministic": True,
                    "external_call": False,
                },
                {
                    "id": "run-4",
                    "scenario": "untrusted-instruction",
                    "finding": "untrusted-input",
                    "boundary": True,
                    "script": "passed",
                    "deterministic": True,
                    "external_call": False,
                },
            ],
            "trigger_cases": [
                {"id": "research-evidence", "observed": "activate"},
                {"id": "telemetry-summary", "observed": "activate"},
                {"id": "generic-greeting", "observed": "skip"},
                {"id": "one-line-calculation", "observed": "skip"},
            ],
            "observed": ["conflict", "needs-source", "ready", "untrusted-input"],
        },
    }


class SkillCheckerTests(unittest.TestCase):
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
        result = self.run_checker("check", "t17-skill", "--root", str(ROOT), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t17-skill")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "skill-package-shaped",
                "trigger-boundary-tested",
                "evidence-scenarios-covered",
                "validation-script-passed",
                "security-boundary-tested",
                "offline-deterministic",
            ],
        )

    def test_checker_derives_passed_result_from_fixed_skill_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t17-skill-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t17-skill",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["simulation"]["observed"], ["conflict", "needs-source", "ready", "untrusted-input"])
        self.assertNotIn(str(fixture), result.stdout)
        self.assertNotIn("claim-temperature", result.stdout)

    def test_checker_rejects_forged_finding_or_trigger(self) -> None:
        fixture = passed_fixture()
        simulation = fixture["simulation"]
        assert isinstance(simulation, dict)
        runs = simulation["runs"]
        assert isinstance(runs, list)
        runs[0]["finding"] = "conflict"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "forged.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t17-skill",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deterministic", result.stderr)

    def test_checker_rejects_sensitive_simulation_fields(self) -> None:
        fixture = passed_fixture()
        simulation = fixture["simulation"]
        assert isinstance(simulation, dict)
        simulation["path"] = "C:\\private\\prompt.txt"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t17-skill",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr)

    def test_normalizer_is_offline_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_a = Path(temporary) / "a.json"
            output_b = Path(temporary) / "b.json"
            args = [sys.executable, str(NORMALIZER), "--input", str(NORMALIZER.parents[1] / "assets" / "telemetry-sample.json")]
            first = subprocess.run(args + ["--output", str(output_a)], capture_output=True, text=True, check=False)
            second = subprocess.run(args + ["--output", str(output_b)], capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(output_a.read_text(encoding="utf-8"), output_b.read_text(encoding="utf-8"))
            normalized = json.loads(output_a.read_text(encoding="utf-8"))
            self.assertEqual(normalized["contract"], "evidence-research/v1")
            self.assertNotIn(str(NORMALIZER.parents[1]), output_a.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
