import type { MapCell } from "./data";

export type RegionKey = "western_ghats_karnataka" | "palisades_la";

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

type DashboardResponse = {
  generated_at_utc: string;
  source: string;
  data_type: string;
  cell_size_degrees: number;
  total_detections: number;
  regions: Record<RegionKey, RegionStats>;
};

type MapResponse = {
  generated_at_utc: string;
  cell_size_degrees: number;
  aggregation: string;
  regions: Record<RegionKey, MapCell[]>;
};

type NumericAggregate = {
  count: number;
  mean: number;
  min: number;
  max: number;
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

export type HarmonizedMetricSeries = {
  period: string;
  observedModisDetections: number;
  observedViirsDetections: number;
  estimatedViirsDetections: number | null;
  observedModisFrp: number | null;
  observedViirsFrp: number | null;
  estimatedCalibratedFrp: number | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readAggregate(value: unknown, name: string): NumericAggregate {
  if (!isRecord(value)) {
    throw new Error(`Invalid harmonized summary: missing ${name} aggregate.`);
  }

  const { count, mean, min, max } = value;
  if (
    !Number.isInteger(count) ||
    (count as number) < 0 ||
    typeof mean !== "number" ||
    !Number.isFinite(mean) ||
    typeof min !== "number" ||
    !Number.isFinite(min) ||
    typeof max !== "number" ||
    !Number.isFinite(max)
  ) {
    throw new Error(`Invalid harmonized summary: malformed ${name} aggregate.`);
  }

  return { count: count as number, mean, min, max };
}

function readMetricSeries(value: unknown, name: string): HarmonizedMetricSeries[] {
  if (!Array.isArray(value)) {
    throw new Error(`Invalid harmonized summary: missing ${name} time series.`);
  }

  return value.map((row, index) => {
    if (
      !isRecord(row) ||
      typeof row.period !== "string" ||
      !row.period ||
      typeof row.observed_modis_detections !== "number" ||
      !Number.isFinite(row.observed_modis_detections) ||
      typeof row.observed_viirs_detections !== "number" ||
      !Number.isFinite(row.observed_viirs_detections)
    ) {
      throw new Error(`Invalid harmonized summary: malformed ${name} row ${index}.`);
    }

    const optionalMetrics = [
      "estimated_viirs_detections",
      "observed_modis_frp",
      "observed_viirs_frp",
      "estimated_calibrated_frp",
    ] as const;
    for (const key of optionalMetrics) {
      const metric = row[key];
      if (metric !== null && (typeof metric !== "number" || !Number.isFinite(metric))) {
        throw new Error(`Invalid harmonized summary: malformed ${name} row ${index} ${key}.`);
      }
    }

    return {
      period: row.period,
      observedModisDetections: row.observed_modis_detections,
      observedViirsDetections: row.observed_viirs_detections,
      estimatedViirsDetections: row.estimated_viirs_detections as number | null,
      observedModisFrp: row.observed_modis_frp as number | null,
      observedViirsFrp: row.observed_viirs_frp as number | null,
      estimatedCalibratedFrp: row.estimated_calibrated_frp as number | null,
    };
  });
}

function parseHarmonizedSummary(value: unknown): HarmonizedSummary {
  if (!isRecord(value) || !isRecord(value.metadata) || !isRecord(value.aggregated_metrics)) {
    throw new Error("Invalid harmonized summary: missing metadata or aggregated metrics.");
  }

  const metadata = value.metadata;
  const metrics = value.aggregated_metrics;
  const rowsBySource = metrics.rows_by_source;
  const metricsBySource = metrics.numeric_columns_by_source;
  const provided = metrics.provided;
  const timeseries = isRecord(provided) ? provided.timeseries : undefined;
  if (
    typeof metadata.region !== "string" ||
    typeof metadata.created_at_utc !== "string" ||
    typeof metadata.count_model !== "string" ||
    typeof metadata.frp_method !== "string" ||
    !Number.isInteger(metadata.n_rows) ||
    (metadata.n_rows as number) < 0 ||
    !isRecord(rowsBySource) ||
    !isRecord(metricsBySource) ||
    !isRecord(metricsBySource.observed) ||
    !isRecord(metricsBySource.estimated)
  ) {
    throw new Error("Invalid harmonized summary: malformed metadata or source groups.");
  }
  if (!isRecord(timeseries)) {
    throw new Error("Invalid harmonized summary: missing observed/estimated time series.");
  }

  const observedRows = rowsBySource.observed;
  const estimatedRows = rowsBySource.estimated;
  if (
    !Number.isInteger(observedRows) ||
    (observedRows as number) < 0 ||
    !Number.isInteger(estimatedRows) ||
    (estimatedRows as number) < 0 ||
    (observedRows as number) + (estimatedRows as number) !== metadata.n_rows
  ) {
    throw new Error("Invalid harmonized summary: observed and estimated row counts do not match.");
  }

  const observed = metricsBySource.observed;
  const estimated = metricsBySource.estimated;
  const observedViirsDetections = readAggregate(
    observed.n_detections_VIIRS,
    "observed VIIRS detections",
  );
  const estimatedViirsDetections = readAggregate(
    estimated.predicted_n_detections_VIIRS,
    "estimated VIIRS detections",
  );
  if (
    observedViirsDetections.count !== observedRows ||
    estimatedViirsDetections.count !== estimatedRows
  ) {
    throw new Error("Invalid harmonized summary: source metrics do not match source row counts.");
  }

  return {
    region: metadata.region,
    createdAt: metadata.created_at_utc,
    countModel: metadata.count_model,
    frpMethod: metadata.frp_method,
    rows: {
      observed: observedRows as number,
      estimated: estimatedRows as number,
      total: metadata.n_rows as number,
    },
    metrics: {
      observed: {
        viirsDetections: observedViirsDetections,
        meanFrp: readAggregate(observed.mean_frp_VIIRS, "observed VIIRS FRP"),
      },
      estimated: {
        predictedViirsDetections: estimatedViirsDetections,
        calibratedFrp: readAggregate(estimated.calibrated_frp, "estimated calibrated FRP"),
      },
    },
    timeseries: {
      yearly: readMetricSeries(timeseries.yearly, "yearly"),
      monthly: readMetricSeries(timeseries.monthly, "monthly"),
    },
  };
}

export async function loadDashboardData() {
  const [dashboardResponse, mapResponse, harmonizedResponse] = await Promise.all([
    fetch("/data/dashboard.json"),
    fetch("/data/map.json"),
    fetch("/data/harmonized_summary.json"),
  ]);

  if (!dashboardResponse.ok || !mapResponse.ok || !harmonizedResponse.ok) {
    throw new Error("Unable to load FireTrace project data.");
  }

  const [dashboard, map, harmonizedSummary] = await Promise.all([
    dashboardResponse.json() as Promise<DashboardResponse>,
    mapResponse.json() as Promise<MapResponse>,
    harmonizedResponse.json().then(parseHarmonizedSummary),
  ]);

  return { dashboard, map, harmonizedSummary };
}