"""Public evidence-loop seam tests for Issue #3.

The tests exercise the learner-facing checker command and the small, stable
evidence document API.  They intentionally do not assert how the checker
finds a lesson artifact; only the anonymous result that can cross into the
course website is part of this contract.
"""

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

from course_check.evidence import (
    EvidenceError,
    build_evidence_document,
    classify_checks,
    validate_evidence_document,
)


COURSE_VERSION = json.loads(
    (ROOT / "course-version.json").read_text(encoding="utf-8")
)["course_version"]


class EvidenceDocumentTests(unittest.TestCase):
    def test_checker_classifies_correct_partial_error_and_alternative_results(self) -> None:
        self.assertEqual(classify_checks(["passed", "passed"]), "passed")
        self.assertEqual(classify_checks(["passed", "failed"]), "partial")
        self.assertEqual(classify_checks(["failed", "failed"]), "failed")
        self.assertEqual(classify_checks(["alternative", "passed"]), "alternative")

    def test_each_result_state_can_cross_the_json_boundary(self) -> None:
        cases = (
            ("passed", ["passed", "passed"]),
            ("partial", ["passed", "failed"]),
            ("failed", ["failed", "failed"]),
            ("alternative", ["alternative", "passed"]),
        )
        for expected, results in cases:
            document = build_evidence_document(
                course_version=COURSE_VERSION,
                lesson_id="t01-foundation",
                checks=[
                    {"id": f"check-{index}", "result": result}
                    for index, result in enumerate(results)
                ],
            )
            self.assertEqual(document["result"], expected)
            self.assertEqual(validate_evidence_document(document)["result"], expected)

    def test_evidence_document_is_anonymous_and_versioned(self) -> None:
        document = build_evidence_document(
            course_version=COURSE_VERSION,
            lesson_id="t01-foundation",
            checks=[
                {"id": "course-version-lock", "result": "passed"},
                {"id": "foundation-contract", "result": "passed"},
            ],
        )

        self.assertEqual(document["contract"], "agent-engineering-course/evidence")
        self.assertEqual(document["contract_version"], "1")
        self.assertEqual(document["course_version"], COURSE_VERSION)
        self.assertEqual(document["lesson_id"], "t01-foundation")
        self.assertEqual(document["result"], "passed")
        self.assertTrue(document["anonymous"])
        encoded = json.dumps(document, ensure_ascii=False)
        for forbidden in ("source.py", "C:\\Users\\", "api_key", "sk-secret"):
            self.assertNotIn(forbidden, encoded)

        validated = validate_evidence_document(document)
        self.assertEqual(validated, document)

    def test_evidence_validation_rejects_sensitive_result_fields(self) -> None:
        document = build_evidence_document(
            course_version=COURSE_VERSION,
            lesson_id="t01-foundation",
            checks=[{"id": "foundation-contract", "result": "passed"}],
        )
        document["evidence"][0]["path"] = "C:\\Users\\Ada\\secret.txt"

        with self.assertRaises(EvidenceError):
            validate_evidence_document(document)


class EvidenceCommandTests(unittest.TestCase):
    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(CHECKER)
        return subprocess.run(
            [sys.executable, "-m", "course_check", *args],
            cwd=CHECKER,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_public_check_command_emits_importable_anonymous_json(self) -> None:
        result = self.run_checker(
            "check",
            "t01-foundation",
            "--root",
            str(ROOT),
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["course_version"], COURSE_VERSION)
        self.assertEqual(document["lesson_id"], "t01-foundation")
        self.assertEqual(document["result"], "passed")
        self.assertTrue(document["anonymous"])

    def test_public_check_command_writes_json_without_leaking_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "evidence.json"
            result = self.run_checker(
                "check",
                "t01-foundation",
                "--root",
                str(ROOT),
                "--output",
                str(output_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_path.exists())
            document = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(document["result"], "passed")
            self.assertNotIn(str(output_path), output_path.read_text(encoding="utf-8"))
            self.assertIn("passed", result.stdout.lower())

    def test_public_check_command_preserves_all_four_result_states(self) -> None:
        cases = (
            ("partial", ["passed", "failed"]),
            ("failed", ["failed", "failed"]),
            ("alternative", ["alternative", "passed"]),
        )
        with tempfile.TemporaryDirectory() as temporary:
            for expected, results in cases:
                fixture = Path(temporary) / f"{expected}.json"
                fixture.write_text(
                    json.dumps(
                        {
                            "lesson_id": "t01-foundation",
                            "checks": [
                                {"id": f"check-{index}", "result": result}
                                for index, result in enumerate(results)
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                result = self.run_checker(
                    "check",
                    "t01-foundation",
                    "--root",
                    str(ROOT),
                    "--evidence-file",
                    str(fixture),
                    "--json",
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["result"], expected)


if __name__ == "__main__":
    unittest.main()
