# QA Test Environment & Run Metadata

**Project:** NASA Space Apps Challenge – Harmonizing MODIS and VIIRS Fire Hotspots into a Burning Activity Calendar  
**Repository:** `https://github.com/faiza55fz/Ackermans`  
**Execution Date:** 2026-11-15  
**QA Lead / Owner:** Antigravity QA Engineering  

---

## 1. Git & Branch Lineage Metadata

| Ref / Branch | Commit Hash | Author | Description / Role |
|---|---|---|---|
| `origin/main` | `b233aca583d8e764c21ce74b20dfc12fbe2e8022` | faiza55fz | Base dashboard branch (React 19 + Vite 8 + Leaflet UI) |
| `origin/firetrace-pipeline-integration` | `1931a20de96d8734dbaca9832ecf2b5e4a1ba3bd` | faiza55fz, Fathima khan | Real regional fire data ingestion, JSON exports (`dashboard.json`, `map.json`), KPI cards & grid circles |
| `origin/regional-analytics` | `e552493e33ca3570915ce0b8a834b178d43a235c` | Raksha K R | Multi-region comparison analytics page (`RegionalComparison.tsx`), runtime CSV loaders (`region_comparison.csv`, `yearly_trends.csv`) |
| `origin/feature/harmonization-engine` | `b7898e02632c6d7bae1d42c4c801a8343c173a08` | yashaswiyashaswi | Western Ghats harmonization model integration, `harmonized_summary.json`, `HarmonizedMetricCharts`, model evaluation metrics |
| `qa/test-merge` *(Local Only)* | `b8f99c0` | QA Integration Merge | Non-destructive local merge of all 3 feature branches in specified order: `firetrace-pipeline-integration` → `regional-analytics` → `feature/harmonization-engine` |
| `qa-regional-only` *(Worktree)* | `e552493e33ca3570915ce0b8a834b178d43a235c` | Raksha K R | Standalone read-only checkout of Raksha's branch used for isolated UI verification |

---

## 2. Runtime & Toolchain Environment

| Component | Version / Specification | Details / Notes |
|---|---|---|
| **Operating System** | Windows 11 (x86_64) | PowerShell 5.1 / UTF-8 |
| **Node.js** | `v24.14.0` | Node runtime environment |
| **Package Manager** | `pnpm v12.3.4` | Dependency resolution via content-addressable virtual store |
| **Bundler / Dev Server** | `Vite v8.0.5` | ES module hot reload and local preview server |
| **Frontend Framework** | `React 19.2.4` / `ReactDOM 19.2.4` | Modern React runtime |
| **Styling Engine** | `Tailwind CSS v4.2.2` | Configured with `@tailwindcss/vite` |
| **Mapping Engine** | `Leaflet 1.9.4` / `react-leaflet 5.0.0` | Interactive tile & geospatial circle layer rendering |
| **Charting Engine** | `Recharts 3.10.1` | Responsive SVG/HTML composed chart visualization |
| **Icons** | `Lucide React 1.72.0` | Modern SVG system icon suite |

---

## 3. Server Instances & Network Ports

| Service Instance | Local URL | Working Copy Directory | Purpose / Test Scope |
|---|---|---|---|
| **Merged Dashboard** | `http://localhost:8450/` (previously `8443`) | `../qa-test-merge-view` (on `qa/test-merge`) | Testing full cross-teammate integration, routing collision, module functionality |
| **Standalone Regional View** | `http://localhost:8451/` (previously `8444`) | `../qa-regional-only` (on detached `origin/regional-analytics`) | Verifying Raksha's Regional Comparison page in isolation across Palisades, Western Ghats, and Punjab & Haryana |

---

## 4. Verification Protocol & Quality Gates
- **Zero code modification on business logic:** Application and calculation code remain 100% read-only.
- **Strict Git boundary:** `qa/test-merge` is isolated locally and never pushed to remote.
- **Dual-server evaluation:** Used to isolate routing collisions from component-level defects.
