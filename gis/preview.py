import os
import argparse
from pathlib import Path
from typing import Optional
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box

try:
    from .aoi import get_aoi_bbox
except ImportError:
    from aoi import get_aoi_bbox

# Set headless backend for environment compatibility
os.environ["MPLBACKEND"] = "Agg"


def plot_preview(
    region: str = "palisades",
    geojson_path: Optional[str] = None,
    output_png: Optional[str] = None
):
    """Plot GeoJSON cells colored by total hotspot count and save preview image."""
    reg_clean = region.lower().strip()

    if not geojson_path:
        cand_geojson = Path(f"gis/output/{reg_clean}_cells.geojson")
        if cand_geojson.is_file():
            geojson_path = str(cand_geojson)
        elif reg_clean in ["palisades", "palisades_la"] and Path("gis/output/palisades_cells.geojson").is_file():
            geojson_path = "gis/output/palisades_cells.geojson"
        else:
            raise FileNotFoundError(f"Could not locate GeoJSON for region '{region}'.")

    if not output_png:
        output_png = f"gis/output/{reg_clean}_preview.png"
        if reg_clean in ["palisades", "palisades_la"]:
            output_png = "gis/output/preview.png"

    p_geojson = Path(geojson_path)
    print(f"Loading GeoJSON from: {p_geojson}")
    gdf = gpd.read_file(p_geojson)

    # Dissolve by cell_id to compute total count across all months/sensors
    cell_gdf = gdf.dissolve(by="cell_id", aggfunc={"count": "sum", "frp_sum": "sum"}).reset_index()

    fig, ax = plt.subplots(figsize=(11, 7))

    # Plot cells colored by total count
    cell_gdf.plot(
        column="count",
        cmap="YlOrRd",
        legend=True,
        edgecolor="black",
        linewidth=0.2,
        alpha=0.85,
        ax=ax,
        legend_kwds={"label": "Total Hotspot Count per Cell", "orientation": "vertical"}
    )

    # Reference AOI bounding box
    bbox = get_aoi_bbox(region=reg_clean, df=gdf.rename(columns={"geometry": "geom"}).assign(
        latitude=gdf.geometry.centroid.y,
        longitude=gdf.geometry.centroid.x
    ))
    aoi_polygon = box(bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"])
    aoi_series = gpd.GeoSeries([aoi_polygon], crs="EPSG:4326")
    aoi_series.boundary.plot(
        ax=ax,
        color="royalblue",
        linestyle="--",
        linewidth=1.8,
        label=f"AOI BBox ({bbox['min_lat']}-{bbox['max_lat']} N, {bbox['min_lon']}-{bbox['max_lon']} E)"
    )

    ax.set_title(f"{region.replace('_', ' ').title()} Active Fire Detections\nTotal Hotspot Count per 0.01° Grid Cell", fontsize=14, pad=12)
    ax.set_xlabel("Longitude (°)", fontsize=11)
    ax.set_ylabel("Latitude (°)", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left")

    plt.tight_layout()
    out_file = Path(output_png)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_file, dpi=180)
    plt.close()
    print(f"Preview plot successfully saved to: {out_file.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Region-aware preview map generation.")
    parser.add_argument("--region", type=str, default="palisades", help="Region name")
    parser.add_argument("--input", type=str, default=None, help="Input GeoJSON path")
    parser.add_argument("--output", type=str, default=None, help="Output PNG path")

    args = parser.parse_args()
    plot_preview(region=args.region, geojson_path=args.input, output_png=args.output)


if __name__ == "__main__":
    main()
