import json
from pathlib import Path
from typing import Union, Optional, Any
import pandas as pd
import geopandas as gpd
from shapely.geometry import box, shape, Polygon, MultiPolygon
from shapely.ops import unary_union

# Default AOI bounding box matching the Palisades study area (widened to -118.42 E)
DEFAULT_AOI_BBOX = {
    "min_lat": 34.0,
    "max_lat": 34.2,
    "min_lon": -118.75,
    "max_lon": -118.42,
}


def get_default_aoi() -> Polygon:
    """
    Get the default Area of Interest (AOI) polygon representing
    the bounding box (lat 34.0 to 34.2, lon -118.75 to -118.42).
    """
    return box(
        DEFAULT_AOI_BBOX["min_lon"],
        DEFAULT_AOI_BBOX["min_lat"],
        DEFAULT_AOI_BBOX["max_lon"],
        DEFAULT_AOI_BBOX["max_lat"],
    )


def parse_geojson_polygon(polygon_input: Any) -> Union[Polygon, MultiPolygon]:
    """Parse various polygon inputs (Shapely, GeoJSON dict, file path, GeoDataFrame)."""
    if polygon_input is None:
        return get_default_aoi()

    if isinstance(polygon_input, (Polygon, MultiPolygon)):
        return polygon_input

    # File path
    if isinstance(polygon_input, (str, Path)):
        p = Path(polygon_input)
        if p.is_file():
            gdf = gpd.read_file(p)
            return unary_union(gdf.geometry)

    # GeoJSON dict
    if isinstance(polygon_input, dict):
        if polygon_input.get("type") == "FeatureCollection":
            geoms = [shape(f["geometry"]) for f in polygon_input.get("features", []) if f.get("geometry")]
            return unary_union(geoms)
        elif polygon_input.get("type") == "Feature":
            return shape(polygon_input["geometry"])
        elif "type" in polygon_input and "coordinates" in polygon_input:
            return shape(polygon_input)

    # GeoDataFrame or GeoSeries
    if isinstance(polygon_input, (gpd.GeoDataFrame, gpd.GeoSeries)):
        return unary_union(polygon_input.geometry)

    raise ValueError(f"Unable to parse polygon from input type: {type(polygon_input)}")


def clip_to_aoi(
    df: pd.DataFrame,
    polygon_geojson: Optional[Any] = None
) -> gpd.GeoDataFrame:
    """
    Clip hotspot DataFrame to an Area of Interest (AOI) polygon.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'longitude' and 'latitude' columns.
    polygon_geojson : GeoJSON dict, file path, Shapely geometry, or None
        The clipping boundary polygon. If None, the default bounding box
        (lat 34.0 to 34.2, lon -118.75 to -118.42) is used.

    Returns:
    --------
    gpd.GeoDataFrame:
        Points strictly falling within or intersecting the AOI polygon (EPSG:4326).
    """
    polygon = parse_geojson_polygon(polygon_geojson)

    # Ensure GeoDataFrame
    if not isinstance(df, gpd.GeoDataFrame) or "geometry" not in df.columns:
        if "longitude" not in df.columns or "latitude" not in df.columns:
            raise ValueError("Input DataFrame must have 'longitude' and 'latitude' columns.")
        gdf = gpd.GeoDataFrame(
            df.copy(),
            geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
            crs="EPSG:4326"
        )
    else:
        gdf = df.copy()
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")

    # Filter points within or on boundary of AOI
    mask = gdf.geometry.intersects(polygon)
    clipped = gdf[mask].copy()

    return clipped
