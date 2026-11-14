#!/usr/bin/env python3
"""
src/checks.py - Sanity checks and verification suite for cleaned FIRMS data.

Verifies:
  1. No null dates or datetimes.
  2. All coordinates inside region bounding box.
  3. No null latitude, longitude, frp, or confidence values.
  4. Non-negative FRP (reports min, median, max).
  5. Valid sensor start dates and no future dates.
  6. Year-over-year counts and volatility flags.
  7. Row count reconciliation (loaded - duplicates - dropped = final).

Outputs markdown report to reports/sanity_<region>.md.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import numpy as np

# ==============================================================================
# NAMED CONSTANTS & THRESHOLDS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_CLEAN_DIR = BASE_DIR / "data" / "clean"
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
REPORTS_DIR = BASE_DIR / "reports"

REGIONS = {
    "palisades_la": {
        "bbox": (-118.75, 33.95, -118.40, 34.20),
        "name": "Pacific Palisades, Los Angeles, USA"
    },
    "nsw_victoria_au": {
        "bbox": (140.9, -39.2, 154.0, -28.1),
        "name": "New South Wales & Victoria, Australia"
    },
    "western_ghats_karnataka": {
        "bbox": (74.0, 13.3, 76.1, 15.8),
        "name": "Western Ghats, Karnataka, India"
    },
    "punjab_haryana": {
        "bbox": (73.8, 27.6, 77.7, 32.6),
        "name": "Punjab & Haryana, India"
    }
}

SENSOR_VALID_BOUNDS = {
    "MODIS": {"min_date": date(2000, 11, 1)},
    "VIIRS": {"min_date": date(2012, 1, 20)}
}

VOLATILITY_FACTOR = 10.0


# ==============================================================================
# SANITY CHECK ENGINE
# ==============================================================================
def run_checks_for_region(region_id: str) -> tuple[bool, str]:
    """
    Execute all sanity checks for a region and write markdown report.
    Returns: (overall_pass: bool, report_markdown: str)
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / f"sanity_{region_id}.md"

    print(f"\n=======================================================")
    print(f"RUNNING SANITY CHECKS FOR: {region_id}")
    print(f"=======================================================")

    combined_file = DATA_CLEAN_DIR / f"{region_id}_combined.parquet"
    if not combined_file.exists():
        msg = f"FAIL: Combined cleaned dataset not found: {combined_file}"
        print(msg)
        return False, msg

    df = pd.read_parquet(combined_file)
    bbox = REGIONS[region_id]["bbox"]
    west, south, east, north = bbox
    today_date = date.today()

    checks = []
    all_pass = True

    # -------------------------------------------------------------------------
    # Check 1: Null Dates or Datetimes
    # -------------------------------------------------------------------------
    null_dates = int(df["date"].isna().sum())
    null_datetimes = int(df["datetime_utc"].isna().sum())
    c1_pass = (null_dates == 0) and (null_datetimes == 0)
    all_pass = all_pass and c1_pass
    checks.append({
        "name": "1. Null Dates or Datetimes",
        "pass": c1_pass,
        "details": f"Null dates: {null_dates:,}, Null datetimes: {null_datetimes:,} (Expected: 0)"
    })

    # -------------------------------------------------------------------------
    # Check 2: Coordinates within Bounding Box
    # -------------------------------------------------------------------------
    # Floating-point coordinate tolerance for pixel edge rounding (1e-4 deg ~ 10m)
    EPSILON = 1e-4
    lon_cond = (df["longitude"] >= west - EPSILON) & (df["longitude"] <= east + EPSILON)
    lat_cond = (df["latitude"] >= south - EPSILON) & (df["latitude"] <= north + EPSILON)
    inside_mask = lon_cond & lat_cond
    outside_count = int((~inside_mask).sum())
    c2_pass = (outside_count == 0)
    all_pass = all_pass and c2_pass

    outside_samples = []
    if outside_count > 0:
        df_outside = df[~inside_mask].copy()
        outside_file = DATA_CLEAN_DIR / f"outside_bbox_{region_id}.parquet"
        df_outside.to_parquet(outside_file, index=False)
        date_col = "date" if "date" in df_outside.columns else ("acq_date" if "acq_date" in df_outside.columns else "datetime_utc")
        outside_samples = df_outside[["latitude", "longitude", date_col, "sensor"]].head(5).to_dict(orient="records")

    checks.append({
        "name": "2. Bounding Box Coordinates",
        "pass": c2_pass,
        "details": f"Outside bbox count: {outside_count:,} (BBox: west={west}, south={south}, east={east}, north={north})"
    })

    # -------------------------------------------------------------------------
    # Check 3: Null Essential Fields
    # -------------------------------------------------------------------------
    null_lats = int(df["latitude"].isna().sum())
    null_lons = int(df["longitude"].isna().sum())
    null_frp = int(df["frp"].isna().sum())
    null_conf = int(df["confidence"].isna().sum())
    c3_pass = (null_lats == 0) and (null_lons == 0) and (null_frp == 0) and (null_conf == 0)
    all_pass = all_pass and c3_pass
    checks.append({
        "name": "3. Null Essential Fields",
        "pass": c3_pass,
        "details": f"Null lat: {null_lats}, lon: {null_lons}, frp: {null_frp}, confidence: {null_conf} (Expected: all 0)"
    })

    # -------------------------------------------------------------------------
    # Check 4: FRP Values & Non-Negativity
    # -------------------------------------------------------------------------
    neg_frp = int((df["frp"] < 0).sum())
    frp_min = float(df["frp"].min()) if len(df) > 0 else 0.0
    frp_median = float(df["frp"].median()) if len(df) > 0 else 0.0
    frp_max = float(df["frp"].max()) if len(df) > 0 else 0.0
    c4_pass = (neg_frp == 0) and (frp_min >= 0.0)
    all_pass = all_pass and c4_pass
    checks.append({
        "name": "4. Non-negative Fire Radiative Power (FRP)",
        "pass": c4_pass,
        "details": f"Negative FRP count: {neg_frp} (Expected: 0). FRP Min: {frp_min:.2f}, Median: {frp_median:.2f}, Max: {frp_max:.2f}"
    })

    # -------------------------------------------------------------------------
    # Check 5: Sensor Operational Date Ranges
    # -------------------------------------------------------------------------
    c5_pass = True
    sensor_ranges = {}
    for sens, bounds in SENSOR_VALID_BOUNDS.items():
        df_sens = df[df["sensor"] == sens]
        if len(df_sens) > 0:
            s_min = df_sens["date"].min()
            s_max = df_sens["date"].max()
            valid_start = s_min >= bounds["min_date"]
            valid_end = s_max <= today_date
            sens_pass = valid_start and valid_end
            c5_pass = c5_pass and sens_pass
            sensor_ranges[sens] = {
                "first_date": str(s_min),
                "last_date": str(s_max),
                "expected_min": str(bounds["min_date"]),
                "pass": sens_pass
            }
        else:
            sensor_ranges[sens] = {"first_date": "None", "last_date": "None", "pass": True}

    all_pass = all_pass and c5_pass
    checks.append({
        "name": "5. Sensor Operational Date Ranges",
        "pass": c5_pass,
        "details": "; ".join([f"{k}: {v['first_date']} to {v['last_date']} (Pass: {v['pass']})" for k, v in sensor_ranges.items()])
    })

    # -------------------------------------------------------------------------
    # Check 6: Year-over-Year Counts & Volatility Flags
    # -------------------------------------------------------------------------
    counts_table = df.groupby(["year", "sensor"]).size().unstack(fill_value=0)
    # Ensure all years between min and max exist
    if len(df) > 0:
        full_years = range(df["year"].min(), df["year"].max() + 1)
        counts_table = counts_table.reindex(full_years, fill_value=0)

    volatility_flags = []
    for sens in counts_table.columns:
        counts = counts_table[sens].tolist()
        years = counts_table.index.tolist()
        for i in range(len(years)):
            yr = years[i]
            cnt = counts[i]
            if cnt == 0:
                volatility_flags.append(f"Zero detections in {yr} for {sens}")
            if i > 0 and counts[i-1] > 0 and cnt > 0:
                prev = counts[i-1]
                ratio = cnt / prev
                if ratio >= VOLATILITY_FACTOR:
                    volatility_flags.append(f"High surge in {yr} for {sens}: {cnt:,} (vs {prev:,} in {years[i-1]}, ratio {ratio:.1f}x)")
                elif ratio <= (1.0 / VOLATILITY_FACTOR):
                    volatility_flags.append(f"Steep drop in {yr} for {sens}: {cnt:,} (vs {prev:,} in {years[i-1]}, ratio {ratio:.2f}x)")

    checks.append({
        "name": "6. Yearly Counts & Volatility Review",
        "pass": True,  # Flags are for review
        "details": f"{len(volatility_flags)} review flag(s) identified."
    })

    # -------------------------------------------------------------------------
    # Check 7: Row Count Reconciliation
    # -------------------------------------------------------------------------
    # Load raw files count, duplicates dropped, and low confidence dropped
    reconciliation = {}
    c7_pass = True
    for sens in ["MODIS", "VIIRS"]:
        raw_dir = DATA_RAW_DIR / region_id / sens
        raw_rows = 0
        if raw_dir.exists():
            for f in raw_dir.glob("*.csv"):
                try:
                    df_r = pd.read_csv(f)
                    raw_rows += len(df_r)
                except Exception:
                    pass

        dropped_file = DATA_CLEAN_DIR / f"dropped_low_confidence_{region_id}_{sens}.csv"
        dropped_rows = 0
        if dropped_file.exists():
            try:
                df_dr = pd.read_csv(dropped_file)
                dropped_rows = len(df_dr)
            except Exception:
                pass

        clean_sens_file = DATA_CLEAN_DIR / f"{region_id}_{sens}.parquet"
        clean_sens_rows = len(pd.read_parquet(clean_sens_file)) if clean_sens_file.exists() else 0

        # Raw rows minus deduplication and confidence drop
        # Read raw concat to check exact deduplication
        raw_dfs = [pd.read_csv(f) for f in raw_dir.glob("*.csv") if f.stat().st_size > 0]
        if raw_dfs:
            df_raw_all = pd.concat(raw_dfs, ignore_index=True)
            dup_count = len(df_raw_all) - len(df_raw_all.drop_duplicates())
        else:
            dup_count = 0

        expected_clean = raw_rows - dup_count - dropped_rows
        match = (clean_sens_rows == expected_clean)
        c7_pass = c7_pass and match

        reconciliation[sens] = {
            "raw_loaded": raw_rows,
            "duplicates": dup_count,
            "low_confidence_dropped": dropped_rows,
            "clean_rows": clean_sens_rows,
            "reconciled": match
        }

    all_pass = all_pass and c7_pass
    checks.append({
        "name": "7. Row Count Reconciliation",
        "pass": c7_pass,
        "details": "; ".join([f"{s}: loaded={r['raw_loaded']}, dups={r['duplicates']}, low_conf={r['low_confidence_dropped']} -> clean={r['clean_rows']} (Match: {r['reconciled']})" for s, r in reconciliation.items()])
    })

    # -------------------------------------------------------------------------
    # BUILD MARKDOWN REPORT
    # -------------------------------------------------------------------------
    md_lines = [
        f"# Sanity Check Report: {region_id}",
        f"**Region Name:** {REGIONS[region_id]['name']}  ",
        f"**Bounding Box:** west={west}, south={south}, east={east}, north={north}  ",
        f"**Execution Date:** {today_date.strftime('%Y-%m-%d')}  ",
        f"**Overall Status:** **{'PASS' if all_pass else 'FAIL'}**\n",
        "## Summary of Checks",
        "| Check | Status | Details |",
        "|---|:---:|---|"
    ]

    for c in checks:
        st = "PASS" if c["pass"] else "FAIL"
        md_lines.append(f"| {c['name']} | **{st}** | {c['details']} |")

    md_lines.append("\n## Detections Per Year by Sensor")
    md_lines.append(counts_table.to_markdown())

    if volatility_flags:
        md_lines.append("\n## Year-over-Year Volatility & Inactive Flags")
        for fl in volatility_flags:
            md_lines.append(f"- {fl}")

    if outside_samples:
        md_lines.append("\n## Detections Outside Bounding Box (Samples)")
        md_lines.append(pd.DataFrame(outside_samples).to_markdown(index=False))

    md_lines.append("\n## Row Count Reconciliation Details")
    for s, r in reconciliation.items():
        md_lines.append(f"- **{s}**: Raw Loaded = `{r['raw_loaded']:,}`, Duplicates Dropped = `{r['duplicates']:,}`, Low-Confidence Dropped = `{r['low_confidence_dropped']:,}`, Clean Rows = `{r['clean_rows']:,}`. Reconciled: **{'PASS' if r['reconciled'] else 'FAIL'}**")

    report_markdown = "\n".join(md_lines)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    print(f"\nSanity Check Results for {region_id}:")
    for c in checks:
        st = "[PASS]" if c["pass"] else "[FAIL]"
        print(f"  {st:8} {c['name']}: {c['details']}")
    print(f"\n>> Report saved to: {report_file}")
    print(f">> Overall Result: {'PASS' if all_pass else 'FAIL'}")

    return all_pass, report_markdown


# ==============================================================================
# CLI ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Run sanity checks on cleaned FIRMS datasets.")
    parser.add_argument("--region", choices=list(REGIONS.keys()) + ["all"], default="palisades_la",
                        help="Region identifier or 'all'")
    parser.add_argument("--all", action="store_true", help="Check all configured regions")

    args = parser.parse_args()
    target_regions = list(REGIONS.keys()) if (args.all or args.region == "all") else [args.region]

    global_pass = True
    for reg in target_regions:
        passed, _ = run_checks_for_region(reg)
        if not passed:
            global_pass = False

    if not global_pass:
        print("\n[ALERT] One or more sanity checks FAILED.", file=sys.stderr)
        sys.exit(1)
    else:
        print("\n[SUCCESS] All sanity checks PASSED.")


if __name__ == "__main__":
    main()
