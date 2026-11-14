# Cleaned Fire Detections (Palisades Full-Year Dataset)

## Overview
- **Status:** Full-year `palisades_la` cleaned active fire dataset, containing **6,083 rows** (577 MODIS, 5,506 VIIRS).
- **Temporal Range:**
  - **MODIS:** 2005-09-29 to 2026-09-09
  - **VIIRS:** 2012-05-10 to 2026-11-09
  - **Processing streams:** Standard Processing (`SP`) plus 6 Near Real-Time (`NRT`) rows (1 MODIS, 5 VIIRS).
- **Completeness:** Zero-detection years reflect no fires detected within the bounding box (`[-118.75, 33.95, -118.40, 34.20]`), not missing data. All 5-day windows from stream launches through November 2026 were fully downloaded. VIIRS rows prior to 2012-05 do not exist because no fires were detected in the box.
- **Regions:** Only `palisades_la` is included so far. The other regions will be added later.

## Schema (23 Columns)
1. `region`
2. `sensor`
3. `satellite`
4. `processing`
5. `datetime_utc`
6. `date`
7. `year`
8. `latitude`
9. `longitude`
10. `confidence` (stored as text/string in the combined file to accommodate numeric MODIS 0–100 and categorical VIIRS `l`/`n`/`h`)
11. `confidence_class` (`nominal`, `high`; low-confidence rows dropped to separate files)
12. `frp`
13. `daynight`
14. `scan`
15. `track`
16. `instrument`
17. `version`
18. `brightness` (MODIS only; empty for VIIRS)
19. `bright_t31` (MODIS only; empty for VIIRS)
20. `bright_ti4` (VIIRS only; empty for MODIS)
21. `bright_ti5` (VIIRS only; empty for MODIS)
22. `type`
23. `is_vegetation_fire` (Boolean: `True` when `type == 0` or missing, `False` otherwise)

## Formats
Both Apache Parquet (`.parquet`) and CSV (`.csv`) formats are provided in `data/clean/` and `data/clean/csv/` with exact row parity.
