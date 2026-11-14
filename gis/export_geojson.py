import os
import sys
from pathlib import Path
from typing import Optional, Union
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

try:
    from .grid import assign_grid, cell_to_polygon
    from .aoi import clip_to_aoi
    from .aggregate import aggregate_by_cell
except ImportError:
    from grid import assign_grid, cell_to_polygon
    from aoi import clip_to_aoi
    from aggregate import aggregate_by_cell


def export_cells_to_geojson(
    agg_df: pd.DataFrame,
    output_path: Union[str, Path] = "gis/output/palisades_cells.geojson",
    cell_size: float = 0.01
) -> gpd.GeoDataFrame:
    """
    Save aggregated cells as GeoJSON squares with specified properties.

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

    # Derive cell_x and cell_y if missing
    df = agg_df.copy()
    if "cell_x" not in df.columns or "cell_y" not in df.columns:
        coords = df["cell_id"].str.split("_", expand=True)
        df["cell_x"] = coords[0].astype(int)
        df["cell_y"] = coords[1].astype(int)

    # Construct square polygons rounded to 6 decimal places
    geometries = [
        box(
            round(cx * cell_size, 6),
            round(cy * cell_size, 6),
            round((cx + 1) * cell_size, 6),
            round((cy + 1) * cell_size, 6)
        )
        for cx, cy in zip(df["cell_x"], df["cell_y"])
    ]

    # Select required properties
    required_props = ["cell_id", "period", "sensor", "count", "days", "frp_sum"]
    if "frp_missing_count" in df.columns:
        required_props.append("frp_missing_count")

    export_df = df[required_props].copy()

    gdf = gpd.GeoDataFrame(export_df, geometry=geometries, crs="EPSG:4326")
    gdf.to_file(out_file, driver="GeoJSON")
    print(f"Exported {len(gdf)} grid cell records to {out_file.resolve()}")
    return gdf


def run_pipeline(
    csv_path: str = "gis/data/palisades_la_combined.csv",
    output_path: str = "gis/output/palisades_cells.geojson",
    cell_size: float = 0.01,
    period: str = "M"
):
    """Run full GIS processing and analysis pipeline."""
    p_csv = Path(csv_path)
    if not p_csv.is_file():
        # Fallback to relative script location
        alt_path = Path(__file__).resolve().parent / "data" / "palisades_la_combined.csv"
        if alt_path.is_file():
            p_csv = alt_path
        else:
            raise FileNotFoundError(f"Data file not found at {csv_path}")

    print(f"1. Loading data from: {p_csv}")
    df = pd.read_csv(p_csv)
    print(f"   Loaded {len(df):,} total records.")

    print("2. Clipping to default AOI bounding box (lat 34.0 to 34.2, lon -118.75 to -118.42)...")
    clipped_gdf = clip_to_aoi(df)
    print(f"   Retained {len(clipped_gdf):,} records within AOI.")

    print(f"3. Assigning spatial grid (cell_size={cell_size} deg)...")
    gridded_df = assign_grid(clipped_gdf, cell_size=cell_size)

    print(f"4. Aggregating by cell, period='{period}', and sensor...")
    agg_df = aggregate_by_cell(gridded_df, period=period)
    print(f"   Generated {len(agg_df):,} aggregated cell-period-sensor records.")

    print(f"5. Exporting to GeoJSON: {output_path}...")
    export_cells_to_geojson(agg_df, output_path=output_path, cell_size=cell_size)

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)

    # 1. Number of distinct cells with hotspots per sensor (across all data)
    cells_per_sensor = gridded_df.groupby("sensor")["cell_id"].nunique()
    print("Unique cells with hotspots per sensor (entire dataset):")
    for sensor, count in cells_per_sensor.items():
        print(f"  - {sensor}: {count} cells")

    # 2. Number of cells with hotspots per sensor in 2012-2026
    df_2012_2026 = gridded_df[(gridded_df["year"] >= 2012) & (gridded_df["year"] <= 2026)]
    cells_2012_2026_per_sensor = df_2012_2026.groupby("sensor")["cell_id"].nunique()
    print("\nUnique cells with hotspots per sensor in 2012-2026:")
    for sensor, count in cells_2012_2026_per_sensor.items():
        print(f"  - {sensor}: {count} cells")

    # 3. Cells having BOTH sensors in 2012-2026
    modis_cells_2012 = set(df_2012_2026[df_2012_2026["sensor"] == "MODIS"]["cell_id"].unique())
    viirs_cells_2012 = set(df_2012_2026[df_2012_2026["sensor"] == "VIIRS"]["cell_id"].unique())
    both_sensors_cells = modis_cells_2012.intersection(viirs_cells_2012)

    print("\nSensor Overlap Analysis (2012-2026):")
    print(f"  - MODIS cells (2012-2026): {len(modis_cells_2012)}")
    print(f"  - VIIRS cells (2012-2026): {len(viirs_cells_2012)}")
    print(f"  - Cells with BOTH MODIS and VIIRS: {len(both_sensors_cells)}")

    return agg_df


if __name__ == "__main__":
    run_pipeline()
