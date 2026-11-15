"""Tests for cell assignment and MODIS/VIIRS cell-day tables."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.grid.grid_builder import (
    DETECTION_COLUMNS,
    add_overlap_valid,
    aggregate_cell_day,
    assign_cell,
    assign_cells,
    build_cell_day_table,
    load_cell_size_degrees,
    pivot_cell_day,
    require_detection_columns,
)

PROJECT_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"


def _detection(**overrides: object) -> dict[str, object]:
    """Return one cleaned detection row, with optional column overrides."""

    row: dict[str, object] = {
        "region": "palisades_la",
        "sensor": "MODIS",
        "satellite": "Aqua",
        "processing": "SP",
        "datetime_utc": "2020-01-02 09:10:00+00:00",
        "date": "2020-01-02",
        "year": 2020,
        "latitude": 34.1938,
        "longitude": -118.7358,
        "confidence": "100",
        "confidence_class": "high",
        "frp": 10.0,
        "daynight": "D",
        "scan": 1.0,
        "track": 1.0,
        "instrument": "MODIS",
        "version": "6.03",
        "brightness": 320.0,
        "bright_t31": 290.0,
        "bright_ti4": None,
        "bright_ti5": None,
        "type": 0,
        "is_vegetation_fire": True,
    }
    row.update(overrides)
    return row


def _frame(*rows: dict[str, object]) -> pd.DataFrame:
    """Build a detection frame that preserves the cleaned column order."""

    records = list(rows) or [_detection()]
    return pd.DataFrame(records).loc[:, list(DETECTION_COLUMNS)]


def test_detection_schema_has_23_columns() -> None:
    """The cleaned FIRMS schema has the 23 columns used by the grid."""

    assert len(DETECTION_COLUMNS) == 23
    assert DETECTION_COLUMNS[:4] == ("region", "sensor", "satellite", "processing")
    assert "is_vegetation_fire" in DETECTION_COLUMNS


def test_assign_cell_uses_lower_left_edge() -> None:
    """Points fall in the cell whose lower-left corner is below and left of them."""

    assert assign_cell(34.1938, -118.7358, 0.25) == "34.00_-118.75"
    assert assign_cell(34.25, -118.75, 0.25) == "34.25_-118.75"
    assert assign_cell(34.249, -118.7501, 0.25) == "34.00_-119.00"


def test_assign_cell_bins_southern_and_western_coordinates() -> None:
    """Negative coordinates use floor division, so bins move away from zero."""

    assert assign_cell(-33.1, 18.0, 0.25) == "-33.25_18.00"
    assert assign_cell(-0.01, -0.01, 1.0) == "-1_-1"


def test_assign_cell_formats_edges_to_the_cell_size_precision() -> None:
    """Printed edges keep the decimal places implied by the cell size."""

    assert assign_cell(34.26, -118.24, 0.5) == "34.0_-118.5"
    assert assign_cell(34.26, -118.24, 1) == "34_-119"


def test_assign_cell_rejects_invalid_inputs() -> None:
    """Cell size must be positive and both coordinates must be finite."""

    with pytest.raises(ValueError, match="positive finite"):
        assign_cell(34.0, -118.0, 0)
    with pytest.raises(ValueError, match="positive finite"):
        assign_cell(34.0, -118.0, -0.25)
    with pytest.raises(TypeError, match="positive number"):
        assign_cell(34.0, -118.0, True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="lat must be finite"):
        assign_cell(float("nan"), -118.0, 0.25)
    with pytest.raises(ValueError, match="lon must be finite"):
        assign_cell(34.0, float("inf"), 0.25)
    with pytest.raises(TypeError, match="lat must be a real number"):
        assign_cell("34", -118.0, 0.25)  # type: ignore[arg-type]


def test_assign_cells_adds_ids_without_changing_the_input() -> None:
    """Cell assignment returns a new frame and leaves the source frame unchanged."""

    source = _frame(_detection(), _detection(latitude=34.4, longitude=-118.4))
    original = source.copy()

    assigned = assign_cells(source, 0.25)

    pd.testing.assert_frame_equal(source, original)
    assert "cell_id" not in source.columns
    assert assigned["cell_id"].tolist() == ["34.00_-118.75", "34.25_-118.50"]


def test_assign_cells_requires_coordinates() -> None:
    """Missing latitude or longitude is reported before any ids are built."""

    with pytest.raises(ValueError, match="latitude"):
        assign_cells(pd.DataFrame({"longitude": [1.0]}), 0.25)


def test_load_cell_size_degrees_reads_project_config() -> None:
    """The repository config sets the common grid to 0.25 degrees."""

    assert load_cell_size_degrees(PROJECT_CONFIG) == 0.25
    assert load_cell_size_degrees() == 0.25


def test_load_cell_size_degrees_defaults_when_unset(tmp_path: Path) -> None:
    """A missing file, empty file, or omitted key falls back to 0.25."""

    missing = tmp_path / "absent.yaml"
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    other_keys = tmp_path / "other.yaml"
    other_keys.write_text("min_overlap_samples: 30\n", encoding="utf-8")
    explicit_null = tmp_path / "null.yaml"
    explicit_null.write_text("cell_size_degrees:\n", encoding="utf-8")

    assert load_cell_size_degrees(missing) == 0.25
    assert load_cell_size_degrees(empty) == 0.25
    assert load_cell_size_degrees(other_keys) == 0.25
    assert load_cell_size_degrees(explicit_null) == 0.25


def test_load_cell_size_degrees_rejects_bad_config(tmp_path: Path) -> None:
    """Config files must be mappings and cell size must be positive."""

    sequence = tmp_path / "list.yaml"
    sequence.write_text("- 0.25\n", encoding="utf-8")
    zero = tmp_path / "zero.yaml"
    zero.write_text(yaml.safe_dump({"cell_size_degrees": 0}), encoding="utf-8")
    custom = tmp_path / "custom.yaml"
    custom.write_text(yaml.safe_dump({"cell_size_degrees": 0.5}), encoding="utf-8")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_cell_size_degrees(sequence)
    with pytest.raises(ValueError, match="positive finite"):
        load_cell_size_degrees(zero)
    assert load_cell_size_degrees(custom) == 0.5


def test_require_detection_columns_accepts_the_cleaned_schema() -> None:
    """A full 23-column frame passes, and a dropped column is named."""

    require_detection_columns(_frame())
    incomplete = _frame().drop(columns=["track"])

    with pytest.raises(ValueError, match="track"):
        require_detection_columns(incomplete)


def test_aggregate_cell_day_computes_sensor_metrics() -> None:
    """Counts, FRP, scan, night fraction, and fire_day match the grouped rows."""

    frame = pd.DataFrame(
        [
            {
                "cell_id": "34.00_-118.75",
                "date": date(2020, 1, 2),
                "sensor": " modis ",
                "frp": 10.0,
                "scan": 1.0,
                "daynight": "N",
            },
            {
                "cell_id": "34.00_-118.75",
                "date": date(2020, 1, 2),
                "sensor": "MODIS",
                "frp": 30.0,
                "scan": 3.0,
                "daynight": "D",
            },
            {
                "cell_id": "34.00_-118.75",
                "date": date(2020, 1, 2),
                "sensor": "VIIRS",
                "frp": None,
                "scan": 2.5,
                "daynight": "night",
            },
        ]
    )

    aggregated = aggregate_cell_day(frame)

    assert aggregated["sensor"].tolist() == ["MODIS", "VIIRS"]
    modis = aggregated.loc[aggregated["sensor"].eq("MODIS")].iloc[0]
    viirs = aggregated.loc[aggregated["sensor"].eq("VIIRS")].iloc[0]
    assert int(modis["n_detections"]) == 2
    assert int(modis["fire_day"]) == 1
    assert modis["mean_frp"] == pytest.approx(20.0)
    assert modis["max_frp"] == pytest.approx(30.0)
    assert modis["mean_scan"] == pytest.approx(2.0)
    assert modis["night_fraction"] == pytest.approx(0.5)
    assert int(viirs["n_detections"]) == 1
    assert int(viirs["fire_day"]) == 1
    assert pd.isna(viirs["mean_frp"])
    assert pd.isna(viirs["max_frp"])
    assert viirs["mean_scan"] == pytest.approx(2.5)
    assert viirs["night_fraction"] == pytest.approx(1.0)


def test_aggregate_cell_day_keeps_null_frp_in_the_count() -> None:
    """A detection with missing FRP still counts, and the mean skips that FRP."""

    frame = pd.DataFrame(
        [
            {
                "cell_id": "1.00_2.00",
                "date": date(2020, 1, 3),
                "sensor": "VIIRS",
                "frp": 10.0,
                "scan": 1.0,
                "daynight": None,
            },
            {
                "cell_id": "1.00_2.00",
                "date": date(2020, 1, 3),
                "sensor": "VIIRS",
                "frp": None,
                "scan": 1.0,
                "daynight": "D",
            },
        ]
    )

    aggregated = aggregate_cell_day(frame)

    assert int(aggregated.loc[0, "n_detections"]) == 2
    assert aggregated.loc[0, "mean_frp"] == pytest.approx(10.0)
    assert aggregated.loc[0, "night_fraction"] == pytest.approx(0.0)


def test_aggregate_cell_day_rejects_bad_frames() -> None:
    """Aggregation requires its columns and a sensor on every row."""

    with pytest.raises(ValueError, match="scan"):
        aggregate_cell_day(pd.DataFrame({"cell_id": ["a"], "date": ["2020-01-02"]}))

    empty = pd.DataFrame(columns=["cell_id", "date", "sensor", "frp", "scan", "daynight"])
    assert aggregate_cell_day(empty).empty
    assert list(aggregate_cell_day(empty).columns) == [
        "cell_id",
        "date",
        "sensor",
        "n_detections",
        "fire_day",
        "mean_frp",
        "max_frp",
        "mean_scan",
        "night_fraction",
    ]

    missing_sensor = pd.DataFrame(
        [
            {
                "cell_id": "1_2",
                "date": date(2020, 1, 2),
                "sensor": None,
                "frp": 1.0,
                "scan": 1.0,
                "daynight": "D",
            }
        ]
    )
    with pytest.raises(ValueError, match="sensor contains null"):
        aggregate_cell_day(missing_sensor)


def test_pivot_cell_day_places_modis_and_viirs_side_by_side() -> None:
    """Each cell-day has MODIS metrics, then VIIRS metrics, with gaps filled at zero."""

    aggregated = pd.DataFrame(
        [
            {
                "cell_id": "34.00_-118.75",
                "date": date(2020, 1, 2),
                "sensor": "VIIRS",
                "n_detections": 1,
                "fire_day": 1,
                "mean_frp": 5.0,
                "max_frp": 5.0,
                "mean_scan": 1.5,
                "night_fraction": 1.0,
            },
            {
                "cell_id": "34.00_-118.75",
                "date": date(2020, 1, 3),
                "sensor": "MODIS",
                "n_detections": 2,
                "fire_day": 1,
                "mean_frp": 8.0,
                "max_frp": 9.0,
                "mean_scan": 2.0,
                "night_fraction": 0.0,
            },
        ]
    )

    wide = pivot_cell_day(aggregated)

    assert list(wide.columns) == [
        "cell_id",
        "date",
        "n_detections_MODIS",
        "fire_day_MODIS",
        "mean_frp_MODIS",
        "max_frp_MODIS",
        "mean_scan_MODIS",
        "night_fraction_MODIS",
        "n_detections_VIIRS",
        "fire_day_VIIRS",
        "mean_frp_VIIRS",
        "max_frp_VIIRS",
        "mean_scan_VIIRS",
        "night_fraction_VIIRS",
    ]
    first = wide.loc[wide["date"].eq(date(2020, 1, 2))].iloc[0]
    assert int(first["n_detections_MODIS"]) == 0
    assert int(first["fire_day_MODIS"]) == 0
    assert pd.isna(first["mean_frp_MODIS"])
    assert int(first["n_detections_VIIRS"]) == 1
    assert first["max_frp_VIIRS"] == pytest.approx(5.0)
    second = wide.loc[wide["date"].eq(date(2020, 1, 3))].iloc[0]
    assert int(second["n_detections_MODIS"]) == 2
    assert int(second["fire_day_VIIRS"]) == 0
    assert pd.isna(second["night_fraction_VIIRS"])


def test_pivot_cell_day_appends_other_sensors_after_the_pair() -> None:
    """Sensors other than MODIS and VIIRS keep their metrics after the canonical pair."""

    aggregated = pd.DataFrame(
        [
            {
                "cell_id": "1.00_2.00",
                "date": date(2020, 2, 1),
                "sensor": "LANDSAT",
                "n_detections": 4,
                "fire_day": 1,
                "mean_frp": 3.0,
                "max_frp": 4.0,
                "mean_scan": 1.0,
                "night_fraction": 0.25,
            }
        ]
    )

    wide = pivot_cell_day(aggregated)

    assert wide.columns[-6:].tolist() == [
        "n_detections_LANDSAT",
        "fire_day_LANDSAT",
        "mean_frp_LANDSAT",
        "max_frp_LANDSAT",
        "mean_scan_LANDSAT",
        "night_fraction_LANDSAT",
    ]
    assert int(wide.loc[0, "n_detections_MODIS"]) == 0
    assert int(wide.loc[0, "n_detections_VIIRS"]) == 0
    assert int(wide.loc[0, "n_detections_LANDSAT"]) == 4


def test_pivot_cell_day_empty_and_invalid_inputs() -> None:
    """An empty aggregate still has both sensor blocks, and bad frames fail clearly."""

    empty = pd.DataFrame(
        columns=[
            "cell_id",
            "date",
            "sensor",
            "n_detections",
            "fire_day",
            "mean_frp",
            "max_frp",
            "mean_scan",
            "night_fraction",
        ]
    )
    wide = pivot_cell_day(empty)

    assert wide.empty
    assert "mean_scan_MODIS" in wide.columns
    assert "night_fraction_VIIRS" in wide.columns
    with pytest.raises(ValueError, match="mean_frp"):
        pivot_cell_day(empty.drop(columns=["mean_frp"]))


def test_add_overlap_valid_requires_both_sensors() -> None:
    """Overlap is true only when MODIS and VIIRS each have a detection that cell-day."""

    cell_days = pd.DataFrame(
        [
            {"cell_id": "a", "n_detections_MODIS": 2, "n_detections_VIIRS": 1},
            {"cell_id": "b", "n_detections_MODIS": 0, "n_detections_VIIRS": 3},
            {"cell_id": "c", "n_detections_MODIS": 1, "n_detections_VIIRS": 0},
            {"cell_id": "d", "n_detections_MODIS": None, "n_detections_VIIRS": 1},
        ]
    )
    original = cell_days.copy()

    flagged = add_overlap_valid(cell_days)

    pd.testing.assert_frame_equal(cell_days, original)
    assert flagged["overlap_valid"].tolist() == [True, False, False, False]
    assert flagged["overlap_valid"].dtype == bool
    with pytest.raises(ValueError, match="n_detections_VIIRS"):
        add_overlap_valid(cell_days.drop(columns=["n_detections_VIIRS"]))


def test_build_cell_day_table_bins_aggregates_and_flags_overlap() -> None:
    """The public table uses the config cell size and keeps the input unchanged."""

    source = _frame(
        _detection(frp=10.0, scan=1.0, daynight="N"),
        _detection(
            frp=30.0,
            scan=3.0,
            daynight="D",
            latitude=34.2,
            longitude=-118.7,
        ),
        _detection(
            sensor="VIIRS",
            satellite="NOAA-20",
            instrument="VIIRS",
            frp=5.0,
            scan=2.0,
            daynight="N",
            brightness=None,
            bright_t31=None,
            bright_ti4=330.0,
            bright_ti5=300.0,
            confidence="nominal",
        ),
        _detection(
            sensor="viirs",
            date="2020-01-03",
            datetime_utc="2020-01-03 11:00:00+00:00",
            latitude=34.6,
            longitude=-118.2,
            frp=7.0,
            scan=1.2,
            daynight="D",
        ),
    )
    original = source.copy()

    table = build_cell_day_table(source)

    pd.testing.assert_frame_equal(source, original)
    assert "cell_id" not in source.columns
    january_second = table.loc[table["date"].eq(date(2020, 1, 2))].iloc[0]
    january_third = table.loc[table["date"].eq(date(2020, 1, 3))].iloc[0]
    assert january_second["cell_id"] == "34.00_-118.75"
    assert int(january_second["n_detections_MODIS"]) == 2
    assert int(january_second["fire_day_MODIS"]) == 1
    assert january_second["mean_frp_MODIS"] == pytest.approx(20.0)
    assert january_second["max_frp_MODIS"] == pytest.approx(30.0)
    assert january_second["mean_scan_MODIS"] == pytest.approx(2.0)
    assert january_second["night_fraction_MODIS"] == pytest.approx(0.5)
    assert int(january_second["n_detections_VIIRS"]) == 1
    assert january_second["mean_frp_VIIRS"] == pytest.approx(5.0)
    assert bool(january_second["overlap_valid"])
    assert january_third["cell_id"] == "34.50_-118.25"
    assert int(january_third["n_detections_MODIS"]) == 0
    assert int(january_third["fire_day_MODIS"]) == 0
    assert int(january_third["fire_day_VIIRS"]) == 1
    assert not bool(january_third["overlap_valid"])


def test_build_cell_day_table_honors_an_explicit_cell_size(tmp_path: Path) -> None:
    """An explicit cell size is used even when a config file says something else."""

    config = tmp_path / "config.yaml"
    config.write_text("cell_size_degrees: 0.25\n", encoding="utf-8")
    source = _frame(_detection(latitude=34.2, longitude=-118.2))

    table = build_cell_day_table(source, cell_size_deg=1, config_path=config)

    assert table.loc[0, "cell_id"] == "34_-119"
    assert not bool(table.loc[0, "overlap_valid"])


def test_build_cell_day_table_collapses_timestamps_to_the_calendar_day() -> None:
    """Datetime values on the same UTC date stay in one cell-day."""

    source = _frame(
        _detection(
            date=datetime(2020, 1, 2, 1, 0, tzinfo=timezone.utc),
            frp=4.0,
            daynight="D",
        ),
        _detection(
            date=datetime(2020, 1, 2, 23, 0, tzinfo=timezone.utc),
            sensor="VIIRS",
            frp=6.0,
            daynight="N",
        ),
    )

    table = build_cell_day_table(source, cell_size_deg=0.25)

    assert len(table) == 1
    assert table.loc[0, "date"] == date(2020, 1, 2)
    assert bool(table.loc[0, "overlap_valid"])
    assert table.loc[0, "max_frp_MODIS"] == pytest.approx(4.0)
    assert table.loc[0, "max_frp_VIIRS"] == pytest.approx(6.0)


def test_build_cell_day_table_rejects_incomplete_or_undated_rows() -> None:
    """Schema gaps and null dates are errors, and an empty schema frame is empty."""

    with pytest.raises(ValueError, match="bright_ti5"):
        build_cell_day_table(_frame().drop(columns=["bright_ti5"]))

    undated = _frame(_detection(date=None))
    with pytest.raises(ValueError, match="date contains null"):
        build_cell_day_table(undated)

    empty = pd.DataFrame(columns=list(DETECTION_COLUMNS))
    table = build_cell_day_table(empty, cell_size_deg=0.25)
    assert table.empty
    assert table["overlap_valid"].dtype == bool
    assert "mean_frp_MODIS" in table.columns
    assert "mean_frp_VIIRS" in table.columns
