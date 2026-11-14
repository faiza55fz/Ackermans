"""
FireTrace Pilot Pipeline - Data Ingestion Skeleton
Prepares ingestion for raw NASA FIRMS CSV granules into validated processed records and quarantine logs.
Preserves 100% of raw NASA columns, preserves confidence_raw, and separates derived metadata.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from validate_data import (
    compute_dataset_spatial_bounds,
    validate_coordinates,
    validate_raw_record,
    validate_timestamp,
)


def detect_sensor_family(header_keys: List[str], sample_record: Dict[str, Any]) -> str:
    """
    Detects whether the file represents MODIS or VIIRS based on header columns or values.
    Does not hardcode specific sensor versions.
    """
    keys_lower = [k.lower() for k in header_keys]

    # VIIRS-specific raw spectral band columns
    if any(k in keys_lower for k in ("bright_ti4", "bright_ti5")):
        return "VIIRS"

    # MODIS-specific raw spectral band columns
    if any(k in keys_lower for k in ("brightness", "bright_t31")):
        return "MODIS"

    # Fallback to instrument / satellite column inspection
    instrument_val = str(sample_record.get("instrument", "")).upper()
    if "VIIRS" in instrument_val:
        return "VIIRS"
    if "MODIS" in instrument_val:
        return "MODIS"

    return "UNKNOWN"


def map_canonical_satellite_name(satellite_raw: Any, family: str) -> str:
    """Maps raw satellite code to display string without mutating raw satellite value."""
    sat_clean = str(satellite_raw).strip()
    if family == "MODIS":
        if sat_clean in ("Terra", "T"):
            return "MODIS Terra"
        if sat_clean in ("Aqua", "A"):
            return "MODIS Aqua"
        return f"MODIS {sat_clean}"
    if family == "VIIRS":
        if sat_clean in ("N", "NPP", "Suomi-NPP"):
            return "VIIRS S-NPP"
        if sat_clean in ("1", "20", "NOAA-20", "JPSS-1"):
            return "VIIRS NOAA-20"
        if sat_clean in ("2", "21", "NOAA-21", "JPSS-2"):
            return "VIIRS NOAA-21"
        return f"VIIRS {sat_clean}"
    return sat_clean


def process_raw_firms_file(
    input_file: Path,
    processed_dir: Path,
    quarantine_dir: Path,
) -> Dict[str, Any]:
    """
    Ingests a raw NASA FIRMS CSV file:
    1. Preserves all original NASA columns as delivered.
    2. Stores raw confidence as 'confidence_raw'.
    3. Populates sensor-specific confidence without conflation.
    4. Quarantines fatal defects into quarantine_dir with diagnostic error messages.
    5. Stages valid records in processed_dir.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    processed_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    with input_file.open("r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []

        records_processed = 0
        valid_records: List[Dict[str, Any]] = []
        quarantined_records: List[Dict[str, Any]] = []

        family_detected = "UNKNOWN"

        for row in reader:
            records_processed += 1
            if records_processed == 1:
                family_detected = detect_sensor_family(header, row)

            validation = validate_raw_record(row)

            if validation.is_fatal:
                quarantine_row = dict(row)
                quarantine_row["_quarantine_issues"] = [
                    {"field": i.field, "message": i.message, "raw_value": str(i.raw_value)}
                    for i in validation.issues if i.issue_type == "FATAL"
                ]
                quarantined_records.append(quarantine_row)
            else:
                # Build unified record while explicitly preserving all raw columns
                cleaned_record: Dict[str, Any] = {}

                # 1. Preserve 100% of raw NASA columns as delivered
                for k, v in row.items():
                    cleaned_record[k] = v

                # 2. Explicitly preserve raw confidence string
                raw_conf = row.get("confidence", "")
                cleaned_record["confidence_raw"] = str(raw_conf)

                # 3. Handle sensor-specific confidence separately (no arbitrary conversion)
                if family_detected == "MODIS":
                    try:
                        cleaned_record["modis_confidence"] = int(float(raw_conf))
                    except (ValueError, TypeError):
                        cleaned_record["modis_confidence"] = None
                    cleaned_record["viirs_confidence"] = None
                elif family_detected == "VIIRS":
                    cleaned_record["viirs_confidence"] = str(raw_conf).lower().strip()
                    cleaned_record["modis_confidence"] = None
                else:
                    cleaned_record["modis_confidence"] = None
                    cleaned_record["viirs_confidence"] = None

                # 4. Populate derived metadata in separated namespace
                lat_k = next((k for k in row if k.lower() in ("latitude", "lat")), "latitude")
                lng_k = next((k for k in row if k.lower() in ("longitude", "lng", "lon")), "longitude")
                date_k = next((k for k in row if k.lower() in ("acq_date", "date")), "acq_date")
                time_k = next((k for k in row if k.lower() in ("acq_time", "time")), "acq_time")

                _, lat_f, lng_f, _ = validate_coordinates(row.get(lat_k), row.get(lng_k))
                _, iso_ts, _ = validate_timestamp(row.get(date_k), row.get(time_k))

                sat_val = row.get("satellite", "")
                cleaned_record["derived_timestamp_utc"] = iso_ts
                cleaned_record["derived_family"] = family_detected
                cleaned_record["derived_sensor_canonical"] = map_canonical_satellite_name(sat_val, family_detected)
                cleaned_record["derived_period"] = "Day" if str(row.get("daynight", "")).upper() == "D" else "Night"

                valid_records.append(cleaned_record)

    # Compute observed spatial extent from valid records
    spatial_bounds = compute_dataset_spatial_bounds(valid_records)

    # Save output artifacts
    out_valid_file = processed_dir / f"{input_file.stem}_processed.json"
    out_quarantine_file = quarantine_dir / f"{input_file.stem}_quarantined.json"

    with out_valid_file.open("w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2)

    with out_quarantine_file.open("w", encoding="utf-8") as f:
        json.dump(quarantined_records, f, indent=2)

    return {
        "file_name": input_file.name,
        "family": family_detected,
        "total_read": records_processed,
        "valid_count": len(valid_records),
        "quarantined_count": len(quarantined_records),
        "processed_output": str(out_valid_file),
        "quarantine_output": str(out_quarantine_file),
        "spatial_bounds": spatial_bounds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest and validate raw NASA FIRMS active fire granules")
    parser.add_argument("input_file", help="Path to raw NASA FIRMS CSV file")
    parser.add_argument("--processed_dir", default="data/processed", help="Directory for valid processed records")
    parser.add_argument("--quarantine_dir", default="data/quarantine", help="Directory for quarantined records")
    args = parser.parse_args()

    input_p = Path(args.input_file)
    processed_p = Path(args.processed_dir)
    quarantine_p = Path(args.quarantine_dir)

    print(f"Ingesting: {input_p} ...")
    results = process_raw_firms_file(input_p, processed_p, quarantine_p)
    print("Ingestion Complete:")
    print(f"  Detected Family:    {results['family']}")
    print(f"  Records Processed:  {results['total_read']:,}")
    print(f"  Valid Accepted:     {results['valid_count']:,}")
    print(f"  Quarantined:        {results['quarantined_count']:,}")
    print(f"  Spatial Bounds:     {results['spatial_bounds']}")


if __name__ == "__main__":
    main()
