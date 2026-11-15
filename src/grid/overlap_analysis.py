"""Overlap-period diagnostics for the MODIS/VIIRS cell-day grid.

Operates on the **wide** cell-day table produced by
:func:`src.grid.grid_builder.build_cell_day_table`.  Every function
expects that table to have already received the ``overlap_valid`` column
added by :func:`src.grid.grid_builder.add_overlap_valid`.

Three public functions are provided:

* :func:`compute_sensor_ratios` – VIIRS-to-MODIS count and FRP ratios
  restricted to days when both sensors fired (``overlap_valid == True``).
* :func:`check_overdispersion` – variance-to-mean ratio for MODIS and
  VIIRS detection counts, used to decide between Poisson and Negative
  Binomial regression.
* :func:`generate_overlap_diagnostics` – writes a JSON summary report
  that bundles the two analyses above.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Required columns
# ---------------------------------------------------------------------------

_OVERLAP_REQUIRED: tuple[str, ...] = (
    "n_detections_MODIS",
    "n_detections_VIIRS",
    "overlap_valid",
)

_FRP_COLUMNS: tuple[str, str] = ("mean_frp_MODIS", "mean_frp_VIIRS")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_sensor_ratios(cell_day_df: pd.DataFrame) -> dict[str, float | None]:
    """Compute VIIRS-to-MODIS detection-count and FRP ratios during overlap.

    Only rows where ``overlap_valid`` is truthy are included; all other
    rows are ignored.  FRP ratios are computed only when both sensors
    have non-missing ``mean_frp`` values on the same row.

    Parameters
    ----------
    cell_day_df:
        Wide cell-day table with at least the columns
        ``n_detections_MODIS``, ``n_detections_VIIRS``,
        ``overlap_valid``, ``mean_frp_MODIS``, and ``mean_frp_VIIRS``.
        Missing FRP columns are tolerated; FRP ratio is then ``None``.

    Returns
    -------
    dict[str, float | None]
        A dictionary with the following keys:

        ``overlap_days``
            Number of cell-day rows where ``overlap_valid`` is true.
        ``count_ratio_mean``
            Mean of the per-row ratio ``n_detections_VIIRS /
            n_detections_MODIS``.  ``None`` when no valid rows exist.
        ``count_ratio_median``
            Median of the same per-row ratios.  ``None`` when no valid
            rows exist.
        ``frp_ratio_mean``
            Mean of ``mean_frp_VIIRS / mean_frp_MODIS`` across rows
            where both FRP values are finite and the MODIS value is
            non-zero.  ``None`` when neither FRP column is present or no
            valid paired rows exist.
        ``frp_ratio_median``
            Median of the same per-row FRP ratios.  ``None`` when no
            valid paired rows exist.

    Raises
    ------
    ValueError
        When any of ``n_detections_MODIS``, ``n_detections_VIIRS``, or
        ``overlap_valid`` is absent from *cell_day_df*.
    """
    _require_columns(cell_day_df, _OVERLAP_REQUIRED)

    overlap = cell_day_df.loc[cell_day_df["overlap_valid"].astype(bool)].copy()
    n_overlap = int(len(overlap))

    if n_overlap == 0:
        return {
            "overlap_days": 0,
            "count_ratio_mean": None,
            "count_ratio_median": None,
            "frp_ratio_mean": None,
            "frp_ratio_median": None,
        }

    # --- detection count ratios -------------------------------------------
    modis_counts = overlap["n_detections_MODIS"].astype(float)
    viirs_counts = overlap["n_detections_VIIRS"].astype(float)

    # Avoid division by zero; rows with MODIS count == 0 are excluded from
    # the ratio (they cannot be valid overlap rows by definition, but we
    # guard defensively).
    valid_count_mask = modis_counts > 0
    count_ratios = viirs_counts[valid_count_mask] / modis_counts[valid_count_mask]

    count_ratio_mean: float | None = (
        float(count_ratios.mean()) if len(count_ratios) > 0 else None
    )
    count_ratio_median: float | None = (
        float(count_ratios.median()) if len(count_ratios) > 0 else None
    )

    # --- FRP ratios ----------------------------------------------------------
    frp_ratio_mean: float | None = None
    frp_ratio_median: float | None = None

    has_modis_frp = "mean_frp_MODIS" in overlap.columns
    has_viirs_frp = "mean_frp_VIIRS" in overlap.columns

    if has_modis_frp and has_viirs_frp:
        modis_frp = overlap["mean_frp_MODIS"].astype(float)
        viirs_frp = overlap["mean_frp_VIIRS"].astype(float)
        frp_valid = (
            modis_frp.notna()
            & viirs_frp.notna()
            & modis_frp.apply(math.isfinite)
            & viirs_frp.apply(math.isfinite)
            & (modis_frp > 0)
        )
        paired_ratios = viirs_frp[frp_valid] / modis_frp[frp_valid]
        if len(paired_ratios) > 0:
            frp_ratio_mean = float(paired_ratios.mean())
            frp_ratio_median = float(paired_ratios.median())

    return {
        "overlap_days": n_overlap,
        "count_ratio_mean": count_ratio_mean,
        "count_ratio_median": count_ratio_median,
        "frp_ratio_mean": frp_ratio_mean,
        "frp_ratio_median": frp_ratio_median,
    }


def check_overdispersion(
    cell_day_df: pd.DataFrame,
) -> dict[str, dict[str, float | None]]:
    """Compute variance-to-mean ratios for MODIS and VIIRS detection counts.

    The variance-to-mean ratio (VMR, also called the *index of
    dispersion*) is 1 for a Poisson distribution.  A VMR substantially
    greater than 1 indicates overdispersion, suggesting that a Negative
    Binomial model is preferable.

    Analysis is performed on **all** rows (not just overlap rows) so
    that the full marginal distributions are characterised.  A second
    analysis is also performed restricted to ``overlap_valid == True``
    rows.

    Parameters
    ----------
    cell_day_df:
        Wide cell-day table with ``n_detections_MODIS``,
        ``n_detections_VIIRS``, and ``overlap_valid``.

    Returns
    -------
    dict[str, dict[str, float | None]]
        A two-level dict keyed first by scope (``"all"`` or
        ``"overlap"``), then by sensor label (``"MODIS"`` or
        ``"VIIRS"``).  Each inner dict contains:

        ``n``
            Number of non-null rows used.
        ``mean``
            Arithmetic mean of the counts.
        ``variance``
            Sample variance (ddof=1) of the counts.  ``None`` when
            fewer than two rows are available.
        ``vmr``
            Variance-to-mean ratio.  ``None`` when ``mean == 0`` or
            fewer than two rows are available.
        ``overdispersed``
            ``True`` when ``vmr > 1``, ``False`` when ``vmr <= 1``,
            ``None`` when ``vmr`` cannot be computed.

    Raises
    ------
    ValueError
        When any of ``n_detections_MODIS``, ``n_detections_VIIRS``, or
        ``overlap_valid`` is absent from *cell_day_df*.
    """
    _require_columns(cell_day_df, _OVERLAP_REQUIRED)

    overlap_mask = cell_day_df["overlap_valid"].astype(bool)

    return {
        "all": {
            "MODIS": _vmr_stats(cell_day_df["n_detections_MODIS"]),
            "VIIRS": _vmr_stats(cell_day_df["n_detections_VIIRS"]),
        },
        "overlap": {
            "MODIS": _vmr_stats(cell_day_df.loc[overlap_mask, "n_detections_MODIS"]),
            "VIIRS": _vmr_stats(cell_day_df.loc[overlap_mask, "n_detections_VIIRS"]),
        },
    }


def generate_overlap_diagnostics(
    cell_day_df: pd.DataFrame,
    output_dir: Path | str,
) -> Path:
    """Export a JSON diagnostic report for the overlap period.

    The report bundles the results of :func:`compute_sensor_ratios` and
    :func:`check_overdispersion` into a single JSON file.  The file is
    written to *output_dir* and named ``overlap_diagnostics.json``.

    The output directory is created if it does not already exist.  An
    existing ``overlap_diagnostics.json`` file in that directory is
    overwritten.

    Parameters
    ----------
    cell_day_df:
        Wide cell-day table passed unchanged to the two analysis
        functions.
    output_dir:
        Directory in which to write ``overlap_diagnostics.json``.

    Returns
    -------
    pathlib.Path
        Absolute path of the written JSON file.

    Raises
    ------
    ValueError
        When *cell_day_df* is missing any required column (propagated
        from the analysis functions).
    NotADirectoryError
        When *output_dir* exists but is a regular file.
    """
    out_path = Path(output_dir).resolve()

    if out_path.is_file():
        raise NotADirectoryError(
            f"output_dir must be a directory, got a file: {out_path}"
        )
    out_path.mkdir(parents=True, exist_ok=True)

    ratios = compute_sensor_ratios(cell_day_df)
    dispersion = check_overdispersion(cell_day_df)

    total_rows = int(len(cell_day_df))
    total_overlap = int(cell_day_df["overlap_valid"].astype(bool).sum())

    report: dict[str, Any] = {
        "summary": {
            "total_cell_days": total_rows,
            "overlap_valid_cell_days": total_overlap,
            "overlap_fraction": (
                round(total_overlap / total_rows, 6) if total_rows > 0 else None
            ),
        },
        "sensor_ratios": ratios,
        "overdispersion": dispersion,
    }

    dest = out_path / "overlap_diagnostics.json"
    with dest.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, allow_nan=False, default=_json_default)

    return dest


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    """Raise ``ValueError`` listing every column absent from *df*."""
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(
            "Cell-day table is missing columns: " + ", ".join(missing)
        )


def _vmr_stats(series: pd.Series) -> dict[str, float | None]:
    """Return VMR statistics for one detection-count column."""
    counts = series.dropna().astype(float)
    n = int(len(counts))

    if n == 0:
        return {"n": 0, "mean": None, "variance": None, "vmr": None, "overdispersed": None}

    mean_val = float(counts.mean())

    if n < 2:
        return {
            "n": n,
            "mean": mean_val,
            "variance": None,
            "vmr": None,
            "overdispersed": None,
        }

    var_val = float(counts.var(ddof=1))

    if mean_val == 0:
        vmr: float | None = None
        overdispersed: bool | None = None
    else:
        vmr = var_val / mean_val
        overdispersed = vmr > 1.0

    return {
        "n": n,
        "mean": mean_val,
        "variance": var_val,
        "vmr": vmr,
        "overdispersed": overdispersed,
    }


def _json_default(obj: object) -> object:
    """Serialise numpy scalar types to plain Python."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")
