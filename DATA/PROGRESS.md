# FIRMS Fire Data Pipeline Progress

## Setup & Environment
- [x] Create project structure inside `DATA/` (`src/`, `data/raw/`, `data/clean/`, `notebooks/`, `reports/`, `logs/`)
- [x] Create `requirements.txt` and Python virtual environment (`.venv`)
- [x] Review FIRMS API documentation (endpoints, source names, day range limits, rate limits, coordinate ordering)
- [x] Verify `FIRMS_MAP_KEY` environment variable

## Phase 0: Download
- [x] 0.1 Test the API with a small test call for `palisades_la` (Jan 2025) for each sensor
  - `MODIS_SP`: 307 rows (Satellites: Aqua, Terra)
  - `VIIRS_SNPP_SP`: 1,104 rows (Satellite: N)
  - `VIIRS_NOAA20_SP`: 1,112 rows (Satellite: N20)
  - `VIIRS_NOAA21_SP`: 1,590 rows (Satellite: N21)
- [x] 0.2 Implement `src/download.py`
  - [x] Loop by region, sensor, and date window (max 5 days per call)
  - [x] Rate limit compliance, backoff retries, clean stop on transaction limits
  - [x] Resumable logic (skip existing downloaded windows)
  - [x] Raw files saved to `data/raw/<region>/<sensor>/` by year
  - [x] Log failed windows to `logs/download_failures.csv` (never logging the MAP_KEY)
  - [x] CLI argument parsing for region and sensor, including `--all`
  - [x] Summary table output (region, sensor, files, rows, min date, max date)
- [x] 0.3 Run test region (`palisades_la`) across all sensors over full date ranges
  - MODIS: 27 files, 595 raw rows -> 577 clean rows (2005-09-29 to 2026-09-09)
  - VIIRS: 15 files, 5,744 raw rows -> 5,506 clean rows (2012-05-10 to 2026-11-09)

## Phase 1: Get and Clean Data
- [x] 1.1 Inspect raw files for `palisades_la` (file sizes, row counts)
- [x] 1.2 Exploratory analysis in `notebooks/01_inspect.ipynb`
  - [x] Compare MODIS vs VIIRS schemas, dtypes, unique values
  - [x] Document differences (e.g., numeric confidence vs categorical)
- [x] 1.3 Implement `src/ingest.py`
  - [x] Read and concatenate raw CSVs
  - [x] Standardize columns, add `sensor` ("MODIS" / "VIIRS"), preserve `satellite`
  - [x] Implement confidence filtering (MODIS >= 30, VIIRS drop 'l')
  - [x] Export dropped low-confidence detections to `data/clean/dropped_low_confidence_<region>_<sensor>.csv`
  - [x] Parse `datetime_utc`, `date`, `year`
  - [x] Deduplicate exact rows
  - [x] Select final 23-column schema (including scan, track, instrument, version, brightness, bright_t31, bright_ti4, bright_ti5, type, is_vegetation_fire)
  - [x] Save clean Parquet in `data/clean/` and clean CSV in `data/clean/csv/`
- [x] 1.4 Generate Hotspots per Year plot (`reports/slide2_hotspots_per_year_by_sensor_palisades_la.png`)
  - [x] Annotation for 2012 VIIRS introduction explaining resolution differences
- [x] 1.6 Sanity checks for `palisades_la` (`src/checks.py` -> `reports/sanity_palisades_la.md`) - ALL 7 CHECKS PASSED
- [ ] 1.5 Repeat pipeline for remaining regions (`western_ghats_karnataka`, `punjab_haryana`, `nsw_victoria_au`)
  - [x] Implement master orchestration script `run_all.py`
  - [x] Complete download, ingest, sanity checks, and plots for `western_ghats_karnataka` (133,605 clean rows; all 7 checks passed)
  - [x] Complete download, ingest, sanity checks, and plots for `punjab_haryana` (2,732,329 clean rows; all 7 checks passed)
  - [ ] Complete download, ingest, sanity checks, and plots for `nsw_victoria_au`
