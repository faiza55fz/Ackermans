# Sanity Check Report: punjab_haryana
**Region Name:** Punjab & Haryana, India  
**Bounding Box:** west=73.8, south=27.6, east=77.7, north=32.6  
**Execution Date:** 2026-11-14  
**Overall Status:** **PASS**

## Summary of Checks
| Check | Status | Details |
|---|:---:|---|
| 1. Null Dates or Datetimes | **PASS** | Null dates: 0, Null datetimes: 0 (Expected: 0) |
| 2. Bounding Box Coordinates | **PASS** | Outside bbox count: 0 (BBox: west=73.8, south=27.6, east=77.7, north=32.6) |
| 3. Null Essential Fields | **PASS** | Null lat: 0, lon: 0, frp: 0, confidence: 0 (Expected: all 0) |
| 4. Non-negative Fire Radiative Power (FRP) | **PASS** | Negative FRP count: 0 (Expected: 0). FRP Min: 0.00, Median: 5.68, Max: 1289.20 |
| 5. Sensor Operational Date Ranges | **PASS** | MODIS: 2000-11-01 to 2026-11-13 (Pass: True); VIIRS: 2012-01-20 to 2026-11-14 (Pass: True) |
| 6. Yearly Counts & Volatility Review | **PASS** | 13 review flag(s) identified. |
| 7. Row Count Reconciliation | **PASS** | MODIS: loaded=519034, dups=0, low_conf=15551 -> clean=503483 (Match: True); VIIRS: loaded=2593220, dups=0, low_conf=364374 -> clean=2228846 (Match: True) |

## Detections Per Year by Sensor
|   year |   MODIS |   VIIRS |
|-------:|--------:|--------:|
|   2000 |     282 |       0 |
|   2001 |    5997 |       0 |
|   2002 |   16095 |       0 |
|   2003 |   18701 |       0 |
|   2004 |   16746 |       0 |
|   2005 |   24458 |       0 |
|   2006 |   16508 |       0 |
|   2007 |   22970 |       0 |
|   2008 |   23430 |       0 |
|   2009 |   23033 |       0 |
|   2010 |   21229 |       0 |
|   2011 |   22571 |       0 |
|   2012 |   26746 |  114315 |
|   2013 |   23214 |  102397 |
|   2014 |   23108 |  114919 |
|   2015 |   18569 |   96939 |
|   2016 |   27225 |  131793 |
|   2017 |   19423 |   98740 |
|   2018 |   22895 |  212763 |
|   2019 |   18889 |  171135 |
|   2020 |   22744 |  210034 |
|   2021 |   25731 |  241049 |
|   2022 |   18839 |  172683 |
|   2023 |   13513 |  186590 |
|   2024 |   12022 |  157901 |
|   2025 |    9459 |  119583 |
|   2026 |    9086 |   98005 |

## Year-over-Year Volatility & Inactive Flags
- High surge in 2001 for MODIS: 5,997 (vs 282 in 2000, ratio 21.3x)
- Zero detections in 2000 for VIIRS
- Zero detections in 2001 for VIIRS
- Zero detections in 2002 for VIIRS
- Zero detections in 2003 for VIIRS
- Zero detections in 2004 for VIIRS
- Zero detections in 2005 for VIIRS
- Zero detections in 2006 for VIIRS
- Zero detections in 2007 for VIIRS
- Zero detections in 2008 for VIIRS
- Zero detections in 2009 for VIIRS
- Zero detections in 2010 for VIIRS
- Zero detections in 2011 for VIIRS

## Row Count Reconciliation Details
- **MODIS**: Raw Loaded = `519,034`, Duplicates Dropped = `0`, Low-Confidence Dropped = `15,551`, Clean Rows = `503,483`. Reconciled: **PASS**
- **VIIRS**: Raw Loaded = `2,593,220`, Duplicates Dropped = `0`, Low-Confidence Dropped = `364,374`, Clean Rows = `2,228,846`. Reconciled: **PASS**