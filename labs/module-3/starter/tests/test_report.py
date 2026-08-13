from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from telemetry_report import build_report  # noqa: E402


class TelemetryReportTests(unittest.TestCase):
    def test_normalizes_fahrenheit_and_skips_invalid_rows(self) -> None:
        report = build_report(ROOT / "data" / "readings.csv")
        self.assertEqual(report["schema"], "telemetry-report-v1")
        self.assertEqual(report["valid_count"], 3)
        self.assertEqual(report["unit"], "C")
        self.assertEqual(report["mean_celsius"], 20.333)

    def test_report_has_no_raw_records(self) -> None:
        report = build_report(ROOT / "data" / "readings.csv")
        self.assertNotIn("timestamp", report)
        self.assertNotIn("rows", report)
        encoded = json.dumps(report)
        self.assertNotIn("not-a-timestamp", encoded)


if __name__ == "__main__":
    unittest.main()
