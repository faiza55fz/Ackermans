import { useMemo, useState } from "react";
import {
  Flame,
  CalendarDays,
  Target,
  Radio,
  Globe2,
  ChevronRight,
  Activity,
  Sparkles,
  BarChart3,
  Orbit,
  AlertTriangle,
  Info,
  Database,
} from "lucide-react";
import { Card, LoadingSkeleton, Status } from "./UI";
import { FireMap } from "./FireMap";
import { useFilters } from "../context/FiltersContext";
import type { DashboardResponse, MapResponse, HarmonizedSummary } from "../services/apiClient";
import { hotspots, type Hotspot, type PageName } from "../data";

interface OverviewModuleProps {
  dashboard?: DashboardResponse | null;
  mapData?: MapResponse | null;
  harmonizedSummary?: HarmonizedSummary | null;
  setPage: (page: PageName) => void;
  loading?: boolean;
  isStatic?: boolean;
}

import {
  VERIFIED_TOTALS,
  SENSOR_SUM_NOTE,
  PIPELINE_STATIC_BADGE,
} from "../config/verifiedTotals";

export { VERIFIED_TOTALS };

export function OverviewModule({
  dashboard,
  mapData,
  harmonizedSummary,
  setPage,
  loading,
  isStatic = true,
}: OverviewModuleProps) {
  const { filters, currentRegionMeta } = useFilters();
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);

  const regionKey = useMemo(() => {
    if (filters.region === "palisades_la") return "palisades_la";
    if (filters.region === "punjab_haryana") return "punjab_haryana";
    return "western_ghats_karnataka";
  }, [filters.region]);

  const verifiedMeta = useMemo(() => {
    if (filters.region === "all") return VERIFIED_TOTALS.all;
    if (filters.region === "palisades_la") return VERIFIED_TOTALS.palisades_la;
    if (filters.region === "punjab_haryana") return VERIFIED_TOTALS.punjab_haryana;
    if (filters.region === "nsw_victoria_au") return VERIFIED_TOTALS.nsw_victoria_au;
    return VERIFIED_TOTALS.western_ghats_karnataka;
  }, [filters.region]);

  const mapCells = useMemo(() => {
    if (!mapData?.regions) return [];
    if (filters.region === "punjab_haryana") return [];
    if (filters.region === "all") {
      return [
        ...(mapData.regions.western_ghats_karnataka || []),
        ...(mapData.regions.palisades_la || []),
      ];
    }
    return mapData.regions[regionKey] || [];
  }, [mapData, filters.region, regionKey]);

  const isPalisadesSnapshotOutdated = useMemo(() => {
    return filters.region === "palisades_la" || filters.region === "all";
  }, [filters.region]);

  const kpis = useMemo(() => {
    let totalDetections = verifiedMeta.total;
    if (filters.satellite === "MODIS") totalDetections = verifiedMeta.modis;
    if (filters.satellite === "VIIRS") totalDetections = verifiedMeta.viirs;

    let periodSpan = "2000 — 2026";
    let periodYears = "26.0 yrs";
    if (filters.dateRange === "2000-2011") {
      periodSpan = "2000 — 2011";
      periodYears = "12.0 yrs";
    } else if (filters.dateRange === "2012-2024") {
      periodSpan = "2012 — 2024";
      periodYears = "13.0 yrs";
    } else if (filters.dateRange === "2024-2026") {
      periodSpan = "2024 — 2026";
      periodYears = "2.0 yrs";
    }

    const meanFrpStr = "meanFrp" in verifiedMeta ? `${verifiedMeta.meanFrp} MW` : "14.2 MW";

    const harmonizedSourceNote = harmonizedSummary
      ? `${harmonizedSummary.rows.observed.toLocaleString()} observed / ${harmonizedSummary.rows.total.toLocaleString()} total`
      : "Results not available yet (provided by the harmonisation backend)";

    return {
      totalDetections,
      periodSpan,
      periodYears,
      meanFrpStr,
      harmonizedSourceNote,
    };
  }, [verifiedMeta, filters.satellite, filters.dateRange, harmonizedSummary]);

  if (loading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton lines={5} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#233142]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider text-[#ff7547] font-semibold">
              Satellite Fire Intelligence Platform
            </span>
            {isStatic && (
              <span className="text-[10px] bg-[#233142] text-[#8e9eb3] px-2 py-0.5 rounded flex items-center gap-1 font-mono">
                <Database size={10} /> Static data snapshot
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">
            Harmonizing MODIS & VIIRS Wildfire Observations
          </h1>
          <p className="text-sm text-[#8e9eb3] mt-1">
            A scientifically consistent 24-year burning activity record across Earth observation eras.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="button primary" onClick={() => setPage("Wildfire Map")}>
            <Globe2 size={15} /> Open Wildfire Map
          </button>
        </div>
      </div>

      {filters.region === "nsw_victoria_au" && (
        <div className="bg-[#141d28] border border-[#233142] rounded-lg p-8 text-center space-y-3">
          <AlertTriangle size={36} className="mx-auto text-[#ffb84d]" />
          <h3 className="text-lg font-bold text-white">NSW & Victoria (Australia)</h3>
          <p className="text-sm text-[#8e9eb3] max-w-md mx-auto">
            Data not available yet (pipeline download pending). Raw FIRMS downloads for Southeast Australia have not been ingested into the static snapshot.
          </p>
        </div>
      )}

      {isPalisadesSnapshotOutdated && filters.region !== "nsw_victoria_au" && (
        <div className="bg-[#ffb84d]/10 border border-[#ffb84d]/30 rounded-lg p-3.5 flex items-start gap-3">
          <AlertTriangle size={18} className="text-[#ffb84d] shrink-0 mt-0.5" />
          <div className="text-xs text-[#d8e2ef] space-y-0.5">
            <strong className="text-[#ffb84d]">
              Data snapshot predates the full-year Palisades data
            </strong>
            <p className="text-[#8e9eb3]">
              The static JSON files (<code className="text-white">dashboard.json</code>,{" "}
              <code className="text-white">map.json</code>) contain the earlier winter-only Palisades extract (4,560 rows). Verified full-year totals show{" "}
              <strong className="text-white">6,083 detections</strong> (577 MODIS, 5,506 VIIRS) as reported in the regional benchmark table.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="kpi-card">
          <div className="kpi-top">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs text-[#8e9eb3]">Clean Hotspots</span>
              <span className="text-[10px] bg-[#233142] text-[#8e9eb3] px-1.5 py-0.5 rounded font-mono font-normal">
                {PIPELINE_STATIC_BADGE}
              </span>
            </div>
            <Flame size={17} className="text-[#ff7547]" />
          </div>
          <strong className="text-2xl text-white">{kpis.totalDetections.toLocaleString()}</strong>
          <small className="text-xs text-[#8e9eb3] truncate" title={verifiedMeta.source}>
            Source: {verifiedMeta.source}
          </small>
          {filters.satellite === "All" && (
            <p className="text-[11px] text-[#ffb84d] mt-1 border-t border-[#233142] pt-1 leading-tight">
              {SENSOR_SUM_NOTE}
            </p>
          )}
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Observation Horizon</span>
            <CalendarDays size={17} className="text-[#61d9fa]" />
          </div>
          <strong className="text-2xl text-white">{kpis.periodSpan}</strong>
          <small className="text-xs text-[#8e9eb3]">{kpis.periodYears} continuous timeline</small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Mean Radiative Flux</span>
            <Target size={17} className="text-[#ffb84d]" />
          </div>
          <strong className="text-2xl text-white">{kpis.meanFrpStr}</strong>
          <small className="text-xs text-[#8e9eb3]">{currentRegionMeta.label}</small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Data Composition</span>
            <Radio size={17} className="text-[#36c9f4]" />
          </div>
          <strong className="text-sm text-white mt-1">Verified Benchmark</strong>
          <small className="text-xs text-[#8e9eb3]">{kpis.harmonizedSourceNote}</small>
        </Card>
      </div>

      <Card
        className="map-card"
        title="Geospatial Fire Observation Density"
        eyebrow={`0.25° Spatial Grid (~28 km) · ${currentRegionMeta.label} (${mapCells.length} cells in view)`}
        action={
          <button
            className="text-button flex items-center gap-1 text-xs text-[#61d9fa]"
            onClick={() => setPage("Wildfire Map")}
          >
            Full interactive map <ChevronRight size={14} />
          </button>
        }
      >
        {filters.region === "punjab_haryana" ? (
          <div className="p-12 text-center bg-[#141d28]/80 border border-dashed border-[#233142] rounded-lg my-4 space-y-3">
            <Globe2 className="mx-auto text-[#61d9fa]" size={36} />
            <h4 className="text-white font-semibold text-base">Punjab & Haryana Spatial Grid Notice</h4>
            <p className="text-xs text-[#8e9eb3] max-w-lg mx-auto">
              Due to dataset volume (2,732,329 detections), raw spatial cells for Punjab & Haryana are preserved on the split-data branch (<code>punjab-data-parts</code>) to ensure web application stability.
            </p>
            <button
              className="button secondary text-xs py-1.5 px-3 inline-flex items-center gap-1.5"
              onClick={() => setPage("Analytics")}
            >
              <BarChart3 size={13} /> View Punjab & Haryana Regional Analytics
            </button>
          </div>
        ) : (
          <FireMap
            cells={mapCells}
            hotspots={hotspots}
            center={currentRegionMeta.coordinates}
            zoomLevel={currentRegionMeta.defaultZoom}
            height={400}
            onSelect={setSelectedHotspot}
            selected={selectedHotspot}
          />
        )}
      </Card>

      <div>
        <h3 className="text-base font-semibold text-white mb-3">Explore Dashboard Modules</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div
            className="p-4 bg-[#182330] hover:bg-[#1f2d3d] border border-[#233142] rounded-lg cursor-pointer transition flex flex-col justify-between"
            onClick={() => setPage("MODIS")}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <Flame size={20} className="text-[#ff7547]" />
                <span className="text-[10px] text-[#ff7547] bg-[#ff7547]/10 px-2 py-0.5 rounded font-mono">1 km</span>
              </div>
              <strong className="text-white text-sm block">1. MODIS</strong>
              <p className="text-xs text-[#8e9eb3] mt-1">
                Terra & Aqua long-term 2000–present baseline.
              </p>
            </div>
            <span className="text-xs text-[#ff7547] flex items-center gap-1 mt-3">
              Explore MODIS <ChevronRight size={13} />
            </span>
          </div>

          <div
            className="p-4 bg-[#182330] hover:bg-[#1f2d3d] border border-[#233142] rounded-lg cursor-pointer transition flex flex-col justify-between"
            onClick={() => setPage("VIIRS")}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <Activity size={20} className="text-[#36c9f4]" />
                <span className="text-[10px] text-[#36c9f4] bg-[#36c9f4]/10 px-2 py-0.5 rounded font-mono">375 m</span>
              </div>
              <strong className="text-white text-sm block">2. VIIRS</strong>
              <p className="text-xs text-[#8e9eb3] mt-1">
                Suomi-NPP & NOAA-20/21 high resolution data.
              </p>
            </div>
            <span className="text-xs text-[#36c9f4] flex items-center gap-1 mt-3">
              Explore VIIRS <ChevronRight size={13} />
            </span>
          </div>

          <div
            className="p-4 bg-[#182330] hover:bg-[#1f2d3d] border border-[#233142] rounded-lg cursor-pointer transition flex flex-col justify-between"
            onClick={() => setPage("Harmonisation")}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <Sparkles size={20} className="text-[#ffb84d]" />
                <span className="text-[10px] text-[#ffb84d] bg-[#ffb84d]/10 px-2 py-0.5 rounded font-mono">Statistical</span>
              </div>
              <strong className="text-white text-sm block">3. Harmonisation</strong>
              <p className="text-xs text-[#8e9eb3] mt-1">
                Zero-inflated count regression & FRP scaling.
              </p>
            </div>
            <span className="text-xs text-[#ffb84d] flex items-center gap-1 mt-3">
              View Model <ChevronRight size={13} />
            </span>
          </div>

          <div
            className="p-4 bg-[#182330] hover:bg-[#1f2d3d] border border-[#233142] rounded-lg cursor-pointer transition flex flex-col justify-between"
            onClick={() => setPage("Wildfire Map")}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <Globe2 size={20} className="text-[#61d9fa]" />
                <span className="text-[10px] text-[#61d9fa] bg-[#61d9fa]/10 px-2 py-0.5 rounded font-mono">0.25°</span>
              </div>
              <strong className="text-white text-sm block">4. Wildfire Map</strong>
              <p className="text-xs text-[#8e9eb3] mt-1">
                Interactive spatial grids and fire clustering.
              </p>
            </div>
            <span className="text-xs text-[#61d9fa] flex items-center gap-1 mt-3">
              Open Map <ChevronRight size={13} />
            </span>
          </div>

          <div
            className="p-4 bg-[#182330] hover:bg-[#1f2d3d] border border-[#233142] rounded-lg cursor-pointer transition flex flex-col justify-between"
            onClick={() => setPage("Analytics")}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <BarChart3 size={20} className="text-[#9cecff]" />
                <span className="text-[10px] text-[#9cecff] bg-[#9cecff]/10 px-2 py-0.5 rounded font-mono">3 Biomes</span>
              </div>
              <strong className="text-white text-sm block">5. Analytics</strong>
              <p className="text-xs text-[#8e9eb3] mt-1">
                Multi-region benchmark & sensor comparison.
              </p>
            </div>
            <span className="text-xs text-[#9cecff] flex items-center gap-1 mt-3">
              Compare Regions <ChevronRight size={13} />
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
