"""Calibrate MODIS Fire Radiative Power (FRP) to VIIRS FRP measurements.

The module supports log-linear regression, a Gaussian generalized linear
model, and empirical quantile mapping. Calibration models are fitted at
region-month and region levels where enough paired observations exist,
with a global model as the final fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
import statsmodels.api as sm

CalibrationMethod = Literal["log_linear", "gaussian", "quantile_mapping"]
FallbackLevel = Literal["region_month", "region", "global"]


@dataclass(frozen=True)
class _RegressionCalibration:
    """Fitted statsmodels regression used by a calibration group."""

    result: object
    log_scale: bool

    def predict(self, modis_frp: float) -> float:
        """Return a non-negative calibrated estimate for one input."""
        predictor = np.log(modis_frp) if self.log_scale else modis_frp
        design = sm.add_constant(np.array([[predictor]], dtype=float), has_constant="add")
        prediction = float(np.asarray(self.result.predict(design)).reshape(-1)[0])  # type: ignore[attr-defined]
        if self.log_scale:
            prediction = float(np.exp(prediction))
        return max(0.0, prediction)


@dataclass(frozen=True)
class _QuantileCalibration:
    """Empirical MODIS-to-VIIRS quantile mapping."""

    source_quantiles: np.ndarray
    target_quantiles: np.ndarray

    def predict(self, modis_frp: float) -> float:
        """Interpolate the empirical mapping, clamping outside its range."""
        return max(
            0.0,
            float(
                np.interp(
                    modis_frp, self.source_quantiles, self.target_quantiles
                )
            ),
        )


_Calibration = _RegressionCalibration | _QuantileCalibration


@dataclass(frozen=True)
class FRPCalibrator:
    """Fitted FRP calibrations at region-month, region, and global levels.

    Attributes
    ----------
    method:
        Calibration technique used.
    modis_col:
        MODIS FRP input column used during fitting.
    viirs_col:
        VIIRS FRP response column used during fitting.
    region_col:
        Region label column used to build hierarchical calibrations.
    month_col:
        Month column used to build region-month calibrations.
    region_month_models:
        Models keyed by ``(region, month)`` for groups with sufficient data.
    region_models:
        Models keyed by region for groups with sufficient data.
    global_model:
        Calibration trained on all valid paired observations.
    """

    method: CalibrationMethod
    modis_col: str
    viirs_col: str
    region_col: str
    month_col: str
    region_month_models: dict[tuple[str, int], _Calibration]
    region_models: dict[str, _Calibration]
    global_model: _Calibration


def fit_frp_calibrator(
    training_data: pd.DataFrame,
    *,
    method: CalibrationMethod = "log_linear",
    modis_col: str = "mean_frp_MODIS",
    viirs_col: str = "mean_frp_VIIRS",
    region_col: str = "region",
    month_col: str = "month",
    min_samples: int = 3,
) -> FRPCalibrator:
    """Fit hierarchical FRP calibration models from paired sensor data.

    Invalid or non-positive FRP pairs are excluded. Both region and month
    are required in training data; rows without valid grouping labels are
    still included in the global calibration.

    Parameters
    ----------
    training_data:
        Paired MODIS and VIIRS measurements with region and month columns.
    method:
        ``"log_linear"`` fits OLS to log VIIRS FRP versus log MODIS FRP;
        ``"gaussian"`` fits a Gaussian GLM with identity link; and
        ``"quantile_mapping"`` interpolates paired empirical quantiles.
    modis_col, viirs_col:
        Names of the input and target FRP columns.
    region_col, month_col:
        Names of the spatial and temporal grouping columns.
    min_samples:
        Minimum number of valid pairs needed to fit a region or
        region-month model. Must be at least three. The global model
        always needs this many pairs.

    Returns
    -------
    FRPCalibrator
        Fitted calibrator with available models at each fallback level.

    Raises
    ------
    ValueError
        If required columns are absent, arguments are invalid, or too few
        valid pairs remain for the global model.
    """
    if method not in ("log_linear", "gaussian", "quantile_mapping"):
        raise ValueError(f"Unknown FRP calibration method: {method!r}")
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 3:
        raise ValueError("min_samples must be an integer greater than or equal to 3")

    required = (modis_col, viirs_col, region_col, month_col)
    missing = [column for column in required if column not in training_data.columns]
    if missing:
        raise ValueError("Training data is missing columns: " + ", ".join(missing))

    valid = _valid_frp_pairs(training_data, modis_col, viirs_col)
    if len(valid) < min_samples:
        raise ValueError(
            f"At least {min_samples} valid positive FRP pairs are required "
            "for global calibration"
        )

    global_model = _fit_calibration(valid[modis_col].to_numpy(), valid[viirs_col].to_numpy(), method)
    region_models: dict[str, _Calibration] = {}
    region_month_models: dict[tuple[str, int], _Calibration] = {}

    grouped = valid.assign(
        _region=valid[region_col].map(_clean_region),
        _month=valid[month_col].map(_clean_month),
    )
    grouped_region = grouped.loc[grouped["_region"].notna()]
    for region, group in grouped_region.groupby("_region", sort=True):
        if len(group) >= min_samples:
            region_models[str(region)] = _fit_calibration(
                group[modis_col].to_numpy(),
                group[viirs_col].to_numpy(),
                method,
            )

    grouped_region_month = grouped.loc[
        grouped["_region"].notna() & grouped["_month"].notna()
    ]
    for (region, month), group in grouped_region_month.groupby(
        ["_region", "_month"], sort=True
    ):
        if len(group) >= min_samples:
            region_month_models[(str(region), int(month))] = _fit_calibration(
                group[modis_col].to_numpy(),
                group[viirs_col].to_numpy(),
                method,
            )

    return FRPCalibrator(
        method=method,
        modis_col=modis_col,
        viirs_col=viirs_col,
        region_col=region_col,
        month_col=month_col,
        region_month_models=region_month_models,
        region_models=region_models,
        global_model=global_model,
    )


def predict_frp(
    calibrator: FRPCalibrator,
    observations: pd.DataFrame,
    *,
    prediction_col: str = "calibrated_frp",
    fallback_col: str = "fallback_level",
) -> pd.DataFrame:
    """Predict calibrated VIIRS FRP and record the fallback used per row.

    Each row uses the most specific available model: region-month, then
    region, then global. Missing or unknown grouping values naturally
    fall through to a less-specific model. The input frame is not modified.

    Parameters
    ----------
    calibrator:
        Fitted FRP calibrator returned by :func:`fit_frp_calibrator`.
    observations:
        Frame containing the MODIS FRP column. Region and month columns
        are optional; if absent, global calibration is used.
    prediction_col:
        Name for the output calibrated FRP column.
    fallback_col:
        Name for the output fallback-level column.

    Returns
    -------
    pandas.DataFrame
        Copy of *observations* with prediction and fallback columns.

    Raises
    ------
    ValueError
        If required input values are absent, non-finite, or non-positive.
    """
    if calibrator.modis_col not in observations.columns:
        raise ValueError(f"Observations are missing column {calibrator.modis_col!r}")
    if prediction_col == fallback_col:
        raise ValueError("prediction_col and fallback_col must be different")

    modis_values = pd.to_numeric(observations[calibrator.modis_col], errors="coerce")
    if not np.isfinite(modis_values.to_numpy(dtype=float)).all() or (modis_values <= 0).any():
        raise ValueError(f"{calibrator.modis_col} values must be finite and positive")

    output = observations.copy()
    predictions: list[float] = []
    levels: list[FallbackLevel] = []
    has_region = calibrator.region_col in observations.columns
    has_month = calibrator.month_col in observations.columns

    for position, modis_value in enumerate(modis_values.to_numpy(dtype=float)):
        region = (
            _clean_region(observations[calibrator.region_col].iloc[position])
            if has_region
            else None
        )
        month = (
            _clean_month(observations[calibrator.month_col].iloc[position])
            if has_month
            else None
        )

        model: _Calibration
        level: FallbackLevel
        if region is not None and month is not None:
            model = calibrator.region_month_models.get((region, month), calibrator.global_model)
            if (region, month) in calibrator.region_month_models:
                level = "region_month"
            elif region in calibrator.region_models:
                model = calibrator.region_models[region]
                level = "region"
            else:
                level = "global"
        elif region is not None and region in calibrator.region_models:
            model = calibrator.region_models[region]
            level = "region"
        else:
            model = calibrator.global_model
            level = "global"

        predictions.append(model.predict(float(modis_value)))
        levels.append(level)

    output[prediction_col] = predictions
    output[fallback_col] = levels
    return output


def _valid_frp_pairs(
    data: pd.DataFrame,
    modis_col: str,
    viirs_col: str,
) -> pd.DataFrame:
    """Return rows with finite, positive paired FRP values."""
    valid = data.copy()
    valid[modis_col] = pd.to_numeric(valid[modis_col], errors="coerce")
    valid[viirs_col] = pd.to_numeric(valid[viirs_col], errors="coerce")
    mask = (
        np.isfinite(valid[modis_col].to_numpy(dtype=float))
        & np.isfinite(valid[viirs_col].to_numpy(dtype=float))
        & (valid[modis_col] > 0)
        & (valid[viirs_col] > 0)
    )
    return valid.loc[mask].copy()


def _fit_calibration(
    modis_frp: np.ndarray,
    viirs_frp: np.ndarray,
    method: CalibrationMethod,
) -> _Calibration:
    """Fit one requested calibration technique."""
    if method == "quantile_mapping":
        probabilities = np.linspace(0.0, 1.0, max(100, len(modis_frp)))
        source = np.quantile(modis_frp, probabilities)
        target = np.quantile(viirs_frp, probabilities)
        unique_source, inverse = np.unique(source, return_inverse=True)
        target_sum = np.bincount(inverse, weights=target)
        target_count = np.bincount(inverse)
        unique_target = target_sum / target_count
        return _QuantileCalibration(unique_source, unique_target)

    log_scale = method == "log_linear"
    x = np.log(modis_frp) if log_scale else modis_frp
    y = np.log(viirs_frp) if log_scale else viirs_frp
    design = sm.add_constant(x, has_constant="add")
    if log_scale:
        fitted = sm.OLS(y, design).fit()
    else:
        fitted = sm.GLM(y, design, family=sm.families.Gaussian()).fit()
    return _RegressionCalibration(fitted, log_scale)


def _clean_region(value: object) -> str | None:
    """Normalize a region label, returning None for missing or blank values."""
    if pd.isna(value):
        return None
    region = str(value).strip()
    return region or None


def _clean_month(value: object) -> int | None:
    """Normalize valid calendar month values, returning None otherwise."""
    if pd.isna(value):
        return None
    try:
        month = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if month != value or not 1 <= month <= 12:
        return None
    return month
