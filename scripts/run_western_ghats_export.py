
import pandas as pd

from src.grid.grid_builder import build_cell_day_table
from src.models.counts import (
    prepare_model_frame,
    fit_count_model,
    _predict,
)
from src.models.frp import fit_frp_calibrator, predict_frp
from src.export.exporter import export_harmonized_dataset

region = "western_ghats_karnataka"

raw = pd.read_parquet(
    "DATA/data/clean/western_ghats_karnataka_combined.parquet"
)
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
)

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
