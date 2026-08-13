"""Public seams for the module 0 environment-diagnosis journey.

These tests describe what a learner can observe: a PowerShell diagnostic's
public output and an anonymous evidence document that can be imported by the
existing website contract.  The built page contract is checked by the site
test seam, not by reading MDX or PowerShell source files here.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "checker"
CONTENT_CONTRACT = ROOT / "docs" / "contracts" / "content-contract.json"
DIAGNOSTIC_SCRIPT = ROOT / "labs" / "module-0" / "diagnose-environment.ps1"
COURSE_VERSION = json.loads(
    (ROOT / "course-version.json").read_text(encoding="utf-8")
)["course_version"]
ENVIRONMENT_CHECK_IDS = {
    "powershell-7",
    "editor-command",
    "python-on-path",
    "python-version",
    "git-on-path",
    "git-version",
    "github-account",
    "coding-agent-account",
}


class EnvironmentContentTests(unittest.TestCase):
    def test_module_zero_is_a_complete_contract_lesson(self) -> None:
        content = json.loads(CONTENT_CONTRACT.read_text(encoding="utf-8"))
        lesson = next(item for item in content["lessons"] if item["id"] == "t05-environment")

        self.assertEqual(lesson["title"], "模块 0：环境诊断学习旅程")
        self.assertEqual(lesson["platforms"]["primary"], "Windows 11 + PowerShell 7")
        self.assertIn("macOS + zsh", lesson["platforms"]["secondary"])
        self.assertIn("Linux + bash", lesson["platforms"]["secondary"])
        self.assertTrue(lesson["outcomes"])
        self.assertTrue(lesson["artifacts"])
        self.assertIn("GitHub account (manual check)", lesson["access"]["accounts"])
        self.assertIn("one Coding Agent account (manual check)", lesson["access"]["accounts"])

class EnvironmentEvidenceCommandTests(unittest.TestCase):
    def run_diagnostic(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            if os.environ.get("CI", "").lower() == "true":
                self.fail("PowerShell 7 is required in CI; pwsh was not found")
            self.skipTest("PowerShell 7 is unavailable on this runner")
        return subprocess.run(
            [pwsh, "-NoProfile", "-File", str(DIAGNOSTIC_SCRIPT), *args],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    @staticmethod
    def expected_platform() -> str:
        if sys.platform == "win32":
            return "windows"
        if sys.platform == "darwin":
            return "macos"
        return "linux"

    @staticmethod
    def write_failing_command(directory: Path, name: str) -> Path:
        if os.name == "nt":
            path = directory / f"{name}.cmd"
            path.write_text("@echo off\r\nexit /b 1\r\n", encoding="ascii")
        else:
            path = directory / name
            path.write_text("#!/bin/sh\nexit 1\n", encoding="ascii")
            path.chmod(0o755)
        return path

    @staticmethod
    def write_environment_fixture(
        path: Path,
        checks: list[dict[str, str]],
        *,
        include_metadata: bool = True,
    ) -> None:
        value: dict[str, object] = {
            "lesson_id": "t05-environment",
            "checks": checks,
        }
        if include_metadata:
            value["platform"] = "windows"
            value["shell"] = "powershell"
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_diagnostic_failure_is_explicit_and_stays_anonymous(self) -> None:
        result = self.run_diagnostic("-MinimumPythonMajor", "99")

        self.assertEqual(result.returncode, 0, result.stderr)
        diagnostic = json.loads(result.stdout)
        python_check = next(
            check for check in diagnostic["checks"] if check["id"] == "python-version"
        )
        self.assertEqual(python_check["result"], "failed")
        self.assertEqual(set(python_check), {"id", "result"})
        self.assertNotIn("C:\\Users\\", result.stdout)

    def test_missing_commands_are_reported_as_failed_states(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env = os.environ.copy()
            env["PATH"] = temporary
            result = self.run_diagnostic(env=env)

        self.assertEqual(result.returncode, 0, result.stderr)
        diagnostic = json.loads(result.stdout)
        checks = {check["id"]: check["result"] for check in diagnostic["checks"]}
        self.assertEqual(checks["python-on-path"], "failed")
        self.assertEqual(checks["python-version"], "failed")
        self.assertEqual(checks["git-on-path"], "failed")
        self.assertEqual(checks["git-version"], "failed")

    def test_diagnostic_can_rerun_to_the_same_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "environment-diagnostic.json"
            arguments = ("-EditorReady", "-GitHubReady", "-CodingAgent", "codex", "-OutputPath", str(output_path))
            first = self.run_diagnostic(*arguments)
            second = self.run_diagnostic(*arguments)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            diagnostic = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(diagnostic["lesson_id"], "t05-environment")

    def test_git_major_three_is_outside_the_git_two_x_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            if os.name == "nt":
                fake_git = directory / "git.cmd"
                fake_git.write_text(
                    "@echo off\r\necho git version 3.0.0\r\nexit /b 0\r\n",
                    encoding="ascii",
                )
            else:
                fake_git = directory / "git"
                fake_git.write_text(
                    "#!/bin/sh\nprintf '%s\\n' 'git version 3.0.0'\n",
                    encoding="ascii",
                )
                fake_git.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = temporary
            result = self.run_diagnostic(env=env)

        self.assertEqual(result.returncode, 0, result.stderr)
        checks = {check["id"]: check["result"] for check in json.loads(result.stdout)["checks"]}
        self.assertEqual(checks["git-on-path"], "passed")
        self.assertEqual(checks["git-version"], "failed")

    def test_visible_but_unusable_command_is_a_path_or_alias_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.write_failing_command(Path(temporary), "python")
            env = os.environ.copy()
            env["PATH"] = temporary
            result = self.run_diagnostic(env=env)

        self.assertEqual(result.returncode, 0, result.stderr)
        checks = {
            check["id"]: check["result"] for check in json.loads(result.stdout)["checks"]
        }
        self.assertEqual(checks["python-on-path"], "passed")
        self.assertEqual(checks["python-version"], "failed")
        self.assertNotIn("python.cmd", result.stdout)

    def test_power_shell_diagnostic_emits_status_only_fixture(self) -> None:
        result = self.run_diagnostic(
            "-EditorReady", "-GitHubReady", "-CodingAgent", "codex"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        diagnostic = json.loads(result.stdout)
        self.assertEqual(diagnostic["lesson_id"], "t05-environment")
        self.assertEqual(diagnostic["platform"], self.expected_platform())
        self.assertEqual(diagnostic["shell"], "powershell")
        self.assertTrue(diagnostic["checks"])
        self.assertTrue(
            all(set(check) == {"id", "result"} for check in diagnostic["checks"])
        )
        powershell_check = next(
            check for check in diagnostic["checks"] if check["id"] == "powershell-7"
        )
        self.assertEqual(powershell_check["result"], "passed")
        for forbidden in ("C:\\Users\\", "USERNAME", "USERPROFILE", "api_key", "token"):
            self.assertNotIn(forbidden.lower(), result.stdout.lower())

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

    def test_environment_diagnostic_states_become_existing_anonymous_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "environment-diagnostic.json"
            fixture.write_text(
                json.dumps(
                    {
                        "lesson_id": "t05-environment",
                        "platform": "windows",
                        "shell": "powershell",
                        "checks": [
                            {
                                "id": "powershell-7",
                                "result": "passed",
                                "detail": "C:\\Users\\Ada\\private\\pwsh.exe",
                            },
                            {"id": "editor-command", "result": "passed"},
                            {"id": "python-on-path", "result": "passed"},
                            {"id": "python-version", "result": "passed"},
                            {"id": "git-on-path", "result": "passed"},
                            {"id": "git-version", "result": "passed"},
                            {"id": "github-account", "result": "passed"},
                            {"id": "coding-agent-account", "result": "passed"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker(
                "check",
                "t05-environment",
                "--root",
                str(ROOT),
                "--environment-file",
                str(fixture),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["course_version"], COURSE_VERSION)
        self.assertEqual(document["lesson_id"], "t05-environment")
        self.assertEqual(document["result"], "passed")
        self.assertTrue(document["anonymous"])
        self.assertEqual(
            document["evidence"],
            [
                {"id": "powershell-7", "result": "passed"},
                {"id": "editor-command", "result": "passed"},
                {"id": "python-on-path", "result": "passed"},
                {"id": "python-version", "result": "passed"},
                {"id": "git-on-path", "result": "passed"},
                {"id": "git-version", "result": "passed"},
                {"id": "github-account", "result": "passed"},
                {"id": "coding-agent-account", "result": "passed"},
            ],
        )
        self.assertNotIn("C:\\Users\\Ada", result.stdout)

    def test_environment_fixture_rejects_an_unknown_check_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "unknown-check.json"
            self.write_environment_fixture(
                fixture,
                [{"id": "foo", "result": "passed"}],
            )
            result = self.run_checker(
                "check",
                "t05-environment",
                "--root",
                str(ROOT),
                "--environment-file",
                str(fixture),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("check", result.stderr.lower())

    def test_environment_fixture_rejects_incomplete_expected_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "incomplete-checks.json"
            self.write_environment_fixture(
                fixture,
                [{"id": "powershell-7", "result": "passed"}],
            )
            result = self.run_checker(
                "check",
                "t05-environment",
                "--root",
                str(ROOT),
                "--environment-file",
                str(fixture),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checks", result.stderr.lower())

    def test_environment_fixture_requires_platform_and_shell_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "missing-metadata.json"
            self.write_environment_fixture(
                fixture,
                [
                    {"id": check_id, "result": "passed"}
                    for check_id in sorted(ENVIRONMENT_CHECK_IDS)
                ],
                include_metadata=False,
            )
            result = self.run_checker(
                "check",
                "t05-environment",
                "--root",
                str(ROOT),
                "--environment-file",
                str(fixture),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("platform", result.stderr.lower())

    def test_environment_diagnostic_requires_a_fixture_instead_of_claiming_success(self) -> None:
        result = self.run_checker(
            "check",
            "t05-environment",
            "--root",
            str(ROOT),
            "--json",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("environment-file", result.stderr)

    def test_environment_fixture_rejects_a_different_lesson(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "wrong-lesson.json"
            fixture.write_text(
                json.dumps(
                    {
                        "lesson_id": "t01-foundation",
                        "checks": [{"id": "anything", "result": "passed"}],
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker(
                "check",
                "t05-environment",
                "--root",
                str(ROOT),
                "--environment-file",
                str(fixture),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lesson_id", result.stderr)


if __name__ == "__main__":
    unittest.main()
