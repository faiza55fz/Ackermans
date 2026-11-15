import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

def process_palisades(path: str):
    usecols = ["date", "year", "sensor", "latitude", "longitude", "frp", "confidence"]
    df = pd.read_csv(path, usecols=usecols, low_memory=False)
    
    # Palisades AOI: lat 34.0 to 34.2, lon -118.75 to -118.42
    mask = (
        (df["latitude"] >= 34.0) & (df["latitude"] <= 34.2) &
        (df["longitude"] >= -118.75) & (df["longitude"] <= -118.42)
    )
    clipped = df[mask].copy()
    clipped["region"] = "palisades"
    return clipped

def process_western_ghats(path: str):
    usecols = ["date", "year", "sensor", "latitude", "longitude", "frp", "confidence"]
    df = pd.read_csv(path, usecols=usecols, low_memory=False)
    df["region"] = "western_ghats_karnataka"
    return df

def process_punjab_chunks(path: str, chunksize: int = 500000):
    usecols = ["date", "year", "sensor", "latitude", "longitude", "frp", "confidence"]
    chunks = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False):
        chunk["region"] = "punjab_haryana"
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)

def main():
    print("Building yearly trends from raw CSV datasets...")
    
    p_pal = "gis/data/palisades_la_combined.csv"
    p_wg = "gis/data/western_ghats_karnataka_combined.csv"
    p_pun = "gis/data/punjab_haryana_combined.csv"
    
    print(f"1. Loading & clipping Palisades from {p_pal}...")
    pal_df = process_palisades(p_pal)
    print(f"   Palisades kept: {len(pal_df):,} rows")
    
    print(f"2. Loading Western Ghats from {p_wg}...")
    wg_df = process_western_ghats(p_wg)
    print(f"   Western Ghats kept: {len(wg_df):,} rows")
    
    print(f"3. Loading Punjab & Haryana in chunks from {p_pun}...")
    pun_df = process_punjab_chunks(p_pun)
    print(f"   Punjab & Haryana kept: {len(pun_df):,} rows")
    
    combined = pd.concat([pal_df, wg_df, pun_df], ignore_index=True)
    
    # Print row totals per region and sensor
    print("\n" + "=" * 60)
    print("ROW TOTALS PER REGION AND SENSOR:")
    print("=" * 60)
    summary_counts = combined.groupby(["region", "sensor"]).size().unstack(fill_value=0)
    summary_counts["TOTAL"] = summary_counts.sum(axis=1)
    print(summary_counts.to_string())
    print("=" * 60)
    
    # Calculate yearly trends
    combined["frp_num"] = pd.to_numeric(combined["frp"], errors="coerce")
    combined["date_str"] = combined["date"].astype(str).str.slice(0, 10)
    
    grouped = combined.groupby(["region", "year", "sensor"], as_index=False).agg(
        detections=("date_str", "count"),
        active_days=("date_str", "nunique"),
        frp_sum=("frp_num", "sum"),
        frp_valid_count=("frp_num", "count")
    )
    
    # If all frp in a group were NaN, frp_sum should be NaN
    all_nan = grouped["frp_valid_count"] == 0
    grouped.loc[all_nan, "frp_sum"] = np.nan
    grouped["frp_sum"] = grouped["frp_sum"].round(2)
    
    # is_partial_year is True for 2026
    grouped["is_partial_year"] = grouped["year"] == 2026
    
    # Order columns
    output_cols = ["region", "year", "sensor", "detections", "active_days", "frp_sum", "is_partial_year"]
    final_df = grouped[output_cols].sort_values(by=["region", "year", "sensor"]).reset_index(drop=True)
    
    out_path = Path("public/data/yearly_trends.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(final_df)} yearly trend records to {out_path.resolve()}")
    
    print("\nFirst 15 rows of yearly_trends.csv:")
    print(final_df.head(15).to_string(index=False))

if __name__ == "__main__":
    main()
