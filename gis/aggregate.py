import numpy as np
import pandas as pd
from typing import Optional

try:
    from .grid import assign_grid
except ImportError:
    from grid import assign_grid


def aggregate_by_cell(
    df: pd.DataFrame,
    period: Optional[str] = "M"
) -> pd.DataFrame:
    """
    Aggregate hotspot detections per grid cell, period, and sensor.

    Computes:
    - Hotspot count (total detections)
    - Unique detection-days (counting each cell at most once per day per sensor)
    - FRP sum (sum of Fire Radiative Power, skipping NaNs; NaN if all missing)
    - FRP missing count (number of observations with NaN/missing FRP)

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with hotspot detections. Must have 'date', 'sensor', and
        either ('cell_id', 'cell_x', 'cell_y') or ('latitude', 'longitude').
    period : str, optional (default="M")
        Pandas frequency period alias, e.g. 'M' (monthly), 'Y' (yearly),
        'D' (daily), or None/'all' for the entire timeline.

    Returns:
    --------
    pd.DataFrame:
        Aggregated results with columns:
        ['cell_id', 'cell_x', 'cell_y', 'period', 'sensor', 'count', 'days', 'frp_sum', 'frp_missing_count']
    """
    work_df = df.copy()

    # Ensure grid assignment exists
    if "cell_id" not in work_df.columns or "cell_x" not in work_df.columns or "cell_y" not in work_df.columns:
        work_df = assign_grid(work_df)

    # Format period
    dates = pd.to_datetime(work_df["date"], errors="coerce")
    if period and str(period).lower() != "all":
        work_df["period"] = dates.dt.to_period(period).astype(str)
    else:
        work_df["period"] = "all"

    # Ensure FRP is numeric while PRESERVING NaN values
    if "frp" in work_df.columns:
        work_df["frp"] = pd.to_numeric(work_df["frp"], errors="coerce")
    else:
        work_df["frp"] = np.nan

    # Ensure date string for unique day counting
    work_df["date_str"] = dates.dt.strftime("%Y-%m-%d")

    # Group by cell, period, and sensor
    group_cols = ["cell_id", "cell_x", "cell_y", "period", "sensor"]
    agg_df = (
        work_df.groupby(group_cols, as_index=False)
        .agg(
            count=("date_str", "count"),
            days=("date_str", "nunique"),
            frp_sum=("frp", lambda s: s.sum(min_count=1)),
            frp_missing_count=("frp", lambda s: s.isna().sum()),
        )
    )

    # Round frp_sum for clean output where not NaN
    agg_df["frp_sum"] = agg_df["frp_sum"].round(2)

    # Sort for deterministic output
    agg_df = agg_df.sort_values(by=["period", "cell_id", "sensor"]).reset_index(drop=True)

    return agg_df
