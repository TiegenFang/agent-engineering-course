"""Deterministic unit tests for the offline T33 release audit."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("release_audit", ROOT / "scripts" / "release_audit.py")
assert SPEC and SPEC.loader
release_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_audit)


def write_fixture(root: Path, *, secret: bool = False, stale: bool = False) -> None:
    (root / "docs" / "contracts").mkdir(parents=True)
    (root / "docs" / "sources").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "site").mkdir()
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    source = {
        "id": "official-example",
        "title": "Official example",
        "url": "https://example.com/docs",
        "source_role": "official-fact-source",
        "pinned_version": "page observed 2026-08-13",
        "usage": "fact reference only",
        "license_or_terms": "reference-only; no copied assets",
        "copied_assets": False,
    }
    lesson = {
        "id": "t99-fixture",
        "title": "Fixture",
        "stage": "alpha",
        "duration_minutes": 10,
        "prerequisites": [],
        "outcomes": ["test"],
        "artifacts": ["test"],
        "primary_tool": "none",
        "migration_tool": "none",
        "platforms": {"primary": "Windows", "secondary": []},
        "versions": {"client": "none", "sdk": "none", "model": "none", "protocol": "none"},
        "verified_on": "2026-08-13" if not stale else "2025-01-01",
        "access": {"accounts": [], "cost": "free", "network": "none"},
        "risk": {"permissions": "local read", "side_effects": "none", "staleness": "review"},
        "sources": ["official-example"],
        "licenses": ["MIT"],
    }
    (root / "docs" / "sources" / "source-ledger.json").write_text(json.dumps({"sources": [source]}, indent=2), encoding="utf-8")
    (root / "docs" / "contracts" / "content-contract.json").write_text(json.dumps({"lessons": [lesson]}, indent=2), encoding="utf-8")
    (root / "package.json").write_text(json.dumps({"devDependencies": {"fixture": "1.0.0"}}, indent=2), encoding="utf-8")
    (root / "site" / "package.json").write_text(json.dumps({"dependencies": {}}, indent=2), encoding="utf-8")
    (root / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {"": {"devDependencies": {"fixture": "1.0.0"}}, "node_modules/fixture": {"version": "1.0.0"}}}, indent=2), encoding="utf-8")
    (root / ".github" / "workflows" / "ci.yml").write_text("permissions:\n  contents: read\n", encoding="utf-8")
    if secret:
        token = "sk-" + "123456789012345678901234"
        (root / "secret.txt").write_text(f'OPENAI_API_KEY = "{token}"\n', encoding="utf-8")


class ReleaseAuditTests(unittest.TestCase):
    def test_clean_fixture_passes_but_records_offline_link_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root)
            report = release_audit.audit_repository(root, as_of=date(2026, 8, 13))
        self.assertEqual(report["result"], "passed")
        self.assertGreaterEqual(report["summary"]["review"], 1)
        self.assertFalse(report["checks"]["scan_links"]["network_checked"])

    def test_secret_is_failed_without_echoing_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root, secret=True)
            report = release_audit.audit_repository(root, as_of=date(2026, 8, 13))
        self.assertEqual(report["result"], "failed")
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("sk-" + "123456789012345678901234", encoded)
        self.assertTrue(any(item["check"] == "sensitive-data" for item in report["findings"]))

    def test_stale_lesson_fails_90_day_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root, stale=True)
            report = release_audit.audit_repository(root, as_of=date(2026, 8, 13))
        self.assertEqual(report["result"], "failed")
        self.assertTrue(any(item["check"] == "freshness" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
