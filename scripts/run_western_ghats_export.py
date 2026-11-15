
import sys
from shutil import copy2
from pathlib import Path

import pandas as pd

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.grid.grid_builder import build_cell_day_table
from src.models.counts import (
    prepare_model_frame,
    fit_count_model,
    _predict,
)
from src.models.frp import fit_frp_calibrator, predict_frp
from src.export.exporter import export_harmonized_dataset

region = "western_ghats_karnataka"


def build_metric_series(
    observed: pd.DataFrame,
    estimated: pd.DataFrame,
    period: str,
) -> list[dict]:
    observed_frame = observed.copy()
    estimated_frame = estimated.copy()
    observed_frame["period"] = pd.to_datetime(observed_frame["date"]).dt.to_period(period).astype(str)
    estimated_frame["period"] = pd.to_datetime(estimated_frame["date"]).dt.to_period(period).astype(str)

    observed_metrics = observed_frame.groupby("period").agg(
        observed_modis_detections=("n_detections_MODIS", "sum"),
        observed_viirs_detections=("n_detections_VIIRS", "sum"),
        observed_modis_frp=("mean_frp_MODIS", "mean"),
        observed_viirs_frp=("mean_frp_VIIRS", "mean"),
    )
    estimated_metrics = estimated_frame.groupby("period").agg(
        estimated_viirs_detections=("predicted_n_detections_VIIRS", "sum"),
        estimated_calibrated_frp=("calibrated_frp", "mean"),
    )
    series = observed_metrics.join(estimated_metrics, how="outer").sort_index()

    records = []
    for period_label, row in series.iterrows():
        record = {"period": period_label}
        for column, value in row.items():
            record[column] = None if pd.isna(value) else float(value)
        records.append(record)
    return records


input_name = f"{region}_combined.parquet"
input_candidates = (
    project_root / "DATA" / "data" / "clean" / input_name,
    project_root / "data" / "data" / "clean" / input_name,
)
input_path = next(
    (candidate for candidate in input_candidates if candidate.is_file()),
    None,
)
if input_path is None:
    checked_paths = "\n".join(f"  {path}" for path in input_candidates)
    raise FileNotFoundError(
        f"Could not find {input_name}. Checked:\n{checked_paths}"
    )

raw = pd.read_parquet(input_path)
grid = build_cell_day_table(raw)
grid["region"] = region

# Count model and matching cell/date keys
model_frame = prepare_model_frame(grid)

eligible = (
    grid["overlap_valid"].astype(bool)
    & (grid["n_detections_MODIS"].fillna(0).astype(int) >= 1)
)
keys = grid.loc[eligible, ["cell_id", "date"]].reset_index(drop=True)

if len(keys) != len(model_frame):
    raise ValueError("Count-model rows do not match cell/date keys")

model_frame["cell_id"] = keys["cell_id"]
model_frame["date"] = keys["date"]
model_frame["region"] = region

count_model = fit_count_model(model_frame)

estimated = model_frame[["cell_id", "date", "region"]].copy()
estimated["predicted_n_detections_VIIRS"] = _predict(
    count_model, model_frame
)

# FRP calibration
frp_train = grid.dropna(
    subset=["mean_frp_MODIS", "mean_frp_VIIRS"]
).copy()

frp_train = frp_train[
    (frp_train["mean_frp_MODIS"] > 0)
    & (frp_train["mean_frp_VIIRS"] > 0)
].copy()

frp_train["month"] = pd.to_datetime(frp_train["date"]).dt.month
calibrator = fit_frp_calibrator(frp_train)

frp_predictions = predict_frp(calibrator, frp_train)

frp_estimates = frp_train[["cell_id", "date"]].copy()
frp_estimates["calibrated_frp"] = frp_predictions[
    "calibrated_frp"
].to_numpy()

estimated = estimated.merge(
    frp_estimates,
    on=["cell_id", "date"],
    how="left",
    validate="one_to_one",
)

observed = grid.copy()

result = export_harmonized_dataset(
    observed,
    estimated,
    "outputs/western_ghats/harmonized",
    metadata={
        "region": region,
        "input": "western_ghats_karnataka_combined.parquet",
        "count_model": count_model.family,
        "frp_method": calibrator.method,
        "note": "In-sample pipeline output; not independent validation.",
    },
    metrics={
        "timeseries": {
            "yearly": build_metric_series(observed, estimated, "Y"),
            "monthly": build_metric_series(observed, estimated, "M"),
        }
    },
)

public_summary_path = project_root / "public" / "data" / "harmonized_summary.json"
public_summary_path.parent.mkdir(parents=True, exist_ok=True)
copy2(result.summary_path, public_summary_path)

print("Export complete!")
print("Observed rows:", len(observed))
print("Estimated rows:", len(estimated))
print(
    "Rows with calibrated FRP:",
    estimated["calibrated_frp"].notna().sum(),
)
print("Total exported rows:", result.n_rows)
print("Parquet:", result.parquet_path)
print("Summary:", result.summary_path)
print("Frontend summary:", public_summary_path)
