"""
FireTrace Pilot Pipeline - Data Inspection Tool
Inspects CSV and Parquet datasets for schema, column names, data types, nulls, and record counts.
"""

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional


def inspect_csv(file_path: Path, sample_size: int = 5) -> Dict[str, Any]:
    """
    Inspects a CSV file to determine column names, record counts, and sample values.
    Uses standard library to inspect structure without assuming schema upfront.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with file_path.open("r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return {
                "file": str(file_path),
                "format": "csv",
                "total_records": 0,
                "columns": [],
                "error": "Empty file or no header found",
            }

        columns = [col.strip() for col in header]
        sample_rows: List[Dict[str, str]] = []
        total_records = 0
        null_counts = {col: 0 for col in columns}

        for row in reader:
            if not row or all(field.strip() == "" for field in row):
                continue
            total_records += 1

            row_dict = {}
            for col_idx, col_name in enumerate(columns):
                val = row[col_idx] if col_idx < len(row) else ""
                val_clean = val.strip()
                if val_clean == "" or val_clean.lower() in ("null", "none", "nan", "na"):
                    null_counts[col_name] += 1
                row_dict[col_name] = val_clean

            if len(sample_rows) < sample_size:
                sample_rows.append(row_dict)

    # Infer basic data types from sample
    inferred_types: Dict[str, str] = {}
    for col in columns:
        sample_vals = [s[col] for s in sample_rows if s.get(col)]
        if not sample_vals:
            inferred_types[col] = "unknown / all_null"
        elif all(v.replace("-", "", 1).isdigit() for v in sample_vals):
            inferred_types[col] = "integer"
        elif all(
            v.replace("-", "", 1).replace(".", "", 1).isdigit() and "." in v for v in sample_vals
        ):
            inferred_types[col] = "float"
        else:
            inferred_types[col] = "string"

    return {
        "file": str(file_path),
        "file_name": file_path.name,
        "format": "csv",
        "file_size_bytes": file_path.stat().st_size,
        "total_records": total_records,
        "column_count": len(columns),
        "columns": columns,
        "inferred_types": inferred_types,
        "null_counts": null_counts,
        "sample_rows": sample_rows,
    }


def inspect_parquet(file_path: Path, sample_size: int = 5) -> Dict[str, Any]:
    """
    Inspects a Parquet file schema and record count.
    Attempts PyArrow or Polars if installed; provides graceful message if missing.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        import pyarrow.parquet as pq

        table = pq.read_table(file_path)
        schema = table.schema
        columns = schema.names
        types = {name: str(schema.field(name).type) for name in columns}
        total_records = table.num_rows

        sample_rows = (
            table.slice(0, min(sample_size, total_records)).to_pylist() if total_records > 0 else []
        )

        return {
            "file": str(file_path),
            "file_name": file_path.name,
            "format": "parquet",
            "file_size_bytes": file_path.stat().st_size,
            "total_records": total_records,
            "column_count": len(columns),
            "columns": columns,
            "schema_types": types,
            "sample_rows": sample_rows,
        }
    except ImportError:
        return {
            "file": str(file_path),
            "format": "parquet",
            "file_size_bytes": file_path.stat().st_size,
            "note": "pyarrow is not yet installed. Install pyarrow or polars to inspect Parquet metadata directly.",
        }


def print_inspection_summary(info: Dict[str, Any]) -> None:
    """Prints a structured summary of inspected dataset."""
    print("=" * 70)
    print(f"Dataset Inspection: {info.get('file_name', info.get('file'))}")
    print("=" * 70)
    print(f"Format:        {info.get('format', 'unknown').upper()}")
    print(f"Size:          {info.get('file_size_bytes', 0):,} bytes")
    print(f"Total Records: {info.get('total_records', 'N/A'):,}")
    print(f"Columns ({info.get('column_count', 0)}):")

    columns = info.get("columns", [])
    types = info.get("inferred_types", info.get("schema_types", {}))
    nulls = info.get("null_counts", {})

    for col in columns:
        type_str = types.get(col, "unknown")
        null_str = f" | Nulls: {nulls.get(col, 0)}" if col in nulls else ""
        print(f"  - {col:<24} [{type_str}]{null_str}")

    print("\nSample Preview (First record):")
    sample = info.get("sample_rows", [])
    if sample:
        for k, v in sample[0].items():
            print(f"    {k:<20}: {v}")
    else:
        print("    (No records to display)")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect CSV/Parquet dataset schema and counts")
    parser.add_argument("path", help="Path to CSV or Parquet file, or directory")
    parser.add_argument("--sample", type=int, default=5, help="Number of sample rows to preview")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        files = list(target.glob("*.csv")) + list(target.glob("*.parquet"))
        if not files:
            print(f"No CSV or Parquet files found in {target}")
            return
        for f in files:
            info = inspect_parquet(f, args.sample) if f.suffix == ".parquet" else inspect_csv(f, args.sample)
            print_inspection_summary(info)
    elif target.suffix.lower() == ".parquet":
        info = inspect_parquet(target, args.sample)
        print_inspection_summary(info)
    else:
        info = inspect_csv(target, args.sample)
        print_inspection_summary(info)


if __name__ == "__main__":
    main()
