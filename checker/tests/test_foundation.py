"""Public foundation seam tests for the course workspace.

These tests deliberately execute the checker through ``python -m course_check``
instead of importing validation helpers.  The command is the learner-facing
surface that later lessons will build on.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "checker"


class FoundationContractTests(unittest.TestCase):
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

    def contract_fixture(self) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        fixture_root = Path(temporary.name)
        for boundary in ("site", "labs", "checker", "docs"):
            (fixture_root / boundary).mkdir(parents=True, exist_ok=True)

        shutil.copy2(ROOT / "course-version.json", fixture_root / "course-version.json")
        for relative_path in (
            Path("docs/contracts/content-contract.json"),
            Path("docs/contracts/lesson.schema.json"),
            Path("docs/sources/source-ledger.json"),
        ):
            destination = fixture_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative_path, destination)
        return temporary

    def test_public_validation_command_accepts_foundation_contract(self) -> None:
        result = self.run_checker("validate", "--root", str(ROOT))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Foundation validation passed", result.stdout)
        self.assertIn("0.1.0-foundation", result.stdout)

    def test_public_contract_contains_unified_version_content_and_sources(self) -> None:
        contract = json.loads((ROOT / "course-version.json").read_text(encoding="utf-8"))
        content = json.loads(
            (ROOT / contract["contracts"]["content"]).read_text(encoding="utf-8")
        )
        sources = json.loads(
            (ROOT / contract["contracts"]["sources"]).read_text(encoding="utf-8")
        )

        self.assertEqual(
            contract["boundaries"],
            {"site": "site", "labs": "labs", "checker": "checker", "docs": "docs"},
        )
        self.assertEqual(contract["course_version"], "0.1.0-foundation")
        self.assertEqual(content["contract_version"], "1")
        self.assertEqual(content["lessons"][0]["id"], "t01-foundation")
        self.assertGreaterEqual(len(sources["entries"]), 1)

    def test_public_validation_rejects_invalid_lesson_contract(self) -> None:
        with self.contract_fixture() as temporary_path:
            fixture_root = Path(temporary_path)
            content_path = fixture_root / "docs/contracts/content-contract.json"
            content = json.loads(content_path.read_text(encoding="utf-8"))
            content["lessons"][0]["verified_on"] = "not-a-date"
            content["lessons"][0]["prerequisites"] = ["missing-lesson"]
            content_path.write_text(
                json.dumps(content, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker("validate", "--root", str(fixture_root))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verified_on", result.stderr)

    def test_public_validation_rejects_incomplete_source_entry(self) -> None:
        with self.contract_fixture() as temporary_path:
            fixture_root = Path(temporary_path)
            sources_path = fixture_root / "docs/sources/source-ledger.json"
            sources = json.loads(sources_path.read_text(encoding="utf-8"))
            del sources["entries"][0]["license_or_terms"]
            sources_path.write_text(
                json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_checker("validate", "--root", str(fixture_root))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("license_or_terms", result.stderr)


if __name__ == "__main__":
    unittest.main()
