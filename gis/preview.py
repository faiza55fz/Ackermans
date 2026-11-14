import os
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box

# Set headless backend for environment compatibility
os.environ["MPLBACKEND"] = "Agg"


def plot_preview(
    geojson_path: str = "gis/output/palisades_cells.geojson",
    output_png: str = "gis/output/preview.png"
):
    """Plot GeoJSON cells colored by total hotspot count and save preview image."""
    p_geojson = Path(geojson_path)
    if not p_geojson.is_file():
        raise FileNotFoundError(f"GeoJSON file not found at: {geojson_path}")

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
        linewidth=0.4,
        alpha=0.85,
        ax=ax,
        legend_kwds={"label": "Total Hotspot Count per Cell", "orientation": "vertical"}
    )

    # Reference AOI bounding box (widened to -118.42 E)
    aoi_polygon = box(-118.75, 34.0, -118.42, 34.2)
    aoi_series = gpd.GeoSeries([aoi_polygon], crs="EPSG:4326")
    aoi_series.boundary.plot(
        ax=ax,
        color="royalblue",
        linestyle="--",
        linewidth=1.8,
        label="Default AOI (34.0-34.2 N, 118.75-118.42 W)"
    )

    ax.set_title("Palisades Active Fire Detections\nTotal Hotspot Count per 0.01° Grid Cell", fontsize=14, pad=12)
    ax.set_xlabel("Longitude (°W)", fontsize=11)
    ax.set_ylabel("Latitude (°N)", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left")

    plt.tight_layout()
    out_file = Path(output_png)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_file, dpi=180)
    plt.close()
    print(f"Preview plot successfully saved to: {out_file.resolve()}")


if __name__ == "__main__":
    plot_preview()
