"""
FireTrace Pilot Pipeline - Data Inspection Tool
Schema-independent inspection for CSV and Parquet active fire datasets.
Checks row-width consistency, duplicate headers, null frequencies, and metadata
without loading entire Parquet tables into memory or assuming fixed schemas.
Parquet inspection remains strictly optional without requiring pip dependencies.
"""

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional


def inspect_csv(file_path: Path, sample_size: int = 5) -> Dict[str, Any]:
    """
    Inspects a CSV file schema-independently:
    - Detects empty files (0 bytes or header only)
    - Detects duplicate header columns
    - Detects row-width inconsistencies with line numbers
    - Calculates null frequencies
    - Samples preview records
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sample_size = max(1, sample_size)
    file_size = file_path.stat().st_size

    if file_size == 0:
        return {
            "file": str(file_path),
            "file_name": file_path.name,
            "format": "csv",
            "file_size_bytes": 0,
            "is_empty": True,
            "total_records": 0,
            "columns": [],
            "issues": ["File is 0 bytes (empty)"],
        }

    with file_path.open("r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)

        if not header:
            return {
                "file": str(file_path),
                "file_name": file_path.name,
                "format": "csv",
                "file_size_bytes": file_size,
                "is_empty": True,
                "total_records": 0,
                "columns": [],
                "issues": ["File contains no header row"],
            }

        columns = [col.strip() for col in header]
        expected_width = len(columns)

        # Check for duplicate headers
        seen_headers = set()
        duplicate_headers = []
        for col in columns:
            if col in seen_headers:
                duplicate_headers.append(col)
            seen_headers.add(col)

        sample_rows: List[Dict[str, str]] = []
        total_records = 0
        null_counts = {col: 0 for col in columns}
        row_width_mismatches: List[Dict[str, Any]] = []

        for line_num, row in enumerate(reader, start=2):
            # Skip empty lines
            if not row or all(c.strip() == "" for c in row):
                continue

            total_records += 1

            if len(row) != expected_width:
                if len(row_width_mismatches) < 10:
                    row_width_mismatches.append({
                        "line_number": line_num,
                        "expected_fields": expected_width,
                        "actual_fields": len(row),
                    })
                continue

            row_dict = {}
            for col_idx, col_name in enumerate(columns):
                val = row[col_idx]
                val_clean = val.strip()
                if val_clean == "" or val_clean.lower() in ("null", "none", "nan", "na"):
                    null_counts[col_name] += 1
                row_dict[col_name] = val_clean

            if len(sample_rows) < sample_size:
                sample_rows.append(row_dict)

    # Basic data type inference from sample
    inferred_types: Dict[str, str] = {}
    for col in columns:
        sample_vals = [s[col] for s in sample_rows if col in s and s[col]]
        if not sample_vals:
            inferred_types[col] = "all_null_or_empty"
        elif all(v.replace("-", "", 1).isdigit() for v in sample_vals):
            inferred_types[col] = "integer"
        elif all(
            v.replace("-", "", 1).replace(".", "", 1).isdigit() and "." in v for v in sample_vals
        ):
            inferred_types[col] = "float"
        else:
            inferred_types[col] = "string"

    issues: List[str] = []
    if duplicate_headers:
        issues.append(f"Duplicate column headers found: {duplicate_headers}")
    if row_width_mismatches:
        issues.append(f"{len(row_width_mismatches)} row-width mismatches detected (first mismatch at line {row_width_mismatches[0]['line_number']})")
    if total_records == 0:
        issues.append("File contains header but zero data records")

    return {
        "file": str(file_path),
        "file_name": file_path.name,
        "format": "csv",
        "file_size_bytes": file_size,
        "is_empty": (total_records == 0),
        "total_records": total_records,
        "column_count": len(columns),
        "columns": columns,
        "duplicate_headers": duplicate_headers,
        "row_width_mismatches": row_width_mismatches,
        "inferred_types": inferred_types,
        "null_counts": null_counts,
        "sample_rows": sample_rows,
        "issues": issues,
    }


def inspect_parquet(file_path: Path, sample_size: int = 5) -> Dict[str, Any]:
    """
    Inspects a Parquet file schema and record count using METADATA ONLY.
    Uses memory-efficient batch iterator to read ONLY the small sample slice.
    Avoids loading full row groups into memory.
    Keeps pyarrow dependency optional.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sample_size = max(1, sample_size)
    file_size = file_path.stat().st_size

    try:
        import pyarrow.parquet as pq

        # Open ParquetFile reader (reads metadata only, zero data rows loaded into RAM)
        p_file = pq.ParquetFile(file_path)
        metadata = p_file.metadata
        total_records = metadata.num_rows
        schema = p_file.schema_arrow
        columns = schema.names
        types = {name: str(schema.field(name).type) for name in columns}

        # Memory-efficient sample batch reading without loading entire row groups
        sample_rows: List[Dict[str, Any]] = []
        if total_records > 0:
            try:
                batch_iter = p_file.iter_batches(batch_size=sample_size)
                first_batch = next(batch_iter, None)
                if first_batch is not None:
                    sample_rows = first_batch.slice(0, sample_size).to_pylist()
            except Exception:
                # Safe fallback if batch iterator is unsupported on specific Arrow build
                if metadata.num_row_groups > 0:
                    first_group = p_file.read_row_group(0)
                    sample_rows = first_group.slice(0, min(sample_size, first_group.num_rows)).to_pylist()

        return {
            "file": str(file_path),
            "file_name": file_path.name,
            "format": "parquet",
            "file_size_bytes": file_size,
            "total_records": total_records,
            "row_groups_count": metadata.num_row_groups,
            "column_count": len(columns),
            "columns": columns,
            "schema_types": types,
            "sample_rows": sample_rows,
            "issues": [],
        }
    except ImportError:
        return {
            "file": str(file_path),
            "file_name": file_path.name,
            "format": "parquet",
            "file_size_bytes": file_size,
            "note": "pyarrow is not installed. Parquet inspection requires pyarrow installed in the environment.",
            "issues": ["Parquet inspection skipped: pyarrow library unavailable"],
        }
    except Exception as e:
        return {
            "file": str(file_path),
            "file_name": file_path.name,
            "format": "parquet",
            "file_size_bytes": file_size,
            "issues": [f"Error reading Parquet metadata: {str(e)}"],
        }


def print_inspection_summary(info: Dict[str, Any]) -> None:
    """Prints a structured summary of inspected dataset."""
    print("=" * 70)
    print(f"Dataset Inspection: {info.get('file_name', info.get('file'))}")
    print("=" * 70)
    print(f"Format:          {info.get('format', 'unknown').upper()}")
    print(f"File Size:       {info.get('file_size_bytes', 0):,} bytes")
    print(f"Total Records:   {info.get('total_records', 'N/A'):,}")
    print(f"Column Count:    {info.get('column_count', 0)}")

    issues = info.get("issues", [])
    if issues:
        print("\nWarnings / Anomalies Detected:")
        for iss in issues:
            print(f"  [!] {iss}")

    columns = info.get("columns", [])
    types = info.get("inferred_types", info.get("schema_types", {}))
    nulls = info.get("null_counts", {})

    print(f"\nColumn Inventory:")
    for col in columns:
        type_str = types.get(col, "unknown")
        null_str = f" | Nulls: {nulls.get(col, 0):,}" if col in nulls else ""
        print(f"  - {col:<26} [{type_str}]{null_str}")

    sample = info.get("sample_rows", [])
    print(f"\nSample Preview (Record 1 of {len(sample)} sampled):")
    if sample:
        for k, v in sample[0].items():
            print(f"    {k:<24}: {v}")
    else:
        print("    (No records available to sample)")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Schema-independent inspection for CSV and Parquet fire datasets")
    parser.add_argument("path", help="Path to CSV or Parquet file, or directory")
    parser.add_argument("--sample", type=int, default=5, help="Number of sample rows to preview")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        files = list(target.glob("*.csv")) + list(target.glob("*.parquet"))
        if not files:
            print(f"No CSV or Parquet files found in {target}")
            return
        for f in sorted(files):
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
