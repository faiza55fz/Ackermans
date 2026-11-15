# FireTrace Dashboard QA Test Matrix

**Project:** NASA Space Apps Challenge – Harmonizing MODIS and VIIRS Fire Hotspots into a Burning Activity Calendar  
**Test Harness:** Puppeteer Headless Chrome + Visual Inspection  
**Target Instances:**
- `http://localhost:8443/` (Merged Branch: `qa/test-merge`)
- `http://localhost:8444/` (Standalone Worktree: `origin/regional-analytics`)

---

## 1. Module-by-Module Verification Matrix

| # | Dashboard Module | Component Name | Data Backing | Status in Merged Build (`:8443`) | Status in Standalone Build (`:8444`) | Key Observations / QA Verdict |
|---|---|---|---|---|---|---|
| **1** | **Overview** | `Overview` (`src/App.tsx`) | Real (`dashboard.json`, `map.json`) | **PASS** | **PASS** | Displays real KPIs (1,33,605 detections, 4,616 observation days, 92 cells, 7.26 MW FRP). Aggregated Leaflet circles render with tooltips. Verified in `01_overview.png`. |
| **2** | **Fire Explorer** | `FireExplorer` (`src/App.tsx`) | Mock (`src/data.ts`) | **PASS** | **PASS** | Interactive map workspace renders smoothly with clustering, search bar, and drawing controls. Verified in `02_fire_explorer.png`. |
| **3** | **Historical Calendar** | `HistoricalCalendar` (`src/App.tsx`) | Mock (`src/data.ts`) | **PASS** | **PASS** | Year-by-month activity grid renders across 2000–2024 with intensity color scale. Verified in `03_historical_calendar.png`. |
| **4** | **Sensor Comparison** | `SensorComparison` (`src/App.tsx`) | Real (`harmonized_summary.json`) | **BLOCKED / Label Collision** | N/A *(Mock in main)* | Replaced and shadowed by Yashaswi's route refactor. Button missing from sidebar under its own name (confusingly rendered as "Regional Comparison" at slot 4). Verified in `04_sensor_comparison.png`. |
| **5** | **Harmonized Activity** | `HarmonizedActivity` (`src/App.tsx`) | Real (`harmonized_summary.json`) | **PASS** | N/A *(Mock in main)* | Connected to Western Ghats model export. Displays observed vs. estimated proportions (76.8% vs 23.2%) and interactive line charts. Verified in `05_harmonized_activity.png`. |
| **6** | **Anomaly Detection** | `AnomalyDetection` (`src/App.tsx`) | Mock (`src/data.ts`) | **PASS** | **PASS** | High-risk pattern intelligence cards and sensitivity threshold sliders function as designed. Verified in `06_anomaly_detection.png`. |
| **7** | **Data Quality** | `DataQuality` (`src/App.tsx`) | Mock (`src/data.ts`) | **PASS** | **PASS** | Transparency metrics, sensor uptime, and detection confidence break down cleanly. Verified in `07_data_quality.png`. |
| **8** | **Regional Comparison** | `RegionalComparison` (`RegionalComparison.tsx`) | Real (`region_comparison.csv`, `yearly_trends.csv`) | **BLOCKED on Team Branches** | **PASS** | **Merged Build:** Shadowed by BUG-001 collision. Proposed rename (`comparison_regions`) verified only on local test branch (`merged_regional_comparison_click.png`).<br>**Standalone Build:** **PASS resting on verified unique screenshots** (`regional_standalone_palisades.png`, `regional_standalone_western_ghats.png`, `regional_standalone_punjab_haryana.png`). Flawlessly renders Chart A, Chart B, and the ground-truth table for all 3 study regions. |

---

## 2. Section A: Regional Comparison Deep-Dive Testing

Tested on `http://localhost:8444/` (detached `origin/regional-analytics`):

| Test Case | Region / Scenario | Expected Output | Actual Result | Verification Evidence & Status |
|---|---|---|---|---|
| **RC-01** | Pacific Palisades | Loads Palisades annual detections (2005–2026), 6 ground-truth table rows | Detections match `yearly_trends.csv`. Fixed heat source footnote appears. | **PASS**<br>Verified by `regional_standalone_palisades.png`<br>SHA-256: `6E9E9DE186E0A3FAC747350CF1AA085B88D3610FBC383FCC35D09C020968B893` |
| **RC-02** | Western Ghats | Loads Western Ghats annual detections (2000–2026), 6 ground-truth table rows | Sharp seasonal peaks in Feb/March visible. Agreement metrics match. | **PASS**<br>Verified by `regional_standalone_western_ghats.png`<br>SHA-256: `9E69B9001491D4E9E13D30D3FCDC9A3B49AAF9933B478FCE9FD6261BA3B6C7DB` |
| **RC-03** | Punjab & Haryana | Loads Punjab & Haryana annual detections (2000–2026), 6 ground-truth table rows | Distinct Oct/Nov post-monsoon stubble burning peaks clearly prominent. | **PASS**<br>Verified by `regional_standalone_punjab_haryana.png`<br>SHA-256: `8F81CD340FE6EA22B7C3FC51DDAFAAEC61E818B86495DCE83771F5F1744391E6` |
| **RC-04** | Chart A Scale Toggle | Switch between Linear Scale and Log10 Scale | Recharts dynamically switches y-axis domain to logarithmic base 10. | **PASS** |
| **RC-05** | Chart B Grid Toggle | Switch between 0.05° (coarse) and 0.01° (fine) | Bars update: MODIS-only, VIIRS-also, VIIRS-only cell counts refresh. | **PASS** |
| **RC-06** | Top Bar Consistency | Top bar header reflects multi-region scope | Top bar retains static Western US filter badges (BUG-002). | **FAIL** *(Minor)*<br>Verified by `regional_topbar_issue.png`<br>SHA-256: `2868BDCD1D55ABDE9B6CC78C115C8C58C2D006259212FD9C173FD932D4B189A6` |

---

## 3. Section B: Chart Visualization Testing

| Test Case | Target Chart | Verification Focus | Observed Result | Status |
|---|---|---|---|---|
| **CH-01** | Overview Trend Chart | Renders ComposedChart with real yearly data | Yearly detection bar/line series displays 2000–2026 trends cleanly. | **PASS** |
| **CH-02** | Harmonized Metric Charts | Dual LineCharts for Detections and FRP | Renders Observed MODIS, Observed VIIRS, and Estimated VIIRS / Calibrated FRP. | **PASS** |
| **CH-03** | Regional Chart A | Sensor separation (MODIS Aqua/Terra vs VIIRS S-NPP) | Colors distinct: MODIS (orange `#ff7547`), VIIRS (cyan `#00d4ff`). | **PASS** |
| **CH-04** | Regional Chart B | Three-segment stacked bar for spatial overlap | Displays MODIS-only (slate), VIIRS-also (emerald), VIIRS-only (cyan). | **PASS** |
| **CH-05** | Partial Year Marker | 2026 data boundary visualization | Hollow dot marker with disclaimer banner for incomplete year 2026. | **PASS** |

---

## 4. Section C: Geospatial & Map Testing

| Test Case | Map Component | Test Scope | Result | Status |
|---|---|---|---|---|
| **MP-01** | Overview Geospatial View | Leaflet container rendering | Dark tiles load from CartoDB Dark Matter without visual tearing. | **PASS** |
| **MP-02** | Aggregated Grid Cells | Render 92 cells for Western Ghats | Circles plotted with radius scaled to $\sqrt{\text{detections}}$. Color-coded by sensor. | **PASS** |
| **MP-03** | Cell Tooltips | Hover inspection on circle markers | Tooltip displays detection count, sensor breakdown, mean FRP, and period. | **PASS** |
| **MP-04** | Fire Explorer Workspace | Point clustering and cluster explosion on zoom | Hotspots cluster with count badges and zoom-in transitions smoothly. | **PASS** |

---

## 5. Section D: Navigation, Performance & Error Logs

| Test Case | Area | Criteria | Measured Metric | Status |
|---|---|---|---|---|
| **FN-01** | Console Logs (`:8443`) | Zero unhandled JS exceptions | 0 Errors, 2 debug logs (Vite connect) | **PASS** |
| **FN-02** | Network Requests (`:8443`) | Zero 404 Not Found errors | 0 404s (304 Not Modified cache hits for JSONs) | **PASS** |
| **FN-03** | Console Logs (`:8444`) | Zero unhandled JS exceptions | 0 Errors | **PASS** |
| **FN-04** | Network Requests (`:8444`) | CSV assets load successfully | HTTP 200/304 for `region_comparison.csv` and `yearly_trends.csv` | **PASS** |
| **FN-05** | Sidebar Navigation (`:8443`) | Unique, correct routing for each module | Collision between items 4 and 8 (BUG-001). | **FAIL** *(Major)* |
