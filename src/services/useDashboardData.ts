import { useState, useEffect, useCallback } from "react";
import {
  fetchDashboardSummary,
  fetchMapCells,
  fetchHarmonizedSummary,
  fetchYearlyTrends,
  fetchRegionComparison,
  type DashboardResponse,
  type MapResponse,
  type HarmonizedSummary,
  type YearlyTrendRow,
  type RegionComparisonRow,
  IS_STATIC_MODE,
} from "./apiClient";

export interface DashboardDataState {
  dashboard: DashboardResponse | null;
  map: MapResponse | null;
  harmonizedSummary: HarmonizedSummary | null;
  yearlyTrends: YearlyTrendRow[];
  regionComparison: RegionComparisonRow[];
  loading: boolean;
  error: string | null;
  isStatic: boolean;
  reload: () => Promise<void>;
}

export function useDashboardData(): DashboardDataState {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [map, setMap] = useState<MapResponse | null>(null);
  const [harmonizedSummary, setHarmonizedSummary] = useState<HarmonizedSummary | null>(null);
  const [yearlyTrends, setYearlyTrends] = useState<YearlyTrendRow[]>([]);
  const [regionComparison, setRegionComparison] = useState<RegionComparisonRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [dashRes, mapRes, harmRes, trendsRes, compRes] = await Promise.all([
        fetchDashboardSummary().catch((e) => {
          console.warn("fetchDashboardSummary failed:", e);
          return null;
        }),
        fetchMapCells().catch((e) => {
          console.warn("fetchMapCells failed:", e);
          return null;
        }),
        fetchHarmonizedSummary().catch((e) => {
          console.warn("fetchHarmonizedSummary failed:", e);
          return null;
        }),
        fetchYearlyTrends().catch((e) => {
          console.warn("fetchYearlyTrends failed:", e);
          return [];
        }),
        fetchRegionComparison().catch((e) => {
          console.warn("fetchRegionComparison failed:", e);
          return [];
        }),
      ]);

      if (!dashRes && !mapRes && !harmRes) {
        throw new Error("Unable to connect to FireTrace data sources or static assets.");
      }

      setDashboard(dashRes);
      setMap(mapRes);
      setHarmonizedSummary(harmRes);
      setYearlyTrends(trendsRes);
      setRegionComparison(compRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load FireTrace datasets.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return {
    dashboard,
    map,
    harmonizedSummary,
    yearlyTrends,
    regionComparison,
    loading,
    error,
    isStatic: IS_STATIC_MODE,
    reload: loadData,
  };
}
