# MODIS–VIIRS active fire harmonization

Harmonize MODIS and VIIRS active fire hotspots from NASA FIRMS CSVs onto one common grid so the two sensors can be compared and modeled together.

## Inputs

- NASA FIRMS CSV exports for MODIS and VIIRS active fire detections.
- Files live in `data/raw` and are never modified.
- Paths, sensor names, grid definition, and model settings come from `config.yaml`.

## Output

- Gridded hotspot products written only under `data/processed`.
- Any table that mixes observed detections with estimated values includes an `is_estimated` column: `False` for observed rows, `True` for estimated rows.

## Stack

- Python 3.11
- pandas, geopandas, statsmodels, scikit-learn
- pytest for tests
- PyYAML for `config.yaml`
- numpy and pyarrow are available as supporting libraries (see `requirements.txt`)

## Layout

```text
src/ingest/      read FIRMS CSVs
src/clean/       filter and standardize detections
src/grid/        assign detections to the common grid
src/models/      cross-sensor models and gap estimates
src/validate/    checks on grid, schema, and estimates
src/export/      write processed outputs
tests/           pytest, one test module per source module
data/raw/        immutable FIRMS inputs
data/processed/  derived products
config.yaml      all runtime configuration
```

## Pipeline

1. **Ingest.** Load FIRMS CSVs into tabular frames. Do not write back to `data/raw`.
2. **Clean.** Standardize columns, timestamps, and geometries for both sensors. Drop or flag invalid rows explicitly.
3. **Grid.** Map cleaned points onto the common grid defined in `config.yaml`.
4. **Model.** Fit cross-sensor relationships with statsmodels or scikit-learn. Estimates stay distinguishable from observations.
5. **Validate.** Confirm grid assignment, required columns, and that mixed outputs carry `is_estimated`.
6. **Export.** Write results under `data/processed`.

## Code rules

- Core logic is Python modules, not notebooks.
- Functions are small and pure: they take inputs and return values, and they do not overwrite source files.
- Every function has type hints, a docstring, and a pytest test.

## Data rules

- Never overwrite raw data.
- Never merge observed and estimated values without an `is_estimated` column.
