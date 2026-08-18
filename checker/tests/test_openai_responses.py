"""T27 Responses adapter contract tests; all paths stay offline."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from course_check.__main__ import check_lesson
from course_check.evidence import EvidenceError
from course_check.openai_responses import load_openai_responses_checks


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / "labs" / "openai-responses" / "openai_responses_adapter.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("t27_openai_responses_adapter", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the T27 adapter module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ADAPTER = load_adapter()


class OpenAIResponsesAdapterTests(unittest.TestCase):
    def test_offline_source_shapes_two_responses_and_refills_call_id(self) -> None:
        client = ADAPTER.OfflineResponsesClient(
            [
                ADAPTER._function_call(),
                ADAPTER._final_output(ADAPTER._valid_output()),
            ]
        )
        source = ADAPTER.ResponsesResponseSource(client)
        state = {"tool_results": [], "tool_attempts": 0, "retry_count": 0, "retry_budget": 1}

        first = source.respond(state)
        self.assertEqual(first.kind, "tool_call")
        self.assertEqual(first.tool_name, "read_telemetry")
        self.assertEqual(source.last_request_summary["structured_output"], "json_schema")
        self.assertEqual(source.last_request_summary["max_output_tokens"], 256)
        self.assertFalse(source.last_request_summary["store"])
        self.assertEqual(client.requests[0]["tools"][0]["type"], "function")
        self.assertTrue(client.requests[0]["tools"][0]["strict"])

        state["tool_results"].append({"status": "ok", "value": 42, "unit": "degC"})
        state["tool_attempts"] = 1
        final = source.respond(state)
        self.assertEqual(final.kind, "final")
        self.assertEqual(final.output["status"], "completed")
        self.assertEqual(source.request_count, 2)
        refill = client.requests[1]["input"][-1]
        self.assertEqual(refill["type"], "function_call_output")
        self.assertEqual(refill["call_id"], "call_offline_1")
        self.assertNotIn("OPENAI_API_KEY", json.dumps(source.last_request_summary))

    def test_offline_path_needs_no_key_sdk_or_network(self) -> None:
        self.assertEqual(ADAPTER.credential_status({}), "missing")
        self.assertEqual(ADAPTER.credential_status({"OPENAI_API_KEY": "present-only"}), "present")
        with self.assertRaises(ADAPTER.MissingCredentialError):
            ADAPTER.create_live_openai_client(None)
        document = ADAPTER.build_offline_evidence(checked_on="2026-08-13")
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["experiment"]["network"], "not-called")
        self.assertEqual(document["experiment"]["access"], "not-required")
        self.assertEqual(document["experiment"]["live_smoke"]["status"], "not-run")
        self.assertNotIn("present-only", json.dumps(document))

    def test_adapter_binds_only_the_documented_t26_injection_seam(self) -> None:
        client = ADAPTER.OfflineResponsesClient([ADAPTER._function_call()])
        observed = {}

        def fake_t26_loop(scenario, **kwargs):
            observed["scenario"] = scenario
            observed.update(kwargs)
            return {"outcome": "injected"}

        result = ADAPTER.run_t26_with_responses_source(
            fake_t26_loop,
            tool_executor=object(),
            client=client,
            max_steps=3,
            retry_budget=1,
        )
        self.assertEqual(result, {"outcome": "injected"})
        self.assertEqual(observed["scenario"], "success")
        self.assertIn("response_source", observed)
        self.assertIn("tool_executor", observed)
        self.assertEqual(observed["max_steps"], 3)

    def test_checker_rederives_offline_fixture_and_rejects_sensitive_additions(self) -> None:
        fixture = ADAPTER.build_offline_evidence(checked_on="2026-08-13")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "t27-fixture.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            checks, experiment = load_openai_responses_checks(
                path, expected_course_version="3.0.0"
            )
            self.assertTrue(all(check["result"] == "passed" for check in checks))
            self.assertEqual(experiment["live_smoke"]["status"], "not-run")
            checked = check_lesson(ROOT, "t27-openai-responses", evidence_file=path)
            self.assertEqual(checked["result"], "passed")
            self.assertEqual(checked["experiment"]["network"], "not-called")

            invalid = dict(fixture)
            invalid["api_key"] = "not-a-real-key"
            path.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(EvidenceError):
                load_openai_responses_checks(path, expected_course_version="3.0.0")

            invalid = ADAPTER.build_offline_evidence(checked_on="2026-08-13")
            invalid["experiment"]["cases"][0]["access"] = "present"
            path.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(EvidenceError):
                load_openai_responses_checks(path, expected_course_version="3.0.0")


if __name__ == "__main__":
    unittest.main()
