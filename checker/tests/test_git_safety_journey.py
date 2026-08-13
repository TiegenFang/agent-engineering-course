"""End-to-end tests for the module 0 Git safety evidence seam."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "checker"
LESSON_PAGE = ROOT / "site" / "src" / "content" / "docs" / "module-0-git-safety.mdx"
CONTENT_CONTRACT = ROOT / "docs" / "contracts" / "content-contract.json"
GIT_SAFETY_CHECK_IDS = {
    "status-baseline",
    "diff-reviewed",
    "selective-stage",
    "intentional-commit",
    "branch-inspected",
    "history-inspected",
    "secret-ignored",
    "recovery-complete",
}


class GitSafetyJourneyTests(unittest.TestCase):
    @staticmethod
    def write_fixture(
        path: Path,
        checks: list[dict[str, object]],
        *,
        lesson_id: str = "t06-git-safety",
        platform: str = "windows",
        shell: str = "powershell",
    ) -> None:
        path.write_text(
            json.dumps(
                {
                    "lesson_id": lesson_id,
                    "platform": platform,
                    "shell": shell,
                    "checks": checks,
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def passed_checks() -> list[dict[str, object]]:
        return [
            {"id": check_id, "result": "passed"}
            for check_id in sorted(GIT_SAFETY_CHECK_IDS)
        ]

    def run_checker(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(CHECKER)
        return subprocess.run(
            [sys.executable, "-m", "course_check", *args],
            cwd=CHECKER,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_content_contract_and_page_cover_the_git_safety_journey(self) -> None:
        content = json.loads(CONTENT_CONTRACT.read_text(encoding="utf-8"))
        lesson = next(item for item in content["lessons"] if item["id"] == "t06-git-safety")
        self.assertEqual(lesson["prerequisites"], ["t05-environment"])
        self.assertGreaterEqual(len(lesson["outcomes"]), 3)
        self.assertGreaterEqual(len(lesson["artifacts"]), 3)
        self.assertIn("git-check-ignore", lesson["sources"])
        self.assertIn("git-restore", lesson["sources"])

        page = LESSON_PAGE.read_text(encoding="utf-8")
        for phrase in (
            "真实问题",
            "心智模型",
            "操作前预测",
            "主工具演示",
            "本地实验",
            "故障注入与恢复",
            "迁移挑战",
            "可核验成果",
            "风险、版本与来源卡片",
            "git status",
            "git diff",
            "git add",
            "git commit",
            "git branch",
            "git log",
            "git check-ignore",
            "git restore",
            "DEMO_VALUE_DO_NOT_USE",
        ):
            self.assertIn(phrase, page)

    def test_passed_fixture_becomes_anonymous_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "git-safety-diagnostic.json"
            self.write_fixture(
                fixture,
                [
                    {
                        "id": check["id"],
                        "result": check["result"],
                        "detail": "C:\\Users\\Ada\\practice-repo",
                    }
                    for check in self.passed_checks()
                ],
            )
            result = self.run_checker(
                "check",
                "t06-git-safety",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["lesson_id"], "t06-git-safety")
        self.assertEqual(document["result"], "passed")
        self.assertTrue(document["anonymous"])
        self.assertEqual(
            {check["id"] for check in document["evidence"]}, GIT_SAFETY_CHECK_IDS
        )
        self.assertNotIn("C:\\Users\\Ada", result.stdout)
        self.assertNotIn("detail", result.stdout)

    def test_fixture_requires_every_fixed_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "incomplete.json"
            self.write_fixture(fixture, self.passed_checks()[:-1])
            result = self.run_checker(
                "check",
                "t06-git-safety",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(fixture),
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete", result.stderr.lower())

    def test_fixture_rejects_wrong_shell_and_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            wrong_shell = Path(temporary) / "wrong-shell.json"
            self.write_fixture(
                wrong_shell,
                self.passed_checks(),
                platform="windows",
                shell="bash",
            )
            wrong_shell_result = self.run_checker(
                "check",
                "t06-git-safety",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(wrong_shell),
                "--json",
            )

            sensitive = Path(temporary) / "sensitive.json"
            checks = self.passed_checks()
            checks[0]["secret"] = "DEMO_VALUE_DO_NOT_USE"
            self.write_fixture(sensitive, checks)
            sensitive_result = self.run_checker(
                "check",
                "t06-git-safety",
                "--root",
                str(ROOT),
                "--evidence-file",
                str(sensitive),
                "--json",
            )

        self.assertNotEqual(wrong_shell_result.returncode, 0)
        self.assertIn("shell", wrong_shell_result.stderr.lower())
        self.assertNotEqual(sensitive_result.returncode, 0)
        self.assertIn("sensitive", sensitive_result.stderr.lower())

    def test_script_can_verify_a_clean_disposable_repo_when_powershell_is_available(
        self,
    ) -> None:
        pwsh = shutil.which("pwsh")
        git = shutil.which("git")
        if pwsh is None or git is None:
            self.skipTest("PowerShell 7 and Git are required for the script smoke test")

        script = ROOT / "labs" / "module-0" / "git-safety.ps1"
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "practice"
            repo.mkdir()

            def run_git(*args: str) -> None:
                completed = subprocess.run(
                    [git, "-C", str(repo), *args],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

            run_git("init")
            run_git("config", "user.name", "Course Practice")
            run_git("config", "user.email", "learner@example.invalid")
            (repo / "README.md").write_text("practice\n", encoding="utf-8")
            (repo / ".gitignore").write_text("secrets/\n", encoding="utf-8")
            (repo / "secrets").mkdir()
            (repo / "secrets" / "local.env").write_text(
                "DEMO_VALUE_DO_NOT_USE=placeholder\n", encoding="utf-8"
            )
            run_git("add", "README.md", ".gitignore")
            run_git("commit", "-m", "baseline")
            run_git("switch", "-c", "lesson/git-safety")

            output = Path(temporary) / "diagnostic.json"
            completed = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-RepoPath",
                    str(repo),
                    "-OutputPath",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output_text = output.read_text(encoding="utf-8")
            diagnostic = json.loads(output_text)

        self.assertEqual(diagnostic["lesson_id"], "t06-git-safety")
        self.assertEqual(
            {check["id"] for check in diagnostic["checks"]}, GIT_SAFETY_CHECK_IDS
        )
        self.assertTrue(all(check["result"] == "passed" for check in diagnostic["checks"]))
        self.assertNotIn("DEMO_VALUE_DO_NOT_USE", output_text)


if __name__ == "__main__":
    unittest.main()
