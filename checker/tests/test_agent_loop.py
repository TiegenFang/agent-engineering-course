"""Public checker seam tests for the deterministic Agent loop lesson."""

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
COURSE_VERSION = "0.1.0-foundation"


class AgentLoopCheckerTests(unittest.TestCase):
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

    def test_t02_checker_emits_a_complete_anonymous_trace_result(self) -> None:
        result = self.run_checker(
            "check",
            "t02-agent-loop",
            "--root",
            str(ROOT),
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["course_version"], COURSE_VERSION)
        self.assertEqual(document["lesson_id"], "t02-agent-loop")
        self.assertEqual(document["result"], "passed")
        self.assertTrue(document["anonymous"])
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            ["agent-loop-page", "agent-loop-simulator", "agent-loop-trace-contract"],
        )

    def test_t02_checker_accepts_exported_evidence_document(self) -> None:
        exported = {
            "contract": "agent-engineering-course/evidence",
            "contract_version": "1",
            "course_version": COURSE_VERSION,
            "lesson_id": "t02-agent-loop",
            "result": "passed",
            "anonymous": True,
            "checked_on": "2026-08-13",
            "summary": "所有必需证据均已通过。",
            "evidence": [
                {"id": "prediction-recorded", "result": "passed"},
                {"id": "trace-observed", "result": "passed"},
                {"id": "stop-condition-observed", "result": "passed"},
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "t02-agent-loop-evidence.json"
            evidence_path.write_text(json.dumps(exported), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t02-agent-loop",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["lesson_id"], "t02-agent-loop")
        self.assertEqual(document["result"], "passed")
        self.assertNotIn(str(evidence_path), result.stdout)


if __name__ == "__main__":
    unittest.main()
