#!/usr/bin/env python3
"""
run_all.py - Master pipeline runner for NASA FIRMS fire data.

Executes per region in order:
  palisades_la -> western_ghats_karnataka -> punjab_haryana -> nsw_victoria_au

For each region:
  1. download.py  (Download raw data by region, sensor, and year within seasonal windows)
  2. ingest.py    (Clean, standardize, apply confidence filter, export Parquet)
  3. checks.py    (Verify bounding boxes, nulls, FRP, and row reconciliation; STOPS if any fail)
  4. plot.py      (Generate slide 2 pitch visualization at 200 dpi)
"""

import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

REGIONS_ORDER = [
    "palisades_la",
    "western_ghats_karnataka",
    "punjab_haryana",
    "nsw_victoria_au"
]


def run_command(cmd_args: list[str], description: str) -> bool:
    """Run a pipeline sub-command, stream output, and check return code."""
    print(f"\n=======================================================")
    print(f"STEP: {description}")
    print(f"Command: {' '.join(cmd_args)}")
    print(f"=======================================================")

    res = subprocess.run(cmd_args, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"\n[PIPELINE ERROR] Command failed with exit code {res.returncode}: {description}", file=sys.stderr)
        return False
    return True


def run_pipeline_for_region(region_id: str, skip_download: bool, workers: int) -> bool:
    """Run download, ingest, sanity checks, and plotting for a single region."""
    print(f"\n######################################################################")
    print(f"PIPELINE EXECUTION FOR REGION: {region_id}")
    print(f"######################################################################")

    # Step 1: Download
    if not skip_download:
        dl_cmd = [
            PYTHON_EXE, "src/download.py",
            "--region", region_id,
            "--sensor", "all",
            "--workers", str(workers),
            "--wait-on-limit"
        ]
        if not run_command(dl_cmd, f"Download raw data for {region_id}"):
            return False
    else:
        print(f"[INFO] Skipping download step for {region_id} (--skip-download passed).")

    # Step 2: Ingest
    ingest_cmd = [PYTHON_EXE, "src/ingest.py", "--region", region_id]
    if not run_command(ingest_cmd, f"Ingest and clean data for {region_id}"):
        return False

    # Step 3: Sanity Checks (MUST PASS BEFORE MOVING ON)
    checks_cmd = [PYTHON_EXE, "src/checks.py", "--region", region_id]
    if not run_command(checks_cmd, f"Run sanity verification suite for {region_id}"):
        print(f"\n[HALT] Sanity checks failed for {region_id}. Stopping pipeline.", file=sys.stderr)
        return False

    # Step 4: Visualizations
    plot_cmd = [PYTHON_EXE, "src/plot.py", "--region", region_id]
    if not run_command(plot_cmd, f"Generate slide 2 visualization for {region_id}"):
        return False

    print(f"\n[SUCCESS] Pipeline successfully completed for region: {region_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Master runner for NASA FIRMS pipeline.")
    parser.add_argument("--region", choices=REGIONS_ORDER + ["all"], default="all",
                        help="Target region or 'all'")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip downloading and run ingest, sanity checks, and plots on existing data")
    parser.add_argument("--workers", type=int, default=4,
                        help="Worker threads for downloader (default: 4)")

    args = parser.parse_args()

    targets = REGIONS_ORDER if (args.region == "all") else [args.region]

    for reg in targets:
        success = run_pipeline_for_region(reg, args.skip_download, args.workers)
        if not success:
            print(f"\n[HALT] Execution stopped because region '{reg}' failed.", file=sys.stderr)
            sys.exit(1)

    print("\n=======================================================")
    print("ALL REQUESTED REGIONS COMPLETED SUCCESSFULLY.")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
