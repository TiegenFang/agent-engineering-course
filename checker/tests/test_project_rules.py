"""Behavioral and privacy tests for the module 4 project-rules seam."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "checker"
COURSE_VERSION = json.loads((ROOT / "course-version.json").read_text(encoding="utf-8"))["course_version"]
CHECK_IDS = [
    "safe-lab-boundary",
    "codex-scope-observed",
    "claude-scope-observed",
    "nested-conflict-diagnosed",
    "recovery-rechecked",
    "cross-tool-migration",
]
STAGE_OBSERVATIONS = {
    "safe-boundary": ["new_target", "not_repo", "new_output"],
    "codex-observation": [
        "root_rule_seen",
        "nested_override_seen",
        "nested_regular_skipped",
        "nearest_last",
    ],
    "claude-observation": [
        "ancestor_rule_seen",
        "nested_rule_seen",
        "agent_import_seen",
        "scoped_rule_seen",
        "ancestor_before_nested",
    ],
    "conflict-diagnosis": [
        "codex_conflict_seen",
        "claude_conflict_seen",
        "difference_logged",
        "conflict_isolated",
    ],
    "recovery": ["override_removed", "regular_rechecked", "project_rule_kept", "recheck_complete"],
    "migration": ["comparison_done", "goal_unchanged", "difference_noted"],
}
STAGE_IDS = list(STAGE_OBSERVATIONS)


def passed_stages(*, failed: set[str] | None = None) -> list[dict[str, object]]:
    failed = failed or set()
    return [
        {
            "id": stage_id,
            "sequence": sequence,
            "result": "failed" if stage_id in failed else "passed",
            "observations": {
                key: stage_id not in failed for key in observations
            },
        }
        for sequence, (stage_id, observations) in enumerate(STAGE_OBSERVATIONS.items(), start=1)
    ]


def checks_for_stages(*, failed: set[str] | None = None) -> list[dict[str, str]]:
    failed = failed or set()
    return [
        {"id": check_id, "result": "failed" if any(stage in failed for stage in stage_ids) else "passed"}
        for check_id, stage_ids in (
            ("safe-lab-boundary", ["safe-boundary"]),
            ("codex-scope-observed", ["codex-observation"]),
            ("claude-scope-observed", ["claude-observation"]),
            ("nested-conflict-diagnosed", ["conflict-diagnosis"]),
            ("recovery-rechecked", ["recovery"]),
            ("cross-tool-migration", ["migration"]),
        )
    ]


def fixture(*, failed: set[str] | None = None) -> dict[str, object]:
    failed = failed or set()
    result = "passed" if not failed else "partial"
    return {
        "lesson_id": "t04-project-rules",
        "course_version": COURSE_VERSION,
        "platform": "windows",
        "shell": "powershell",
        "journey": {
            "trace_version": "1",
            "trace_id": "rulesfixture",
            "stages": passed_stages(failed=failed),
        },
        "checks": checks_for_stages(failed=failed),
        "result_hint": result,
    }


class ProjectRulesCheckerTests(unittest.TestCase):
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
            errors="replace",
            check=False,
        )

    def test_structure_check_is_partial_until_a_journey_runs(self) -> None:
        result = self.run_checker(
            "check", "t04-project-rules", "--root", str(ROOT), "--json"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "project-rules-page",
                "project-rules-lab",
                "project-rules-contract",
                "project-rules-sources",
                "project-rules-evidence-executed",
            ],
        )

    def test_complete_journey_derives_anonymous_passed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "diagnostic.json"
            evidence.write_text(json.dumps(fixture()), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t04-project-rules",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertTrue(document["anonymous"])
        self.assertEqual([check["id"] for check in document["evidence"]], CHECK_IDS)
        self.assertNotIn("rulesfixture", result.stdout)
        self.assertNotIn("journey", result.stdout)

    def test_failed_observation_is_reported_as_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "partial.json"
            evidence.write_text(
                json.dumps(fixture(failed={"conflict-diagnosis"})), encoding="utf-8"
            )
            result = self.run_checker(
                "check",
                "t04-project-rules",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "partial")

    def test_final_checks_cannot_forge_a_passed_journey(self) -> None:
        value = fixture()
        value["checks"] = checks_for_stages(failed={"recovery"})
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "forged.json"
            evidence.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t04-project-rules",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not match", result.stderr.lower())

    def test_wrong_stage_order_and_missing_observation_are_rejected(self) -> None:
        for mutate, expected in (
            (
                lambda value: value["journey"]["stages"].reverse(),
                "out of order",
            ),
            (
                lambda value: value["journey"]["stages"][0]["observations"].pop("new_output"),
                "incomplete",
            ),
        ):
            value = fixture()
            mutate(value)
            with tempfile.TemporaryDirectory() as temporary:
                evidence = Path(temporary) / "invalid.json"
                evidence.write_text(json.dumps(value), encoding="utf-8")
                result = self.run_checker(
                    "check",
                    "t04-project-rules",
                    "--root",
                    str(ROOT),
                    "--evidence-file",
                    str(evidence),
                    "--json",
                )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected, result.stderr.lower())

    def test_sensitive_fixture_fields_do_not_cross_boundary(self) -> None:
        value = fixture()
        value["journey"]["stages"][0]["absolute_path"] = "C:\\Users\\Ada\\secret"
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "sensitive.json"
            evidence.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t04-project-rules",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())

    def test_course_version_mismatch_is_rejected(self) -> None:
        value = fixture()
        value["course_version"] = "0.0.0-old"
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "old.json"
            evidence.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t04-project-rules",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("course_version", result.stderr)


if __name__ == "__main__":
    unittest.main()
