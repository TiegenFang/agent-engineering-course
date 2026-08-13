"""Anonymous evidence contract for the T28 Anthropic Messages migration lab.

The checker intentionally validates the *observable boundary* of the offline
fixture.  It never asks for an API key, an absolute path, a prompt transcript,
or a real Messages API response.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .evidence import EvidenceError


ANTHROPIC_MESSAGES_LESSON_ID = "t28-anthropic-messages"
ANTHROPIC_MESSAGES_VERSION = "1"
ANTHROPIC_MESSAGES_MODEL = "claude-sonnet-4-5"
ANTHROPIC_MESSAGES_MODE = "offline-fixture"

CASE_ORDER = (
    "offline-success",
    "invalid-arguments",
    "malformed-structured-output",
    "transport-error",
    "authentication-error",
)

CHECK_IDS = (
    "messages-request-shaped",
    "offline-no-credential",
    "tool-use-round-trip",
    "message-history-owned-by-app",
    "structured-output-validated",
    "budget-owned-by-loop",
    "errors-contained",
    "agent-sdk-boundary-recorded",
    "live-smoke-metadata-recorded",
    "live-api-not-claimed",
)

PACKAGE_FILES = (
    "labs/anthropic-messages/anthropic_messages_adapter.py",
    "labs/anthropic-messages/run_fixture.py",
    "labs/anthropic-messages/README.md",
    "site/src/content/docs/module-11-anthropic-messages.mdx",
    "site/src/lib/anthropic-messages.mjs",
    "site/src/components/AnthropicMessagesLab.astro",
    "site/scripts/test-anthropic-messages.mjs",
    "site/scripts/verify-anthropic-messages.mjs",
    "checker/tests/test_anthropic_messages.py",
    "docs/research/t28-anthropic-api-sources.md",
)

_SENSITIVE_TOKENS = ("api_key", "apikey", "token", "secret", "credential", "authorization")
_EXPECTED_CASES: dict[str, dict[str, Any]] = {
    "offline-success": {
        "outcome": "completed",
        "request_count": 2,
        "tool_use": True,
        "tool_result_refilled": True,
        "history_replayed": True,
        "structured_output": "accepted",
        "error": "none",
    },
    "invalid-arguments": {
        "outcome": "invalid-arguments-contained",
        "request_count": 2,
        "tool_use": True,
        "tool_result_refilled": True,
        "history_replayed": True,
        "structured_output": "accepted",
        "error": "invalid-arguments",
    },
    "malformed-structured-output": {
        "outcome": "structured-output-rejected",
        "request_count": 2,
        "tool_use": True,
        "tool_result_refilled": True,
        "history_replayed": True,
        "structured_output": "rejected",
        "error": "protocol",
    },
    "transport-error": {
        "outcome": "transport-error-contained",
        "request_count": 1,
        "tool_use": False,
        "tool_result_refilled": False,
        "history_replayed": False,
        "structured_output": "not-requested",
        "error": "connection",
    },
    "authentication-error": {
        "outcome": "authentication-error-contained",
        "request_count": 1,
        "tool_use": False,
        "tool_result_refilled": False,
        "history_replayed": False,
        "structured_output": "not-requested",
        "error": "authentication",
    },
}


def _error(message: str) -> EvidenceError:
    return EvidenceError(f"{ANTHROPIC_MESSAGES_LESSON_ID}: {message}")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(f"{label} must be an object")
    return value


def _required(mapping: Mapping[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise _error(f"{label}.{key} is required")
    return mapping[key]


def _string(mapping: Mapping[str, Any], key: str, label: str) -> str:
    value = _required(mapping, key, label)
    if not isinstance(value, str) or not value:
        raise _error(f"{label}.{key} must be a non-empty string")
    return value


def _boolean(mapping: Mapping[str, Any], key: str, label: str) -> bool:
    value = _required(mapping, key, label)
    if not isinstance(value, bool):
        raise _error(f"{label}.{key} must be a boolean")
    return value


def _positive_int(mapping: Mapping[str, Any], key: str, label: str) -> int:
    value = _required(mapping, key, label)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _error(f"{label}.{key} must be a positive integer")
    return value


def _reject_sensitive(value: Any, label: str = "evidence") -> None:
    """Reject secrets even when an otherwise-forward-compatible field is used."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower().replace("-", "_")
            # Token *counts/limits* are public aggregate metadata in this
            # lesson; only credential-like token fields are prohibited.
            safe_budget_fields = {"request_max_tokens", "max_tokens"}
            if key_text not in safe_budget_fields and any(
                token in key_text for token in _SENSITIVE_TOKENS
            ):
                raise _error(f"{label}.{key} looks like sensitive data and must not be recorded")
            _reject_sensitive(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{label}[{index}]")


def _require_exact(mapping: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
    for key, value in expected.items():
        observed = _required(mapping, key, label)
        if observed != value:
            raise _error(f"{label}.{key} must be {value!r}, got {observed!r}")


def adapter_package_result(root: Path) -> str:
    missing = [path for path in PACKAGE_FILES if not (root / path).is_file()]
    return "passed" if not missing else f"failed: missing {', '.join(missing)}"


def _validate_request(experiment: Mapping[str, Any]) -> None:
    request = _mapping(_required(experiment, "request", "experiment"), "experiment.request")
    expected = {
        "tool_schema": "input_schema",
        "tool_result_reference": "tool_use_id",
        "structured_output": "json_schema",
        "max_tokens": 256,
    }
    _require_exact(request, expected, "experiment.request")


def _validate_agent_sdk(experiment: Mapping[str, Any]) -> None:
    sdk = _mapping(_required(experiment, "agent_sdk", "experiment"), "experiment.agent_sdk")
    _require_exact(
        sdk,
        {
            "surface": "Claude Agent SDK",
            "status": "comparison-only-not-invoked",
            "messages_api_state": "application-replays-message-history",
            "t26_loop_state": "harness-owned",
            "sdk_runtime": "verify-current-session-permission-and-tool-behavior-before-use",
            "budget": "do-not-infer-a-shared-budget-from-this-fixture",
        },
        "experiment.agent_sdk",
    )


def _validate_live_smoke(experiment: Mapping[str, Any]) -> None:
    smoke = _mapping(_required(experiment, "live_smoke", "experiment"), "experiment.live_smoke")
    _require_exact(
        smoke,
        {
            "status": "not-run",
            "sdk": "anthropic-python-not-imported",
            "model": ANTHROPIC_MESSAGES_MODEL,
            "verified_on": "not-run",
            "cost": "not-incurred",
            "limitations": "offline fixture only; no credential and no network call",
        },
        "experiment.live_smoke",
    )


def validate_anthropic_messages_experiment(experiment_value: Any) -> dict[str, Any]:
    experiment = _mapping(experiment_value, "experiment")
    _reject_sensitive(experiment)

    _require_exact(
        experiment,
        {
            "version": ANTHROPIC_MESSAGES_VERSION,
            "mode": ANTHROPIC_MESSAGES_MODE,
            "adapter": "anthropic-messages-response-source",
            "model": ANTHROPIC_MESSAGES_MODEL,
            "network": "not-called",
            "access": "not-required",
            "request_max_tokens": 256,
            "loop_budget_owner": "t26-agent-loop",
            "state_owner": "application-message-history",
        },
        "experiment",
    )
    _validate_request(experiment)
    _validate_agent_sdk(experiment)
    _validate_live_smoke(experiment)

    raw_cases = _required(experiment, "cases", "experiment")
    if not isinstance(raw_cases, list) or len(raw_cases) != len(CASE_ORDER):
        raise _error("experiment.cases must contain the five ordered offline cases")

    public_cases: list[dict[str, Any]] = []
    for index, expected_id in enumerate(CASE_ORDER):
        case = _mapping(raw_cases[index], f"experiment.cases[{index}]")
        label = f"experiment.cases[{index}]"
        if _string(case, "id", label) != expected_id:
            raise _error(f"{label}.id must be {expected_id!r}")
        _require_exact(case, _EXPECTED_CASES[expected_id], label)
        if _string(case, "network", label) != "not-called":
            raise _error(f"{label}.network must be 'not-called'")
        if _string(case, "access", label) != "not-required":
            raise _error(f"{label}.access must be 'not-required'")
        _positive_int(case, "request_count", label)
        _boolean(case, "tool_use", label)
        _boolean(case, "tool_result_refilled", label)
        _boolean(case, "history_replayed", label)
        public_cases.append({key: case[key] for key in (
            "id",
            "outcome",
            "request_count",
            "tool_use",
            "tool_result_refilled",
            "history_replayed",
            "structured_output",
            "error",
            "network",
            "access",
        )})

    return {
        "mode": experiment["mode"],
        "model": experiment["model"],
        "network": experiment["network"],
        "access": experiment["access"],
        "request_max_tokens": experiment["request_max_tokens"],
        "loop_budget_owner": experiment["loop_budget_owner"],
        "state_owner": experiment["state_owner"],
        "cases": public_cases,
        "agent_sdk": dict(_mapping(experiment["agent_sdk"], "experiment.agent_sdk")),
        "live_smoke": dict(_mapping(experiment["live_smoke"], "experiment.live_smoke")),
    }


def _derived_checks(experiment: Mapping[str, Any]) -> list[dict[str, str]]:
    cases = {case["id"]: case for case in experiment["cases"]}
    success = cases["offline-success"]
    invalid = cases["invalid-arguments"]
    malformed = cases["malformed-structured-output"]
    transport = cases["transport-error"]
    authentication = cases["authentication-error"]
    checks = {
        "messages-request-shaped": experiment["request_max_tokens"] == 256,
        "offline-no-credential": experiment["network"] == "not-called" and experiment["access"] == "not-required",
        "tool-use-round-trip": success["tool_use"] and success["tool_result_refilled"],
        "message-history-owned-by-app": success["history_replayed"] and experiment["state_owner"] == "application-message-history",
        "structured-output-validated": success["structured_output"] == "accepted" and malformed["structured_output"] == "rejected",
        "budget-owned-by-loop": experiment["loop_budget_owner"] == "t26-agent-loop",
        "errors-contained": invalid["error"] == "invalid-arguments" and transport["error"] == "connection" and authentication["error"] == "authentication",
        "agent-sdk-boundary-recorded": experiment["agent_sdk"]["status"] == "comparison-only-not-invoked",
        "live-smoke-metadata-recorded": experiment["live_smoke"]["status"] == "not-run",
        "live-api-not-claimed": experiment["live_smoke"]["status"] != "passed",
    }
    return [{"id": check_id, "result": "passed" if checks[check_id] else "failed"} for check_id in CHECK_IDS]


def load_anthropic_messages_checks(evidence_file: Path, *, expected_course_version: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    try:
        document = json.loads(evidence_file.read_text(encoding="utf-8"))
    except OSError as exc:
        raise _error(f"could not read evidence: {exc.__class__.__name__}") from exc
    except json.JSONDecodeError as exc:
        raise _error("evidence is not valid JSON") from exc

    root = _mapping(document, "evidence")
    _reject_sensitive(root)
    if _string(root, "lesson_id", "evidence") != ANTHROPIC_MESSAGES_LESSON_ID:
        raise _error("evidence.lesson_id does not match this lab")
    if _string(root, "course_version", "evidence") != expected_course_version:
        raise _error("evidence.course_version does not match the locked course version")
    _string(root, "recorded_at", "evidence")
    experiment = validate_anthropic_messages_experiment(_required(root, "experiment", "evidence"))
    return _derived_checks(experiment), experiment
