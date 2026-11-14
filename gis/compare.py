import os
import sys
import time
import argparse
import tracemalloc
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np

try:
    from .grid import assign_grid
    from .export_geojson import resolve_input_csv
except ImportError:
    from grid import assign_grid
    from export_geojson import resolve_input_csv


def compare_sensors_by_day(
    df: pd.DataFrame,
    cell_size: float = 0.01
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Perform same-day cell-level comparison between MODIS and VIIRS sensors.

    Conditions:
    - Filters to dates >= '2012-01-01' (when both sensors were operational).
    - Identifies unique (cell_id, date) pairs per sensor.
    - Determines for each cell-day whether MODIS, VIIRS, or both detected hotspots.

    Parameters:
    -----------
    df : pd.DataFrame
        Hotspot DataFrame with 'date', 'sensor', and coordinate columns.
    cell_size : float, optional (default=0.01)
        Spatial cell resolution in degrees.

    Returns:
    --------
    Tuple[pd.DataFrame, Dict[str, Any]]:
        - cell_day_df: DataFrame of unique (cell_id, date) with boolean columns
          'modis_detected', 'viirs_detected', and 'category' ('modis_only', 'viirs_only', 'both').
        - summary: Dictionary with total counts and agreement shares.
    """
    work_df = df.copy()

    # Assign spatial grid if not present
    if "cell_id" not in work_df.columns:
        work_df = assign_grid(work_df, cell_size=cell_size)

    # Standardize date format YYYY-MM-DD
    work_df["date_str"] = pd.to_datetime(work_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Filter to 2012-01-01 onward
    filtered_df = work_df[work_df["date_str"] >= "2012-01-01"].copy()

    # Extract unique (cell_id, date) pairs per sensor
    modis_pairs = (
        filtered_df[filtered_df["sensor"].str.upper() == "MODIS"][["cell_id", "date_str"]]
        .drop_duplicates()
        .rename(columns={"date_str": "date"})
    )
    modis_pairs["modis_detected"] = True

    viirs_pairs = (
        filtered_df[filtered_df["sensor"].str.upper() == "VIIRS"][["cell_id", "date_str"]]
        .drop_duplicates()
        .rename(columns={"date_str": "date"})
    )
    viirs_pairs["viirs_detected"] = True

    # Outer join to capture all cell-days across both sensors
    merged = pd.merge(modis_pairs, viirs_pairs, on=["cell_id", "date"], how="outer")
    merged["modis_detected"] = merged["modis_detected"].eq(True)
    merged["viirs_detected"] = merged["viirs_detected"].eq(True)

    # Determine agreement category
    conditions = [
        (merged["modis_detected"] & ~merged["viirs_detected"]),
        (~merged["modis_detected"] & merged["viirs_detected"]),
        (merged["modis_detected"] & merged["viirs_detected"]),
    ]
    choices = ["modis_only", "viirs_only", "both"]
    merged["category"] = np.select(conditions, choices, default="none")

    # Compute overall summary
    modis_only_cnt = int((merged["category"] == "modis_only").sum())
    viirs_only_cnt = int((merged["category"] == "viirs_only").sum())
    both_cnt = int((merged["category"] == "both").sum())
    total_modis = int(merged["modis_detected"].sum())
    total_viirs = int(merged["viirs_detected"].sum())
    total_cell_days = len(merged)

    share_modis_seen_by_viirs = both_cnt / total_modis if total_modis > 0 else 0.0

    summary = {
        "modis_only": modis_only_cnt,
        "viirs_only": viirs_only_cnt,
        "both": both_cnt,
        "total_modis_cell_days": total_modis,
        "total_viirs_cell_days": total_viirs,
        "total_cell_days": total_cell_days,
        "share_modis_seen_by_viirs": share_modis_seen_by_viirs,
    }

    return merged, summary


def compute_sensor_agreement(
    df: pd.DataFrame,
    cell_size: float = 0.01,
    output_csv: Optional[str] = None,
    region: str = "palisades"
) -> pd.DataFrame:
    """
    Compute sensor agreement per year and day/night period (daynight column).
    """
    work_df = df.copy()

    if "cell_id" not in work_df.columns:
        work_df = assign_grid(work_df, cell_size=cell_size)

    dates = pd.to_datetime(work_df["date"], errors="coerce")
    work_df["date_str"] = dates.dt.strftime("%Y-%m-%d")
    work_df["year"] = dates.dt.year

    if "daynight" in work_df.columns:
        work_df["daynight"] = work_df["daynight"].fillna("Unknown").astype(str).str.upper()
    else:
        work_df["daynight"] = "Unknown"

    filtered_df = work_df[work_df["date_str"] >= "2012-01-01"].copy()

    modis = (
        filtered_df[filtered_df["sensor"].str.upper() == "MODIS"][
            ["cell_id", "date_str", "year", "daynight"]
        ]
        .drop_duplicates()
        .rename(columns={"date_str": "date"})
    )
    modis["modis"] = True

    viirs = (
        filtered_df[filtered_df["sensor"].str.upper() == "VIIRS"][
            ["cell_id", "date_str", "year", "daynight"]
        ]
        .drop_duplicates()
        .rename(columns={"date_str": "date"})
    )
    viirs["viirs"] = True

    merged = pd.merge(modis, viirs, on=["cell_id", "date", "year", "daynight"], how="outer")
    merged["modis"] = merged["modis"].eq(True)
    merged["viirs"] = merged["viirs"].eq(True)

    merged["modis_only"] = (merged["modis"] & ~merged["viirs"]).astype(int)
    merged["viirs_only"] = (~merged["modis"] & merged["viirs"]).astype(int)
    merged["both"] = (merged["modis"] & merged["viirs"]).astype(int)

    summary_df = (
        merged.groupby(["year", "daynight"], as_index=False)[["modis_only", "viirs_only", "both"]]
        .sum()
        .sort_values(by=["year", "daynight"])
        .reset_index(drop=True)
    )

    if not output_csv:
        output_csv = f"gis/output/{region}_sensor_agreement.csv"
        if region in ["palisades", "palisades_la"]:
            output_csv = "gis/output/sensor_agreement.csv"

    out_p = Path(output_csv)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_p, index=False)
    print(f"Saved sensor agreement table to: {out_p.resolve()}")

    return summary_df


def main():
    parser = argparse.ArgumentParser(description="Region-aware sensor comparison and agreement analysis.")
    parser.add_argument("--region", type=str, default="palisades", help="Region name")
    parser.add_argument("--input", type=str, default=None, help="Input CSV path")
    parser.add_argument("--output", type=str, default=None, help="Output CSV path")
    parser.add_argument("--cell-size", type=float, default=0.01, help="Cell size in degrees")

    args = parser.parse_args()
    p_csv = resolve_input_csv(args.region, args.input)

    tracemalloc.start()
    t_start = time.time()

    print(f"Loading data for region '{args.region}' from: {p_csv}")
    use_cols = ["latitude", "longitude", "date", "sensor", "daynight"]
    df = pd.read_csv(p_csv, usecols=lambda c: c in use_cols, low_memory=False)

    print(f"\nRunning compare_sensors_by_day (2012-2026) for {args.region.upper()} (cell_size={args.cell_size}°)...")
    cell_day_df, summary = compare_sensors_by_day(df, cell_size=args.cell_size)

    print("\n" + "=" * 65)
    print(f"SAME-DAY SENSOR COMPARISON: {args.region.upper()} (2012 - 2026)")
    print("=" * 65)
    print(f"Total Unique Cell-Days Analyzed : {summary['total_cell_days']:,}")
    print(f"  - MODIS only                  : {summary['modis_only']:,} cell-days ({summary['modis_only']/summary['total_cell_days']*100:.1f}%)")
    print(f"  - VIIRS only                  : {summary['viirs_only']:,} cell-days ({summary['viirs_only']/summary['total_cell_days']*100:.1f}%)")
    print(f"  - Both sensors on same day    : {summary['both']:,} cell-days ({summary['both']/summary['total_cell_days']*100:.1f}%)")
    print(f"\nMODIS Recovery Rate:")
    print(f"  - Total MODIS cell-days       : {summary['total_modis_cell_days']:,}")
    print(f"  - Also detected by VIIRS      : {summary['both']:,} ({summary['share_modis_seen_by_viirs']*100:.2f}%)")
    print("=" * 65)

    print("\nComputing breakdown by year and daynight...")
    agreement_df = compute_sensor_agreement(df, cell_size=args.cell_size, output_csv=args.output, region=args.region)

    t_end = time.time()
    total_time = t_end - t_start
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\nExecution stats: Run time = {total_time:.2f}s | Peak Memory = {peak_mem / (1024*1024):.1f} MB")
    print("\nFirst 10 rows of sensor_agreement.csv:")
    print(agreement_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
