"""Tests for hierarchical FRP calibration methods."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.models.frp import FRPCalibrator, fit_frp_calibrator, predict_frp


@pytest.fixture
def training_data() -> pd.DataFrame:
    """Provide sparse groups that exercise each level of the fallback ladder."""
    return pd.DataFrame(
        {
            "mean_frp_MODIS": [1.0, 2.0, 3.0, 4.0, 5.0],
            "mean_frp_VIIRS": [2.0, 4.1, 5.9, 7.5, 10.5],
            "region": ["A", "A", "A", "A", "B"],
            "month": [1, 1, 1, 2, 1],
            "sample": ["a1", "a2", "a3", "a4", "b1"],
        }
    )


@pytest.mark.parametrize(
    "method",
    ["log_linear", "gaussian", "quantile_mapping"],
)
def test_fit_and_predict_all_calibration_methods(
    training_data: pd.DataFrame,
    method: str,
) -> None:
    """Each method returns finite, non-negative estimates."""
    calibrator = fit_frp_calibrator(training_data, method=method)  # type: ignore[arg-type]
    predictions = predict_frp(
        calibrator,
        pd.DataFrame(
            {
                "mean_frp_MODIS": [1.5, 2.5],
                "region": ["A", "unknown"],
                "month": [1, 3],
            }
        ),
    )

    assert isinstance(calibrator, FRPCalibrator)
    assert np.isfinite(predictions["calibrated_frp"]).all()
    assert (predictions["calibrated_frp"] >= 0).all()


def test_fallback_ladder_records_level_per_prediction(
    training_data: pd.DataFrame,
) -> None:
    """Predictions select region-month, region, then global calibration."""
    calibrator = fit_frp_calibrator(training_data, method="gaussian")
    observations = pd.DataFrame(
        {
            "mean_frp_MODIS": [1.5, 2.5, 3.5, 1.5],
            "region": ["A", "A", "B", "unknown"],
            "month": [1, 2, 1, 1],
        },
        index=[10, 11, 12, 13],
    )
    original = observations.copy()

    predictions = predict_frp(calibrator, observations)

    assert list(predictions.index) == [10, 11, 12, 13]
    assert predictions["fallback_level"].tolist() == [
        "region_month",
        "region",
        "global",
        "global",
    ]
    assert predictions.loc[10, "calibrated_frp"] == pytest.approx(3.05, abs=0.1)
    pd.testing.assert_frame_equal(observations, original)


def test_region_fallback_used_when_month_is_missing(
    training_data: pd.DataFrame,
) -> None:
    """A usable region model applies when month is absent from predictions."""
    calibrator = fit_frp_calibrator(training_data)
    predictions = predict_frp(
        calibrator,
        pd.DataFrame({"mean_frp_MODIS": [2.0], "region": ["A"]}),
    )

    assert predictions.loc[0, "fallback_level"] == "region"


def test_missing_group_columns_use_global_model(
    training_data: pd.DataFrame,
) -> None:
    """Prediction frames need only the MODIS FRP value."""
    calibrator = fit_frp_calibrator(training_data)
    predictions = predict_frp(
        calibrator,
        pd.DataFrame({"mean_frp_MODIS": [2.0]}),
    )

    assert predictions.loc[0, "fallback_level"] == "global"
    assert predictions.loc[0, "calibrated_frp"] == pytest.approx(4.0, abs=0.01)


def test_fit_uses_custom_measurement_and_group_columns() -> None:
    """Column-name options support alternate input schemas."""
    data = pd.DataFrame(
        {
            "sensor_a": [1.0, 2.0, 3.0],
            "sensor_b": [3.1, 5.8, 9.2],
            "area": ["north", "north", "north"],
            "period": [1, 1, 1],
        }
    )
    calibrator = fit_frp_calibrator(
        data,
        method="gaussian",
        modis_col="sensor_a",
        viirs_col="sensor_b",
        region_col="area",
        month_col="period",
    )

    predictions = predict_frp(
        calibrator,
        pd.DataFrame({"sensor_a": [2.0], "area": ["north"], "period": [1]}),
    )
    assert predictions.loc[0, "calibrated_frp"] == pytest.approx(5.9, abs=0.2)
    assert predictions.loc[0, "fallback_level"] == "region_month"


def test_invalid_pairs_are_excluded_from_training() -> None:
    """Null, infinite, and non-positive pairs do not enter the calibration."""
    data = pd.DataFrame(
        {
            "mean_frp_MODIS": [1.0, 2.0, 3.0, 0.0, np.nan, np.inf],
            "mean_frp_VIIRS": [2.0, 4.0, 5.5, 2.0, 3.0, 3.0],
            "region": ["A"] * 6,
            "month": [1] * 6,
        }
    )

    calibrator = fit_frp_calibrator(data)

    assert calibrator.region_month_models
    with pytest.raises(ValueError, match="At least 4"):
        fit_frp_calibrator(data, min_samples=4)


@pytest.mark.parametrize("method", ["unknown", "", None])
def test_invalid_method_raises(training_data: pd.DataFrame, method: object) -> None:
    """Unsupported calibration methods fail clearly."""
    with pytest.raises(ValueError, match="Unknown FRP calibration method"):
        fit_frp_calibrator(training_data, method=method)  # type: ignore[arg-type]


@pytest.mark.parametrize("min_samples", [0, 1, 2, 2.5, True])
def test_invalid_min_samples_raises(
    training_data: pd.DataFrame,
    min_samples: object,
) -> None:
    """The minimum group size must be an integer of at least three."""
    with pytest.raises(ValueError, match="min_samples"):
        fit_frp_calibrator(
            training_data,
            min_samples=min_samples,  # type: ignore[arg-type]
        )


def test_missing_training_column_raises(training_data: pd.DataFrame) -> None:
    """Missing required schema fields are reported."""
    with pytest.raises(ValueError, match="mean_frp_VIIRS"):
        fit_frp_calibrator(training_data.drop(columns="mean_frp_VIIRS"))


def test_too_few_valid_pairs_for_global_model_raises() -> None:
    """Global calibration cannot be fitted without enough valid pairs."""
    data = pd.DataFrame(
        {
            "mean_frp_MODIS": [1.0, 0.0],
            "mean_frp_VIIRS": [2.0, 3.0],
            "region": ["A", "A"],
            "month": [1, 1],
        }
    )

    with pytest.raises(ValueError, match="valid positive FRP pairs"):
        fit_frp_calibrator(data)


def test_prediction_rejects_missing_or_invalid_modis_values(
    training_data: pd.DataFrame,
) -> None:
    """Prediction inputs must contain positive finite MODIS FRP values."""
    calibrator = fit_frp_calibrator(training_data)
    with pytest.raises(ValueError, match="mean_frp_MODIS"):
        predict_frp(calibrator, pd.DataFrame({"other": [1.0]}))

    for bad_value in [0.0, -1.0, np.nan, np.inf]:
        with pytest.raises(ValueError, match="finite and positive"):
            predict_frp(
                calibrator,
                pd.DataFrame({"mean_frp_MODIS": [bad_value]}),
            )


def test_output_column_names_are_configurable(
    training_data: pd.DataFrame,
) -> None:
    """Callers can choose names for the prediction and fallback columns."""
    calibrator = fit_frp_calibrator(training_data)
    predictions = predict_frp(
        calibrator,
        pd.DataFrame({"mean_frp_MODIS": [2.0]}),
        prediction_col="estimated_viirs",
        fallback_col="used_level",
    )

    assert "estimated_viirs" in predictions
    assert "used_level" in predictions


def test_identical_output_column_names_raise(
    training_data: pd.DataFrame,
) -> None:
    """Prediction and fallback output columns cannot overwrite one another."""
    calibrator = fit_frp_calibrator(training_data)
    with pytest.raises(ValueError, match="must be different"):
        predict_frp(
            calibrator,
            pd.DataFrame({"mean_frp_MODIS": [2.0]}),
            prediction_col="same",
            fallback_col="same",
        )


def test_quantile_mapping_is_monotonic_and_clamps_to_training_range() -> None:
    """Empirical mapping is monotonic and does not extrapolate beyond endpoints."""
    data = pd.DataFrame(
        {
            "mean_frp_MODIS": [1.0, 2.0, 3.0, 4.0],
            "mean_frp_VIIRS": [2.0, 3.0, 8.0, 10.0],
            "region": ["A"] * 4,
            "month": [1] * 4,
        }
    )
    calibrator = fit_frp_calibrator(data, method="quantile_mapping")
    predictions = predict_frp(
        calibrator,
        pd.DataFrame({"mean_frp_MODIS": [0.5, 1.5, 2.5, 5.0]}),
    )

    estimates = predictions["calibrated_frp"].to_numpy()
    assert np.all(np.diff(estimates) >= 0)
    assert estimates[0] == pytest.approx(2.0)
    assert estimates[-1] == pytest.approx(10.0)
