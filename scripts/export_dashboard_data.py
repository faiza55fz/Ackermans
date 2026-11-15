
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.grid.grid_builder import assign_cells, load_cell_size_degrees


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "data" / "clean"
OUTPUT_DIR = ROOT / "public" / "data"

DATASETS = {
    "western_ghats_karnataka": {
        "file": "western_ghats_karnataka_combined.parquet",
        "label": "Western Ghats, Karnataka",
    },
    "palisades_la": {
        "file": "palisades_la_combined.parquet",
        "label": "Palisades, California",
    },
}


def clean_value(value: Any) -> Any:
    """Convert pandas/numpy values into JSON-safe values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def load_dataset(region_key: str, info: dict) -> pd.DataFrame:
    path = CLEAN_DIR / info["file"]
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_parquet(path)
    required = {
        "sensor", "satellite", "datetime_utc", "date", "year",
        "latitude", "longitude", "confidence", "confidence_class",
        "frp", "daynight", "is_vegetation_fire",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")

    df = df.copy()
    df["region_key"] = region_key
    df["region_label"] = info["label"]
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.strftime("%Y-%m-%d")
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    df["year"] = df["datetime_utc"].dt.year
    df["month"] = df["datetime_utc"].dt.month
    df["sensor"] = df["sensor"].astype(str).str.upper().str.strip()
    df["satellite"] = df["satellite"].astype(str).str.strip()
    df["daynight"] = df["daynight"].astype(str).str.upper().str.strip()
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df.dropna(subset=["latitude", "longitude", "datetime_utc"])
    return df


def build_statistics(df: pd.DataFrame) -> dict:
    years = (
        df.groupby("year")
        .size()
        .rename("detections")
        .reset_index()
        .to_dict("records")
    )

    monthly = (
        df.groupby("month")
        .size()
        .rename("detections")
        .reindex(range(1, 13), fill_value=0)
        .rename_axis("month")
        .reset_index()
        .to_dict("records")
    )

    sensor_counts = (
        df.groupby("sensor")
        .size()
        .rename("detections")
        .reset_index()
        .to_dict("records")
    )

    satellite_counts = (
        df.groupby("satellite")
        .size()
        .rename("detections")
        .reset_index()
        .to_dict("records")
    )

    daynight_counts = (
        df["daynight"]
        .where(df["daynight"].isin(["D", "N"]), "Unknown")
        .map({"D": "Day", "N": "Night"})
        .fillna("Unknown")
        .value_counts()
        .rename_axis("period")
        .reset_index(name="detections")
        .to_dict("records")
    )

    confidence_counts = (
        df["confidence_class"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.title()
        .value_counts()
        .rename_axis("confidence")
        .reset_index(name="detections")
        .to_dict("records")
    )

    vegetation_counts = (
        df["is_vegetation_fire"]
        .value_counts(dropna=False)
        .rename_axis("vegetation_fire")
        .reset_index(name="detections")
        .to_dict("records")
    )

    frp = df["frp"].dropna()

    return {
        "total_detections": int(len(df)),
        "date_start": df["datetime_utc"].min().isoformat(),
        "date_end": df["datetime_utc"].max().isoformat(),
        "year_start": int(df["year"].min()),
        "year_end": int(df["year"].max()),
        "unique_detection_days": int(df["date"].nunique()),
        "unique_grid_cells": int(df["cell_id"].nunique()),
        "frp": {
            "available_records": int(frp.count()),
            "mean": clean_value(frp.mean()),
            "median": clean_value(frp.median()),
            "maximum": clean_value(frp.max()),
        },
        "yearly_trend": [
            {"year": int(r["year"]), "detections": int(r["detections"])}
            for r in years
        ],
        "monthly_distribution": [
            {"month": int(r["month"]), "detections": int(r["detections"])}
            for r in monthly
        ],
        "sensor_counts": [
            {"sensor": str(r["sensor"]), "detections": int(r["detections"])}
            for r in sensor_counts
        ],
        "satellite_counts": [
            {"satellite": str(r["satellite"]), "detections": int(r["detections"])}
            for r in satellite_counts
        ],
        "daynight_counts": [
            {"period": str(r["period"]), "detections": int(r["detections"])}
            for r in daynight_counts
        ],
        "confidence_counts": [
            {"confidence": str(r["confidence"]), "detections": int(r["detections"])}
            for r in confidence_counts
        ],
        "vegetation_counts": [
            {
                "vegetation_fire": clean_value(r["vegetation_fire"]),
                "detections": int(r["detections"]),
            }
            for r in vegetation_counts
        ],
    }


def build_map_cells(df: pd.DataFrame, cell_size: float) -> list[dict]:
    assigned = assign_cells(df, cell_size)

    assigned["_night"] = assigned["daynight"].isin(["N", "NIGHT"])
    assigned["_frp"] = pd.to_numeric(assigned["frp"], errors="coerce")

    grouped = (
        assigned.groupby(["region_key", "cell_id"], as_index=False)
        .agg(
            detections=("cell_id", "size"),
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
            mean_frp=("_frp", "mean"),
            max_frp=("_frp", "max"),
            night_detections=("_night", "sum"),
            modis_detections=("sensor", lambda s: int((s == "MODIS").sum())),
            viirs_detections=("sensor", lambda s: int((s == "VIIRS").sum())),
            first_date=("date", "min"),
            last_date=("date", "max"),
        )
    )

    cells = []
    for row in grouped.to_dict("records"):
        cells.append({
            "region": row["region_key"],
            "cell_id": row["cell_id"],
            "latitude": clean_value(row["latitude"]),
            "longitude": clean_value(row["longitude"]),
            "detections": int(row["detections"]),
            "mean_frp": clean_value(row["mean_frp"]),
            "max_frp": clean_value(row["max_frp"]),
            "night_detections": int(row["night_detections"]),
            "modis_detections": int(row["modis_detections"]),
            "viirs_detections": int(row["viirs_detections"]),
            "first_date": row["first_date"],
            "last_date": row["last_date"],
        })
    return cells


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    frames = []
    for key, info in DATASETS.items():
        print(f"Loading {info['file']}...")
        frames.append(load_dataset(key, info))

    combined = pd.concat(frames, ignore_index=True)

    cell_size = load_cell_size_degrees(ROOT / "config.yaml")
    combined = assign_cells(combined, cell_size)

    regions = {}
    for key, info in DATASETS.items():
        region_df = combined[combined["region_key"] == key].copy()
        regions[key] = {
            "label": info["label"],
            **build_statistics(region_df),
        }

    dashboard = {
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "source": "Cleaned NASA FIRMS combined Parquet datasets",
        "data_type": "observed_detections",
        "cell_size_degrees": cell_size,
        "total_detections": int(len(combined)),
        "regions": regions,
    }

    map_data = {
        "generated_at_utc": dashboard["generated_at_utc"],
        "cell_size_degrees": cell_size,
        "aggregation": "All dates and sensors aggregated by spatial cell",
        "regions": {
            key: build_map_cells(
                combined[combined["region_key"] == key],
                cell_size,
            )
            for key in DATASETS
        },
    }

    dashboard_path = OUTPUT_DIR / "dashboard.json"
    map_path = OUTPUT_DIR / "map.json"

    dashboard_path.write_text(
        json.dumps(dashboard, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    map_path.write_text(
        json.dumps(map_data, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    print("\nDashboard export complete.")
    print(f"Total observed detections: {len(combined):,}")
    print(f"Grid cell size: {cell_size} degrees")
    for key, region in regions.items():
        print(
            f"{region['label']}: "
            f"{region['total_detections']:,} detections, "
            f"{region['unique_grid_cells']:,} cells"
        )
    print(f"Dashboard JSON: {dashboard_path}")
    print(f"Map JSON: {map_path}")


if __name__ == "__main__":
    main()
