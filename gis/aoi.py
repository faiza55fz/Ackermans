import json
from pathlib import Path
from typing import Union, Optional, Any, Dict
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box, shape, Polygon, MultiPolygon
from shapely.ops import unary_union

# Curated regional bounding boxes
KNOWN_REGIONS_BBOX: Dict[str, Dict[str, float]] = {
    "palisades": {
        "min_lat": 34.0,
        "max_lat": 34.2,
        "min_lon": -118.75,
        "max_lon": -118.42,
    },
    "palisades_la": {
        "min_lat": 34.0,
        "max_lat": 34.2,
        "min_lon": -118.75,
        "max_lon": -118.42,
    },
}

DEFAULT_AOI_BBOX = KNOWN_REGIONS_BBOX["palisades"]


def compute_bbox_from_df(df: pd.DataFrame, cell_size: float = 0.01) -> Dict[str, float]:
    """
    Compute Area of Interest bounding box from DataFrame coordinates,
    rounded outward to the nearest cell_size.
    """
    if "latitude" not in df.columns or "longitude" not in df.columns:
        raise ValueError("DataFrame must contain 'latitude' and 'longitude' columns.")

    min_lat = round(np.floor(np.round(df["latitude"].min() / cell_size, 6)) * cell_size, 6)
    max_lat = round(np.ceil(np.round(df["latitude"].max() / cell_size, 6)) * cell_size, 6)
    min_lon = round(np.floor(np.round(df["longitude"].min() / cell_size, 6)) * cell_size, 6)
    max_lon = round(np.ceil(np.round(df["longitude"].max() / cell_size, 6)) * cell_size, 6)

    return {
        "min_lat": float(min_lat),
        "max_lat": float(max_lat),
        "min_lon": float(min_lon),
        "max_lon": float(max_lon),
    }


def get_aoi_bbox(
    region: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
    cell_size: float = 0.01
) -> Dict[str, float]:
    """
    Retrieve bounding box dictionary for a specific region or compute from data.
    """
    if region:
        reg_key = region.lower().strip()
        if reg_key in KNOWN_REGIONS_BBOX:
            return KNOWN_REGIONS_BBOX[reg_key]

    if df is not None and not df.empty:
        return compute_bbox_from_df(df, cell_size=cell_size)

    return DEFAULT_AOI_BBOX


def get_default_aoi(
    region: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
    cell_size: float = 0.01
) -> Polygon:
    """
    Get Area of Interest (AOI) polygon.
    """
    bbox = get_aoi_bbox(region=region, df=df, cell_size=cell_size)
    return box(bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"])


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
    polygon_geojson: Optional[Any] = None,
    region: Optional[str] = None,
    cell_size: float = 0.01
) -> gpd.GeoDataFrame:
    """
    Clip hotspot DataFrame to an Area of Interest (AOI) polygon or bounding box.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'longitude' and 'latitude' columns.
    polygon_geojson : GeoJSON dict, file path, Shapely geometry, or None
        Explicit clipping polygon. If None, uses regional AOI or computes from data.
    region : str, optional
        Region identifier (e.g. 'palisades', 'western_ghats_karnataka').
    cell_size : float, optional (default=0.01)
        Cell size for outward bounding box rounding.

    Returns:
    --------
    gpd.GeoDataFrame:
        Points strictly falling within or intersecting the AOI (EPSG:4326).
    """
    if "longitude" not in df.columns or "latitude" not in df.columns:
        raise ValueError("Input DataFrame must have 'longitude' and 'latitude' columns.")

    if polygon_geojson is not None:
        polygon = parse_geojson_polygon(polygon_geojson)
        if not isinstance(df, gpd.GeoDataFrame) or "geometry" not in df.columns:
            gdf = gpd.GeoDataFrame(
                df.copy(),
                geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
                crs="EPSG:4326"
            )
        else:
            gdf = df.copy()
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")

        mask = gdf.geometry.intersects(polygon)
        return gdf[mask].copy()

    # Fast vectorized bounding box filtering
    bbox = get_aoi_bbox(region=region, df=df, cell_size=cell_size)
    mask = (
        (df["latitude"] >= bbox["min_lat"])
        & (df["latitude"] <= bbox["max_lat"])
        & (df["longitude"] >= bbox["min_lon"])
        & (df["longitude"] <= bbox["max_lon"])
    )
    clipped_df = df[mask].copy()

    gdf = gpd.GeoDataFrame(
        clipped_df,
        geometry=gpd.points_from_xy(clipped_df["longitude"], clipped_df["latitude"]),
        crs="EPSG:4326"
    )
    return gdf
