import numpy as np
import pandas as pd
from shapely.geometry import box, Polygon


def assign_grid(df: pd.DataFrame, cell_size: float = 0.01) -> pd.DataFrame:
    """
    Assign each hotspot point to a regular spatial grid cell.

    Uses np.floor(np.round(coord / cell_size, 6)) to eliminate IEEE 754 float
    precision errors on coordinate boundaries.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing 'longitude' and 'latitude' columns.
    cell_size : float, optional (default=0.01)
        Grid cell size in degrees (~1.1 km at 34 deg latitude).

    Returns:
    --------
    pd.DataFrame:
        Copy of input DataFrame with added integer columns 'cell_x', 'cell_y'
        and string identifier 'cell_id' (e.g. 'cell_x_cell_y').
    """
    if "longitude" not in df.columns or "latitude" not in df.columns:
        raise ValueError("DataFrame must contain 'longitude' and 'latitude' columns.")

    result = df.copy()
    result["cell_x"] = np.floor(np.round(result["longitude"] / cell_size, 6)).astype(int)
    result["cell_y"] = np.floor(np.round(result["latitude"] / cell_size, 6)).astype(int)
    result["cell_id"] = result["cell_x"].astype(str) + "_" + result["cell_y"].astype(str)
    return result


def cell_to_polygon(cell_x: int, cell_y: int, cell_size: float = 0.01) -> Polygon:
    """
    Construct a square bounding box Polygon for a given grid cell index.
    Coordinates are rounded to 5 decimal places (~1m precision) to keep GeoJSON compact.

    Parameters:
    -----------
    cell_x : int
        Grid column index (longitude / cell_size).
    cell_y : int
        Grid row index (latitude / cell_size).
    cell_size : float, optional (default=0.01)
        Grid cell size in degrees.

    Returns:
    --------
    shapely.geometry.Polygon:
        Square polygon representing the grid cell boundary.
    """
    min_lon = round(cell_x * cell_size, 5)
    min_lat = round(cell_y * cell_size, 5)
    max_lon = round(min_lon + cell_size, 5)
    max_lat = round(min_lat + cell_size, 5)
    return box(min_lon, min_lat, max_lon, max_lat)
