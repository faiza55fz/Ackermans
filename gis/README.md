# GIS Data Processing & Grid Analysis

This directory contains geospatial analysis and spatial aggregation tools for NASA FIRMS active fire datasets (MODIS and VIIRS) in the Palisades / Santa Monica Mountains study area.

---

## Modules and Functions

### 1. `gis/grid.py`
Provides spatial discretization for point hotspot observations.
* **`assign_grid(df, cell_size=0.01)`**:
  Calculates integer grid cell indices `cell_x = floor(lon / cell_size)` and `cell_y = floor(lat / cell_size)`, and assigns a string identifier `cell_id` (`"{cell_x}_{cell_y}"`) to each row in the DataFrame.
* **`cell_to_polygon(cell_x, cell_y, cell_size=0.01)`**:
  Constructs a square Shapely `Polygon` representing the bounding box of a specific grid cell `(min_lon, min_lat, max_lon, max_lat)`.

---

### 2. `gis/aoi.py`
Handles spatial boundaries and Area of Interest (AOI) clipping.
* **`clip_to_aoi(df, polygon_geojson=None)`**:
  Converts input points to a GeoPandas `GeoDataFrame` (EPSG:4326) and clips them to the AOI using spatial intersection (`intersects`). If `polygon_geojson` is `None`, it defaults to the bounding box of the study area.
* **`get_default_aoi()`**:
  Returns a Shapely `Polygon` for the default bounding box: `Latitude [34.0, 34.2]`, `Longitude [-118.75, -118.43]`.
* **`parse_geojson_polygon(polygon_input)`**:
  Parses diverse polygon input types, including GeoJSON file paths, GeoJSON dictionaries, Shapely geometry objects, or GeoDataFrames.

---

### 3. `gis/aggregate.py`
Aggregates point detections into spatiotemporal summaries.
* **`aggregate_by_cell(df, period="M")`**:
  Aggregates observations per grid cell, time period (default monthly `"M"`), and sensor (`MODIS` or `VIIRS`). Computes:
  * `count`: Total hotspot detections.
  * `days`: Unique detection-days (ensures each cell is counted at most once per calendar day per sensor).
  * `frp_sum`: Total Fire Radiative Power (sum of FRP in Megawatts, rounded to 2 decimals).

---

### 4. `gis/export_geojson.py`
Exports aggregated spatial grid cells to GeoJSON for mapping and visualization.
* **`export_cells_to_geojson(agg_df, output_path="gis/output/palisades_cells.geojson", cell_size=0.01)`**:
  Converts aggregated tabular records into square polygons (EPSG:4326) and saves them as GeoJSON with the properties:
  `cell_id`, `period`, `sensor`, `count`, `days`, and `frp_sum`.
* **`run_pipeline(...)`**:
  Orchestrates the entire workflow: loading data, AOI clipping, grid assignment, aggregation, GeoJSON export, and sensor overlap reporting.

---

### 5. `gis/compare.py`
Performs same-day spatio-temporal comparison between MODIS and VIIRS sensors.
* **`compare_sensors_by_day(df, cell_size=0.01)`**:
  Filters observations to 2012-01-01 onward (the operational overlap window). Builds unique `(cell_id, date)` pairs for each sensor, returns whether each cell-day was detected by MODIS, VIIRS, or both, and provides overall summary statistics.
* **`compute_sensor_agreement(df, cell_size=0.01, output_csv="gis/output/sensor_agreement.csv")`**:
  Aggregates same-day detections broken down by `year` and day/night passes (`daynight` column). Outputs a summary CSV with columns: `year`, `daynight`, `modis_only`, `viirs_only`, `both`.

---

### 6. `gis/preview.py`
* **`plot_preview(...)`**:
  Visualizes `gis/output/palisades_cells.geojson` on a map colored by total hotspot count per cell, overlays the AOI boundary, and exports the map to `gis/output/preview.png`.

---

### 7. `gis/explore.py`
* Diagnostic utility that loads a CSV from `gis/data/`, prints row counts, columns, and date ranges, and generates a scatter plot preview of longitude vs. latitude.

---

## Running the Pipeline

1. **Generate Grid & GeoJSON Export:**
   ```powershell
   python gis/export_geojson.py
   ```
   Outputs: `gis/output/palisades_cells.geojson`

2. **Generate Map Preview:**
   ```powershell
   python gis/preview.py
   ```
   Outputs: `gis/output/preview.png`

3. **Run Sensor Comparison & Agreement:**
   ```powershell
   python gis/compare.py
   ```
   Outputs: `gis/output/sensor_agreement.csv`
