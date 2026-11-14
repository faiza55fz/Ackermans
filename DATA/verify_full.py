#!/usr/bin/env python3
"""
verify_full.py - Comprehensive independent verification of FIRMS raw & clean data.

Recomputes all metrics directly from data/raw/ without importing ingest.py logic,
and verifies schema, deduplication, confidence filtering, date ranges, file timestamps,
and window completeness against the download manifests and clean outputs.
Supports CLI flag: --region <region_id> (default: western_ghats_karnataka).
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
DATA_CLEAN_DIR = BASE_DIR / "data" / "clean"
DATA_CLEAN_CSV_DIR = DATA_CLEAN_DIR / "csv"
LOGS_DIR = BASE_DIR / "logs"

REGIONS = {
    "palisades_la": {
        "name": "Pacific Palisades, Los Angeles, USA",
        "bbox": (-118.75, 33.95, -118.40, 34.20)
    },
    "western_ghats_karnataka": {
        "name": "Western Ghats, Karnataka, India",
        "bbox": (74.0, 13.3, 76.1, 15.8)
    },
    "punjab_haryana": {
        "name": "Punjab & Haryana, India",
        "bbox": (73.8, 27.6, 77.7, 32.6)
    },
    "nsw_victoria_au": {
        "name": "New South Wales & Victoria, Australia",
        "bbox": (140.9, -39.2, 154.0, -28.1)
    }
}

TODAY = date(2026, 11, 14)

EXPECTED_COLUMNS = [
    "region", "sensor", "satellite", "processing", "datetime_utc", "date", "year",
    "latitude", "longitude", "confidence", "confidence_class", "frp", "daynight",
    "scan", "track", "instrument", "version", "brightness", "bright_t31",
    "bright_ti4", "bright_ti5", "type", "is_vegetation_fire"
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


def run_verification(region: str = "western_ghats_karnataka") -> bool:
    print("=" * 80)
    print(f"INDEPENDENT FULL-PIPELINE VERIFICATION FOR {region.upper()}")
    print("=" * 80)

    bbox = REGIONS[region]["bbox"]
    raw_dir = BASE_DIR / "data" / "raw" / region

    streams = [
        {
            "name": "MODIS (Terra & Aqua)",
            "sensor": "MODIS",
            "stream_id": "MODIS",
            "start_date": date(2000, 11, 1),
            "end_date": TODAY,
            "manifest_path": raw_dir / "MODIS" / ".download_manifest.json"
        },
        {
            "name": "VIIRS NOAA-21",
            "sensor": "VIIRS",
            "stream_id": "VIIRS_NOAA21",
            "start_date": date(2023, 3, 1),
            "end_date": TODAY,
            "manifest_path": raw_dir / "VIIRS" / ".download_manifest.json"
        },
        {
            "name": "VIIRS NOAA-20",
            "sensor": "VIIRS",
            "stream_id": "VIIRS_NOAA20",
            "start_date": date(2018, 4, 1),
            "end_date": TODAY,
            "manifest_path": raw_dir / "VIIRS" / ".download_manifest.json"
        },
        {
            "name": "VIIRS S-NPP",
            "sensor": "VIIRS",
            "stream_id": "VIIRS_SNPP",
            "start_date": date(2012, 1, 20),
            "end_date": date(2026, 11, 2),
            "manifest_path": raw_dir / "VIIRS" / ".download_manifest.json"
        }
    ]

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

    for stream in streams:
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
    reg_fails_count = 0
    if failures_file.exists():
        df_fails = pd.read_csv(failures_file)
        for _, row in df_fails.iterrows():
            reg = str(row.get("region", "")).strip()
            if reg != region:
                continue
            reg_fails_count += 1
            s = str(row.get("sensor", "")).strip()
            sd = str(row.get("start_date", "")).strip()
            m_path = (raw_dir / "MODIS" / ".download_manifest.json") if s == "MODIS" else (raw_dir / "VIIRS" / ".download_manifest.json")
            m_data = manifest_cache.get(m_path, {})
            cw = set(m_data.get("completed_windows", []))
            matching = [w for w in cw if f"_{sd}_" in w]
            if not matching:
                unresolved.append(f"{reg}/{s}/{sd}")

    record_check(
        "Unresolved Failures Log",
        len(unresolved) == 0,
        f"{len(unresolved)} unresolved windows out of {reg_fails_count} logged entries for {region}"
    )

    # --------------------------------------------------------------------------
    # CHECK 3: INDEPENDENT RECOMPUTATION FROM DATA/RAW/
    # --------------------------------------------------------------------------
    print("\n--- 3. Independent Raw Recomputation vs Cleaned Files ---")
    # MODIS recomputation
    modis_files = sorted((raw_dir / "MODIS").glob("*.csv"))
    modis_dfs = [pd.read_csv(f, low_memory=False) for f in modis_files]
    df_m_raw = pd.concat([d for d in modis_dfs if len(d) > 0], ignore_index=True) if modis_dfs else pd.DataFrame()
    m_raw_count = len(df_m_raw)

    m_dedup = df_m_raw.drop_duplicates().copy()
    m_dup_dropped = m_raw_count - len(m_dedup)

    m_conf = pd.to_numeric(m_dedup["confidence"], errors="coerce")
    m_low_dropped = len(m_dedup[m_conf < 30])
    m_final = len(m_dedup[(m_conf >= 30) & (m_conf <= 100)])

    # Read clean MODIS file to compare
    clean_modis_parquet = DATA_CLEAN_DIR / f"{region}_MODIS.parquet"
    df_clean_modis = pd.read_parquet(clean_modis_parquet)
    m_matches = (m_final == len(df_clean_modis))
    record_check(
        "MODIS Row Accounting Reconciliation",
        m_matches,
        f"raw_loaded={m_raw_count} - dups={m_dup_dropped} - low_conf={m_low_dropped} = final={m_final} (clean_file={len(df_clean_modis)})"
    )

    # VIIRS recomputation
    viirs_files = sorted((raw_dir / "VIIRS").glob("*.csv"))
    viirs_dfs = [pd.read_csv(f, low_memory=False) for f in viirs_files]
    df_v_raw = pd.concat([d for d in viirs_dfs if len(d) > 0], ignore_index=True) if viirs_dfs else pd.DataFrame()
    v_raw_count = len(df_v_raw)

    v_dedup = df_v_raw.drop_duplicates().copy()
    v_dup_dropped = v_raw_count - len(v_dedup)

    v_conf = v_dedup["confidence"].astype(str).str.strip().str.lower()
    v_low_dropped = len(v_dedup[v_conf == "l"])
    v_final = len(v_dedup[v_conf.isin(["n", "h"])])

    clean_viirs_parquet = DATA_CLEAN_DIR / f"{region}_VIIRS.parquet"
    df_clean_viirs = pd.read_parquet(clean_viirs_parquet)
    v_matches = (v_final == len(df_clean_viirs))
    record_check(
        "VIIRS Row Accounting Reconciliation",
        v_matches,
        f"raw_loaded={v_raw_count} - dups={v_dup_dropped} - low_conf={v_low_dropped} = final={v_final} (clean_file={len(df_clean_viirs)})"
    )

    combined_expected = m_final + v_final
    clean_comb_parquet = DATA_CLEAN_DIR / f"{region}_combined.parquet"
    df_clean_comb = pd.read_parquet(clean_comb_parquet)
    comb_matches = (combined_expected == len(df_clean_comb))
    record_check(
        "Combined Total Clean Rows",
        comb_matches,
        f"clean_total={len(df_clean_comb)} (MODIS {m_final} + VIIRS {v_final}, expected {combined_expected})"
    )

    # --------------------------------------------------------------------------
    # CHECK 4: CLEANED FILES EXISTENCE & ROW COUNTS (PARQUET & CSV)
    # --------------------------------------------------------------------------
    print("\n--- 4. Clean File Formats & Row Count Parity ---")
    file_checks = [
        (f"{region}_MODIS.parquet", clean_modis_parquet, m_final),
        (f"{region}_MODIS.csv", DATA_CLEAN_CSV_DIR / f"{region}_MODIS.csv", m_final),
        (f"{region}_VIIRS.parquet", clean_viirs_parquet, v_final),
        (f"{region}_VIIRS.csv", DATA_CLEAN_CSV_DIR / f"{region}_VIIRS.csv", v_final),
        (f"{region}_combined.parquet", clean_comb_parquet, combined_expected),
        (f"{region}_combined.csv", DATA_CLEAN_CSV_DIR / f"{region}_combined.csv", combined_expected),
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
            f"rows={len(df_read):,} (expected {exp_rows:,}), cols={len(df_read.columns)} (expected 23)"
        )

    # --------------------------------------------------------------------------
    # CHECK 5: FULL-YEAR COVERAGE & DETECTION TABLE
    # --------------------------------------------------------------------------
    print("\n--- 5. Full-Year Coverage & Seasonality ---")
    dates_series = pd.to_datetime(df_clean_comb["date"])
    min_date = df_clean_comb["date"].min()
    max_date = df_clean_comb["date"].max()

    months_present = set(dates_series.dt.month.unique())
    record_check(
        "Full-Year Months Coverage",
        len(months_present) == 12,
        f"distinct_months={len(months_present)}/12, date_range={min_date} to {max_date}"
    )

    # Print Year-by-Month detection summary
    print("\nYear-by-Month Detection Distribution (Cleaned Data):")
    df_clean_comb["month"] = dates_series.dt.month
    ym_table = df_clean_comb.groupby(["year", "month"]).size().unstack(fill_value=0)
    print(ym_table.to_string())

    # --------------------------------------------------------------------------
    # CHECK 6: SCHEMA, DUPLICATES, NULLS, BOUNDING BOX, FRP
    # --------------------------------------------------------------------------
    print("\n--- 6. Schema, Deduplication, Nulls & Coordinate Boundaries ---")
    exact_cols = list(df_clean_comb.columns[:23]) == EXPECTED_COLUMNS
    record_check(
        "Schema Columns",
        exact_cols,
        "23 agreed columns match expected schema"
    )

    total_dupes = df_clean_comb.duplicated().sum()
    df_2026 = df_clean_comb[df_clean_comb["year"] == 2026]
    dupes_2026 = df_2026.duplicated(subset=["latitude", "longitude", "datetime_utc", "sensor"]).sum()
    record_check(
        "Deduplication (including SP/NRT)",
        (total_dupes == 0 and dupes_2026 == 0),
        f"total_duplicates={total_dupes}, 2026_sp_nrt_duplicates={dupes_2026}"
    )

    key_fields = ["date", "datetime_utc", "latitude", "longitude", "frp", "confidence"]
    null_counts = df_clean_comb[key_fields].isna().sum().to_dict()
    all_zero_nulls = all(v == 0 for v in null_counts.values())
    record_check(
        "Zero Nulls in Key Fields",
        all_zero_nulls,
        f"null_counts={null_counts}"
    )

    # Bounding box coordinates with float tolerance (1e-4)
    eps = 1e-4
    lon_valid = (df_clean_comb["longitude"] >= bbox[0] - eps) & (df_clean_comb["longitude"] <= bbox[2] + eps)
    lat_valid = (df_clean_comb["latitude"] >= bbox[1] - eps) & (df_clean_comb["latitude"] <= bbox[3] + eps)
    all_in_bbox = lon_valid.all() and lat_valid.all()
    record_check(
        "Bounding Box Enforcement",
        all_in_bbox,
        f"lon_range=[{df_clean_comb['longitude'].min()}, {df_clean_comb['longitude'].max()}], lat_range=[{df_clean_comb['latitude'].min()}, {df_clean_comb['latitude'].max()}], bbox={bbox}"
    )

    frp_min = df_clean_comb["frp"].min()
    record_check(
        "Non-negative FRP",
        frp_min >= 0,
        f"min_frp={frp_min:.2f}"
    )

    # --------------------------------------------------------------------------
    # CHECK 7: TIMESTAMPS (CLEAN FILES NEWER THAN RAW FILES)
    # --------------------------------------------------------------------------
    print("\n--- 7. File Timestamp Freshness ---")
    raw_files = list(raw_dir.glob("*/*.csv"))
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
    # SENSOR & SATELLITE DETAILS
    # --------------------------------------------------------------------------
    print("\n--- 8. Operational Details & SP/NRT Breakdown ---")
    for s_name, df_s in [("MODIS", df_clean_modis), ("VIIRS", df_clean_viirs)]:
        print(f"\n{s_name}:")
        print(f"  First detection: {df_s['date'].min()} | Last detection: {df_s['date'].max()}")
        sat_counts = df_s.groupby("satellite").size().to_dict()
        print(f"  Satellites: {sat_counts}")
        proc_counts = df_s.groupby("processing").size().to_dict()
        print(f"  Processing streams: {proc_counts}")
        if "NRT" in proc_counts and proc_counts["NRT"] > 0:
            sp_max = df_s[df_s["processing"] == "SP"]["date"].max()
            nrt_min = df_s[df_s["processing"] == "NRT"]["date"].min()
            print(f"  SP/NRT Switch Date: SP max={sp_max}, NRT min={nrt_min}")

    # --------------------------------------------------------------------------
    # YEAR-OVER-YEAR VOLATILITY REVIEW
    # --------------------------------------------------------------------------
    print("\n--- 9. Year-Over-Year Detection Volatility (>10x or <0.1x) ---")
    for s_name, df_s in [("MODIS", df_clean_modis), ("VIIRS", df_clean_viirs)]:
        yearly = df_s.groupby("year").size().sort_index()
        prev_yr, prev_val = None, None
        flags = []
        for yr, val in yearly.items():
            if prev_val is not None and prev_val > 0:
                ratio = val / prev_val
                if ratio > 10.0 or ratio < 0.1:
                    flags.append(f"Year {yr} ({val:,}) vs {prev_yr} ({prev_val:,}) [Ratio: {ratio:.2f}x]")
            prev_yr, prev_val = yr, val
        print(f"  {s_name} Volatility review flags: {len(flags)}")
        for fl in flags:
            print(f"    * {fl}")

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY FOR {region.upper()}")
    print("=" * 80)
    pass_count = sum(1 for _, st, _ in results if st == "PASS")
    fail_count = sum(1 for _, st, _ in results if st == "FAIL")
    print(f"Total Checks: {len(results)} | PASSED: {pass_count} | FAILED: {fail_count}")

    if all_passed:
        print(f"\nOVERALL STATUS FOR {region.upper()}: ALL CHECKS PASSED [OK]")
    else:
        print(f"\nOVERALL STATUS FOR {region.upper()}: VERIFICATION FAILED [FAIL]")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Independent verification of clean fire data.")
    parser.add_argument("--region", default="western_ghats_karnataka", choices=list(REGIONS.keys()))
    args = parser.parse_args()
    success = run_verification(args.region)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
