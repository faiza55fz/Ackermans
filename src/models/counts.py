"""Count-regression models for VIIRS fire detection from MODIS observations.

This module fits Poisson or Negative Binomial regression models that
predict VIIRS detection counts using MODIS observations and additional
covariates (month, region, mean scan angle, night fraction).

The choice between Poisson and Negative Binomial is data-driven: when
the dispersion diagnostic from :func:`src.grid.overlap_analysis.check_overdispersion`
indicates overdispersion (VMR > 1) a Negative Binomial model is used;
otherwise a Poisson model is used.  The caller may also force either
family explicitly.

Spatial-block cross-validation holds out whole ``region`` blocks in
turn so that performance metrics are not inflated by spatial
autocorrelation between train and test sets.

Public API
----------
* :func:`prepare_model_frame`     – build design matrix from cell-day table.
* :func:`fit_count_model`         – fit Poisson or NB on a prepared frame.
* :func:`spatial_block_cv`        – leave-one-region-out CV loop.
* :class:`CountModelResult`       – lightweight result container.
* :class:`CVSummary`              – per-fold and aggregate CV metrics.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import (
    NegativeBinomial,
    Poisson,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Columns required in the cell-day table before feature engineering.
_REQUIRED_CELL_DAY_COLS: tuple[str, ...] = (
    "n_detections_MODIS",
    "n_detections_VIIRS",
    "overlap_valid",
)

#: Optional covariates consumed when present.
_OPTIONAL_COLS: tuple[str, ...] = (
    "date",
    "region",
    "mean_scan_MODIS",
    "night_fraction_MODIS",
)

#: Model family literals accepted by :func:`fit_count_model`.
ModelFamily = Literal["poisson", "negativebinomial", "auto"]

# ---------------------------------------------------------------------------
# Public data-classes
# ---------------------------------------------------------------------------


@dataclass
class CountModelResult:
    """Container for a fitted count-regression model and its metadata.

    Attributes
    ----------
    family:
        ``"poisson"`` or ``"negativebinomial"`` as actually fitted.
    result:
        The statsmodels ``Results`` object returned by ``.fit()``.
    formula_columns:
        Ordered list of column names in the design matrix (excluding the
        intercept if ``add_constant`` was used by statsmodels).
    n_obs:
        Number of observations used to fit the model.
    aic:
        Akaike information criterion of the fitted model.
    bic:
        Bayesian information criterion of the fitted model.
    alpha:
        Estimated overdispersion parameter *α* for Negative Binomial
        models; ``None`` for Poisson.
    """

    family: str
    result: object
    formula_columns: list[str]
    n_obs: int
    aic: float
    bic: float
    alpha: float | None = None


@dataclass
class FoldMetrics:
    """Metrics for one spatial fold (held-out region).

    Attributes
    ----------
    region:
        The region label that was held out.
    n_test:
        Number of test-set observations.
    mae:
        Mean absolute error of predicted vs. actual VIIRS counts.
    rmse:
        Root-mean-squared error of predicted vs. actual VIIRS counts.
    correlation:
        Pearson correlation between predicted and actual counts.
        ``None`` when fewer than two test observations exist.
    """

    region: str
    n_test: int
    mae: float
    rmse: float
    correlation: float | None


@dataclass
class CVSummary:
    """Aggregate results from spatial-block cross-validation.

    Attributes
    ----------
    n_folds:
        Number of spatial folds executed.
    folds:
        Per-fold metrics in fold order.
    mean_mae:
        Macro-averaged MAE across folds.
    mean_rmse:
        Macro-averaged RMSE across folds.
    mean_correlation:
        Macro-averaged Pearson correlation across folds where correlation
        could be computed.  ``None`` when no fold produced a valid
        correlation.
    """

    n_folds: int
    folds: list[FoldMetrics] = field(default_factory=list)
    mean_mae: float = 0.0
    mean_rmse: float = 0.0
    mean_correlation: float | None = None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def prepare_model_frame(
    cell_day_df: pd.DataFrame,
    *,
    overlap_only: bool = True,
    min_modis_count: int = 1,
) -> pd.DataFrame:
    """Build a regression-ready design frame from a wide cell-day table.

    Rows are filtered to those suitable for modelling (optionally
    restricted to the overlap period) and feature columns are added:

    * ``log_modis`` – natural log of MODIS detection counts (offset-style
      predictor); rows with ``n_detections_MODIS < min_modis_count`` are
      dropped after the overlap filter.
    * ``month`` – integer 1–12 extracted from ``date`` when present.
    * ``region`` – region label carried through unchanged when present.
    * ``mean_scan_MODIS`` – mean scan angle (kept as-is when present).
    * ``night_fraction_MODIS`` – night fraction (kept as-is when present).

    Parameters
    ----------
    cell_day_df:
        Wide cell-day table produced by
        :func:`src.grid.grid_builder.build_cell_day_table` with an
        ``overlap_valid`` column.
    overlap_only:
        When ``True`` (the default) only rows where ``overlap_valid`` is
        truthy are included, ensuring that the response variable
        (``n_detections_VIIRS``) is always observed.
    min_modis_count:
        Rows with ``n_detections_MODIS`` strictly less than this value
        are dropped.  Must be a positive integer.  Default is ``1``.

    Returns
    -------
    pandas.DataFrame
        A new frame containing the response (``n_detections_VIIRS``) and
        predictor columns.  The index is reset.  At minimum the frame has
        columns ``n_detections_VIIRS``, ``n_detections_MODIS``, and
        ``log_modis``.

    Raises
    ------
    ValueError
        When *cell_day_df* is missing any of the required columns, or
        when *min_modis_count* is not a positive integer.
    """
    if not isinstance(min_modis_count, int) or isinstance(min_modis_count, bool):
        raise ValueError("min_modis_count must be a positive integer")
    if min_modis_count < 1:
        raise ValueError("min_modis_count must be >= 1")

    _require_columns(cell_day_df, _REQUIRED_CELL_DAY_COLS)

    df = cell_day_df.copy()

    # --- overlap filter ------------------------------------------------------
    if overlap_only:
        df = df.loc[df["overlap_valid"].astype(bool)].copy()

    # --- MODIS count filter --------------------------------------------------
    df = df.loc[df["n_detections_MODIS"].fillna(0).astype(int) >= min_modis_count].copy()

    if df.empty:
        return _empty_model_frame(df)

    # --- core columns --------------------------------------------------------
    out = pd.DataFrame(index=df.index)
    out["n_detections_VIIRS"] = df["n_detections_VIIRS"].fillna(0).astype(int)
    out["n_detections_MODIS"] = df["n_detections_MODIS"].astype(int)
    out["log_modis"] = np.log(out["n_detections_MODIS"].astype(float))

    # --- optional covariates -------------------------------------------------
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce")
        out["month"] = dates.dt.month.astype("Int64")

    if "region" in df.columns:
        out["region"] = df["region"].astype(str)

    if "mean_scan_MODIS" in df.columns:
        out["mean_scan_MODIS"] = pd.to_numeric(
            df["mean_scan_MODIS"], errors="coerce"
        ).astype(float)

    if "night_fraction_MODIS" in df.columns:
        out["night_fraction_MODIS"] = pd.to_numeric(
            df["night_fraction_MODIS"], errors="coerce"
        ).astype(float)

    return out.reset_index(drop=True)


def fit_count_model(
    model_frame: pd.DataFrame,
    *,
    family: ModelFamily = "auto",
    vmr: float | None = None,
    overdispersion_threshold: float = 1.5,
) -> CountModelResult:
    """Fit a Poisson or Negative Binomial regression on *model_frame*.

    The design matrix includes:

    * ``log_modis`` (continuous).
    * Dummy variables for each ``month`` value minus one reference level
      (when ``month`` is present).
    * Dummy variables for each ``region`` value minus one reference level
      (when ``region`` is present, using the lexicographically first
      region as the reference).
    * ``mean_scan_MODIS`` (continuous, when present and not all-NaN).
    * ``night_fraction_MODIS`` (continuous, when present and not all-NaN).

    An intercept column is always prepended (via
    :func:`statsmodels.api.add_constant`).

    Parameters
    ----------
    model_frame:
        Frame produced by :func:`prepare_model_frame`.  Must contain
        ``n_detections_VIIRS`` (response) and ``log_modis`` (predictor).
    family:
        ``"poisson"`` – always use Poisson.
        ``"negativebinomial"`` – always use Negative Binomial.
        ``"auto"`` (default) – use Negative Binomial when ``vmr`` ≥
        ``overdispersion_threshold``, otherwise Poisson.
    vmr:
        Variance-to-mean ratio of VIIRS counts from
        :func:`src.grid.overlap_analysis.check_overdispersion`.  Only
        used when *family* is ``"auto"``.  When ``None`` and *family* is
        ``"auto"``, the ratio is estimated from the response counts in
        *model_frame*.
    overdispersion_threshold:
        VMR value at or above which the ``"auto"`` selector picks
        Negative Binomial.  Default is ``1.5``.

    Returns
    -------
    CountModelResult
        Fitted model wrapped in a :class:`CountModelResult`.

    Raises
    ------
    ValueError
        When required columns are absent, the frame is empty, or
        *family* is not one of the recognised literals.
    RuntimeError
        When statsmodels convergence fails after one retry with relaxed
        tolerances.
    """
    if family not in ("poisson", "negativebinomial", "auto"):
        raise ValueError(
            f"family must be 'poisson', 'negativebinomial', or 'auto'; got {family!r}"
        )
    _require_columns(model_frame, ("n_detections_VIIRS", "log_modis"))
    if model_frame.empty:
        raise ValueError("model_frame is empty; cannot fit a model")

    # --- choose family -------------------------------------------------------
    # --- build design matrix -------------------------------------------------
    X, feature_cols = _build_design_matrix(model_frame)
    y = model_frame["n_detections_VIIRS"].to_numpy(dtype=float)

    if family == "auto" and vmr is None:
        vmr = _variance_to_mean_ratio(y)
    resolved_family = _resolve_family(family, vmr, overdispersion_threshold)

    # --- fit -----------------------------------------------------------------
    fitted = _fit_model(resolved_family, y, X)

    alpha: float | None = None
    if resolved_family == "negativebinomial":
        # The design matrix is a NumPy array, so statsmodels returns ndarray
        # parameters and direct positional indexing is unambiguous.
        alpha = float(fitted.params[-1])

    return CountModelResult(
        family=resolved_family,
        result=fitted,
        formula_columns=feature_cols,
        n_obs=int(len(y)),
        aic=float(fitted.aic),
        bic=float(fitted.bic),
        alpha=alpha,
    )


def spatial_block_cv(
    model_frame: pd.DataFrame,
    *,
    family: ModelFamily = "auto",
    vmr: float | None = None,
    overdispersion_threshold: float = 1.5,
    min_train_size: int = 10,
) -> CVSummary:
    """Leave-one-region-out cross-validation for count regression models.

    Each unique value of the ``region`` column is held out in turn.  A
    fresh model is fitted on the remaining regions, then used to predict
    counts in the held-out region.  Performance metrics (MAE, RMSE,
    Pearson correlation) are computed per fold and averaged.

    Parameters
    ----------
    model_frame:
        Frame produced by :func:`prepare_model_frame`.  Must contain a
        ``region`` column; rows with a null ``region`` are skipped.
    family:
        Model family forwarded to :func:`fit_count_model` on each fold.
    vmr:
        Variance-to-mean ratio forwarded to :func:`fit_count_model`.
    overdispersion_threshold:
        Forwarded to :func:`fit_count_model`.
    min_train_size:
        Folds whose training set has fewer than this many rows are
        skipped.  Default is ``10``.

    Returns
    -------
    CVSummary
        Per-fold metrics and macro-averages.

    Raises
    ------
    ValueError
        When *model_frame* does not contain a ``region`` column, or when
        *min_train_size* is not a positive integer.
    """
    if "region" not in model_frame.columns:
        raise ValueError(
            "model_frame must contain a 'region' column for spatial-block CV"
        )
    if not isinstance(min_train_size, int) or isinstance(min_train_size, bool):
        raise ValueError("min_train_size must be a positive integer")
    if min_train_size < 1:
        raise ValueError("min_train_size must be >= 1")

    df = model_frame.dropna(subset=["region"]).copy()
    regions = sorted(df["region"].unique())

    folds: list[FoldMetrics] = []

    for region in regions:
        test_mask = df["region"] == region
        train_df = df.loc[~test_mask].reset_index(drop=True)
        test_df = df.loc[test_mask].reset_index(drop=True)

        if len(train_df) < min_train_size or test_df.empty:
            continue

        cr = fit_count_model(
            train_df,
            family=family,
            vmr=vmr,
            overdispersion_threshold=overdispersion_threshold,
        )

        preds = _predict(cr, test_df)
        actual = test_df["n_detections_VIIRS"].to_numpy(dtype=float)

        folds.append(_fold_metrics(region, actual, preds))

    return _aggregate_cv(folds)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...] | tuple[str, str]) -> None:
    """Raise ``ValueError`` listing every column absent from *df*."""
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(
            "Model frame is missing columns: " + ", ".join(missing)
        )


def _resolve_family(
    family: ModelFamily,
    vmr: float | None,
    threshold: float,
) -> str:
    """Return the concrete family string (``"poisson"`` or ``"negativebinomial"``)."""
    if family == "poisson":
        return "poisson"
    if family == "negativebinomial":
        return "negativebinomial"
    # auto
    if vmr is not None and vmr >= threshold:
        return "negativebinomial"
    return "poisson"


def _variance_to_mean_ratio(counts: np.ndarray) -> float | None:
    """Estimate the sample variance-to-mean ratio for non-negative counts."""
    mean = float(np.mean(counts))
    if len(counts) < 2 or mean <= 0.0:
        return None
    return float(np.var(counts, ddof=1) / mean)


def _build_design_matrix(
    model_frame: pd.DataFrame,
    feature_columns: list[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Return ``(X_with_const, feature_names)`` for the model frame.

    Builds dummies for ``month`` and ``region`` with drop-first encoding,
    then prepends a constant column.  When *feature_columns* is provided,
    categorical indicators are generated against those training columns so
    held-out regions/months cannot shift predictor positions.
    """
    if feature_columns is not None:
        aligned = pd.DataFrame(index=model_frame.index)
        for column in feature_columns:
            if column == "log_modis":
                aligned[column] = model_frame["log_modis"]
            elif column.startswith("month_") and "month" in model_frame:
                month = int(column.removeprefix("month_"))
                aligned[column] = model_frame["month"].astype(float).eq(month)
            elif column.startswith("region_") and "region" in model_frame:
                region = column.removeprefix("region_")
                aligned[column] = model_frame["region"].astype(str).eq(region)
            elif column in ("mean_scan_MODIS", "night_fraction_MODIS"):
                aligned[column] = model_frame[column]
            else:
                raise ValueError(f"Unsupported design-matrix feature: {column!r}")

        X = sm.add_constant(aligned.to_numpy(dtype=float), has_constant="add")
        return X, feature_columns

    parts: list[pd.DataFrame | pd.Series] = []
    feature_cols: list[str] = []

    # log_modis (always present)
    parts.append(model_frame["log_modis"].rename("log_modis"))
    feature_cols.append("log_modis")

    # month dummies (drop first level to avoid multicollinearity)
    if "month" in model_frame.columns:
        month_valid = model_frame["month"].dropna()
        if len(month_valid) == len(model_frame) and month_valid.nunique() > 1:
            month_dummies = pd.get_dummies(
                model_frame["month"].astype(int),
                prefix="month",
                drop_first=True,
                dtype=float,
            )
            parts.append(month_dummies)
            feature_cols.extend(month_dummies.columns.tolist())

    # region dummies (drop first level)
    if "region" in model_frame.columns:
        region_valid = model_frame["region"].dropna()
        if len(region_valid) == len(model_frame) and region_valid.nunique() > 1:
            region_dummies = pd.get_dummies(
                model_frame["region"].astype(str),
                prefix="region",
                drop_first=True,
                dtype=float,
            )
            parts.append(region_dummies)
            feature_cols.extend(region_dummies.columns.tolist())

    # mean_scan_MODIS
    if "mean_scan_MODIS" in model_frame.columns:
        col = model_frame["mean_scan_MODIS"]
        if col.notna().all():
            parts.append(col.rename("mean_scan_MODIS"))
            feature_cols.append("mean_scan_MODIS")

    # night_fraction_MODIS
    if "night_fraction_MODIS" in model_frame.columns:
        col = model_frame["night_fraction_MODIS"]
        if col.notna().all():
            parts.append(col.rename("night_fraction_MODIS"))
            feature_cols.append("night_fraction_MODIS")

    X_df = pd.concat(parts, axis=1).astype(float)
    X = sm.add_constant(X_df.to_numpy(dtype=float), has_constant="add")

    return X, feature_cols


def _fit_model(
    family: str,
    y: np.ndarray,
    X: np.ndarray,
) -> object:
    """Fit the chosen GLM family, retrying with relaxed tolerances on failure."""
    model_cls = Poisson if family == "poisson" else NegativeBinomial
    model = model_cls(y, X)

    fit_kwargs = dict(disp=0, warn_convergence=False)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            result = model.fit(**fit_kwargs)
        except Exception:
            # Retry with more iterations and looser tolerance
            try:
                result = model.fit(maxiter=200, gtol=1e-4, disp=0, warn_convergence=False)
            except Exception as exc:
                raise RuntimeError(
                    f"statsmodels {family} fit failed after retry: {exc}"
                ) from exc

    return result


def _predict(cr: CountModelResult, test_df: pd.DataFrame) -> np.ndarray:
    """Predict VIIRS counts on *test_df* using a fitted :class:`CountModelResult`."""
    fitted = cr.result  # type: ignore[attr-defined]

    X_pred, _ = _build_design_matrix(test_df, cr.formula_columns)

    params = np.asarray(fitted.params)
    if cr.family == "negativebinomial":
        params = params[:-1]
    if X_pred.shape[1] != len(params):
        raise ValueError(
            "Prediction design matrix does not match the fitted coefficient count"
        )

    lin_pred = X_pred @ params
    return np.exp(lin_pred)


def _fold_metrics(region: str, actual: np.ndarray, preds: np.ndarray) -> FoldMetrics:
    """Compute MAE, RMSE, and Pearson correlation for one fold."""
    errors = preds - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    corr: float | None = None
    if len(actual) >= 2 and np.std(actual) > 0 and np.std(preds) > 0:
        corr = float(np.corrcoef(actual, preds)[0, 1])

    return FoldMetrics(region=region, n_test=len(actual), mae=mae, rmse=rmse, correlation=corr)


def _aggregate_cv(folds: list[FoldMetrics]) -> CVSummary:
    """Build a :class:`CVSummary` from a list of :class:`FoldMetrics`."""
    if not folds:
        return CVSummary(n_folds=0)

    mean_mae = float(np.mean([f.mae for f in folds]))
    mean_rmse = float(np.mean([f.rmse for f in folds]))

    corrs = [f.correlation for f in folds if f.correlation is not None]
    mean_corr: float | None = float(np.mean(corrs)) if corrs else None

    return CVSummary(
        n_folds=len(folds),
        folds=folds,
        mean_mae=mean_mae,
        mean_rmse=mean_rmse,
        mean_correlation=mean_corr,
    )


def _empty_model_frame(source: pd.DataFrame) -> pd.DataFrame:
    """Return an empty frame with the expected model columns."""
    base_cols = ["n_detections_VIIRS", "n_detections_MODIS", "log_modis"]
    extra = [c for c in _OPTIONAL_COLS if c in source.columns]
    return pd.DataFrame(columns=base_cols + extra)
