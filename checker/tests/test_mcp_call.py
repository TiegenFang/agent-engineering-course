"""Public checker seam tests for the T20 MCP call lesson."""

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
CHECK_IDS = [
    "transport-connected",
    "discovery-bridge",
    "permission-confirmed",
    "tool-called",
    "side-effect-bounded",
    "fault-observed",
    "fault-recovered",
    "no-sensitive-output",
    "inspector-checked",
    "fallback-explicit",
]


def passed_fixture() -> dict[str, object]:
    checks = [{"id": check_id, "result": "passed"} for check_id in CHECK_IDS]
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t20-mcp-call",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": checks,
        "experiment": {
            "version": "1",
            "mode": "live",
            "formal_mcp": True,
            "protocol": "2026-07-28",
            "transport": "stdio",
            "discovery_source": "t19-tool-catalog-v1",
            "tools_observed": ["report.publish", "telemetry.read"],
            "permission": "confirmed",
            "call_completed": True,
            "side_effect": "bounded-local-write",
            "faults": [{"id": "protocol", "observed": True, "recovered": True}],
            "inspector": "passed",
            "no_sensitive_output": True,
        },
    }


class McpCallCheckerTests(unittest.TestCase):
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

    def test_structure_is_partial_without_real_evidence(self) -> None:
        result = self.run_checker("check", "t20-mcp-call", "--root", str(ROOT), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t20-mcp-call")
        self.assertEqual([check["id"] for check in document["evidence"]], [
            "mcp-call-page",
            "mcp-call-server",
            "mcp-call-client",
            "mcp-call-inspector",
            "mcp-call-contract",
            "mcp-call-evidence",
        ])

    def test_live_fixture_derives_passed_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t20-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t20-mcp-call",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["experiment"]["protocol"], "2026-07-28")
        self.assertTrue(document["anonymous"])
        self.assertNotIn(str(fixture), result.stdout)

    def test_offline_fallback_can_never_pass(self) -> None:
        fixture = passed_fixture()
        fixture["result"] = "passed"
        fixture["summary"] = "所有必需证据均已通过。"
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment.update(
            {
                "mode": "offline-fallback",
                "formal_mcp": False,
                "protocol": "offline-fixture-v1",
                "transport": "not-used",
                "discovery_source": "offline-tool-catalog",
                "tools_observed": ["report.publish", "telemetry.read"],
                "permission": "not-requested",
                "call_completed": False,
                "side_effect": "none",
                "faults": [],
                "inspector": "not-run",
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "offline.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t20-mcp-call", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("offline", result.stderr.lower())

    def test_sensitive_fault_fields_are_rejected(self) -> None:
        fixture = passed_fixture()
        experiment = fixture["experiment"]
        assert isinstance(experiment, dict)
        experiment["token"] = "should-not-cross-seam"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check", "t20-mcp-call", "--root", str(ROOT), "--evidence-file", str(path), "--json"
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
