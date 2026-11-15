import { Info } from "lucide-react";
import { RegionalComparison } from "./RegionalComparison";
import { Status } from "./UI";
import { useFilters } from "../context/FiltersContext";

export function AnalyticsModule() {
  const { filters } = useFilters();
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#233142]">
        <div>
          <span className="text-xs uppercase tracking-wider text-[#39bde7] font-semibold">
            Comparative Geospatial Intelligence
          </span>
          <h2 className="text-2xl font-bold text-white mt-1">Cross-Regional Analytics & Benchmarks</h2>
          <p className="text-sm text-[#8e9eb3] mt-1">
            Empirical multi-sensor comparison across three distinct biomes: Pacific Palisades, Western Ghats, and Punjab & Haryana.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Status type="verified">3 Eco-Zones · 0.05° & 0.01° Grids</Status>
        </div>
      </div>

      {filters.region === "nsw_victoria_au" && (
        <div className="bg-[#141d28] border border-[#233142] rounded-lg p-6 text-center space-y-2">
          <Info size={32} className="mx-auto text-[#ffb84d]" />
          <h3 className="text-lg font-bold text-white">NSW & Victoria (Australia)</h3>
          <p className="text-sm text-[#8e9eb3]">Cross-regional benchmark data not available yet (pipeline download pending).</p>
        </div>
      )}

      <div className="bg-[#182330] p-3.5 rounded-lg border border-[#233142] flex items-start gap-3">
        <Info size={18} className="text-[#39bde7] shrink-0 mt-0.5" />
        <div className="text-xs text-[#8e9eb3] space-y-0.5">
          <strong className="text-[#d8e2ef]">Pre-Aggregated Benchmark Notice</strong>
          <p>
            The multi-resolution comparative tables and sensor share curves below are pre-computed benchmarks across the 2012–2026 co-observation window across all nominal and high confidence classes. Global topbar satellite and date range filters are locked to the benchmark scope.
          </p>
        </div>
      </div>

      <div className="analytics-content">
        <RegionalComparison />
      </div>
    </div>
  );
}
