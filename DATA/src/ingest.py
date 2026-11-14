#!/usr/bin/env python3
"""
src/ingest.py - Data standardizer, confidence filter, and Parquet/CSV exporter.

Reads raw CSVs, standardizes schema, applies confidence filtering,
derives UTC timestamps, deduplicates, and saves clean Parquet and CSV files.
Preserves required raw metadata columns (scan, track, instrument, version,
brightness, bright_t31, bright_ti4, bright_ti5, type) and stores confidence as string in combined output.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# ==============================================================================
# NAMED CONSTANTS & SETTINGS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_CLEAN_DIR = BASE_DIR / "data" / "clean"
DATA_CLEAN_CSV_DIR = DATA_CLEAN_DIR / "csv"

# Confidence rule constants
MODIS_MIN_CONFIDENCE = 30
MODIS_NOMINAL_MIN = 30
MODIS_NOMINAL_MAX = 79
MODIS_HIGH_MIN = 80
MODIS_HIGH_MAX = 100

VIIRS_DROP_VALUES = {"l", "L"}
VIIRS_NOMINAL_VALUES = {"n", "N"}
VIIRS_HIGH_VALUES = {"h", "H"}

# Complete output schema: standard fields + raw auxiliary columns requested
OUTPUT_COLUMNS = [
    "region",
    "sensor",
    "satellite",
    "processing",
    "datetime_utc",
    "date",
    "year",
    "latitude",
    "longitude",
    "confidence",
    "confidence_class",
    "frp",
    "daynight",
    # Raw metadata columns requested
    "scan",
    "track",
    "instrument",
    "version",
    "brightness",
    "bright_t31",
    "bright_ti4",
    "bright_ti5",
    "type",
    "is_vegetation_fire"
]

REGIONS_ORDER = [
    "palisades_la",
    "western_ghats_karnataka",
    "punjab_haryana",
    "nsw_victoria_au"
]


# ==============================================================================
# CONFIDENCE CLASSIFICATION
# ==============================================================================
def classify_modis_confidence(conf_series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """
    Apply MODIS confidence rule:
      Keep confidence >= 30.
      confidence_class: 30 to 79 = nominal, 80 to 100 = high.
    Returns: (keep_mask, confidence_class_series)
    """
    conf_num = pd.to_numeric(conf_series, errors="coerce")
    keep_mask = (conf_num >= MODIS_MIN_CONFIDENCE) & (conf_num <= 100)

    classes = pd.Series(index=conf_series.index, dtype="object")
    nominal_mask = (conf_num >= MODIS_NOMINAL_MIN) & (conf_num <= MODIS_NOMINAL_MAX)
    high_mask = (conf_num >= MODIS_HIGH_MIN) & (conf_num <= MODIS_HIGH_MAX)
    low_mask = conf_num < MODIS_MIN_CONFIDENCE

    classes[nominal_mask] = "nominal"
    classes[high_mask] = "high"
    classes[low_mask] = "low"
    return keep_mask, classes


def classify_viirs_confidence(conf_series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """
    Apply VIIRS confidence rule:
      confidence is l, n or h. Drop 'l'. n = nominal, h = high.
    Returns: (keep_mask, confidence_class_series)
    """
    conf_str = conf_series.astype(str).str.strip().str.lower()
    classes = pd.Series(index=conf_series.index, dtype="object")

    classes[conf_str == "n"] = "nominal"
    classes[conf_str == "h"] = "high"
    classes[conf_str == "l"] = "low"

    keep_mask = conf_str.isin(["n", "h"])
    return keep_mask, classes


# ==============================================================================
# INGESTION WORKFLOW PER SENSOR
# ==============================================================================
def ingest_sensor(region: str, sensor: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Read, clean, and standardize detections for a single region and sensor.
    Saves clean Parquet in data/clean/ and CSV in data/clean/csv/.
    """
    sensor_dir = DATA_RAW_DIR / region / sensor
    if not sensor_dir.exists():
        print(f"Warning: Directory not found: {sensor_dir}")
        return pd.DataFrame(columns=OUTPUT_COLUMNS), pd.DataFrame(), {}

    csv_files = sorted(list(sensor_dir.glob("*.csv")))
    if not csv_files:
        print(f"No CSV files found in {sensor_dir}")
        return pd.DataFrame(columns=OUTPUT_COLUMNS), pd.DataFrame(), {}

    dfs = []
    for f in csv_files:
        try:
            df_part = pd.read_csv(f, low_memory=False)
            if len(df_part) > 0:
                dfs.append(df_part)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not dfs:
        print(f"No records loaded across {len(csv_files)} files for {region} - {sensor}")
        df_empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
        return df_empty, pd.DataFrame(), {"loaded": 0, "after_dup": 0, "after_conf": 0, "final": 0}

    df_raw = pd.concat(dfs, ignore_index=True)
    loaded_count = len(df_raw)

    # 1. Add sensor and region columns
    df_raw["sensor"] = sensor
    df_raw["region"] = region

    # Identify satellites found
    satellites_found = df_raw["satellite"].dropna().unique().tolist() if "satellite" in df_raw.columns else []

    # 2. Drop exact duplicate rows
    raw_cols = [c for c in df_raw.columns if c not in ["sensor", "region"]]
    df_dedup = df_raw.drop_duplicates(subset=raw_cols).copy()
    after_dup_count = len(df_dedup)
    dropped_dup_count = loaded_count - after_dup_count

    # 3. Apply Confidence Rule
    if sensor == "MODIS":
        keep_mask, conf_classes = classify_modis_confidence(df_dedup["confidence"])
    elif sensor == "VIIRS":
        keep_mask, conf_classes = classify_viirs_confidence(df_dedup["confidence"])
    else:
        raise ValueError(f"Unknown sensor: {sensor}")

    df_dedup["confidence_class"] = conf_classes
    df_kept = df_dedup[keep_mask].copy()
    df_dropped = df_dedup[~keep_mask].copy()

    after_conf_count = len(df_kept)
    dropped_conf_count = len(df_dropped)
    dropped_pct = (dropped_conf_count / after_dup_count * 100.0) if after_dup_count > 0 else 0.0

    # 4. Build datetime_utc, date, year
    def parse_datetimes(df_in: pd.DataFrame) -> pd.DataFrame:
        if len(df_in) == 0:
            df_in["datetime_utc"] = pd.Series(dtype="datetime64[ns, UTC]")
            df_in["date"] = pd.Series(dtype="object")
            df_in["year"] = pd.Series(dtype="int64")
            return df_in

        time_str = df_in["acq_time"].fillna(0).astype(int).astype(str).str.zfill(4)
        date_str = df_in["acq_date"].astype(str)
        hours = time_str.str.slice(0, 2)
        minutes = time_str.str.slice(2, 4)
        dt_series = pd.to_datetime(
            date_str + " " + hours + ":" + minutes + ":00",
            utc=True,
            errors="coerce"
        )
        df_in["datetime_utc"] = dt_series
        df_in["date"] = df_in["datetime_utc"].dt.date
        df_in["year"] = df_in["datetime_utc"].dt.year
        return df_in

    df_kept = parse_datetimes(df_kept)
    df_dropped = parse_datetimes(df_dropped)

    # 5. Compute is_vegetation_fire: True when type is 0 or missing, False otherwise
    # Retain all rows regardless of type; do not remove non-vegetation fires.
    if "type" in df_kept.columns:
        type_num = pd.to_numeric(df_kept["type"], errors="coerce")
        df_kept["is_vegetation_fire"] = (type_num.isna() | (type_num == 0)).astype(bool)
    else:
        df_kept["is_vegetation_fire"] = True

    # 6. Keep all standard + raw metadata columns
    for col in OUTPUT_COLUMNS:
        if col not in df_kept.columns:
            df_kept[col] = None

    # Cast confidence to string for consistent serialization
    df_kept["confidence"] = df_kept["confidence"].astype(str)

    df_final = df_kept[OUTPUT_COLUMNS].copy()
    final_count = len(df_final)

    # 7. Save dropped low-confidence rows
    DATA_CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    DATA_CLEAN_CSV_DIR.mkdir(parents=True, exist_ok=True)

    dropped_file = DATA_CLEAN_DIR / f"dropped_low_confidence_{region}_{sensor}.csv"
    if len(df_dropped) > 0:
        df_dropped.to_csv(dropped_file, index=False)
    else:
        pd.DataFrame(columns=df_raw.columns).to_csv(dropped_file, index=False)

    # 7. Save Parquet AND CSV
    parquet_file = DATA_CLEAN_DIR / f"{region}_{sensor}.parquet"
    df_final.to_parquet(parquet_file, index=False, engine="pyarrow")

    csv_clean_file = DATA_CLEAN_CSV_DIR / f"{region}_{sensor}.csv"
    df_final.to_csv(csv_clean_file, index=False)

    metrics = {
        "region": region,
        "sensor": sensor,
        "satellites": satellites_found,
        "loaded": loaded_count,
        "duplicates_dropped": dropped_dup_count,
        "after_duplicates": after_dup_count,
        "low_conf_dropped": dropped_conf_count,
        "low_conf_pct": dropped_pct,
        "after_confidence": after_conf_count,
        "final": final_count,
        "parquet_path": str(parquet_file),
        "csv_path": str(csv_clean_file),
        "dropped_path": str(dropped_file)
    }

    print(f"\n--- Ingest Summary: {region} | {sensor} ---")
    print(f"  Satellites found:       {satellites_found}")
    print(f"  1. Loaded rows:         {loaded_count:,}")
    print(f"  2. After duplicates:    {after_dup_count:,} (dropped {dropped_dup_count:,})")
    print(f"  3. After confidence:    {after_conf_count:,} (dropped {dropped_conf_count:,} [{dropped_pct:.2f}%])")
    print(f"  4. Final saved rows:    {final_count:,}")
    print(f"  Clean Parquet:          {parquet_file.name}")
    print(f"  Clean CSV:              {csv_clean_file.name}")
    print(f"  Dropped CSV:            {dropped_file.name}")

    return df_final, df_dropped, metrics


# ==============================================================================
# REGION ORCHESTRATION & COMBINED EXPORT
# ==============================================================================
def ingest_region(region: str) -> pd.DataFrame:
    """
    Ingest all sensors for a region and write both combined Parquet and CSV.
    Stores confidence as text in the combined file as required.
    """
    print(f"\n=======================================================")
    print(f"INGESTING REGION: {region}")
    print(f"=======================================================")

    DATA_CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    DATA_CLEAN_CSV_DIR.mkdir(parents=True, exist_ok=True)

    df_modis, _, _ = ingest_sensor(region, "MODIS")
    df_viirs, _, _ = ingest_sensor(region, "VIIRS")

    combined_dfs = [df for df in [df_modis, df_viirs] if len(df) > 0]
    if combined_dfs:
        df_combined = pd.concat(combined_dfs, ignore_index=True)
    else:
        df_combined = pd.DataFrame(columns=OUTPUT_COLUMNS)

    # Store confidence as string in combined file
    df_combined["confidence"] = df_combined["confidence"].astype(str)

    # Save combined Parquet
    combined_parquet = DATA_CLEAN_DIR / f"{region}_combined.parquet"
    df_combined.to_parquet(combined_parquet, index=False, engine="pyarrow")

    # Save combined CSV
    combined_csv = DATA_CLEAN_CSV_DIR / f"{region}_combined.csv"
    df_combined.to_csv(combined_csv, index=False)

    print(f"\n>> Combined Dataset Created:")
    print(f"   Parquet: {combined_parquet.name}")
    print(f"   CSV:     {combined_csv.name}")
    print(f"   Total rows: {len(df_combined):,} (MODIS: {len(df_modis):,}, VIIRS: {len(df_viirs):,})")
    return df_combined


# ==============================================================================
# CLI ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Clean and ingest NASA FIRMS fire data.")
    parser.add_argument("--region", choices=REGIONS_ORDER + ["all"], default="palisades_la",
                        help="Region identifier or 'all'")
    parser.add_argument("--all", action="store_true", help="Ingest all configured regions")

    args = parser.parse_args()
    target_regions = REGIONS_ORDER if (args.all or args.region == "all") else [args.region]

    for reg in target_regions:
        ingest_region(reg)


if __name__ == "__main__":
    main()
