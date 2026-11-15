import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowUpDown,
  BarChart3,
  Calendar,
  Database,
  Info,
  Layers,
  LineChart as LineChartIcon,
  RefreshCw,
  Sliders,
  Table as TableIcon,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, EmptyState } from "./UI";

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

export type YearlyTrendRow = {
  region: string;
  year: number;
  sensor: string;
  detections: number;
  active_days: number;
  frp_sum: number | null;
  is_partial_year: boolean;
};

const REGION_LABELS: Record<string, string> = {
  palisades: "Pacific Palisades (USA)",
  western_ghats_karnataka: "Western Ghats, Karnataka (India)",
  punjab_haryana: "Punjab & Haryana (India)",
};

const CHART_COLORS = {
  modis: "#ff7547",
  viirs: "#36c9f4",
  both: "#ffb84d",
  grid005: "#ffb84d",
  grid001: "#36c9f4",
  gridLine: "#1f2d3d",
  textMuted: "#7f8fa3",
  cardBg: "#0c1724",
};

function parseCsv(text: string): Record<string, string>[] {
  const lines = text.trim().split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",").map((v) => v.trim());
    const row: Record<string, string> = {};
    headers.forEach((h, i) => {
      row[h] = values[i] ?? "";
    });
    return row;
  });
}

export function RegionalComparison() {
  const [comparisonData, setComparisonData] = useState<RegionComparisonRow[]>([]);
  const [yearlyData, setYearlyData] = useState<YearlyTrendRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // User Interactive Controls
  const [chartACellSize, setChartACellSize] = useState<0.05 | 0.01>(0.05);
  const [chartAScale, setChartAScale] = useState<"linear" | "log">("linear");
  const [selectedRegion, setSelectedRegion] = useState<string>("palisades");
  const [isLogScale, setIsLogScale] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [compRes, yearlyRes] = await Promise.all([
        fetch("/data/region_comparison.csv"),
        fetch("/data/yearly_trends.csv"),
      ]);

      if (!compRes.ok) {
        throw new Error(`Failed to load region_comparison.csv (status ${compRes.status})`);
      }
      if (!yearlyRes.ok) {
        throw new Error(`Failed to load yearly_trends.csv (status ${yearlyRes.status})`);
      }

      const compText = await compRes.text();
      const yearlyText = await yearlyRes.text();

      const parsedComp = parseCsv(compText).map((r) => ({
        region: r.region,
        cell_size: parseFloat(r.cell_size),
        rows: parseInt(r.rows, 10),
        modis_cells_2012_2026: parseInt(r.modis_cells_2012_2026, 10),
        viirs_cells_2012_2026: parseInt(r.viirs_cells_2012_2026, 10),
        cells_seen_by_both: parseInt(r.cells_seen_by_both, 10),
        modis_cell_days: parseInt(r.modis_cell_days, 10),
        viirs_also: parseInt(r.viirs_also, 10),
        viirs_only: parseInt(r.viirs_only, 10),
        modis_only: parseInt(r.modis_only, 10),
        share_modis_seen_by_viirs: parseFloat(r.share_modis_seen_by_viirs),
      }));

      const parsedYearly = parseCsv(yearlyText).map((r) => ({
        region: r.region,
        year: parseInt(r.year, 10),
        sensor: r.sensor,
        detections: parseInt(r.detections, 10),
        active_days: parseInt(r.active_days, 10),
        frp_sum: r.frp_sum !== "" && !isNaN(parseFloat(r.frp_sum)) ? parseFloat(r.frp_sum) : null,
        is_partial_year: r.is_partial_year.toLowerCase() === "true",
      }));

      setComparisonData(parsedComp);
      setYearlyData(parsedYearly);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred while loading data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // ----------------------------------------------------
  // Chart A: Grouped Bars of Cells with Hotspots per Sensor by Region
  // ----------------------------------------------------
  const chartAData = useMemo(() => {
    return comparisonData
      .filter((r) => Math.abs(r.cell_size - chartACellSize) < 0.001)
      .map((r) => ({
        regionKey: r.region,
        regionName: REGION_LABELS[r.region] || r.region,
        modis: r.modis_cells_2012_2026,
        viirs: r.viirs_cells_2012_2026,
        both: r.cells_seen_by_both,
        cellSize: r.cell_size,
      }));
  }, [comparisonData, chartACellSize]);

  // ----------------------------------------------------
  // Chart B: Same-Day Agreement Rate (0.05° vs 0.01° Side by Side)
  // ----------------------------------------------------
  const chartBData = useMemo(() => {
    const regions = Array.from(new Set(comparisonData.map((r) => r.region)));
    return regions.map((reg) => {
      const row005 = comparisonData.find((r) => r.region === reg && Math.abs(r.cell_size - 0.05) < 0.001);
      const row001 = comparisonData.find((r) => r.region === reg && Math.abs(r.cell_size - 0.01) < 0.001);
      return {
        regionKey: reg,
        regionName: REGION_LABELS[reg] || reg,
        "0.05° Grid (Coarse)": row005 ? row005.share_modis_seen_by_viirs : 0,
        "0.01° Grid (Fine)": row001 ? row001.share_modis_seen_by_viirs : 0,
        stats005: row005
          ? `${row005.viirs_also.toLocaleString()} / ${row005.modis_cell_days.toLocaleString()}`
          : "",
        stats001: row001
          ? `${row001.viirs_also.toLocaleString()} / ${row001.modis_cell_days.toLocaleString()}`
          : "",
      };
    });
  }, [comparisonData]);

  // ----------------------------------------------------
  // Chart C: Region-Specific Sensor Boundaries & Continuous Year Axis
  // ----------------------------------------------------
  const regionSensorBounds = useMemo(() => {
    const filtered = yearlyData.filter((r) => r.region === selectedRegion);
    const modisYears = filtered
      .filter((r) => r.sensor.toUpperCase() === "MODIS")
      .map((r) => r.year);
    const viirsYears = filtered
      .filter((r) => r.sensor.toUpperCase() === "VIIRS")
      .map((r) => r.year);

    const modisMin = modisYears.length > 0 ? Math.min(...modisYears) : null;
    const modisMax = modisYears.length > 0 ? Math.max(...modisYears) : 2026;
    const viirsMin = 2012; // VIIRS operational start
    const viirsMax = viirsYears.length > 0 ? Math.max(...viirsYears) : 2026;

    return {
      modisMin,
      modisMax,
      viirsMin,
      viirsMax,
    };
  }, [yearlyData, selectedRegion]);

  const chartCData = useMemo(() => {
    const filtered = yearlyData.filter((r) => r.region === selectedRegion);

    const modisMap = new Map<number, number>();
    const viirsMap = new Map<number, number>();

    filtered.forEach((r) => {
      if (r.sensor.toUpperCase() === "MODIS") {
        modisMap.set(r.year, r.detections);
      } else if (r.sensor.toUpperCase() === "VIIRS") {
        viirsMap.set(r.year, r.detections);
      }
    });

    const { modisMin } = regionSensorBounds;
    const viirsMin = 2012;

    const continuousYears = Array.from({ length: 27 }, (_, i) => 2000 + i); // 2000 to 2026

    return continuousYears.map((yr) => {
      // MODIS: null before sensor's first data year; 0 if missing inside range; null if 0 in log mode
      let modisVal: number | null = null;
      if (modisMin !== null && yr >= modisMin) {
        const raw = modisMap.get(yr) ?? 0;
        modisVal = isLogScale && raw === 0 ? null : raw;
      }

      // VIIRS: null before 2012; 0 if missing inside range; null if 0 in log mode
      let viirsVal: number | null = null;
      if (yr >= viirsMin) {
        const raw = viirsMap.get(yr) ?? 0;
        viirsVal = isLogScale && raw === 0 ? null : raw;
      }

      return {
        year: yr.toString(),
        yearNum: yr,
        MODIS: modisVal,
        VIIRS: viirsVal,
        isPartial: yr === 2026,
      };
    });
  }, [yearlyData, selectedRegion, regionSensorBounds, isLogScale]);

  // Round ticks for Chart C y-axis
  const chartCYAxis = useMemo(() => {
    const filtered = yearlyData.filter((r) => r.region === selectedRegion);
    const maxVal = Math.max(0, ...filtered.map((r) => r.detections));

    // Linear round ticks: 0, 1k, 2k, 3k, 4k or clean round values
    let ticks: number[] = [0, 1000, 2000, 3000, 4000];
    if (maxVal > 0) {
      const exp = Math.floor(Math.log10(maxVal));
      const fraction = maxVal / Math.pow(10, exp);
      let step = Math.pow(10, exp);
      if (fraction <= 1.2) {
        step = 0.25 * Math.pow(10, exp);
      } else if (fraction <= 2.5) {
        step = 0.5 * Math.pow(10, exp);
      } else if (fraction <= 5.0) {
        step = 1.0 * Math.pow(10, exp);
      } else {
        step = 2.0 * Math.pow(10, exp);
      }

      ticks = [0];
      let curr = step;
      while (curr < maxVal + step * 0.99) {
        ticks.push(Math.round(curr));
        curr += step;
      }
    }

    // Log ticks: powers of 10
    const logTicks: number[] = [1];
    let lCurr = 10;
    while (lCurr <= Math.max(10, maxVal * 1.5)) {
      logTicks.push(lCurr);
      lCurr *= 10;
    }

    return {
      ticks,
      domain: [0, ticks[ticks.length - 1]],
      logTicks,
      logDomain: [1, logTicks[logTicks.length - 1]],
    };
  }, [yearlyData, selectedRegion]);

  // Custom marker renderer for Chart C (hollow circle for 2026 partial year)
  const renderDot = (color: string) => (props: any) => {
    const { cx, cy, payload } = props;
    if (cx == null || cy == null || isNaN(cx) || isNaN(cy)) return null;
    const is2026 = payload?.year === "2026";
    if (is2026) {
      return (
        <circle
          key={`hollow-dot-${payload.year}-${color}`}
          cx={cx}
          cy={cy}
          r={5.5}
          fill="#07101b"
          stroke={color}
          strokeWidth={2.5}
        />
      );
    }
    return (
      <circle
        key={`dot-${payload.year}-${color}`}
        cx={cx}
        cy={cy}
        r={3}
        fill={color}
      />
    );
  };

  if (loading) {
    return (
      <div className="p-6">
        <Card title="Loading Regional Analytics..." eyebrow="Dataset Ingestion">
          <div className="flex flex-col items-center justify-center p-12 text-slate-400 gap-3">
            <RefreshCw className="animate-spin text-cyan-400" size={32} />
            <p className="text-sm">Fetching and parsing regional comparison CSV datasets...</p>
          </div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Card title="Data Load Error" eyebrow="Network / Pipeline Alert">
          <div className="p-8 text-center space-y-4">
            <div className="inline-flex p-3 rounded-full bg-red-500/10 text-red-400">
              <AlertTriangle size={36} />
            </div>
            <h3 className="text-lg font-semibold text-white">Could not load regional dataset</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto">{error}</p>
            <button className="button primary" onClick={loadData}>
              <RefreshCw size={14} className="mr-2" /> Retry Data Load
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (!comparisonData.length && !yearlyData.length) {
    return (
      <div className="p-6">
        <EmptyState reset={loadData} />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <span className="text-xs font-semibold tracking-wider uppercase text-cyan-400">
            Harmonized Regional Analytics
          </span>
          <h1 className="text-2xl font-bold text-slate-100 mt-1">Cross-Region Sensor Comparison</h1>
          <p className="text-sm text-slate-400 mt-1">
            Empirical multi-region analysis of NASA MODIS (1 km) and VIIRS (375 m) active fire observations
            across Palisades, Western Ghats, and Punjab &amp; Haryana.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Database size={12} /> Real Spatial Datasets
          </span>
        </div>
      </div>

      {/* Grid of Top 2 Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CHART A: Grouped Bars of Cells with Hotspots */}
        <Card
          eyebrow={`Spatial Grid Resolution: ${chartACellSize}°`}
          title={`Chart A: Unique Hotspot Cells by Sensor (${chartACellSize}° Grid)`}
          action={
            <div className="flex flex-wrap items-center gap-2">
              {/* Linear / Log Toggle for Chart A */}
              <div className="flex items-center gap-1 p-0.5 bg-slate-900 border border-slate-700/80 rounded-lg">
                <button
                  type="button"
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                    chartAScale === "linear"
                      ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  onClick={() => setChartAScale("linear")}
                >
                  Linear
                </button>
                <button
                  type="button"
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                    chartAScale === "log"
                      ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  onClick={() => setChartAScale("log")}
                >
                  Log10
                </button>
              </div>

              {/* Cell Size Toggle */}
              <div className="segmented">
                <button
                  className={chartACellSize === 0.05 ? "active" : ""}
                  onClick={() => setChartACellSize(0.05)}
                >
                  0.05° (~5.5 km)
                </button>
                <button
                  className={chartACellSize === 0.01 ? "active" : ""}
                  onClick={() => setChartACellSize(0.01)}
                >
                  0.01° (~1.1 km)
                </button>
              </div>
            </div>
          }
        >
          <div className="mt-4 h-84 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartAData} margin={{ top: 28, right: 30, left: 10, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.gridLine} />
                <XAxis
                  dataKey="regionName"
                  stroke={CHART_COLORS.textMuted}
                  tick={{ fill: CHART_COLORS.textMuted, fontSize: 11 }}
                  interval={0}
                />
                <YAxis
                  stroke={CHART_COLORS.textMuted}
                  tick={{ fill: CHART_COLORS.textMuted, fontSize: 11 }}
                  scale={chartAScale === "log" ? "log" : "auto"}
                  domain={chartAScale === "log" ? [1, "auto"] : [0, "auto"]}
                  tickFormatter={(val) => (val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val)}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    return (
                      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs shadow-xl space-y-1.5">
                        <strong className="block text-slate-200 border-b border-slate-800 pb-1">{label}</strong>
                        <div className="text-slate-400">Cell Size: {chartACellSize}°</div>
                        {payload.map((entry) => (
                          <div key={entry.name} className="flex justify-between gap-4">
                            <span style={{ color: entry.color }}>{entry.name}:</span>
                            <span className="font-semibold text-slate-100">
                              {Number(entry.value).toLocaleString()} cells
                            </span>
                          </div>
                        ))}
                      </div>
                    );
                  }}
                />
                <Legend
                  wrapperStyle={{ paddingTop: "12px", fontSize: "12px" }}
                  formatter={(value) => <span className="text-slate-300">{value}</span>}
                />
                <Bar name="MODIS (2012–2026)" dataKey="modis" fill={CHART_COLORS.modis} radius={[4, 4, 0, 0]}>
                  <LabelList
                    dataKey="modis"
                    position="top"
                    fill="#ff9f7d"
                    fontSize={10}
                    formatter={(v: any) => (v != null && v > 0 ? Number(v).toLocaleString() : "")}
                  />
                </Bar>
                <Bar name="VIIRS (2012–2026)" dataKey="viirs" fill={CHART_COLORS.viirs} radius={[4, 4, 0, 0]}>
                  <LabelList
                    dataKey="viirs"
                    position="top"
                    fill="#7fe1fc"
                    fontSize={10}
                    formatter={(v: any) => (v != null && v > 0 ? Number(v).toLocaleString() : "")}
                  />
                </Bar>
                <Bar name="Both Sensors" dataKey="both" fill={CHART_COLORS.both} radius={[4, 4, 0, 0]}>
                  <LabelList
                    dataKey="both"
                    position="top"
                    fill="#ffd285"
                    fontSize={10}
                    formatter={(v: any) => (v != null && v > 0 ? Number(v).toLocaleString() : "")}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            Values displayed on top of each bar ensure small geographic regions (e.g. Palisades) remain easily readable.
            Toggle between Linear and Log10 scales for dynamic cross-magnitude comparisons.
          </p>
        </Card>

        {/* CHART B: Share of MODIS Cell-Days Seen by VIIRS Side by Side */}
        <Card
          eyebrow="Temporal Overlap & Agreement Rate"
          title="Share of MODIS cell-days also detected by VIIRS the same day, by cell size"
        >
          <div className="mt-4 h-84 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartBData} margin={{ top: 28, right: 30, left: 10, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.gridLine} />
                <XAxis
                  dataKey="regionName"
                  stroke={CHART_COLORS.textMuted}
                  tick={{ fill: CHART_COLORS.textMuted, fontSize: 11 }}
                  interval={0}
                />
                <YAxis
                  stroke={CHART_COLORS.textMuted}
                  tick={{ fill: CHART_COLORS.textMuted, fontSize: 11 }}
                  unit="%"
                  domain={[0, 100]}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const dataItem = payload[0]?.payload;
                    return (
                      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs shadow-xl space-y-2">
                        <strong className="block text-slate-200 border-b border-slate-800 pb-1">{label}</strong>
                        {payload.map((entry) => {
                          const is005 = entry.dataKey === "0.05° Grid (Coarse)";
                          const counts = is005 ? dataItem?.stats005 : dataItem?.stats001;
                          return (
                            <div key={entry.name} className="space-y-0.5">
                              <div className="flex justify-between gap-4">
                                <span style={{ color: entry.color }} className="font-medium">
                                  {entry.name}:
                                </span>
                                <span className="font-semibold text-slate-100">
                                  {Number(entry.value).toFixed(2)}%
                                </span>
                              </div>
                              {counts && (
                                <div className="text-[11px] text-slate-400 pl-2">
                                  {counts} cell-days (viirs_also / modis_cell_days)
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  }}
                />
                <Legend
                  payload={[
                    {
                      value: "0.05° Grid (Coarse ~5.5 km)",
                      type: "rect",
                      id: "0.05° Grid (Coarse)",
                      color: CHART_COLORS.grid005,
                    },
                    {
                      value: "0.01° Grid (Fine ~1.1 km)",
                      type: "rect",
                      id: "0.01° Grid (Fine)",
                      color: CHART_COLORS.grid001,
                    },
                  ]}
                  wrapperStyle={{ paddingTop: "12px", fontSize: "12px" }}
                  formatter={(value) => <span className="text-slate-300">{value}</span>}
                />
                <Bar
                  name="0.05° Grid (Coarse ~5.5 km)"
                  dataKey="0.05° Grid (Coarse)"
                  fill={CHART_COLORS.grid005}
                  radius={[4, 4, 0, 0]}
                >
                  <LabelList
                    dataKey="0.05° Grid (Coarse)"
                    position="top"
                    fill="#ffd285"
                    fontSize={10}
                    formatter={(v: any) => (v ? `${Number(v).toFixed(1)}%` : "")}
                  />
                </Bar>
                <Bar
                  name="0.01° Grid (Fine ~1.1 km)"
                  dataKey="0.01° Grid (Fine)"
                  fill={CHART_COLORS.grid001}
                  radius={[4, 4, 0, 0]}
                >
                  <LabelList
                    dataKey="0.01° Grid (Fine)"
                    position="top"
                    fill="#7fe1fc"
                    fontSize={10}
                    formatter={(v: any) => (v ? `${Number(v).toFixed(1)}%` : "")}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 p-3 rounded bg-slate-900/60 border border-slate-800 flex items-start gap-2.5 text-xs text-amber-300/90">
            <Info size={16} className="shrink-0 mt-0.5" />
            <p>
              <strong>Methodological Note:</strong> Same-day agreement depends strongly on cell size; larger cells
              make a match easier.
            </p>
          </div>
        </Card>
      </div>

      {/* CHART C: Yearly Detections per Region */}
      <Card
        eyebrow="Multi-Decadal Time Series (Continuous Axis)"
        title={`Chart C: Yearly Active Fire Detections — ${REGION_LABELS[selectedRegion] || selectedRegion}`}
        action={
          <div className="flex flex-wrap items-center gap-3">
            {/* Prominent Linear / Log Toggle */}
            <div className="flex items-center gap-1.5 p-1 bg-slate-900 border border-slate-700/80 rounded-lg shadow-sm">
              <button
                type="button"
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  !isLogScale
                    ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                onClick={() => setIsLogScale(false)}
              >
                Linear Scale
              </button>
              <button
                type="button"
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  isLogScale
                    ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                onClick={() => setIsLogScale(true)}
              >
                Log10 Scale
              </button>
            </div>

            <select
              className="bg-slate-900 text-slate-200 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-medium focus:ring-1 focus:ring-cyan-500"
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
            >
              <option value="palisades">Pacific Palisades (USA)</option>
              <option value="western_ghats_karnataka">Western Ghats, Karnataka (India)</option>
              <option value="punjab_haryana">Punjab &amp; Haryana (India)</option>
            </select>
          </div>
        }
      >
        <div className="mt-4 h-88 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartCData} margin={{ top: 25, right: 40, left: 15, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.gridLine} />
              <XAxis
                dataKey="year"
                stroke={CHART_COLORS.textMuted}
                tick={{ fill: CHART_COLORS.textMuted, fontSize: 11 }}
              />
              <YAxis
                stroke={CHART_COLORS.textMuted}
                tick={{ fill: CHART_COLORS.textMuted, fontSize: 11 }}
                scale={isLogScale ? "log" : "auto"}
                domain={isLogScale ? chartCYAxis.logDomain : chartCYAxis.domain}
                ticks={isLogScale ? chartCYAxis.logTicks : chartCYAxis.ticks}
                tickFormatter={(val) => {
                  if (val === 0) return "0";
                  if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
                  if (val >= 1000) return `${(val / 1000).toFixed(0)}k`;
                  return val.toString();
                }}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const isPartial = label === "2026";
                  return (
                    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs shadow-xl space-y-1.5">
                      <div className="flex items-center justify-between gap-4 border-b border-slate-800 pb-1">
                        <strong className="text-slate-200">Year {label}</strong>
                        {isPartial && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-500/20 text-red-300 font-semibold border border-red-500/30">
                            Partial Year
                          </span>
                        )}
                      </div>
                      {payload.map((entry) => (
                        <div key={entry.name} className="flex justify-between gap-4">
                          <span style={{ color: entry.color }}>{entry.name}:</span>
                          <span className="font-semibold text-slate-100">
                            {entry.value !== null && entry.value !== undefined
                              ? Number(entry.value).toLocaleString()
                              : "No observations"}
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "10px", fontSize: "12px" }}
                formatter={(value) => <span className="text-slate-300">{value}</span>}
              />
              <ReferenceLine
                x="2026"
                stroke="#ef4444"
                strokeDasharray="4 4"
                label={{
                  value: "2026 (partial year)",
                  fill: "#f87171",
                  fontSize: 11,
                  position: "insideTopRight",
                  offset: 12,
                }}
              />
              <Line
                name="MODIS Detections"
                type="linear"
                dataKey="MODIS"
                stroke={CHART_COLORS.modis}
                strokeWidth={2.5}
                dot={renderDot(CHART_COLORS.modis)}
                connectNulls={false}
              />
              <Line
                name="VIIRS Detections"
                type="linear"
                dataKey="VIIRS"
                stroke={CHART_COLORS.viirs}
                strokeWidth={2.5}
                dot={renderDot(CHART_COLORS.viirs)}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Region-Specific Coverage Note & Log Scale Gap Notice */}
        <div className="mt-3 space-y-2 border-t border-slate-800/80 pt-3 text-xs text-slate-400">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p>
              <span className="font-semibold text-slate-300">
                Observation Coverage for {REGION_LABELS[selectedRegion] || selectedRegion}:
              </span>{" "}
              {regionSensorBounds.modisMin !== null
                ? `MODIS observations span ${regionSensorBounds.modisMin}–${regionSensorBounds.modisMax}.`
                : "No MODIS data."}{" "}
              VIIRS observations span {regionSensorBounds.viirsMin}–{regionSensorBounds.viirsMax}. Counts are
              reported separately by sensor and are never summed.
            </p>
            <span className="text-red-400 font-mono text-[11px] bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded">
              * 2026 hollow marker: partial calendar year
            </span>
          </div>
          <p className="text-amber-300/90 text-xs">
            2026 is a partial year (data to Nov 2026), so it shouldn't be compared with full years. A zero means no retained detections in the cleaned data, not necessarily no fire.
          </p>
          {isLogScale && (
            <p className="text-amber-300/90 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded inline-block">
              <strong>Log Scale Note:</strong> Years with 0 detections cannot be represented on a logarithmic scale
              and are shown as visual gaps in the line plot.
            </p>
          )}
        </div>
      </Card>

      {/* FULL COMPARISON TABLE */}
      <Card
        eyebrow="Raw Ground Truth Metrics"
        title="Cross-Region Comparison Dataset (region_comparison.csv)"
      >
        <div className="overflow-x-auto mt-4 rounded border border-slate-800">
          <table className="w-full text-left text-xs text-slate-300 divide-y divide-slate-800">
            <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider font-mono text-[11px]">
              <tr>
                <th className="px-3 py-2.5">region</th>
                <th className="px-3 py-2.5">cell_size</th>
                <th className="px-3 py-2.5 text-right">rows</th>
                <th className="px-3 py-2.5 text-right">modis_cells_2012_2026</th>
                <th className="px-3 py-2.5 text-right">viirs_cells_2012_2026</th>
                <th className="px-3 py-2.5 text-right">cells_seen_by_both</th>
                <th className="px-3 py-2.5 text-right">modis_cell_days</th>
                <th className="px-3 py-2.5 text-right">viirs_also</th>
                <th className="px-3 py-2.5 text-right">viirs_only</th>
                <th className="px-3 py-2.5 text-right">modis_only</th>
                <th className="px-3 py-2.5 text-right">share_modis_seen_by_viirs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70 bg-slate-950/40">
              {comparisonData.map((row) => (
                <tr key={`${row.region}_${row.cell_size}`} className="hover:bg-slate-900/50 transition-colors">
                  <td className="px-3 py-2 font-medium text-slate-200">
                    {row.region}
                    <span className="block text-[10px] text-slate-500 font-sans">
                      {REGION_LABELS[row.region] || ""}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-cyan-400">{row.cell_size}°</td>
                  <td className="px-3 py-2 text-right font-mono">{row.rows.toLocaleString()}</td>
                  <td className="px-3 py-2 text-right font-mono text-orange-300">
                    {row.modis_cells_2012_2026.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-cyan-300">
                    {row.viirs_cells_2012_2026.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-amber-300">
                    {row.cells_seen_by_both.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{row.modis_cell_days.toLocaleString()}</td>
                  <td className="px-3 py-2 text-right font-mono text-emerald-400 font-semibold">
                    {row.viirs_also.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-slate-400">
                    {row.viirs_only.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-slate-400">
                    {row.modis_only.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-bold text-cyan-300">
                    {row.share_modis_seen_by_viirs.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Palisades Specific Footnote */}
        <div className="mt-4 p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
          <Info size={17} className="text-amber-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <span className="font-semibold text-amber-300">Palisades Footnote:</span> One Palisades cell near -118.72,
            34.15 shows ~119 night-time, low-FRP VIIRS detections across 15 years and looks like a fixed heat source
            (under review).
          </p>
        </div>
      </Card>
    </div>
  );
}
