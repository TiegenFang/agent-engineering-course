from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pressure_report import build_report  # noqa: E402


class PressureReportTests(unittest.TestCase):
    def test_normalizes_pressure_units_and_skips_invalid_rows(self) -> None:
        report = build_report(ROOT / "data" / "readings.csv")
        self.assertEqual(report["schema"], "pressure-report-v1")
        self.assertEqual(report["valid_count"], 3)
        self.assertEqual(report["mean_kpa"], 101.317)
        self.assertEqual(report["peak_kpa"], 101.325)
        self.assertEqual(report["alarm_count"], 2)
        self.assertEqual(report["unit"], "kPa")

    def test_report_has_no_raw_records(self) -> None:
        report = build_report(ROOT / "data" / "readings.csv")
        self.assertNotIn("timestamp", report)
        self.assertNotIn("rows", report)
        self.assertNotIn("not-a-timestamp", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
