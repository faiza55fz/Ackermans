import os
import sys
import glob
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


def find_csv_file(data_dir: Path) -> Path:
    """Find the first CSV file in the data directory or from CLI argument."""
    if len(sys.argv) > 1 and sys.argv[1].endswith(".csv") and os.path.isfile(sys.argv[1]):
        return Path(sys.argv[1])

    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        # Check current working directory if relative path fails
        alt_dir = Path("gis/data")
        if alt_dir.exists():
            csv_files = list(alt_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found in '{data_dir}'.\n"
            f"Please place your CSV data file into '{data_dir}' (e.g. fire data) and run this script again."
        )

    return csv_files[0]


def main():
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir / "data"

    print("=" * 60)
    print("GIS Exploration Script")
    print("=" * 60)

    try:
        csv_path = find_csv_file(data_dir)
        print(f"Loading CSV from: {csv_path}\n")
    except FileNotFoundError as e:
        print(e)
        return

    # Load dataset
    df = pd.read_csv(csv_path)

    # 1. Row count
    row_count = len(df)
    print(f"Total Rows: {row_count:,}")

    # 2. Columns
    print(f"\nColumns ({len(df.columns)}):")
    for col in df.columns:
        print(f"  - {col}")

    # 3. acq_date range
    date_col = next((c for c in df.columns if c.lower() == "acq_date"), None)
    if date_col:
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        print(f"\nacq_date range: {min_date} to {max_date}")
    else:
        # Check for any other date-like column
        alt_date_col = next((c for c in df.columns if "date" in c.lower()), None)
        if alt_date_col:
            min_date = df[alt_date_col].min()
            max_date = df[alt_date_col].max()
            print(f"\n'{alt_date_col}' range: {min_date} to {max_date}")
        else:
            print("\nNote: 'acq_date' column not found in this CSV.")

    # 4. Plot Longitude vs Latitude
    lon_col = next((c for c in df.columns if c.lower() in ["longitude", "lon", "long", "x"]), None)
    lat_col = next((c for c in df.columns if c.lower() in ["latitude", "lat", "y"]), None)

    if lon_col and lat_col:
        print(f"\nFound coordinate columns: '{lon_col}' and '{lat_col}'")
        # Build GeoDataFrame with Shapely geometry points
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
            crs="EPSG:4326"
        )
        print("Constructed GeoDataFrame (EPSG:4326).")

        print("Plotting Longitude vs Latitude...")
        fig, ax = plt.subplots(figsize=(10, 6))
        gdf.plot(
            ax=ax,
            color="red",
            markersize=12,
            alpha=0.6,
            edgecolor="none"
        )
        ax.set_title(f"Fire Detections: Longitude vs Latitude\n({csv_path.name})", fontsize=14)
        ax.set_xlabel("Longitude", fontsize=12)
        ax.set_ylabel("Latitude", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.5)

        plt.tight_layout()
        output_png = script_dir / "plot.png"
        plt.savefig(output_png, dpi=150)
        print(f"Saved plot preview to: {output_png}")
        print("Displaying interactive plot window...")
        plt.show()
    else:
        print("\nCould not find latitude/longitude columns to plot.")


if __name__ == "__main__":
    main()
