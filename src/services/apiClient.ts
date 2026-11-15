import type { MapCell } from "../data";

export type RegionKey = "western_ghats_karnataka" | "palisades_la" | "punjab_haryana";

export type RegionStats = {
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
  yearly_trend: { year: number; detections: number }[];
  monthly_distribution: { month: number; detections: number }[];
  sensor_counts: { sensor: string; detections: number }[];
  satellite_counts: { satellite: string; detections: number }[];
  daynight_counts: { period: string; detections: number }[];
  confidence_counts: { confidence: string; detections: number }[];
  vegetation_counts: { vegetation_fire: boolean; detections: number }[];
};

export type DashboardResponse = {
  generated_at_utc: string;
  source: string;
  data_type: string;
  cell_size_degrees: number;
  total_detections: number;
  regions: Record<string, RegionStats>;
};

export type MapResponse = {
  generated_at_utc: string;
  cell_size_degrees: number;
  aggregation: string;
  regions: Record<string, MapCell[]>;
};

export type NumericAggregate = {
  count: number;
  mean: number;
  min: number;
  max: number;
};

export type HarmonizedMetricSeries = {
  period: string;
  observedModisDetections: number;
  observedViirsDetections: number;
  estimatedViirsDetections: number | null;
  observedModisFrp: number | null;
  observedViirsFrp: number | null;
  estimatedCalibratedFrp: number | null;
};

export type HarmonizedSummary = {
  region: string;
  createdAt: string;
  countModel: string;
  frpMethod: string;
  rows: {
    observed: number;
    estimated: number;
    total: number;
  };
  metrics: {
    observed: {
      viirsDetections: NumericAggregate;
      meanFrp: NumericAggregate;
    };
    estimated: {
      predictedViirsDetections: NumericAggregate;
      calibratedFrp: NumericAggregate;
    };
  };
  timeseries: {
    yearly: HarmonizedMetricSeries[];
    monthly: HarmonizedMetricSeries[];
  };
};

export type YearlyTrendRow = {
  region: string;
  year: number;
  sensor: string;
  detections: number;
  active_days: number;
  frp_sum: number | null;
  is_partial_year: boolean;
};

export type RegionComparisonRow = {
  region: string;
  cell_size: number;
  rows: number;
  modis_cells_2012_2026: number;
  viirs_cells_2012_2026: number;
  cells_seen_by_both: number;
  modis_cell_days: number;
  viirs_also: number;
  viirs_only: number;
  modis_only: number;
  share_modis_seen_by_viirs: number;
};

export interface ApiFilterParams {
  region?: string;
  start_date?: string;
  end_date?: string;
  sensor?: string;
  satellite?: string;
  confidence?: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";
export const DATA_SOURCE = ((import.meta.env.VITE_DATA_SOURCE as string | undefined) || "static").toLowerCase();
export const IS_STATIC_MODE = DATA_SOURCE !== "api";

function safeNumber(val: unknown, fallback = 0): number {
  if (typeof val === "number" && Number.isFinite(val)) return val;
  if (typeof val === "string") {
    const parsed = parseFloat(val);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function safeInt(val: unknown, fallback = 0): number {
  const num = safeNumber(val, fallback);
  return Math.round(num);
}

function safeString(val: unknown, fallback = ""): string {
  if (typeof val === "string") return val;
  if (val !== null && val !== undefined) return String(val);
  return fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readAggregate(value: unknown, name: string): NumericAggregate {
  if (!isRecord(value)) {
    return { count: 0, mean: 0, min: 0, max: 0 };
  }
  return {
    count: safeInt(value.count, 0),
    mean: safeNumber(value.mean, 0),
    min: safeNumber(value.min, 0),
    max: safeNumber(value.max, 0),
  };
}

function readMetricSeries(value: unknown): HarmonizedMetricSeries[] {
  if (!Array.isArray(value)) return [];
  return value.map((row) => {
    if (!isRecord(row)) {
      return {
        period: "",
        observedModisDetections: 0,
        observedViirsDetections: 0,
        estimatedViirsDetections: null,
        observedModisFrp: null,
        observedViirsFrp: null,
        estimatedCalibratedFrp: null,
      };
    }
    return {
      period: safeString(row.period),
      observedModisDetections: safeNumber(row.observed_modis_detections, 0),
      observedViirsDetections: safeNumber(row.observed_viirs_detections, 0),
      estimatedViirsDetections:
        row.estimated_viirs_detections !== null && row.estimated_viirs_detections !== undefined
          ? safeNumber(row.estimated_viirs_detections)
          : null,
      observedModisFrp:
        row.observed_modis_frp !== null && row.observed_modis_frp !== undefined
          ? safeNumber(row.observed_modis_frp)
          : null,
      observedViirsFrp:
        row.observed_viirs_frp !== null && row.observed_viirs_frp !== undefined
          ? safeNumber(row.observed_viirs_frp)
          : null,
      estimatedCalibratedFrp:
        row.estimated_calibrated_frp !== null && row.estimated_calibrated_frp !== undefined
          ? safeNumber(row.estimated_calibrated_frp)
          : null,
    };
  });
}

export function parseHarmonizedSummary(value: unknown): HarmonizedSummary {
  if (!isRecord(value) || !isRecord(value.metadata) || !isRecord(value.aggregated_metrics)) {
    throw new Error("Invalid harmonized summary: missing metadata or aggregated metrics.");
  }

  const metadata = value.metadata;
  const metrics = value.aggregated_metrics;
  const rowsBySource = isRecord(metrics.rows_by_source) ? metrics.rows_by_source : {};
  const metricsBySource = isRecord(metrics.numeric_columns_by_source) ? metrics.numeric_columns_by_source : {};
  const provided = isRecord(metrics.provided) ? metrics.provided : {};
  const timeseries = isRecord(provided.timeseries) ? provided.timeseries : {};

  const observedRows = safeInt(rowsBySource.observed, 0);
  const estimatedRows = safeInt(rowsBySource.estimated, 0);
  const totalRows = safeInt(metadata.n_rows, observedRows + estimatedRows);

  const observed = isRecord(metricsBySource.observed) ? metricsBySource.observed : {};
  const estimated = isRecord(metricsBySource.estimated) ? metricsBySource.estimated : {};

  return {
    region: safeString(metadata.region, "unknown"),
    createdAt: safeString(metadata.created_at_utc, new Date().toISOString()),
    countModel: safeString(metadata.count_model, "negativebinomial"),
    frpMethod: safeString(metadata.frp_method, "log_linear"),
    rows: {
      observed: observedRows,
      estimated: estimatedRows,
      total: totalRows,
    },
    metrics: {
      observed: {
        viirsDetections: readAggregate(observed.n_detections_VIIRS, "observed VIIRS detections"),
        meanFrp: readAggregate(observed.mean_frp_VIIRS, "observed VIIRS FRP"),
      },
      estimated: {
        predictedViirsDetections: readAggregate(
          estimated.predicted_n_detections_VIIRS,
          "estimated VIIRS detections",
        ),
        calibratedFrp: readAggregate(estimated.calibrated_frp, "estimated calibrated FRP"),
      },
    },
    timeseries: {
      yearly: readMetricSeries(timeseries.yearly),
      monthly: readMetricSeries(timeseries.monthly),
    },
  };
}

export async function fetchDashboardSummary(params?: ApiFilterParams): Promise<DashboardResponse> {
  if (!IS_STATIC_MODE && API_BASE_URL) {
    const q = new URLSearchParams();
    if (params?.region) q.set("region", params.region);
    if (params?.start_date) q.set("start_date", params.start_date);
    if (params?.end_date) q.set("end_date", params.end_date);
    if (params?.satellite) q.set("satellite", params.satellite);
    if (params?.confidence) q.set("confidence", params.confidence);

    const res = await fetch(`${API_BASE_URL}/api/v1/summary?${q.toString()}`);
    if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
    return res.json();
  }

  const res = await fetch("/data/dashboard.json");
  if (!res.ok) throw new Error("Unable to load /data/dashboard.json static asset.");
  return res.json();
}

export async function fetchMapCells(params?: ApiFilterParams): Promise<MapResponse> {
  if (!IS_STATIC_MODE && API_BASE_URL) {
    const q = new URLSearchParams();
    if (params?.region) q.set("region", params.region);
    if (params?.satellite) q.set("satellite", params.satellite);
    if (params?.confidence) q.set("confidence", params.confidence);

    const res = await fetch(`${API_BASE_URL}/api/v1/grid?${q.toString()}`);
    if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
    return res.json();
  }

  const res = await fetch("/data/map.json");
  if (!res.ok) throw new Error("Unable to load /data/map.json static asset.");
  return res.json();
}

export async function fetchHarmonizedSummary(): Promise<HarmonizedSummary> {
  if (!IS_STATIC_MODE && API_BASE_URL) {
    const res = await fetch(`${API_BASE_URL}/api/v1/harmonization/summary`);
    if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
    const json = await res.json();
    return parseHarmonizedSummary(json);
  }

  const res = await fetch("/data/harmonized_summary.json");
  if (!res.ok) throw new Error("Unable to load /data/harmonized_summary.json static asset.");
  const json = await res.json();
  return parseHarmonizedSummary(json);
}

export async function fetchYearlyTrends(): Promise<YearlyTrendRow[]> {
  const res = await fetch("/data/yearly_trends.csv");
  if (!res.ok) throw new Error("Unable to load /data/yearly_trends.csv");
  const text = await res.text();
  const lines = text.trim().split("\n");
  const rows: YearlyTrendRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",").map((s) => s.trim());
    if (parts.length >= 7) {
      rows.push({
        region: safeString(parts[0]),
        year: safeInt(parts[1]),
        sensor: safeString(parts[2]),
        detections: safeInt(parts[3]),
        active_days: safeInt(parts[4]),
        frp_sum: parts[5] && parts[5] !== "None" ? safeNumber(parts[5]) : null,
        is_partial_year: parts[6].toLowerCase() === "true",
      });
    }
  }
  return rows;
}

export async function fetchRegionComparison(): Promise<RegionComparisonRow[]> {
  const res = await fetch("/data/region_comparison.csv");
  if (!res.ok) throw new Error("Unable to load /data/region_comparison.csv");
  const text = await res.text();
  const lines = text.trim().split("\n");
  const rows: RegionComparisonRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",").map((s) => s.trim());
    if (parts.length >= 11) {
      rows.push({
        region: safeString(parts[0]),
        cell_size: safeNumber(parts[1]),
        rows: safeInt(parts[2]),
        modis_cells_2012_2026: safeInt(parts[3]),
        viirs_cells_2012_2026: safeInt(parts[4]),
        cells_seen_by_both: safeInt(parts[5]),
        modis_cell_days: safeInt(parts[6]),
        viirs_also: safeInt(parts[7]),
        viirs_only: safeInt(parts[8]),
        modis_only: safeInt(parts[9]),
        share_modis_seen_by_viirs: safeNumber(parts[10]),
      });
    }
  }
  return rows;
}
