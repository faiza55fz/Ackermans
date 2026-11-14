# GIS Data Processing & Grid Analysis

This directory contains geospatial analysis and spatial aggregation tools for NASA FIRMS active fire datasets (MODIS and VIIRS), designed to work across any geographic region (e.g. Pacific Palisades, USA and Western Ghats, Karnataka, India).

---

## Architectural & Numerical Decisions

1. **Multi-Region & Dynamic AOI:**
   - The pipeline accepts a `--region` parameter (e.g. `--region palisades` or `--region western_ghats_karnataka`).
   - For curated regions like **Palisades**, the vetted study area bounding box (`lat: [34.0, 34.2]°N`, `lon: [-118.75, -118.42]°W`) is applied automatically.
   - For any other region, the default AOI is dynamically computed from the data's bounding box and rounded outward to the grid cell size (`floor(min / cell_size)` and `ceil(max / cell_size)`), ensuring zero valid land observations are clipped.

2. **Robust Grid Indexing (Float Precision Fix):**
   - Coordinates divided by float cell sizes (e.g. `coord / 0.01`) avoid binary float drift via `np.floor(np.round(coord / cell_size, 6)).astype(int)`.
   - Polygon coordinates in `cell_to_polygon` and GeoJSON exports are rounded to 6 decimal places.
   - Validated by unit tests in `gis/test_grid.py`.

3. **Preserving Missing FRP (NaN):**
   - Missing or non-numeric FRP values remain `NaN` rather than being imputed to `0.0`.
   - `frp_sum` skips NaNs and evaluates to `NaN` only if all observations in a group are missing.
   - Each record tracks `frp_missing_count`. In GeoJSON exports, `NaN` is serialized as valid standard JSON `null`.

4. **Performance on Large Datasets:**
   - All spatial, temporal, and agreement operations use fully vectorized NumPy, Pandas, and GeoPandas routines (cached unique-cell geometries, fast bounding box masking), processing 130,000+ records in seconds without row loops.

---

## Modules and Functions

### 1. `gis/grid.py`
* **`assign_grid(df, cell_size=0.01)`**:
  Calculates integer grid cell indices `cell_x = floor(round(lon / cell_size, 6))` and `cell_y = floor(round(lat / cell_size, 6))`, and assigns `cell_id` (`"{cell_x}_{cell_y}"`).
* **`cell_to_polygon(cell_x, cell_y, cell_size=0.01)`**:
  Constructs a square Shapely `Polygon` representing the bounding box of a grid cell with 6-decimal precision.

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
  Aggregates observations per grid cell, time period (default monthly `"M"`), and sensor (`MODIS` or `VIIRS`). Computes `count`, `days` (unique detection-days), `frp_sum`, and `frp_missing_count`.

---

### 4. `gis/export_geojson.py`
* **`export_cells_to_geojson(agg_df, output_path, cell_size=0.01)`**:
  Converts aggregated tabular records into square polygons (EPSG:4326) and saves them as GeoJSON with properties:
  `cell_id`, `period`, `sensor`, `count`, `days`, `frp_sum`, and `frp_missing_count`.
* **`run_pipeline(region, csv_path=None, output_path=None, cell_size=0.01, period='M')`**:
  Full automated workflow executable via CLI.

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

## Running the Pipeline

### 1. Run Unit Tests
```powershell
python gis/test_grid.py
```

### 2. Run for Pacific Palisades (LA)
```powershell
python gis/export_geojson.py --region palisades
python gis/compare.py --region palisades
python gis/preview.py --region palisades
```
Outputs:
- `gis/output/palisades_cells.geojson`
- `gis/output/sensor_agreement.csv`
- `gis/output/preview.png`

### 3. Run for Western Ghats (Karnataka)
```powershell
python gis/export_geojson.py --region western_ghats_karnataka
python gis/compare.py --region western_ghats_karnataka
python gis/preview.py --region western_ghats_karnataka
```
Outputs:
- `gis/output/western_ghats_karnataka_cells.geojson`
- `gis/output/western_ghats_karnataka_sensor_agreement.csv`
- `gis/output/western_ghats_karnataka_preview.png`
