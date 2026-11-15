import { useState, useEffect, lazy, Suspense } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  ChevronsUpDown,
  CircleHelp,
  Database,
  Flame,
  Globe2,
  Menu,
  Orbit,
  PanelLeftClose,
  PanelLeftOpen,
  Radio,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  X,
  RefreshCw,
  Home,
} from "lucide-react";
import {
  FiltersProvider,
  useFilters,
  REGION_OPTIONS,
  SATELLITE_OPTIONS,
  DATE_RANGE_OPTIONS,
  CONFIDENCE_OPTIONS,
} from "./context/FiltersContext";
import { useDashboardData } from "./services/useDashboardData";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DataUnavailable, LoadingSkeleton } from "./components/UI";
import { type PageName } from "./data";

const OverviewModule = lazy(() =>
  import("./components/OverviewModule").then((m) => ({ default: m.OverviewModule }))
);
const ModisModule = lazy(() =>
  import("./components/ModisModule").then((m) => ({ default: m.ModisModule }))
);
const ViirsModule = lazy(() =>
  import("./components/ViirsModule").then((m) => ({ default: m.ViirsModule }))
);
const HarmonisationModule = lazy(() =>
  import("./components/HarmonisationModule").then((m) => ({ default: m.HarmonisationModule }))
);
const WildfireMapModule = lazy(() =>
  import("./components/WildfireMapModule").then((m) => ({ default: m.WildfireMapModule }))
);
const AnalyticsModule = lazy(() =>
  import("./components/AnalyticsModule").then((m) => ({ default: m.AnalyticsModule }))
);

const navItems: { name: PageName; label: string; icon: any; badge?: string }[] = [
  { name: "Overview", label: "Overview", icon: Orbit },
  { name: "MODIS", label: "1. MODIS", icon: Flame, badge: "1 km" },
  { name: "VIIRS", label: "2. VIIRS", icon: Activity, badge: "375 m" },
  { name: "Harmonisation", label: "3. Harmonisation", icon: Sparkles, badge: "Statistical" },
  { name: "Wildfire Map", label: "4. Wildfire Map", icon: Globe2, badge: "0.25°" },
  { name: "Analytics", label: "5. Analytics", icon: BarChart3, badge: "Benchmark" },
];

function Topbar({
  page,
  openSidebar,
  isStatic,
}: {
  page: PageName;
  openSidebar: () => void;
  isStatic: boolean;
}) {
  const {
    filters,
    setRegion,
    setSatellite,
    setDateRange,
    setConfidence,
    resetFilters,
    confidenceNote,
  } = useFilters();

  const isHarmonisationPage = page === "Harmonisation";
  const isAnalyticsPage = page === "Analytics";

  return (
    <header className="topbar">
      <div className="topbar-title">
        <button className="mobile-menu" onClick={openSidebar}>
          <Menu size={19} />
        </button>
        <div>
          <span>NASA Space Apps · FireTrace Dashboard</span>
          <strong>{page}</strong>
        </div>
      </div>
      <div className="top-controls">
        <label title="Study Region Selection">
          <Globe2 size={14} className="text-[#36c9f4]" />
          <select
            value={filters.region}
            onChange={(e) => setRegion(e.target.value as any)}
          >
            {REGION_OPTIONS.map((r) => (
              <option key={r.value} value={r.value} disabled={r.disabled}>
                {r.label}
              </option>
            ))}
          </select>
          <ChevronsUpDown size={12} />
        </label>

        <label
          title={
            isHarmonisationPage
              ? "Harmonisation model is calibrated across combined sensors (filter disabled)"
              : isAnalyticsPage
              ? "Analytics benchmarks evaluate MODIS and VIIRS simultaneously (filter disabled)"
              : "Satellite Sensor Platform"
          }
          className={isHarmonisationPage || isAnalyticsPage ? "opacity-50 cursor-not-allowed" : ""}
        >
          <Orbit size={14} className="text-[#ff7547]" />
          <select
            value={filters.satellite}
            onChange={(e) => setSatellite(e.target.value as any)}
            disabled={isHarmonisationPage || isAnalyticsPage}
          >
            {SATELLITE_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <ChevronsUpDown size={12} />
        </label>

        <label title="Observation Date Range">
          <CalendarDays size={14} className="text-[#61d9fa]" />
          <select
            value={filters.dateRange}
            onChange={(e) => setDateRange(e.target.value as any)}
          >
            {DATE_RANGE_OPTIONS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          <ChevronsUpDown size={12} />
        </label>

        <label
          title={
            isHarmonisationPage
              ? "Harmonisation model uses full cleaned dataset (filter disabled)"
              : `Detection Confidence Threshold: ${confidenceNote}`
          }
          className={isHarmonisationPage ? "opacity-50 cursor-not-allowed" : ""}
        >
          <ShieldCheck size={14} className="text-[#ffb84d]" />
          <select
            value={filters.confidence}
            onChange={(e) => setConfidence(e.target.value as any)}
            disabled={isHarmonisationPage}
          >
            {CONFIDENCE_OPTIONS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <ChevronsUpDown size={12} />
        </label>

        <button
          className="button secondary text-xs py-1.5 px-2.5 inline-flex items-center gap-1.5"
          onClick={resetFilters}
          title="Reset all filters to defaults (Western Ghats, All sensors, All dates, Nominal+High)"
        >
          <RefreshCw size={12} /> Reset
        </button>

        {isStatic ? (
          <span className="data-online" title="Reading validated pre-computed static JSON/CSV datasets">
            <Database size={11} className="text-[#61d9fa]" /> Static Data
          </span>
        ) : (
          <span className="data-online" title="Connected to dynamic backend API service">
            <i /> API Online
          </span>
        )}
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
            <span>NASA Space Apps</span>
          </div>
        )}
        <button className="mobile-sidebar-x" onClick={closeMobile}>
          <X size={18} />
        </button>
      </div>
      <nav>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            page === item.name ||
            (item.name === "Harmonisation" && page === "Harmonized Activity") ||
            (item.name === "Wildfire Map" && page === "Fire Explorer") ||
            (item.name === "Analytics" && (page === "Sensor Comparison" || page === "Regional Comparison"));

          return (
            <button
              key={item.name}
              className={isActive ? "active" : ""}
              onClick={() => {
                setPage(item.name);
                closeMobile();
                window.scrollTo(0, 0);
              }}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={18} />
              {!collapsed && (
                <div className="flex-1 flex items-center justify-between text-left">
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="text-[10px] font-mono text-[#8e9eb3] bg-[#141d28] px-1.5 py-0.5 rounded ml-2">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
              {isActive && <i />}
            </button>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        <button className="collapse-button" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          {!collapsed && <span>Collapse sidebar</span>}
        </button>
        <div className="mission-status">
          <i />
          {!collapsed && (
            <span>
              <strong>NASA SPACE APPS</strong>All systems nominal
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}

function NotFoundPage({ setPage }: { setPage: (p: PageName) => void }) {
  return (
    <div className="p-16 text-center bg-[#141d28] border border-[#233142] rounded-lg my-6 space-y-4">
      <AlertTriangle className="mx-auto text-[#ffb84d]" size={48} />
      <h2 className="text-xl font-bold text-white">404 — Page Not Found</h2>
      <p className="text-sm text-[#8e9eb3] max-w-md mx-auto">
        The requested dashboard route does not exist. Choose one of the five core modules from the sidebar navigation.
      </p>
      <div className="pt-2">
        <button
          className="button primary inline-flex items-center gap-2 text-xs py-2 px-4"
          onClick={() => setPage("Overview")}
        >
          <Home size={14} /> Return to Overview
        </button>
      </div>
    </div>
  );
}

function DashboardApp() {
  const [page, setPage] = useState<PageName>("Overview");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const {
    dashboard,
    map,
    harmonizedSummary,
    yearlyTrends,
    regionComparison,
    loading,
    error,
    isStatic,
    reload,
  } = useDashboardData();

  // Listen to browser URL hash for direct links and browser back/forward buttons
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.replace("#", "").trim();
      if (!hash) {
        setPage("Overview");
        return;
      }
      const matched = navItems.find(
        (n) => n.name.toLowerCase().replace(/\s+/g, "-") === hash.toLowerCase()
      );
      if (matched) {
        setPage(matched.name);
      } else {
        setPage("404" as any);
      }
    };
    handleHash();
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  const handlePageChange = (newPage: PageName) => {
    setPage(newPage);
    window.location.hash = newPage.toLowerCase().replace(/\s+/g, "-");
  };

  let content;
  if (error) {
    content = <DataUnavailable message={error} onRetry={reload} />;
  } else if (page === "Overview") {
    content = (
      <ErrorBoundary fallbackTitle="Overview Module Error" onReset={reload}>
        <OverviewModule
          dashboard={dashboard}
          mapData={map}
          harmonizedSummary={harmonizedSummary}
          setPage={handlePageChange}
          loading={loading}
          isStatic={isStatic}
        />
      </ErrorBoundary>
    );
  } else if (page === "MODIS") {
    content = (
      <ErrorBoundary fallbackTitle="MODIS Module Error" onReset={reload}>
        <ModisModule
          dashboard={dashboard}
          yearlyTrends={yearlyTrends}
          regionComparison={regionComparison}
          loading={loading}
          onReload={reload}
        />
      </ErrorBoundary>
    );
  } else if (page === "VIIRS") {
    content = (
      <ErrorBoundary fallbackTitle="VIIRS Module Error" onReset={reload}>
        <ViirsModule
          dashboard={dashboard}
          yearlyTrends={yearlyTrends}
          regionComparison={regionComparison}
          loading={loading}
          onReload={reload}
        />
      </ErrorBoundary>
    );
  } else if (page === "Harmonisation" || page === "Harmonized Activity") {
    content = (
      <ErrorBoundary fallbackTitle="Harmonisation Module Error" onReset={reload}>
        <HarmonisationModule
          harmonizedSummary={harmonizedSummary}
          loading={loading}
          onReload={reload}
        />
      </ErrorBoundary>
    );
  } else if (page === "Wildfire Map" || page === "Fire Explorer") {
    content = (
      <ErrorBoundary fallbackTitle="Wildfire Map Module Error" onReset={reload}>
        <WildfireMapModule
          mapData={map}
          loading={loading}
          onReload={reload}
        />
      </ErrorBoundary>
    );
  } else if (
    page === "Analytics" ||
    page === "Sensor Comparison" ||
    (page as string) === "Regional Comparison"
  ) {
    content = (
      <ErrorBoundary fallbackTitle="Analytics Module Error" onReset={reload}>
        <AnalyticsModule />
      </ErrorBoundary>
    );
  } else {
    content = <NotFoundPage setPage={handlePageChange} />;
  }

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar
        page={page}
        setPage={handlePageChange}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        closeMobile={() => setMobileOpen(false)}
      />
      <div className="app-main">
        <Topbar
          page={page}
          openSidebar={() => setMobileOpen(true)}
          isStatic={isStatic}
        />
        <main className={page === "Wildfire Map" || page === "Fire Explorer" ? "explorer-main" : ""}>
          <Suspense fallback={<div className="p-6"><LoadingSkeleton lines={6} /></div>}>
            {content}
          </Suspense>
          <footer>
            <span>FireTrace · MODIS & VIIRS Wildfire Harmonisation</span>
            <span>NASA Space Apps Challenge · Verified FIRMS Data & Statistical Calibration</span>
          </footer>
        </main>
      </div>
      {mobileOpen && <button className="mobile-overlay" onClick={() => setMobileOpen(false)} />}
    </div>
  );
}

export default function App() {
  return (
    <FiltersProvider>
      <DashboardApp />
    </FiltersProvider>
  );
}
