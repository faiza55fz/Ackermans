import { useState, useMemo } from "react";
import { Globe2, Filter, AlertTriangle, Info, X, RefreshCw } from "lucide-react";
import { Card, LoadingSkeleton, Status, DataUnavailable } from "./UI";
import { FireMap } from "./FireMap";
import { useFilters } from "../context/FiltersContext";
import type { MapResponse, RegionKey } from "../services/apiClient";
import { hotspots, type Hotspot, type MapCell } from "../data";

interface WildfireMapModuleProps {
  mapData?: MapResponse | null;
  loading?: boolean;
  onReload?: () => void;
}

export function WildfireMapModule({ mapData, loading, onReload }: WildfireMapModuleProps) {
  const { filters, setSatellite, setConfidence, resetFilters, currentRegionMeta, confidenceNote } = useFilters();
  const [selectedCell, setSelectedCell] = useState<MapCell | null>(null);
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);

  const regionKey: RegionKey = useMemo(() => {
    if (filters.region === "palisades_la") return "palisades_la";
    if (filters.region === "punjab_haryana") return "punjab_haryana";
    return "western_ghats_karnataka";
  }, [filters.region]);

  const rawCells = useMemo(() => {
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

  const filteredCells = useMemo(() => {
    return rawCells.filter((cell) => {
      if (filters.satellite === "MODIS" && cell.modis_detections === 0) return false;
      if (filters.satellite === "VIIRS" && cell.viirs_detections === 0) return false;
      return true;
    });
  }, [rawCells, filters.satellite]);

  const filteredHotspots = useMemo(() => {
    return hotspots.filter((h) => {
      if (filters.satellite === "MODIS" && h.family !== "MODIS") return false;
      if (filters.satellite === "VIIRS" && h.family !== "VIIRS") return false;
      if (filters.confidence === "high" && h.confidence < 80) return false;
      return true;
    });
  }, [filters.satellite, filters.confidence]);

  const totalDetectionsInView = useMemo(() => {
    return filteredCells.reduce((sum, c) => sum + c.detections, 0);
  }, [filteredCells]);

  if (loading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  if (!mapData || !mapData.regions) {
    return (
      <div className="space-y-6">
        <DataUnavailable
          title="Map Data Unavailable"
          message="Spatial grid dataset (public/data/map.json) could not be loaded."
          onRetry={onReload}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#233142]">
        <div>
          <span className="text-xs uppercase tracking-wider text-[#36c9f4] font-semibold">
            Geospatial Analysis Workspace
          </span>
          <h2 className="text-2xl font-bold text-white mt-1">Wildfire Geospatial Map</h2>
          <p className="text-sm text-[#8e9eb3] mt-1">
            Aggregated 0.25° grid cells and clean satellite hotspot detections across study regions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Status type="verified">{filteredCells.length} Grid Cells (0.25° Resolution)</Status>
          <button
            className="md:hidden button secondary py-1.5 px-3 text-xs flex items-center gap-1.5"
            onClick={() => setFilterPanelOpen(!filterPanelOpen)}
          >
            <Filter size={13} /> Filters
          </button>
        </div>
      </div>

      {filters.region === "palisades_la" && (
        <div className="bg-[#ffb84d]/10 border border-[#ffb84d]/30 rounded-lg p-3 flex items-start gap-3">
          <AlertTriangle size={18} className="text-[#ffb84d] shrink-0 mt-0.5" />
          <div className="text-xs text-[#d8e2ef] space-y-0.5">
            <strong className="text-[#ffb84d]">
              Data snapshot predates the full-year Palisades data
            </strong>
            <p className="text-[#8e9eb3]">
              The spatial grid below shows the 2 grid cells (4,560 detections) from the earlier winter extract. Full-year callset contains 6,083 detections.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-4">
          <Card className="map-card relative p-0 overflow-hidden border border-[#233142]">
            <div className="p-3 bg-[#182330]/90 border-b border-[#233142] flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-white flex items-center gap-1.5">
                  <Globe2 size={14} className="text-[#36c9f4]" /> {currentRegionMeta.label}
                </span>
                <span className="text-[#8e9eb3]">·</span>
                <span className="text-[#8e9eb3]">
                  {totalDetectionsInView.toLocaleString()} Detections
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-[#ff7547]">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#ff7547]" /> MODIS
                </span>
                <span className="flex items-center gap-1 text-[#36c9f4]">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#36c9f4]" /> VIIRS
                </span>
                <span className="flex items-center gap-1 text-[#ffb84d]">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#ffb84d]" /> Dual Consensus
                </span>
              </div>
            </div>

            {filters.region === "nsw_victoria_au" ? (
              <div className="p-16 text-center bg-[#141d28]/90 m-4 rounded-lg border border-dashed border-[#233142] space-y-3">
                <Globe2 className="mx-auto text-[#ffb84d]" size={42} />
                <h4 className="text-white font-semibold text-lg">NSW & Victoria Spatial Grid Data</h4>
                <p className="text-xs text-[#8e9eb3] max-w-md mx-auto">
                  Data not available yet (pipeline download pending). Grid cells for Southeast Australia have not been ingested into the static snapshot.
                </p>
              </div>
            ) : filters.region === "punjab_haryana" ? (
              <div className="p-16 text-center bg-[#141d28] border-b border-[#233142] space-y-4">
                <Globe2 className="mx-auto text-[#61d9fa]" size={48} />
                <h3 className="text-white font-semibold text-lg">Punjab & Haryana Spatial Grid Unavailable</h3>
                <p className="text-sm text-[#8e9eb3] max-w-lg mx-auto">
                  Punjab & Haryana contains 2,732,329 total detections. To maintain client responsiveness and stay within web memory limits, individual spatial cells were not pre-baked into static map.json.
                </p>
                <div className="pt-2">
                  <button
                    className="button secondary text-xs py-2 px-4 inline-flex items-center gap-2"
                    onClick={resetFilters}
                  >
                    <RefreshCw size={13} /> Switch to Western Ghats
                  </button>
                </div>
              </div>
            ) : filteredCells.length === 0 && filteredHotspots.length === 0 ? (
              <div className="p-16 text-center bg-[#141d28] border-b border-[#233142] space-y-4">
                <AlertTriangle className="mx-auto text-[#ffb84d]" size={40} />
                <h3 className="text-white font-semibold text-base">No Detections Match Current Filters</h3>
                <p className="text-xs text-[#8e9eb3] max-w-md mx-auto">
                  No spatial grid cells or fire points were found matching the selected sensor, confidence, or date parameters.
                </p>
                <button
                  className="button secondary text-xs py-1.5 px-3 inline-flex items-center gap-1.5"
                  onClick={resetFilters}
                >
                  <RefreshCw size={12} /> Reset All Filters
                </button>
              </div>
            ) : (
              <FireMap
                cells={filteredCells}
                hotspots={filteredHotspots}
                height={520}
                center={currentRegionMeta.coordinates}
                zoomLevel={currentRegionMeta.defaultZoom}
                onSelectCell={setSelectedCell}
                selectedCell={selectedCell}
                onSelect={setSelectedHotspot}
                selected={selectedHotspot}
              />
            )}

            {selectedCell && (
              <div className="p-4 bg-[#141d28]/95 border-t border-[#233142] flex flex-wrap items-center justify-between gap-4 text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#ffb84d]/20 border border-[#ffb84d]/40 flex items-center justify-center text-[#ffb84d] font-bold">
                    0.25°
                  </div>
                  <div>
                    <strong className="text-white text-sm">Grid Cell: {selectedCell.cell_id}</strong>
                    <span className="text-[#8e9eb3] block">
                      {selectedCell.latitude.toFixed(4)}°N, {selectedCell.longitude.toFixed(4)}°E
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <div>
                    <span className="text-[#8e9eb3] block">Detections</span>
                    <strong className="text-white text-sm">{selectedCell.detections.toLocaleString()}</strong>
                  </div>
                  <div>
                    <span className="text-[#8e9eb3] block">MODIS vs VIIRS</span>
                    <span className="text-[#ff7547] font-semibold">{selectedCell.modis_detections}</span>
                    <span className="text-[#8e9eb3]"> / </span>
                    <span className="text-[#36c9f4] font-semibold">{selectedCell.viirs_detections}</span>
                  </div>
                  {selectedCell.mean_frp !== null && (
                    <div>
                      <span className="text-[#8e9eb3] block">Mean FRP</span>
                      <strong className="text-[#ffb84d] text-sm">{selectedCell.mean_frp} MW</strong>
                    </div>
                  )}
                  <div>
                    <span className="text-[#8e9eb3] block">Time Window</span>
                    <span className="text-white">{selectedCell.first_date} → {selectedCell.last_date}</span>
                  </div>
                </div>

                <button
                  className="p-1 text-[#8e9eb3] hover:text-white"
                  onClick={() => setSelectedCell(null)}
                >
                  <X size={16} />
                </button>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="Map Filters" eyebrow="Dynamic Query">
            <div className="space-y-4 text-xs mt-3">
              <div>
                <label className="text-[#8e9eb3] block mb-1 font-medium">Sensor Family</label>
                <div className="grid grid-cols-3 gap-1">
                  {(["All", "MODIS", "VIIRS"] as const).map((sat) => (
                    <button
                      key={sat}
                      className={`py-1.5 px-2 rounded text-center border font-medium ${
                        filters.satellite === sat
                          ? "bg-[#36c9f4]/20 border-[#36c9f4] text-[#36c9f4]"
                          : "bg-[#182330] border-[#233142] text-[#8e9eb3]"
                      }`}
                      onClick={() => setSatellite(sat)}
                    >
                      {sat}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-[#8e9eb3] block mb-1 font-medium">Confidence Level</label>
                <select
                  className="w-full bg-[#182330] border border-[#233142] rounded p-2 text-white text-xs"
                  value={filters.confidence}
                  onChange={(e) => setConfidence(e.target.value as any)}
                >
                  <option value="nominal_high">Nominal + High (all cleaned data)</option>
                  <option value="high">High only</option>
                </select>
                <p className="text-[11px] text-[#77879b] mt-1.5 italic">
                  {confidenceNote}
                </p>
              </div>

              <div className="pt-3 border-t border-[#233142] space-y-2 text-[#8e9eb3]">
                <strong className="text-white block">Layer Legend</strong>
                <p>
                  Circle sizes scale dynamically with <span className="text-white font-mono">√detections</span>.
                </p>
                <p>
                  Click any grid circle on the map to inspect sensor breakdown, radiative flux, and observation bounds.
                </p>
              </div>
            </div>
          </Card>

          <Card title="Region Coverage" eyebrow="Data Summary">
            <div className="space-y-3 text-xs text-[#8e9eb3] mt-2">
              <div className="flex justify-between py-1 border-b border-[#233142]">
                <span>Active Grid Cells</span>
                <strong className="text-white">{filteredCells.length} cells (0.25°)</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-[#233142]">
                <span>Total Observations</span>
                <strong className="text-[#61d9fa]">{totalDetectionsInView.toLocaleString()}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-[#233142]">
                <span>Spatial Binning</span>
                <strong className="text-white">0.25° Lat/Lng (~28 km)</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-[#233142]">
                <span>Coordinate System</span>
                <strong className="text-white">WGS 84 (EPSG:4326)</strong>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
