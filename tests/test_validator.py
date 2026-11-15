"""Tests for model holdout evaluation and bootstrap intervals."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.validate.validator import (
    HoldoutEvaluation,
    HoldoutMetrics,
    bootstrap_prediction_intervals,
    evaluate_holdout_performance,
    grouped_holdout_splits,
)


@pytest.fixture
def holdout_predictions() -> pd.DataFrame:
    """Provide two-region, two-period predictions with known errors."""
    return pd.DataFrame(
        {
            "region": ["north", "north", "south", "south"],
            "date": pd.to_datetime(
                ["2020-01-03", "2020-02-03", "2020-01-05", "2020-02-05"]
            ),
            "observed": [1.0, 3.0, 2.0, 4.0],
            "predicted": [2.0, 2.0, 4.0, 3.0],
        }
    )


def test_spatial_grouped_splits_hold_out_complete_regions(
    holdout_predictions: pd.DataFrame,
) -> None:
    """Every spatial test fold is one whole region excluded from training."""
    splits = grouped_holdout_splits(holdout_predictions, strategy="spatial")

    assert [label for label, _, _ in splits] == ["north", "south"]
    for label, train, test in splits:
        assert set(test["region"]) == {label}
        assert label not in set(train["region"])
        assert len(train) + len(test) == len(holdout_predictions)


def test_temporal_grouped_splits_hold_out_complete_periods(
    holdout_predictions: pd.DataFrame,
) -> None:
    """Every temporal test fold holds out a full calendar month."""
    splits = grouped_holdout_splits(
        holdout_predictions,
        strategy="temporal",
        temporal_frequency="M",
    )

    assert [label for label, _, _ in splits] == ["2020-01", "2020-02"]
    for label, train, test in splits:
        assert set(pd.to_datetime(test["date"]).dt.to_period("M").astype(str)) == {
            label
        }
        assert label not in set(pd.to_datetime(train["date"]).dt.to_period("M").astype(str))


@pytest.mark.parametrize(
    ("strategy", "expected_labels"),
    [
        ("spatial", ["north", "south"]),
        ("temporal", ["2020-01", "2020-02"]),
    ],
)
def test_evaluate_holdout_performance_reports_metrics_by_fold_and_overall(
    holdout_predictions: pd.DataFrame,
    strategy: str,
    expected_labels: list[str],
) -> None:
    """MAE, RMSE, bias, and R2 are reported for each group and pooled."""
    evaluation = evaluate_holdout_performance(
        holdout_predictions,
        actual_col="observed",
        prediction_col="predicted",
        strategy=strategy,  # type: ignore[arg-type]
    )

    assert isinstance(evaluation, HoldoutEvaluation)
    assert [fold.holdout for fold in evaluation.folds] == expected_labels
    assert evaluation.overall.holdout == "overall"
    assert evaluation.overall.n_observations == 4
    assert evaluation.overall.mae == pytest.approx(1.25)
    assert evaluation.overall.rmse == pytest.approx(np.sqrt(1.75))
    assert evaluation.overall.bias == pytest.approx(0.25)
    assert evaluation.overall.r2 == pytest.approx(-0.4)
    assert all(fold.r2 is not None for fold in evaluation.folds)


def test_r2_is_none_for_singleton_fold(
    holdout_predictions: pd.DataFrame,
) -> None:
    """R2 is undefined for held-out groups with fewer than two observations."""
    data = holdout_predictions.iloc[[0, 2]].copy()
    evaluation = evaluate_holdout_performance(
        data,
        actual_col="observed",
        prediction_col="predicted",
        strategy="spatial",
    )

    assert all(fold.n_observations == 1 for fold in evaluation.folds)
    assert all(fold.r2 is None for fold in evaluation.folds)
    assert evaluation.overall.r2 is not None


def test_r2_is_none_for_constant_actual_values() -> None:
    """R2 is reported as None when the actual values have zero variance."""
    data = pd.DataFrame(
        {
            "region": ["a", "a", "b", "b"],
            "actual": [2.0, 2.0, 2.0, 2.0],
            "predicted": [1.0, 2.0, 3.0, 2.0],
        }
    )
    evaluation = evaluate_holdout_performance(
        data,
        actual_col="actual",
        prediction_col="predicted",
        strategy="spatial",
    )

    assert evaluation.overall.r2 is None


def test_metrics_have_expected_type(holdout_predictions: pd.DataFrame) -> None:
    """Fold and overall summaries use the documented result type."""
    evaluation = evaluate_holdout_performance(
        holdout_predictions,
        actual_col="observed",
        prediction_col="predicted",
        strategy="spatial",
    )

    assert isinstance(evaluation.folds[0], HoldoutMetrics)
    assert isinstance(evaluation.overall, HoldoutMetrics)


def test_bootstrap_intervals_for_counts_and_frp_are_reproducible() -> None:
    """Both estimate types receive bootstrap bounds with a stable seed."""
    estimates = pd.DataFrame(
        {"estimated_counts": [1.0, 10.0], "estimated_frp": [5.0, 50.0]}
    )
    residuals = pd.DataFrame(
        {
            "counts_residual": [-2.0, -1.0, 1.0, 3.0],
            "frp_residual": [-10.0, -5.0, 5.0, 15.0],
        }
    )
    kwargs = {
        "prediction_columns": {
            "counts": "estimated_counts",
            "frp": "estimated_frp",
        },
        "n_resamples": 200,
        "random_state": 42,
    }

    first = bootstrap_prediction_intervals(estimates, residuals, **kwargs)
    second = bootstrap_prediction_intervals(estimates, residuals, **kwargs)

    pd.testing.assert_frame_equal(first, second)
    for estimate_col in ("estimated_counts", "estimated_frp"):
        lower = first[f"{estimate_col}_lower"]
        upper = first[f"{estimate_col}_upper"]
        assert (lower <= first[estimate_col]).all()
        assert (upper >= first[estimate_col]).all()
        assert (lower <= upper).all()


def test_bootstrap_intervals_can_use_custom_residual_columns() -> None:
    """Custom residual mapping and interval suffixes are respected."""
    estimates = pd.DataFrame({"n_hat": [4.0, 8.0]})
    residuals = pd.DataFrame({"count_error": [-1.0, 1.0, 2.0]})
    result = bootstrap_prediction_intervals(
        estimates,
        residuals,
        prediction_columns={"counts": "n_hat"},
        residual_columns={"counts": "count_error"},
        n_resamples=500,
        confidence_level=0.8,
        random_state=4,
        lower_suffix="_lo",
        upper_suffix="_hi",
    )

    assert {"n_hat_lo", "n_hat_hi"} <= set(result.columns)
    assert (result["n_hat_lo"] >= 0.0).all()


def test_bootstrap_intervals_preserve_estimate_input() -> None:
    """Interval generation returns a copy without mutating its input."""
    estimates = pd.DataFrame({"predicted": [3.0, 5.0]})
    original = estimates.copy()
    residuals = pd.DataFrame({"value_residual": [-1.0, 1.0]})

    bootstrap_prediction_intervals(
        estimates,
        residuals,
        prediction_columns={"value": "predicted"},
        n_resamples=10,
        random_state=0,
    )

    pd.testing.assert_frame_equal(estimates, original)


@pytest.mark.parametrize("strategy", ["other", "", None])
def test_invalid_holdout_strategy_raises(
    holdout_predictions: pd.DataFrame,
    strategy: object,
) -> None:
    """Unsupported holdout strategies fail with a clear error."""
    with pytest.raises(ValueError, match="strategy"):
        grouped_holdout_splits(
            holdout_predictions,
            strategy=strategy,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="strategy"):
        evaluate_holdout_performance(
            holdout_predictions,
            actual_col="observed",
            prediction_col="predicted",
            strategy=strategy,  # type: ignore[arg-type]
        )


def test_splits_require_two_groups_and_complete_labels(
    holdout_predictions: pd.DataFrame,
) -> None:
    """A split fails rather than silently dropping null or single groups."""
    with pytest.raises(ValueError, match="at least two"):
        grouped_holdout_splits(
            holdout_predictions.assign(region="one"),
            strategy="spatial",
        )
    with pytest.raises(ValueError, match="must not be missing"):
        grouped_holdout_splits(
            holdout_predictions.assign(region=["north", None, "south", "south"]),
            strategy="spatial",
        )
    with pytest.raises(ValueError, match="valid, non-missing dates"):
        grouped_holdout_splits(
            holdout_predictions.assign(
                date=pd.to_datetime(["2020-01-03", None, "2020-01-05", None])
            ),
            strategy="temporal",
        )


def test_holdout_evaluation_validates_columns_and_values(
    holdout_predictions: pd.DataFrame,
) -> None:
    """Missing columns and non-finite target/prediction values are rejected."""
    with pytest.raises(ValueError, match="observed"):
        evaluate_holdout_performance(
            holdout_predictions.drop(columns="observed"),
            actual_col="observed",
            prediction_col="predicted",
            strategy="spatial",
        )
    with pytest.raises(ValueError, match="finite numeric"):
        evaluate_holdout_performance(
            holdout_predictions.assign(predicted=np.nan),
            actual_col="observed",
            prediction_col="predicted",
            strategy="spatial",
        )


@pytest.mark.parametrize(
    ("n_resamples", "confidence_level"),
    [(0, 0.95), (True, 0.95), (5, 0.0), (5, 1.0)],
)
def test_bootstrap_validates_resampling_options(
    n_resamples: object,
    confidence_level: float,
) -> None:
    """Invalid bootstrap counts and confidence levels are rejected."""
    with pytest.raises(ValueError):
        bootstrap_prediction_intervals(
            pd.DataFrame({"estimate": [1.0]}),
            pd.DataFrame({"value_residual": [0.0, 1.0]}),
            prediction_columns={"value": "estimate"},
            n_resamples=n_resamples,  # type: ignore[arg-type]
            confidence_level=confidence_level,
        )


def test_bootstrap_requires_residual_samples_and_matching_keys() -> None:
    """Each requested estimate must have a usable corresponding residual."""
    estimates = pd.DataFrame({"estimate": [2.0]})
    with pytest.raises(ValueError, match="same keys"):
        bootstrap_prediction_intervals(
            estimates,
            pd.DataFrame({"residual": [0.0, 1.0]}),
            prediction_columns={"value": "estimate"},
            residual_columns={"other": "residual"},
        )
    with pytest.raises(ValueError, match="at least two finite"):
        bootstrap_prediction_intervals(
            estimates,
            pd.DataFrame({"value_residual": [np.nan, 1.0]}),
            prediction_columns={"value": "estimate"},
        )
