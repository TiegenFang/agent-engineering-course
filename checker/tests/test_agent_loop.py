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
COURSE_VERSION = json.loads(
    (ROOT / "course-version.json").read_text(encoding="utf-8")
)["course_version"]

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
BUDGET_TRACE_IDS = [
    "prediction-1",
    "response-1",
    "tool-request-1",
    "budget-stop-1",
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


def trace_fixture(
    ids: list[str],
    *,
    outcome: str = "success",
    max_steps: int = 6,
    status_overrides: dict[str, str] | None = None,
    result_overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    default_status = {
        "response-1": "ok",
        "tool-request-1": "ok",
        "tool-execution-1": "error" if outcome == "error" else "ok",
        "tool-result-1": "error" if outcome == "error" else "ok",
        "response-2": "ok",
        "stop-1": "error" if outcome == "error" else "passed",
        "budget-stop-1": "budget",
    }
    return {
        "version": "1",
        "outcome": outcome,
        "max_steps": max_steps,
        "steps": [
            {
                "id": step_id,
                "kind": TRACE_KINDS.get(step_id, "stop" if step_id == "budget-stop-1" else "unknown"),
                "result": (result_overrides or {}).get(
                    step_id, "alternative" if step_id == "budget-stop-1" else "passed"
                ),
                **(
                    {
                        "status": (status_overrides or {}).get(
                            step_id, default_status.get(step_id, "ok")
                        )
                    }
                    if step_id != "prediction-1"
                    else {}
                ),
            }
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
            encoding="utf-8",
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

    def test_t02_checker_accepts_budget_stop_as_an_alternative(self) -> None:
        exported = {
            "contract": "agent-engineering-course/evidence",
            "contract_version": "1",
            "course_version": COURSE_VERSION,
            "lesson_id": "t02-agent-loop",
            "result": "alternative",
            "anonymous": True,
            "checked_on": "2026-08-13",
            "summary": "检测到满足验收目标的替代实现。",
            "evidence": [
                {"id": "prediction-recorded", "result": "passed"},
                {"id": "trace-observed", "result": "passed"},
                {"id": "stop-condition-observed", "result": "alternative"},
            ],
            "trace": trace_fixture(BUDGET_TRACE_IDS, outcome="budget-stop", max_steps=2),
        }
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "budget-stop.json"
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
        self.assertEqual(json.loads(result.stdout)["result"], "alternative")

    def test_t02_checker_rejects_budget_stop_after_error_status(self) -> None:
        exported = {
            "contract": "agent-engineering-course/evidence",
            "contract_version": "1",
            "course_version": COURSE_VERSION,
            "lesson_id": "t02-agent-loop",
            "result": "alternative",
            "anonymous": True,
            "checked_on": "2026-08-13",
            "summary": "检测到满足验收目标的替代实现。",
            "evidence": [
                {"id": "prediction-recorded", "result": "passed"},
                {"id": "trace-observed", "result": "passed"},
                {"id": "stop-condition-observed", "result": "alternative"},
            ],
            "trace": trace_fixture(
                ["prediction-1", "response-1", "tool-request-1", "tool-execution-1", "budget-stop-1"],
                outcome="budget-stop",
                max_steps=3,
                status_overrides={"tool-execution-1": "error"},
            ),
        }
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "budget-error-mix.json"
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
        self.assertIn("budget-stop", result.stderr)

    def test_t02_checker_rejects_inconsistent_trace_status_and_result(self) -> None:
        malformed_traces = (
            trace_fixture(SUCCESS_TRACE_IDS, status_overrides={"stop-1": "error"}),
            trace_fixture(ERROR_TRACE_IDS, status_overrides={"tool-execution-1": "ok"}, outcome="error"),
            trace_fixture(SUCCESS_TRACE_IDS, result_overrides={"tool-result-1": "failed"}),
        )
        for trace in malformed_traces:
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
                "trace": trace,
            }
            with tempfile.TemporaryDirectory() as temporary:
                evidence_path = Path(temporary) / "semantic-mismatch.json"
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

            self.assertNotEqual(result.returncode, 0, trace)

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
