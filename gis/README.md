# GIS Data Processing & Grid Analysis

This directory contains geospatial analysis and spatial aggregation tools for NASA FIRMS active fire datasets (MODIS and VIIRS), designed to work across any geographic region (e.g. Pacific Palisades, USA; Western Ghats, Karnataka, India; and Punjab & Haryana, India).

---

## Architectural & Numerical Decisions

1. **Lightweight Web Map Export Modes:**
   - **`--mode monthly` (default):** Spatiotemporal aggregation per month and sensor.
   - **`--mode totals`:** Aggregates observations across all time into **one feature per unique spatial cell** (`{region}_cells_totals.geojson`), recording overall and sensor-specific detection metrics (`count`, `days`, `frp_sum`, `modis_count`, `viirs_count`, etc.). Drastically reduces payload for regional overviews.
   - **`--mode yearly`:** Generates individual files per year (`{region}_cells_{year}.geojson` inside `gis/output/{region}_yearly/`), enabling fast on-demand temporal loading ($\le 2.9$ MB per year).
   - **`--cell-size 0.05`:** Coarser spatial resolution (~5.5 km) reducing regional feature count by $> 90\%$ for fast client-side rendering.

2. **High-Performance Streaming & Vectorized Processing:**
   - Large multi-million-row regional datasets (e.g. Punjab & Haryana with 2.73M records) are processed using selective columnar reads (`usecols`) with fully vectorized pandas and geopandas operations. No slow row-by-row python loops are used.
   - Peak memory usage remains bounded under ~1.85 GB even on full 2.73M-record analysis.

3. **Compact Coordinates & Standard NaN Serialization:**
   - Polygon coordinates are rounded to 5 decimal places (~1m precision), reducing JSON text size without loss of cartographic accuracy.
   - Missing or non-numeric FRP values remain `NaN` internally and serialize cleanly as standard JSON `null`.

4. **Multi-Region & Dynamic AOI:**
   - Accepts `--region <name>` (e.g. `palisades`, `western_ghats_karnataka`, `punjab_haryana`).
   - For **Palisades**, the vetted study area bounding box (`lat: [34.0, 34.2]°N`, `lon: [-118.75, -118.42]°W`) is applied automatically.
   - For other regions, the AOI bounding box is dynamically computed from coordinates rounded outward to the cell size.

5. **Robust Grid Indexing (Float Precision Bug Fix):**
   - Coordinates use `np.floor(np.round(coord / cell_size, 6)).astype(int)` to prevent IEEE 754 float drift on cell boundaries.
   - Validated by unit tests in `gis/test_grid.py`.

6. **Repository Size Management:**
   - Files exceeding 20 MB (e.g. uncompressed 0.01° full-history monthly exports like `western_ghats_karnataka_cells.geojson` at 26.5 MB) are excluded via `.gitignore` to keep repository clones fast and prevent GitHub upload bottlenecks. All Punjab & Haryana 0.05° files ($\le 2.8$ MB) are tracked cleanly.

---

## Modules and Functions

### 1. `gis/grid.py`
* **`assign_grid(df, cell_size=0.01)`**:
  Calculates integer grid cell indices `cell_x = floor(round(lon / cell_size, 6))` and `cell_y = floor(round(lat / cell_size, 6))`, and assigns `cell_id` (`"{cell_x}_{cell_y}"`).
* **`cell_to_polygon(cell_x, cell_y, cell_size=0.01)`**:
  Constructs a square Shapely `Polygon` for a grid cell with 5-decimal precision.

---

### 2. `gis/aoi.py`
* **`compute_bbox_from_df(df, cell_size=0.01)`**:
  Computes outward-rounded bounding box directly from data coordinates.
* **`get_aoi_bbox(region=None, df=None, cell_size=0.01)`**:
  Returns curated bounding box for known regions or computes from dataset.
* **`clip_to_aoi(df, polygon_geojson=None, region=None, cell_size=0.01)`**:
  Vectorized clipping of hotspot observations to the AOI boundary.

---

### 3. `gis/aggregate.py`
* **`aggregate_by_cell(df, period="M")`**:
  Aggregates observations per grid cell, time period (e.g. `"M"`, `"Y"`), and sensor (`MODIS` or `VIIRS`). Computes `count`, `days` (unique detection-days), `frp_sum`, and `frp_missing_count`.

---

### 4. `gis/export_geojson.py`
* **`export_cells_to_geojson(agg_df, output_path, cell_size=0.01, coord_precision=5)`**:
  Converts aggregated records to GeoJSON square polygons with 5-decimal precision and `null` for missing values.
* **`export_totals(gridded_df, output_path, cell_size=0.01)`**:
  Exports one feature per cell across all time with per-sensor metrics.
* **`export_yearly(gridded_df, output_dir, region, cell_size=0.01)`**:
  Exports separate GeoJSON files partitioned by calendar year.
* **`run_pipeline(...)`**:
  Full automated workflow executable via CLI with `--region`, `--mode`, `--cell-size`, and `--period`.

---

### 5. `gis/compare.py`
* **`compare_sensors_by_day(df, cell_size=0.01)`**:
  Filters observations to 2012-01-01 onward. Builds unique `(cell_id, date)` pairs for each sensor, categorizing cell-days into `modis_only`, `viirs_only`, or `both`.
* **`compute_sensor_agreement(df, cell_size=0.01, output_csv=None, region='palisades')`**:
  Aggregates same-day detections broken down by `year` and day/night passes (`daynight`).

---

### 6. `gis/preview.py`
* **`plot_preview(region='palisades', geojson_path=None, output_png=None)`**:
  Visualizes regional GeoJSON cells colored by total hotspot count, overlays the AOI boundary, and exports a high-resolution preview map.

---

### 7. `gis/test_grid.py`
* Unit test suite verifying boundary edge-cases for grid assignment and coordinate rounding.

---

### 8. `gis/generate_region_comparison.py`
* Computes and writes `gis/output/region_comparison.csv` summarizing comparative statistics across regions (`palisades`, `western_ghats_karnataka`, `punjab_haryana`) at both `0.05°` and `0.01°` grid resolutions.
* Tracks dataset rows, spatial cell counts per sensor (2012–2026), spatial cell overlap, and same-day agreement metrics (`modis_cell_days`, `viirs_also`, `viirs_only`, `modis_only`, and `share_modis_seen_by_viirs`).

---

## Cross-Region Sensor Comparison & Grid Resolution Effects

Spatial agreement between MODIS and VIIRS is strongly modulated by grid cell resolution:

| Region | Cell Size | Rows | MODIS Cells (2012–26) | VIIRS Cells (2012–26) | Both Cells | MODIS Cell-Days | VIIRS Also | VIIRS Only | MODIS Only | % MODIS Seen by VIIRS |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Palisades** | 0.05° | 6,083 | 23 | 27 | 22 | 66 | 55 | 262 | 11 | **83.33%** |
| **Palisades** | 0.01° | 6,083 | 228 | 361 | 210 | 332 | 260 | 579 | 72 | **78.31%** |
| **Western Ghats** | 0.05° | 133,605 | 1,171 | 1,732 | 1,168 | 8,783 | 4,352 | 59,601 | 4,431 | **49.55%** |
| **Western Ghats** | 0.01° | 133,605 | 7,000 | 22,975 | 6,376 | 11,044 | 3,240 | 77,925 | 7,804 | **29.34%** |
| **Punjab & Haryana** | 0.05° | 2,732,329 | 5,708 | 6,810 | 5,656 | 202,761 | 133,329 | 783,639 | 69,432 | **65.76%** |
| **Punjab & Haryana** | 0.01° | 2,732,329 | 73,350 | 120,664 | 71,539 | 285,634 | 64,748 | 1,641,821 | 220,886 | **22.67%** |

* **Impact of Cell Size on Percentages:**
  * When cell size decreases from `0.05°` (~5.5 km) to `0.01°` (~1.1 km), each spatial bucket becomes 25 times smaller. Detections from MODIS and VIIRS that occurred on the same day in the same general neighborhood but separated by $>1.1$ km fall into adjacent but distinct cells rather than the same cell-day.
  * Consequently, the proportion of same-day MODIS cell-days matched by VIIRS decreases in all regions (Palisades: 83.3% $\rightarrow$ 78.3%; Western Ghats: 49.6% $\rightarrow$ 29.3%; Punjab & Haryana: 65.8% $\rightarrow$ 22.7%).

---

## Running the Pipeline

### 1. Run Unit Tests
```powershell
python gis/test_grid.py
```

### 2. Generate Cross-Region Comparison Table
```powershell
python gis/generate_region_comparison.py
```

### 2. Punjab & Haryana (Multi-Million Record Large Region)
* **All-Time Totals at 0.05° (6,908 features — 2.75 MB):**
  ```powershell
  python gis/export_geojson.py --region punjab_haryana --mode totals --cell-size 0.05
  ```
* **Yearly Slices at 0.05° ($\le 2.77$ MB per year):**
  ```powershell
  python gis/export_geojson.py --region punjab_haryana --mode yearly --cell-size 0.05
  ```
* **Sensor Agreement & Same-Day Analysis at 0.05°:**
  ```powershell
  python gis/compare.py --region punjab_haryana --cell-size 0.05
  ```

### 3. Western Ghats (Karnataka)
* **All-Time Totals:**
  ```powershell
  python gis/export_geojson.py --region western_ghats_karnataka --mode totals
  ```
* **Yearly Slices:**
  ```powershell
  python gis/export_geojson.py --region western_ghats_karnataka --mode yearly
  ```

### 4. Pacific Palisades (LA)
```powershell
python gis/export_geojson.py --region palisades
python gis/compare.py --region palisades
python gis/preview.py --region palisades
```
