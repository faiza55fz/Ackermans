# Sanity Check Report: palisades_la
**Region Name:** Pacific Palisades, Los Angeles, USA  
**Bounding Box:** west=-118.75, south=33.95, east=-118.4, north=34.2  
**Execution Date:** 2026-11-14  
**Overall Status:** **PASS**

## Summary of Checks
| Check | Status | Details |
|---|:---:|---|
| 1. Null Dates or Datetimes | **PASS** | Null dates: 0, Null datetimes: 0 (Expected: 0) |
| 2. Bounding Box Coordinates | **PASS** | Outside bbox count: 0 (BBox: west=-118.75, south=33.95, east=-118.4, north=34.2) |
| 3. Null Essential Fields | **PASS** | Null lat: 0, lon: 0, frp: 0, confidence: 0 (Expected: all 0) |
| 4. Non-negative Fire Radiative Power (FRP) | **PASS** | Negative FRP count: 0 (Expected: 0). FRP Min: 0.00, Median: 12.73, Max: 4563.40 |
| 5. Sensor Operational Date Ranges | **PASS** | MODIS: 2005-09-29 to 2026-09-09 (Pass: True); VIIRS: 2012-05-10 to 2026-11-09 (Pass: True) |
| 6. Yearly Counts & Volatility Review | **PASS** | 19 review flag(s) identified. |
| 7. Row Count Reconciliation | **PASS** | MODIS: loaded=595, dups=0, low_conf=18 -> clean=577 (Match: True); VIIRS: loaded=5744, dups=0, low_conf=238 -> clean=5506 (Match: True) |

## Detections Per Year by Sensor
|   year |   MODIS |   VIIRS |
|-------:|--------:|--------:|
|   2005 |      27 |       0 |
|   2006 |       5 |       0 |
|   2007 |      49 |       0 |
|   2008 |      10 |       0 |
|   2009 |       2 |       0 |
|   2010 |       0 |       0 |
|   2011 |       0 |       0 |
|   2012 |       4 |      12 |
|   2013 |       0 |      19 |
|   2014 |       2 |       7 |
|   2015 |       1 |       8 |
|   2016 |       2 |      16 |
|   2017 |       8 |      38 |
|   2018 |     118 |     966 |
|   2019 |      23 |     121 |
|   2020 |       2 |      49 |
|   2021 |       4 |      75 |
|   2022 |       0 |      17 |
|   2023 |       0 |      14 |
|   2024 |      17 |     439 |
|   2025 |     302 |    3709 |
|   2026 |       1 |      16 |

## Year-over-Year Volatility & Inactive Flags
- Zero detections in 2010 for MODIS
- Zero detections in 2011 for MODIS
- Zero detections in 2013 for MODIS
- High surge in 2018 for MODIS: 118 (vs 8 in 2017, ratio 14.8x)
- Steep drop in 2020 for MODIS: 2 (vs 23 in 2019, ratio 0.09x)
- Zero detections in 2022 for MODIS
- Zero detections in 2023 for MODIS
- High surge in 2025 for MODIS: 302 (vs 17 in 2024, ratio 17.8x)
- Steep drop in 2026 for MODIS: 1 (vs 302 in 2025, ratio 0.00x)
- Zero detections in 2005 for VIIRS
- Zero detections in 2006 for VIIRS
- Zero detections in 2007 for VIIRS
- Zero detections in 2008 for VIIRS
- Zero detections in 2009 for VIIRS
- Zero detections in 2010 for VIIRS
- Zero detections in 2011 for VIIRS
- High surge in 2018 for VIIRS: 966 (vs 38 in 2017, ratio 25.4x)
- High surge in 2024 for VIIRS: 439 (vs 14 in 2023, ratio 31.4x)
- Steep drop in 2026 for VIIRS: 16 (vs 3,709 in 2025, ratio 0.00x)

## Row Count Reconciliation Details
- **MODIS**: Raw Loaded = `595`, Duplicates Dropped = `0`, Low-Confidence Dropped = `18`, Clean Rows = `577`. Reconciled: **PASS**
- **VIIRS**: Raw Loaded = `5,744`, Duplicates Dropped = `0`, Low-Confidence Dropped = `238`, Clean Rows = `5,506`. Reconciled: **PASS**