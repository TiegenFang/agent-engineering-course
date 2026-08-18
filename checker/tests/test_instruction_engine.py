"""Public checker seam tests for the deterministic instruction lesson."""

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
COURSE_VERSION = "3.0.0"
CHECK_IDS = [
    "prediction-recorded",
    "baseline-compared",
    "conflict-contained",
    "injection-contained",
    "long-instruction-diagnosed",
    "migration-completed",
]


def evidence_document(results: list[str], *, experiment: dict[str, object] | None = None) -> dict[str, object]:
    result = (
        "passed"
        if all(item == "passed" for item in results)
        else "failed"
        if all(item == "failed" for item in results)
        else "partial"
    )
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t03-agent-instruction",
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": {
            "passed": "所有必需证据均已通过。",
            "partial": "部分证据已通过，仍有证据需要补齐。",
            "failed": "证据未通过，请根据本地检查结果恢复后重试。",
        }[result],
        "evidence": [
            {"id": check_id, "result": value}
            for check_id, value in zip(CHECK_IDS, results, strict=True)
        ],
        "experiment": experiment
        if experiment is not None
        else {
            "version": "2",
            "baseline_id": "telemetry-report-v1",
            "completed_scenarios": ["baseline", "conflict", "injection", "long"],
            "migration_variants": ["pressure-night"],
            "migration_contracts": [
                {"id": "pressure-night", "subject": "压力", "unit": "kPa", "limit": "最近 3 条有效记录"}
            ],
            "latest": {
                "scenario_id": "long",
                "variant_id": "pressure-night",
                "variant_subject": "压力",
                "variant_unit": "kPa",
                "variant_limit": "最近 3 条有效记录",
                "ambiguous_outcome": "overloaded",
                "engineered_outcome": "scoped",
            },
        },
    }


class InstructionCheckerTests(unittest.TestCase):
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

    def test_t03_without_evidence_is_structure_only(self) -> None:
        result = self.run_checker(
            "check",
            "t03-agent-instruction",
            "--root",
            str(ROOT),
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["lesson_id"], "t03-agent-instruction")
        self.assertEqual(document["result"], "partial")
        self.assertTrue(document["anonymous"])
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "instruction-page",
                "instruction-simulator",
                "instruction-contract",
                "instruction-scenarios",
                "instruction-evidence-executed",
                "instruction-migration-executed",
            ],
        )

    def test_t03_accepts_complete_comparison_and_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "t03-evidence.json"
            evidence_path.write_text(
                json.dumps(evidence_document(["passed"] * len(CHECK_IDS)), ensure_ascii=False),
                encoding="utf-8",
            )
            result = self.run_checker(
                "check",
                "t03-agent-instruction",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["experiment"]["baseline_id"], "telemetry-report-v1")
        self.assertEqual(document["experiment"]["migration_variants"], ["pressure-night"])
        self.assertNotIn("工程化指令", result.stdout)

    def test_t03_preserves_partial_result_for_incomplete_runs(self) -> None:
        experiment = {
            "version": "2",
            "baseline_id": "telemetry-report-v1",
            "completed_scenarios": ["baseline"],
            "migration_variants": [],
            "migration_contracts": [],
            "latest": {
                "scenario_id": "baseline",
                "variant_id": "temperature-daily",
                "variant_subject": "温度",
                "variant_unit": "°C",
                "variant_limit": "最近 5 条有效记录",
                "ambiguous_outcome": "under-specified",
                "engineered_outcome": "controlled",
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "partial.json"
            evidence_path.write_text(
                json.dumps(evidence_document(["passed", "passed", "failed", "failed", "failed", "failed"])),
                encoding="utf-8",
            )
            value = json.loads(evidence_path.read_text(encoding="utf-8"))
            value["experiment"] = experiment
            evidence_path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t03-agent-instruction",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "partial")

    def test_t03_rejects_passed_injection_without_injection_run(self) -> None:
        value = evidence_document(["passed"] * len(CHECK_IDS))
        value["experiment"] = {
            "version": "2",
            "baseline_id": "telemetry-report-v1",
            "completed_scenarios": ["baseline", "conflict", "long"],
            "migration_variants": ["pressure-night"],
            "migration_contracts": [
                {"id": "pressure-night", "subject": "压力", "unit": "kPa", "limit": "最近 3 条有效记录"}
            ],
            "latest": None,
        }
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "invalid.json"
            evidence_path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t03-agent-instruction",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("injection", result.stderr.lower())

    def test_t03_rejects_prompt_and_path_fields_at_public_boundary(self) -> None:
        value = evidence_document(["passed"] * len(CHECK_IDS))
        value["experiment"]["prompt"] = "C:\\Users\\Ada\\private.txt"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "sensitive.json"
            evidence_path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t03-agent-instruction",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported fields", result.stderr.lower())

    def test_t03_rejects_out_of_order_scenarios(self) -> None:
        value = evidence_document(["passed"] * len(CHECK_IDS))
        value["experiment"]["completed_scenarios"] = [  # type: ignore[index]
            "baseline",
            "injection",
            "conflict",
            "long",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "order.json"
            evidence_path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t03-agent-instruction",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixed order", result.stderr.lower())

    def test_t03_rejects_mismatched_migration_contract(self) -> None:
        value = evidence_document(["passed"] * len(CHECK_IDS))
        value["experiment"]["migration_contracts"][0]["unit"] = "°C"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "variant-contract.json"
            evidence_path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t03-agent-instruction",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("migration contract", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
