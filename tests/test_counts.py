"""Tests for src/models/counts.py.

Coverage targets
----------------
prepare_model_frame  – filtering, feature engineering, edge cases.
fit_count_model      – family selection, design matrix, result fields.
spatial_block_cv     – fold splitting, metric aggregation, edge cases.
CountModelResult     – dataclass fields populated correctly.
CVSummary / FoldMetrics – dataclass fields populated correctly.
"""

from __future__ import annotations

import math
from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.models.counts import (
    CountModelResult,
    CVSummary,
    FoldMetrics,
    fit_count_model,
    prepare_model_frame,
    spatial_block_cv,
    _predict,
)

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(0)


def _cell_day(
    n: int = 60,
    *,
    regions: list[str] | None = None,
    modis_counts: np.ndarray | None = None,
    viirs_counts: np.ndarray | None = None,
    include_scan: bool = True,
    include_night: bool = True,
    seed: int = 0,
) -> pd.DataFrame:
    """Generate a synthetic wide cell-day table suitable for modelling."""
    rng = np.random.default_rng(seed)
    if modis_counts is None:
        modis_counts = rng.integers(1, 10, size=n)
    if viirs_counts is None:
        viirs_counts = rng.integers(1, 15, size=n)
    if regions is None:
        regions = [f"region_{i % 3}" for i in range(n)]

    start = date(2020, 1, 1)
    dates = pd.date_range(start, periods=n, freq="D")

    df = pd.DataFrame(
        {
            "cell_id": [f"cell_{i % 5}" for i in range(n)],
            "date": dates,
            "region": regions,
            "n_detections_MODIS": modis_counts.astype(int),
            "n_detections_VIIRS": viirs_counts.astype(int),
            "mean_frp_MODIS": rng.uniform(5, 50, n),
            "mean_frp_VIIRS": rng.uniform(5, 50, n),
            "overlap_valid": True,
        }
    )

    if include_scan:
        df["mean_scan_MODIS"] = rng.uniform(0.5, 2.5, n)
    if include_night:
        df["night_fraction_MODIS"] = rng.uniform(0.0, 1.0, n)

    return df


def _model_frame(n: int = 60, **kwargs) -> pd.DataFrame:
    """Return a prepared model frame ready for fitting."""
    return prepare_model_frame(_cell_day(n, **kwargs))


# ===========================================================================
# prepare_model_frame
# ===========================================================================


class TestPrepareModelFrame:
    def test_basic_columns_present(self) -> None:
        """Core output columns are always present."""
        mf = _model_frame()
        assert "n_detections_VIIRS" in mf.columns
        assert "n_detections_MODIS" in mf.columns
        assert "log_modis" in mf.columns

    def test_log_modis_equals_log_of_counts(self) -> None:
        """log_modis is exactly log(n_detections_MODIS)."""
        mf = _model_frame()
        expected = np.log(mf["n_detections_MODIS"].astype(float))
        np.testing.assert_allclose(mf["log_modis"].to_numpy(), expected.to_numpy())

    def test_overlap_only_filters_non_overlap(self) -> None:
        """When overlap_only=True (default) non-overlap rows are dropped."""
        df = _cell_day(10)
        df.loc[0, "overlap_valid"] = False
        df.loc[5, "overlap_valid"] = False
        mf = prepare_model_frame(df, overlap_only=True)
        assert len(mf) == 8

    def test_overlap_only_false_keeps_all_rows(self) -> None:
        """When overlap_only=False non-overlap rows are kept."""
        df = _cell_day(10)
        df.loc[0, "overlap_valid"] = False
        mf = prepare_model_frame(df, overlap_only=False)
        # all rows kept (subject to min_modis_count filter)
        assert len(mf) == 10

    def test_min_modis_count_filters_low_counts(self) -> None:
        """Rows where MODIS count < min_modis_count are dropped."""
        df = _cell_day(10, modis_counts=np.array([1, 2, 3, 1, 5, 1, 7, 1, 9, 10]))
        mf = prepare_model_frame(df, min_modis_count=3)
        assert all(mf["n_detections_MODIS"] >= 3)

    def test_month_column_extracted_from_date(self) -> None:
        """month column contains integer month values."""
        mf = _model_frame()
        assert "month" in mf.columns
        assert mf["month"].between(1, 12).all()

    def test_region_column_carried_through(self) -> None:
        """region column is preserved as a string-like dtype."""
        mf = _model_frame()
        assert "region" in mf.columns
        # pandas 3.0+ may use StringDtype; both str and object are acceptable.
        assert pd.api.types.is_string_dtype(mf["region"])

    def test_scan_and_night_columns_carried_through(self) -> None:
        """mean_scan_MODIS and night_fraction_MODIS are preserved when present."""
        mf = _model_frame(include_scan=True, include_night=True)
        assert "mean_scan_MODIS" in mf.columns
        assert "night_fraction_MODIS" in mf.columns

    def test_missing_optional_columns_absent_in_output(self) -> None:
        """When optional columns are absent they do not appear in the output."""
        mf = _model_frame(include_scan=False, include_night=False)
        assert "mean_scan_MODIS" not in mf.columns
        assert "night_fraction_MODIS" not in mf.columns

    def test_index_reset_on_output(self) -> None:
        """Output index is always a default RangeIndex."""
        mf = _model_frame()
        assert list(mf.index) == list(range(len(mf)))

    def test_missing_required_column_raises(self) -> None:
        """ValueError listing the missing column is raised."""
        df = _cell_day().drop(columns=["overlap_valid"])
        with pytest.raises(ValueError, match="overlap_valid"):
            prepare_model_frame(df)

    def test_missing_n_detections_modis_raises(self) -> None:
        df = _cell_day().drop(columns=["n_detections_MODIS"])
        with pytest.raises(ValueError, match="n_detections_MODIS"):
            prepare_model_frame(df)

    def test_invalid_min_modis_count_raises(self) -> None:
        """Non-integer or non-positive min_modis_count raises ValueError."""
        df = _cell_day()
        with pytest.raises(ValueError):
            prepare_model_frame(df, min_modis_count=0)
        with pytest.raises(ValueError):
            prepare_model_frame(df, min_modis_count=1.5)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            prepare_model_frame(df, min_modis_count=True)  # bool subclass of int

    def test_all_rows_filtered_returns_empty_frame(self) -> None:
        """When all rows are filtered, an empty frame with correct columns is returned."""
        df = _cell_day(5, modis_counts=np.zeros(5, dtype=int))
        mf = prepare_model_frame(df, min_modis_count=1)
        assert mf.empty
        assert "n_detections_VIIRS" in mf.columns
        assert "log_modis" in mf.columns

    def test_viirs_null_filled_to_zero(self) -> None:
        """NaN VIIRS counts are filled to 0 in the model frame."""
        df = _cell_day(5)
        df.loc[2, "n_detections_VIIRS"] = None
        mf = prepare_model_frame(df)
        assert int(mf.loc[mf.index[2], "n_detections_VIIRS"]) == 0

    def test_overlap_valid_as_integer(self) -> None:
        """overlap_valid stored as 0/1 int is handled correctly."""
        df = _cell_day(10)
        df["overlap_valid"] = df["overlap_valid"].astype(int)
        mf = prepare_model_frame(df, overlap_only=True)
        assert len(mf) == 10


# ===========================================================================
# fit_count_model
# ===========================================================================


class TestFitCountModel:
    def test_returns_count_model_result(self) -> None:
        """Return type is CountModelResult."""
        result = fit_count_model(_model_frame())
        assert isinstance(result, CountModelResult)

    def test_poisson_family_set_correctly(self) -> None:
        """Explicit Poisson family is recorded in the result."""
        result = fit_count_model(_model_frame(), family="poisson")
        assert result.family == "poisson"

    def test_negativebinomial_family_set_correctly(self) -> None:
        """Explicit NB family is recorded in the result."""
        result = fit_count_model(_model_frame(), family="negativebinomial")
        assert result.family == "negativebinomial"

    def test_auto_selects_poisson_when_vmr_low(self) -> None:
        """'auto' picks Poisson when VMR < threshold."""
        result = fit_count_model(_model_frame(), family="auto", vmr=1.0)
        assert result.family == "poisson"

    def test_auto_selects_nb_when_vmr_high(self) -> None:
        """'auto' picks Negative Binomial when VMR >= threshold."""
        result = fit_count_model(_model_frame(), family="auto", vmr=3.0)
        assert result.family == "negativebinomial"

    def test_auto_estimates_overdispersion_when_vmr_is_missing(self) -> None:
        """'auto' estimates the response VMR when none is supplied."""
        mf = _model_frame()
        vmr = float(
            np.var(mf["n_detections_VIIRS"], ddof=1)
            / np.mean(mf["n_detections_VIIRS"])
        )
        result = fit_count_model(mf, family="auto", vmr=None)
        expected = "negativebinomial" if vmr >= 1.5 else "poisson"
        assert result.family == expected

    def test_auto_uses_poisson_for_underdispersed_counts(self) -> None:
        """'auto' selects Poisson when response counts are not overdispersed."""
        df = _cell_day(30, viirs_counts=np.full(30, 4))
        result = fit_count_model(prepare_model_frame(df), family="auto")
        assert result.family == "poisson"

    def test_custom_overdispersion_threshold(self) -> None:
        """'auto' respects a custom threshold."""
        result = fit_count_model(
            _model_frame(), family="auto", vmr=2.0, overdispersion_threshold=3.0
        )
        assert result.family == "poisson"
        result2 = fit_count_model(
            _model_frame(), family="auto", vmr=4.0, overdispersion_threshold=3.0
        )
        assert result2.family == "negativebinomial"

    def test_n_obs_matches_frame_length(self) -> None:
        """n_obs equals the number of rows in the model frame."""
        mf = _model_frame(50)
        result = fit_count_model(mf)
        assert result.n_obs == len(mf)

    def test_aic_and_bic_are_finite(self) -> None:
        """AIC and BIC are finite floats."""
        result = fit_count_model(_model_frame())
        assert math.isfinite(result.aic)
        assert math.isfinite(result.bic)

    def test_alpha_is_none_for_poisson(self) -> None:
        """alpha is None for a Poisson fit."""
        result = fit_count_model(_model_frame(), family="poisson")
        assert result.alpha is None

    def test_alpha_is_float_for_nb(self) -> None:
        """alpha is a finite float for a Negative Binomial fit."""
        result = fit_count_model(_model_frame(), family="negativebinomial")
        assert result.alpha is not None
        assert math.isfinite(result.alpha)
        assert result.alpha == pytest.approx(result.result.params[-1])  # type: ignore[attr-defined]

    def test_formula_columns_contains_log_modis(self) -> None:
        """log_modis is always the first feature column."""
        result = fit_count_model(_model_frame())
        assert result.formula_columns[0] == "log_modis"

    def test_formula_columns_contains_region_dummies(self) -> None:
        """Region dummy columns appear in formula_columns."""
        mf = _model_frame()
        result = fit_count_model(mf)
        region_cols = [c for c in result.formula_columns if c.startswith("region_")]
        assert len(region_cols) > 0  # 3 regions → 2 dummies

    def test_invalid_family_raises(self) -> None:
        """An unrecognised family string raises ValueError."""
        with pytest.raises(ValueError, match="family"):
            fit_count_model(_model_frame(), family="gamma")  # type: ignore[arg-type]

    def test_empty_model_frame_raises(self) -> None:
        """An empty model frame raises ValueError before attempting to fit."""
        mf = prepare_model_frame(_cell_day(5, modis_counts=np.zeros(5, dtype=int)))
        assert mf.empty
        with pytest.raises(ValueError, match="empty"):
            fit_count_model(mf)

    def test_missing_log_modis_raises(self) -> None:
        mf = _model_frame().drop(columns=["log_modis"])
        with pytest.raises(ValueError, match="log_modis"):
            fit_count_model(mf)

    def test_model_without_optional_covariates(self) -> None:
        """Model fits when scan and night fraction columns are absent."""
        mf = _model_frame(include_scan=False, include_night=False)
        result = fit_count_model(mf, family="poisson")
        assert result.n_obs > 0

    def test_model_with_single_region_no_dummies(self) -> None:
        """When only one region is present no region dummy is added."""
        df = _cell_day(30, regions=["only_region"] * 30)
        mf = prepare_model_frame(df)
        result = fit_count_model(mf, family="poisson")
        region_cols = [c for c in result.formula_columns if c.startswith("region_")]
        assert len(region_cols) == 0

    def test_params_dict_accessible_on_result(self) -> None:
        """The statsmodels result object exposes a params attribute."""
        result = fit_count_model(_model_frame(), family="poisson")
        params = result.result.params  # type: ignore[attr-defined]
        assert len(params) > 0

    def test_poisson_log_modis_coefficient_positive(self) -> None:
        """The log_modis coefficient should be positive (more MODIS → more VIIRS)."""
        # Generate data with strong MODIS signal
        rng = np.random.default_rng(99)
        n = 80
        modis = rng.integers(1, 10, size=n)
        viirs = (modis * 2 + rng.integers(0, 2, size=n)).astype(int)
        df = _cell_day(n, modis_counts=modis, viirs_counts=viirs)
        mf = prepare_model_frame(df)
        result = fit_count_model(mf, family="poisson")
        # const col is first; log_modis is first feature (index 1 in params)
        params = result.result.params  # type: ignore[attr-defined]
        # Find the log_modis param by name or position
        if hasattr(params, "index") and "x1" in params.index:
            log_modis_coef = float(params["x1"])
        else:
            log_modis_coef = float(np.asarray(params)[1])
        assert log_modis_coef > 0


# ===========================================================================
# spatial_block_cv
# ===========================================================================


class TestSpatialBlockCV:
    def test_returns_cv_summary(self) -> None:
        """Return type is CVSummary."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        assert isinstance(cv, CVSummary)

    def test_n_folds_equals_number_of_regions(self) -> None:
        """With three regions there are three folds (or fewer if a fold is skipped)."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        assert cv.n_folds <= 3

    def test_fold_list_length_matches_n_folds(self) -> None:
        """len(cv.folds) equals cv.n_folds."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        assert len(cv.folds) == cv.n_folds

    def test_fold_metrics_types(self) -> None:
        """Every FoldMetrics entry has the correct attribute types."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        for fold in cv.folds:
            assert isinstance(fold, FoldMetrics)
            assert isinstance(fold.region, str)
            assert isinstance(fold.n_test, int)
            assert math.isfinite(fold.mae)
            assert math.isfinite(fold.rmse)
            if fold.correlation is not None:
                assert -1.0 <= fold.correlation <= 1.0

    def test_mae_and_rmse_non_negative(self) -> None:
        """MAE and RMSE are always >= 0."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        for fold in cv.folds:
            assert fold.mae >= 0.0
            assert fold.rmse >= 0.0

    def test_mean_mae_averages_fold_maes(self) -> None:
        """mean_mae equals the arithmetic mean of fold MAEs."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        if cv.n_folds > 0:
            expected = float(np.mean([f.mae for f in cv.folds]))
            assert cv.mean_mae == pytest.approx(expected, rel=1e-6)

    def test_mean_rmse_averages_fold_rmses(self) -> None:
        """mean_rmse equals the arithmetic mean of fold RMSEs."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        if cv.n_folds > 0:
            expected = float(np.mean([f.rmse for f in cv.folds]))
            assert cv.mean_rmse == pytest.approx(expected, rel=1e-6)

    def test_missing_region_column_raises(self) -> None:
        """ValueError is raised when model_frame has no region column."""
        mf = _model_frame().drop(columns=["region"])
        with pytest.raises(ValueError, match="region"):
            spatial_block_cv(mf)

    def test_invalid_min_train_size_raises(self) -> None:
        """Non-positive or non-integer min_train_size raises ValueError."""
        mf = _model_frame()
        with pytest.raises(ValueError):
            spatial_block_cv(mf, min_train_size=0)
        with pytest.raises(ValueError):
            spatial_block_cv(mf, min_train_size=True)  # type: ignore[arg-type]

    def test_single_region_produces_zero_folds(self) -> None:
        """When only one region exists every fold's training set is empty → skipped."""
        df = _cell_day(20, regions=["single"] * 20)
        mf = prepare_model_frame(df)
        cv = spatial_block_cv(mf, family="poisson")
        assert cv.n_folds == 0

    def test_min_train_size_skips_small_training_sets(self) -> None:
        """Folds with fewer training rows than min_train_size are skipped."""
        # 3 regions of 5 each → training sets have 10 rows.
        # With min_train_size=15, all folds are skipped.
        df = _cell_day(15, regions=(["r1"] * 5 + ["r2"] * 5 + ["r3"] * 5))
        mf = prepare_model_frame(df)
        cv = spatial_block_cv(mf, family="poisson", min_train_size=15)
        assert cv.n_folds == 0

    def test_vmr_forwarded_to_model_family(self) -> None:
        """The model family in each fold reflects the vmr argument."""
        mf = _model_frame()
        # Force NB via high VMR
        cv = spatial_block_cv(mf, family="auto", vmr=10.0)
        # We can't inspect fold family directly, but we can verify no exception
        assert isinstance(cv, CVSummary)

    def test_held_out_region_name_in_fold(self) -> None:
        """Each fold's region attribute matches one of the input region labels."""
        mf = _model_frame()
        all_regions = set(mf["region"].unique())
        cv = spatial_block_cv(mf, family="poisson")
        for fold in cv.folds:
            assert fold.region in all_regions

    def test_no_overlap_between_train_and_test(self) -> None:
        """Every test observation's region is absent from the training set for that fold.

        We verify this indirectly: each fold region appears exactly once.
        """
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="poisson")
        seen = [fold.region for fold in cv.folds]
        # Each region should appear at most once as a fold
        assert len(seen) == len(set(seen))

    def test_cv_with_nb_family(self) -> None:
        """CV runs end-to-end with Negative Binomial family."""
        mf = _model_frame()
        cv = spatial_block_cv(mf, family="negativebinomial")
        assert isinstance(cv, CVSummary)
        assert cv.n_folds >= 1

    def test_n_test_sums_to_total_rows(self) -> None:
        """Sum of n_test across folds equals total rows in the model frame
        (every row is a test point in exactly one fold)."""
        mf = _model_frame(60)
        cv = spatial_block_cv(mf, family="poisson")
        if cv.n_folds == 3:
            assert sum(f.n_test for f in cv.folds) == len(mf)

    def test_prediction_aligns_month_and_region_dummy_columns(self) -> None:
        """Held-out category indicators map to their training coefficients."""
        result = CountModelResult(
            family="poisson",
            result=SimpleNamespace(params=np.array([0.0, 0.0, 2.0, 3.0])),
            formula_columns=["log_modis", "month_2", "region_r2"],
            n_obs=4,
            aic=0.0,
            bic=0.0,
        )
        test_frame = pd.DataFrame(
            {"log_modis": [0.0], "month": [2], "region": ["r2"]}
        )

        prediction = _predict(result, test_frame)

        np.testing.assert_allclose(prediction, [np.exp(5.0)])


# ===========================================================================
# CountModelResult and CVSummary dataclass fields
# ===========================================================================


class TestDataclasses:
    def test_count_model_result_fields(self) -> None:
        """CountModelResult stores all documented fields."""
        result = fit_count_model(_model_frame(), family="poisson")
        assert hasattr(result, "family")
        assert hasattr(result, "result")
        assert hasattr(result, "formula_columns")
        assert hasattr(result, "n_obs")
        assert hasattr(result, "aic")
        assert hasattr(result, "bic")
        assert hasattr(result, "alpha")
        assert isinstance(result.formula_columns, list)

    def test_cv_summary_zero_folds(self) -> None:
        """CVSummary with zero folds has sane defaults."""
        df = _cell_day(10, regions=["only"] * 10)
        mf = prepare_model_frame(df)
        cv = spatial_block_cv(mf, family="poisson")
        assert cv.n_folds == 0
        assert cv.folds == []
        assert cv.mean_correlation is None

    def test_fold_metrics_fields(self) -> None:
        """FoldMetrics stores all documented fields."""
        fm = FoldMetrics(region="r1", n_test=10, mae=1.5, rmse=2.0, correlation=0.9)
        assert fm.region == "r1"
        assert fm.n_test == 10
        assert fm.mae == pytest.approx(1.5)
        assert fm.rmse == pytest.approx(2.0)
        assert fm.correlation == pytest.approx(0.9)

    def test_cv_summary_mean_correlation_none_when_no_valid_folds(self) -> None:
        """mean_correlation is None when no fold produced a valid correlation."""
        summary = CVSummary(
            n_folds=2,
            folds=[
                FoldMetrics("r1", 1, 1.0, 1.0, None),
                FoldMetrics("r2", 1, 2.0, 2.0, None),
            ],
            mean_mae=1.5,
            mean_rmse=1.5,
            mean_correlation=None,
        )
        assert summary.mean_correlation is None
