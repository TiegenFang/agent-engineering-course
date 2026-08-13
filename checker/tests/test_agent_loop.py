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

SUCCESS_TRACE_IDS = [
    "prediction-1",
    "response-1",
    "tool-request-1",
    "tool-execution-1",
    "tool-result-1",
    "response-2",
    "stop-1",
]
ERROR_TRACE_IDS = [
    "prediction-1",
    "response-1",
    "tool-request-1",
    "tool-execution-1",
    "tool-result-1",
    "stop-1",
]
TRACE_KINDS = {
    "prediction-1": "prediction",
    "response-1": "response",
    "tool-request-1": "tool-request",
    "tool-execution-1": "tool-execution",
    "tool-result-1": "tool-result",
    "response-2": "response",
    "stop-1": "stop",
}


def trace_fixture(ids: list[str], *, outcome: str = "success") -> dict[str, object]:
    return {
        "version": "1",
        "outcome": outcome,
        "steps": [
            {"id": step_id, "kind": TRACE_KINDS.get(step_id, "unknown"), "result": "passed"}
            for step_id in ids
        ],
    }


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

    def test_t02_checker_without_evidence_is_structure_only(self) -> None:
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
        self.assertEqual(document["result"], "partial")
        self.assertTrue(document["anonymous"])
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "agent-loop-page",
                "agent-loop-simulator",
                "agent-loop-trace-contract",
                "agent-loop-trace-executed",
            ],
        )

    def test_t02_checker_rejects_empty_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "empty.json"
            evidence_path.write_text(
                json.dumps({"lesson_id": "t02-agent-loop", "checks": []}),
                encoding="utf-8",
            )
            result = self.run_checker(
                "check",
                "t02-agent-loop",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Evidence", result.stderr)

    def test_t02_checker_rejects_arbitrary_evidence_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "arbitrary.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "lesson_id": "t02-agent-loop",
                        "checks": [{"id": "arbitrary-id", "result": "passed"}],
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker(
                "check",
                "t02-agent-loop",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(evidence_path),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("trace", result.stderr.lower())

    def test_t02_checker_accepts_success_and_error_trace_contracts(self) -> None:
        for outcome, ids in (("success", SUCCESS_TRACE_IDS), ("error", ERROR_TRACE_IDS)):
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
                "trace": trace_fixture(ids, outcome=outcome),
            }
            with tempfile.TemporaryDirectory() as temporary:
                evidence_path = Path(temporary) / f"{outcome}.json"
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
            self.assertEqual(json.loads(result.stdout)["result"], "passed")

    def test_t02_checker_rejects_missing_unknown_and_duplicate_trace_ids(self) -> None:
        malformed_traces = (
            SUCCESS_TRACE_IDS[:-1],
            [*SUCCESS_TRACE_IDS[:-1], "unknown-step", "stop-1"],
            [*SUCCESS_TRACE_IDS[:-1], "stop-1", "stop-1"],
        )
        for ids in malformed_traces:
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
                "trace": trace_fixture(ids),
            }
            with tempfile.TemporaryDirectory() as temporary:
                evidence_path = Path(temporary) / "malformed.json"
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

            self.assertNotEqual(result.returncode, 0, ids)

    def test_t02_checker_rejects_old_course_version(self) -> None:
        exported = {
            "contract": "agent-engineering-course/evidence",
            "contract_version": "1",
            "course_version": "0.0.0-old",
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
            "trace": trace_fixture(SUCCESS_TRACE_IDS),
        }
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "old-version.json"
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

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("course_version", result.stderr)

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
            "trace": trace_fixture(SUCCESS_TRACE_IDS),
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
