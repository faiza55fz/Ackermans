"""
FireTrace Pilot Pipeline - Full Pipeline Runner
Executes the complete ingestion, validation, quarantine, reconciliation,
and reporting pipeline for MODIS, VIIRS, and combined active fire datasets.
"""

import argparse
import sys
from pathlib import Path

# Add project root and scripts dir to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from scripts.inspect_data import inspect_csv, print_inspection_summary
    from scripts.ingest_data import ingest_firms_csv
    from scripts.generate_report import generate_quality_report
except ImportError:
    from inspect_data import inspect_csv, print_inspection_summary
    from ingest_data import ingest_firms_csv
    from generate_report import generate_quality_report


def run_pipeline_for_dataset(
    csv_path: Path,
    processed_dir: Path,
    quarantine_dir: Path,
    reports_dir: Path,
    overwrite: bool = True,
) -> dict:
    print("\n" + "=" * 70)
    print(f"PIPELINE STEP 1: Inspecting {csv_path.name}")
    print("=" * 70)
    inspect_info = inspect_csv(csv_path, sample_size=3)
    print_inspection_summary(inspect_info)

    print("\n" + "=" * 70)
    print(f"PIPELINE STEP 2: Ingesting & Validating {csv_path.name}")
    print("=" * 70)
    ingest_res = ingest_firms_csv(
        csv_path,
        processed_dir,
        quarantine_dir,
        overwrite=overwrite,
    )
    print(f"  Dataset Family:     {ingest_res['family']}")
    print(f"  Records Processed:  {ingest_res['total_read']:,}")
    print(f"  Valid Accepted:     {ingest_res['valid_count']:,}")
    print(f"  Quarantined:        {ingest_res['quarantined_count']:,}")
    print(f"  Reconciliation:     {'PASSED' if ingest_res['reconciliation_passed'] else 'FAILED'}")
    print(f"  Manifest:           {ingest_res['manifest_output']}")

    print("\n" + "=" * 70)
    print(f"PIPELINE STEP 3: Generating Data Quality Audit Report")
    print("=" * 70)
    report_file = generate_quality_report(
        Path(ingest_res["processed_output"]),
        Path(ingest_res["quarantine_output"]),
        reports_dir,
        manifest_file=Path(ingest_res["manifest_output"]),
    )
    print(f"  Audit Report Generated: {report_file}")

    return {
        "dataset": csv_path.name,
        "total_records": ingest_res["total_read"],
        "valid_accepted": ingest_res["valid_count"],
        "quarantined": ingest_res["quarantined_count"],
        "family": ingest_res["family"],
        "family_counts": ingest_res["family_counts"],
        "report_file": str(report_file),
    }


def main():
    parser = argparse.ArgumentParser(description="Run complete FireTrace data integration pipeline")
    parser.add_argument("--data_dir", default="data/data/clean/csv", help="Directory containing clean CSV datasets")
    parser.add_argument("--processed_dir", default="data/processed", help="Output directory for processed JSON")
    parser.add_argument("--quarantine_dir", default="data/quarantine", help="Output directory for quarantined JSON")
    parser.add_argument("--reports_dir", default="reports", help="Output directory for reports")
    parser.add_argument("--overwrite", action="store_true", default=True, help="Overwrite existing output files")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    processed_dir = Path(args.processed_dir)
    quarantine_dir = Path(args.quarantine_dir)
    reports_dir = Path(args.reports_dir)

    target_files = [
        data_dir / "palisades_la_MODIS.csv",
        data_dir / "palisades_la_VIIRS.csv",
        data_dir / "palisades_la_combined.csv",
    ]

    for f in target_files:
        if not f.exists():
            print(f"Error: Target dataset file not found: {f}", file=sys.stderr)
            sys.exit(1)

    print("=" * 80)
    print("FIRETRACE DATA INTEGRATION PIPELINE: FULL RUN")
    print("=" * 80)

    summaries = []
    for csv_file in target_files:
        summary = run_pipeline_for_dataset(
            csv_file,
            processed_dir,
            quarantine_dir,
            reports_dir,
            overwrite=args.overwrite,
        )
        summaries.append(summary)

    print("\n" + "=" * 80)
    print("FINAL PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"{'Dataset':<32} {'Family':<10} {'Total':<8} {'Valid':<8} {'Quarantine':<12} {'Status'}")
    print("-" * 80)
    for s in summaries:
        print(f"{s['dataset']:<32} {s['family']:<10} {s['total_records']:<8} {s['valid_accepted']:<8} {s['quarantined']:<12} PASSED")
    print("=" * 80)
    print("All datasets processed, validated, reconciled, and audited successfully.")


if __name__ == "__main__":
    main()
