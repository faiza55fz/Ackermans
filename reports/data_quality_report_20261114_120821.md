# FireTrace Data Quality Audit Report

**Generated:** 2026-11-14 12:08:21 UTC
**Processed Dataset:** `palisades_la_VIIRS_processed.json`
**Quarantine Source:** `palisades_la_VIIRS_quarantined.json`

---

## 1. Executive Accounting & Reconciliation Summary

| Accounting Item | Value | Share |
| :--- | :--- | :--- |
| **Total Raw Input Rows** | `4,137` | 100.0% |
| **Accepted Valid Observations** | `4,137` | 100.00% |
| **Quarantined Fatal Defects** | `0` | 0.00% |
| **Count Reconciliation** | **RECONCILED** | Verified against raw ingest manifest |

## 2. Observed Hotspot Detection Bounds vs Preliminary Study Window

> **Note on Spatial Scope**: The spatial coordinates below represent the **Observed Hotspot Detection Bounding Box** in this specific dataset file. They are data-derived and do not constitute an official certified incident boundary.

* **Observed Latitude Range:** `34.01585°N` to `34.19991°N`
* **Observed Longitude Range:** `118.73651°W` to `118.44553°W`
* **Observed Centroid:** `34.10788°N`, `118.59102°W`

### Preliminary Palisades Study Window Comparison
* **Preliminary Window:** Lat `[33.95000°N, 34.15000°N]` × Lng `[118.65000°W, 118.45000°W]`
* **Evaluation Status:** `EXTENDS_BEYOND_PRELIMINARY_BOX`
* **Finding:** Observed detections extend beyond preliminary box: Max Lat 34.1999 > 34.15; Min Lng -118.7365 < -118.65; Max Lng -118.4455 > -118.45. Adjust boundary before final study ingestion.

## 3. Observation Time Span (UTC)

* **Earliest Acquisition Date:** `2013-01-31`
* **Latest Acquisition Date:** `2026-02-28`

## 4. Platform & Sensor Breakdown

| Canonical Platform / Sensor | Family | Records | Share |
| :--- | :--- | :--- | :--- |
| **VIIRS (N21)** | `VIIRS` | `1,688` | 40.8% |
| **VIIRS (N20)** | `VIIRS` | `1,245` | 30.1% |
| **VIIRS S-NPP** | `VIIRS` | `1,204` | 29.1% |

## 5. Confidence Distribution Summary (Sensor-Specific)

*No MODIS observations with numeric confidence in this dataset.*

### VIIRS Categorical Confidence ('l', 'n', 'h' Quality Classes)
| Category | Description | Records | Share |
| :--- | :--- | :--- | :--- |
| `h` | High ('h') | `590` | 14.3% |
| `n` | Nominal ('n') | `3,547` | 85.7% |

## 6. Quarantine Defect Log Summary

*(Zero fatal defects detected; 0 records quarantined)*

## 7. Verified Scientific & Architectural Checklist

> **Checklist Verification**: Check statuses below are computed strictly from programmatic verification tests run over the actual output files.

| Scientific Requirement | Verification Status | Audit Detail |
| :--- | :--- | :--- |
| `confidence_raw_preservation` | **[PASSED]** | Verified: 100% (4137/4137) of records with input confidence preserved confidence_raw without loss |
| `confidence_separation` | **[PASSED]** | Verified: Sensor scales isolated across 0 MODIS and 4137 VIIRS records without cross-conversion |
| `raw_scan_track_unrounded` | **[PASSED]** | Verified: Original float dimensions preserved without rounding across all 4137 observations |
| `fatal_defects_quarantined` | **[PASSED]** | Verified: 0 fatal defects in valid records; all 0 quarantined records carry traceable defect logs |
| `cross_satellite_independence` | **[PASSED]** | Verified: Cross-satellite detections are preserved independently; overlap flag initialized to unassessed (None) |
| `spatial_extent_verified` | **[EXTENDS_BEYOND_PRELIMINARY_BOX]** | Observed detections extend beyond preliminary box: Max Lat 34.1999 > 34.15; Min Lng -118.7365 < -118.65; Max Lng -118.4455 > -118.45. Adjust boundary before final study ingestion. |

