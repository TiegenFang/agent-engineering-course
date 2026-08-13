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
GIT_SAFETY_STAGE_IDS = (
    "baseline",
    "branch-history",
    "change-created",
    "selective-stage",
    "first-commit-decision",
    "first-commit-recorded",
    "secret-before",
    "secret-ignored",
    "secret-commit-decision",
    "secret-commit-recorded",
    "recovery-before",
    "recovery-recorded",
    "final",
)
GIT_SAFETY_STAGE_OBSERVATIONS = {
    "baseline": ("repo", "clean", "head", "branch", "history"),
    "branch-history": ("branch", "history"),
    "change-created": ("tracked_change", "untracked_change", "diff"),
    "selective-stage": ("staged_change", "unstaged_change", "staged_diff", "diff"),
    "first-commit-decision": ("staged_change", "secret_untracked", "approval"),
    "first-commit-recorded": ("head_changed", "clean"),
    "secret-before": ("secret_absent", "ignore_absent"),
    "secret-ignored": ("secret_present", "ignored", "untracked", "ignore_unstaged"),
    "secret-commit-decision": ("staged_ignore", "secret_untracked", "approval"),
    "secret-commit-recorded": ("head_changed", "clean"),
    "recovery-before": ("tracked_change", "diff"),
    "recovery-recorded": ("clean", "matches_head"),
    "final": ("clean", "secret_untracked"),
}


class GitSafetyJourneyTests(unittest.TestCase):
    @staticmethod
    def write_fixture(
        path: Path,
        checks: list[dict[str, object]],
        *,
        stages: list[dict[str, object]] | None = None,
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
                    "journey": {
                        "trace_version": "1",
                        "trace_id": "fixturetrace",
                        "stages": (
                            stages
                            if stages is not None
                            else GitSafetyJourneyTests.passed_stages()
                        ),
                    },
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

    @staticmethod
    def passed_stages(
        *,
        failed_stages: set[str] | None = None,
    ) -> list[dict[str, object]]:
        failed = failed_stages or set()
        return [
            {
                "id": stage_id,
                "sequence": sequence,
                "result": "failed" if stage_id in failed else "passed",
                "observations": {
                    key: stage_id not in failed
                    for key in GIT_SAFETY_STAGE_OBSERVATIONS[stage_id]
                },
            }
            for sequence, stage_id in enumerate(GIT_SAFETY_STAGE_IDS, start=1)
        ]

    @classmethod
    def checks_for_stages(
        cls,
        *,
        failed_stages: set[str] | None = None,
    ) -> list[dict[str, object]]:
        failed = failed_stages or set()
        passed = lambda *stage_ids: all(stage_id not in failed for stage_id in stage_ids)
        return [
            {"id": "status-baseline", "result": "passed" if passed("baseline") else "failed"},
            {
                "id": "diff-reviewed",
                "result": "passed" if passed("change-created", "selective-stage") else "failed",
            },
            {"id": "selective-stage", "result": "passed" if passed("selective-stage") else "failed"},
            {
                "id": "intentional-commit",
                "result": "passed"
                if passed(
                    "first-commit-decision",
                    "first-commit-recorded",
                    "secret-commit-decision",
                    "secret-commit-recorded",
                )
                else "failed",
            },
            {"id": "branch-inspected", "result": "passed" if passed("branch-history") else "failed"},
            {"id": "history-inspected", "result": "passed" if passed("branch-history") else "failed"},
            {
                "id": "secret-ignored",
                "result": "passed" if passed("secret-before", "secret-ignored") else "failed",
            },
            {
                "id": "recovery-complete",
                "result": "passed"
                if passed("recovery-before", "recovery-recorded", "final")
                else "failed",
            },
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
            "拒绝使用已有的练习目录",
            "-ReadOnlyConfirmed",
            "-AllowOverwrite",
        ):
            self.assertIn(phrase, page)
        self.assertNotIn("New-Item -ItemType Directory -Path $labRoot -Force", page)

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

    def test_final_state_without_a_stage_journey_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "final-only.json"
            fixture.write_text(
                json.dumps(
                    {
                        "lesson_id": "t06-git-safety",
                        "platform": "windows",
                        "shell": "powershell",
                        "checks": self.passed_checks(),
                    }
                ),
                encoding="utf-8",
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

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stage journey", result.stderr.lower())

    def test_partial_stage_journey_is_reported_as_partial(self) -> None:
        failed_stages = {"selective-stage"}
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "partial.json"
            self.write_fixture(
                fixture,
                self.checks_for_stages(failed_stages=failed_stages),
                stages=self.passed_stages(failed_stages=failed_stages),
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
        self.assertEqual(json.loads(result.stdout)["result"], "partial")

    def test_checks_cannot_claim_pass_when_a_stage_failed(self) -> None:
        failed_stages = {"secret-ignored"}
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "forged.json"
            self.write_fixture(
                fixture,
                self.passed_checks(),
                stages=self.passed_stages(failed_stages=failed_stages),
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

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not match", result.stderr.lower())

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

    def test_script_records_the_complete_disposable_journey_when_powershell_is_available(
        self,
    ) -> None:
        pwsh = shutil.which("pwsh")
        git = shutil.which("git")
        if pwsh is None or git is None:
            self.skipTest("PowerShell 7 and Git are required for the script smoke test")

        script = ROOT / "labs" / "module-0" / "git-safety.ps1"
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repo = workspace / "git-safety-practice"
            repo.mkdir()
            artifacts = workspace / "artifacts"
            stages = artifacts / "git-safety-stages"
            stages.mkdir(parents=True)

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
            run_git("add", "README.md")
            run_git("commit", "-m", "baseline")
            def run_stage(stage: str, *, human_approved: bool = False) -> None:
                arguments = [
                    pwsh,
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-RepoPath",
                    str(repo),
                    "-Stage",
                    stage,
                    "-EvidenceDirectory",
                    str(stages),
                    "-ReadOnlyConfirmed",
                ]
                if human_approved:
                    arguments.append("-HumanApproved")
                completed = subprocess.run(
                    arguments,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

            run_stage("baseline")
            run_git("switch", "-c", "lesson/git-safety")
            run_stage("branch-history")
            (repo / "README.md").write_text("practice\nchanged\n", encoding="utf-8")
            (repo / "notes.md").write_text("review later\n", encoding="utf-8")
            run_stage("change-created")
            run_git("add", "README.md")
            run_stage("selective-stage")
            run_stage("first-commit-decision", human_approved=True)
            run_git("commit", "-m", "record README")
            run_git("add", "notes.md")
            run_git("commit", "-m", "record notes")
            run_stage("first-commit-recorded")
            run_stage("secret-before")
            (repo / "secrets").mkdir()
            (repo / "secrets" / "local.env").write_text(
                "DEMO_VALUE_DO_NOT_USE=placeholder\n", encoding="utf-8"
            )
            (repo / ".gitignore").write_text("secrets/\n", encoding="utf-8")
            run_stage("secret-ignored")
            run_git("add", ".gitignore")
            run_stage("secret-commit-decision", human_approved=True)
            run_git("commit", "-m", "ignore local config")
            run_stage("secret-commit-recorded")
            with (repo / "README.md").open("a", encoding="utf-8") as handle:
                handle.write("fault injection\n")
            run_stage("recovery-before")
            run_git("restore", "--", "README.md")
            run_stage("recovery-recorded")

            output = artifacts / "git-safety-diagnostic.json"
            completed = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-RepoPath",
                    str(repo),
                    "-Stage",
                    "final",
                    "-EvidenceDirectory",
                    str(stages),
                    "-ReadOnlyConfirmed",
                    "-OutputPath",
                    str(output),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output_text = output.read_text(encoding="utf-8")
            diagnostic = json.loads(output_text)

            self.assertEqual(diagnostic["lesson_id"], "t06-git-safety")
            self.assertEqual(
                {check["id"] for check in diagnostic["checks"]}, GIT_SAFETY_CHECK_IDS
            )
            self.assertTrue(
                all(check["result"] == "passed" for check in diagnostic["checks"]),
                output_text,
            )
            self.assertEqual(
                [stage["id"] for stage in diagnostic["journey"]["stages"]],
                list(GIT_SAFETY_STAGE_IDS),
            )
            self.assertNotIn("DEMO_VALUE_DO_NOT_USE", output_text)

            repeated = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-RepoPath",
                    str(repo),
                    "-Stage",
                    "final",
                    "-EvidenceDirectory",
                    str(stages),
                    "-ReadOnlyConfirmed",
                    "-OutputPath",
                    str(output),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("already exists", repeated.stderr.lower())

            allowed = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-RepoPath",
                    str(repo),
                    "-Stage",
                    "final",
                    "-EvidenceDirectory",
                    str(stages),
                    "-ReadOnlyConfirmed",
                    "-AllowOverwrite",
                    "-OutputPath",
                    str(output),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

            unsafe_output = workspace / "unsafe.json"
            unsafe = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-RepoPath",
                    str(repo),
                    "-Stage",
                    "final",
                    "-EvidenceDirectory",
                    str(stages),
                    "-ReadOnlyConfirmed",
                    "-OutputPath",
                    str(unsafe_output),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(unsafe.returncode, 0)
            self.assertIn("selected artifacts", unsafe.stderr.lower())

            existing_repo_without_confirmation = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-RepoPath",
                    str(repo),
                    "-Stage",
                    "final",
                    "-EvidenceDirectory",
                    str(stages),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(existing_repo_without_confirmation.returncode, 0)
            self.assertIn("readonlyconfirmed", existing_repo_without_confirmation.stderr.lower())


if __name__ == "__main__":
    unittest.main()
