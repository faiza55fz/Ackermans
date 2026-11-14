# Punjab & Haryana Fire Dataset (Split Binary Parts)

Due to file size constraints on GitHub (files exceeding 50 MB), the cleaned datasets for `punjab_haryana` have been compressed and split into binary parts ($\le 45$ MB each).

## Contents
- `punjab_data.part01` — Binary part 1 (45.00 MB)
- `punjab_data.part02` — Binary part 2 (45.00 MB)
- `punjab_data.part03` — Binary part 3 (35.25 MB)
- `rejoin_punjab.py` — Python extraction and verification script
- `checksums.txt` — Authoritative SHA-256 and row count checksums

## How to Reassemble the Clean Data
From the `DATA/` directory, run:
```bash
python data/punjab_parts/rejoin_punjab.py
```

This will automatically:
1. Concatenate `punjab_data.part*` into an archive in memory/temp.
2. Extract the cleaned files directly into `data/clean/` and `data/clean/csv/`:
   - `data/clean/punjab_haryana_combined.parquet`
   - `data/clean/csv/punjab_haryana_combined.csv`
   - `data/clean/punjab_haryana_MODIS.parquet`
   - `data/clean/punjab_haryana_VIIRS.parquet`
3. Verify every file's exact SHA-256 hash and total row count (2,732,329 rows for combined).
