"""Public checker seam tests for the Claude Code migration challenge."""

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
COURSE_VERSION = "2.0.0"
STAGE_OBSERVATIONS = {
    "baseline": ["repo", "clean", "head", "branch", "path_declared"],
    "clarify": ["goal", "non_goal", "acceptance", "migration"],
    "plan": ["files", "commands", "permissions", "stop", "approval"],
    "official-facts": [
        "installation",
        "operation",
        "permissions",
        "cost",
        "date",
        "no_live_claim",
    ],
    "failure-observed": ["expected_failure", "error_classified", "no_fake_result"],
    "change": ["source_changed", "diff", "approval", "variant_changed"],
    "recovery": ["tests_passed", "report_generated", "summary_only"],
    "review": ["diff_reviewed", "scope_clean", "no_secrets", "path_complete"],
    "delivery": ["handoff", "evidence_ready", "human_approved", "live_call_not_claimed"],
}
STAGE_IDS = list(STAGE_OBSERVATIONS)
CHECK_IDS = [
    "clarification-recorded",
    "plan-recorded",
    "official-facts-recorded",
    "migration-input-changed",
    "failure-recovered",
    "tests-passed",
    "permission-cost-compared",
    "path-completed",
    "live-claude-not-claimed",
    "report-generated",
    "delivery-recorded",
]


def evidence_document(
    *, mode: str = "claude-only", failed_stage: str | None = None
) -> dict[str, object]:
    stages: list[dict[str, object]] = []
    stage_passed: dict[str, bool] = {}
    for sequence, stage_id in enumerate(STAGE_IDS, start=1):
        observations = {key: True for key in STAGE_OBSERVATIONS[stage_id]}
        if failed_stage == stage_id:
            observations[STAGE_OBSERVATIONS[stage_id][0]] = False
        passed = all(observations.values())
        stage_passed[stage_id] = passed
        stages.append(
            {
                "id": stage_id,
                "sequence": sequence,
                "mode": mode,
                "result": "passed" if passed else "failed",
                "observations": observations,
            }
        )

    checks = [
        {"id": "clarification-recorded", "result": "passed" if stage_passed["clarify"] else "failed"},
        {"id": "plan-recorded", "result": "passed" if stage_passed["plan"] else "failed"},
        {"id": "official-facts-recorded", "result": "passed" if stage_passed["official-facts"] else "failed"},
        {"id": "migration-input-changed", "result": "passed" if stage_passed["change"] else "failed"},
        {
            "id": "failure-recovered",
            "result": "passed"
            if stage_passed["failure-observed"] and stage_passed["recovery"]
            else "failed",
        },
        {"id": "tests-passed", "result": "passed" if stage_passed["recovery"] else "failed"},
        {"id": "permission-cost-compared", "result": "passed" if stage_passed["official-facts"] else "failed"},
        {"id": "path-completed", "result": "passed" if stage_passed["review"] else "failed"},
        {
            "id": "live-claude-not-claimed",
            "result": "passed"
            if stage_passed["official-facts"] and stage_passed["delivery"]
            else "failed",
        },
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
        "lesson_id": "t04-claude-migration",
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": {
            "passed": "所有必需证据均已通过。",
            "partial": "部分证据已通过，仍有证据需要补齐。",
            "failed": "证据未通过，请根据本地检查结果恢复后重试。",
        }[result],
        "evidence": checks,
        "task_id": "pressure-report-v1",
        "platform": "windows",
        "shell": "powershell",
        "journey": {
            "trace_version": "1",
            "trace_id": "claude-migration-test-trace",
            "stages": stages,
        },
        "experiment": {
            "version": "1",
            "mode": mode,
            "migration_variant": "pressure-night",
            "input_contract": {
                "subject": "pressure",
                "units": ["kPa", "psi", "bar"],
                "record_limit": "recent-3-valid",
                "outputs": ["mean_kpa", "peak_kpa", "alarm_count"],
            },
            "official_facts": {
                "installation": "recorded",
                "operation": "recorded",
                "permissions": "recorded",
                "cost": "recorded",
            },
            "live_call": "not-verified",
            "codex_reference": "not-required" if mode == "claude-only" else "status-only",
        },
    }


class ClaudeMigrationCheckerTests(unittest.TestCase):
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
        path = Path(temporary.name) / "t04-claude-migration-evidence.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return temporary, path

    def test_structure_is_partial_without_live_evidence(self) -> None:
        result = self.run_checker(
            "check",
            "t04-claude-migration",
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
                "claude-migration-page",
                "claude-migration-powershell",
                "claude-migration-starter",
                "claude-migration-official-facts",
                "claude-migration-evidence-executed",
            ],
        )

    def test_accepts_claude_only_journey(self) -> None:
        temporary, path = self.with_evidence(evidence_document())
        try:
            result = self.run_checker(
                "check",
                "t04-claude-migration",
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
        self.assertNotIn("claude-migration-test-trace", result.stdout)

    def test_accepts_dual_tool_journey_without_claiming_live_calls(self) -> None:
        temporary, path = self.with_evidence(evidence_document(mode="dual-tool"))
        try:
            result = self.run_checker(
                "check",
                "t04-claude-migration",
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
        self.assertIn('"live_call": "not-verified"', result.stdout)

    def test_changed_input_is_required(self) -> None:
        value = evidence_document()
        value["experiment"]["input_contract"]["units"] = ["C", "F"]  # type: ignore[index]
        temporary, path = self.with_evidence(value)
        try:
            result = self.run_checker(
                "check",
                "t04-claude-migration",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        finally:
            temporary.cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("input_contract", result.stderr)

    def test_live_call_claim_is_rejected(self) -> None:
        value = evidence_document()
        value["experiment"]["live_call"] = "observed"  # type: ignore[index]
        temporary, path = self.with_evidence(value)
        try:
            result = self.run_checker(
                "check",
                "t04-claude-migration",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        finally:
            temporary.cleanup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live Claude", result.stderr)

    def test_stage_order_is_enforced(self) -> None:
        value = evidence_document()
        value["journey"]["stages"][1], value["journey"]["stages"][2] = (  # type: ignore[index]
            value["journey"]["stages"][2],
            value["journey"]["stages"][1],
        )
        temporary, path = self.with_evidence(value)
        try:
            result = self.run_checker(
                "check",
                "t04-claude-migration",
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


if __name__ == "__main__":
    unittest.main()
