# FireTrace Data Quality & Scientific Integrity Report

**Scope:** NASA Space Apps Challenge – Harmonizing MODIS and VIIRS Fire Hotspots into a Burning Activity Calendar  
**QA Assessment:** Read-Only Audit of Harmonization Datasets and Scientific Outputs  
**Target Regions:**
1. Pacific Palisades, California, USA (`palisades`)
2. Western Ghats, Karnataka, India (`western_ghats_karnataka`)
3. Punjab & Haryana, India (`punjab_haryana`)

---

## 1. Summary of Evaluated Datasets

| Dataset / File | Rows / Size | Format | Source Branch | Content / Scientific Role |
|---|---|---|---|---|
| `public/data/dashboard.json` | 449 lines / 12 KB | JSON | `firetrace-pipeline-integration` | Regional metadata, date ranges, total detections, observation days, mean FRP, yearly trends |
| `public/data/map.json` | 1,327 lines / 37 KB | JSON | `firetrace-pipeline-integration` | Aggregated grid cells (0.25° resolution) with lat/lon, detection breakdown (MODIS vs VIIRS), and mean FRP |
| `public/data/harmonized_summary.json` | 109.9 KB | JSON | `feature/harmonization-engine` | Western Ghats model harmonization export: observed vs estimated rows, VIIRS detection modeling, calibrated FRP, monthly/yearly timeseries |
| `public/data/region_comparison.csv` | 7 rows / 651 B | CSV | `regional-analytics` | Ground-truth sensor agreement across 3 regions at coarse (0.05°) and fine (0.01°) resolutions |
| `public/data/yearly_trends.csv` | 117 rows / 3.4 KB | CSV | `regional-analytics` | Sensor-specific annual detections, active days, FRP sums, and partial-year flags (2000–2026) |

---

## 2. Key Data Quality Findings & Scientific Risks

### Risk 1: Upstream Test Data Dependency for Regional CSVs
- **Observation:** `public/data/yearly_trends.csv` and `public/data/region_comparison.csv` were built using the initial test dataset for Pacific Palisades (`palisades-test-data`).
- **Scientific Impact:** If the pipeline team re-cleans or updates the final Palisades dataset, the pre-built CSVs loaded by `RegionalComparison.tsx` will become desynchronized.
- **Recommendation:** Flagged as an operational data risk. Do not manually edit or regenerate during the hackathon freeze unless full re-ingestion of all three regions is conducted.

---

### Risk 2: Fixed Heat Source Anomaly in Pacific Palisades
- **Observation:** Spatial filtering in Pacific Palisades identified a grid cell near coordinate **(-118.72°W, 34.15°N)** exhibiting ~119 night-time, low-FRP VIIRS detections consistently across a 15-year span.
- **Scientific Assessment:** Genuine wildfire hotspots do not recur at identical sub-pixel coordinates for 15 consecutive years with persistent low radiative power. This signature strongly suggests an artificial fixed thermal emitter (e.g., an industrial flare, landfill gas exhaust, or static thermal chimney).
- **Data Safeguard:** Raksha appropriately added a prominent footnote in the UI warning reviewers of this under-review fixed heat source.

---

### Risk 3: Satellite Constellation Expansions (NOAA-20 & NOAA-21)
- **Observation:** Annual VIIRS detection totals exhibit pronounced upward shifts:
  - First jump in **2012** (Suomi-NPP VIIRS operational introduction).
  - Second jump in **2018** (NOAA-20 / JPSS-1 operational deployment).
  - Third jump in **2023** (NOAA-21 / JPSS-2 operational deployment).
- **Scientific Assessment:** The observed increase in raw detection volume reflects increased daily orbital overpasses (more sensor eyes on the ground), not a doubling of real physical fire activity.
- **Safeguard:** Any scientific comparison of burning activity across years must evaluate detections normalized per satellite or through the calibrated harmonization model.

---

### Risk 4: 2026 Calendar Year Truncation
- **Observation:** Hotspot detection records in the repository terminate in **November 2026**.
- **Scientific Assessment:** Because 2026 is an incomplete calendar year (~11 months of observations), raw annual sums for 2026 are artificially lower than preceding full calendar years.
- **Safeguard:** In `yearly_trends.csv`, rows for 2026 have `is_partial_year = True`. The frontend plots 2026 points with distinct hollow markers and a clear warning banner.

---

### Risk 5: In-Sample Calibration Scope for Harmonization Engine
- **Observation:** In `public/data/harmonized_summary.json`, the model achieves an in-sample fit of $R^2 \approx 0.84$.
- **Scientific Assessment:** The harmonization model currently represents an in-sample regional calibration for the Western Ghats overlap period (2012–2024). Independent out-of-region holdout validation is ongoing.
- **Safeguard:** All estimated timeseries plots and KPI cards in the dashboard explicitly feature the mandatory disclosure badge:  
  `"Experimental Model Output (In-Sample Calibration)"`.

---

## 3. Data Integrity & Verification Verdict

| Verification Item | Tested Metric | Result | Notes |
|---|---|---|---|
| **Schema Validation** | 23-column standardized FIRMS schema | **PASS** | Cleaned datasets strictly adhere to agreed unified schema. |
| **Completeness** | Missing data / null values in core metrics | **PASS** | `frp.available_records` and `detections` fully accounted for. |
| **Boundary Consistency** | SP vs NRT transition & duplicate deduplication | **PASS** | Verified in prior cleaning phases with zero overlap boundary duplicates. |
| **Temporal Bounding** | First and last observation timestamps | **PASS** | Accurately spans from Nov 2000 (Terra launch) to Nov 2026. |
