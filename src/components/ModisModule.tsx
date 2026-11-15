import { useMemo } from "react";
import { Flame, CalendarDays, Target, Orbit, Info, AlertTriangle } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, ChartTooltip, LoadingSkeleton, DataUnavailable, Status } from "./UI";
import { useFilters } from "../context/FiltersContext";
import type { DashboardResponse, YearlyTrendRow, RegionComparisonRow } from "../services/apiClient";
import { VERIFIED_TOTALS, PIPELINE_STATIC_BADGE } from "../config/verifiedTotals";

interface ModisModuleProps {
  dashboard?: DashboardResponse | null;
  yearlyTrends?: YearlyTrendRow[];
  regionComparison?: RegionComparisonRow[];
  loading?: boolean;
  onReload?: () => void;
}

export function ModisModule({ dashboard, yearlyTrends = [], regionComparison = [], loading, onReload }: ModisModuleProps) {
  const { filters, currentRegionMeta } = useFilters();

  const regionKey = useMemo(() => {
    if (filters.region === "palisades_la") return "palisades";
    if (filters.region === "punjab_haryana") return "punjab_haryana";
    return "western_ghats_karnataka";
  }, [filters.region]);

  const modisTrend = useMemo(() => {
    let minYear = 2000;
    let maxYear = 2026;
    if (filters.dateRange === "2000-2011") {
      minYear = 2000;
      maxYear = 2011;
    } else if (filters.dateRange === "2012-2024") {
      minYear = 2012;
      maxYear = 2024;
    } else if (filters.dateRange === "2024-2026") {
      minYear = 2024;
      maxYear = 2026;
    }

    const rows = yearlyTrends.filter(
      (r) =>
        r.sensor === "MODIS" &&
        (filters.region === "all" || r.region === regionKey) &&
        r.year >= minYear &&
        r.year <= maxYear
    );
    return rows.sort((a, b) => a.year - b.year);
  }, [yearlyTrends, filters.region, regionKey, filters.dateRange]);

  const chartSum = useMemo(() => {
    return modisTrend.reduce((sum, r) => sum + r.detections, 0);
  }, [modisTrend]);

  const isViirsSatelliteSelected =
    filters.satellite === "VIIRS" ||
    filters.satellite === "N" ||
    filters.satellite === "N20" ||
    filters.satellite === "N21";

  const modisStats = useMemo(() => {
    let totalDetections = VERIFIED_TOTALS.western_ghats_karnataka.modis;
    let source = VERIFIED_TOTALS.western_ghats_karnataka.source;

    if (filters.region === "palisades_la") {
      totalDetections = VERIFIED_TOTALS.palisades_la.modis;
      source = VERIFIED_TOTALS.palisades_la.source;
    } else if (filters.region === "punjab_haryana") {
      totalDetections = VERIFIED_TOTALS.punjab_haryana.modis;
      source = VERIFIED_TOTALS.punjab_haryana.source;
    } else if (filters.region === "nsw_victoria_au") {
      totalDetections = VERIFIED_TOTALS.nsw_victoria_au.modis;
      source = VERIFIED_TOTALS.nsw_victoria_au.source;
    } else if (filters.region === "all") {
      totalDetections = VERIFIED_TOTALS.all.modis;
      source = VERIFIED_TOTALS.all.source;
    }

    // Single-satellite MODIS breakdown if Terra or Aqua selected
    if (filters.satellite === "Terra" || filters.satellite === "Aqua") {
      const satCounts = dashboard?.regions[filters.region === "palisades_la" ? "palisades_la" : "western_ghats_karnataka"]?.satellite_counts;
      const found = satCounts?.find((s) => s.satellite === filters.satellite);
      if (found) {
        totalDetections = found.detections;
        source = `public/data/dashboard.json (${filters.satellite} count)`;
      }
    } else if (filters.dateRange !== "all") {
      totalDetections = chartSum;
      source = `public/data/yearly_trends.csv (${filters.dateRange} filtered sum)`;
    }

    return {
      totalDetections,
      source,
      satellites: filters.satellite === "Terra" ? "Terra (AM 10:30)" : filters.satellite === "Aqua" ? "Aqua (PM 13:30)" : "Terra (AM 10:30) & Aqua (PM 13:30)",
      nominalResolution: "1,000 m (1 km)",
      temporalSpan: filters.dateRange === "2000-2011" ? "2000 — 2011 (12 yrs)" : filters.dateRange === "2012-2024" ? "2012 — 2024 (13 yrs)" : filters.dateRange === "2024-2026" ? "2024 — 2026 (3 yrs)" : "2000 — 2026 (26 yrs)",
    };
  }, [filters.region, filters.satellite, filters.dateRange, chartSum, dashboard]);

  if (loading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton lines={4} />
      </div>
    );
  }

  if (!yearlyTrends || yearlyTrends.length === 0) {
    return (
      <div className="space-y-6">
        <DataUnavailable
          title="Trend Data Unavailable"
          message="Yearly trends dataset (public/data/yearly_trends.csv) could not be loaded."
          onRetry={onReload}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#233142]">
        <div>
          <span className="text-xs uppercase tracking-wider text-[#ff7547] font-semibold">
            NASA Earth Observing System (EOS)
          </span>
          <h2 className="text-2xl font-bold text-white mt-1">MODIS Wildfire Observations</h2>
          <p className="text-sm text-[#8e9eb3] mt-1">
            Moderate Resolution Imaging Spectroradiometer aboard NASA Terra and Aqua satellites.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Status type="verified">24+ Year Baseline (2000–2026)</Status>
        </div>
      </div>

      {filters.region === "nsw_victoria_au" && (
        <div className="bg-[#141d28] border border-[#233142] rounded-lg p-8 text-center space-y-3">
          <AlertTriangle size={36} className="mx-auto text-[#ffb84d]" />
          <h3 className="text-lg font-bold text-white">NSW & Victoria (Australia)</h3>
          <p className="text-sm text-[#8e9eb3] max-w-md mx-auto">
            Data not available yet (pipeline download pending). MODIS data for Southeast Australia is not ingested in the current snapshot.
          </p>
        </div>
      )}

      {isViirsSatelliteSelected && (
        <div className="bg-[#141d28] border border-[#ff7547]/40 rounded-lg p-3 flex items-start gap-3">
          <Info size={18} className="text-[#ff7547] shrink-0 mt-0.5" />
          <div className="text-xs text-[#d8e2ef] space-y-0.5">
            <strong className="text-[#ff7547]">Filter Notice: MODIS Module Scope</strong>
            <p className="text-[#8e9eb3]">
              MODIS module displays Terra and Aqua observations. Selected VIIRS filter (<code>{filters.satellite}</code>) is disabled on this view; switch to the VIIRS module for 375m observations.
            </p>
          </div>
        </div>
      )}

      {filters.confidence === "high" && (
        <div className="bg-[#141d28] border border-[#233142] rounded-lg p-3 flex items-start gap-3">
          <Info size={18} className="text-[#61d9fa] shrink-0 mt-0.5" />
          <div className="text-xs text-[#d8e2ef] space-y-0.5">
            <strong className="text-[#61d9fa]">Confidence Filter Status</strong>
            <p className="text-[#8e9eb3]">
              MODIS yearly trend is pre-aggregated across all cleaned confidence levels (Nominal + High). Low-confidence noise was removed during pipeline cleaning; separate confidence breakdown is disabled on this timeseries.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="kpi-card">
          <div className="kpi-top">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs text-[#8e9eb3]">MODIS Detections</span>
              <span className="text-[10px] bg-[#233142] text-[#8e9eb3] px-1.5 py-0.5 rounded font-mono font-normal">
                {PIPELINE_STATIC_BADGE}
              </span>
            </div>
            <Flame size={17} className="text-[#ff7547]" />
          </div>
          <strong className="text-2xl text-white">{modisStats.totalDetections.toLocaleString()}</strong>
          <small className="text-xs text-[#8e9eb3] truncate" title={modisStats.source}>
            Source: {modisStats.source}
          </small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Observation Horizon</span>
            <CalendarDays size={17} className="text-[#61d9fa]" />
          </div>
          <strong className="text-2xl text-white">{modisStats.temporalSpan}</strong>
          <small className="text-xs text-[#8e9eb3]">Unbroken climate record</small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Ground Resolution</span>
            <Target size={17} className="text-[#ffb84d]" />
          </div>
          <strong className="text-2xl text-white">{modisStats.nominalResolution}</strong>
          <small className="text-xs text-[#8e9eb3]">Nadir pixel footprint</small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Constellation Platforms</span>
            <Orbit size={17} className="text-[#36c9f4]" />
          </div>
          <strong className="text-sm text-white mt-1">{modisStats.satellites}</strong>
          <small className="text-xs text-[#8e9eb3]">Sun-synchronous polar orbits</small>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card
          className="lg:col-span-2"
          title="MODIS Annual Fire Hotspot Detections"
          eyebrow={`Historical timeseries (2000–2026) · ${currentRegionMeta.label}`}
        >
          {modisTrend.length > 0 ? (
            <div style={{ height: 300 }} className="mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modisTrend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid stroke="#233142" vertical={false} />
                  <XAxis dataKey="year" tick={{ fill: "#77879b", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#77879b", fontSize: 11 }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="detections" name="MODIS Detections" fill="#ff7547" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <DataUnavailable message="No yearly MODIS observations found for this region." />
          )}
        </Card>

        <Card title="Sensor Specifications" eyebrow="Technical Benchmark">
          <div className="space-y-3 text-xs text-[#8e9eb3] mt-2">
            <div className="p-3 bg-[#182330] rounded border border-[#233142]">
              <strong className="text-[#d8e2ef] block text-sm mb-1">Terra (EOS AM-1)</strong>
              <span>Launched Dec 1999 · Descending node (10:30 AM equator crossing)</span>
            </div>
            <div className="p-3 bg-[#182330] rounded border border-[#233142]">
              <strong className="text-[#d8e2ef] block text-sm mb-1">Aqua (EOS PM-1)</strong>
              <span>Launched May 2002 · Ascending node (1:30 PM equator crossing)</span>
            </div>
            <div className="p-3 bg-[#182330] rounded border border-[#233142]">
              <strong className="text-[#d8e2ef] block text-sm mb-1">Detection Channels</strong>
              <span>4 µm (Bands 21 & 22) and 11 µm (Band 31) brightness temperature</span>
            </div>
            <div className="p-3 bg-[#182330] rounded border border-[#233142]">
              <strong className="text-[#d8e2ef] block text-sm mb-1">Scientific Role</strong>
              <span>Provides the vital pre-2012 anchor baseline for long-term fire regime harmonization.</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="bg-[#141d28] p-4 rounded-lg border border-[#233142] flex items-start gap-3">
        <Info size={18} className="text-[#ff7547] shrink-0 mt-0.5" />
        <div className="text-xs text-[#8e9eb3] space-y-1">
          <strong className="text-white">Scientific Context: The 1 km Footprint Artifact</strong>
          <p>
            Because MODIS cells span 1,000 meters at nadir and expand toward scan edges, small or sub-canopy burns may not produce enough thermal radiative flux to trigger the contextual threshold. This causes raw MODIS detection counts to appear significantly lower than post-2012 VIIRS measurements in the same geographic region.
          </p>
        </div>
      </div>
    </div>
  );
}
