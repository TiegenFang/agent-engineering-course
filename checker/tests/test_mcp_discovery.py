"""Public checker tests for the real MCP discovery lesson."""

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


def formal_fixture() -> dict[str, object]:
    return {
        "fixture_version": "1",
        "lesson_id": "t19-mcp-discovery",
        "mode": "real-stdio",
        "transport": "stdio",
        "protocol_version": "2026-07-28",
        "server": {"name": "t19-discovery-server", "version": "1.0.0"},
        "capabilities": {
            "tools": ["summarize_telemetry"],
            "resources": ["telemetry://demo/snapshot"],
            "prompts": ["review-telemetry"],
        },
        "observations": {
            "server_connected": True,
            "tools_listed": True,
            "resources_listed": True,
            "prompts_listed": True,
            "tool_called": True,
            "resource_read": True,
            "prompt_retrieved": True,
            "failure_recovered": True,
        },
        "inspector": {
            "verified": True,
            "methods": ["tools/list", "resources/list", "prompts/list"],
        },
    }


def fallback_fixture() -> dict[str, object]:
    value = formal_fixture()
    value.update(
        {
            "mode": "offline-fallback",
            "transport": "deterministic-in-memory",
            "protocol_version": "conceptual-only",
            "inspector": {"verified": False, "methods": []},
        }
    )
    return value


class McpDiscoveryCheckerTests(unittest.TestCase):
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

    def write_fixture(self, directory: str, value: dict[str, object]) -> Path:
        path = Path(directory) / "mcp.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_structure_check_is_partial_without_live_evidence(self) -> None:
        result = self.run_checker(
            "check", "t19-mcp-discovery", "--root", str(ROOT), "--json"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "mcp-page",
                "mcp-server-client",
                "mcp-inspector-script",
                "mcp-offline-fallback",
                "mcp-evidence-executed",
            ],
        )

    def test_checker_derives_formal_pass_from_real_fixture_and_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.write_fixture(temporary, formal_fixture())
            output = Path(temporary) / "checked.json"
            result = self.run_checker(
                "check",
                "t19-mcp-discovery",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--output",
                str(output),
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(result.stdout)
            self.assertEqual(document["result"], "passed")
            self.assertEqual(document["mcp"]["inspector"]["verified"], True)
            self.assertEqual(
                document["mcp"]["inspector"]["methods"],
                ["prompts/list", "resources/list", "tools/list"],
            )
            self.assertNotIn(str(ROOT), output.read_text(encoding="utf-8"))

            round_trip = self.run_checker(
                "check",
                "t19-mcp-discovery",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(output),
                "--json",
            )
            self.assertEqual(round_trip.returncode, 0, round_trip.stderr)
            self.assertEqual(json.loads(round_trip.stdout)["result"], "passed")

    def test_offline_fixture_is_explicitly_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.write_fixture(temporary, fallback_fixture())
            result = self.run_checker(
                "check",
                "t19-mcp-discovery",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["evidence"][0], {"id": "offline-deterministic", "result": "passed"})
        self.assertEqual(document["mcp"]["mode"], "offline-fallback")

    def test_checker_rejects_a_forged_passed_contract(self) -> None:
        fixture = formal_fixture()
        fixture["mode"] = "offline-fallback"
        fixture["transport"] = "deterministic-in-memory"
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_fixture(
                temporary,
                {
                    "contract": "agent-engineering-course/evidence",
                    "contract_version": "1",
                    "course_version": COURSE_VERSION,
                    "lesson_id": "t19-mcp-discovery",
                    "result": "passed",
                    "anonymous": True,
                    "checked_on": "2026-08-13",
                    "summary": "所有必需证据均已通过。",
                    "evidence": [
                        {"id": check_id, "result": "passed"}
                        for check_id in [
                            "real-transport",
                            "server-connected",
                            "tools-discovered",
                            "resources-discovered",
                            "prompts-discovered",
                            "tool-call-observed",
                            "resource-read-observed",
                            "prompt-retrieval-observed",
                            "failure-recovered",
                            "inspector-verified",
                        ]
                    ],
                    "mcp": fixture,
                },
            )
            result = self.run_checker(
                "check",
                "t19-mcp-discovery",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MCP", result.stderr)

    def test_checker_rejects_sensitive_paths(self) -> None:
        fixture = formal_fixture()
        fixture["server"] = {"name": "t19-discovery-server", "version": "1.0.0", "path": "C:\\private"}
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_fixture(temporary, fixture)
            result = self.run_checker(
                "check",
                "t19-mcp-discovery",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr)


if __name__ == "__main__":
    unittest.main()
