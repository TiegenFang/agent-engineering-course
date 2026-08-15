"""Public checker seam tests for the Codex repository task."""

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
COURSE_VERSION = "1.0.0"
STAGES = [
    ("baseline", ["repo", "clean", "head", "branch"]),
    ("clarify", ["goal", "non_goal", "acceptance"]),
    ("plan", ["files", "commands", "permissions", "stop", "approval"]),
    ("failure-observed", ["expected_failure", "error_classified"]),
    ("change", ["source_changed", "diff", "approval"]),
    ("recovery", ["tests_passed", "report_generated"]),
    ("review", ["diff_reviewed", "scope_clean", "no_secrets"]),
    ("delivery", ["handoff", "evidence_ready", "human_approved"]),
]
CHECK_IDS = [
    "clarification-recorded",
    "plan-recorded",
    "failure-recovered",
    "scoped-change",
    "tests-passed",
    "diff-reviewed",
    "report-generated",
    "delivery-recorded",
]


def evidence_document(*, failed_stage: str | None = None) -> dict[str, object]:
    stages: list[dict[str, object]] = []
    stage_passed: dict[str, bool] = {}
    for sequence, (stage_id, observation_ids) in enumerate(STAGES, start=1):
        observations = {key: True for key in observation_ids}
        if stage_id == "failure-observed":
            observations["expected_failure"] = True
            observations["error_classified"] = True
        if failed_stage == stage_id:
            observations[observation_ids[0]] = False
        passed = all(observations.values())
        stage_passed[stage_id] = passed
        stages.append(
            {
                "id": stage_id,
                "sequence": sequence,
                "result": "passed" if passed else "failed",
                "observations": observations,
            }
        )

    checks = [
        {"id": "clarification-recorded", "result": "passed" if stage_passed["clarify"] else "failed"},
        {"id": "plan-recorded", "result": "passed" if stage_passed["plan"] else "failed"},
        {
            "id": "failure-recovered",
            "result": "passed"
            if stage_passed["failure-observed"] and stage_passed["recovery"]
            else "failed",
        },
        {
            "id": "scoped-change",
            "result": "passed"
            if stage_passed["change"] and stage_passed["review"]
            else "failed",
        },
        {"id": "tests-passed", "result": "passed" if stage_passed["recovery"] else "failed"},
        {"id": "diff-reviewed", "result": "passed" if stage_passed["review"] else "failed"},
        {
            "id": "report-generated",
            "result": "passed"
            if stage_passed["recovery"] and stage_passed["delivery"]
            else "failed",
        },
        {"id": "delivery-recorded", "result": "passed" if stage_passed["delivery"] else "failed"},
    ]
    result = (
        "passed"
        if all(check["result"] == "passed" for check in checks)
        else "failed"
        if all(check["result"] == "failed" for check in checks)
        else "partial"
    )
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t04-codex-repository-task",
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": {
            "passed": "所有必需证据均已通过。",
            "partial": "部分证据已通过，仍有证据需要补齐。",
            "failed": "证据未通过，请根据本地检查结果恢复后重试。",
        }[result],
        "evidence": checks,
        "task_id": "telemetry-report-v1",
        "platform": "windows",
        "shell": "powershell",
        "journey": {
            "trace_version": "1",
            "trace_id": "codex-task-test-trace",
            "stages": stages,
        },
        "artifact": {
            "version": "1",
            "report": "passed" if stage_passed["recovery"] else "failed",
            "tests": "passed" if stage_passed["recovery"] else "failed",
            "delivery": "passed" if stage_passed["delivery"] else "failed",
        },
    }


class CodexTaskCheckerTests(unittest.TestCase):
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

    def with_evidence(self, value: dict[str, object]):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "t04-evidence.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return temporary, path

    def test_structure_only_is_partial_without_live_evidence(self) -> None:
        result = self.run_checker(
            "check",
            "t04-codex-repository-task",
            "--root",
            str(ROOT),
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "codex-task-page",
                "codex-task-powershell",
                "codex-task-starter",
                "codex-task-evidence-executed",
            ],
        )

    def test_accepts_complete_ordered_journey(self) -> None:
        temporary, path = self.with_evidence(evidence_document())
        try:
            result = self.run_checker(
                "check",
                "t04-codex-repository-task",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        finally:
            temporary.cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual([item["id"] for item in document["evidence"]], CHECK_IDS)
        self.assertNotIn("telemetry_report.py", result.stdout)
        self.assertNotIn("codex-task-test-trace", result.stdout)

    def test_failure_stage_can_be_reported_as_partial_without_false_success(self) -> None:
        temporary, path = self.with_evidence(evidence_document(failed_stage="failure-observed"))
        try:
            result = self.run_checker(
                "check",
                "t04-codex-repository-task",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        finally:
            temporary.cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "partial")

    def test_rejects_stage_order_and_claimed_result_mismatch(self) -> None:
        value = evidence_document()
        value["journey"]["stages"][1], value["journey"]["stages"][2] = (  # type: ignore[index]
            value["journey"]["stages"][2],
            value["journey"]["stages"][1],
        )
        temporary, path = self.with_evidence(value)
        try:
            result = self.run_checker(
                "check",
                "t04-codex-repository-task",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        finally:
            temporary.cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("out of order", result.stderr.lower())

    def test_rejects_sensitive_fields_at_public_boundary(self) -> None:
        value = evidence_document()
        value["source_path"] = "C:\\private\\raw.csv"
        temporary, path = self.with_evidence(value)
        try:
            result = self.run_checker(
                "check",
                "t04-codex-repository-task",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        finally:
            temporary.cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())

    def test_rejects_artifact_status_not_derived_from_journey(self) -> None:
        value = evidence_document()
        value["artifact"]["report"] = "failed"  # type: ignore[index]
        temporary, path = self.with_evidence(value)
        try:
            result = self.run_checker(
                "check",
                "t04-codex-repository-task",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        finally:
            temporary.cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifact.report", result.stderr)


if __name__ == "__main__":
    unittest.main()
