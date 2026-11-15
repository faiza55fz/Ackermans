"""Tests for harmonized Parquet and backend summary exports."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.export.exporter import ExportResult, export_harmonized_dataset


@pytest.fixture
def observed() -> pd.DataFrame:
    """Provide observed cell-day values."""
    return pd.DataFrame(
        {
            "cell_id": ["c1", "c2"],
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "n_detections_VIIRS": [2, 4],
            "mean_frp_VIIRS": [12.5, 25.0],
            "is_estimated": [False, False],
        }
    )


@pytest.fixture
def estimated() -> pd.DataFrame:
    """Provide model-generated cell-day values with prediction bounds."""
    return pd.DataFrame(
        {
            "cell_id": ["c3"],
            "date": pd.to_datetime(["2020-01-03"]),
            "n_detections_VIIRS": [3],
            "mean_frp_VIIRS": [18.0],
            "n_detections_VIIRS_lower": [1.0],
            "n_detections_VIIRS_upper": [5.0],
            "mean_frp_VIIRS_lower": [10.0],
            "mean_frp_VIIRS_upper": [26.0],
            "is_estimated": [True],
        }
    )


def test_export_writes_parquet_with_explicit_source_column(
    tmp_path: Path,
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
) -> None:
    """Exported rows retain values and are explicitly sourced."""
    result = export_harmonized_dataset(observed, estimated, tmp_path)

    assert isinstance(result, ExportResult)
    assert result.n_rows == 3
    assert result.parquet_path == tmp_path / "harmonized_hotspots.parquet"
    assert result.summary_path == tmp_path / "summary.json"
    exported = pd.read_parquet(result.parquet_path)
    assert exported["source"].tolist() == ["observed", "observed", "estimated"]
    assert exported.loc[exported["source"] == "observed", "is_estimated"].eq(False).all()
    assert exported.loc[exported["source"] == "estimated", "is_estimated"].eq(True).all()
    assert exported.loc[2, "n_detections_VIIRS_lower"] == pytest.approx(1.0)


def test_export_does_not_mutate_input_frames(
    tmp_path: Path,
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
) -> None:
    """Source frames remain unchanged after exporting."""
    observed_before = observed.copy()
    estimated_before = estimated.copy()

    export_harmonized_dataset(observed, estimated, tmp_path)

    pd.testing.assert_frame_equal(observed, observed_before)
    pd.testing.assert_frame_equal(estimated, estimated_before)
    assert "source" not in observed.columns
    assert "source" not in estimated.columns


def test_export_creates_output_directory(
    tmp_path: Path,
    observed: pd.DataFrame,
) -> None:
    """The destination directory is created when it does not exist."""
    output_dir = tmp_path / "new" / "processed"

    result = export_harmonized_dataset(observed, pd.DataFrame(), output_dir)

    assert result.parquet_path.exists()
    assert result.summary_path.exists()
    assert result.n_rows == len(observed)


def test_summary_contains_metadata_source_counts_and_aggregates(
    tmp_path: Path,
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
) -> None:
    """JSON summary includes backend metadata and provided validation metrics."""
    metrics = {"mae": 0.75, "rmse": 1.2, "bias": -0.1, "r2": 0.82}
    result = export_harmonized_dataset(
        observed,
        estimated,
        tmp_path,
        metadata={"project": "MODIS_VIIRS_HARMONIZATION", "grid_size": 0.25},
        metrics=metrics,
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["metadata"]["project"] == "MODIS_VIIRS_HARMONIZATION"
    assert summary["metadata"]["grid_size"] == 0.25
    assert summary["metadata"]["dataset"] == "harmonized_hotspots.parquet"
    assert summary["metadata"]["n_rows"] == 3
    assert summary["metadata"]["created_at_utc"].endswith("+00:00")
    assert summary["aggregated_metrics"]["rows_by_source"] == {
        "observed": 2,
        "estimated": 1,
    }
    assert summary["aggregated_metrics"]["numeric_columns"]["n_detections_VIIRS"] == {
        "count": 3,
        "mean": 3.0,
        "min": 2.0,
        "max": 4.0,
    }
    assert summary["aggregated_metrics"]["provided"] == metrics
    assert summary["aggregated_metrics"]["numeric_columns_by_source"][
        "estimated"
    ]["mean_frp_VIIRS"]["mean"] == pytest.approx(18.0)


def test_source_column_conflicts_are_rejected(
    tmp_path: Path,
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
) -> None:
    """An input with mislabeled source provenance cannot be exported."""
    with pytest.raises(ValueError, match="source values"):
        export_harmonized_dataset(
            observed.assign(source="estimated"), estimated, tmp_path
        )
    with pytest.raises(ValueError, match="source values"):
        export_harmonized_dataset(
            observed, estimated.assign(source="observed"), tmp_path
        )


def test_estimation_flag_conflicts_are_rejected(
    tmp_path: Path,
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
) -> None:
    """An is_estimated value that contradicts source role is rejected."""
    with pytest.raises(ValueError, match="is_estimated=False"):
        export_harmonized_dataset(
            observed.assign(is_estimated=True), estimated, tmp_path
        )
    with pytest.raises(ValueError, match="is_estimated=True"):
        export_harmonized_dataset(
            observed, estimated.assign(is_estimated=False), tmp_path
        )


def test_estimation_flag_requires_boolean_values(
    tmp_path: Path,
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
) -> None:
    """Integer-like estimation flags are rejected rather than coerced."""
    with pytest.raises(ValueError, match="non-null booleans"):
        export_harmonized_dataset(
            observed.assign(is_estimated=[0, 0]), estimated, tmp_path
        )
    with pytest.raises(ValueError, match="non-null booleans"):
        export_harmonized_dataset(
            observed.assign(is_estimated=[False, None]), estimated, tmp_path
        )


def test_empty_estimated_frame_exports_observed_only(
    tmp_path: Path,
    observed: pd.DataFrame,
) -> None:
    """Observed-only outputs still use explicit source provenance."""
    result = export_harmonized_dataset(observed, pd.DataFrame(), tmp_path)
    exported = pd.read_parquet(result.parquet_path)
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    assert len(exported) == 2
    assert exported["source"].eq("observed").all()
    assert summary["aggregated_metrics"]["rows_by_source"]["estimated"] == 0


def test_summary_handles_empty_numeric_source_aggregates(
    tmp_path: Path,
    observed: pd.DataFrame,
) -> None:
    """An empty source side produces valid JSON aggregates without NaNs."""
    result = export_harmonized_dataset(observed, pd.DataFrame(), tmp_path)
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    empty_numeric = summary["aggregated_metrics"]["numeric_columns_by_source"][
        "estimated"
    ]
    assert empty_numeric["n_detections_VIIRS"] == {
        "count": 0,
        "mean": 0.0,
        "min": 0.0,
        "max": 0.0,
    }


def test_non_finite_values_are_excluded_from_numeric_summary(
    tmp_path: Path,
) -> None:
    """Numeric summary statistics use finite values only."""
    observed = pd.DataFrame({"n_detections": [1.0, np.inf, np.nan]})
    result = export_harmonized_dataset(observed, pd.DataFrame(), tmp_path)
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    assert summary["aggregated_metrics"]["numeric_columns"]["n_detections"] == {
        "count": 1,
        "mean": 1.0,
        "min": 1.0,
        "max": 1.0,
    }


def test_metadata_must_be_json_serializable(
    tmp_path: Path,
    observed: pd.DataFrame,
) -> None:
    """Unsupported metadata values fail before output is written."""
    with pytest.raises(ValueError, match="not JSON serializable"):
        export_harmonized_dataset(
            observed,
            pd.DataFrame(),
            tmp_path,
            metadata={"not_serializable": object()},
        )

    assert not (tmp_path / "harmonized_hotspots.parquet").exists()
    assert not (tmp_path / "summary.json").exists()
