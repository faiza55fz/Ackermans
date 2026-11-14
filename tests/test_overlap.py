"""Tests for src/grid/overlap_analysis.py.

Coverage targets:
- compute_sensor_ratios: ratio values, None handling, edge cases.
- check_overdispersion: VMR arithmetic, all vs. overlap scopes.
- generate_overlap_diagnostics: JSON structure, file creation, errors.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.grid.overlap_analysis import (
    check_overdispersion,
    compute_sensor_ratios,
    generate_overlap_diagnostics,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_cell_day(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal wide cell-day frame from a list of dicts."""
    defaults = {
        "cell_id": "34.00_-118.75",
        "date": date(2020, 1, 2),
        "n_detections_MODIS": 0,
        "n_detections_VIIRS": 0,
        "mean_frp_MODIS": None,
        "mean_frp_VIIRS": None,
        "overlap_valid": False,
    }
    records = [{**defaults, **row} for row in rows]
    return pd.DataFrame(records)


def _overlap_frame() -> pd.DataFrame:
    """Four-row frame with two overlap and two non-overlap days."""
    return _make_cell_day(
        [
            # overlap day 1 – both sensors active
            {
                "date": date(2020, 1, 1),
                "n_detections_MODIS": 2,
                "n_detections_VIIRS": 4,
                "mean_frp_MODIS": 10.0,
                "mean_frp_VIIRS": 20.0,
                "overlap_valid": True,
            },
            # overlap day 2 – both sensors active
            {
                "date": date(2020, 1, 2),
                "n_detections_MODIS": 4,
                "n_detections_VIIRS": 8,
                "mean_frp_MODIS": 20.0,
                "mean_frp_VIIRS": 60.0,
                "overlap_valid": True,
            },
            # non-overlap – only MODIS
            {
                "date": date(2020, 1, 3),
                "n_detections_MODIS": 3,
                "n_detections_VIIRS": 0,
                "mean_frp_MODIS": 5.0,
                "mean_frp_VIIRS": None,
                "overlap_valid": False,
            },
            # non-overlap – only VIIRS
            {
                "date": date(2020, 1, 4),
                "n_detections_MODIS": 0,
                "n_detections_VIIRS": 5,
                "mean_frp_MODIS": None,
                "mean_frp_VIIRS": 15.0,
                "overlap_valid": False,
            },
        ]
    )


# ===========================================================================
# compute_sensor_ratios
# ===========================================================================


class TestComputeSensorRatios:
    def test_count_ratios_overlap_rows_only(self) -> None:
        """Ratios use only rows where overlap_valid is True."""
        df = _overlap_frame()
        result = compute_sensor_ratios(df)

        # overlap day 1: 4/2 = 2.0;  overlap day 2: 8/4 = 2.0
        assert result["overlap_days"] == 2
        assert result["count_ratio_mean"] == pytest.approx(2.0)
        assert result["count_ratio_median"] == pytest.approx(2.0)

    def test_frp_ratios_overlap_rows_only(self) -> None:
        """FRP ratios are computed only for overlap rows with valid FRP pairs."""
        df = _overlap_frame()
        result = compute_sensor_ratios(df)

        # overlap day 1: 20/10 = 2.0;  overlap day 2: 60/20 = 3.0  → mean 2.5
        assert result["frp_ratio_mean"] == pytest.approx(2.5)
        assert result["frp_ratio_median"] == pytest.approx(2.5)

    def test_no_overlap_rows_returns_none_values(self) -> None:
        """When no cell-day has overlap_valid, all ratio values are None."""
        df = _make_cell_day(
            [
                {"n_detections_MODIS": 3, "n_detections_VIIRS": 0, "overlap_valid": False},
                {"n_detections_MODIS": 0, "n_detections_VIIRS": 2, "overlap_valid": False},
            ]
        )
        result = compute_sensor_ratios(df)

        assert result["overlap_days"] == 0
        assert result["count_ratio_mean"] is None
        assert result["count_ratio_median"] is None
        assert result["frp_ratio_mean"] is None
        assert result["frp_ratio_median"] is None

    def test_missing_frp_columns_returns_none_frp_ratios(self) -> None:
        """When FRP columns are absent, FRP ratio keys are None."""
        df = _make_cell_day(
            [{"n_detections_MODIS": 2, "n_detections_VIIRS": 4, "overlap_valid": True}]
        ).drop(columns=["mean_frp_MODIS", "mean_frp_VIIRS"])
        result = compute_sensor_ratios(df)

        assert result["frp_ratio_mean"] is None
        assert result["frp_ratio_median"] is None

    def test_missing_one_frp_column_returns_none_frp_ratios(self) -> None:
        """Only one FRP column present → FRP ratios are None."""
        df = _make_cell_day(
            [
                {
                    "n_detections_MODIS": 2,
                    "n_detections_VIIRS": 4,
                    "mean_frp_MODIS": 10.0,
                    "overlap_valid": True,
                }
            ]
        ).drop(columns=["mean_frp_VIIRS"])
        result = compute_sensor_ratios(df)

        assert result["frp_ratio_mean"] is None

    def test_frp_rows_with_zero_modis_frp_excluded(self) -> None:
        """Zero MODIS FRP rows are excluded from the FRP ratio to avoid division by zero."""
        df = _make_cell_day(
            [
                {
                    "n_detections_MODIS": 2,
                    "n_detections_VIIRS": 4,
                    "mean_frp_MODIS": 0.0,
                    "mean_frp_VIIRS": 20.0,
                    "overlap_valid": True,
                },
                {
                    "n_detections_MODIS": 2,
                    "n_detections_VIIRS": 6,
                    "mean_frp_MODIS": 10.0,
                    "mean_frp_VIIRS": 30.0,
                    "overlap_valid": True,
                },
            ]
        )
        result = compute_sensor_ratios(df)

        # Only the second row is valid: 30/10 = 3.0
        assert result["frp_ratio_mean"] == pytest.approx(3.0)

    def test_nan_frp_pair_excluded(self) -> None:
        """Rows where either FRP value is NaN are excluded from FRP ratios."""
        df = _make_cell_day(
            [
                {
                    "n_detections_MODIS": 2,
                    "n_detections_VIIRS": 4,
                    "mean_frp_MODIS": float("nan"),
                    "mean_frp_VIIRS": 20.0,
                    "overlap_valid": True,
                },
                {
                    "n_detections_MODIS": 2,
                    "n_detections_VIIRS": 6,
                    "mean_frp_MODIS": 10.0,
                    "mean_frp_VIIRS": 20.0,
                    "overlap_valid": True,
                },
            ]
        )
        result = compute_sensor_ratios(df)

        assert result["frp_ratio_mean"] == pytest.approx(2.0)

    def test_overlap_valid_as_integer_flag(self) -> None:
        """overlap_valid can be stored as 0/1 integers (truthy cast)."""
        df = _make_cell_day(
            [
                {"n_detections_MODIS": 2, "n_detections_VIIRS": 6, "overlap_valid": 1},
                {"n_detections_MODIS": 1, "n_detections_VIIRS": 0, "overlap_valid": 0},
            ]
        )
        result = compute_sensor_ratios(df)

        assert result["overlap_days"] == 1
        assert result["count_ratio_mean"] == pytest.approx(3.0)

    def test_all_valid_frp_rows_missing_returns_none(self) -> None:
        """If all FRP pairs are (NaN, something), frp_ratio_mean is None."""
        df = _make_cell_day(
            [
                {
                    "n_detections_MODIS": 2,
                    "n_detections_VIIRS": 4,
                    "mean_frp_MODIS": None,
                    "mean_frp_VIIRS": 20.0,
                    "overlap_valid": True,
                }
            ]
        )
        result = compute_sensor_ratios(df)

        assert result["frp_ratio_mean"] is None
        assert result["frp_ratio_median"] is None

    def test_missing_required_column_raises(self) -> None:
        """ValueError is raised listing the first missing required column."""
        df = _overlap_frame().drop(columns=["overlap_valid"])
        with pytest.raises(ValueError, match="overlap_valid"):
            compute_sensor_ratios(df)

    def test_missing_n_detections_modis_raises(self) -> None:
        df = _overlap_frame().drop(columns=["n_detections_MODIS"])
        with pytest.raises(ValueError, match="n_detections_MODIS"):
            compute_sensor_ratios(df)

    def test_missing_n_detections_viirs_raises(self) -> None:
        df = _overlap_frame().drop(columns=["n_detections_VIIRS"])
        with pytest.raises(ValueError, match="n_detections_VIIRS"):
            compute_sensor_ratios(df)

    def test_single_overlap_row(self) -> None:
        """With one overlap row, mean and median are the same value."""
        df = _make_cell_day(
            [
                {
                    "n_detections_MODIS": 3,
                    "n_detections_VIIRS": 9,
                    "mean_frp_MODIS": 5.0,
                    "mean_frp_VIIRS": 15.0,
                    "overlap_valid": True,
                }
            ]
        )
        result = compute_sensor_ratios(df)

        assert result["overlap_days"] == 1
        assert result["count_ratio_mean"] == pytest.approx(3.0)
        assert result["count_ratio_median"] == pytest.approx(3.0)
        assert result["frp_ratio_mean"] == pytest.approx(3.0)
        assert result["frp_ratio_median"] == pytest.approx(3.0)

    def test_returned_dict_has_expected_keys(self) -> None:
        """The returned dict always contains exactly the documented keys."""
        result = compute_sensor_ratios(_overlap_frame())
        expected_keys = {
            "overlap_days",
            "count_ratio_mean",
            "count_ratio_median",
            "frp_ratio_mean",
            "frp_ratio_median",
        }
        assert set(result.keys()) == expected_keys


# ===========================================================================
# check_overdispersion
# ===========================================================================


class TestCheckOverdispersion:
    def test_vmr_gt_one_flagged_as_overdispersed(self) -> None:
        """When variance > mean, overdispersed is True."""
        # counts: [1, 1, 1, 10] → mean≈3.25, var≈20.25, VMR≈6.23
        df = _make_cell_day(
            [
                {"n_detections_MODIS": 1, "n_detections_VIIRS": 1, "overlap_valid": False},
                {"n_detections_MODIS": 1, "n_detections_VIIRS": 1, "overlap_valid": False},
                {"n_detections_MODIS": 1, "n_detections_VIIRS": 1, "overlap_valid": False},
                {"n_detections_MODIS": 10, "n_detections_VIIRS": 10, "overlap_valid": False},
            ]
        )
        result = check_overdispersion(df)

        assert result["all"]["MODIS"]["overdispersed"] is True
        assert result["all"]["VIIRS"]["overdispersed"] is True
        assert result["all"]["MODIS"]["vmr"] > 1.0

    def test_vmr_equal_one_poisson_like(self) -> None:
        """When every count equals the mean, variance is 0 and VMR < 1 (underdispersed)."""
        # Constant series: variance = 0, VMR = 0 → NOT overdispersed
        df = _make_cell_day(
            [
                {"n_detections_MODIS": 5, "n_detections_VIIRS": 5, "overlap_valid": False},
                {"n_detections_MODIS": 5, "n_detections_VIIRS": 5, "overlap_valid": False},
                {"n_detections_MODIS": 5, "n_detections_VIIRS": 5, "overlap_valid": False},
            ]
        )
        result = check_overdispersion(df)

        assert result["all"]["MODIS"]["vmr"] == pytest.approx(0.0)
        assert result["all"]["MODIS"]["overdispersed"] is False

    def test_overlap_scope_uses_only_overlap_rows(self) -> None:
        """The 'overlap' sub-dict is computed from overlap_valid==True rows only."""
        df = _make_cell_day(
            [
                # overlap rows: uniform count → VMR should be 0
                {"n_detections_MODIS": 3, "n_detections_VIIRS": 3, "overlap_valid": True},
                {"n_detections_MODIS": 3, "n_detections_VIIRS": 3, "overlap_valid": True},
                # non-overlap row with a very different count (should not affect overlap stats)
                {"n_detections_MODIS": 100, "n_detections_VIIRS": 100, "overlap_valid": False},
            ]
        )
        result = check_overdispersion(df)

        # 'all' scope includes the outlier → high VMR
        assert result["all"]["MODIS"]["vmr"] is not None
        assert result["all"]["MODIS"]["vmr"] > 0  # non-trivial due to the 100 outlier
        # 'overlap' scope: constant 3, VMR == 0
        assert result["overlap"]["MODIS"]["vmr"] == pytest.approx(0.0)

    def test_vmr_arithmetic_correctness(self) -> None:
        """VMR = variance / mean using sample variance (ddof=1)."""
        counts = [2, 4, 6]  # mean=4, var=4 (ddof=1), VMR=1.0
        df = _make_cell_day(
            [
                {"n_detections_MODIS": c, "n_detections_VIIRS": c, "overlap_valid": False}
                for c in counts
            ]
        )
        result = check_overdispersion(df)

        modis = result["all"]["MODIS"]
        assert modis["n"] == 3
        assert modis["mean"] == pytest.approx(4.0)
        assert modis["variance"] == pytest.approx(4.0)
        assert modis["vmr"] == pytest.approx(1.0)
        # VMR == 1 → NOT overdispersed
        assert modis["overdispersed"] is False

    def test_single_row_variance_and_vmr_are_none(self) -> None:
        """With fewer than two rows, variance and VMR cannot be computed."""
        df = _make_cell_day(
            [{"n_detections_MODIS": 5, "n_detections_VIIRS": 3, "overlap_valid": False}]
        )
        result = check_overdispersion(df)

        assert result["all"]["MODIS"]["n"] == 1
        assert result["all"]["MODIS"]["variance"] is None
        assert result["all"]["MODIS"]["vmr"] is None
        assert result["all"]["MODIS"]["overdispersed"] is None

    def test_zero_overlap_rows_gives_none_vmr(self) -> None:
        """When no rows have overlap_valid, the overlap scope returns None VMR."""
        df = _make_cell_day(
            [
                {"n_detections_MODIS": 2, "n_detections_VIIRS": 2, "overlap_valid": False},
                {"n_detections_MODIS": 4, "n_detections_VIIRS": 4, "overlap_valid": False},
            ]
        )
        result = check_overdispersion(df)

        # overlap scope has 0 rows
        assert result["overlap"]["MODIS"]["n"] == 0
        assert result["overlap"]["MODIS"]["mean"] is None
        assert result["overlap"]["MODIS"]["vmr"] is None

    def test_all_zero_counts_vmr_is_none(self) -> None:
        """When mean is 0, VMR is undefined (None)."""
        df = _make_cell_day(
            [
                {"n_detections_MODIS": 0, "n_detections_VIIRS": 0, "overlap_valid": False},
                {"n_detections_MODIS": 0, "n_detections_VIIRS": 0, "overlap_valid": False},
            ]
        )
        result = check_overdispersion(df)

        assert result["all"]["MODIS"]["mean"] == pytest.approx(0.0)
        assert result["all"]["MODIS"]["vmr"] is None
        assert result["all"]["MODIS"]["overdispersed"] is None

    def test_returned_structure_has_expected_keys(self) -> None:
        """The return dict has the documented two-level key structure."""
        result = check_overdispersion(_overlap_frame())

        assert set(result.keys()) == {"all", "overlap"}
        for scope in ("all", "overlap"):
            assert set(result[scope].keys()) == {"MODIS", "VIIRS"}
            for sensor in ("MODIS", "VIIRS"):
                inner = result[scope][sensor]
                assert set(inner.keys()) == {"n", "mean", "variance", "vmr", "overdispersed"}

    def test_missing_required_column_raises(self) -> None:
        df = _overlap_frame().drop(columns=["n_detections_MODIS"])
        with pytest.raises(ValueError, match="n_detections_MODIS"):
            check_overdispersion(df)

    def test_numpy_integer_counts_handled(self) -> None:
        """numpy integer dtype columns are accepted without error."""
        df = _overlap_frame().copy()
        df["n_detections_MODIS"] = df["n_detections_MODIS"].astype(np.int32)
        df["n_detections_VIIRS"] = df["n_detections_VIIRS"].astype(np.int64)

        result = check_overdispersion(df)
        assert result["all"]["MODIS"]["n"] == 4

    def test_large_overdispersion(self) -> None:
        """Highly variable counts produce VMR well above 1."""
        counts = [0, 0, 0, 100]
        df = _make_cell_day(
            [
                {"n_detections_MODIS": c, "n_detections_VIIRS": c, "overlap_valid": False}
                for c in counts
            ]
        )
        result = check_overdispersion(df)

        assert result["all"]["MODIS"]["vmr"] > 10
        assert result["all"]["MODIS"]["overdispersed"] is True


# ===========================================================================
# generate_overlap_diagnostics
# ===========================================================================


class TestGenerateOverlapDiagnostics:
    def test_creates_json_file_in_output_dir(self, tmp_path: Path) -> None:
        """The function creates overlap_diagnostics.json in output_dir."""
        df = _overlap_frame()
        dest = generate_overlap_diagnostics(df, tmp_path)

        assert dest.name == "overlap_diagnostics.json"
        assert dest.is_file()

    def test_creates_output_dir_when_missing(self, tmp_path: Path) -> None:
        """output_dir is created when it does not exist."""
        new_dir = tmp_path / "reports" / "nested"
        dest = generate_overlap_diagnostics(_overlap_frame(), new_dir)

        assert new_dir.is_dir()
        assert dest.exists()

    def test_returned_path_is_absolute(self, tmp_path: Path) -> None:
        """The returned Path is always absolute."""
        dest = generate_overlap_diagnostics(_overlap_frame(), tmp_path)
        assert dest.is_absolute()

    def test_json_is_valid_and_parseable(self, tmp_path: Path) -> None:
        """The written file is valid JSON that can be parsed back."""
        generate_overlap_diagnostics(_overlap_frame(), tmp_path)
        raw = (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_json_top_level_keys(self, tmp_path: Path) -> None:
        """The JSON has 'summary', 'sensor_ratios', and 'overdispersion' keys."""
        generate_overlap_diagnostics(_overlap_frame(), tmp_path)
        parsed = json.loads(
            (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        )
        assert set(parsed.keys()) == {"summary", "sensor_ratios", "overdispersion"}

    def test_summary_counts_match_dataframe(self, tmp_path: Path) -> None:
        """Summary total and overlap cell-day counts match the input frame."""
        df = _overlap_frame()  # 4 rows, 2 overlap
        generate_overlap_diagnostics(df, tmp_path)
        parsed = json.loads(
            (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        )
        assert parsed["summary"]["total_cell_days"] == 4
        assert parsed["summary"]["overlap_valid_cell_days"] == 2
        assert parsed["summary"]["overlap_fraction"] == pytest.approx(0.5)

    def test_sensor_ratios_in_json_match_function(self, tmp_path: Path) -> None:
        """sensor_ratios section equals compute_sensor_ratios output."""
        df = _overlap_frame()
        generate_overlap_diagnostics(df, tmp_path)
        parsed = json.loads(
            (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        )
        expected = compute_sensor_ratios(df)
        for key, value in expected.items():
            if value is None:
                assert parsed["sensor_ratios"][key] is None
            else:
                assert parsed["sensor_ratios"][key] == pytest.approx(value, rel=1e-6)

    def test_overdispersion_in_json_matches_function(self, tmp_path: Path) -> None:
        """overdispersion section equals check_overdispersion output."""
        df = _overlap_frame()
        generate_overlap_diagnostics(df, tmp_path)
        parsed = json.loads(
            (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        )
        expected = check_overdispersion(df)
        for scope in ("all", "overlap"):
            for sensor in ("MODIS", "VIIRS"):
                for stat_key, stat_value in expected[scope][sensor].items():
                    actual = parsed["overdispersion"][scope][sensor][stat_key]
                    if stat_value is None:
                        assert actual is None, f"{scope}/{sensor}/{stat_key} should be None"
                    elif isinstance(stat_value, bool):
                        assert actual == stat_value
                    else:
                        assert actual == pytest.approx(stat_value, rel=1e-6)

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """A second call overwrites the first file without error."""
        df = _overlap_frame()
        generate_overlap_diagnostics(df, tmp_path)
        first_mtime = (tmp_path / "overlap_diagnostics.json").stat().st_mtime

        # Modify df slightly and write again
        df2 = df.copy()
        df2.loc[0, "n_detections_MODIS"] = 99
        generate_overlap_diagnostics(df2, tmp_path)
        second_content = json.loads(
            (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        )
        # second write should reflect the new data
        assert second_content["summary"]["total_cell_days"] == 4

    def test_empty_dataframe_summary_has_zero_counts(self, tmp_path: Path) -> None:
        """An empty wide frame produces 0 total rows and 0 overlap rows."""
        empty = pd.DataFrame(
            columns=[
                "cell_id",
                "date",
                "n_detections_MODIS",
                "n_detections_VIIRS",
                "mean_frp_MODIS",
                "mean_frp_VIIRS",
                "overlap_valid",
            ]
        )
        generate_overlap_diagnostics(empty, tmp_path)
        parsed = json.loads(
            (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        )
        assert parsed["summary"]["total_cell_days"] == 0
        assert parsed["summary"]["overlap_valid_cell_days"] == 0
        assert parsed["summary"]["overlap_fraction"] is None

    def test_output_dir_is_a_file_raises(self, tmp_path: Path) -> None:
        """NotADirectoryError when output_dir path points to an existing file."""
        existing_file = tmp_path / "conflict.json"
        existing_file.write_text("not a dir", encoding="utf-8")

        with pytest.raises(NotADirectoryError):
            generate_overlap_diagnostics(_overlap_frame(), existing_file)

    def test_missing_required_column_raises_before_writing(self, tmp_path: Path) -> None:
        """ValueError is raised before any file is written."""
        df = _overlap_frame().drop(columns=["overlap_valid"])
        out_file = tmp_path / "overlap_diagnostics.json"

        with pytest.raises(ValueError, match="overlap_valid"):
            generate_overlap_diagnostics(df, tmp_path)

        assert not out_file.exists()

    def test_no_overlap_rows_produces_none_ratio_in_json(self, tmp_path: Path) -> None:
        """count_ratio_mean is null in JSON when there are no overlap rows."""
        df = _make_cell_day(
            [{"n_detections_MODIS": 1, "n_detections_VIIRS": 0, "overlap_valid": False}]
        )
        generate_overlap_diagnostics(df, tmp_path)
        parsed = json.loads(
            (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        )
        assert parsed["sensor_ratios"]["count_ratio_mean"] is None

    def test_accepts_string_path_for_output_dir(self, tmp_path: Path) -> None:
        """output_dir can be passed as a string rather than a Path."""
        dest = generate_overlap_diagnostics(_overlap_frame(), str(tmp_path))
        assert dest.exists()

    def test_no_nan_in_json_output(self, tmp_path: Path) -> None:
        """NaN values are never written (JSON has no NaN literal)."""
        df = _overlap_frame()
        generate_overlap_diagnostics(df, tmp_path)
        raw = (tmp_path / "overlap_diagnostics.json").read_text(encoding="utf-8")
        # JSON spec does not include NaN; json.loads would raise on 'NaN'
        assert "NaN" not in raw
        assert "Infinity" not in raw
