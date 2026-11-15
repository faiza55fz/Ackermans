"""Holdout evaluation and bootstrap prediction intervals for fire estimates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

import numpy as np
import pandas as pd

HoldoutStrategy = Literal["spatial", "temporal"]


@dataclass(frozen=True)
class HoldoutMetrics:
    """Performance metrics computed for one held-out group or pooled data.

    Attributes
    ----------
    holdout:
        Region or temporal period represented by the metrics; ``"overall"``
        for pooled holdout observations.
    n_observations:
        Number of evaluated observations.
    mae:
        Mean absolute error.
    rmse:
        Root mean squared error.
    bias:
        Mean prediction minus observed value.
    r2:
        Coefficient of determination, or ``None`` for constant actuals or
        fewer than two observations.
    """

    holdout: str
    n_observations: int
    mae: float
    rmse: float
    bias: float
    r2: float | None


@dataclass(frozen=True)
class HoldoutEvaluation:
    """Fold-level and pooled performance for spatial or temporal holdouts."""

    strategy: HoldoutStrategy
    folds: tuple[HoldoutMetrics, ...]
    overall: HoldoutMetrics


def grouped_holdout_splits(
    data: pd.DataFrame,
    *,
    strategy: HoldoutStrategy,
    region_col: str = "region",
    date_col: str = "date",
    temporal_frequency: str = "M",
) -> list[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Create leave-one-region or leave-one-period-out data splits.

    Each tuple contains the held-out group label, a training frame, and a
    test frame. Entire regions or temporal periods are excluded from
    training, respectively. Temporal grouping uses pandas period
    frequencies such as ``"M"`` (month) or ``"Y"`` (year).

    Parameters
    ----------
    data:
        Observations containing the grouping column and model inputs.
    strategy:
        ``"spatial"`` holds out each region; ``"temporal"`` holds out each
        period formed from ``date_col``.
    region_col:
        Region column used for spatial holdouts.
    date_col:
        Date column used for temporal holdouts.
    temporal_frequency:
        Pandas period frequency used to construct temporal blocks.

    Returns
    -------
    list[tuple[str, pandas.DataFrame, pandas.DataFrame]]
        Ordered ``(group_label, train, test)`` splits. Returned frames are
        copies and preserve their original indices.

    Raises
    ------
    ValueError
        If the strategy or required grouping values are invalid, or the
        input contains fewer than two groups.
    """
    if strategy not in ("spatial", "temporal"):
        raise ValueError("strategy must be 'spatial' or 'temporal'")
    if data.empty:
        raise ValueError("data must contain at least one observation")

    if strategy == "spatial":
        if region_col not in data.columns:
            raise ValueError(f"data is missing spatial grouping column {region_col!r}")
        groups = data[region_col]
        if groups.isna().any():
            raise ValueError(f"{region_col} values must not be missing")
        labels = groups.astype(str)
    else:
        if date_col not in data.columns:
            raise ValueError(f"data is missing temporal grouping column {date_col!r}")
        dates = pd.to_datetime(data[date_col], errors="coerce")
        if dates.isna().any():
            raise ValueError(f"{date_col} values must be valid, non-missing dates")
        try:
            labels = dates.dt.to_period(temporal_frequency).astype(str)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid temporal_frequency {temporal_frequency!r}"
            ) from exc

    unique_labels = sorted(labels.unique().tolist())
    if len(unique_labels) < 2:
        raise ValueError("at least two distinct groups are required for holdout splits")

    splits: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []
    for label in unique_labels:
        mask = labels == label
        train = data.loc[~mask].copy()
        test = data.loc[mask].copy()
        splits.append((str(label), train, test))
    return splits


def evaluate_holdout_performance(
    predictions: pd.DataFrame,
    *,
    actual_col: str,
    prediction_col: str,
    strategy: HoldoutStrategy,
    region_col: str = "region",
    date_col: str = "date",
    temporal_frequency: str = "M",
) -> HoldoutEvaluation:
    """Summarize errors for predictions from spatial or temporal holdouts.

    Rows are grouped by region for spatial evaluation or by the specified
    date period for temporal evaluation. The function assumes predictions
    were generated without training on their corresponding held-out group;
    :func:`grouped_holdout_splits` creates leakage-safe input splits.

    Metrics use ``prediction - actual`` as the signed error, so positive
    bias indicates overprediction. R² is ``None`` for a fold with fewer
    than two rows or constant actual values.

    Parameters
    ----------
    predictions:
        Frame of held-out observations containing actual and predicted
        values, plus the selected region or date field.
    actual_col:
        Column containing observed counts or FRP.
    prediction_col:
        Column containing model estimates in the same units.
    strategy:
        ``"spatial"`` or ``"temporal"`` fold grouping.
    region_col, date_col, temporal_frequency:
        Grouping options forwarded to temporal/spatial label generation.

    Returns
    -------
    HoldoutEvaluation
        Per-group metrics and pooled metrics across all observations.

    Raises
    ------
    ValueError
        If required columns or finite actual/predicted values are absent.
    """
    for column in (actual_col, prediction_col):
        if column not in predictions.columns:
            raise ValueError(f"predictions are missing column {column!r}")
    if predictions.empty:
        raise ValueError("predictions must contain at least one observation")

    actual = pd.to_numeric(predictions[actual_col], errors="coerce").to_numpy(dtype=float)
    predicted = pd.to_numeric(
        predictions[prediction_col], errors="coerce"
    ).to_numpy(dtype=float)
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("actual and predicted values must be finite numeric values")

    if strategy == "spatial":
        if region_col not in predictions.columns:
            raise ValueError(f"predictions are missing region column {region_col!r}")
        labels = predictions[region_col]
        if labels.isna().any():
            raise ValueError(f"{region_col} values must not be missing")
        labels = labels.astype(str).reset_index(drop=True)
    elif strategy == "temporal":
        if date_col not in predictions.columns:
            raise ValueError(f"predictions are missing date column {date_col!r}")
        dates = pd.to_datetime(predictions[date_col], errors="coerce")
        if dates.isna().any():
            raise ValueError(f"{date_col} values must be valid, non-missing dates")
        try:
            labels = dates.dt.to_period(temporal_frequency).astype(str)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid temporal_frequency {temporal_frequency!r}"
            ) from exc
        labels = labels.reset_index(drop=True)
    else:
        raise ValueError("strategy must be 'spatial' or 'temporal'")

    folds = tuple(
        _calculate_metrics(
            str(label),
            actual[labels.to_numpy() == label],
            predicted[labels.to_numpy() == label],
        )
        for label in sorted(labels.unique())
    )
    overall = _calculate_metrics("overall", actual, predicted)
    return HoldoutEvaluation(strategy=strategy, folds=folds, overall=overall)


def bootstrap_prediction_intervals(
    estimates: pd.DataFrame,
    calibration_residuals: pd.DataFrame,
    *,
    prediction_columns: Mapping[str, str],
    residual_columns: Mapping[str, str] | None = None,
    n_resamples: int = 200,
    confidence_level: float = 0.95,
    random_state: int | None = None,
    lower_suffix: str = "_lower",
    upper_suffix: str = "_upper",
) -> pd.DataFrame:
    """Attach residual-bootstrap prediction intervals to count or FRP estimates.

    For each requested variable, calibration residuals (observed minus
    predicted values on held-out data) are sampled with replacement. Each
    sampled residual is added to each point estimate; the requested
    percentile bounds across bootstrap draws form the prediction interval.
    Lower bounds are clipped at zero, appropriate for fire counts and FRP.

    Parameters
    ----------
    estimates:
        Frame containing model estimates to which intervals are attached.
    calibration_residuals:
        Frame containing held-out residuals. Residual columns must be
        present here and contain at least two finite values each.
    prediction_columns:
        Mapping from variable keys (for example ``"counts"`` or ``"frp"``)
        to estimate columns in *estimates*.
    residual_columns:
        Mapping from variable keys to residual columns in
        *calibration_residuals*. Defaults to ``{key: f"{key}_residual"}``.
    n_resamples:
        Number of residual bootstrap draws. Default is 200.
    confidence_level:
        Central interval coverage in ``(0, 1)``. Default is 0.95.
    random_state:
        Optional seed for reproducible resampling.
    lower_suffix, upper_suffix:
        Suffixes for generated interval-bound column names.

    Returns
    -------
    pandas.DataFrame
        Copy of *estimates* with ``<estimate>_lower`` and
        ``<estimate>_upper`` columns (or the configured suffixes).

    Raises
    ------
    ValueError
        If arguments, requested columns, estimates, or residual samples are
        invalid.
    """
    if estimates.empty:
        raise ValueError("estimates must contain at least one row")
    if not prediction_columns:
        raise ValueError("prediction_columns must contain at least one mapping")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not np.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be strictly between 0 and 1")
    residual_map = residual_columns or {
        key: f"{key}_residual" for key in prediction_columns
    }
    if set(residual_map) != set(prediction_columns):
        raise ValueError("residual_columns must have the same keys as prediction_columns")

    rng = np.random.default_rng(random_state)
    output = estimates.copy()
    tail = (1.0 - confidence_level) / 2.0
    for key, estimate_col in prediction_columns.items():
        residual_col = residual_map[key]
        if estimate_col not in estimates.columns:
            raise ValueError(f"estimates are missing column {estimate_col!r}")
        if residual_col not in calibration_residuals.columns:
            raise ValueError(
                f"calibration_residuals are missing column {residual_col!r}"
            )
        point_estimates = pd.to_numeric(estimates[estimate_col], errors="coerce").to_numpy(
            dtype=float
        )
        residuals = pd.to_numeric(
            calibration_residuals[residual_col], errors="coerce"
        ).to_numpy(dtype=float)
        if not np.isfinite(point_estimates).all():
            raise ValueError(f"{estimate_col} values must be finite numeric values")
        residuals = residuals[np.isfinite(residuals)]
        if len(residuals) < 2:
            raise ValueError(
                f"{residual_col} must contain at least two finite residuals"
            )

        sampled_residuals = rng.choice(
            residuals,
            size=(n_resamples, len(point_estimates)),
            replace=True,
        )
        bootstrap_values = np.maximum(
            0.0, point_estimates[np.newaxis, :] + sampled_residuals
        )
        output[f"{estimate_col}{lower_suffix}"] = np.quantile(
            bootstrap_values, tail, axis=0
        )
        output[f"{estimate_col}{upper_suffix}"] = np.quantile(
            bootstrap_values, 1.0 - tail, axis=0
        )
    return output


def _calculate_metrics(
    label: str,
    actual: np.ndarray,
    predicted: np.ndarray,
) -> HoldoutMetrics:
    """Compute MAE, RMSE, bias, and a guarded coefficient of determination."""
    errors = predicted - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    bias = float(np.mean(errors))
    r2: float | None = None
    if len(actual) >= 2:
        total_sum_squares = float(np.sum(np.square(actual - np.mean(actual))))
        if total_sum_squares > 0.0:
            residual_sum_squares = float(np.sum(np.square(errors)))
            r2 = float(1.0 - residual_sum_squares / total_sum_squares)
    return HoldoutMetrics(
        holdout=label,
        n_observations=len(actual),
        mae=mae,
        rmse=rmse,
        bias=bias,
        r2=r2,
    )
