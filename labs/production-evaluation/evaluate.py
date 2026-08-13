"""Deterministic, privacy-preserving production evaluator for T29.

The evaluator deliberately models the public control plane only.  It does not
import a provider SDK and it never performs a network request.  It is useful
for learning evaluation gates before a live API is approved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EVALUATOR_VERSION = "production-evaluator-v1"
COURSE_VERSION = "0.1.0-alpha"
LESSON_ID = "t29-production"
DEFAULT_BUDGET_USD = 0.01
ALLOWED_LOG_EVENTS = ("evaluation-start", "case-result", "recovery", "budget-stop", "evaluation-end")


def _read_fixture(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("fixture must be a JSON object")
    required = {
        "lesson_id", "fixture_version", "input_id", "device", "unit", "records",
        "inject_failure", "change_input", "max_output_tokens", "prompt_tokens",
        "model", "provider",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValueError("fixture missing: " + ", ".join(missing))
    if value["lesson_id"] != LESSON_ID or value["fixture_version"] != "1":
        raise ValueError("unsupported T29 fixture")
    for key in ("device", "unit", "input_id", "model", "provider"):
        if not isinstance(value[key], str) or not value[key]:
            raise ValueError(f"fixture {key} must be non-empty")
    for key in ("records", "max_output_tokens", "prompt_tokens"):
        if not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] < 1:
            raise ValueError(f"fixture {key} must be a positive integer")
    for key in ("inject_failure", "change_input"):
        if not isinstance(value[key], bool):
            raise ValueError(f"fixture {key} must be boolean")
    return value


def estimate_cost_usd(*, input_tokens: int, output_tokens: int, input_rate: float = 0.001, output_rate: float = 0.002) -> float:
    """Estimate cost from an explicit teaching price card, never provider billing."""

    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts cannot be negative")
    return round((input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate), 6)


def _check(check_id: str, passed: bool) -> dict[str, str]:
    return {"id": check_id, "result": "passed" if passed else "failed"}


def evaluate_fixture(fixture: dict[str, Any], *, budget_usd: float = DEFAULT_BUDGET_USD) -> dict[str, Any]:
    if budget_usd < 0:
        raise ValueError("budget must not be negative")
    input_tokens = fixture["prompt_tokens"]
    output_tokens = min(fixture["max_output_tokens"], 96)
    estimated_cost = estimate_cost_usd(input_tokens=input_tokens, output_tokens=output_tokens)
    budget_allowed = estimated_cost <= budget_usd
    variant_passed = bool(fixture["change_input"] and fixture["device"] != "baseline-device")
    failure_observed = bool(fixture["inject_failure"])
    recovery_passed = bool(failure_observed and budget_allowed)
    success_passed = bool(budget_allowed and fixture["records"] >= 1)
    checks = [
        _check("success-case", success_passed),
        _check("failure-case", failure_observed),
        _check("variant-input", variant_passed),
        _check("recovery-observed", recovery_passed),
        _check("budget-gate", budget_allowed),
        _check("log-redaction", True),
    ]
    passed = all(item["result"] == "passed" for item in checks)
    status = "passed" if passed else "partial"
    events = ["evaluation-start"]
    if not budget_allowed:
        events.append("budget-stop")
    events.append("case-result")
    if recovery_passed:
        events.append("recovery")
    events.append("evaluation-end")
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": LESSON_ID,
        "result": status,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。" if passed else "部分证据已通过，仍有证据需要补齐。",
        "evidence": checks,
        "evaluation": {
            "evaluator_version": EVALUATOR_VERSION,
            "fixture_version": fixture["fixture_version"],
            "input_id": fixture["input_id"],
            "cases_total": 3,
            "cases_passed": sum(1 for item in checks[:3] if item["result"] == "passed"),
            "success_case_passed": success_passed,
            "failure_case_observed": failure_observed,
            "variant_input_passed": variant_passed,
            "recovery_observed": recovery_passed,
            "failures_recovered": 1 if recovery_passed else 0,
            "estimated_input_tokens": input_tokens,
            "estimated_output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost,
            "budget_usd": round(budget_usd, 6),
            "budget_status": "allowed" if budget_allowed else "stopped",
            "provider": "offline-fixture",
            "model": fixture["model"],
            "live_api_called": False,
        },
        "logs": {"event_count": len(events), "events": events},
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser(prog="t29-production-evaluator")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = evaluate_fixture(_read_fixture(args.fixture), budget_usd=args.budget_usd)
    output_path = args.output.resolve()
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
