"""
FireTrace Pilot Pipeline - Full Integration & Validation Test Suite
Tests:
- Datetime UTC validation across formats (ISO-8601, timezone offsets, naive)
- Coordinate validation, geographic bounding, NaN/Inf rejection
- Ground pixel dimensions (scan/track) float preservation
- FRP validation and nullable handling
- Confidence parsing and strict separation (MODIS 0-100 vs VIIRS l/n/h)
- Sensor identification at record level
- Quarantine isolation for fatal defects with traceable diagnostic logs
- Record reconciliation (processed == valid + quarantined)
- Manifest generation and audit report checks
- End-to-end ingestion and report generation on real Palisades test data
"""

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_data import (
    compute_dataset_spatial_bounds,
    validate_coordinates,
    validate_datetime_utc,
    validate_frp,
    validate_pixel_dimensions,
    validate_raw_record,
    validate_timestamp,
)
from scripts.ingest_data import (
    identify_record_sensor,
    ingest_firms_csv,
    parse_confidence_fields,
)
from scripts.generate_report import (
    generate_quality_report,
    verify_scientific_checklist,
)


class TestValidationModule(unittest.TestCase):
    """Unit tests for validation functions."""

    def test_validate_datetime_utc_formats(self):
        # Explicit offset with space
        valid, ts, err = validate_datetime_utc("2005-09-29 09:10:00+00:00")
        self.assertTrue(valid)
        self.assertEqual(ts, "2005-09-29T09:10:00Z")
        self.assertIsNone(err)

        # Explicit offset with T and Z
        valid, ts, err = validate_datetime_utc("2025-01-08T18:30:00Z")
        self.assertTrue(valid)
        self.assertEqual(ts, "2025-01-08T18:30:00Z")

        # Non-zero UTC offset normalized to UTC
        valid, ts, err = validate_datetime_utc("2025-01-08T10:30:00-08:00")
        self.assertTrue(valid)
        self.assertEqual(ts, "2025-01-08T18:30:00Z")

        # Naive datetime normalized to UTC
        valid, ts, err = validate_datetime_utc("2025-01-08 18:30:00")
        self.assertTrue(valid)
        self.assertEqual(ts, "2025-01-08T18:30:00Z")

        # Invalid datetime strings
        valid, ts, err = validate_datetime_utc("")
        self.assertFalse(valid)
        self.assertIn("Missing", err)

        valid, ts, err = validate_datetime_utc("not-a-date")
        self.assertFalse(valid)
        self.assertIn("Invalid ISO-8601", err)

    def test_validate_coordinates(self):
        # Valid coords
        valid, lat, lng, err = validate_coordinates("34.1938", "-118.7358")
        self.assertTrue(valid)
        self.assertAlmostEqual(lat, 34.1938)
        self.assertAlmostEqual(lng, -118.7358)

        # Out of bounds
        valid, _, _, err = validate_coordinates("95.0", "-118.0")
        self.assertFalse(valid)
        self.assertIn("out of valid geographic range", err)

        valid, _, _, err = validate_coordinates("34.0", "190.0")
        self.assertFalse(valid)
        self.assertIn("out of valid geographic range", err)

        # NaN and Inf rejection
        valid, _, _, err = validate_coordinates("nan", "-118.0")
        self.assertFalse(valid)
        self.assertIn("NaN or Infinity", err)

        valid, _, _, err = validate_coordinates("34.0", "inf")
        self.assertFalse(valid)
        self.assertIn("NaN or Infinity", err)

    def test_validate_pixel_dimensions(self):
        # Valid dimensions
        valid, s, t, err, avail = validate_pixel_dimensions("0.49", "0.39")
        self.assertTrue(valid)
        self.assertTrue(avail)
        self.assertEqual(s, 0.49)
        self.assertEqual(t, 0.39)

        # Zero or negative
        valid, _, _, err, _ = validate_pixel_dimensions("0.0", "1.0")
        self.assertFalse(valid)
        self.assertIn("Non-positive", err)

        valid, _, _, err, _ = validate_pixel_dimensions("1.0", "-0.5")
        self.assertFalse(valid)
        self.assertIn("Non-positive", err)

        # Missing dimensions (non-fatal warning per NASA spec)
        valid, s, t, err, avail = validate_pixel_dimensions("", "")
        self.assertTrue(valid)
        self.assertFalse(avail)
        self.assertIsNone(s)
        self.assertIsNone(t)

    def test_validate_frp(self):
        # Valid FRP
        valid, frp, err = validate_frp("343.0")
        self.assertTrue(valid)
        self.assertEqual(frp, 343.0)

        # Zero FRP is valid
        valid, frp, err = validate_frp("0.0")
        self.assertTrue(valid)
        self.assertEqual(frp, 0.0)

        # Negative FRP is fatal
        valid, frp, err = validate_frp("-5.0")
        self.assertFalse(valid)
        self.assertIn("Negative FRP", err)

        # NaN FRP is fatal
        valid, frp, err = validate_frp("nan")
        self.assertFalse(valid)
        self.assertIn("NaN or Infinity", err)

        # Missing FRP is allowed (nullable)
        valid, frp, err = validate_frp("")
        self.assertTrue(valid)
        self.assertIsNone(frp)


class TestConfidenceParsing(unittest.TestCase):
    """Unit tests for sensor confidence parsing and strict isolation."""

    def test_modis_confidence(self):
        # Valid integer percentage
        raw, mod_c, vii_c, issues = parse_confidence_fields("100", "MODIS")
        self.assertEqual(raw, "100")
        self.assertEqual(mod_c, 100)
        self.assertIsNone(vii_c)
        self.assertEqual(len(issues), 0)

        # Non-integer rejected (no rounding allowed)
        raw, mod_c, vii_c, issues = parse_confidence_fields("85.5", "MODIS")
        self.assertIsNone(mod_c)
        self.assertTrue(any("Fractional" in i for i in issues))

        # Out of range [0, 100]
        raw, mod_c, vii_c, issues = parse_confidence_fields("105", "MODIS")
        self.assertIsNone(mod_c)
        self.assertTrue(any("outside valid range" in i for i in issues))

    def test_viirs_confidence(self):
        # Valid categories
        for cat in ("l", "n", "h"):
            raw, mod_c, vii_c, issues = parse_confidence_fields(cat, "VIIRS")
            self.assertEqual(raw, cat)
            self.assertIsNone(mod_c)
            self.assertEqual(vii_c, cat)
            self.assertEqual(len(issues), 0)

        # Full word categories normalized with warning
        raw, mod_c, vii_c, issues = parse_confidence_fields("nominal", "VIIRS")
        self.assertEqual(raw, "nominal")
        self.assertIsNone(mod_c)
        self.assertEqual(vii_c, "n")
        self.assertTrue(any("normalized" in i for i in issues))

        # Invalid category
        raw, mod_c, vii_c, issues = parse_confidence_fields("extreme", "VIIRS")
        self.assertIsNone(vii_c)
        self.assertTrue(any("Unexpected VIIRS confidence" in i for i in issues))


class TestIngestionAndQuarantine(unittest.TestCase):
    """Tests ingestion, quarantine routing, and reconciliation."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.processed_dir = self.test_dir / "processed"
        self.quarantine_dir = self.test_dir / "quarantine"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_quarantine_fatal_records(self):
        # Create CSV with 2 valid and 3 corrupt records
        csv_path = self.test_dir / "mixed_records.csv"
        fieldnames = [
            "region", "sensor", "satellite", "datetime_utc", "latitude",
            "longitude", "confidence", "frp", "daynight", "scan", "track",
            "instrument", "brightness", "bright_t31", "bright_ti4", "bright_ti5",
        ]
        records = [
            # 1. Valid MODIS record
            {
                "region": "palisades_la", "sensor": "MODIS", "satellite": "Aqua",
                "datetime_utc": "2025-01-08 18:30:00+00:00", "latitude": "34.05",
                "longitude": "-118.55", "confidence": "85", "frp": "45.0",
                "daynight": "D", "scan": "1.2", "track": "1.1", "instrument": "MODIS",
                "brightness": "320.0", "bright_t31": "295.0", "bright_ti4": "", "bright_ti5": "",
            },
            # 2. Corrupt record: Latitude out of range
            {
                "region": "palisades_la", "sensor": "MODIS", "satellite": "Aqua",
                "datetime_utc": "2025-01-08 18:30:00+00:00", "latitude": "99.0",
                "longitude": "-118.55", "confidence": "85", "frp": "45.0",
                "daynight": "D", "scan": "1.2", "track": "1.1", "instrument": "MODIS",
                "brightness": "320.0", "bright_t31": "295.0", "bright_ti4": "", "bright_ti5": "",
            },
            # 3. Corrupt record: Malformed datetime
            {
                "region": "palisades_la", "sensor": "VIIRS", "satellite": "N",
                "datetime_utc": "invalid-datetime", "latitude": "34.05",
                "longitude": "-118.55", "confidence": "n", "frp": "2.0",
                "daynight": "N", "scan": "0.4", "track": "0.4", "instrument": "VIIRS",
                "brightness": "", "bright_t31": "", "bright_ti4": "300.0", "bright_ti5": "280.0",
            },
            # 4. Corrupt record: Negative FRP
            {
                "region": "palisades_la", "sensor": "VIIRS", "satellite": "N",
                "datetime_utc": "2025-01-08 18:30:00+00:00", "latitude": "34.05",
                "longitude": "-118.55", "confidence": "h", "frp": "-10.0",
                "daynight": "N", "scan": "0.4", "track": "0.4", "instrument": "VIIRS",
                "brightness": "", "bright_t31": "", "bright_ti4": "300.0", "bright_ti5": "280.0",
            },
            # 5. Valid VIIRS record
            {
                "region": "palisades_la", "sensor": "VIIRS", "satellite": "N",
                "datetime_utc": "2025-01-08 18:30:00+00:00", "latitude": "34.08",
                "longitude": "-118.52", "confidence": "h", "frp": "12.5",
                "daynight": "D", "scan": "0.45", "track": "0.40", "instrument": "VIIRS",
                "brightness": "", "bright_t31": "", "bright_ti4": "335.0", "bright_ti5": "290.0",
            },
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        result = ingest_firms_csv(csv_path, self.processed_dir, self.quarantine_dir, overwrite=True)

        # Check reconciliation: 5 read == 2 valid + 3 quarantined
        self.assertEqual(result["total_read"], 5)
        self.assertEqual(result["valid_count"], 2)
        self.assertEqual(result["quarantined_count"], 3)
        self.assertTrue(result["reconciliation_passed"])

        # Check manifest exists
        manifest_path = Path(result["manifest_output"])
        self.assertTrue(manifest_path.exists())
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["total_input_records"], 5)
        self.assertEqual(manifest["valid_accepted_records"], 2)
        self.assertEqual(manifest["quarantined_records"], 3)

        # Check quarantine file has detailed issues
        quar_path = Path(result["quarantine_output"])
        with quar_path.open("r", encoding="utf-8") as f:
            quarantined = json.load(f)
        self.assertEqual(len(quarantined), 3)
        for q in quarantined:
            self.assertIn("_quarantine_issues", q)
            self.assertGreater(len(q["_quarantine_issues"]), 0)


class TestRealPalisadesDatasetPipeline(unittest.TestCase):
    """End-to-end integration tests on actual Palisades test datasets."""

    def test_real_modis_dataset(self):
        csv_file = Path("data/data/clean/csv/palisades_la_MODIS.csv")
        self.assertTrue(csv_file.exists())

        res = ingest_firms_csv(csv_file, Path("data/processed"), Path("data/quarantine"), overwrite=True)
        self.assertEqual(res["total_read"], 423)
        self.assertEqual(res["valid_count"], 423)
        self.assertEqual(res["quarantined_count"], 0)
        self.assertEqual(res["family"], "MODIS")
        self.assertTrue(res["reconciliation_passed"])

        report = generate_quality_report(
            Path(res["processed_output"]),
            Path(res["quarantine_output"]),
            Path("reports"),
        )
        self.assertTrue(report.exists())

    def test_real_viirs_dataset(self):
        csv_file = Path("data/data/clean/csv/palisades_la_VIIRS.csv")
        self.assertTrue(csv_file.exists())

        res = ingest_firms_csv(csv_file, Path("data/processed"), Path("data/quarantine"), overwrite=True)
        self.assertEqual(res["total_read"], 4137)
        self.assertEqual(res["valid_count"], 4137)
        self.assertEqual(res["quarantined_count"], 0)
        self.assertEqual(res["family"], "VIIRS")
        self.assertTrue(res["reconciliation_passed"])

        report = generate_quality_report(
            Path(res["processed_output"]),
            Path(res["quarantine_output"]),
            Path("reports"),
        )
        self.assertTrue(report.exists())

    def test_real_combined_dataset(self):
        csv_file = Path("data/data/clean/csv/palisades_la_combined.csv")
        self.assertTrue(csv_file.exists())

        res = ingest_firms_csv(csv_file, Path("data/processed"), Path("data/quarantine"), overwrite=True)
        self.assertEqual(res["total_read"], 4560)
        self.assertEqual(res["valid_count"], 4560)
        self.assertEqual(res["quarantined_count"], 0)
        self.assertEqual(res["family"], "MIXED")
        self.assertEqual(res["family_counts"], {"MODIS": 423, "VIIRS": 4137})
        self.assertTrue(res["reconciliation_passed"])

        report = generate_quality_report(
            Path(res["processed_output"]),
            Path(res["quarantine_output"]),
            Path("reports"),
        )
        self.assertTrue(report.exists())


if __name__ == "__main__":
    unittest.main()
