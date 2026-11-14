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
| 4. Non-negative Fire Radiative Power (FRP) | **PASS** | Negative FRP count: 0 (Expected: 0). FRP Min: 0.00, Median: 13.25, Max: 4563.40 |
| 5. Sensor Operational Date Ranges | **PASS** | MODIS: 2005-09-29 to 2025-01-11 (Pass: True); VIIRS: 2013-01-31 to 2026-02-28 (Pass: True) |
| 6. Yearly Counts & Volatility Review | **PASS** | 26 review flag(s) identified. |
| 7. Row Count Reconciliation | **PASS** | MODIS: loaded=438, dups=0, low_conf=15 -> clean=423 (Match: True); VIIRS: loaded=4303, dups=0, low_conf=166 -> clean=4137 (Match: True) |

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
|   2012 |       4 |       0 |
|   2013 |       0 |       2 |
|   2014 |       2 |       2 |
|   2015 |       0 |       1 |
|   2016 |       0 |       1 |
|   2017 |       5 |      17 |
|   2018 |       0 |       2 |
|   2019 |       0 |       0 |
|   2020 |       0 |       2 |
|   2021 |       0 |       0 |
|   2022 |       0 |       7 |
|   2023 |       0 |       1 |
|   2024 |      17 |     421 |
|   2025 |     302 |    3677 |
|   2026 |       0 |       4 |

## Year-over-Year Volatility & Inactive Flags
- Zero detections in 2010 for MODIS
- Zero detections in 2011 for MODIS
- Zero detections in 2013 for MODIS
- Zero detections in 2015 for MODIS
- Zero detections in 2016 for MODIS
- Zero detections in 2018 for MODIS
- Zero detections in 2019 for MODIS
- Zero detections in 2020 for MODIS
- Zero detections in 2021 for MODIS
- Zero detections in 2022 for MODIS
- Zero detections in 2023 for MODIS
- High surge in 2025 for MODIS: 302 (vs 17 in 2024, ratio 17.8x)
- Zero detections in 2026 for MODIS
- Zero detections in 2005 for VIIRS
- Zero detections in 2006 for VIIRS
- Zero detections in 2007 for VIIRS
- Zero detections in 2008 for VIIRS
- Zero detections in 2009 for VIIRS
- Zero detections in 2010 for VIIRS
- Zero detections in 2011 for VIIRS
- Zero detections in 2012 for VIIRS
- High surge in 2017 for VIIRS: 17 (vs 1 in 2016, ratio 17.0x)
- Zero detections in 2019 for VIIRS
- Zero detections in 2021 for VIIRS
- High surge in 2024 for VIIRS: 421 (vs 1 in 2023, ratio 421.0x)
- Steep drop in 2026 for VIIRS: 4 (vs 3,677 in 2025, ratio 0.00x)

## Row Count Reconciliation Details
- **MODIS**: Raw Loaded = `438`, Duplicates Dropped = `0`, Low-Confidence Dropped = `15`, Clean Rows = `423`. Reconciled: **PASS**
- **VIIRS**: Raw Loaded = `4,303`, Duplicates Dropped = `0`, Low-Confidence Dropped = `166`, Clean Rows = `4,137`. Reconciled: **PASS**