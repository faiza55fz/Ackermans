import numpy as np
import pandas as pd
from shapely.geometry import box, Polygon


def assign_grid(df: pd.DataFrame, cell_size: float = 0.01) -> pd.DataFrame:
    """
    Assign each hotspot point to a regular spatial grid cell.

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
    result["cell_x"] = np.floor(result["longitude"] / cell_size).astype(int)
    result["cell_y"] = np.floor(result["latitude"] / cell_size).astype(int)
    result["cell_id"] = result["cell_x"].astype(str) + "_" + result["cell_y"].astype(str)
    return result


def cell_to_polygon(cell_x: int, cell_y: int, cell_size: float = 0.01) -> Polygon:
    """
    Construct a square bounding box Polygon for a given grid cell index.

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
    min_lon = cell_x * cell_size
    min_lat = cell_y * cell_size
    max_lon = min_lon + cell_size
    max_lat = min_lat + cell_size
    return box(min_lon, min_lat, max_lon, max_lat)
