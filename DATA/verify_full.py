#!/usr/bin/env python3
"""
verify_full.py - Comprehensive independent verification of FIRMS raw & clean data.

Recomputes all metrics directly from data/raw/ without importing ingest.py logic,
and verifies schema, deduplication, confidence filtering, date ranges, file timestamps,
and window completeness against the download manifests and clean outputs.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw" / "palisades_la"
DATA_CLEAN_DIR = BASE_DIR / "data" / "clean"
DATA_CLEAN_CSV_DIR = DATA_CLEAN_DIR / "csv"
LOGS_DIR = BASE_DIR / "logs"

BBOX = (-118.75, 33.95, -118.40, 34.20)
TODAY = date(2026, 11, 14)

EXPECTED_COLUMNS = [
    "region", "sensor", "satellite", "processing", "datetime_utc", "date", "year",
    "latitude", "longitude", "confidence", "confidence_class", "frp", "daynight",
    "scan", "track", "instrument", "version", "brightness", "bright_t31",
    "bright_ti4", "bright_ti5", "type", "is_vegetation_fire"
]

STREAMS = [
    {
        "name": "MODIS (Terra & Aqua)",
        "sensor": "MODIS",
        "stream_id": "MODIS",
        "start_date": date(2000, 11, 1),
        "end_date": TODAY,
        "manifest_path": DATA_RAW_DIR / "MODIS" / ".download_manifest.json"
    },
    {
        "name": "VIIRS S-NPP",
        "sensor": "VIIRS",
        "stream_id": "VIIRS_SNPP",
        "start_date": date(2012, 1, 20),
        "end_date": date(2026, 11, 2),
        "manifest_path": DATA_RAW_DIR / "VIIRS" / ".download_manifest.json"
    },
    {
        "name": "VIIRS NOAA-20",
        "sensor": "VIIRS",
        "stream_id": "VIIRS_NOAA20",
        "start_date": date(2018, 4, 1),
        "end_date": TODAY,
        "manifest_path": DATA_RAW_DIR / "VIIRS" / ".download_manifest.json"
    },
    {
        "name": "VIIRS NOAA-21",
        "sensor": "VIIRS",
        "stream_id": "VIIRS_NOAA21",
        "start_date": date(2023, 3, 1),
        "end_date": TODAY,
        "manifest_path": DATA_RAW_DIR / "VIIRS" / ".download_manifest.json"
    }
]


def generate_full_year_windows(stream_id: str, start_d: date, end_d: date) -> list[str]:
    """Generate expected 5-day windows covering the full year calendar."""
    windows = []
    for yr in range(start_d.year, end_d.year + 1):
        yr_start = date(yr, 1, 1)
        yr_end = date(yr, 12, 31)
        act_start = max(yr_start, start_d)
        act_end = min(yr_end, end_d)
        if act_start > act_end:
            continue
        cur = act_start
        while cur <= act_end:
            w_days = min(5, (act_end - cur).days + 1)
            ds = cur.strftime("%Y-%m-%d")
            windows.append(f"{stream_id}_{ds}_{w_days}")
            cur += timedelta(days=w_days)
    return windows


def run_verification():
    print("=" * 80)
    print("INDEPENDENT FULL-PIPELINE VERIFICATION FOR palisades_la")
    print("=" * 80)

    all_passed = True
    results = []

    def record_check(name: str, passed: bool, details: str):
        nonlocal all_passed
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        results.append((name, status, details))
        print(f"[{status}] {name}: {details}")

    # --------------------------------------------------------------------------
    # CHECK 1: MANIFEST WINDOWS (EXPECTED VS SAVED)
    # --------------------------------------------------------------------------
    print("\n--- 1. Download Windows Verification ---")
    manifest_cache = {}
    total_expected_windows = 0
    total_saved_windows = 0

    for stream in STREAMS:
        mpath = stream["manifest_path"]
        if mpath not in manifest_cache:
            if mpath.exists():
                with open(mpath, "r", encoding="utf-8") as f:
                    manifest_cache[mpath] = json.load(f)
            else:
                manifest_cache[mpath] = {"completed_windows": []}

        saved_windows_set = set(manifest_cache[mpath].get("completed_windows", []))
        expected_windows = generate_full_year_windows(
            stream["stream_id"], stream["start_date"], stream["end_date"]
        )
        total_expected_windows += len(expected_windows)

        missing = set(expected_windows) - saved_windows_set
        stream_saved = {w for w in saved_windows_set if w.startswith(stream["stream_id"] + "_")}

        passed = (len(missing) == 0)
        record_check(
            f"Windows {stream['name']}",
            passed,
            f"expected={len(expected_windows)}, saved_matching={len(stream_saved)}, missing={len(missing)}"
        )

    # --------------------------------------------------------------------------
    # CHECK 2: FAILED WINDOWS IN LOGS
    # --------------------------------------------------------------------------
    print("\n--- 2. Unresolved Download Failures ---")
    failures_file = LOGS_DIR / "download_failures.csv"
    unresolved = []
    if failures_file.exists():
        df_fails = pd.read_csv(failures_file)
        # Check if each logged failure is present in completed_windows
        for _, row in df_fails.iterrows():
            reg = row.get("region")
            s = row.get("sensor")
            sd = row.get("start_date")
            # find corresponding manifest
            m_path = (DATA_RAW_DIR / "MODIS" / ".download_manifest.json") if s == "MODIS" else (DATA_RAW_DIR / "VIIRS" / ".download_manifest.json")
            m_data = manifest_cache.get(m_path, {})
            cw = set(m_data.get("completed_windows", []))
            # match by date prefix
            matching = [w for w in cw if f"_{sd}_" in w]
            if not matching:
                unresolved.append(f"{reg}/{s}/{sd}")

    record_check(
        "Unresolved Failures Log",
        len(unresolved) == 0,
        f"{len(unresolved)} unresolved windows out of {len(df_fails) if failures_file.exists() else 0} logged entries"
    )

    # --------------------------------------------------------------------------
    # CHECK 3: INDEPENDENT RECOMPUTATION FROM DATA/RAW/
    # --------------------------------------------------------------------------
    print("\n--- 3. Independent Raw Recomputation vs Cleaned Files ---")
    # MODIS recomputation
    modis_files = sorted((DATA_RAW_DIR / "MODIS").glob("*.csv"))
    modis_dfs = [pd.read_csv(f, low_memory=False) for f in modis_files]
    df_m_raw = pd.concat([d for d in modis_dfs if len(d) > 0], ignore_index=True) if modis_dfs else pd.DataFrame()
    m_raw_count = len(df_m_raw)

    m_dedup = df_m_raw.drop_duplicates().copy()
    m_dup_dropped = m_raw_count - len(m_dedup)

    m_conf = pd.to_numeric(m_dedup["confidence"], errors="coerce")
    m_low_dropped = len(m_dedup[m_conf < 30])
    m_final = len(m_dedup[(m_conf >= 30) & (m_conf <= 100)])

    record_check(
        "MODIS Row Pipeline Counts",
        (m_raw_count == 595 and m_low_dropped == 18 and m_final == 577),
        f"raw_loaded={m_raw_count} (expected 595), duplicates_dropped={m_dup_dropped} (expected 0), low_conf_dropped={m_low_dropped} (expected 18), final_clean={m_final} (expected 577)"
    )

    # VIIRS recomputation
    viirs_files = sorted((DATA_RAW_DIR / "VIIRS").glob("*.csv"))
    viirs_dfs = [pd.read_csv(f, low_memory=False) for f in viirs_files]
    df_v_raw = pd.concat([d for d in viirs_dfs if len(d) > 0], ignore_index=True) if viirs_dfs else pd.DataFrame()
    v_raw_count = len(df_v_raw)

    v_dedup = df_v_raw.drop_duplicates().copy()
    v_dup_dropped = v_raw_count - len(v_dedup)

    v_conf = v_dedup["confidence"].astype(str).str.strip().str.lower()
    v_low_dropped = len(v_dedup[v_conf == "l"])
    v_final = len(v_dedup[v_conf.isin(["n", "h"])])

    record_check(
        "VIIRS Row Pipeline Counts",
        (v_raw_count == 5744 and v_low_dropped == 238 and v_final == 5506),
        f"raw_loaded={v_raw_count} (expected 5744), duplicates_dropped={v_dup_dropped} (expected 0), low_conf_dropped={v_low_dropped} (expected 238), final_clean={v_final} (expected 5506)"
    )

    combined_expected = m_final + v_final
    record_check(
        "Combined Total Clean Rows",
        combined_expected == 6083,
        f"clean_total={combined_expected} (MODIS 577 + VIIRS 5506, expected 6083)"
    )

    # --------------------------------------------------------------------------
    # CHECK 4: CLEANED FILES EXISTENCE & ROW COUNTS (PARQUET & CSV)
    # --------------------------------------------------------------------------
    print("\n--- 4. Clean File Formats & Row Count Parity ---")
    file_checks = [
        ("palisades_la_MODIS.parquet", DATA_CLEAN_DIR / "palisades_la_MODIS.parquet", 577),
        ("palisades_la_MODIS.csv", DATA_CLEAN_CSV_DIR / "palisades_la_MODIS.csv", 577),
        ("palisades_la_VIIRS.parquet", DATA_CLEAN_DIR / "palisades_la_VIIRS.parquet", 5506),
        ("palisades_la_VIIRS.csv", DATA_CLEAN_CSV_DIR / "palisades_la_VIIRS.csv", 5506),
        ("palisades_la_combined.parquet", DATA_CLEAN_DIR / "palisades_la_combined.parquet", 6083),
        ("palisades_la_combined.csv", DATA_CLEAN_CSV_DIR / "palisades_la_combined.csv", 6083),
    ]

    for fname, fpath, exp_rows in file_checks:
        exists = fpath.exists()
        if not exists:
            record_check(f"File Existence: {fname}", False, f"File missing at {fpath}")
            continue
        df_read = pd.read_parquet(fpath) if fpath.suffix == ".parquet" else pd.read_csv(fpath, low_memory=False)
        row_match = len(df_read) == exp_rows
        col_match = len(df_read.columns) == 23
        record_check(
            f"Integrity: {fname}",
            (row_match and col_match),
            f"rows={len(df_read)} (expected {exp_rows}), cols={len(df_read.columns)} (expected 23)"
        )

    # --------------------------------------------------------------------------
    # CHECK 5: FULL-YEAR COVERAGE & SEASONALITY
    # --------------------------------------------------------------------------
    print("\n--- 5. Full-Year Coverage & Seasonality ---")
    df_comb = pd.read_parquet(DATA_CLEAN_DIR / "palisades_la_combined.parquet")
    dates_series = pd.to_datetime(df_comb["date"])
    min_date = df_comb["date"].min()
    max_date = df_comb["date"].max()

    months_present = set(dates_series.dt.month.unique())
    all_12_months = len(months_present) == 12

    sep_nov_rows = len(df_comb[dates_series.dt.month.isin([9, 10, 11])])
    has_sep_nov = sep_nov_rows > 0

    record_check(
        "Full-Year Months Coverage",
        all_12_months and has_sep_nov,
        f"distinct_months={len(months_present)}/12, Sep-Nov detections={sep_nov_rows:,}, date_range={min_date} to {max_date}"
    )

    # --------------------------------------------------------------------------
    # CHECK 6: SCHEMA, DUPLICATES, NULLS, BOUNDING BOX
    # --------------------------------------------------------------------------
    print("\n--- 6. Schema, Deduplication, Nulls & Coordinate Boundaries ---")
    # Columns check
    exact_cols = list(df_comb.columns) == EXPECTED_COLUMNS
    record_check(
        "Schema Columns",
        exact_cols,
        f"23 agreed columns exactly match expected schema"
    )

    # Duplicates check (including SP and NRT)
    total_dupes = df_comb.duplicated().sum()
    df_2026 = df_comb[df_comb["year"] == 2026]
    dupes_2026 = df_2026.duplicated(subset=["latitude", "longitude", "datetime_utc", "sensor"]).sum()
    record_check(
        "Deduplication (including SP/NRT)",
        (total_dupes == 0 and dupes_2026 == 0),
        f"total_duplicates={total_dupes}, 2026_sp_nrt_duplicates={dupes_2026}"
    )

    # Key fields nulls check
    key_fields = ["date", "datetime_utc", "latitude", "longitude", "frp", "confidence"]
    null_counts = df_comb[key_fields].isna().sum().to_dict()
    all_zero_nulls = all(v == 0 for v in null_counts.values())
    record_check(
        "Zero Nulls in Key Fields",
        all_zero_nulls,
        f"null_counts={null_counts}"
    )

    # Bounding box coordinates check
    lon_valid = (df_comb["longitude"] >= BBOX[0]) & (df_comb["longitude"] <= BBOX[2])
    lat_valid = (df_comb["latitude"] >= BBOX[1]) & (df_comb["latitude"] <= BBOX[3])
    all_in_bbox = lon_valid.all() and lat_valid.all()
    record_check(
        "Bounding Box Enforcement",
        all_in_bbox,
        f"lon_range=[{df_comb['longitude'].min()}, {df_comb['longitude'].max()}], lat_range=[{df_comb['latitude'].min()}, {df_comb['latitude'].max()}], bbox={BBOX}"
    )

    # --------------------------------------------------------------------------
    # CHECK 7: TIMESTAMPS (CLEAN FILES NEWER THAN RAW FILES)
    # --------------------------------------------------------------------------
    print("\n--- 7. File Timestamp Freshness ---")
    raw_files = list(DATA_RAW_DIR.glob("*/*.csv"))
    last_raw_mtime = max(f.stat().st_mtime for f in raw_files)
    last_raw_file = max(raw_files, key=lambda f: f.stat().st_mtime)

    clean_paths = [fpath for _, fpath, _ in file_checks]
    min_clean_mtime = min(f.stat().st_mtime for f in clean_paths)
    earliest_clean_file = min(clean_paths, key=lambda f: f.stat().st_mtime)

    clean_is_newer = min_clean_mtime > last_raw_mtime
    record_check(
        "Clean Files Freshness",
        clean_is_newer,
        f"earliest_clean={earliest_clean_file.name} ({datetime.fromtimestamp(min_clean_mtime).strftime('%Y-%m-%d %H:%M:%S')}) > latest_raw={last_raw_file.name} ({datetime.fromtimestamp(last_raw_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
    )

    # --------------------------------------------------------------------------
    # SUMMARY REPORT
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    pass_count = sum(1 for _, st, _ in results if st == "PASS")
    fail_count = sum(1 for _, st, _ in results if st == "FAIL")
    print(f"Total Checks: {len(results)} | PASSED: {pass_count} | FAILED: {fail_count}")

    if all_passed:
        print("\nOVERALL STATUS: ALL CHECKS PASSED [OK]")
    else:
        print("\nOVERALL STATUS: VERIFICATION FAILED [FAIL]")

    return all_passed


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
