import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Union
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
    output_path: Union[str, Path] = "gis/output/palisades_cells.geojson",
    cell_size: float = 0.01
) -> gpd.GeoDataFrame:
    """
    Save aggregated cells as GeoJSON squares with specified properties.
    NaN values are automatically serialized as JSON 'null'.

    Properties:
    -----------
    - cell_id
    - period
    - sensor
    - count
    - days
    - frp_sum
    - frp_missing_count (if present)

    Parameters:
    -----------
    agg_df : pd.DataFrame
        Aggregated dataframe containing cell information.
    output_path : str or Path
        Destination GeoJSON file path.
    cell_size : float, optional (default=0.01)
        Cell size in degrees.

    Returns:
    --------
    gpd.GeoDataFrame:
        The exported GeoDataFrame.
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
            round(cx * cell_size, 6),
            round(cy * cell_size, 6),
            round((cx + 1) * cell_size, 6),
            round((cy + 1) * cell_size, 6),
        )
        for cx, cy in zip(unique_cells["cell_x"], unique_cells["cell_y"])
    }
    geometries = [geom_map[(int(cx), int(cy))] for cx, cy in zip(df["cell_x"], df["cell_y"])]

    # Select required properties
    required_props = ["cell_id", "period", "sensor", "count", "days", "frp_sum"]
    if "frp_missing_count" in df.columns:
        required_props.append("frp_missing_count")

    export_df = df[required_props].copy()

    gdf = gpd.GeoDataFrame(export_df, geometry=geometries, crs="EPSG:4326")
    gdf.to_file(out_file, driver="GeoJSON")
    file_size_mb = out_file.stat().st_size / (1024 * 1024)
    print(f"Exported {len(gdf):,} grid cell features to {out_file.resolve()} ({file_size_mb:.2f} MB)")
    return gdf


def resolve_input_csv(region: str, input_path: Optional[str] = None) -> Path:
    """Find input CSV dataset based on region name or explicit path."""
    if input_path:
        p = Path(input_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"Specified input CSV not found: {input_path}")

    # Region search order
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
    period: str = "M"
):
    """Run full GIS processing and analysis pipeline for any region."""
    p_csv = resolve_input_csv(region, csv_path)

    if not output_path:
        output_path = f"gis/output/{region}_cells.geojson"

    print("=" * 65)
    print(f"GIS PROCESSING PIPELINE — REGION: {region.upper()}")
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

    # 4. Spatiotemporal Aggregation
    print(f"4. Aggregating by cell, period='{period}', and sensor...")
    agg_df = aggregate_by_cell(gridded_df, period=period)
    print(f"   Generated {len(agg_df):,} aggregated cell-period-sensor records.")

    # 5. Export GeoJSON
    print(f"5. Exporting to GeoJSON: {output_path}...")
    export_cells_to_geojson(agg_df, output_path=output_path, cell_size=cell_size)

    # 6. Analysis Reporting
    print("\n" + "=" * 65)
    print(f"ANALYSIS RESULTS: {region.upper()}")
    print("=" * 65)

    # Unique cells with hotspots per sensor (across all data)
    cells_per_sensor = gridded_df.groupby("sensor")["cell_id"].nunique()
    print("Unique cells with hotspots per sensor (entire dataset):")
    for sensor, count in cells_per_sensor.items():
        print(f"  - {sensor}: {count:,} cells")

    # Filter to operational overlap period 2012-2026
    year_col = "year"
    if year_col not in gridded_df.columns:
        gridded_df["year"] = pd.to_datetime(gridded_df["date"], errors="coerce").dt.year

    df_2012_2026 = gridded_df[(gridded_df["year"] >= 2012) & (gridded_df["year"] <= 2026)]
    cells_2012_2026_per_sensor = df_2012_2026.groupby("sensor")["cell_id"].nunique()

    print("\nUnique cells with hotspots per sensor in 2012-2026:")
    for sensor, count in cells_2012_2026_per_sensor.items():
        print(f"  - {sensor}: {count:,} cells")

    # Overlap
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

    return agg_df


def main():
    parser = argparse.ArgumentParser(description="Region-aware GIS hotspot aggregation and GeoJSON export.")
    parser.add_argument("--region", type=str, default="palisades", help="Region name (e.g. 'palisades', 'western_ghats_karnataka')")
    parser.add_argument("--input", type=str, default=None, help="Path to input CSV dataset")
    parser.add_argument("--output", type=str, default=None, help="Path to output GeoJSON file")
    parser.add_argument("--cell-size", type=float, default=0.01, help="Spatial grid cell size in degrees (default: 0.01)")
    parser.add_argument("--period", type=str, default="M", help="Temporal aggregation period (default: 'M')")

    args = parser.parse_args()
    run_pipeline(
        region=args.region,
        csv_path=args.input,
        output_path=args.output,
        cell_size=args.cell_size,
        period=args.period
    )


if __name__ == "__main__":
    main()
