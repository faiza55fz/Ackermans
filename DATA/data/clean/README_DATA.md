# Cleaned NASA FIRMS Fire Detections Dataset

## Overview & Multi-Satellite Note
This repository contains standardized, quality-filtered active fire datasets downloaded from NASA FIRMS across multiple regions.

> [!NOTE]
> **Important Note on VIIRS Multi-Satellite Detections:**
> Aggregate VIIRS detection counts naturally rise across time as additional satellites entered orbit:
> - **S-NPP (Satellite `N`):** Operational from 2012-01-20 to 2026-11-02.
> - **NOAA-20 (Satellite `N20`):** Added on 2018-04-01, roughly doubling overpass frequency.
> - **NOAA-21 (Satellite `N21`):** Added on 2023-03-01, further increasing daily sampling.
> For consistent longitudinal analysis across years, detection counts should be compared **per satellite** rather than purely on the raw aggregate VIIRS stream.

---

## Standard 23-Column Schema

Every cleaned dataset conforms to the exact 23-column standardized schema:
1. `region` — Region identifier (e.g., `palisades_la`, `western_ghats_karnataka`, `punjab_haryana`).
2. `sensor` — Sensor stream name (`MODIS` or `VIIRS`).
3. `satellite` — Specific satellite identifier (`Terra`, `Aqua`, `N` for S-NPP, `N20` for NOAA-20, `N21` for NOAA-21).
4. `processing` — Processing pipeline (`SP` for Standard Science Processing; `NRT` for Near Real-Time).
5. `datetime_utc` — Combined ISO UTC timestamp (`YYYY-MM-DD HH:MM:SS`).
6. `date` — Calendar acquisition date (`YYYY-MM-DD`).
7. `year` — Calendar acquisition year (`YYYY`).
8. `latitude` — Decimal latitude (WGS84).
9. `longitude` — Decimal longitude (WGS84).
10. `confidence` — Detection confidence (stored as text/string in combined datasets to accommodate MODIS 0–100 numeric and VIIRS categorical `n`/`h`).
11. `confidence_class` — Standardized classification (`nominal` or `high`; low-confidence rows dropped to separate files).
12. `frp` — Fire Radiative Power in megawatts (MW).
13. `daynight` — Overpass time indicator (`D` = daytime, `N` = nighttime).
14. `scan` — Spatial scan pixel size (km).
15. `track` — Spatial track pixel size (km).
16. `instrument` — Instrument name (`MODIS` or `VIIRS`).
17. `version` — Collection / algorithm version.
18. `brightness` — Brightness temperature (MODIS only, Kelvin; empty for VIIRS).
19. `bright_t31` — Channel 31 brightness temperature (MODIS only, Kelvin; empty for VIIRS).
20. `bright_ti4` — I-4 channel brightness temperature (VIIRS only, Kelvin; empty for MODIS).
21. `bright_ti5` — I-5 channel brightness temperature (VIIRS only, Kelvin; empty for MODIS).
22. `type` — FIRMS detection type flag (`0` = presumed vegetation fire, `1` = active volcano, `2` = other static land source, `3` = offshore).
23. `is_vegetation_fire` — Boolean flag (`True` if `type == 0` or missing; `False` if static/industrial/volcano).

---

## Region 1: Pacific Palisades, Los Angeles (`palisades_la`)
- **Bounding Box:** `[-118.75, 33.95, -118.40, 34.20]`
- **Total Clean Rows:** **6,083** (MODIS: 577, VIIRS: 5,506)
- **First & Last Detection Dates:**
  - **MODIS Overall:** 2005-09-29 to 2026-09-09
    - Satellite `Terra`: 2005-09-29 to 2026-09-09 (213 rows)
    - Satellite `Aqua`: 2006-07-24 to 2025-01-08 (364 rows)
  - **VIIRS Overall:** 2012-05-10 to 2026-11-09
    - Satellite `N` (S-NPP): 2012-05-10 to 2026-11-01 (2,683 rows)
    - Satellite `N20` (NOAA-20): 2018-04-01 to 2026-11-09 (1,745 rows)
    - Satellite `N21` (NOAA-21): 2023-03-01 to 2026-11-09 (1,078 rows)
- **SP vs NRT Breakdown:**
  - MODIS: 576 SP rows, 1 NRT row (SP max: 2026-05-29, NRT min: 2026-09-09)
  - VIIRS: 5,501 SP rows, 5 NRT rows (SP max: 2026-07-26, NRT min: 2026-11-08)
- **File Sizes on Disk:**
  - `palisades_la_MODIS.parquet`: 0.03 MB | CSV: 0.10 MB
  - `palisades_la_VIIRS.parquet`: 0.15 MB | CSV: 0.81 MB
  - `palisades_la_combined.parquet`: 0.17 MB | CSV: 0.90 MB

---

## Region 2: Western Ghats, Karnataka (`western_ghats_karnataka`)
- **Bounding Box:** `[74.0, 13.3, 76.1, 15.8]`
- **Total Clean Rows:** **133,605** (MODIS: 18,131, VIIRS: 115,474)
- **First & Last Detection Dates:**
  - **MODIS Overall:** 2000-11-11 to 2026-11-11
    - Satellite `Terra`: 2000-11-11 to 2026-11-04 (6,713 rows)
    - Satellite `Aqua`: 2002-10-18 to 2026-11-11 (11,418 rows)
  - **VIIRS Overall:** 2012-01-20 to 2026-11-14
    - Satellite `N` (S-NPP): 2012-01-20 to 2026-11-01 (70,196 rows)
    - Satellite `N20` (NOAA-20): 2018-04-01 to 2026-11-14 (31,670 rows)
    - Satellite `N21` (NOAA-21): 2023-03-01 to 2026-11-14 (13,608 rows)
- **SP vs NRT Breakdown:**
  - MODIS: 18,107 SP rows, 24 NRT rows (SP max: 2026-05-29, NRT min: 2026-09-07)
  - VIIRS: 115,059 SP rows, 415 NRT rows (SP max: 2026-07-26, NRT min: 2026-08-10)
- **File Sizes on Disk:**
  - `western_ghats_karnataka_MODIS.parquet`: 0.40 MB | CSV: 2.84 MB
  - `western_ghats_karnataka_VIIRS.parquet`: 2.78 MB | CSV: 18.02 MB
  - `western_ghats_karnataka_combined.parquet`: 3.13 MB | CSV: 20.86 MB

---

## Region 3: Punjab & Haryana (`punjab_haryana`)
- **Bounding Box:** `[73.8, 27.6, 77.7, 32.6]`
- **Total Clean Rows:** **2,732,329** (MODIS: 503,483, VIIRS: 2,228,846)
- **First & Last Detection Dates:**
  - **MODIS Overall:** 2000-11-01 to 2026-11-13
    - Satellite `Terra`: 2000-11-01 to 2026-11-10 (119,690 rows)
    - Satellite `Aqua`: 2002-07-13 to 2026-11-13 (383,793 rows)
  - **VIIRS Overall:** 2012-01-20 to 2026-11-14
    - Satellite `N` (S-NPP): 2012-01-20 to 2026-11-02 (1,339,842 rows)
    - Satellite `N20` (NOAA-20): 2018-04-01 to 2026-11-14 (703,843 rows)
    - Satellite `N21` (NOAA-21): 2023-03-01 to 2026-11-14 (185,161 rows)
- **SP vs NRT Breakdown:**
  - MODIS: 497,520 SP rows, 5,963 NRT rows (SP max: 2026-08-30, NRT min: 2026-09-03)
  - VIIRS: 2,209,165 SP rows, 19,681 NRT rows (SP max: 2026-07-31, NRT min: 2026-08-04)
- **File Sizes on Disk:**
  - `punjab_haryana_MODIS.parquet`: 5.48 MB | CSV: 70.79 MB
  - `punjab_haryana_VIIRS.parquet`: 47.53 MB | CSV: 312.70 MB
  - `punjab_haryana_combined.parquet`: 53.00 MB | CSV: 383.49 MB
  *(Note: Due to repository limits, punjab_haryana files are tracked externally; see `LARGE_FILES.md`)*.

---

## Formats & Storage
All datasets are stored in both Apache Parquet (`.parquet`) and CSV (`.csv`) formats. Exact row-count parity is verified across all formats.
