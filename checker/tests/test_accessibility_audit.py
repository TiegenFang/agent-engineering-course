"""Deterministic unit tests for the offline T32 accessibility audit."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("accessibility_audit", ROOT / "scripts" / "accessibility_audit.py")
assert SPEC and SPEC.loader
accessibility_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(accessibility_audit)


def write_fixture(root: Path, *, missing_focus: bool = False, missing_alt: bool = False) -> None:
    (root / "site" / "src" / "components").mkdir(parents=True)
    (root / "site" / "src" / "pages").mkdir(parents=True)
    styles = "" if missing_focus else ":focus-visible { outline: 3px solid #000; }\n"
    styles += "@media (max-width: 42rem) { .lab { grid-template-columns: 1fr; } }\n"
    styles += "@media (prefers-reduced-motion: reduce) { * { animation-duration: 0.01ms; } }\n"
    styles += ".button { min-height: 44px; }\n"
    (root / "site" / "src" / "styles").mkdir(parents=True)
    (root / "site" / "src" / "styles" / "custom.css").write_text(styles, encoding="utf-8")
    alt = "" if missing_alt else ' alt="fixture illustration"'
    (root / "site" / "src" / "components" / "CourseShell.astro").write_text(
        '<div data-course-shell><header aria-labelledby="course-shell-title"><h1 id="course-shell-title">Fixture</h1></header>'
        '<nav aria-label="课程首页章节导航"><a href="#course-shell-main">Search</a></nav>'
        '<main id="course-shell-main">移动阅读路径 <button type="button" aria-label="Run">Run</button>'
        f'<img{alt} /></main></div>',
        encoding="utf-8",
    )


class AccessibilityAuditTests(unittest.TestCase):
    def test_clean_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root)
            report = accessibility_audit.audit_repository(root)
        self.assertEqual(report["result"], "passed")
        self.assertGreaterEqual(report["summary"]["review"], 1)

    def test_missing_focus_hook_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root, missing_focus=True)
            report = accessibility_audit.audit_repository(root)
        self.assertEqual(report["result"], "failed")
        self.assertTrue(any(item["check"] == "style-hooks" for item in report["findings"]))

    def test_missing_alt_fails_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root, missing_alt=True)
            report = accessibility_audit.audit_repository(root)
        self.assertEqual(report["result"], "failed")
        self.assertTrue(any(item["check"] == "alternative-text" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
