import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  AreaChart as AreaIcon,
  BarChart3,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronsUpDown,
  CircleHelp,
  Database,
  Flame,
  Globe2,
  Grid3X3,
  Info,
  Layers3,
  Menu,
  Orbit,
  PanelLeftClose,
  PanelLeftOpen,
  Radio,
  Ruler,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FireMap } from "./components/FireMap";
import {
  loadDashboardData,
  type HarmonizedMetricSeries,
  type HarmonizedSummary,
} from "./dashboardData";
import { Card, ChartTooltip, DemoBadge, EmptyState, Status } from "./components/UI";
import {
  calendarYears,
  hotspots,
  monthlyData,
  pageNames,
  sensorTimeline,
  trendData,
  type Hotspot,
  type PageName,
} from "./data";


const navIcons = [Grid3X3, Globe2, CalendarDays, Layers3, AreaIcon, AlertTriangle, ShieldCheck];
const chartColors = {
  modis: "#ff7547",
  viirs: "#36c9f4",
  harmonized: "#ffb84d",
  baseline: "#75859a",
};
const MODEL_OUTPUT_DISCLAIMER = "Experimental Model Output (In-Sample Calibration)";

type GlobalFilters = { region: string; range: string };

function isHotspotInRegion(hotspot: Hotspot, region: string): boolean {
  if (!region || region === "Global" || region === "Western United States") return true;
  if (region === "California") {
    return (
      hotspot.place.includes("California") ||
      hotspot.place === "Sierra Nevada" ||
      hotspot.place === "Klamath"
    );
  }
  if (region === "Pacific Northwest") {
    return (
      hotspot.place === "Oregon" || hotspot.place === "Washington" || hotspot.place === "Idaho"
    );
  }
  return true;
}

function PageIntro({
  kicker,
  title,
  text,
  badge = true,
  children,
}: {
  kicker: string;
  title: string;
  text: string;
  badge?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-intro">
      <div>
        <div className="intro-kicker">
          <span>{kicker}</span>
          {badge && <DemoBadge />}
        </div>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
      {children && <div className="intro-actions">{children}</div>}
    </div>
  );
}

function TrendChart({
  type = "overview",
  height = 260,
  range = "Jan 2000 — Aug 2024",
  yearlyData,
}: {
  type?: "overview" | "harmonized";
  height?: number;
  range?: string;
  yearlyData?: { year: number; detections: number }[];
}) {
  const [visible, setVisible] = useState({
    modis: true,
    viirs: true,
    harmonized: true,
    uncertainty: true,
  });
    const items =
    type === "overview" ? ["detections"] : ["modis", "viirs", "harmonized", "uncertainty"];

  const chartData = useMemo(() => {
    if (type === "overview") {
      return (yearlyData ?? []).map((item) => ({
        year: String(item.year),
        detections: item.detections,
      }));
    }

    if (range === "2024 only") {
      return trendData.filter((d) => Number(d.year) >= 2023);
    }
    if (range === "Last 12 months") {
      return trendData.filter((d) => Number(d.year) >= 2021);
    }
    return trendData;
  }, [range, type, yearlyData]);
  
  return (
    <>
      <div className="chart-legend">
        {items.map((item) => (
          <button
            key={item}
            className={!visible[item as keyof typeof visible] ? "muted" : ""}
            onClick={() =>
              setVisible({ ...visible, [item]: !visible[item as keyof typeof visible] })
            }
          >
            <i
              style={{
                background:
                  item === "uncertainty"
                    ? "#ffb84d55"
                    : chartColors[item as keyof typeof chartColors],
              }}
            />
            {item}
          </button>
        ))}
      </div>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData as any} margin={{ top: 16, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="#233142" vertical={false} />
            <XAxis
              dataKey="year"
              tick={{ fill: "#77879b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis tick={{ fill: "#77879b", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            {type === "harmonized" && visible.uncertainty && (
              <Area
                dataKey="high"
                name="Upper bound"
                stroke="none"
                fill="#ffb84d"
                fillOpacity={0.08}
              />
            )}
            {type === "harmonized" && visible.uncertainty && (
              <Area
                dataKey="low"
                name="Lower bound"
                stroke="none"
                fill="#09121e"
                fillOpacity={0.9}
              />
            )}
            {visible.modis && (
              <Line
                type="monotone"
                dataKey="modis"
                name="MODIS raw"
                stroke={chartColors.modis}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
            )}
            {visible.viirs && (
              <Line
                type="monotone"
                dataKey="viirs"
                name="VIIRS raw"
                stroke={chartColors.viirs}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
            )}
            {type === "harmonized" && visible.harmonized && (
              <Line
                type="monotone"
                dataKey="harmonized"
                name="Harmonized estimate"
                stroke={chartColors.harmonized}
                strokeWidth={3}
                dot={false}
                connectNulls={false}
              />
            )}
            {type === "harmonized" && chartData.some((d) => d.year === "2013") && (
              <ReferenceLine
                x="2013"
                stroke="#8796a9"
                strokeDasharray="4 4"
                label={{
                  value: "Overlap calibration only",
                  fill: "#8796a9",
                  fontSize: 10,
                  position: "insideTopRight",
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}

function MonthlyChart({
  comparison = false,
  anomaly = false,
  height = 230,
}: {
  comparison?: boolean;
  anomaly?: boolean;
  height?: number;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {anomaly ? (
          <ComposedChart data={monthlyData} margin={{ top: 10, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="#233142" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fill: "#77879b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis tick={{ fill: "#77879b", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="baseline"
              fill="#64748b"
              fillOpacity={0.12}
              stroke="#77879b"
              strokeDasharray="4 4"
            />
            <Line
              type="monotone"
              dataKey="current"
              stroke="#ff7b45"
              strokeWidth={2.5}
              dot={{ r: 2, fill: "#ff7b45" }}
            />
          </ComposedChart>
        ) : (
          <BarChart data={monthlyData} margin={{ top: 10, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="#233142" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fill: "#77879b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis tick={{ fill: "#77879b", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            {comparison ? (
              <>
                <Bar dataKey="modis" fill={chartColors.modis} radius={[3, 3, 0, 0]} />
                <Bar dataKey="viirs" fill={chartColors.viirs} radius={[3, 3, 0, 0]} />
              </>
            ) : (
              <Bar dataKey="current" radius={[3, 3, 0, 0]}>
                {monthlyData.map((item) => (
                  <Cell
                    key={item.month}
                    fill={
                      item.current > 110 ? "#ff594d" : item.current > 70 ? "#ff8a49" : "#b86238"
                    }
                  />
                ))}
              </Bar>
            )}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

function HarmonizedMetricCharts({
  series,
  periodLabel,
}: {
  series: HarmonizedMetricSeries[];
  periodLabel: "Year" | "Month";
}) {
  return (
    <div className="content-grid two">
      <Card
        title="Observed and estimated detections"
        eyebrow={`Cell-day totals by ${periodLabel.toLowerCase()}`}
      >
        <div style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#233142" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#77879b", fontSize: 10 }} />
              <YAxis tick={{ fill: "#77879b", fontSize: 10 }} />
              <Tooltip content={<ChartTooltip modelOutputDisclaimer />} />
              <Legend
                formatter={(value) => <span className="chart-legend-label">{value}</span>}
              />
              <Line
                type="monotone"
                dataKey="observedModisDetections"
                name="Observed MODIS"
                stroke={chartColors.modis}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="observedViirsDetections"
                name="Observed VIIRS"
                stroke={chartColors.viirs}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="estimatedViirsDetections"
                name={`Estimated VIIRS · ${MODEL_OUTPUT_DISCLAIMER}`}
                stroke={chartColors.harmonized}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card
        title="Observed and calibrated FRP"
        eyebrow={`Mean FRP by ${periodLabel.toLowerCase()} · MW`}
      >
        <div style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#233142" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#77879b", fontSize: 10 }} />
              <YAxis tick={{ fill: "#77879b", fontSize: 10 }} />
              <Tooltip content={<ChartTooltip modelOutputDisclaimer />} />
              <Legend
                formatter={(value) => <span className="chart-legend-label">{value}</span>}
              />
              <Line
                type="monotone"
                dataKey="observedModisFrp"
                name="Observed MODIS FRP"
                stroke={chartColors.modis}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="observedViirsFrp"
                name="Observed VIIRS FRP"
                stroke={chartColors.viirs}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="estimatedCalibratedFrp"
                name={`Calibrated FRP · ${MODEL_OUTPUT_DISCLAIMER}`}
                stroke={chartColors.harmonized}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

function Overview({
  setPage,
  filters,
  projectData,
}: {
  setPage: (page: PageName) => void;
  filters: GlobalFilters;
  projectData: Awaited<ReturnType<typeof loadDashboardData>>;
}) {
  const regionKey =
    filters.region === "Palisades, California"
      ? "palisades_la"
      : "western_ghats_karnataka";

  const regionStats = projectData.dashboard.regions[regionKey];
  const regionalCells = projectData.map.regions[regionKey];
  const [selected, setSelected] = useState<Hotspot | null>(null);

  return (
    <>
      <PageIntro
        kicker="Satellite fire intelligence"
        title="Understand Fire Activity. Across Time. Across Sensors."
        text="Explore 24 years of MODIS and VIIRS observations through a transparent, harmonized view of fire activity."
      >
        <button className="button primary" onClick={() => setPage("Fire Explorer")}>
          <Globe2 size={15} /> Open Fire Explorer
        </button>
      </PageIntro>
      
<div className="kpi-grid">
  {[
    [
      "Total recorded detections",
      regionStats.total_detections.toLocaleString("en-IN"),
      `${regionStats.unique_detection_days.toLocaleString("en-IN")} observation days`,
      Flame,
    ],
    [
      "Observation period",
      `${regionStats.year_start}–${regionStats.year_end}`,
      `${regionStats.date_start} to ${regionStats.date_end}`,
      CalendarDays,
    ],
    [
      "Grid cells analysed",
      regionStats.unique_grid_cells.toLocaleString("en-IN"),
      `${projectData.dashboard.cell_size_degrees}° grid resolution`,
      Target,
    ],
    [
      "Mean fire radiative power",
      regionStats.frp.mean == null
        ? "Unavailable"
        : `${regionStats.frp.mean.toFixed(2)} MW`,
      `${regionStats.frp.available_records.toLocaleString("en-IN")} records with FRP`,
      Radio,
    ],
  ].map(([label, value, note, Icon]) => (
    <Card key={label as string} className="kpi-card">
      <div className="kpi-top">
        <span>{label as string}</span>
        <Icon size={17} />
      </div>
      <strong>{value as string}</strong>
      <small>{note as string}</small>
    </Card>
  ))}
</div>

      <Card
        className="map-card"
        eyebrow={`Geospatial overview · ${filters.region}`}
        title="Active fire observation density"
        action={
          <button className="text-button" onClick={() => setPage("Fire Explorer")}>
            Explore map <ChevronLeft className="rotate-180" size={14} />
          </button>
        }
      >
        <FireMap
          hotspots={[]}
          cells={regionalCells}
          onSelect={setSelected}
          selected={selected}
          height={455}
        />
        {selected && (
          <div className="map-selection-strip">
            <span className={`sensor-icon ${selected.family.toLowerCase()}`}>
              <Orbit size={15} />
            </span>
            <div>
              <strong>{selected.place}</strong>
              <small>
                {selected.date} · {selected.time}
              </small>
            </div>
            <div>
              <span>Sensor</span>
              <strong>{selected.sensor}</strong>
            </div>
            <div>
              <span>Confidence</span>
              <strong>{selected.confidence}%</strong>
            </div>
            <div>
              <span>FRP</span>
              <strong>{selected.frp} MW</strong>
            </div>
            <button onClick={() => setSelected(null)}>
              <X size={15} />
            </button>
          </div>
        )}
      </Card>
      <div className="content-grid two-one">
        <Card
          title="Historical fire activity"
          eyebrow="Normalized activity index"
          action={<DemoBadge />}
        >
          <TrendChart range={filters.range}
          yearlyData={regionStats.yearly_trend}
          />
        </Card>
        <Card
          title="Monthly distribution"
          eyebrow="2024 observation profile"
          action={<DemoBadge />}
        >
          <MonthlyChart />
        </Card>
      </div>
      <div className="content-grid three">
        <Card title="Recent anomalies" eyebrow={filters.region}>
          <div className="summary-list">
            <div>
              <span className="severity high">HIGH</span>
              <p>
                <strong>Northern California</strong>
                <small>Aug 2024 · 96th percentile</small>
              </p>
              <b>+42%</b>
            </div>
            <div>
              <span className="severity elevated">ELEVATED</span>
              <p>
                <strong>Central Oregon</strong>
                <small>Jul 2024 · 87th percentile</small>
              </p>
              <b>+19%</b>
            </div>
          </div>
        </Card>
        <Card title="Data quality" eyebrow="Selected period">
          <div className="quality-ring">
            <div>
              <strong>94.2%</strong>
              <span>coverage</span>
            </div>
            <ul>
              <li>
                <i className="good" /> 8,416 valid days
              </li>
              <li>
                <i className="partial" /> 134 partial days
              </li>
              <li>
                <i className="missing" /> 82 missing days
              </li>
            </ul>
          </div>
        </Card>
        <Card title="Processing status" eyebrow="Pipeline health">
          <div className="pipeline">
            <Status type="verified">Standard product current</Status>
            <div>
              <span>Last completed</span>
              <strong>18 Aug 2024, 23:40 UTC</strong>
            </div>
            <div>
              <span>Calibration model</span>
              <strong>Experimental v0.8</strong>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

function FireExplorer({
  filters,
  onFiltersChange,
}: {
  filters: GlobalFilters;
  onFiltersChange: (filters: GlobalFilters) => void;
}) {
  const [selected, setSelected] = useState<Hotspot | null>(hotspots[0]);
  const [sensor, setSensor] = useState("All sensors");
  const [confidence, setConfidence] = useState(60);
  const [heatmap, setHeatmap] = useState(false);
  const [drawMode, setDrawMode] = useState(false);
  const [aoiPoints, setAoiPoints] = useState<Array<[number, number]>>([]);
  const [filtersOpen, setFiltersOpen] = useState(true);

  const filtered = useMemo(
    () =>
      hotspots.filter(
        (point) =>
          isHotspotInRegion(point, filters.region) &&
          (sensor === "All sensors" || point.sensor === sensor) &&
          point.confidence >= confidence,
      ),
    [filters.region, sensor, confidence],
  );

  const reset = () => {
    setSensor("All sensors");
    setConfidence(60);
    onFiltersChange({ ...filters, region: "Western United States" });
  };
  return (
    <div className="explorer-page">
      <PageIntro
        kicker="Geospatial workspace"
        title="Fire Explorer"
        text="Inspect demo satellite observations and define an area of interest. Filters update the map and summary together."
      />
      <div className={`explorer-layout ${!filtersOpen ? "filters-closed" : ""}`}>
        <Card
          className="filter-panel"
          title="Observation filters"
          action={
            <button
              className="icon-button mobile-filter-close"
              onClick={() => setFiltersOpen(false)}
            >
              <X size={16} />
            </button>
          }
        >
          <label className="field-label">Observation date</label>
          <div className="date-pair">
            <input type="date" defaultValue="2024-08-01" />
            <input type="date" defaultValue="2024-08-18" />
          </div>
          <label className="field-label">Sensor platform</label>
          <select value={sensor} onChange={(e) => setSensor(e.target.value)}>
            <option>All sensors</option>
            <option>MODIS Terra</option>
            <option>MODIS Aqua</option>
            <option>VIIRS S-NPP</option>
            <option>VIIRS NOAA-20</option>
            <option>VIIRS NOAA-21</option>
          </select>
          <label className="field-label">Day / night</label>
          <div className="segmented">
            <button className="active">All</button>
            <button>Day</button>
            <button>Night</button>
          </div>
          <div className="range-head">
            <label className="field-label">Minimum confidence</label>
            <strong>{confidence}%</strong>
          </div>
          <input
            className="range"
            type="range"
            min="60"
            max="100"
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
          />
          <div className="range-head">
            <label className="field-label">Fire radiative power</label>
            <span>0 — 150+ MW</span>
          </div>
          <input className="range" type="range" min="0" max="150" defaultValue="10" />
          <label className="field-label">Activity type</label>
          <select defaultValue="All classifications">
            <option>All classifications</option>
            <option>Vegetation</option>
            <option>Agricultural</option>
            <option>Unknown</option>
          </select>
          <label className="field-label">Area of interest</label>
          <select
            value={filters.region}
            onChange={(e) => onFiltersChange({ ...filters, region: e.target.value })}
          >
            <option>Western United States</option>
            <option>California</option>
            <option>Pacific Northwest</option>
            <option>Global</option>
          </select>
          <button
            className={`button ${drawMode ? "primary" : "secondary"} full`}
            onClick={() => setDrawMode(!drawMode)}
          >
            <Ruler size={15} /> {drawMode ? "Finish drawing AOI" : "Draw custom AOI"}
          </button>
          {aoiPoints.length > 0 && (
            <small className="aoi-count">{aoiPoints.length} AOI vertices selected</small>
          )}
          <button className="text-button reset" onClick={reset}>
            Reset all filters
          </button>
        </Card>
        <div className="explorer-map">
          {!filtersOpen && (
            <button
              className="floating-filter button secondary"
              onClick={() => setFiltersOpen(true)}
            >
              <SlidersHorizontal size={15} /> Filters
            </button>
          )}
          <div className="map-toolbar">
            <div>
              <button className={!heatmap ? "active" : ""} onClick={() => setHeatmap(false)}>
                Hotspots
              </button>
              <button className={heatmap ? "active" : ""} onClick={() => setHeatmap(true)}>
                Heatmap
              </button>
            </div>
            <span>{filtered.length} demo observations</span>
          </div>
          {filtered.length ? (
            <FireMap
              hotspots={filtered}
              selected={selected}
              onSelect={setSelected}
              heatmap={heatmap}
              drawMode={drawMode}
              onDrawPoint={(point) => setAoiPoints([...aoiPoints, point])}
              height="100%"
            />
          ) : (
            <EmptyState reset={reset} />
          )}
        </div>
        <Card
          className="detail-panel"
          title="Observation detail"
          action={
            selected && (
              <button className="icon-button" onClick={() => setSelected(null)}>
                <X size={15} />
              </button>
            )
          }
        >
          {selected ? (
            <>
              <div className="detail-hero">
                <span className={`sensor-icon ${selected.family.toLowerCase()}`}>
                  <Orbit size={19} />
                </span>
                <div>
                  <Status type={selected.confidence > 85 ? "verified" : "partial"}>
                    {selected.confidence > 85 ? "High confidence" : "Nominal confidence"}
                  </Status>
                  <h3>{selected.place}</h3>
                  <p>
                    {selected.lat.toFixed(4)}°, {selected.lng.toFixed(4)}°
                  </p>
                </div>
              </div>
              <dl className="detail-list">
                <div>
                  <dt>Platform</dt>
                  <dd>{selected.sensor}</dd>
                </div>
                <div>
                  <dt>Observation</dt>
                  <dd>
                    {selected.date}
                    <small>{selected.time}</small>
                  </dd>
                </div>
                <div>
                  <dt>Fire radiative power</dt>
                  <dd>{selected.frp} MW</dd>
                </div>
                <div>
                  <dt>Day / night</dt>
                  <dd>{selected.period}</dd>
                </div>
                <div>
                  <dt>Activity type</dt>
                  <dd>{selected.type}</dd>
                </div>
                <div>
                  <dt>Dataset status</dt>
                  <dd>
                    <DemoBadge />
                  </dd>
                </div>
              </dl>
              <div className="notice">
                <Info size={15} />
                <p>
                  This is a simulated observation for interface demonstration. It is not a live fire
                  alert.
                </p>
              </div>
            </>
          ) : (
            <div className="blank-detail">
              <Target size={25} />
              <p>Select a hotspot to inspect its observation record.</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function HistoricalCalendar({
  filters,
  onFiltersChange,
}: {
  filters: GlobalFilters;
  onFiltersChange: (filters: GlobalFilters) => void;
}) {
  const [year, setYear] = useState(2024);
  const [view, setView] = useState<"Monthly" | "Yearly">("Monthly");
  const monthNames = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const calendar = useMemo(
    () =>
      monthNames.map((month, index) => ({
        month,
        value:
          index === 2 && year === 2001
            ? null
            : Math.round(18 + Math.abs(Math.sin((year + index) * 1.7)) * 116),
        coverage: index === 2 && year === 2001 ? 0 : 86 + ((year + index) % 14),
      })),
    [year],
  );

  const filteredTrendData = useMemo(() => {
    if (filters.range === "2024 only") {
      return trendData.filter((d) => Number(d.year) >= 2023);
    }
    if (filters.range === "Last 12 months") {
      return trendData.filter((d) => Number(d.year) >= 2021);
    }
    return trendData;
  }, [filters.range]);
  return (
    <>
      <PageIntro
        kicker="Historical archive"
        title="Fire Activity Calendar"
        text="Explore seasonal activity since 2000 while keeping zero detections distinct from missing observations."
      >
        <div className="control-row">
          <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {calendarYears.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <div className="segmented">
            <button
              className={view === "Monthly" ? "active" : ""}
              onClick={() => setView("Monthly")}
            >
              Monthly
            </button>
            <button className={view === "Yearly" ? "active" : ""} onClick={() => setView("Yearly")}>
              Yearly
            </button>
          </div>
        </div>
      </PageIntro>
      <Card
        title={
          view === "Monthly" ? `${year} monthly activity profile` : "Year-by-year activity profile"
        }
        eyebrow={`Normalized observation index · ${filters.region}`}
        action={
          <select
            className="compact-select"
            value={filters.region}
            onChange={(e) => onFiltersChange({ ...filters, region: e.target.value })}
          >
            <option>Western United States</option>
            <option>California</option>
            <option>Pacific Northwest</option>
            <option>Global</option>
          </select>
        }
      >
        {view === "Monthly" ? (
          <div className="calendar-grid">
            {calendar.map((item) => (
              <div
                key={item.month}
                className={`calendar-cell level-${item.value === null ? "missing" : Math.min(4, Math.floor(item.value / 30))}`}
                title={`${item.month} ${year} · ${item.value === null ? "Missing observation" : `${item.value} activity index`} · ${item.coverage}% coverage`}
              >
                <span>{item.month}</span>
                <strong>{item.value ?? "—"}</strong>
                <small>{item.value === null ? "Missing" : `${item.coverage}% coverage`}</small>
              </div>
            ))}
          </div>
        ) : (
          <div className="year-grid">
            {calendarYears.map((item) => (
              <button
                key={item}
                className={`year-cell level-${Math.min(4, (item * 7) % 5)} ${item === year ? "selected" : ""}`}
                onClick={() => {
                  setYear(item);
                  setView("Monthly");
                }}
              >
                <span>{item}</span>
                <strong>{42 + ((item * 13) % 92)}</strong>
              </button>
            ))}
          </div>
        )}
        <div className="scale">
          <span>Lower activity</span>
          {[0, 1, 2, 3, 4].map((item) => (
            <i key={item} className={`level-${item}`} />
          ))}
          <span>Higher activity</span>
          <i className="level-missing" />
          <span>Missing</span>
        </div>
      </Card>
      <div className="content-grid two-one">
        <Card
          title="Historical yearly trend"
          eyebrow={
            filters.range === "2024 only"
              ? "2024 · Active range"
              : filters.range === "Last 12 months"
                ? "2023 — 2024 · Active range"
                : "2000 — 2024"
          }
        >
          <div style={{ height: 265 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={filteredTrendData} margin={{ left: -20, right: 4, top: 12 }}>
                <defs>
                  <linearGradient id="historyFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stopColor="#ff7547" stopOpacity=".28" />
                    <stop offset="1" stopColor="#ff7547" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#233142" vertical={false} />
                <XAxis
                  dataKey="year"
                  tick={{ fill: "#77879b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis tick={{ fill: "#77879b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area dataKey="modis" stroke="#ff7547" fill="url(#historyFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Period highlights" eyebrow={`${year} compared with average`}>
          <div className="metric-stack">
            <div>
              <span>Highest activity</span>
              <strong>August</strong>
              <small>151 index · +38% vs avg.</small>
            </div>
            <div>
              <span>Lowest activity</span>
              <strong>January</strong>
              <small>23 index · −4% vs avg.</small>
            </div>
            <div>
              <span>Annual deviation</span>
              <strong className="warm">+12.4%</strong>
              <small>Coverage adjusted</small>
            </div>
          </div>
          <div className="notice">
            <Info size={15} />
            <p>
              Grey hatched cells are unavailable observations. A value of 0 means valid coverage
              with no detections.
            </p>
          </div>
        </Card>
      </div>
    </>
  );
}

function SensorComparison({
  summary,
}: {
  summary: HarmonizedSummary;
}) {
  return (
    <>
      <PageIntro
        kicker="Cross-sensor analysis"
        title="Regional Comparison"
        text="Compare observed MODIS and VIIRS detections with modeled VIIRS counts and calibrated FRP from the harmonization export."
        badge={false}
      />
      <div className="science-warning">
        <AlertTriangle size={19} />
        <div>
          <strong>{MODEL_OUTPUT_DISCLAIMER}</strong>
          <p>
            {summary.region.replace(/_/g, " ")} observed measurements are shown separately from
            estimated VIIRS counts and calibrated FRP. Model values are from in-sample calibration,
            are not independent validation, and should be interpreted as experimental.
          </p>
        </div>
      </div>
      <HarmonizedMetricCharts series={summary.timeseries.monthly} periodLabel="Month" />
      <small className="center-note">
        Monthly totals and means cover available dates in the exported dataset.
      </small>
    </>
  );
}

function HarmonizedActivity({ summary }: { summary: HarmonizedSummary }) {
  const observedShare =
    summary.rows.total === 0 ? 0 : (summary.rows.observed / summary.rows.total) * 100;
  const estimatedShare =
    summary.rows.total === 0 ? 0 : (summary.rows.estimated / summary.rows.total) * 100;

  return (
    <>
      <PageIntro
        kicker="Core methodology"
        title="Harmonized Fire Activity"
        text="Observed grid records and model-estimated values from the latest Western Ghats harmonization export."
        badge={false}
      >
        <Status type="experimental">Experimental · in-sample output</Status>
      </PageIntro>
      <div className="science-warning experiment">
        <Sparkles size={19} />
        <div>
          <strong>{MODEL_OUTPUT_DISCLAIMER}</strong>
          <p>
            Estimated counts and calibrated FRP are loaded from the latest harmonization summary.
            These values use the {summary.countModel} count model and {summary.frpMethod} FRP
            calibration; they are in-sample output, not independent validation.
          </p>
        </div>
      </div>
      <div className="content-grid two-one">
        <Card
          title="Observed and estimated rows"
          eyebrow={summary.region.replace(/_/g, " ")}
        >
          <div className="calibration-stat">
            <div>
              <span>Observed</span>
              <strong>{summary.rows.observed.toLocaleString("en-IN")}</strong>
            </div>
            <div>
              <span>Estimated</span>
              <strong>{summary.rows.estimated.toLocaleString("en-IN")}</strong>
            </div>
            <div>
              <span>Total exported</span>
              <strong>{summary.rows.total.toLocaleString("en-IN")}</strong>
            </div>
          </div>
          <div className="source-share" aria-label="Observed and estimated row proportions">
            <div className="source-share-bar">
              <span style={{ width: `${observedShare}%` }} />
              <i style={{ width: `${estimatedShare}%` }} />
            </div>
            <div>
              <span>Observed {observedShare.toFixed(1)}%</span>
              <span>Estimated {estimatedShare.toFixed(1)}%</span>
            </div>
          </div>
        </Card>
        <Card title="Observed vs. estimated values" eyebrow="Per cell-day row">
          <div className="calibration-stat">
            <div>
              <span>
                Observed mean VIIRS detections ·{" "}
                {summary.metrics.observed.viirsDetections.count.toLocaleString("en-IN")} rows
              </span>
              <strong>{summary.metrics.observed.viirsDetections.mean.toFixed(2)}</strong>
            </div>
            <div>
              <span>
                Estimated mean VIIRS detections ·{" "}
                {summary.metrics.estimated.predictedViirsDetections.count.toLocaleString("en-IN")} rows
              </span>
              <strong>
                {summary.metrics.estimated.predictedViirsDetections.mean.toFixed(2)}
              </strong>
            </div>
            <div>
              <span>
                Observed mean VIIRS FRP ·{" "}
                {summary.metrics.observed.meanFrp.count.toLocaleString("en-IN")} rows
              </span>
              <strong>{summary.metrics.observed.meanFrp.mean.toFixed(2)} MW</strong>
            </div>
            <div>
              <span>
                Estimated calibrated FRP ·{" "}
                {summary.metrics.estimated.calibratedFrp.count.toLocaleString("en-IN")} rows
              </span>
              <strong>{summary.metrics.estimated.calibratedFrp.mean.toFixed(2)} MW</strong>
            </div>
          </div>
          <small className="center-note">
            Summary generated {new Date(summary.createdAt).toLocaleString()}
          </small>
        </Card>
      </div>
      <HarmonizedMetricCharts series={summary.timeseries.yearly} periodLabel="Year" />
      <Card title="How Harmonization Works" eyebrow="Transparent six-stage workflow">
        <div className="process-grid">
          {[
            [
              "01",
              "Collect & clean",
              "Ingest observations and flag invalid or incomplete records.",
            ],
            [
              "02",
              "Standardise",
              "Aggregate observations across common spatial and temporal units.",
            ],
            [
              "03",
              "Account for sensors",
              "Represent differences in resolution, timing and sensitivity.",
            ],
            [
              "04",
              "Calibrate overlap",
              "Fit regional relationships only where both sensors observe.",
            ],
            ["05", "Validate", "Evaluate performance against held-out months and regions."],
            ["06", "Estimate", "Generate harmonized values with explicit uncertainty intervals."],
          ].map(([number, title, text]) => (
            <div key={number}>
              <span>{number}</span>
              <h4>{title}</h4>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

function AnomalyDetection({
  filters,
  onFiltersChange,
}: {
  filters: GlobalFilters;
  onFiltersChange: (filters: GlobalFilters) => void;
}) {
  const [selectedMonth, setSelectedMonth] = useState("August 2024");
  return (
    <>
      <PageIntro
        kicker="Pattern intelligence"
        title="Anomaly Detection"
        text="Identify activity that differs from the historical seasonal pattern while accounting for data coverage."
      >
        <div className="control-row">
          <select
            value={filters.region}
            onChange={(e) => onFiltersChange({ ...filters, region: e.target.value })}
          >
            <option>Western United States</option>
            <option>California</option>
            <option>Pacific Northwest</option>
            <option>Global</option>
          </select>
          <input type="month" defaultValue="2024-08" />
        </div>
      </PageIntro>
      <div className="science-warning neutral">
        <Info size={19} />
        <p>
          <strong>An anomaly indicates activity that differs from the historical pattern.</strong>{" "}
          It is not automatically an emergency or a prediction of future fire.
        </p>
      </div>
      <div className="content-grid two-one">
        <Card
          title="Activity versus historical baseline"
          eyebrow={`Monthly normalized index · ${filters.region}`}
          action={<DemoBadge />}
        >
          <MonthlyChart anomaly height={310} />
        </Card>
        <Card title="Anomaly detail" eyebrow={selectedMonth}>
          <div className="anomaly-score">
            <span className="severity high">UNUSUALLY HIGH</span>
            <strong>
              96<sup>th</sup>
            </strong>
            <small>historical percentile</small>
          </div>
          <dl className="detail-list compact">
            <div>
              <dt>Region</dt>
              <dd>{filters.region}</dd>
            </div>
            <div>
              <dt>Observed activity</dt>
              <dd>151 index</dd>
            </div>
            <div>
              <dt>Historical baseline</dt>
              <dd>104 index</dd>
            </div>
            <div>
              <dt>Data coverage</dt>
              <dd>97.1%</dd>
            </div>
          </dl>
          <div className="notice">
            <Info size={15} />
            <p>
              Flagged because coverage-adjusted activity exceeded 96% of comparable August
              observations.
            </p>
          </div>
        </Card>
      </div>
      <Card title="Anomaly timeline" eyebrow="2024 monthly classification">
        <div className="anomaly-timeline">
          {monthlyData.map((item) => {
            const state =
              item.current > 120
                ? "high"
                : item.current > item.baseline * 1.15
                  ? "elevated"
                  : "normal";
            return (
              <button
                key={item.month}
                className={state}
                onClick={() => setSelectedMonth(`${item.month} 2024`)}
                title={`${item.month}: ${state}`}
              >
                <i />
                <span>{item.month}</span>
                <small>{state === "high" ? "Unusually high" : state}</small>
              </button>
            );
          })}
        </div>
        <div className="timeline-legend">
          <span>
            <i className="normal" /> Normal
          </span>
          <span>
            <i className="elevated" /> Elevated
          </span>
          <span>
            <i className="high" /> Unusually High
          </span>
          <span>
            <i className="insufficient" /> Insufficient data
          </span>
        </div>
      </Card>
    </>
  );
}

function DataQuality({ filters }: { filters: GlobalFilters }) {
  const [qualityYear, setQualityYear] = useState(2024);
  return (
    <>
      <PageIntro
        kicker="Transparency & reliability"
        title="Data Quality"
        text="Review source availability, missing records, processing modes, calibration status and known limitations."
      >
        <select
          value={qualityYear}
          onChange={(event) => setQualityYear(Number(event.target.value))}
        >
          {calendarYears
            .slice()
            .reverse()
            .map((year) => (
              <option key={year}>{year}</option>
            ))}
        </select>
      </PageIntro>
      <div className="quality-kpis">
        <div>
          <Status type="verified">Verified</Status>
          <strong>94.2%</strong>
          <span>Observation coverage</span>
        </div>
        <div>
          <Status type="partial">Partial</Status>
          <strong>134</strong>
          <span>Incomplete records</span>
        </div>
        <div>
          <Status type="missing">Missing</Status>
          <strong>82</strong>
          <span>Unavailable days</span>
        </div>
        <div>
          <Status type="experimental">Experimental</Status>
          <strong>v0.8</strong>
          <span>Calibration model</span>
        </div>
      </div>
      <Card
        title="Sensor & platform availability"
        eyebrow="Mission timeline · transitions shown explicitly"
        action={<span className="timeline-period">2000 — 2024</span>}
      >
        <div className="sensor-timeline">
          <div className="timeline-axis">
            <span>2000</span>
            <span>2006</span>
            <span>2012</span>
            <span>2018</span>
            <span>2024</span>
          </div>
          {sensorTimeline.map((sensor) => (
            <div className="sensor-row" key={sensor.name}>
              <div>
                <strong>{sensor.name}</strong>
                <small>{sensor.note}</small>
              </div>
              <div className="sensor-track">
                <i
                  style={{
                    left: `${((sensor.start - 2000) / 24) * 100}%`,
                    width: `${((sensor.end - sensor.start) / 24) * 100}%`,
                    background: sensor.color,
                  }}
                />
              </div>
              <span>{sensor.start}</span>
            </div>
          ))}
        </div>
      </Card>
      <div className="content-grid two-one">
        <Card
          title="Missing-data calendar"
          eyebrow={`${qualityYear} daily availability`}
          action={
            <div className="mini-legend">
              <i className="valid" /> Valid <i className="partial" /> Partial{" "}
              <i className="missing" /> Missing
            </div>
          }
        >
          <div className="missing-calendar">
            {Array.from({ length: 365 }, (_, index) => (
              <i
                key={index}
                className={
                  index % 47 === 0 || index % 89 === 0
                    ? "missing"
                    : index % 31 === 0
                      ? "partial"
                      : "valid"
                }
                title={`Day ${index + 1}: ${index % 47 === 0 ? "missing" : "valid"}`}
              />
            ))}
          </div>
        </Card>
        <Card title="Processing status" eyebrow="Current archive">
          <div className="processing-list">
            <div>
              <Database size={16} />
              <p>
                <span>Standard archive</span>
                <strong>Current to 31 Jul 2024</strong>
              </p>
              <Status type="verified">Verified</Status>
            </div>
            <div>
              <Radio size={16} />
              <p>
                <span>Near-real-time feed</span>
                <strong>Latency 3h 12m</strong>
              </p>
              <Status type="partial">Partial</Status>
            </div>
            <div>
              <Activity size={16} />
              <p>
                <span>Calibration</span>
                <strong>Regional model v0.8</strong>
              </p>
              <Status type="experimental">Not yet validated</Status>
            </div>
          </div>
        </Card>
      </div>
      <div className="content-grid two-one">
        <Card title="Observation coverage" eyebrow="Valid days by platform">
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={[
                  { name: "MODIS Terra", value: 96 },
                  { name: "MODIS Aqua", value: 94 },
                  { name: "VIIRS S-NPP", value: 97 },
                  { name: "VIIRS NOAA-20", value: 91 },
                  { name: "VIIRS NOAA-21", value: 82 },
                ]}
                margin={{ left: 20, right: 24 }}
              >
                <CartesianGrid stroke="#233142" horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={{ fill: "#77879b", fontSize: 11 }}
                  axisLine={false}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  tick={{ fill: "#aab6c6", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={100}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="value" fill="#36c9f4" radius={[0, 4, 4, 0]} barSize={12} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Quality warnings" eyebrow="Selected period">
          <div className="warnings-list">
            <div>
              <AlertTriangle size={16} />
              <p>
                <strong>NOAA-21 provisional archive</strong>
                <span>Recent records may be reprocessed.</span>
              </p>
            </div>
            <div>
              <Info size={16} />
              <p>
                <strong>MODIS Terra orbit drift</strong>
                <span>Observation timing changes after 2020.</span>
              </p>
            </div>
            <div>
              <AlertTriangle size={16} />
              <p>
                <strong>Regional calibration</strong>
                <span>Calibrated benchmark for {filters.region}.</span>
              </p>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

function Topbar({
  page,
  filters,
  setFilters,
  openSidebar,
}: {
  page: PageName;
  filters: GlobalFilters;
  setFilters: (filters: GlobalFilters) => void;
  openSidebar: () => void;
}) {
  return (
    <header className="topbar">
      <div className="topbar-title">
        <button className="mobile-menu" onClick={openSidebar}>
          <Menu size={19} />
        </button>
        <div>
          <span>FireTrace / {page}</span>
          <strong>{page}</strong>
        </div>
      </div>
      <div className="top-controls">
        <label>
          <Globe2 size={14} />
          <select
            value={filters.region}
            onChange={(e) => setFilters({ ...filters, region: e.target.value })}
          >
            <option>Western United States</option>
            <option>California</option>
            <option>Pacific Northwest</option>
            <option>Global</option>
          </select>
          <ChevronsUpDown size={12} />
        </label>
        <label>
          <CalendarDays size={14} />
          <select
            value={filters.range}
            onChange={(e) => setFilters({ ...filters, range: e.target.value })}
          >
            <option>Jan 2000 — Aug 2024</option>
            <option>Last 12 months</option>
            <option>2024 only</option>
          </select>
          <ChevronsUpDown size={12} />
        </label>
        <span className="data-online">
          <i /> Data systems nominal
        </span>
        <button className="profile" title="Profile">
          FT
        </button>
      </div>
    </header>
  );
}

function Sidebar({
  page,
  setPage,
  collapsed,
  setCollapsed,
  mobileOpen,
  closeMobile,
}: {
  page: PageName;
  setPage: (page: PageName) => void;
  collapsed: boolean;
  setCollapsed: (value: boolean) => void;
  mobileOpen: boolean;
  closeMobile: () => void;
}) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""} ${mobileOpen ? "mobile-open" : ""}`}>
      <div className="brand">
        <div className="brand-mark">
          <Orbit size={23} />
          <Flame size={12} />
        </div>
        {!collapsed && (
          <div>
            <strong>FIRETRACE</strong>
            <span>Satellite Intelligence</span>
          </div>
        )}
        <button className="mobile-sidebar-x" onClick={closeMobile}>
          <X size={18} />
        </button>
      </div>
      <nav>
        {pageNames.map((item, index) => {
          const Icon = navIcons[index];
          return (
            <button
              key={item}
              className={page === item ? "active" : ""}
              onClick={() => {
                setPage(item);
                closeMobile();
                window.scrollTo(0, 0);
              }}
              title={collapsed ? item : undefined}
            >
              <Icon size={18} />
              {!collapsed && <span>{item}</span>}
              {page === item && <i />}
            </button>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        <button>
          <CircleHelp size={18} />
          {!collapsed && <span>About FireTrace</span>}
        </button>
        <button>
          <Settings size={18} />
          {!collapsed && <span>Settings</span>}
        </button>
        <button className="collapse-button" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          {!collapsed && <span>Collapse sidebar</span>}
        </button>
        <div className="mission-status">
          <i />
          {!collapsed && (
            <span>
              <strong>MISSION STATUS</strong>All systems nominal
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}


export default function App() {
  const [page, setPage] = useState<PageName>("Overview");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const [projectData, setProjectData] = useState<Awaited<ReturnType<typeof loadDashboardData>> | null>(null);
  const [dataError, setDataError] = useState("");

  useEffect(() => {
    loadDashboardData()
      .then(setProjectData)
      .catch((error) => setDataError(error.message));
  }, []);

  const [filters, setFilters] = useState<GlobalFilters>({
    region: "Western Ghats, Karnataka",
    range: "All available data",
  });

  const content =
    page === "Overview" ? (
      <Overview setPage={setPage} filters={filters} projectData={projectData!} />
    ) : page === "Fire Explorer" ? (
      <FireExplorer filters={filters} onFiltersChange={setFilters} />
    ) : page === "Historical Calendar" ? (
      <HistoricalCalendar filters={filters} onFiltersChange={setFilters} />
    ) : page === "Regional Comparison" ? (
      <SensorComparison summary={projectData!.harmonizedSummary} />
    ) : page === "Harmonized Activity" ? (
      <HarmonizedActivity summary={projectData!.harmonizedSummary} />
    ) : page === "Anomaly Detection" ? (
      <AnomalyDetection filters={filters} onFiltersChange={setFilters} />
    ) : (
      <DataQuality filters={filters} />
    );

  if (dataError) {
    return <div className="app-shell">Unable to load FireTrace data: {dataError}</div>;
  }

  if (!projectData) {
    return <div className="app-shell">Loading real FireTrace data...</div>;
  }

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar
        page={page}
        setPage={setPage}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        closeMobile={() => setMobileOpen(false)}
      />
      <div className="app-main">
        <Topbar
          page={page}
          filters={filters}
          setFilters={setFilters}
          openSidebar={() => setMobileOpen(true)}
        />
        <main className={page === "Fire Explorer" ? "explorer-main" : ""}>
          {content}
          <footer>
            <span>FireTrace · Satellite Fire Intelligence</span>
            <span>NASA FIRMS · Project dataset</span>
          </footer>
        </main>
      </div>
      {mobileOpen && <button className="mobile-overlay" onClick={() => setMobileOpen(false)} />}
    </div>
  );
}
