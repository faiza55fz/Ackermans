"""Map cleaned FIRMS detections onto a shared cell-day grid.

Detections use the 23-column cleaned schema. Each point is assigned to the
lower-left corner of a square cell, then summarized by cell, calendar day,
and sensor. MODIS and VIIRS metrics are returned side by side.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

DEFAULT_CELL_SIZE_DEGREES: float = 0.25

DETECTION_COLUMNS: tuple[str, ...] = (
    "region",
    "sensor",
    "satellite",
    "processing",
    "datetime_utc",
    "date",
    "year",
    "latitude",
    "longitude",
    "confidence",
    "confidence_class",
    "frp",
    "daynight",
    "scan",
    "track",
    "instrument",
    "version",
    "brightness",
    "bright_t31",
    "bright_ti4",
    "bright_ti5",
    "type",
    "is_vegetation_fire",
)

CANONICAL_SENSORS: tuple[str, ...] = ("MODIS", "VIIRS")

METRIC_COLUMNS: tuple[str, ...] = (
    "n_detections",
    "fire_day",
    "mean_frp",
    "max_frp",
    "mean_scan",
    "night_fraction",
)

_NIGHT_LABELS: frozenset[str] = frozenset({"N", "NIGHT"})


def assign_cell(lat: float, lon: float, cell_size_deg: float) -> str:
    """Return the cell id ``"{lat_bin}_{lon_bin}"`` for one detection.

    ``lat_bin`` and ``lon_bin`` are the lower edges of the cell that
    contains the point. Edges are multiples of ``cell_size_deg``. The
    project default is 0.25 degrees, from ``cell_size_degrees`` in
    ``config.yaml``.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees.
    lon:
        Longitude in decimal degrees.
    cell_size_deg:
        Positive cell width and height in degrees.

    Returns
    -------
    str
        Cell id such as ``"34.00_-118.75"``.
    """

    size = _cell_size(cell_size_deg)
    return f"{_edge_label(lat, size, 'lat')}_{_edge_label(lon, size, 'lon')}"


def assign_cells(df: pd.DataFrame, cell_size_deg: float) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``cell_id`` column.

    Parameters
    ----------
    df:
        Detection table with ``latitude`` and ``longitude`` columns.
    cell_size_deg:
        Positive cell size in degrees passed to :func:`assign_cell`.

    Returns
    -------
    pandas.DataFrame
        Copy of ``df`` with ``cell_id`` values appended.
    """

    missing = [name for name in ("latitude", "longitude") if name not in df.columns]
    if missing:
        raise ValueError("Detection table is missing columns: " + ", ".join(missing))
    assigned = df.copy()
    assigned["cell_id"] = [
        assign_cell(latitude, longitude, cell_size_deg)
        for latitude, longitude in zip(
            assigned["latitude"].tolist(),
            assigned["longitude"].tolist(),
            strict=True,
        )
    ]
    return assigned


def load_cell_size_degrees(config_path: Path | str | None = None) -> float:
    """Read ``cell_size_degrees`` from config, defaulting to 0.25.

    Parameters
    ----------
    config_path:
        YAML config file. When omitted, the project ``config.yaml`` next
        to the ``src`` directory is used. A missing file or a missing
        ``cell_size_degrees`` key also returns 0.25.

    Returns
    -------
    float
        Positive cell size in degrees.
    """

    path = _default_config_path() if config_path is None else Path(config_path)
    if not path.is_file():
        return DEFAULT_CELL_SIZE_DEGREES
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if loaded is None:
        return DEFAULT_CELL_SIZE_DEGREES
    if not isinstance(loaded, dict):
        raise ValueError(f"Config at {path} must be a mapping")
    if "cell_size_degrees" not in loaded or loaded["cell_size_degrees"] is None:
        return DEFAULT_CELL_SIZE_DEGREES
    return _positive_cell_size(float(loaded["cell_size_degrees"]))


def require_detection_columns(df: pd.DataFrame) -> None:
    """Raise ``ValueError`` when ``df`` omits any cleaned-schema column.

    Parameters
    ----------
    df:
        Table expected to carry :data:`DETECTION_COLUMNS`.
    """

    missing = [name for name in DETECTION_COLUMNS if name not in df.columns]
    if missing:
        raise ValueError("Detection table is missing columns: " + ", ".join(missing))


def aggregate_cell_day(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize detections by cell, calendar date, and sensor.

    Each group reports ``n_detections``, ``fire_day`` (1 when the group
    has at least one detection, otherwise 0), ``mean_frp``, ``max_frp``,
    ``mean_scan``, and ``night_fraction``. Night detections are rows whose
    ``daynight`` value is ``N`` or ``Night``, ignoring case. Sensor labels
    are stripped and upper-cased.

    Parameters
    ----------
    df:
        Detections that already include ``cell_id``, ``date``, ``sensor``,
        ``frp``, ``scan``, and ``daynight``.

    Returns
    -------
    pandas.DataFrame
        One row per ``cell_id``, ``date``, and ``sensor``.
    """

    required = ("cell_id", "date", "sensor", "frp", "scan", "daynight")
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise ValueError("Detection table is missing columns: " + ", ".join(missing))
    if df.empty:
        return pd.DataFrame(columns=["cell_id", "date", "sensor", *METRIC_COLUMNS])

    working = df.copy()
    if working["sensor"].isna().any():
        raise ValueError("sensor contains null values")
    working["sensor"] = working["sensor"].map(_sensor_label)
    working["_night"] = working["daynight"].map(_is_night)

    keys = ["cell_id", "date", "sensor"]
    grouped = working.groupby(keys, dropna=False, sort=True)
    counts = grouped.size().rename("n_detections")
    metrics = grouped.agg(
        mean_frp=("frp", "mean"),
        max_frp=("frp", "max"),
        mean_scan=("scan", "mean"),
        night_fraction=("_night", "mean"),
    )
    aggregated = metrics.join(counts).reset_index()
    aggregated["fire_day"] = (aggregated["n_detections"] >= 1).astype(int)
    aggregated["n_detections"] = aggregated["n_detections"].astype(int)
    return aggregated.loc[:, ["cell_id", "date", "sensor", *METRIC_COLUMNS]].reset_index(
        drop=True
    )


def pivot_cell_day(aggregated: pd.DataFrame) -> pd.DataFrame:
    """Place sensor metrics side by side for each cell-day.

    MODIS columns come first, then VIIRS, then any other sensor labels in
    alphabetical order. A sensor with no detections in a cell-day has
    ``n_detections`` and ``fire_day`` of 0. Mean, max, and night fraction
    stay missing for that sensor.

    Parameters
    ----------
    aggregated:
        Long table returned by :func:`aggregate_cell_day`.

    Returns
    -------
    pandas.DataFrame
        One row per ``cell_id`` and ``date``.
    """

    required = ("cell_id", "date", "sensor", *METRIC_COLUMNS)
    missing = [name for name in required if name not in aggregated.columns]
    if missing:
        raise ValueError("Aggregated table is missing columns: " + ", ".join(missing))

    sensors = _sensor_order([] if aggregated.empty else aggregated["sensor"].tolist())
    wide_metrics = _metric_column_names(sensors)
    if aggregated.empty:
        return pd.DataFrame(columns=["cell_id", "date", *wide_metrics])

    pivoted = aggregated.pivot(
        index=["cell_id", "date"],
        columns="sensor",
        values=list(METRIC_COLUMNS),
    )
    pivoted.columns = _flatten_pivot_columns(pivoted.columns)
    wide = pivoted.reset_index()
    for column in wide_metrics:
        if column not in wide.columns:
            wide[column] = pd.NA
    wide = wide.loc[:, ["cell_id", "date", *wide_metrics]]
    for sensor in sensors:
        count_column = f"n_detections_{sensor}"
        fire_column = f"fire_day_{sensor}"
        wide[count_column] = wide[count_column].fillna(0).astype(int)
        wide[fire_column] = wide[fire_column].fillna(0).astype(int)
    return wide.sort_values(["cell_id", "date"], kind="mergesort").reset_index(drop=True)


def add_overlap_valid(cell_days: pd.DataFrame) -> pd.DataFrame:
    """Return ``cell_days`` with boolean ``overlap_valid``.

    The flag is true when both MODIS and VIIRS have at least one detection
    in that cell on that day.

    Parameters
    ----------
    cell_days:
        Wide cell-day table with ``n_detections_MODIS`` and
        ``n_detections_VIIRS``.

    Returns
    -------
    pandas.DataFrame
        Copy of ``cell_days`` with ``overlap_valid`` appended.
    """

    required = ("n_detections_MODIS", "n_detections_VIIRS")
    missing = [name for name in required if name not in cell_days.columns]
    if missing:
        raise ValueError("Cell-day table is missing columns: " + ", ".join(missing))
    flagged = cell_days.copy()
    modis_count = flagged["n_detections_MODIS"].fillna(0)
    viirs_count = flagged["n_detections_VIIRS"].fillna(0)
    both_observed = (modis_count >= 1) & (viirs_count >= 1)
    flagged["overlap_valid"] = both_observed.to_numpy(dtype=bool)
    return flagged


def build_cell_day_table(
    df: pd.DataFrame,
    cell_size_deg: float | None = None,
    config_path: Path | str | None = None,
) -> pd.DataFrame:
    """Build the wide MODIS/VIIRS cell-day table for cleaned detections.

    The table is grouped by cell, calendar date, and sensor, then pivoted
    so each metric exists for MODIS and VIIRS. ``overlap_valid`` is true
    when both sensors observed that cell-day at least once.

    Parameters
    ----------
    df:
        Cleaned detection table with :data:`DETECTION_COLUMNS`.
    cell_size_deg:
        Cell size in degrees. When omitted, the size is loaded from
        ``config.yaml`` (default 0.25).
    config_path:
        Config file used only when ``cell_size_deg`` is omitted.

    Returns
    -------
    pandas.DataFrame
        One row per cell-day, with sensor metrics side by side and an
        ``overlap_valid`` column. The input frame is not modified.
    """

    require_detection_columns(df)
    size = (
        load_cell_size_degrees(config_path)
        if cell_size_deg is None
        else _positive_cell_size(cell_size_deg)
    )
    prepared = df.copy()
    prepared["date"] = _calendar_dates(prepared["date"])
    assigned = assign_cells(prepared, size)
    aggregated = aggregate_cell_day(assigned)
    wide = pivot_cell_day(aggregated)
    return add_overlap_valid(wide)


def _default_config_path() -> Path:
    """Return the repository ``config.yaml`` path."""

    return Path(__file__).resolve().parents[2] / "config.yaml"


def _positive_cell_size(cell_size_deg: float) -> float:
    """Return ``cell_size_deg`` when it is a positive finite number."""

    if isinstance(cell_size_deg, bool) or isinstance(cell_size_deg, str):
        raise TypeError("cell_size_deg must be a positive number")
    if not math.isfinite(cell_size_deg) or cell_size_deg <= 0:
        raise ValueError("cell_size_deg must be a positive finite number")
    return float(cell_size_deg)


def _cell_size(cell_size_deg: float) -> Decimal:
    """Return the cell size as a decimal number of degrees."""

    size = _positive_cell_size(cell_size_deg)
    return Decimal(str(size))


def _edge_label(value: float, cell_size: Decimal, name: str) -> str:
    """Format the lower cell edge that contains ``value``."""

    if isinstance(value, bool) or isinstance(value, str):
        raise TypeError(f"{name} must be a real number")
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real number") from exc
    if not math.isfinite(coordinate):
        raise ValueError(f"{name} must be finite")
    steps = (Decimal(str(coordinate)) / cell_size).to_integral_value(rounding=ROUND_FLOOR)
    edge = steps * cell_size
    if edge == 0:
        edge = Decimal(0)
    places = _decimal_places(cell_size)
    return f"{edge:.{places}f}"


def _decimal_places(cell_size: Decimal) -> int:
    """Return the number of decimal places needed to print ``cell_size``."""

    exponent = cell_size.normalize().as_tuple().exponent
    if isinstance(exponent, str):
        return 0
    return max(0, -exponent)


def _sensor_label(value: object) -> str:
    """Return a stripped upper-case sensor name."""

    return str(value).strip().upper()


def _is_night(value: object) -> bool:
    """Return whether a FIRMS ``daynight`` value counts as night."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    if pd.isna(value):
        return False
    return str(value).strip().upper() in _NIGHT_LABELS


def _calendar_dates(dates: pd.Series) -> pd.Series:
    """Normalize a date column to calendar dates."""

    if dates.isna().any():
        raise ValueError("date contains null values")
    if dates.empty:
        return pd.Series(dtype="object", name="date")
    parsed = pd.to_datetime(dates, errors="raise")
    if parsed.dt.tz is not None:
        parsed = parsed.dt.tz_convert("UTC")
    return pd.Series(parsed.dt.date.to_numpy(), index=dates.index, name="date")


def _sensor_order(sensors: Iterable[object]) -> list[str]:
    """List MODIS, VIIRS, then any other sensors in alphabetical order."""

    labels = {_sensor_label(sensor) for sensor in sensors}
    extras = sorted(labels.difference(CANONICAL_SENSORS))
    return [*CANONICAL_SENSORS, *extras]


def _metric_column_names(sensors: Iterable[str]) -> list[str]:
    """Return wide metric column names for ``sensors``."""

    return [
        f"{metric}_{sensor}"
        for sensor in sensors
        for metric in METRIC_COLUMNS
    ]


def _flatten_pivot_columns(columns: pd.Index) -> list[str]:
    """Return ``metric_sensor`` names from a pivoted column index."""

    if not isinstance(columns, pd.MultiIndex):
        raise ValueError("Pivoted metrics must have a metric and sensor level")
    metric_names = set(METRIC_COLUMNS)
    first_level = set(columns.get_level_values(0))
    metric_first = len(first_level & metric_names) >= len(
        set(columns.get_level_values(1)) & metric_names
    )
    names: list[str] = []
    for left, right in columns:
        metric, sensor = (left, right) if metric_first else (right, left)
        names.append(f"{metric}_{sensor}")
    return names
