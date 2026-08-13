"""Public checker tests for T30's bounded research API seam."""

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


def fixture() -> dict[str, object]:
    import sys as _sys

    _sys.path.insert(0, str(ROOT / "labs" / "research-api-capstone"))
    from research_api_adapter import build_evidence

    return build_evidence(COURSE_VERSION, "pressure-night")


class ResearchApiCapstoneCheckerTests(unittest.TestCase):
    def run_checker(self, path: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(CHECKER)
        return subprocess.run(
            [sys.executable, "-m", "course_check", "check", "t30-research-api-capstone", "--root", str(ROOT), "--evidence-file", str(path), "--json"],
            cwd=CHECKER, env=env, capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def test_offline_pressure_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "t30.json"
            path.write_text(json.dumps(fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["experiment"]["input_variant"], "pressure-night")
        self.assertEqual(document["experiment"]["live_smoke"]["status"], "not-run")
        self.assertNotIn(str(path), result.stdout)

    def test_live_claim_is_rejected(self) -> None:
        value = fixture()
        experiment = value["experiment"]
        assert isinstance(experiment, dict)
        live = experiment["live_smoke"]
        assert isinstance(live, dict)
        live["status"] = "passed"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "claimed.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live", result.stderr.lower())

    def test_sensitive_payload_is_rejected(self) -> None:
        value = fixture()
        experiment = value["experiment"]
        assert isinstance(experiment, dict)
        experiment["raw_prompt"] = "private research data"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
