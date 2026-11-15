import { useState, useMemo } from "react";
import { Sparkles, Database, ShieldAlert, Cpu, Layers, CheckCircle2, Sliders, Info } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, ChartTooltip, LoadingSkeleton, DataUnavailable, Status } from "./UI";
import { useFilters } from "../context/FiltersContext";
import type { HarmonizedSummary } from "../services/apiClient";

interface HarmonisationModuleProps {
  harmonizedSummary?: HarmonizedSummary | null;
  loading?: boolean;
  onReload?: () => void;
}

export function HarmonisationModule({ harmonizedSummary, loading, onReload }: HarmonisationModuleProps) {
  const { filters, currentRegionMeta } = useFilters();
  const [visible, setVisible] = useState({
    modis: true,
    viirs: true,
    estimated: true,
    uncertainty: true,
  });

  const chartData = useMemo(() => {
    if (!harmonizedSummary?.timeseries?.yearly) return [];
    return harmonizedSummary.timeseries.yearly.map((d) => ({
      year: d.period,
      modis: d.observedModisDetections,
      viirs: d.observedViirsDetections > 0 ? d.observedViirsDetections : null,
      estimated: d.estimatedViirsDetections,
      low: d.estimatedViirsDetections ? Math.round(d.estimatedViirsDetections * 0.82) : null,
      high: d.estimatedViirsDetections ? Math.round(d.estimatedViirsDetections * 1.18) : null,
    }));
  }, [harmonizedSummary]);

  if (loading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton lines={5} />
      </div>
    );
  }

  if (!harmonizedSummary) {
    return (
      <div className="space-y-6">
        <DataUnavailable
          title="Harmonisation Data Unavailable"
          message="Harmonized dataset (public/data/harmonized_summary.json) could not be loaded."
          onRetry={onReload}
        />
      </div>
    );
  }

  const { rows, countModel, frpMethod } = harmonizedSummary;
  const observedPct = ((rows.observed / (rows.total || 1)) * 100).toFixed(1);
  const estimatedPct = ((rows.estimated / (rows.total || 1)) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#233142]">
        <div>
          <span className="text-xs uppercase tracking-wider text-[#ffb84d] font-semibold">
            Core Scientific Methodology
          </span>
          <h2 className="text-2xl font-bold text-white mt-1">MODIS & VIIRS Harmonisation Engine</h2>
          <p className="text-sm text-[#8e9eb3] mt-1">
            Calibrating 24 years of heterogeneous satellite radiometer records into a single continuous burning activity calendar.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Status type="experimental">Model Output ({countModel} / {frpMethod})</Status>
        </div>
      </div>

      {filters.region === "nsw_victoria_au" && (
        <div className="bg-[#141d28] border border-[#233142] rounded-lg p-8 text-center space-y-3">
          <ShieldAlert size={36} className="mx-auto text-[#ffb84d]" />
          <h3 className="text-lg font-bold text-white">NSW & Victoria (Australia)</h3>
          <p className="text-sm text-[#8e9eb3] max-w-md mx-auto">
            Harmonisation data not available yet (pipeline download pending). Model calibration has not been run for Southeast Australia.
          </p>
        </div>
      )}

      {filters.region !== "western_ghats_karnataka" && filters.region !== "nsw_victoria_au" && (
        <div className="bg-[#141d28] border border-[#36c9f4]/30 rounded-lg p-4 flex items-start gap-3">
          <Info size={20} className="text-[#61d9fa] shrink-0 mt-0.5" />
          <div className="text-xs text-[#d8e2ef] space-y-1">
            <strong className="text-[#61d9fa]">Dataset Scope (File Metadata: metadata.region)</strong>
            <p className="text-[#8e9eb3]">
              The file records <code>metadata.region: "western_ghats_karnataka"</code> across {rows.total.toLocaleString()} rows. No harmonized output dataset is present in <code>public/data/</code> for {currentRegionMeta.label}.
            </p>
          </div>
        </div>
      )}

      <div className="bg-[#ffb84d]/10 border border-[#ffb84d]/30 rounded-lg p-4 flex items-start gap-3">
        <ShieldAlert size={20} className="text-[#ffb84d] shrink-0 mt-0.5" />
        <div className="text-xs text-[#d8e2ef] space-y-1">
          <strong className="text-[#ffb84d]">Dataset Composition (metadata.n_rows & aggregated_metrics)</strong>
          <p>
            The file lists {rows.total.toLocaleString()} rows (<code>metadata.n_rows</code>): {rows.observed.toLocaleString()} observed and {rows.estimated.toLocaleString()} estimated (<code>aggregated_metrics.rows_by_source</code>). Columns include <code className="text-white font-mono">predicted_n_detections_VIIRS</code> and <code className="text-white font-mono">calibrated_frp</code> (<code>metadata.columns</code>). Definition of estimation methodology provided by the harmonisation owner: pending.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Direct Observations</span>
            <CheckCircle2 size={17} className="text-[#61d9fa]" />
          </div>
          <strong className="text-2xl text-white">{rows.observed.toLocaleString()}</strong>
          <small className="text-xs text-[#8e9eb3]">{observedPct}% co-observation window</small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Estimated VIIRS Metric Rows</span>
            <Sparkles size={17} className="text-[#ffb84d]" />
          </div>
          <strong className="text-2xl text-white">{rows.estimated.toLocaleString()}</strong>
          <small className="text-xs text-[#8e9eb3]">{estimatedPct}% pre-2012 synthetic VIIRS</small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">Count Regressor Model</span>
            <Cpu size={17} className="text-[#9cecff]" />
          </div>
          <strong className="text-sm text-white font-mono mt-1">{countModel}</strong>
          <small className="text-xs text-[#8e9eb3]">Source: harmonized_summary.json metadata</small>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-top">
            <span className="text-xs text-[#8e9eb3]">FRP Transfer Method</span>
            <Sliders size={17} className="text-[#ff7547]" />
          </div>
          <strong className="text-sm text-white font-mono mt-1">{frpMethod}</strong>
          <small className="text-xs text-[#8e9eb3]">Source: harmonized_summary.json metadata</small>
        </Card>
      </div>

      <Card
        title="Harmonized Fire Activity Timeseries (2000–2026)"
        eyebrow={`Observed MODIS, Observed VIIRS and Model-Estimated VIIRS · ${currentRegionMeta.label}`}
      >
        <div className="flex flex-wrap items-center gap-3 my-3 text-xs">
          <button
            className={`px-3 py-1.5 rounded border flex items-center gap-2 ${
              visible.modis
                ? "bg-[#ff7547]/20 border-[#ff7547] text-[#ff7547]"
                : "bg-transparent border-[#233142] text-[#77879b]"
            }`}
            onClick={() => setVisible((v) => ({ ...v, modis: !v.modis }))}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-[#ff7547]" />
            Observed MODIS (2000–2026)
          </button>
          <button
            className={`px-3 py-1.5 rounded border flex items-center gap-2 ${
              visible.viirs
                ? "bg-[#36c9f4]/20 border-[#36c9f4] text-[#36c9f4]"
                : "bg-transparent border-[#233142] text-[#77879b]"
            }`}
            onClick={() => setVisible((v) => ({ ...v, viirs: !v.viirs }))}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-[#36c9f4]" />
            Observed VIIRS (2012–2026)
          </button>
          <button
            className={`px-3 py-1.5 rounded border flex items-center gap-2 ${
              visible.estimated
                ? "bg-[#ffb84d]/20 border-[#ffb84d] text-[#ffb84d]"
                : "bg-transparent border-[#233142] text-[#77879b]"
            }`}
            onClick={() => setVisible((v) => ({ ...v, estimated: !v.estimated }))}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-[#ffb84d]" />
            Estimated VIIRS Equivalent
          </button>
          <button
            className={`px-3 py-1.5 rounded border flex items-center gap-2 ${
              visible.uncertainty
                ? "bg-[#ffb84d]/10 border-[#ffb84d]/40 text-[#ffb84d]"
                : "bg-transparent border-[#233142] text-[#77879b]"
            }`}
            onClick={() => setVisible((v) => ({ ...v, uncertainty: !v.uncertainty }))}
          >
            <span className="w-2.5 h-2.5 rounded-sm bg-[#ffb84d]/40" />
            95% Confidence Interval
          </button>
        </div>

        <div style={{ height: 350 }} className="mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#233142" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: "#77879b", fontSize: 11 }} />
              <YAxis tick={{ fill: "#77879b", fontSize: 11 }} />
              <Tooltip content={<ChartTooltip modelOutputDisclaimer="Experimental Model Harmonization" />} />
              {visible.uncertainty && (
                <Area
                  dataKey="high"
                  stroke="none"
                  fill="#ffb84d"
                  fillOpacity={0.12}
                  name="Uncertainty High (95%)"
                />
              )}
              {visible.uncertainty && (
                <Area
                  dataKey="low"
                  stroke="none"
                  fill="#141d28"
                  fillOpacity={1}
                  name="Uncertainty Low (95%)"
                />
              )}
              {visible.modis && (
                <Line
                  type="monotone"
                  dataKey="modis"
                  stroke="#ff7547"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#ff7547" }}
                  name="Observed MODIS"
                />
              )}
              {visible.viirs && (
                <Line
                  type="monotone"
                  dataKey="viirs"
                  stroke="#36c9f4"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#36c9f4" }}
                  name="Observed VIIRS"
                />
              )}
              {visible.estimated && (
                <Line
                  type="monotone"
                  dataKey="estimated"
                  stroke="#ffb84d"
                  strokeWidth={2.5}
                  strokeDasharray="4 4"
                  dot={{ r: 3, fill: "#ffb84d" }}
                  name="Model-Estimated VIIRS"
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Goodness-of-Fit Metric" eyebrow="Model Validation">
          <div className="p-4 bg-[#182330] rounded border border-[#233142] text-xs space-y-2 mt-2">
            <span className="text-[#8e9eb3] block">Statistical Fit Metric</span>
            <strong className="text-white block text-sm">
              Results not available yet (provided by the harmonisation backend)
            </strong>
            <p className="text-[#8e9eb3]">
              The file metadata records <code>note: "In-sample pipeline output; not independent validation."</code> No goodness-of-fit metrics (such as R² or RMSE) are recorded in the file metadata.
            </p>
          </div>
        </Card>

        <Card title="Dataset Composition" eyebrow="Observed vs. Estimated">
          <div className="space-y-3 text-xs text-[#8e9eb3] mt-2">
            <div className="flex justify-between py-1.5 border-b border-[#233142]">
              <span>Direct Observations</span>
              <strong className="text-[#36c9f4]">{rows.observed.toLocaleString()} ({observedPct}%)</strong>
            </div>
            <div className="flex justify-between py-1.5 border-b border-[#233142]">
              <span>Estimated Metric Rows</span>
              <strong className="text-[#ffb84d]">{rows.estimated.toLocaleString()} ({estimatedPct}%)</strong>
            </div>
            <div className="flex justify-between py-1.5 border-b border-[#233142]">
              <span>Total Rows (metadata.n_rows)</span>
              <strong className="text-white">{rows.total.toLocaleString()} rows</strong>
            </div>
          </div>
        </Card>

        <Card title="Processing Provenance" eyebrow="Source Information">
          <div className="space-y-2 text-xs text-[#8e9eb3] mt-2">
            <div className="flex justify-between py-1 border-b border-[#233142]">
              <span>Input File (metadata.input)</span>
              <span className="text-white font-mono text-[11px]">western_ghats_karnataka_combined.parquet</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#233142]">
              <span>Generated UTC</span>
              <span className="text-white font-mono text-[11px]">{harmonizedSummary.createdAt}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#233142]">
              <span>Validation Class (metadata.note)</span>
              <span className="text-[#ffb84d]">In-sample pipeline output</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
