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

export async function loadDashboardData() {
  const [dashboardResponse, mapResponse] = await Promise.all([
    fetch("/data/dashboard.json"),
    fetch("/data/map.json"),
  ]);

  if (!dashboardResponse.ok || !mapResponse.ok) {
    throw new Error("Unable to load FireTrace project data.");
  }

  const dashboard: DashboardResponse = await dashboardResponse.json();
  const map: MapResponse = await mapResponse.json();

  return { dashboard, map };
}