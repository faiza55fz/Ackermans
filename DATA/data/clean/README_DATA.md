# Cleaned Fire Detections (Palisades Test Data)

> **Notice:** This is a temporary winter-only version for pipeline testing, with about 4,560 rows.

## Dataset Details
- **Status:** Temporary winter-only version for pipeline testing (~4,560 rows).
- **Temporal Coverage:** December 1 to February 28/29 only. MODIS starts from 2005, VIIRS starts from 2013 (as downloaded), all standard processing (`SP`).
- **Future Replacement:** A full-year version will replace it with the exact same 23 columns; only row counts will change.
- **Columns (23 Total):**
  - Standard fields: `region`, `sensor`, `satellite`, `processing`, `datetime_utc`, `date`, `year`, `latitude`, `longitude`, `confidence`, `confidence_class`, `frp`, `daynight`
  - Auxiliary metadata: `scan`, `track`, `instrument`, `version`, `brightness`, `bright_t31`, `bright_ti4`, `bright_ti5`, `type`
  - Fire type classification: `is_vegetation_fire` (boolean: `True` when `type == 0` or missing, `False` otherwise)
- **Serialization:**
  - `confidence` is stored as text/string in the combined dataset (`palisades_la_combined.parquet` and `palisades_la_combined.csv`) to support both numeric MODIS scores (0–100) and categorical VIIRS values (`l`, `n`, `h`).
