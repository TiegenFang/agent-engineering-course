"""Public checker seam tests for the deterministic controlled Memory lesson."""

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

STAGE_OBSERVATIONS = {
    "design": ["purpose", "owner", "lifetime", "deletion", "types"],
    "write": ["record_created", "metadata_complete", "sensitive_excluded"],
    "recall": ["context_window", "summary", "retrieval", "injection", "correct_recall"],
    "stale-update": ["stale_detected", "replacement_confirmed", "old_not_retrieved"],
    "pollution": ["untrusted_quarantined", "trusted_boundary_restored", "revalidated"],
    "delete": ["deletion_requested", "deletion_confirmed", "record_absent"],
}
STAGE_IDS = list(STAGE_OBSERVATIONS)
CHECK_IDS = [
    "purpose-defined",
    "owner-defined",
    "lifetime-defined",
    "deletion-defined",
    "memory-types-separated",
    "context-window-managed",
    "summary-retrieval-injection",
    "correct-recall",
    "stale-memory-corrected",
    "pollution-contained",
    "sensitive-excluded",
    "deletion-confirmed",
    "offline-deterministic",
]


def experiment(*, failed_observation: tuple[str, str] | None = None) -> dict[str, object]:
    stages = []
    for sequence, stage_id in enumerate(STAGE_IDS, start=1):
        observations = {
            key: not (failed_observation == (stage_id, key))
            for key in STAGE_OBSERVATIONS[stage_id]
        }
        stages.append(
            {
                "id": stage_id,
                "sequence": sequence,
                "result": "passed" if all(observations.values()) else "failed",
                "observations": observations,
            }
        )
    return {
        "version": "1",
        "baseline_id": "memory-ledger-v1",
        "stages": stages,
        "memory_types": ["short-term", "long-term", "external"],
        "context_modes": ["window-budget", "summary", "retrieval", "injection"],
        "pollution_injected": True,
        "pollution_recovered": True,
        "model_calls": 0,
        "network_calls": 0,
    }


def expected_checks(experiment_value: dict[str, object]) -> list[dict[str, str]]:
    stage_map = {stage["id"]: stage for stage in experiment_value["stages"]}

    def passed(stage_id: str, *keys: str) -> str:
        stage = stage_map[stage_id]
        return "passed" if all(stage["observations"][key] for key in keys) else "failed"

    return [
        {"id": "purpose-defined", "result": passed("design", "purpose")},
        {"id": "owner-defined", "result": passed("design", "owner")},
        {"id": "lifetime-defined", "result": passed("design", "lifetime")},
        {"id": "deletion-defined", "result": passed("design", "deletion")},
        {"id": "memory-types-separated", "result": passed("design", "types")},
        {"id": "context-window-managed", "result": passed("recall", "context_window")},
        {
            "id": "summary-retrieval-injection",
            "result": passed("recall", "summary", "retrieval", "injection"),
        },
        {"id": "correct-recall", "result": passed("recall", "correct_recall")},
        {
            "id": "stale-memory-corrected",
            "result": passed("stale-update", "stale_detected", "replacement_confirmed", "old_not_retrieved"),
        },
        {
            "id": "pollution-contained",
            "result": passed("pollution", "untrusted_quarantined", "trusted_boundary_restored", "revalidated"),
        },
        {"id": "sensitive-excluded", "result": passed("write", "sensitive_excluded")},
        {
            "id": "deletion-confirmed",
            "result": passed("delete", "deletion_requested", "deletion_confirmed", "record_absent"),
        },
        {"id": "offline-deterministic", "result": "passed"},
    ]


def evidence_document(experiment_value: dict[str, object]) -> dict[str, object]:
    checks = expected_checks(experiment_value)
    result = "passed" if all(check["result"] == "passed" for check in checks) else "partial"
    summary = {
        "passed": "所有必需证据均已通过。",
        "partial": "部分证据已通过，仍有证据需要补齐。",
    }[result]
    return {
        "contract": "agent-engineering-course/evidence",
        "contract_version": "1",
        "course_version": COURSE_VERSION,
        "lesson_id": "t16-memory",
        "result": result,
        "anonymous": True,
        "checked_on": "2026-08-13",
        "summary": summary,
        "evidence": checks,
        "experiment": experiment_value,
    }


class MemoryCheckerTests(unittest.TestCase):
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

    def write_fixture(self, value: dict[str, object]) -> Path:
        temporary = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        )
        with temporary:
            json.dump(value, temporary, ensure_ascii=False)
        self.addCleanup(lambda: Path(temporary.name).unlink(missing_ok=True))
        return Path(temporary.name)

    def test_structure_only_result_is_partial(self) -> None:
        result = self.run_checker("check", "t16-memory", "--root", str(ROOT), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["lesson_id"], "t16-memory")
        self.assertEqual(document["result"], "partial")
        self.assertEqual(
            [check["id"] for check in document["evidence"]],
            ["memory-page", "memory-simulator", "memory-contract", "memory-sources", "memory-evidence-executed"],
        )

    def test_complete_journey_derives_anonymous_passed_evidence(self) -> None:
        value = evidence_document(experiment())
        value["source_path"] = "C:\\Users\\Ada\\private-memory.md"
        value["secret"] = "sk-test-only"
        fixture = self.write_fixture(value)
        result = self.run_checker(
            "check",
            "t16-memory",
            "--root",
            str(ROOT),
            "--evidence-file",
            str(fixture),
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "passed")
        self.assertEqual([check["id"] for check in document["evidence"]], CHECK_IDS)
        self.assertNotIn("private-memory", result.stdout)
        self.assertNotIn("sk-test-only", result.stdout)
        self.assertNotIn("source_path", result.stdout)
        self.assertNotIn("stages", document["experiment"])

    def test_partial_journey_is_reported_without_forging_pass(self) -> None:
        value = evidence_document(experiment(failed_observation=("pollution", "revalidated")))
        fixture = self.write_fixture(value)
        result = self.run_checker(
            "check", "t16-memory", "--root", str(ROOT), "--evidence-file", str(fixture), "--json"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["result"], "partial")
        self.assertEqual(
            next(check for check in document["evidence"] if check["id"] == "pollution-contained")["result"],
            "failed",
        )

    def test_inconsistent_check_status_is_rejected(self) -> None:
        value = evidence_document(experiment())
        value["evidence"][0]["result"] = "failed"
        fixture = self.write_fixture(value)
        result = self.run_checker(
            "check", "t16-memory", "--root", str(ROOT), "--evidence-file", str(fixture), "--json"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not match", result.stderr)

    def test_sensitive_experiment_field_is_rejected(self) -> None:
        value = evidence_document(experiment())
        value["experiment"]["raw_content"] = "真实聊天全文"
        fixture = self.write_fixture(value)
        result = self.run_checker(
            "check", "t16-memory", "--root", str(ROOT), "--evidence-file", str(fixture), "--json"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())

    def test_out_of_order_stage_is_rejected(self) -> None:
        value = evidence_document(experiment())
        value["experiment"]["stages"][1]["sequence"] = 3
        fixture = self.write_fixture(value)
        result = self.run_checker(
            "check", "t16-memory", "--root", str(ROOT), "--evidence-file", str(fixture), "--json"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("out of order", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
