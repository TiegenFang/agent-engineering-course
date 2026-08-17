"""A dependency-free, deterministic Agent Application loop for T26.

The fixture deliberately has no model/API client.  It behaves like a model
response source so that the learner can own the control flow: receive a
response, validate a tool call, execute a tool, refill state, and either ask
for another response or stop.  Every value is synthetic and local.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Protocol, Sequence


LESSON_ID = "t26-offline-agent-loop"
EXPERIMENT_VERSION = "1"
IMPLEMENTATION = "python-stdlib"
FRAMEWORK = "none"
SCENARIOS = (
    "success",
    "tool-failure",
    "invalid-args",
    "budget-stop",
    "retry-recovery",
)
DEFAULT_MAX_STEPS = 4
DEFAULT_BUDGET_MAX_STEPS = 1
MAX_MAX_STEPS = 8
DEFAULT_RETRY_BUDGET = 1
MAX_RETRY_BUDGET = 3
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{2,31}$")
UNIT = "degC"
PUBLIC_EVENT_KINDS = (
    "response",
    "tool_call",
    "tool_execution",
    "state_refill",
    "structured_output",
    "stop",
)
OUTPUT_KEYS = (
    "status",
    "summary",
    "reading",
    "anomaly",
    "attempts",
)
OUTPUT_STATUSES = ("completed", "failed")


class LoopInputError(ValueError):
    """Raised for learner-controlled loop settings or malformed tool input."""


class StructuredOutputError(ValueError):
    """Raised when the final response does not satisfy the output contract."""


@dataclass(frozen=True)
class FixtureResponse:
    """The only response shape the deterministic fixture can produce."""

    kind: str
    text: str
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    output: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolExecution:
    ok: bool
    status: str
    value: int | None = None
    unit: str | None = None
    error_code: str | None = None


class ResponseSource(Protocol):
    """Adapter seam for a response provider after it is normalized locally."""

    def respond(self, state: Mapping[str, Any]) -> FixtureResponse:
        """Return one provider-neutral response without mutating ``state``."""


class ToolExecutor(Protocol):
    """Adapter seam for the application-owned local tool implementation."""

    def execute(self, arguments: Any) -> ToolExecution:
        """Return a classified, provider-neutral local tool result."""


def _require_scenario(scenario: str) -> str:
    if scenario not in SCENARIOS:
        choices = ", ".join(SCENARIOS)
        raise LoopInputError(f"scenario must be one of: {choices}")
    return scenario


def _require_bounded_integer(value: int, label: str, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= upper:
        raise LoopInputError(f"{label} must be an integer from 1 to {upper}")
    return value


def _require_retry_budget(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_RETRY_BUDGET:
        raise LoopInputError(f"retry_budget must be an integer from 0 to {MAX_RETRY_BUDGET}")
    return value


def deterministic_reading(device_id: str = "telemetry-17") -> int:
    """Return a stable synthetic reading for a safe identifier."""

    if not isinstance(device_id, str) or not SAFE_IDENTIFIER.fullmatch(device_id):
        raise LoopInputError("device_id must be a safe synthetic identifier")
    # Keep the fixture deterministic without relying on Python's randomized hash.
    value = sum((index + 3) * ord(character) for index, character in enumerate(device_id))
    return 20 + value % 40


def validate_tool_arguments(arguments: Any) -> dict[str, str]:
    """Validate the tool schema before executing the tool body."""

    if not isinstance(arguments, Mapping):
        raise LoopInputError("tool arguments must be an object")
    if set(arguments) != {"device_id"}:
        raise LoopInputError("tool arguments must contain only device_id")
    device_id = arguments["device_id"]
    if not isinstance(device_id, str) or not SAFE_IDENTIFIER.fullmatch(device_id):
        raise LoopInputError("device_id must be a safe synthetic identifier")
    return {"device_id": device_id}


def tool_schema() -> dict[str, Any]:
    """Return the small, provider-neutral schema owned by the harness."""

    return {
        "name": "read_telemetry",
        "description": "Read one synthetic telemetry value; no files or network.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "pattern": "^[A-Za-z][A-Za-z0-9._-]{2,31}$",
                }
            },
            "required": ["device_id"],
            "additionalProperties": False,
        },
    }


class DeterministicResponseFixture:
    """A scripted response source that stands in for a model response."""

    def __init__(self, scenario: str) -> None:
        self.scenario = _require_scenario(scenario)

    def respond(self, state: Mapping[str, Any]) -> FixtureResponse:
        results = list(state.get("tool_results", []))
        if self.scenario == "budget-stop":
            return self._tool_call()

        if not results:
            if self.scenario == "invalid-args":
                # The harness must reject this before the tool body runs.
                return self._tool_call(arguments={"device_id": 17})
            return self._tool_call()

        last = results[-1]
        status = last.get("status")
        if status == "invalid-arguments" and self.scenario == "invalid-args":
            return self._tool_call()
        if status == "error" and self.scenario == "retry-recovery":
            retries = int(state.get("retry_count", 0))
            if retries < int(state.get("retry_budget", DEFAULT_RETRY_BUDGET)):
                return self._tool_call()
        if status == "ok":
            value = int(last["value"])
            return FixtureResponse(
                kind="final",
                text="工具结果已回填；生成严格结构化结果。",
                output={
                    "status": "completed",
                    "summary": f"Synthetic telemetry is {value} {UNIT}.",
                    "reading": value,
                    "anomaly": value >= 50,
                    "attempts": int(state.get("tool_attempts", 0)),
                },
            )

        return FixtureResponse(
            kind="final",
            text="工具未能提供可用读数；结构化结果明确报告失败。",
            output={
                "status": "failed",
                "summary": "No synthetic reading was accepted; the loop stopped safely.",
                "reading": None,
                "anomaly": False,
                "attempts": int(state.get("tool_attempts", 0)),
            },
        )

    @staticmethod
    def _tool_call(arguments: dict[str, Any] | None = None) -> FixtureResponse:
        return FixtureResponse(
            kind="tool_call",
            text="需要读取一个合成遥测值。",
            tool_name="read_telemetry",
            arguments=arguments or {"device_id": "telemetry-17"},
        )


class DeterministicTelemetryTool:
    """A local tool with schema validation and deterministic failure modes."""

    def __init__(self, scenario: str) -> None:
        self.scenario = _require_scenario(scenario)
        self.calls = 0

    def execute(self, arguments: Any) -> ToolExecution:
        self.calls += 1
        try:
            normalized = validate_tool_arguments(arguments)
        except LoopInputError:
            return ToolExecution(False, "invalid-arguments", error_code="invalid-arguments")

        if self.scenario == "tool-failure":
            return ToolExecution(False, "error", error_code="tool-unavailable")
        if self.scenario == "retry-recovery" and self.calls == 1:
            return ToolExecution(False, "error", error_code="transient-unavailable")

        return ToolExecution(
            True,
            "ok",
            value=deterministic_reading(normalized["device_id"]),
            unit=UNIT,
        )


def validate_structured_output(output: Any) -> dict[str, Any]:
    """Enforce the tiny output contract before the application reports success."""

    if not isinstance(output, Mapping):
        raise StructuredOutputError("structured output must be an object")
    if set(output) != set(OUTPUT_KEYS):
        raise StructuredOutputError("structured output fields do not match the contract")
    status = output["status"]
    if status not in OUTPUT_STATUSES:
        raise StructuredOutputError("structured output status is unsupported")
    summary = output["summary"]
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 240:
        raise StructuredOutputError("structured output summary must be 1-240 characters")
    reading = output["reading"]
    if reading is not None and (
        isinstance(reading, bool) or not isinstance(reading, int) or not 0 <= reading <= 100
    ):
        raise StructuredOutputError("structured output reading must be null or an integer from 0 to 100")
    anomaly = output["anomaly"]
    if not isinstance(anomaly, bool):
        raise StructuredOutputError("structured output anomaly must be boolean")
    attempts = output["attempts"]
    if isinstance(attempts, bool) or not isinstance(attempts, int) or not 1 <= attempts <= MAX_MAX_STEPS:
        raise StructuredOutputError("structured output attempts is outside the loop budget")
    if status == "completed" and reading is None:
        raise StructuredOutputError("completed structured output needs a reading")
    if status == "failed" and reading is not None:
        raise StructuredOutputError("failed structured output cannot claim a reading")
    return {key: output[key] for key in OUTPUT_KEYS}


def _event(
    event_id: str,
    kind: str,
    turn: int,
    *,
    status: str,
    result: str = "passed",
) -> dict[str, Any]:
    return {
        "id": event_id,
        "kind": kind,
        "turn": turn,
        "status": status,
        "result": result,
    }


def _outcome_for(scenario: str, state: Mapping[str, Any], stop_reason: str) -> str:
    if stop_reason == "max_steps":
        return "budget-stop"
    if scenario == "retry-recovery" and int(state.get("retry_count", 0)) > 0:
        return "retry-recovery"
    if scenario == "retry-recovery":
        return "failure"
    if scenario == "invalid-args":
        return "invalid-args"
    if scenario == "tool-failure":
        return "failure"
    return "success"


def run_agent_loop(
    scenario: str = "success",
    *,
    max_steps: int = DEFAULT_MAX_STEPS,
    retry_budget: int = DEFAULT_RETRY_BUDGET,
    response_source: ResponseSource | None = None,
    tool_executor: ToolExecutor | None = None,
) -> dict[str, Any]:
    """Run one deterministic loop and return a public, path-free trace.

    ``max_steps`` counts model-response turns. Tool validation, execution and
    state refill belong to the same turn, so even a failing tool cannot cause
    an unbounded extra turn. ``response_source`` and ``tool_executor`` are
    optional adapter seams: callers must normalize external APIs into the two
    public dataclasses, while the default remains deterministic and offline.
    The returned trace intentionally omits prompt text, tool arguments and
    implementation details.
    """

    scenario = _require_scenario(scenario)
    max_steps = _require_bounded_integer(max_steps, "max_steps", MAX_MAX_STEPS)
    retry_budget = _require_retry_budget(retry_budget)
    fixture = response_source if response_source is not None else DeterministicResponseFixture(scenario)
    tool = tool_executor if tool_executor is not None else DeterministicTelemetryTool(scenario)
    state: dict[str, Any] = {
        "tool_results": [],
        "tool_attempts": 0,
        "retry_count": 0,
        "retry_budget": retry_budget,
    }
    events: list[dict[str, Any]] = []

    for turn in range(1, max_steps + 1):
        response = fixture.respond(state)
        if not isinstance(response, FixtureResponse):
            raise LoopInputError("response_source must return FixtureResponse")
        events.append(_event(f"response-{turn}", "response", turn, status="ok"))
        if response.kind == "final":
            try:
                output = validate_structured_output(response.output)
            except StructuredOutputError:
                output = None
                events.append(_event(f"structured-output-{turn}", "structured_output", turn, status="error", result="failed"))
                events.append(_event(f"stop-{turn}", "stop", turn, status="error", result="failed"))
                return {
                    "version": EXPERIMENT_VERSION,
                    "scenario": scenario,
                    "outcome": "failure",
                    "max_steps": max_steps,
                    "stop_reason": "invalid-structured-output",
                    "retry_count": state["retry_count"],
                    "tool_attempts": state["tool_attempts"],
                    "output_valid": False,
                    "structured_output": None,
                    "events": events,
                }
            events.append(_event(f"structured-output-{turn}", "structured_output", turn, status="passed"))
            stop_reason = "completed" if output["status"] == "completed" else "tool_error"
            events.append(_event(f"stop-{turn}", "stop", turn, status="passed"))
            return {
                "version": EXPERIMENT_VERSION,
                "scenario": scenario,
                "outcome": _outcome_for(scenario, state, stop_reason),
                "max_steps": max_steps,
                "stop_reason": stop_reason,
                "retry_count": state["retry_count"],
                "tool_attempts": state["tool_attempts"],
                "output_valid": True,
                "structured_output": output,
                "events": events,
            }

        if (
            scenario == "retry-recovery"
            and state["tool_results"]
            and state["tool_results"][-1].get("status") == "error"
        ):
            # Count a retry when the fixture actually emits the second call,
            # not when the first transient error is observed.
            state["retry_count"] += 1
        events.append(_event(f"tool-call-{turn}", "tool_call", turn, status="ok"))
        state["tool_attempts"] += 1
        execution = tool.execute(response.arguments)
        if not isinstance(execution, ToolExecution):
            raise LoopInputError("tool_executor must return ToolExecution")
        execution_status = "ok" if execution.ok else execution.status
        events.append(
            _event(
                f"tool-execution-{turn}",
                "tool_execution",
                turn,
                status=execution_status,
                result="passed",
            )
        )
        if execution.ok:
            state["tool_results"].append(
                {"status": "ok", "value": execution.value, "unit": execution.unit}
            )
        else:
            state["tool_results"].append(
                {"status": execution.status, "error_code": execution.error_code}
            )
        events.append(
            _event(
                f"state-refill-{turn}",
                "state_refill",
                turn,
                status="ok" if execution.ok else execution.status,
                result="passed",
            )
        )

    events.append(
        _event(
            f"stop-{max_steps + 1}",
            "stop",
            max_steps,
            status="budget",
            result="passed",
        )
    )
    return {
        "version": EXPERIMENT_VERSION,
        "scenario": scenario,
        "outcome": "budget-stop",
        "max_steps": max_steps,
        "stop_reason": "max_steps",
        "retry_count": state["retry_count"],
        "tool_attempts": state["tool_attempts"],
        "output_valid": False,
        "structured_output": None,
        "events": events,
    }


def _case_is_observable(case: Mapping[str, Any], scenario: str) -> bool:
    if case.get("scenario") != scenario or case.get("version") != EXPERIMENT_VERSION:
        return False
    events = case.get("events")
    if not isinstance(events, list) or not events:
        return False
    kinds = [event.get("kind") for event in events if isinstance(event, Mapping)]
    statuses = [event.get("status") for event in events if isinstance(event, Mapping)]
    if "response" not in kinds or "tool_call" not in kinds or "tool_execution" not in kinds:
        return False
    if "state_refill" not in kinds or kinds[-1] != "stop":
        return False
    if scenario == "success":
        return case.get("outcome") == "success" and case.get("output_valid") is True
    if scenario == "tool-failure":
        return case.get("outcome") == "failure" and "error" in statuses and case.get("output_valid") is True
    if scenario == "invalid-args":
        return (
            case.get("outcome") == "invalid-args"
            and "invalid-arguments" in statuses
            and case.get("output_valid") is True
        )
    if scenario == "budget-stop":
        return case.get("outcome") == "budget-stop" and case.get("stop_reason") == "max_steps" and case.get("output_valid") is False
    if scenario == "retry-recovery":
        return (
            case.get("outcome") == "retry-recovery"
            and int(case.get("retry_count", 0)) >= 1
            and "error" in statuses
            and case.get("output_valid") is True
        )
    return False


def derive_checks(cases: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    by_scenario = {
        case.get("scenario"): case
        for case in cases
        if isinstance(case, Mapping)
    }
    success = by_scenario.get("success", {})
    retry = by_scenario.get("retry-recovery", {})
    all_cases = all(_case_is_observable(by_scenario.get(scenario, {}), scenario) for scenario in SCENARIOS)
    state_refilled = all(
        "state_refill" in [event.get("kind") for event in by_scenario.get(scenario, {}).get("events", []) if isinstance(event, Mapping)]
        for scenario in ("success", "tool-failure", "invalid-args", "retry-recovery")
    )
    return [
        {"id": "deterministic-fixture", "result": "passed" if all_cases else "failed"},
        {"id": "response-tool-loop", "result": "passed" if _case_is_observable(success, "success") else "failed"},
        {"id": "state-refill", "result": "passed" if state_refilled else "failed"},
        {"id": "structured-output", "result": "passed" if _case_is_observable(success, "success") and _case_is_observable(retry, "retry-recovery") else "failed"},
        {"id": "tool-failure-stop", "result": "passed" if _case_is_observable(by_scenario.get("tool-failure", {}), "tool-failure") else "failed"},
        {"id": "invalid-arguments-recovery", "result": "passed" if _case_is_observable(by_scenario.get("invalid-args", {}), "invalid-args") else "failed"},
        {"id": "budget-stop", "result": "passed" if _case_is_observable(by_scenario.get("budget-stop", {}), "budget-stop") else "failed"},
        {"id": "retry-recovery", "result": "passed" if _case_is_observable(retry, "retry-recovery") else "failed"},
        {"id": "framework-free", "result": "passed"},
    ]


def _public_experiment(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Keep runner output stable and free of prompts, paths, and raw payloads."""

    return {
        "version": EXPERIMENT_VERSION,
        "implementation": IMPLEMENTATION,
        "framework": FRAMEWORK,
        "scenarios": list(SCENARIOS),
        "cases": [dict(case) for case in cases],
    }


def build_evidence(
    cases: Sequence[Mapping[str, Any]] | None = None,
    *,
    course_version: str = "2.0.0",
    checked_on: str | None = None,
) -> dict[str, Any]:
    """Build the learner-facing anonymous evidence fixture."""

    if cases is None:
        cases = [
            run_agent_loop(scenario, max_steps=DEFAULT_BUDGET_MAX_STEPS if scenario == "budget-stop" else DEFAULT_MAX_STEPS)
            for scenario in SCENARIOS
        ]
    checks = derive_checks(cases)
    result = "passed" if all(check["result"] == "passed" for check in checks) else "partial"
    checked_on = checked_on or date.today().isoformat()
    summary = "所有必需证据均已通过。" if result == "passed" else "部分证据已通过，仍有证据需要补齐。"
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": course_version,
        "lesson_id": LESSON_ID,
        "result": result,
        "anonymous": True,
        "checked_on": checked_on,
        "summary": summary,
        "evidence": checks,
        "experiment": _public_experiment(cases),
    }


def run_scenario(scenario: str, **kwargs: Any) -> dict[str, Any]:
    """Compatibility alias used by the lab tests and migration exercises."""

    return run_agent_loop(scenario, **kwargs)


def _course_version_from_repo() -> str:
    root = Path(__file__).resolve().parents[2]
    version_file = root / "course-version.json"
    try:
        value = json.loads(version_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "2.0.0"
    version = value.get("course_version")
    return version if isinstance(version, str) and version else "2.0.0"


def _configure_utf8_output() -> None:
    """Match PowerShell 7's UTF-8 console when Python inherits a legacy code page."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_output()
    parser = argparse.ArgumentParser(description="Run the offline T26 Agent loop fixture")
    parser.add_argument("--scenario", choices=("all", *SCENARIOS), default="all")
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--retry-budget", type=int, default=DEFAULT_RETRY_BUDGET)
    parser.add_argument("--output", type=Path, default=None, help="explicit JSON output path")
    args = parser.parse_args(argv)

    try:
        if args.scenario == "all":
            cases = [
                run_agent_loop(
                    scenario,
                    max_steps=(
                        args.max_steps
                        if args.max_steps is not None
                        else DEFAULT_BUDGET_MAX_STEPS
                        if scenario == "budget-stop"
                        else DEFAULT_MAX_STEPS
                    ),
                    retry_budget=args.retry_budget,
                )
                for scenario in SCENARIOS
            ]
        else:
            max_steps = args.max_steps or (
                DEFAULT_BUDGET_MAX_STEPS if args.scenario == "budget-stop" else DEFAULT_MAX_STEPS
            )
            cases = [
                run_agent_loop(
                    args.scenario,
                    max_steps=max_steps,
                    retry_budget=args.retry_budget,
                )
            ]
        document = build_evidence(
            cases,
            course_version=_course_version_from_repo(),
        )
    except (LoopInputError, OSError, StructuredOutputError) as exc:
        print(f"T26 fixture failed: {exc}", file=sys.stderr)
        return 2

    encoded = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
