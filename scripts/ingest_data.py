"""
FireTrace Pilot Pipeline - Data Ingestion Tool
Performs record-level sensor identification with robust multi-attribute conflict detection,
preserves all original NASA columns unmodified, preserves confidence_raw without rounding,
isolates derived fields in the derived_* namespace, routes fatal defects to quarantine,
reconciles record counts, and prevents output artifact naming collisions.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from validate_data import (
        compute_dataset_spatial_bounds,
        validate_raw_record,
    )
except ImportError:
    from scripts.validate_data import (
        compute_dataset_spatial_bounds,
        validate_raw_record,
    )


# Recognized NASA satellite platform codes
MODIS_SATELLITES = {"TERRA", "T", "AQUA", "A"}
VIIRS_SATELLITES = {
    "N", "NPP", "SUOMI-NPP", "SNPP",
    "1", "20", "NOAA-20", "NOAA 20", "JPSS-1",
    "2", "21", "NOAA-21", "NOAA 21", "JPSS-2",
}


def identify_record_sensor(row: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    """
    Identifies the sensor family (MODIS, VIIRS, AMBIGUOUS, or UNKNOWN) at the INDIVIDUAL RECORD level.
    Evaluates instrument, satellite platform, and populated spectral channels together.
    Detects contradictory evidence rather than allowing one field to override another.
    Never guesses when evidence is missing or conflicting.
    Returns: (sensor_family, canonical_sensor_name, identification_notes)
    """
    notes: List[str] = []
    keys_lower = {k.lower(): k for k in row.keys()}

    # 1. Instrument attribute evidence
    inst_key = keys_lower.get("instrument")
    raw_instrument = str(row.get(inst_key, "")).strip().upper() if inst_key else ""
    inst_is_modis = "MODIS" in raw_instrument
    inst_is_viirs = "VIIRS" in raw_instrument

    # 2. Satellite platform attribute evidence
    sat_key = keys_lower.get("satellite")
    raw_satellite = str(row.get(sat_key, "")).strip() if sat_key else ""
    sat_upper = raw_satellite.upper()
    sat_is_modis = sat_upper in MODIS_SATELLITES
    sat_is_viirs = sat_upper in VIIRS_SATELLITES

       # 3. Spectral channel evidence
    def has_populated_value(channel: str) -> bool:
        key = keys_lower.get(channel)
        if not key:
            return False

        value = str(row.get(key, "")).strip().lower()

        return value not in {
            "", "none", "null", "nan",
            "+nan", "-nan", "na",
            "n/a", "inf", "+inf", "-inf",
            "infinity",
        }

    has_viirs_channels = any(
        has_populated_value(ch)
        for ch in ("bright_ti4", "bright_ti5")
    )

    has_modis_channels = any(
        has_populated_value(ch)
        for ch in ("brightness", "bright_t31")
    )
    # Accumulate evidence indicators
    modis_evidence = []
    viirs_evidence = []

    if inst_is_modis:
        modis_evidence.append("instrument=MODIS")
    if sat_is_modis:
        modis_evidence.append(f"satellite={raw_satellite}")
    if has_modis_channels:
        modis_evidence.append("spectral_channels=MODIS(brightness/bright_t31)")

    if inst_is_viirs:
        viirs_evidence.append("instrument=VIIRS")
    if sat_is_viirs:
        viirs_evidence.append(f"satellite={raw_satellite}")
    if has_viirs_channels:
        viirs_evidence.append("spectral_channels=VIIRS(bright_ti4/bright_ti5)")

    # Conflict detection: Both families show positive evidence
    if modis_evidence and viirs_evidence:
        family = "AMBIGUOUS"
        canonical_name = f"Ambiguous Sensor ({raw_satellite or raw_instrument or 'Conflict'})"
        notes.append(
            f"CONFLICT: Contradictory sensor evidence on record. "
            f"MODIS indicators: [{', '.join(modis_evidence)}]; "
            f"VIIRS indicators: [{', '.join(viirs_evidence)}]"
        )
        return family, canonical_name, notes

    # Unambiguous MODIS identification
    if modis_evidence and not viirs_evidence:
        family = "MODIS"
        if sat_upper in ("TERRA", "T"):
            canonical_name = "MODIS Terra"
        elif sat_upper in ("AQUA", "A"):
            canonical_name = "MODIS Aqua"
        elif raw_satellite:
            canonical_name = f"MODIS ({raw_satellite})"
        else:
            canonical_name = "MODIS (Unspecified Satellite)"
        notes.append(f"Identified as MODIS via [{', '.join(modis_evidence)}]")
        return family, canonical_name, notes

    # Unambiguous VIIRS identification
    if viirs_evidence and not modis_evidence:
        family = "VIIRS"
        if sat_upper in ("N", "NPP", "SUOMI-NPP", "SNPP"):
            canonical_name = "VIIRS S-NPP"
        elif sat_upper in ("1", "20", "NOAA-20", "NOAA 20", "JPSS-1"):
            canonical_name = "VIIRS NOAA-20"
        elif sat_upper in ("2", "21", "NOAA-21", "NOAA 21", "JPSS-2"):
            canonical_name = "VIIRS NOAA-21"
        elif raw_satellite:
            canonical_name = f"VIIRS ({raw_satellite})"
        else:
            canonical_name = "VIIRS (Unspecified Satellite)"
        notes.append(f"Identified as VIIRS via [{', '.join(viirs_evidence)}]")
        return family, canonical_name, notes

    # Neither sensor family could be identified from available evidence
    family = "UNKNOWN"
    canonical_name = f"Unknown ({raw_satellite})" if raw_satellite else "Unknown Satellite"
    notes.append("No unambiguous sensor instrument, platform, or spectral channel evidence found")
    return family, canonical_name, notes



def parse_confidence_fields(
    raw_confidence: Any, sensor_family: str
) -> Tuple[Optional[str], Optional[int], Optional[str], List[str]]:
    """
    Preserve the original confidence field exactly as received.

    MODIS: integer percentage 0-100 only.
    VIIRS: categorical l/n/h only.
    No rounding, truncation, or cross-sensor conversion.
    """
    issues: List[str] = []

    if raw_confidence is None:
        return None, None, None, issues

    # Preserve the original CSV field, including whitespace.
    confidence_raw = str(raw_confidence)

    # Use a separate normalized value only for validation.
    raw_str = confidence_raw.strip()

    modis_confidence: Optional[int] = None
    viirs_confidence: Optional[str] = None

    if raw_str == "":
        return confidence_raw, None, None, issues

    if raw_str.lower() in (
        "none", "null", "nan", "+nan", "-nan",
        "inf", "+inf", "-inf", "infinity", "na"
    ):
        issues.append(
            f"Unexpected non-missing confidence literal: '{raw_str}'"
        )
        return confidence_raw, None, None, issues

    if sensor_family == "MODIS":
        try:
            value = float(raw_str)

            if not math.isfinite(value):
                issues.append(f"MODIS confidence is not finite: '{raw_str}'")
            elif not value.is_integer():
                issues.append(
                    f"Fractional MODIS confidence rejected: '{raw_str}'. "
                    "Rounding and truncation are not permitted."
                )
            elif not 0 <= value <= 100:
                issues.append(
                    f"MODIS confidence outside valid range [0, 100]: '{raw_str}'"
                )
            else:
                modis_confidence = int(value)

        except (ValueError, TypeError):
            issues.append(f"Non-numeric MODIS confidence: '{raw_str}'")

    elif sensor_family == "VIIRS":
        category = raw_str.lower()

        if category in ("l", "n", "h"):
            viirs_confidence = category
        elif category in ("low", "nominal", "high"):
            viirs_confidence = category[0]
            issues.append(
                f"VIIRS category '{raw_str}' normalized to "
                f"'{category[0]}'"
            )
        else:
            issues.append(
                f"Unexpected VIIRS confidence category: '{raw_str}'"
            )

    else:
        issues.append(
            f"Sensor family '{sensor_family}' is not classified. "
            "Confidence retained only as confidence_raw."
        )

    return (
        confidence_raw,
        modis_confidence,
        viirs_confidence,
        issues,
    )


def map_derived_period(daynight_raw: Any) -> Optional[str]:
    """
    Maps daynight to 'Day' or 'Night'.
    If missing, unpopulated, or unexpected, returns None (DO NOT assume Night).
    """
    if daynight_raw is None:
        return None
    val = str(daynight_raw).strip().upper()
    if val in ("D", "DAY"):
        return "Day"
    if val in ("N", "NIGHT"):
        return "Night"
    return None



def ingest_firms_csv(
    input_file: Path,
    processed_dir: Path,
    quarantine_dir: Path,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Ingest a NASA FIRMS CSV while preserving original source fields.

    - Identifies sensor family independently for every record.
    - Keeps MODIS and VIIRS confidence separate.
    - Quarantines fatal validation failures.
    - Preserves non-fatal warnings.
    - Does not infer zero coverage or confirmed cross-satellite overlaps.
    """

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    processed_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    out_valid_file = (
        processed_dir / f"{input_file.stem}_processed.json"
    )
    out_quarantine_file = (
        quarantine_dir / f"{input_file.stem}_quarantined.json"
    )
    out_manifest_file = (
        processed_dir / f"{input_file.stem}_manifest.json"
    )

    # Never silently overwrite an earlier ingestion result unless overwrite=True.
    if not overwrite and (out_valid_file.exists() or out_quarantine_file.exists()):
        raise FileExistsError(
            "Output already exists. Move or rename the previous output "
            "files before running this input again, or specify --overwrite."
        )

    records_processed = 0
    valid_records: List[Dict[str, Any]] = []
    quarantined_records: List[Dict[str, Any]] = []
    family_counts: Dict[str, int] = {}

    with input_file.open(
        "r", encoding="utf-8-sig", newline=""
    ) as csv_file:

        reader = csv.DictReader(csv_file)
        header = reader.fieldnames or []

        if not header:
            raise ValueError("CSV file has no header row.")

        if len(header) != len(set(header)):
            raise ValueError(
                "CSV contains duplicate column names. "
                "Resolve duplicate headers before ingestion."
            )

        for row in reader:
            records_processed += 1

            # 1. Identify the sensor for THIS record.
            sensor_family, canonical_name, sensor_notes = (
                identify_record_sensor(row)
            )

            family_counts[sensor_family] = (
                family_counts.get(sensor_family, 0) + 1
            )

            # 2. Validate the original record.
            validation = validate_raw_record(row)

            # 3. Parse confidence without changing the source field.
            raw_confidence = row.get("confidence")

            (
                confidence_raw,
                modis_confidence,
                viirs_confidence,
                confidence_issues,
            ) = parse_confidence_fields(
                raw_confidence,
                sensor_family,
            )

            # Start with every original source column unchanged.
            output_record: Dict[str, Any] = dict(row)

            # 4. Keep raw and sensor-specific confidence separate.
            output_record["confidence_raw"] = confidence_raw
            output_record["modis_confidence"] = modis_confidence
            output_record["viirs_confidence"] = viirs_confidence

            # 5. Add derived metadata.
            output_record["derived_family"] = sensor_family
            output_record["derived_sensor_canonical"] = canonical_name
            output_record["derived_timestamp_utc"] = (
                validation.parsed_iso_timestamp
            )
            output_record["derived_period"] = map_derived_period(
                row.get("daynight")
            )

            output_record["derived_latitude"] = validation.parsed_lat
            output_record["derived_longitude"] = validation.parsed_lng

            output_record["derived_scan"] = validation.parsed_scan
            output_record["derived_track"] = validation.parsed_track
            output_record["derived_scan_km"] = validation.parsed_scan
            output_record["derived_track_km"] = validation.parsed_track
            output_record["derived_frp"] = validation.parsed_frp

            # Deterministic unique record ID from primary physical observation keys
            id_components = (
                f"{validation.parsed_lat}_{validation.parsed_lng}_"
                f"{validation.parsed_iso_timestamp}_{canonical_name}_"
                f"{validation.parsed_scan}_{validation.parsed_track}_"
                f"{output_record.get('frp')}"
            )
            output_record["derived_record_id"] = hashlib.sha256(
                id_components.encode("utf-8")
            ).hexdigest()[:16]

            # No unsupported scientific conclusions.
            output_record["derived_cross_sat_overlap"] = None
            output_record["derived_coverage_status"] = "coverage_unknown"

            # 6. Preserve diagnostic information.
            validation_warnings = [
                {
                    "field": issue.field,
                    "message": issue.message,
                    "raw_value": issue.raw_value,
                }
                for issue in validation.issues
                if issue.issue_type == "WARNING"
            ]

            ingestion_warnings = (
                [{"message": note} for note in sensor_notes]
                + [{"message": issue} for issue in confidence_issues]
            )

            output_record["_validation_warnings"] = validation_warnings
            output_record["_ingestion_warnings"] = ingestion_warnings

            # 7. Fatal defects go to quarantine.
            if validation.is_fatal:
                output_record["_quarantine_issues"] = [
                    {
                        "field": issue.field,
                        "message": issue.message,
                        "raw_value": issue.raw_value,
                    }
                    for issue in validation.issues
                    if issue.issue_type == "FATAL"
                ]

                quarantined_records.append(output_record)

            else:
                valid_records.append(output_record)

    # 8. Compute spatial bounds using original coordinate columns.
    spatial_bounds = compute_dataset_spatial_bounds(valid_records)

    # 9. Determine the overall dataset family from all records.
    known_families = {
        family
        for family in family_counts
        if family in ("MODIS", "VIIRS")
    }

    if known_families == {"MODIS", "VIIRS"}:
        dataset_family = "MIXED"
    elif len(known_families) == 1:
        dataset_family = next(iter(known_families))
    elif family_counts.get("AMBIGUOUS", 0) > 0:
        dataset_family = "AMBIGUOUS"
    else:
        dataset_family = "UNKNOWN"

    # 10. Independently reconcile the record counts.
    if records_processed != (
        len(valid_records) + len(quarantined_records)
    ):
        raise RuntimeError(
            "Record reconciliation failed: "
            f"read={records_processed}, "
            f"accepted={len(valid_records)}, "
            f"quarantined={len(quarantined_records)}"
        )

    # 11. Write the output artifacts.
    with out_valid_file.open("w", encoding="utf-8") as output_file:
        json.dump(valid_records, output_file, indent=2, allow_nan=False)

    with out_quarantine_file.open(
        "w", encoding="utf-8"
    ) as output_file:
        json.dump(
            quarantined_records,
            output_file,
            indent=2,
            allow_nan=False,
        )

    # 12. Write companion ingest manifest for verifiable audit reconciliation.
    manifest_data = {
        "file_name": input_file.name,
        "input_file": str(input_file),
        "dataset_family": dataset_family,
        "family_counts": family_counts,
        "total_input_records": records_processed,
        "valid_accepted_records": len(valid_records),
        "quarantined_records": len(quarantined_records),
        "reconciliation_passed": True,
        "spatial_bounds": spatial_bounds,
    }
    with out_manifest_file.open("w", encoding="utf-8") as output_file:
        json.dump(manifest_data, output_file, indent=2)

    return {
        "file_name": input_file.name,
        "family": dataset_family,
        "family_counts": family_counts,
        "total_read": records_processed,
        "valid_count": len(valid_records),
        "quarantined_count": len(quarantined_records),
        "reconciliation_passed": True,
        "processed_output": str(out_valid_file),
        "quarantine_output": str(out_quarantine_file),
        "manifest_output": str(out_manifest_file),
        "spatial_bounds": spatial_bounds,
    }



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and validate raw NASA FIRMS active fire CSV data"
    )

    parser.add_argument(
        "input_file",
        help="Path to raw NASA FIRMS CSV file",
    )
    parser.add_argument(
        "--processed_dir",
        default="data/processed",
        help="Directory for accepted processed records",
    )
    parser.add_argument(
        "--quarantine_dir",
        default="data/quarantine",
        help="Directory for quarantined records",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files if they already exist",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    processed_path = Path(args.processed_dir)
    quarantine_path = Path(args.quarantine_dir)

    print(f"Ingesting: {input_path}")

    results = ingest_firms_csv(
        input_path,
        processed_path,
        quarantine_path,
        overwrite=args.overwrite,
    )

    print("\nIngestion complete.")
    print(f"  Dataset family:       {results['family']}")
    print(f"  Family counts:        {results['family_counts']}")
    print(f"  Records processed:    {results['total_read']:,}")
    print(f"  Valid accepted:       {results['valid_count']:,}")
    print(f"  Quarantined:          {results['quarantined_count']:,}")
    print(f"  Reconciliation:       {results['reconciliation_passed']}")
    print(f"  Spatial bounds:       {results['spatial_bounds']}")
    print(f"  Processed output:     {results['processed_output']}")
    print(f"  Quarantine output:    {results['quarantine_output']}")





if __name__ == "__main__":
    main()
