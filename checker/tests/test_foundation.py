"""Public foundation seam tests for the course workspace.

These tests deliberately execute the checker through ``python -m course_check``
instead of importing validation helpers.  The command is the learner-facing
surface that later lessons will build on.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
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


if __name__ == "__main__":
    unittest.main()
