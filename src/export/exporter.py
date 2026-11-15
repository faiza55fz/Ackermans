"""Write harmonized fire observations and summary metadata to disk."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExportResult:
    """Paths and row count for a completed harmonized-data export."""

    parquet_path: Path
    summary_path: Path
    n_rows: int


def export_harmonized_dataset(
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
    output_dir: Path | str,
    *,
    metadata: Mapping[str, Any] | None = None,
    metrics: Mapping[str, Any] | None = None,
) -> ExportResult:
    """Export observed and estimated records with explicit source labels.

    The two input frames are concatenated into ``harmonized_hotspots.parquet``
    with a ``source`` column set to ``"observed"`` or ``"estimated"``.
    If either input already contains ``source`` or ``is_estimated``, its
    values must agree with the input's observed/estimated role. Inputs are
    never modified.

    ``summary.json`` records export metadata, record counts by source,
    numeric column aggregates (count, mean, minimum, and maximum) overall
    and by source, and any caller-supplied aggregate metrics.

    Parameters
    ----------
    observed:
        Rows containing directly observed/harmonized measurements.
    estimated:
        Rows containing modeled estimates. May be empty, but must have
        columns compatible with the observed frame when non-empty.
    output_dir:
        Directory to create for the Parquet and JSON outputs.
    metadata:
        Optional JSON-serializable run metadata, such as project version,
        input dates, grid resolution, or model configuration.
    metrics:
        Optional JSON-serializable aggregate metrics to include in the
        summary, such as validation MAE, RMSE, bias, and R².

    Returns
    -------
    ExportResult
        Paths to both output files and the number of exported rows.

    Raises
    ------
    ValueError
        If an input source label is inconsistent or metadata/metrics
        cannot be serialized as JSON.
    """
    observed_frame = _label_source(observed, "observed", False)
    estimated_frame = _label_source(estimated, "estimated", True)
    combined = pd.concat(
        [observed_frame, estimated_frame],
        axis=0,
        ignore_index=True,
        sort=False,
    )

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = target_dir / "harmonized_hotspots.parquet"
    summary_path = target_dir / "summary.json"

    numeric_columns = list(_numeric_aggregates(combined))
    summary = {
        "metadata": {
            **dict(metadata or {}),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "format": "parquet",
            "dataset": parquet_path.name,
            "n_rows": int(len(combined)),
            "columns": combined.columns.tolist(),
        },
        "aggregated_metrics": {
            "rows_by_source": {
                "observed": int(len(observed_frame)),
                "estimated": int(len(estimated_frame)),
            },
            "numeric_columns": _numeric_aggregates(combined),
            "numeric_columns_by_source": {
                "observed": _numeric_aggregates(observed_frame, numeric_columns),
                "estimated": _numeric_aggregates(estimated_frame, numeric_columns),
            },
            "provided": dict(metrics or {}),
        },
    }

    try:
        json.dumps(summary, allow_nan=False, default=_json_default)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"metadata or metrics are not JSON serializable: {exc}") from exc

    combined.to_parquet(parquet_path, index=False)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False, default=_json_default)
        handle.write("\n")

    return ExportResult(
        parquet_path=parquet_path,
        summary_path=summary_path,
        n_rows=len(combined),
    )


def _label_source(
    frame: pd.DataFrame,
    source: str,
    is_estimated: bool,
) -> pd.DataFrame:
    """Copy a source frame and validate or add its unambiguous labels."""
    if "source" in frame.columns:
        existing_source = frame["source"]
        if existing_source.isna().any() or not existing_source.eq(source).all():
            raise ValueError(
                f"{source} input must have source values set to {source!r}"
            )
    if "is_estimated" in frame.columns:
        flags = frame["is_estimated"]
        if flags.isna().any() or not flags.map(
            lambda value: isinstance(value, (bool, np.bool_))
        ).all():
            raise ValueError("is_estimated values must be non-null booleans")
        if not flags.eq(is_estimated).all():
            expected = "True" if is_estimated else "False"
            raise ValueError(f"{source} input requires is_estimated={expected}")

    labeled = frame.copy()
    labeled["source"] = source
    if "is_estimated" in labeled.columns:
        labeled["is_estimated"] = labeled["is_estimated"].astype(bool)
    return labeled


def _numeric_aggregates(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, dict[str, int | float]]:
    """Summarize finite numeric fields, excluding boolean indicator columns."""
    output: dict[str, dict[str, int | float]] = {}
    numeric_columns = (
        frame.select_dtypes(include=[np.number]).columns.tolist()
        if columns is None
        else columns
    )
    for column in numeric_columns:
        if column in frame.columns and pd.api.types.is_bool_dtype(frame[column]):
            continue
        if column not in frame.columns:
            output[column] = {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0}
            continue
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        if len(finite) == 0:
            output[column] = {
                "count": 0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
            }
            continue
        output[column] = {
            "count": int(len(finite)),
            "mean": float(np.mean(finite)),
            "min": float(np.min(finite)),
            "max": float(np.max(finite)),
        }
    return output


def _json_default(value: object) -> object:
    """Convert common NumPy and pandas scalar values to JSON primitives."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        numeric = float(value)
        if not np.isfinite(numeric):
            raise ValueError("JSON numbers must be finite")
        return numeric
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if pd.isna(value):
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
