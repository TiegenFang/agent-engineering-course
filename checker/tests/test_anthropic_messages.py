"""Contract tests for the T28 offline Anthropic Messages migration lab."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from course_check.anthropic_messages import (
    ANTHROPIC_MESSAGES_LESSON_ID,
    CHECK_IDS,
    EvidenceError,
    load_anthropic_messages_checks,
)


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / "labs" / "anthropic-messages" / "anthropic_messages_adapter.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("t28_anthropic_messages_adapter", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load T28 adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def public_evidence(adapter, *, case_id: str = "offline-success"):
    return adapter.build_offline_evidence(
        case_id=case_id,
        course_version="test-course-version",
        recorded_at="2026-08-13T00:00:00Z",
    )


class AnthropicMessagesContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = load_adapter()

    def _load(self, document):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "evidence.json"
            target.write_text(json.dumps(document), encoding="utf-8")
            return load_anthropic_messages_checks(target, expected_course_version="test-course-version")

    def test_offline_evidence_has_no_credential_or_network_claim(self) -> None:
        evidence = public_evidence(self.adapter)
        serialized = json.dumps(evidence).lower()
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("anthropic_api_key", serialized)

        checks, trace = self._load(evidence)
        self.assertEqual([check["id"] for check in checks], list(CHECK_IDS))
        self.assertTrue(all(check["result"] == "passed" for check in checks))
        self.assertEqual(trace["network"], "not-called")
        self.assertEqual(trace["access"], "not-required")
        self.assertEqual(trace["live_smoke"]["status"], "not-run")
        self.assertEqual(trace["agent_sdk"]["status"], "comparison-only-not-invoked")

    def test_rejects_sensitive_field_and_false_live_claim(self) -> None:
        evidence = public_evidence(self.adapter)
        evidence["experiment"]["api_key"] = "never-record-this"
        with self.assertRaises(EvidenceError):
            self._load(evidence)

        evidence = public_evidence(self.adapter)
        evidence["experiment"]["live_smoke"]["status"] = "passed"
        with self.assertRaises(EvidenceError):
            self._load(evidence)

    def test_fixture_records_message_history_tool_result_and_t26_ownership(self) -> None:
        evidence = public_evidence(self.adapter)
        experiment = evidence["experiment"]
        request = experiment["request"]
        success = next(case for case in experiment["cases"] if case["id"] == "offline-success")
        self.assertEqual(request["tool_schema"], "input_schema")
        self.assertEqual(request["tool_result_reference"], "tool_use_id")
        self.assertEqual(request["structured_output"], "json_schema")
        self.assertEqual(request["max_tokens"], 256)
        self.assertEqual(experiment["state_owner"], "application-message-history")
        self.assertEqual(experiment["loop_budget_owner"], "t26-agent-loop")
        self.assertTrue(success["tool_use"])
        self.assertTrue(success["tool_result_refilled"])
        self.assertTrue(success["history_replayed"])

    def test_fixture_errors_are_safe_categories(self) -> None:
        for case_id, expected in (
            ("invalid-arguments", "invalid-arguments"),
            ("malformed-structured-output", "protocol"),
            ("transport-error", "connection"),
            ("authentication-error", "authentication"),
        ):
            evidence = public_evidence(self.adapter, case_id=case_id)
            observed = next(case for case in evidence["experiment"]["cases"] if case["id"] == case_id)
            self.assertEqual(observed["error"], expected)
            self.assertEqual(observed["network"], "not-called")
            self.assertEqual(observed["access"], "not-required")


if __name__ == "__main__":
    unittest.main()
