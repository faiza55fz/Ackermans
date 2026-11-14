import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

try:
    from .grid import assign_grid, cell_to_polygon
    from .aoi import clip_to_aoi, get_aoi_bbox
    from .aggregate import aggregate_by_cell
except ImportError:
    from grid import assign_grid, cell_to_polygon
    from aoi import clip_to_aoi, get_aoi_bbox
    from aggregate import aggregate_by_cell


def export_cells_to_geojson(
    agg_df: pd.DataFrame,
    output_path: Union[str, Path],
    cell_size: float = 0.01,
    coord_precision: int = 5
) -> gpd.GeoDataFrame:
    """
    Save aggregated cells as GeoJSON squares with specified properties.
    Coordinates are rounded to coord_precision (default 5 decimals).
    NaN values are automatically serialized as JSON 'null'.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    df = agg_df.copy()
    if "cell_x" not in df.columns or "cell_y" not in df.columns:
        coords = df["cell_id"].str.split("_", expand=True)
        df["cell_x"] = coords[0].astype(int)
        df["cell_y"] = coords[1].astype(int)

    # Fast cached geometry construction for unique cells
    unique_cells = df[["cell_x", "cell_y"]].drop_duplicates()
    geom_map = {
        (int(cx), int(cy)): box(
            round(cx * cell_size, coord_precision),
            round(cy * cell_size, coord_precision),
            round((cx + 1) * cell_size, coord_precision),
            round((cy + 1) * cell_size, coord_precision),
        )
        for cx, cy in zip(unique_cells["cell_x"], unique_cells["cell_y"])
    }
    geometries = [geom_map[(int(cx), int(cy))] for cx, cy in zip(df["cell_x"], df["cell_y"])]

    # Exclude helper coordinate columns from properties if desired
    exclude_cols = {"cell_x", "cell_y", "geometry"}
    prop_cols = [c for c in df.columns if c not in exclude_cols]

    gdf = gpd.GeoDataFrame(df[prop_cols], geometry=geometries, crs="EPSG:4326")
    gdf.to_file(out_file, driver="GeoJSON")

    file_size_bytes = out_file.stat().st_size
    size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB" if file_size_bytes >= 1024 * 1024 else f"{file_size_bytes / 1024:.1f} KB"
    print(f"Exported {len(gdf):,} features to {out_file.resolve()} ({size_str})")
    return gdf


def export_totals(
    gridded_df: pd.DataFrame,
    output_path: Union[str, Path],
    cell_size: float = 0.01,
    coord_precision: int = 5
) -> gpd.GeoDataFrame:
    """
    Export one feature per cell with total count, days, and FRP metrics per sensor over all time.
    """
    work = gridded_df.copy()
    work["date_str"] = pd.to_datetime(work["date"]).dt.strftime("%Y-%m-%d")
    work["frp_numeric"] = pd.to_numeric(work["frp"], errors="coerce")
    work["frp_missing"] = work["frp_numeric"].isna().astype(int)

    # 1. Overall cell aggregates
    overall = work.groupby(["cell_id", "cell_x", "cell_y"], as_index=False).agg(
        count=("date_str", "count"),
        days=("date_str", "nunique"),
        frp_sum=("frp_numeric", "sum"),
        frp_missing_count=("frp_missing", "sum")
    )
    all_missing = overall["frp_missing_count"] == overall["count"]
    overall.loc[all_missing, "frp_sum"] = np.nan
    overall["frp_sum"] = overall["frp_sum"].round(2)

    # 2. MODIS breakdown
    modis_df = work[work["sensor"].str.upper() == "MODIS"]
    if not modis_df.empty:
        modis_agg = modis_df.groupby("cell_id", as_index=False).agg(
            modis_count=("date_str", "count"),
            modis_days=("date_str", "nunique"),
            modis_frp_sum=("frp_numeric", "sum"),
            modis_frp_missing=("frp_missing", "sum")
        )
        m_all_missing = modis_agg["modis_frp_missing"] == modis_agg["modis_count"]
        modis_agg.loc[m_all_missing, "modis_frp_sum"] = np.nan
        modis_agg["modis_frp_sum"] = modis_agg["modis_frp_sum"].round(2)
        modis_agg = modis_agg.drop(columns=["modis_frp_missing"])
    else:
        modis_agg = pd.DataFrame(columns=["cell_id", "modis_count", "modis_days", "modis_frp_sum"])

    # 3. VIIRS breakdown
    viirs_df = work[work["sensor"].str.upper() == "VIIRS"]
    if not viirs_df.empty:
        viirs_agg = viirs_df.groupby("cell_id", as_index=False).agg(
            viirs_count=("date_str", "count"),
            viirs_days=("date_str", "nunique"),
            viirs_frp_sum=("frp_numeric", "sum"),
            viirs_frp_missing=("frp_missing", "sum")
        )
        v_all_missing = viirs_agg["viirs_frp_missing"] == viirs_agg["viirs_count"]
        viirs_agg.loc[v_all_missing, "viirs_frp_sum"] = np.nan
        viirs_agg["viirs_frp_sum"] = viirs_agg["viirs_frp_sum"].round(2)
        viirs_agg = viirs_agg.drop(columns=["viirs_frp_missing"])
    else:
        viirs_agg = pd.DataFrame(columns=["cell_id", "viirs_count", "viirs_days", "viirs_frp_sum"])

    # Merge overall with per-sensor metrics
    merged = overall.merge(modis_agg, on="cell_id", how="left").merge(viirs_agg, on="cell_id", how="left")
    merged["modis_count"] = merged["modis_count"].fillna(0).astype(int)
    merged["modis_days"] = merged["modis_days"].fillna(0).astype(int)
    merged["viirs_count"] = merged["viirs_count"].fillna(0).astype(int)
    merged["viirs_days"] = merged["viirs_days"].fillna(0).astype(int)

    # Determine sensors label
    has_m = merged["modis_count"] > 0
    has_v = merged["viirs_count"] > 0
    merged["sensor"] = np.where(has_m & has_v, "BOTH", np.where(has_m, "MODIS", "VIIRS"))

    ordered_cols = [
        "cell_id", "cell_x", "cell_y", "sensor", "count", "days", "frp_sum", "frp_missing_count",
        "modis_count", "modis_days", "modis_frp_sum",
        "viirs_count", "viirs_days", "viirs_frp_sum"
    ]
    return export_cells_to_geojson(
        merged[ordered_cols],
        output_path=output_path,
        cell_size=cell_size,
        coord_precision=coord_precision
    )


def export_yearly(
    gridded_df: pd.DataFrame,
    output_dir: Union[str, Path],
    region: str,
    cell_size: float = 0.01,
    coord_precision: int = 5
) -> List[Dict[str, Any]]:
    """
    Export one GeoJSON file per year into output_dir.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Perform yearly aggregation
    yearly_agg = aggregate_by_cell(gridded_df, period="Y")
    years = sorted(yearly_agg["period"].unique())

    yearly_stats = []
    print(f"Exporting {len(years)} yearly GeoJSON files to {out_dir.resolve()}...")

    for yr in years:
        yr_df = yearly_agg[yearly_agg["period"] == yr].copy()
        yr_file = out_dir / f"{region}_cells_{yr}.geojson"
        gdf = export_cells_to_geojson(
            yr_df,
            output_path=yr_file,
            cell_size=cell_size,
            coord_precision=coord_precision
        )
        size_bytes = yr_file.stat().st_size
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB" if size_bytes >= 1024 * 1024 else f"{size_bytes / 1024:.1f} KB"
        yearly_stats.append({
            "year": yr,
            "features": len(gdf),
            "size_str": size_str,
            "path": str(yr_file)
        })

    return yearly_stats


def resolve_input_csv(region: str, input_path: Optional[str] = None) -> Path:
    """Find input CSV dataset based on region name or explicit path."""
    if input_path:
        p = Path(input_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"Specified input CSV not found: {input_path}")

    reg_clean = region.lower().strip()
    candidates = [
        Path(f"gis/data/{reg_clean}_combined.csv"),
        Path(f"gis/data/{reg_clean}.csv"),
        Path(f"gis/data/palisades_la_combined.csv") if reg_clean in ["palisades", "palisades_la"] else None,
    ]

    for cand in candidates:
        if cand and cand.is_file():
            return cand

    raise FileNotFoundError(f"Could not locate CSV for region '{region}'. Tried: {[str(c) for c in candidates if c]}")


def run_pipeline(
    region: str = "palisades",
    csv_path: Optional[str] = None,
    output_path: Optional[str] = None,
    cell_size: float = 0.01,
    period: str = "M",
    mode: str = "monthly",
    coord_precision: int = 5
):
    """Run full GIS processing and analysis pipeline for any region and export mode."""
    p_csv = resolve_input_csv(region, csv_path)

    print("=" * 65)
    print(f"GIS PROCESSING PIPELINE — REGION: {region.upper()} | MODE: {mode.upper()} | CELL SIZE: {cell_size}°")
    print("=" * 65)
    print(f"1. Loading dataset: {p_csv}")
    df = pd.read_csv(p_csv, low_memory=False)
    total_raw_rows = len(df)
    print(f"   Loaded {total_raw_rows:,} total records.")

    # 2. AOI Bounding box & clipping
    bbox = get_aoi_bbox(region=region, df=df, cell_size=cell_size)
    print(f"2. Applying AOI Bounding Box:")
    print(f"   Latitude  : [{bbox['min_lat']}, {bbox['max_lat']}]")
    print(f"   Longitude : [{bbox['min_lon']}, {bbox['max_lon']}]")

    clipped_gdf = clip_to_aoi(df, region=region, cell_size=cell_size)
    retained_rows = len(clipped_gdf)
    clipped_rows = total_raw_rows - retained_rows
    print(f"   Retained {retained_rows:,} records within AOI ({clipped_rows:,} clipped).")

    # 3. Spatial Grid Assignment
    print(f"3. Assigning spatial grid (cell_size={cell_size} deg)...")
    gridded_df = assign_grid(clipped_gdf, cell_size=cell_size)

    # 4. Mode-based Export
    mode_clean = mode.lower().strip()
    if mode_clean == "totals":
        if not output_path:
            output_path = f"gis/output/{region}_cells_totals.geojson"
            if cell_size != 0.01:
                output_path = f"gis/output/{region}_cells_totals_{cell_size}.geojson"
        print(f"4. Generating TOTALS export (one feature per cell): {output_path}...")
        export_totals(gridded_df, output_path=output_path, cell_size=cell_size, coord_precision=coord_precision)

    elif mode_clean == "yearly":
        output_dir = output_path if output_path else f"gis/output/{region}_yearly"
        print(f"4. Generating YEARLY exports in directory: {output_dir}...")
        export_yearly(gridded_df, output_dir=output_dir, region=region, cell_size=cell_size, coord_precision=coord_precision)

    else:
        # Default monthly export
        if not output_path:
            output_path = f"gis/output/{region}_cells.geojson"
            if region in ["palisades", "palisades_la"] and cell_size == 0.01:
                output_path = "gis/output/palisades_cells.geojson"
            elif cell_size != 0.01:
                output_path = f"gis/output/{region}_cells_{cell_size}.geojson"

        print(f"4. Aggregating by cell, period='{period}', and sensor...")
        agg_df = aggregate_by_cell(gridded_df, period=period)
        print(f"   Generated {len(agg_df):,} aggregated cell-period-sensor records.")
        print(f"5. Exporting to GeoJSON: {output_path}...")
        export_cells_to_geojson(agg_df, output_path=output_path, cell_size=cell_size, coord_precision=coord_precision)

    # 5. Sensor Overlap Analysis Reporting
    print("\n" + "=" * 65)
    print(f"ANALYSIS RESULTS: {region.upper()} (cell_size={cell_size}°)")
    print("=" * 65)

    year_col = "year"
    if year_col not in gridded_df.columns:
        gridded_df["year"] = pd.to_datetime(gridded_df["date"], errors="coerce").dt.year

    cells_per_sensor = gridded_df.groupby("sensor")["cell_id"].nunique()
    print("Unique cells with hotspots per sensor (entire dataset):")
    for sensor, count in cells_per_sensor.items():
        print(f"  - {sensor}: {count:,} cells")

    df_2012_2026 = gridded_df[(gridded_df["year"] >= 2012) & (gridded_df["year"] <= 2026)]
    cells_2012_2026_per_sensor = df_2012_2026.groupby("sensor")["cell_id"].nunique()

    print("\nUnique cells with hotspots per sensor in 2012-2026:")
    for sensor, count in cells_2012_2026_per_sensor.items():
        print(f"  - {sensor}: {count:,} cells")

    modis_cells_2012 = set(df_2012_2026[df_2012_2026["sensor"].str.upper() == "MODIS"]["cell_id"].unique())
    viirs_cells_2012 = set(df_2012_2026[df_2012_2026["sensor"].str.upper() == "VIIRS"]["cell_id"].unique())
    both_sensors_cells = modis_cells_2012.intersection(viirs_cells_2012)

    modis_cnt = len(modis_cells_2012)
    viirs_cnt = len(viirs_cells_2012)
    both_cnt = len(both_sensors_cells)

    print("\nSensor Overlap Analysis (2012-2026):")
    print(f"  - MODIS cells (2012-2026)          : {modis_cnt:,}")
    print(f"  - VIIRS cells (2012-2026)          : {viirs_cnt:,}")
    print(f"  - Cells with BOTH MODIS and VIIRS  : {both_cnt:,}")
    if modis_cnt > 0:
        print(f"  - MODIS spatial recovery by VIIRS  : {both_cnt / modis_cnt * 100:.2f}%")


def main():
    parser = argparse.ArgumentParser(description="Region-aware GIS hotspot aggregation and GeoJSON export.")
    parser.add_argument("--region", type=str, default="palisades", help="Region name (e.g. 'palisades', 'western_ghats_karnataka')")
    parser.add_argument("--input", type=str, default=None, help="Path to input CSV dataset")
    parser.add_argument("--output", type=str, default=None, help="Path to output GeoJSON file or directory")
    parser.add_argument("--cell-size", type=float, default=0.01, help="Spatial grid cell size in degrees (default: 0.01)")
    parser.add_argument("--period", type=str, default="M", help="Temporal aggregation period (default: 'M')")
    parser.add_argument("--mode", type=str, default="monthly", choices=["monthly", "totals", "yearly"],
                        help="Export mode: 'monthly' (default), 'totals' (all-time per cell), or 'yearly' (one file per year)")
    parser.add_argument("--coord-precision", type=int, default=5, help="Number of decimal places for coordinates (default: 5)")

    args = parser.parse_args()
    run_pipeline(
        region=args.region,
        csv_path=args.input,
        output_path=args.output,
        cell_size=args.cell_size,
        period=args.period,
        mode=args.mode,
        coord_precision=args.coord_precision
    )


if __name__ == "__main__":
    main()
