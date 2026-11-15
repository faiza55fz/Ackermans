# FireTrace Data Quality Audit Report

**Generated:** 2026-11-14 12:08:20 UTC
**Processed Dataset:** `palisades_la_MODIS_processed.json`
**Quarantine Source:** `palisades_la_MODIS_quarantined.json`

---

## 1. Executive Accounting & Reconciliation Summary

| Accounting Item | Value | Share |
| :--- | :--- | :--- |
| **Total Raw Input Rows** | `423` | 100.0% |
| **Accepted Valid Observations** | `423` | 100.00% |
| **Quarantined Fatal Defects** | `0` | 0.00% |
| **Count Reconciliation** | **RECONCILED** | Verified against raw ingest manifest |

## 2. Observed Hotspot Detection Bounds vs Preliminary Study Window

> **Note on Spatial Scope**: The spatial coordinates below represent the **Observed Hotspot Detection Bounding Box** in this specific dataset file. They are data-derived and do not constitute an official certified incident boundary.

* **Observed Latitude Range:** `34.02870°N` to `34.19980°N`
* **Observed Longitude Range:** `118.74980°W` to `118.43500°W`
* **Observed Centroid:** `34.11425°N`, `118.59240°W`

### Preliminary Palisades Study Window Comparison
* **Preliminary Window:** Lat `[33.95000°N, 34.15000°N]` × Lng `[118.65000°W, 118.45000°W]`
* **Evaluation Status:** `EXTENDS_BEYOND_PRELIMINARY_BOX`
* **Finding:** Observed detections extend beyond preliminary box: Max Lat 34.1998 > 34.15; Min Lng -118.7498 < -118.65; Max Lng -118.4350 > -118.45. Adjust boundary before final study ingestion.

## 3. Observation Time Span (UTC)

* **Earliest Acquisition Date:** `2005-09-29`
* **Latest Acquisition Date:** `2025-01-11`

## 4. Platform & Sensor Breakdown

| Canonical Platform / Sensor | Family | Records | Share |
| :--- | :--- | :--- | :--- |
| **MODIS Aqua** | `MODIS` | `244` | 57.7% |
| **MODIS Terra** | `MODIS` | `179` | 42.3% |

## 5. Confidence Distribution Summary (Sensor-Specific)

### MODIS Numeric Confidence (0–100% Scale)
* **Observations:** `423`
* **Mean Confidence:** `88.0%`
* **Min / Max:** `30%` / `100%`

*No VIIRS observations with categorical confidence in this dataset.*

## 6. Quarantine Defect Log Summary

*(Zero fatal defects detected; 0 records quarantined)*

## 7. Verified Scientific & Architectural Checklist

> **Checklist Verification**: Check statuses below are computed strictly from programmatic verification tests run over the actual output files.

| Scientific Requirement | Verification Status | Audit Detail |
| :--- | :--- | :--- |
| `confidence_raw_preservation` | **[PASSED]** | Verified: 100% (423/423) of records with input confidence preserved confidence_raw without loss |
| `confidence_separation` | **[PASSED]** | Verified: Sensor scales isolated across 423 MODIS and 0 VIIRS records without cross-conversion |
| `raw_scan_track_unrounded` | **[PASSED]** | Verified: Original float dimensions preserved without rounding across all 423 observations |
| `fatal_defects_quarantined` | **[PASSED]** | Verified: 0 fatal defects in valid records; all 0 quarantined records carry traceable defect logs |
| `cross_satellite_independence` | **[PASSED]** | Verified: Cross-satellite detections are preserved independently; overlap flag initialized to unassessed (None) |
| `spatial_extent_verified` | **[EXTENDS_BEYOND_PRELIMINARY_BOX]** | Observed detections extend beyond preliminary box: Max Lat 34.1998 > 34.15; Min Lng -118.7498 < -118.65; Max Lng -118.4350 > -118.45. Adjust boundary before final study ingestion. |

