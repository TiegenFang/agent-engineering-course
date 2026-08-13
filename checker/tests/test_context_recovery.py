"""Checker seam tests for the deterministic T15 context recovery lesson."""

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

from course_check.__main__ import (  # noqa: E402
    T15_CONTEXT_RECOVERY_CHECK_IDS,
    validate_t15_evidence_checks,
    validate_t15_experiment,
)
from course_check.evidence import EvidenceError, build_evidence_document  # noqa: E402


COURSE_VERSION = json.loads((ROOT / "course-version.json").read_text(encoding="utf-8"))["course_version"]


def valid_checks() -> list[dict[str, str]]:
    return [{"id": check_id, "result": "passed"} for check_id in T15_CONTEXT_RECOVERY_CHECK_IDS]


def valid_experiment() -> dict[str, object]:
    return {
        "version": "1",
        "baseline_id": "telemetry-report-v1",
        "compression_modes": ["faithful", "distorted", "constraint-omitted"],
        "comparisons": [
            {
                "mode": "faithful",
                "before_outcome": "report-ready",
                "after_outcome": "faithful",
                "distortion_detected": False,
                "constraint_omission_detected": False,
            },
            {
                "mode": "distorted",
                "before_outcome": "report-ready",
                "after_outcome": "distorted",
                "distortion_detected": True,
                "constraint_omission_detected": False,
            },
            {
                "mode": "constraint-omitted",
                "before_outcome": "report-ready",
                "after_outcome": "constraint-omitted",
                "distortion_detected": False,
                "constraint_omission_detected": True,
            },
        ],
        "pollution": {
            "injected": True,
            "observed": True,
            "recovered": True,
            "outcome": "recovered",
        },
        "handoff": {
            "goal": "report-task",
            "status": "ready-for-next-session",
            "evidence": [
                "compression-before-after",
                "compression-distortion-diagnosed",
                "constraint-omission-diagnosed",
                "pollution-recovered",
            ],
            "risks": [
                "compressed-context-may-be-lossy",
                "history-is-not-a-current-constraint",
                "memory-promotion-requires-owner-and-lifetime",
            ],
            "next_steps": ["重新载入本交接包", "核对三条约束"],
        },
        "layers": {
            "context": "current-working-set",
            "history": "record-only",
            "memory": "owned-and-expiring",
        },
    }


def valid_document() -> dict[str, object]:
    document = build_evidence_document(
        course_version=COURSE_VERSION,
        lesson_id="t15-context-recovery",
        checks=valid_checks(),
        checked_on="2026-08-13",
    )
    document["experiment"] = valid_experiment()
    return document


class ContextRecoveryCheckerTests(unittest.TestCase):
    def test_valid_experiment_and_checks_are_accepted(self) -> None:
        checks = validate_t15_evidence_checks(valid_checks())
        normalized = validate_t15_experiment(
            valid_experiment(), checks=checks, document_result="passed"
        )
        self.assertEqual(normalized["compression_modes"], ["faithful", "distorted", "constraint-omitted"])
        self.assertEqual(normalized["pollution"]["outcome"], "recovered")
        self.assertEqual(normalized["handoff"]["status"], "ready-for-next-session")

    def test_check_states_cannot_claim_passed_without_modes_or_recovery(self) -> None:
        checks = valid_checks()
        checks[1]["result"] = "failed"
        with self.assertRaises(EvidenceError):
            validate_t15_experiment(
                {
                    **valid_experiment(),
                    "compression_modes": [],
                    "comparisons": [],
                    "pollution": {
                        "injected": False,
                        "observed": False,
                        "recovered": False,
                        "outcome": "not-run",
                    },
                    "handoff": {
                        **valid_experiment()["handoff"],
                        "status": "blocked",
                    },
                },
                checks=validate_t15_evidence_checks(
                    [
                        {"id": item["id"], "result": item["result"]}
                        for item in checks
                    ]
                ),
                document_result="partial",
            )

    def test_tampered_distortion_diagnostic_is_rejected(self) -> None:
        experiment = valid_experiment()
        experiment["comparisons"][1]["distortion_detected"] = False  # type: ignore[index]
        with self.assertRaisesRegex(EvidenceError, "distortion diagnostic"):
            validate_t15_experiment(
                experiment,
                checks=validate_t15_evidence_checks(valid_checks()),
                document_result="passed",
            )

    def test_sensitive_fields_do_not_cross_experiment_seam(self) -> None:
        experiment = valid_experiment()
        experiment["handoff"]["source_path"] = "C:\\Users\\Ada\\report.txt"  # type: ignore[index]
        with self.assertRaises(EvidenceError):
            validate_t15_experiment(
                experiment,
                checks=validate_t15_evidence_checks(valid_checks()),
                document_result="passed",
            )

    def test_cli_emits_passed_anonymous_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_file = Path(temporary) / "t15-context-recovery-evidence.json"
            evidence_file.write_text(json.dumps(valid_document(), ensure_ascii=False), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(CHECKER)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "course_check",
                    "check",
                    "t15-context-recovery",
                    "--root",
                    str(ROOT),
                    "--evidence-file",
                    str(evidence_file),
                    "--json",
                ],
                cwd=CHECKER,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output["result"], "passed")
            self.assertTrue(output["anonymous"])
            self.assertEqual(output["experiment"]["layers"]["history"], "record-only")


if __name__ == "__main__":
    unittest.main()
