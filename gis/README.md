# GIS Data Processing & Grid Analysis

This directory contains geospatial analysis and spatial aggregation tools for NASA FIRMS active fire datasets (MODIS and VIIRS) in the Palisades / Santa Monica Mountains study area.

---

## Architectural & Numerical Decisions

1. **Robust Grid Indexing (Float Precision Bug Fix):**
   - Coordinates divided by float cell sizes (e.g. `coord / 0.01`) can suffer from binary floating-point representation drift (e.g. `34.08 / 0.01 == 3407.9999999999995`).
   - All cell assignments now use `np.floor(np.round(coord / cell_size, 6)).astype(int)` to guarantee exact mathematical boundary alignment.
   - Polygon bounding box corner coordinates in `cell_to_polygon` and GeoJSON exports are rounded to 6 decimal places.
   - Verified via unit test suite in `gis/test_grid.py`.

2. **Widened Area of Interest (AOI):**
   - The default AOI bounding box is `Latitude: [34.0, 34.2]°N`, `Longitude: [-118.75, -118.42]°W` (widened from `-118.43` to `-118.42`).
   - Retains all valid land observations (6,081 of 6,083 points). The only 2 excluded points (`lat=33.98934, 33.99037`) are offshore detections south of `34.0°N` in Santa Monica Bay.

3. **Preserving Missing FRP (NaN):**
   - In `gis/aggregate.py`, missing or invalid Fire Radiative Power (FRP) values are kept as `NaN` rather than imputed to `0.0`.
   - `frp_sum` skips NaNs (returns `NaN` if all observations in a group are missing).
   - Each aggregated record includes `frp_missing_count` tracking the exact number of missing FRP entries in that cell-period-sensor slice.

---

## Modules and Functions

### 1. `gis/grid.py`
Provides spatial discretization for point hotspot observations.
* **`assign_grid(df, cell_size=0.01)`**:
  Calculates integer grid cell indices `cell_x = floor(round(lon / cell_size, 6))` and `cell_y = floor(round(lat / cell_size, 6))`, and assigns `cell_id` (`"{cell_x}_{cell_y}"`).
* **`cell_to_polygon(cell_x, cell_y, cell_size=0.01)`**:
  Constructs a square Shapely `Polygon` representing the bounding box of a grid cell, with coordinates rounded to 6 decimals.

---

### 2. `gis/aoi.py`
Handles spatial boundaries and Area of Interest (AOI) clipping.
* **`clip_to_aoi(df, polygon_geojson=None)`**:
  Converts input points to a GeoPandas `GeoDataFrame` (EPSG:4326) and clips them to the AOI using spatial intersection (`intersects`).
* **`get_default_aoi()`**:
  Returns a Shapely `Polygon` for the default bounding box: `Latitude [34.0, 34.2]`, `Longitude [-118.75, -118.42]`.
* **`parse_geojson_polygon(polygon_input)`**:
  Parses diverse polygon input types (GeoJSON file path, dictionary, Shapely geometry, or GeoDataFrame).

---

### 3. `gis/aggregate.py`
Aggregates point detections into spatiotemporal summaries.
* **`aggregate_by_cell(df, period="M")`**:
  Aggregates observations per grid cell, time period (default monthly `"M"`), and sensor (`MODIS` or `VIIRS`). Computes:
  * `count`: Total hotspot detections.
  * `days`: Unique detection-days (counts each cell at most once per calendar day per sensor).
  * `frp_sum`: Total Fire Radiative Power (sum of FRP in Megawatts, skipping NaNs; NaN if all missing).
  * `frp_missing_count`: Count of observations with missing/NaN FRP in each cell-period-sensor group.

---

### 4. `gis/export_geojson.py`
Exports aggregated spatial grid cells to GeoJSON for mapping and visualization.
* **`export_cells_to_geojson(agg_df, output_path="gis/output/palisades_cells.geojson", cell_size=0.01)`**:
  Converts aggregated tabular records into square polygons (EPSG:4326) and saves them as GeoJSON with properties:
  `cell_id`, `period`, `sensor`, `count`, `days`, `frp_sum`, and `frp_missing_count`.
* **`run_pipeline(...)`**:
  Orchestrates the entire workflow: loading data, AOI clipping, grid assignment, aggregation, GeoJSON export, and sensor overlap reporting.

---

### 5. `gis/compare.py`
Performs same-day spatio-temporal comparison between MODIS and VIIRS sensors.
* **`compare_sensors_by_day(df, cell_size=0.01)`**:
  Filters observations to 2012-01-01 onward (the operational overlap window). Builds unique `(cell_id, date)` pairs for each sensor, returns whether each cell-day was detected by MODIS, VIIRS, or both, and provides summary metrics.
* **`compute_sensor_agreement(df, cell_size=0.01, output_csv="gis/output/sensor_agreement.csv")`**:
  Aggregates same-day detections broken down by `year` and day/night passes (`daynight` column). Outputs a summary CSV with columns: `year`, `daynight`, `modis_only`, `viirs_only`, `both`.

---

### 6. `gis/preview.py`
* **`plot_preview(...)`**:
  Visualizes `gis/output/palisades_cells.geojson` on a map colored by total hotspot count per cell, overlays the widened AOI boundary, and exports the map to `gis/output/preview.png`.

---

### 7. `gis/test_grid.py`
* Unit test suite verifying boundary edge-cases for grid assignment (e.g. 34.01, 34.05, 34.08, -118.43, -118.75) and coordinate rounding.

---

## Running the Pipeline

1. **Run Grid Unit Tests:**
   ```powershell
   python gis/test_grid.py
   ```

2. **Generate Grid & GeoJSON Export:**
   ```powershell
   python gis/export_geojson.py
   ```
   Outputs: `gis/output/palisades_cells.geojson`

3. **Generate Map Preview:**
   ```powershell
   python gis/preview.py
   ```
   Outputs: `gis/output/preview.png`

4. **Run Sensor Comparison & Agreement:**
   ```powershell
   python gis/compare.py
   ```
   Outputs: `gis/output/sensor_agreement.csv`
