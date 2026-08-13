"""External-behavior tests for the T26 offline Python Agent loop."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "checker"
LAB = ROOT / "labs" / "api-agent-loop"
sys.path.insert(0, str(LAB))

from agent_loop import (  # noqa: E402
    FixtureResponse,
    LESSON_ID,
    SCENARIOS,
    StructuredOutputError,
    ToolExecution,
    build_evidence,
    run_agent_loop,
    validate_structured_output,
)


COURSE_VERSION = json.loads(
    (ROOT / "course-version.json").read_text(encoding="utf-8")
)["course_version"]


class OfflineAgentLoopTests(unittest.TestCase):
    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(CHECKER)
        return subprocess.run(
            [sys.executable, "-m", "course_check", *args],
            cwd=CHECKER,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_all_fixture_scenarios_close_with_observable_control_flow(self) -> None:
        evidence = build_evidence(course_version=COURSE_VERSION, checked_on="2026-08-13")

        self.assertEqual(evidence["lesson_id"], LESSON_ID)
        self.assertEqual(evidence["result"], "passed")
        self.assertTrue(evidence["anonymous"])
        self.assertEqual(
            [check["id"] for check in evidence["evidence"]],
            [
                "deterministic-fixture",
                "response-tool-loop",
                "state-refill",
                "structured-output",
                "tool-failure-stop",
                "invalid-arguments-recovery",
                "budget-stop",
                "retry-recovery",
                "framework-free",
            ],
        )
        cases = {case["scenario"]: case for case in evidence["experiment"]["cases"]}
        self.assertEqual(tuple(cases), SCENARIOS)
        self.assertEqual(cases["success"]["outcome"], "success")
        self.assertEqual(cases["tool-failure"]["outcome"], "failure")
        self.assertEqual(cases["invalid-args"]["outcome"], "invalid-args")
        self.assertEqual(cases["budget-stop"]["stop_reason"], "max_steps")
        self.assertEqual(cases["retry-recovery"]["outcome"], "retry-recovery")
        self.assertEqual(cases["retry-recovery"]["retry_count"], 1)

    def test_response_tool_execution_and_state_refill_are_separate_events(self) -> None:
        case = run_agent_loop("success")
        self.assertEqual(
            [event["kind"] for event in case["events"]],
            [
                "response",
                "tool_call",
                "tool_execution",
                "state_refill",
                "response",
                "structured_output",
                "stop",
            ],
        )
        self.assertEqual(case["stop_reason"], "completed")
        self.assertTrue(case["output_valid"])

    def test_provider_adapters_must_normalize_at_the_two_public_seams(self) -> None:
        class ExternalResponseAdapter:
            def __init__(self) -> None:
                self.observed_attempts: list[int] = []

            def respond(self, state: object) -> FixtureResponse:
                if not isinstance(state, dict):
                    raise AssertionError("the loop must supply a state mapping")
                self.observed_attempts.append(state["tool_attempts"])
                if not state["tool_results"]:
                    return FixtureResponse(
                        kind="tool_call",
                        text="external adapter requests one local read",
                        tool_name="read_telemetry",
                        arguments={"device_id": "adapter-17"},
                    )
                return FixtureResponse(
                    kind="final",
                    text="external adapter returns normalized structured output",
                    output={
                        "status": "completed",
                        "summary": "Adapter received a local synthetic reading.",
                        "reading": 42,
                        "anomaly": False,
                        "attempts": state["tool_attempts"],
                    },
                )

        class ExternalToolAdapter:
            def __init__(self) -> None:
                self.observed_arguments: list[object] = []

            def execute(self, arguments: object) -> ToolExecution:
                self.observed_arguments.append(arguments)
                return ToolExecution(True, "ok", value=42, unit="degC")

        source = ExternalResponseAdapter()
        tool = ExternalToolAdapter()
        case = run_agent_loop(
            "success",
            response_source=source,
            tool_executor=tool,
        )

        self.assertEqual(source.observed_attempts, [0, 1])
        self.assertEqual(tool.observed_arguments, [{"device_id": "adapter-17"}])
        self.assertEqual(case["structured_output"]["reading"], 42)
        self.assertEqual(case["outcome"], "success")

    def test_invalid_args_and_retry_recovery_are_not_fake_successes(self) -> None:
        invalid = run_agent_loop("invalid-args")
        invalid_statuses = [event["status"] for event in invalid["events"]]
        self.assertIn("invalid-arguments", invalid_statuses)
        self.assertEqual(invalid["outcome"], "invalid-args")
        self.assertEqual(invalid["structured_output"]["status"], "completed")

        recovered = run_agent_loop("retry-recovery", retry_budget=1)
        recovered_statuses = [event["status"] for event in recovered["events"]]
        self.assertIn("error", recovered_statuses)
        self.assertEqual(recovered["retry_count"], 1)
        self.assertEqual(recovered["outcome"], "retry-recovery")
        self.assertEqual(recovered["structured_output"]["status"], "completed")

        exhausted = run_agent_loop("retry-recovery", retry_budget=0)
        self.assertEqual(exhausted["outcome"], "failure")
        self.assertEqual(exhausted["structured_output"]["status"], "failed")

    def test_budget_stop_has_no_structured_output(self) -> None:
        case = run_agent_loop("budget-stop", max_steps=1)

        self.assertEqual(case["outcome"], "budget-stop")
        self.assertEqual(case["stop_reason"], "max_steps")
        self.assertFalse(case["output_valid"])
        self.assertIsNone(case["structured_output"])
        self.assertEqual(case["events"][-1]["status"], "budget")

    def test_structured_output_contract_rejects_extra_or_inconsistent_fields(self) -> None:
        with self.assertRaises(StructuredOutputError):
            validate_structured_output(
                {
                    "status": "completed",
                    "summary": "ok",
                    "reading": None,
                    "anomaly": False,
                    "attempts": 1,
                }
            )
        with self.assertRaises(StructuredOutputError):
            validate_structured_output(
                {
                    "status": "failed",
                    "summary": "failed",
                    "reading": None,
                    "anomaly": False,
                    "attempts": 1,
                    "extra": "not allowed",
                }
            )

    def test_checker_accepts_complete_runner_evidence(self) -> None:
        evidence = build_evidence(course_version=COURSE_VERSION, checked_on="2026-08-13")
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t26-evidence.json"
            fixture.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                LESSON_ID,
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["lesson_id"], LESSON_ID)
        self.assertEqual(
            [case["scenario"] for case in document["experiment"]["cases"]],
            list(SCENARIOS),
        )
        self.assertNotIn('"structured_output":', json.dumps(document, ensure_ascii=False))
        self.assertNotIn(str(fixture), result.stdout)

    def test_checker_rejects_forged_checks_and_sensitive_nested_fields(self) -> None:
        evidence = build_evidence(course_version=COURSE_VERSION, checked_on="2026-08-13")
        forged = copy.deepcopy(evidence)
        forged["experiment"]["cases"] = forged["experiment"]["cases"][:-1]
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "forged.json"
            fixture.write_text(json.dumps(forged, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                LESSON_ID,
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checks", result.stderr)

        sensitive = copy.deepcopy(evidence)
        sensitive["experiment"]["path"] = "C:\\private\\evidence.json"
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "sensitive.json"
            fixture.write_text(json.dumps(sensitive, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                LESSON_ID,
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr)

    def test_structure_check_is_partial_without_learner_evidence(self) -> None:
        result = self.run_checker(
            "check",
            LESSON_ID,
            "--root",
            str(ROOT),
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], LESSON_ID)
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "offline-agent-loop-page",
                "offline-agent-loop-runner",
                "offline-agent-loop-contract",
                "offline-agent-loop-checker",
                "offline-agent-loop-sources",
                "offline-agent-loop-evidence-executed",
            ],
        )


if __name__ == "__main__":
    unittest.main()
