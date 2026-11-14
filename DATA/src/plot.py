#!/usr/bin/env python3
"""
src/plot.py - Generate Slide 2 visualization: Hotspots per year by sensor.

Creates reports/slide2_hotspots_per_year_by_sensor_<region>.png at 200 dpi
with sensor jump annotations and clean presentation styling.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ==============================================================================
# NAMED CONSTANTS & STYLING
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_CLEAN_DIR = BASE_DIR / "data" / "clean"
REPORTS_DIR = BASE_DIR / "reports"

REGIONS = {
    "palisades_la": {
        "title": "Pacific Palisades, Los Angeles",
        "bbox": (-118.75, 33.95, -118.40, 34.20)
    },
    "nsw_victoria_au": {
        "title": "New South Wales & Victoria, Australia",
        "bbox": (140.9, -39.2, 154.0, -28.1)
    },
    "western_ghats_karnataka": {
        "title": "Western Ghats, Karnataka, India",
        "bbox": (74.0, 13.3, 76.1, 15.8)
    },
    "punjab_haryana": {
        "title": "Punjab & Haryana, India",
        "bbox": (73.8, 27.6, 77.7, 32.6)
    }
}

SENSOR_COLORS = {
    "MODIS": "#D95F02",  # Rust orange
    "VIIRS": "#1F78B4"   # Deep blue
}

DPI = 200


def plot_hotspots_per_year(region_id: str):
    """Generate and save the slide 2 pitch chart for a given region."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    combined_parquet = DATA_CLEAN_DIR / f"{region_id}_combined.parquet"

    if not combined_parquet.exists():
        print(f"Error: Cleaned dataset not found: {combined_parquet}")
        return False

    df = pd.read_parquet(combined_parquet)
    if len(df) == 0:
        print(f"Warning: No fire detections in {region_id}")
        return False

    reg_title = REGIONS[region_id]["title"]

    # Aggregate counts by year and sensor
    counts = df.groupby(["year", "sensor"]).size().unstack(fill_value=0)

    # Ensure full continuous range of years from 2000 to max year
    min_year = 2000
    max_year = df["year"].max()
    full_years = list(range(min_year, max_year + 1))
    counts = counts.reindex(full_years, fill_value=0)

    # Initialize figure
    fig, ax = plt.subplots(figsize=(11, 6), dpi=DPI)

    # Plot lines with markers
    for sens in ["MODIS", "VIIRS"]:
        if sens in counts.columns:
            ax.plot(
                counts.index,
                counts[sens],
                marker="o",
                linewidth=2.5,
                markersize=6,
                color=SENSOR_COLORS.get(sens, "#333333"),
                label=f"{sens} Active Detections"
            )

    # Vertical marker at 2012 for VIIRS launch
    ax.axvline(x=2012, color="#E31A1C", linestyle="--", linewidth=1.8, alpha=0.85)
    ax.text(
        2012.2,
        ax.get_ylim()[1] * 0.90,
        "VIIRS starts (Jan 2012)",
        color="#B10026",
        fontsize=10,
        fontweight="bold",
        verticalalignment="top"
    )

    # Explanatory sensor resolution annotation
    explanation_text = (
        "Sensor Shift Notice: The post-2012 increase reflects sensor capabilities (VIIRS did not exist\n"
        "before 2012 and its 375m pixels detect smaller fires than MODIS at 1km), not a real change in fire activity."
    )
    ax.text(
        0.5, -0.15,
        explanation_text,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        fontstyle="italic",
        color="#444444",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#F7F7F7", edgecolor="#CCCCCC", alpha=0.9)
    )

    # Labels and titles
    ax.set_title(f"Annual Active Fire Hotspots by Sensor ({min_year}–{max_year})\n{reg_title}", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Observation Year", fontsize=11, fontweight="semibold")
    ax.set_ylabel("Annual Hotspot Detections (Count)", fontsize=11, fontweight="semibold")

    # Grid and axis formatting
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=True, facecolor="white", edgecolor="#DDDDDD", loc="upper left", fontsize=10)

    plt.tight_layout()

    output_png = REPORTS_DIR / f"slide2_hotspots_per_year_by_sensor_{region_id}.png"
    plt.savefig(output_png, dpi=DPI, bbox_inches="tight")
    plt.close()

    print(f">> Chart saved: {output_png}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate annual hotspots chart.")
    parser.add_argument("--region", choices=list(REGIONS.keys()) + ["all"], default="palisades_la")
    parser.add_argument("--all", action="store_true", help="Plot all regions")

    args = parser.parse_args()
    target_regions = list(REGIONS.keys()) if (args.all or args.region == "all") else [args.region]

    for reg in target_regions:
        plot_hotspots_per_year(reg)


if __name__ == "__main__":
    main()
