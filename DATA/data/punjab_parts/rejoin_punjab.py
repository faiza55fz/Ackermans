#!/usr/bin/env python3
"""
rejoin_punjab.py - Reassemble split binary parts into the clean datasets.

Reads binary parts (punjab_data.part*), reconstructs the ZIP archive,
extracts cleaned Parquet and CSV files into DATA/data/clean/, and verifies
exact SHA-256 checksums and row counts against checksums.txt.
"""

import sys
import hashlib
import zipfile
import argparse
from pathlib import Path
import pandas as pd

PARTS_DIR = Path(__file__).resolve().parent
DEFAULT_DEST_DIR = PARTS_DIR.parent / "clean"
CHECKSUMS_FILE = PARTS_DIR / "checksums.txt"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536 * 16):
            h.update(chunk)
    return h.hexdigest()


def count_rows(filepath: Path) -> int:
    if filepath.suffix == ".parquet":
        return len(pd.read_parquet(filepath))
    elif filepath.suffix == ".csv":
        with open(filepath, "rb") as f:
            return sum(1 for _ in f) - 1
    return 0


def rejoin_and_verify(dest_dir: Path = DEFAULT_DEST_DIR, keep_zip: bool = False) -> bool:
    print(f"================================================================")
    print(f"REASSEMBLING PUNJAB & HARYANA DATASETS")
    print(f"Destination: {dest_dir}")
    print(f"================================================================")

    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "csv").mkdir(parents=True, exist_ok=True)

    # 1. Discover and sort binary parts
    parts = sorted(list(PARTS_DIR.glob("punjab_data.part*")))
    if not parts:
        print("ERROR: No binary parts (punjab_data.part*) found in", PARTS_DIR)
        return False

    print(f"Found {len(parts)} binary part(s):")
    for p in parts:
        print(f"  {p.name} ({p.stat().st_size:,} bytes)")

    # 2. Reassemble into punjab_data.zip
    reassembled_zip = dest_dir / "punjab_data.zip"
    print(f"\nReassembling binary stream into {reassembled_zip.name}...")
    with open(reassembled_zip, "wb") as f_out:
        for p in parts:
            with open(p, "rb") as f_in:
                while chunk := f_in.read(65536 * 16):
                    f_out.write(chunk)

    print(f"Reassembled ZIP size: {reassembled_zip.stat().st_size:,} bytes")

    # 3. Extract contents
    print(f"\nExtracting datasets into {dest_dir}...")
    with zipfile.ZipFile(reassembled_zip, "r") as zf:
        zf.extractall(dest_dir)
        extracted_files = zf.namelist()

    print(f"Extracted {len(extracted_files)} files:")
    for name in extracted_files:
        extracted_path = dest_dir / name
        print(f"  - {name} ({extracted_path.stat().st_size:,} bytes)")

    # Clean up temporary reassembled zip unless instructed to keep
    if not keep_zip and reassembled_zip.exists():
        reassembled_zip.unlink()

    # 4. Verify against checksums.txt
    print(f"\nVerifying checksums and row counts from {CHECKSUMS_FILE.name}...")
    if not CHECKSUMS_FILE.exists():
        print(f"ERROR: Checksums file not found: {CHECKSUMS_FILE}")
        return False

    all_passed = True
    with open(CHECKSUMS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts_info = line.split(",")
            if len(parts_info) != 3:
                continue
            rel_path, expected_sha, expected_rows = parts_info[0].strip(), parts_info[1].strip(), int(parts_info[2].strip())
            target_file = dest_dir / rel_path

            if not target_file.exists():
                print(f"[FAIL] Missing file: {rel_path}")
                all_passed = False
                continue

            actual_sha = compute_sha256(target_file)
            actual_rows = count_rows(target_file)

            sha_match = (actual_sha.lower() == expected_sha.lower())
            rows_match = (actual_rows == expected_rows)

            status = "PASS" if (sha_match and rows_match) else "FAIL"
            if status == "FAIL":
                all_passed = False

            print(f"[{status}] {rel_path}:")
            print(f"  Rows:    {actual_rows:,} (Expected: {expected_rows:,}) - {'OK' if rows_match else 'MISMATCH'}")
            print(f"  SHA-256: {actual_sha} - {'OK' if sha_match else 'MISMATCH'}")

    print("\n" + "=" * 64)
    if all_passed:
        print("ALL VERIFICATIONS PASSED: Datasets reassembled with 100% integrity.")
    else:
        print("VERIFICATION FAILED: One or more files do not match expected integrity.")
    print("=" * 64)

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Reassemble and verify Punjab & Haryana active fire datasets.")
    parser.add_argument("--dest-dir", type=Path, default=DEFAULT_DEST_DIR, help="Destination directory (default: DATA/data/clean)")
    parser.add_argument("--keep-zip", action="store_true", help="Keep intermediate punjab_data.zip")
    args = parser.parse_args()

    success = rejoin_and_verify(dest_dir=args.dest_dir, keep_zip=args.keep_zip)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
