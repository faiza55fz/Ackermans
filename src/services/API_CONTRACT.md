# FireTrace API Contract & Specification

**Challenge:** NASA Space Apps Challenge – *Harmonizing MODIS and VIIRS Fire Hotspots into a Burning Activity Calendar*  
**Architecture:** RESTful OpenAPI 3.0 compatible data service  
**Version:** `v1.0.0`  
**Base URL:** `${VITE_API_BASE_URL}/api/v1` (Fallback to static assets in `/data/*.json` when `VITE_DATA_SOURCE=static`)

---

## 1. Cleaned Data Schema (23 Canonical Columns)

Every observation record delivered by backend data queries matches the 23-column standardized schema:

| Column | Data Type | Nullable | Description / Enumeration |
|---|---|---|---|
| `latitude` | `float64` | No | Hotspot centroid latitude in WGS 84 (-90.0 to 90.0) |
| `longitude` | `float64` | No | Hotspot centroid longitude in WGS 84 (-180.0 to 180.0) |
| `brightness` | `float64` | **Yes** | MODIS channel 21/22 brightness temperature in Kelvin (null for VIIRS) |
| `scan` | `float64` | No | Along-scan pixel dimension in km |
| `track` | `float64` | No | Along-track pixel dimension in km |
| `acq_date` | `string` | No | Acquisition date in ISO-8601 format (`YYYY-MM-DD`) |
| `acq_time` | `string` | No | Acquisition time in UTC (`HHMM`) |
| `satellite` | `string` | No | Satellite platform code: `'Terra'`, `'Aqua'`, `'N'` (Suomi-NPP), `'N20'` (NOAA-20), `'N21'` (NOAA-21) |
| `instrument` | `string` | No | Sensor instrument name: `'MODIS'` or `'VIIRS'` |
| `confidence` | `string` / `int` | No | Raw sensor confidence string or percentage (0–100) |
| `version` | `string` | No | FIRMS collection processing version (e.g. `'6.1'`, `'2.0NRT'`) |
| `bright_t31` | `float64` | **Yes** | Channel 31 brightness temperature in Kelvin (null for VIIRS) |
| `frp` | `float64` | No | Fire Radiative Power in Megawatts (MW) |
| `daynight` | `string` | No | Observation period: `'D'` (Daytime) or `'N'` (Nighttime) |
| `bright_ti4` | `float64` | **Yes** | VIIRS I-4 channel brightness temperature in Kelvin (null for MODIS) |
| `bright_ti5` | `float64` | **Yes** | VIIRS I-5 channel brightness temperature in Kelvin (null for MODIS) |
| `confidence_class` | `string` | No | Cleaned binary confidence: `'nominal'` or `'high'` (lows discarded) |
| `region` | `string` | No | Study region identifier: `'western_ghats_karnataka'`, `'palisades_la'`, `'punjab_haryana'` |
| `cell_id_025` | `string` | No | 0.25° spatial grid cell identifier (`"lat_lng"`) |
| `cell_id_005` | `string` | No | 0.05° spatial grid cell identifier |
| `cell_id_001` | `string` | No | 0.01° sub-kilometer spatial grid cell identifier |
| `acq_datetime_utc` | `string` | No | Normalized ISO-8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`) |
| `year` | `int32` | No | Observation calendar year (2000–2026) |

---

## 2. API Endpoints

### 2.1 `GET /api/v1/summary`

Returns top-level key performance indicators, sensor counts, and annual/monthly aggregations.

#### Query Parameters:
- `region` (optional, string): Filter by region (`western_ghats_karnataka`, `palisades_la`, `punjab_haryana`). Default: all active regions.
- `start_date` (optional, string): Start date in `YYYY-MM-DD`.
- `end_date` (optional, string): End date in `YYYY-MM-DD`.
- `sensor` (optional, string): `'MODIS'`, `'VIIRS'`, or `'Both'`.
- `satellite` (optional, string): `'Terra'`, `'Aqua'`, `'N'`, `'N20'`, `'N21'`.
- `confidence` (optional, string): `'nominal'` or `'high'`.

#### TypeScript Response Type:
```typescript
interface SummaryResponse {
  generated_at_utc: string;
  source: string;
  total_detections: number;
  regions: Record<string, {
    label: string;
    total_detections: number;
    date_start: string;
    date_end: string;
    year_start: number;
    year_end: number;
    unique_detection_days: number;
    unique_grid_cells: number;
    frp: {
      available_records: number;
      mean: number | null;
      median: number | null;
      maximum: number | null;
    };
    yearly_trend: Array<{ year: number; detections: number }>;
    monthly_distribution: Array<{ month: number; detections: number }>;
    sensor_counts: Array<{ sensor: string; detections: number }>;
    satellite_counts: Array<{ satellite: "Terra" | "Aqua" | "N" | "N20" | "N21"; detections: number }>;
    daynight_counts: Array<{ period: "Day" | "Night"; detections: number }>;
    confidence_counts: Array<{ confidence: "Nominal" | "High"; detections: number }>;
  }>;
}
```

#### Example Response:
```json
{
  "generated_at_utc": "2026-11-15T10:00:00Z",
  "source": "NASA FIRMS Harmonized Pipeline",
  "total_detections": 2872017,
  "regions": {
    "western_ghats_karnataka": {
      "label": "Western Ghats, Karnataka",
      "total_detections": 133605,
      "date_start": "2000-11-11T05:41:00Z",
      "date_end": "2026-11-14T09:09:00Z",
      "year_start": 2000,
      "year_end": 2026,
      "unique_detection_days": 4616,
      "unique_grid_cells": 92,
      "frp": {
        "available_records": 133605,
        "mean": 7.26,
        "median": 4.71,
        "maximum": 414.7
      },
      "yearly_trend": [
        { "year": 2000, "detections": 28 },
        { "year": 2024, "detections": 12842 }
      ],
      "monthly_distribution": [
        { "month": 1, "detections": 18450 },
        { "month": 2, "detections": 39120 }
      ],
      "sensor_counts": [
        { "sensor": "MODIS", "detections": 18131 },
        { "sensor": "VIIRS", "detections": 115474 }
      ],
      "satellite_counts": [
        { "satellite": "Terra", "detections": 7240 },
        { "satellite": "Aqua", "detections": 10891 },
        { "satellite": "N", "detections": 44228 },
        { "satellite": "N20", "detections": 41208 },
        { "satellite": "N21", "detections": 30038 }
      ],
      "daynight_counts": [
        { "period": "Day", "detections": 96195 },
        { "period": "Night", "detections": 37410 }
      ],
      "confidence_counts": [
        { "confidence": "Nominal", "detections": 102400 },
        { "confidence": "High", "detections": 31205 }
      ]
    }
  }
}
```

---

### 2.2 `GET /api/v1/grid`

Returns spatially aggregated grid cells for visualization on interactive Leaflet maps.

> [!NOTE]
> For large geographic zones like Punjab & Haryana (>2.7 million raw rows), the backend MUST perform in-database or Parquet spatial grouping and return aggregated cell summaries only. The frontend never downloads multi-million raw rows directly.

#### Query Parameters:
- `region` (required, string): `'western_ghats_karnataka'`, `'palisades_la'`, `'punjab_haryana'`.
- `resolution` (optional, float): Grid resolution in degrees (`0.25`, `0.05`, `0.01`). Default: `0.25`.
- `satellite` (optional, string): `'Terra'`, `'Aqua'`, `'N'`, `'N20'`, `'N21'`.
- `confidence` (optional, string): `'nominal'` or `'high'`.

#### TypeScript Response Type:
```typescript
interface GridResponse {
  generated_at_utc: string;
  cell_size_degrees: number;
  aggregation: string;
  regions: Record<string, Array<{
    region: string;
    cell_id: string;
    latitude: number;
    longitude: number;
    detections: number;
    mean_frp: number | null;
    max_frp: number | null;
    night_detections: number;
    modis_detections: number;
    viirs_detections: number;
    first_date: string;
    last_date: string;
  }>>;
}
```

#### Example Response:
```json
{
  "generated_at_utc": "2026-11-15T10:00:00Z",
  "cell_size_degrees": 0.25,
  "aggregation": "spatial_cell_sum",
  "regions": {
    "western_ghats_karnataka": [
      {
        "region": "western_ghats_karnataka",
        "cell_id": "14.25_74.75",
        "latitude": 14.3821,
        "longitude": 74.8429,
        "detections": 4210,
        "mean_frp": 8.45,
        "max_frp": 142.3,
        "night_detections": 1120,
        "modis_detections": 620,
        "viirs_detections": 3590,
        "first_date": "2001-02-14",
        "last_date": "2026-03-29"
      }
    ]
  }
}
```

---

### 2.3 `GET /api/v1/harmonization/summary`

Returns model regression parameters, co-observation calibration results, and multi-decade harmonized timeseries.

#### TypeScript Response Type:
```typescript
interface HarmonizationSummaryResponse {
  metadata: {
    region: string;
    count_model: string;
    frp_method: string;
    n_rows: number;
    created_at_utc: string;
    r_squared?: number | null;
  };
  aggregated_metrics: {
    rows_by_source: {
      observed: number;
      estimated: number;
    };
    numeric_columns_by_source: {
      observed: {
        n_detections_VIIRS: { count: number; mean: number; min: number; max: number };
        mean_frp_VIIRS: { count: number; mean: number; min: number; max: number };
      };
      estimated: {
        predicted_n_detections_VIIRS: { count: number; mean: number; min: number; max: number };
        calibrated_frp: { count: number; mean: number; min: number; max: number };
      };
    };
    provided: {
      timeseries: {
        yearly: Array<{
          period: string;
          observed_modis_detections: number;
          observed_viirs_detections: number;
          estimated_viirs_detections: number | null;
          observed_modis_frp: number | null;
          observed_viirs_frp: number | null;
          estimated_calibrated_frp: number | null;
        }>;
        monthly: Array<{
          period: string;
          observed_modis_detections: number;
          observed_viirs_detections: number;
          estimated_viirs_detections: number | null;
          observed_modis_frp: number | null;
          observed_viirs_frp: number | null;
          estimated_calibrated_frp: number | null;
        }>;
      };
    };
  };
}
```

---

## 3. Defensive Parsing Rules Implemented on Frontend

1. **Number Coercion:** All numbers (e.g. `count`, `frp`, `detections`) are coerced through `safeNumber()` and `safeInt()`. Numbers serialized as strings (e.g. `"45.2"`) are parsed safely; `NaN`, `null`, or undefined values fall back to `0` or explicit `null`.
2. **Missing Properties & Null Checks:** All source groups (`metadata`, `aggregated_metrics`, `rows_by_source`) verify structure with `isRecord()`. If absent, defaults are substituted rather than triggering `TypeError`.
3. **Date String Normalization:** Timestamps are formatted defensively to handle ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`), UTC strings, or date-only (`YYYY-MM-DD`) formats.
4. **Large Payload Safeguards:** The frontend fetches pre-computed cell aggregations or timeseries; endpoints for raw data points MUST accept pagination (`limit`, `offset`) and enforce a maximum slice size of 5,000 points.
