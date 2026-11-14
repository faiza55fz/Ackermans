# Sanity Check Report: western_ghats_karnataka
**Region Name:** Western Ghats, Karnataka, India  
**Bounding Box:** west=74.0, south=13.3, east=76.1, north=15.8  
**Execution Date:** 2026-11-14  
**Overall Status:** **PASS**

## Summary of Checks
| Check | Status | Details |
|---|:---:|---|
| 1. Null Dates or Datetimes | **PASS** | Null dates: 0, Null datetimes: 0 (Expected: 0) |
| 2. Bounding Box Coordinates | **PASS** | Outside bbox count: 0 (BBox: west=74.0, south=13.3, east=76.1, north=15.8) |
| 3. Null Essential Fields | **PASS** | Null lat: 0, lon: 0, frp: 0, confidence: 0 (Expected: all 0) |
| 4. Non-negative Fire Radiative Power (FRP) | **PASS** | Negative FRP count: 0 (Expected: 0). FRP Min: 0.11, Median: 4.71, Max: 414.70 |
| 5. Sensor Operational Date Ranges | **PASS** | MODIS: 2000-11-11 to 2026-11-11 (Pass: True); VIIRS: 2012-01-20 to 2026-11-14 (Pass: True) |
| 6. Yearly Counts & Volatility Review | **PASS** | 12 review flag(s) identified. |
| 7. Row Count Reconciliation | **PASS** | MODIS: loaded=18978, dups=0, low_conf=847 -> clean=18131 (Match: True); VIIRS: loaded=150275, dups=0, low_conf=34801 -> clean=115474 (Match: True) |

## Detections Per Year by Sensor
|   year |   MODIS |   VIIRS |
|-------:|--------:|--------:|
|   2000 |      28 |       0 |
|   2001 |     199 |       0 |
|   2002 |     182 |       0 |
|   2003 |     484 |       0 |
|   2004 |    1124 |       0 |
|   2005 |     730 |       0 |
|   2006 |     784 |       0 |
|   2007 |     600 |       0 |
|   2008 |     607 |       0 |
|   2009 |     605 |       0 |
|   2010 |     371 |       0 |
|   2011 |    1002 |       0 |
|   2012 |    1083 |    5546 |
|   2013 |     801 |    6025 |
|   2014 |     668 |    4708 |
|   2015 |     600 |    4081 |
|   2016 |    1044 |    7761 |
|   2017 |    1027 |    7066 |
|   2018 |    1109 |    6911 |
|   2019 |     757 |    9408 |
|   2020 |     479 |    5803 |
|   2021 |     401 |    5117 |
|   2022 |     608 |    5988 |
|   2023 |    1278 |   20282 |
|   2024 |     438 |    8243 |
|   2025 |     649 |    9884 |
|   2026 |     473 |    8651 |

## Year-over-Year Volatility & Inactive Flags
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
- **MODIS**: Raw Loaded = `18,978`, Duplicates Dropped = `0`, Low-Confidence Dropped = `847`, Clean Rows = `18,131`. Reconciled: **PASS**
- **VIIRS**: Raw Loaded = `150,275`, Duplicates Dropped = `0`, Low-Confidence Dropped = `34,801`, Clean Rows = `115,474`. Reconciled: **PASS**