"""Public checker seam tests for the deterministic Plugin audit lesson."""

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


def run_fixture(profile: str, status: str, findings: list[str], components: list[str]) -> dict[str, object]:
    return {
        "id": f"run-{profile}",
        "fixture": profile,
        "status": status,
        "findings": findings,
        "components": components,
        "inspected": [
            "origin",
            "version",
            "license",
            "permissions",
            "network",
            "dependencies",
            "lifecycle",
            "execution",
        ],
        "lifecycle": ["upgrade", "rollback", "uninstall"],
        "offline": True,
        "executed": False,
    }


def passed_fixture() -> dict[str, object]:
    runs = [
        run_fixture("reviewable", "reviewable", [], ["skill", "command", "hook", "mcp"]),
        run_fixture(
            "community-shape",
            "needs-review",
            ["license-unknown", "provenance-unpinned", "dependency-unpinned"],
            ["skill", "command"],
        ),
        run_fixture(
            "needs-review",
            "do-not-install",
            [
                "license-unknown",
                "provenance-unpinned",
                "permission-broad",
                "network-enabled",
                "dependency-unpinned",
                "install-script",
                "lifecycle-gap",
            ],
            ["skill", "command", "hook", "mcp"],
        ),
    ]
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t18-plugin-audit",
        "result": "passed",
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": "所有必需证据均已通过。",
        "evidence": [
            {"id": "manifest-reviewed", "result": "passed"},
            {"id": "component-composition-mapped", "result": "passed"},
            {"id": "supply-chain-fields-audited", "result": "passed"},
            {"id": "unsafe-package-contained", "result": "passed"},
            {"id": "lifecycle-reviewed", "result": "passed"},
            {"id": "offline-no-install", "result": "passed"},
        ],
        "audit": {
            "version": "1",
            "runs": runs,
            "observed_findings": [
                "dependency-unpinned",
                "install-script",
                "license-unknown",
                "lifecycle-gap",
                "network-enabled",
                "permission-broad",
                "provenance-unpinned",
            ],
            "observed_components": ["command", "hook", "mcp", "skill"],
            "observed_fields": [
                "dependencies",
                "execution",
                "license",
                "lifecycle",
                "network",
                "origin",
                "permissions",
                "version",
            ],
            "observed_lifecycle": ["rollback", "uninstall", "upgrade"],
        },
    }


class PluginAuditCheckerTests(unittest.TestCase):
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

    def test_structure_check_is_partial_without_learner_evidence(self) -> None:
        result = self.run_checker(
            "check",
            "t18-plugin-audit",
            "--root",
            str(ROOT),
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(document["lesson_id"], "t18-plugin-audit")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            [
                "plugin-audit-page",
                "plugin-audit-simulator",
                "plugin-audit-contract",
                "plugin-audit-sources",
                "plugin-audit-evidence",
            ],
        )

    def test_checker_rederives_complete_evidence_from_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "t18-plugin-audit-evidence.json"
            fixture.write_text(json.dumps(passed_fixture(), ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t18-plugin-audit",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual(document["audit"]["observed_components"], ["command", "hook", "mcp", "skill"])
        self.assertNotIn("example.invalid", result.stdout)
        self.assertNotIn(str(fixture), result.stdout)

    def test_checker_rejects_execution_or_forged_profile_state(self) -> None:
        fixture = passed_fixture()
        audit = fixture["audit"]
        assert isinstance(audit, dict)
        runs = audit["runs"]
        assert isinstance(runs, list)
        runs[0]["executed"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "executed.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t18-plugin-audit",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(path),
                "--json",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("offline", result.stderr)

    def test_checker_rejects_sensitive_fields_in_audit(self) -> None:
        fixture = passed_fixture()
        audit = fixture["audit"]
        assert isinstance(audit, dict)
        audit["path"] = "C:\\private\\plugin"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sensitive.json"
            path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
            result = self.run_checker(
                "check",
                "t18-plugin-audit",
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
