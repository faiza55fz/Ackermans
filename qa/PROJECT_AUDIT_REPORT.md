# FireTrace NASA Space Apps Dashboard – Comprehensive Project Audit Report

**Overall Verdict: PARTIALLY INTEGRATED — CORE METHODOLOGY & REGIONAL DATA FUNCTIONAL, BUT CRITICAL NAVIGATION COLLISIONS, TYPE ERRORS, AND HARDCODED DEMO METRICS REQUIRE RESOLUTION PRIOR TO DEMO**

---

## A. Issues Encountered Previously

1. **Merge Conflict in `src/App.tsx`:** Simultaneous modifications to module imports and routing between `firetrace-pipeline-integration`, `regional-analytics`, and `feature/harmonization-engine` produced an import conflict in `src/App.tsx`.
2. **Page-Name & Route Identifier Collision:** Both `feature/harmonization-engine` and `regional-analytics` used the identical identifier `"Regional Comparison"`, causing the router to shadow the multi-region analytics component and render it unreachable.
3. **Failed Branch Name Lookup:** Initial project notes listed `"firetrace-pipine-integration"` with a typographical spelling error for `"firetrace-pipeline-integration"`, necessitating remote branch discovery via `git ls-remote`.
4. **`DATA/` vs `data/` Case-Insensitivity Clash on Windows NTFS:** Simultaneous tracking of uppercase `DATA/` on `regions-wg-punjab` and lowercase `data/` on `firetrace-pipeline-integration` caused Git checkout and merge aborts on case-insensitive Windows filesystems.
5. **Initial Invalid Duplicate Screenshots:** The original automated screenshot script used a generic `document.querySelector('select')` on the Regional Comparison page, inadvertently targeting the global topbar filter instead of Chart C and capturing identical above-the-fold views.
6. **Top-Bar Global Filter Scope Inconsistency:** The global top-bar dropdown listed generic US regions ("Western United States", "California", "Pacific Northwest", "Global") that did not match the project's actual target study regions, conflicting visually with multi-region pages.
7. **`git-lfs` Filter Process Missing on Windows Host:** Absence of the `git-lfs` executable on the host machine caused noisy smudge filter warnings during branch checkout and merge operations.
8. **TypeScript Deprecation Config Failure:** The setting `"ignoreDeprecations": "6.0"` in `tsconfig.json` halted CLI typechecking under TypeScript 5.9 with error `TS5103`.
9. **Sidebar Label Duplication & Lost "Sensor Comparison":** Renaming the 4th navigation button in `src/data.ts` to `"Regional Comparison"` while adding an 8th button with the same name created two identical sidebar labels and eliminated `"Sensor Comparison"`.

---

## B. Issues Successfully Resolved

1. **Import Conflict in `src/App.tsx`:** Successfully resolved by combining all required imports (`loadDashboardData`, `HarmonizedMetricSeries`, `HarmonizedSummary`, and `RegionalComparison`) into a single non-conflicting import block. *(Fixed locally only on `qa/test-merge`, not on any team branch)*. Evidence: `../qa-test-merge-view/src/App.tsx:38-44`.
2. **Regional Comparison Component Reachability:** Resolved the routing collision by renaming the regional comparison route key to `comparison_regions` in `src/App.tsx`, enabling the 8th sidebar button to mount `<RegionalComparison />`. *(Fixed locally only on `qa/test-merge`, not on any team branch)*. Evidence: `http://localhost:8450/` loads Raksha's component cleanly on button 8.
3. **Windows NTFS `DATA/` Collision Workaround:** Successfully isolated untracked local data files into `_LOCAL_DATA_BACKUP/`, eliminating directory case conflicts and allowing Git merges to proceed cleanly without data loss. Evidence: `git status` shows clean working trees across all test worktrees.
4. **Screenshot Evidence Invalidation & Regeneration:** Completely replaced all invalid duplicate captures with 12 verified unique screenshots featuring distinct visual views and audited SHA-256 hashes. Evidence: `qa/screenshots/` catalog with 100% unique hash validation.
5. **Standalone Regional Analytics Verification:** Successfully isolated and verified `origin/regional-analytics` on a dedicated port (`http://localhost:8451/`), confirming that all regional charts and tables operate flawlessly. Evidence: Automated browser suite passes test cases RC-01 through RC-05.
6. **Git-LFS Smudge Filter Warning Suppression:** Bypassed local Git-LFS smudge requirements via local repository configuration (`filter.lfs.required = false`), preventing pipeline checkout blocks. Evidence: Git worktree operations proceed without halting.

---

## C. Issues Still Remaining

### Issue C.1: Routing Collision & Shadowed Component on Team Branches
- **File / Component:** `src/App.tsx` (lines 1720–1728)
- **Why It Happens:** `feature/harmonization-engine` and `regional-analytics` both define routes for `"Regional Comparison"`. In the ternary router in `App.tsx`, the `feature/harmonization-engine` condition appears earlier. Clicking either button sets `page = "Regional Comparison"`, which routes exclusively to `<SensorComparison />`, leaving `<RegionalComparison />` as unreachable dead code.
- **Recommended Solution:** Rename Raksha's route key to `comparison_regions` in `src/App.tsx` and restore Yashaswi's route key to `"Sensor Comparison"`.
- **Change Category:** Frontend change
- **Origin Branch:** `feature/harmonization-engine` and `regional-analytics`

### Issue C.2: Duplicate Sidebar Labels ("Regional Comparison" at Slot 4 & Slot 8)
- **File / Component:** `src/data.ts` (line 252) and `src/App.tsx` (lines 220–230)
- **Why It Happens:** `feature/harmonization-engine` renamed slot 4 in `pages` array from `"Sensor Comparison"` to `"Regional Comparison"`. `regional-analytics` added an 8th button hardcoded in `src/App.tsx` also titled `"Regional Comparison"`. Consequently, two buttons display `"Regional Comparison"` in the UI, and `"Sensor Comparison"` is completely absent.
- **Recommended Solution:** In `src/data.ts`, restore `pages[3]` back to `"Sensor Comparison"`. In `src/App.tsx`, ensure slot 4 displays "Sensor Comparison" and slot 8 displays "Regional Comparison".
- **Change Category:** Frontend change
- **Origin Branch:** `feature/harmonization-engine` and `regional-analytics`

### Issue C.3: Leaked Snake_Case Route Key in Top-Bar Title & Breadcrumb
- **File / Component:** `src/App.tsx` (lines 25–27, `Topbar` component)
- **Why It Happens:** `Topbar` directly renders `FireTrace / {page}` and `<strong>{page}</strong>`. When navigating to the renamed regional route `comparison_regions`, the UI literally displays `"FireTrace / comparison_regions"` in the breadcrumb and `"comparison_regions"` as the page heading.
- **Recommended Solution:** Add a title display map in `Topbar`: `const pageTitle = page === "comparison_regions" ? "Regional Comparison" : page;`.
- **Change Category:** Frontend change
- **Origin Branch:** Local test merge `qa/test-merge`

### Issue C.4: Top-Bar Global Region Filter Mismatch & Broken California Condition
- **File / Component:** `src/App.tsx` (lines 29–35, lines 450–453)
- **Why It Happens:** Topbar dropdown hardcodes `"Western United States"`, `"California"`, `"Pacific Northwest"`, `"Global"`, omitting the project's actual study regions (`western_ghats_karnataka`, `palisades_la`, `punjab_haryana`). On `Overview`, code checks `filters.region === "Palisades, California"`. Because the dropdown only contains `"California"`, the condition never matches, causing Overview to unconditionally fall back to Western Ghats data.
- **Recommended Solution:** Update dropdown options to list actual study regions, change Overview condition to `.toLowerCase().includes("california")`, and contextualize filter display on multi-region pages.
- **Change Category:** Frontend change
- **Origin Branch:** `main`

### Issue C.5: TypeScript Compilation Errors on `<ChartTooltip>`
- **File / Component:** `src/App.tsx` (lines 361, 404) and `src/components/UI.tsx` (line 71)
- **Why It Happens:** `HarmonizedMetricCharts` passes `modelOutputDisclaimer` to `<ChartTooltip>`, but the component's TypeScript interface in `src/components/UI.tsx` does not declare this prop (`error TS2322`).
- **Recommended Solution:** Add `modelOutputDisclaimer?: boolean;` to `ChartTooltip` props in `src/components/UI.tsx`.
- **Change Category:** Frontend change
- **Origin Branch:** `feature/harmonization-engine`

### Issue C.6: Invalid `ignoreDeprecations` Configuration in `tsconfig.json`
- **File / Component:** `tsconfig.json` (line 13)
- **Why It Happens:** Setting `"ignoreDeprecations": "6.0"` is rejected by TypeScript 5.9 compiler (`error TS5103: Invalid value for '--ignoreDeprecations'`), causing CLI `tsc --noEmit` to fail.
- **Recommended Solution:** Change line 13 to `"ignoreDeprecations": "5.0"` or remove the property.
- **Change Category:** Frontend build configuration change
- **Origin Branch:** `main`

### Issue C.7: Inactive Month Picker in Anomaly Detection
- **File / Component:** `src/App.tsx` (line 1249)
- **Why It Happens:** Native HTML `<input type="month" defaultValue="2024-08" />` lacks an `onChange` event listener, making user input completely inert.
- **Recommended Solution:** Bind state: `value={selectedMonth}` and `onChange={(e) => setSelectedMonth(e.target.value)}`.
- **Change Category:** Frontend change
- **Origin Branch:** `main`

### Issue C.8: Remaining Misleading Hardcoded Demo Metrics Across Multiple Pages
- **File / Component:** `src/data.ts` (lines 31–231) and `src/App.tsx` (lines 542, 886–896, 1270–1298, 1367–1385, 1432–1475)
- **Why It Happens:** Fire Explorer relies on 31 hardcoded California points; Historical Calendar calculates cell values via synthetic formula `Math.sin((year + index) * 1.7) * 116`; Anomaly Detection displays static "96th percentile" cards; Data Quality generates a fake 365-day missing data grid using modulo arithmetic (`index % 47 === 0`).
- **Recommended Solution:** Connect Fire Explorer to real FIRMS point data, replace the sine wave formula with aggregated monthly arrays, and derive Data Quality/Anomaly statistics from pipeline execution outputs.
- **Change Category:** Frontend change
- **Origin Branch:** `main` and `firetrace-pipeline-integration`

### Issue C.9: Windows NTFS Case Collision (`DATA/` vs `data/`)
- **File / Component:** Root directory paths `DATA/` vs `data/`
- **Why It Happens:** Branches `regions-wg-punjab` and `punjab-data-parts` track uppercase `DATA/`, while `firetrace-pipeline-integration`, `feature/harmonization-engine`, and `main` track lowercase `data/`. Windows NTFS is case-insensitive, causing Git checkout and merge aborts when untracked files exist.
- **Recommended Solution:** Standardize all repository branches on lowercase `data/` and rename directory in git with `git mv DATA data`.
- **Change Category:** Git / Repository structure change
- **Origin Branch:** `regions-wg-punjab` and `punjab-data-parts`

### Issue C.10: Committed Python Bytecode (`.pyc`) Files
- **File / Component:** 22 tracked files under `src/**/__pycache__/` and `tests/**/__pycache__/`
- **Why It Happens:** Python compilation artifacts were committed into source control without proper `.gitignore` patterns.
- **Recommended Solution:** Add `__pycache__/` and `*.pyc` to root `.gitignore` and untrack existing files with `git rm -r --cached "**/__pycache__"`.
- **Change Category:** Git repository hygiene change
- **Origin Branch:** `feature/harmonization-engine`

### Issue C.11: Tracked Processed Data Files & ZIP Archive in Source Control
- **File / Component:** `data/processed/*.json` (~13 MB) and `data/processed/palisades_winter_clean_csv.zip` (166.6 KB)
- **Why It Happens:** Generated pipeline output datasets were committed directly to Git rather than published as GitHub releases or Git LFS assets.
- **Recommended Solution:** Untrack generated JSONs and archives; maintain only runtime payload JSONs under `public/data/`.
- **Change Category:** Git / Pipeline storage change
- **Origin Branch:** `firetrace-pipeline-integration` and `feature/harmonization-engine`

### Issue C.12: Committed IDE-Specific Rule Configuration
- **File / Component:** `.cursor/rules/modis-viirs-harmonization.mdc`
- **Why It Happens:** Editor-specific configuration committed to the repository root.
- **Recommended Solution:** Add `.cursor/` to `.gitignore`.
- **Change Category:** Git configuration change
- **Origin Branch:** `feature/harmonization-engine`

### Issue C.13: Missing Upstream Publication of QA Reports Branch
- **File / Component:** Branch `qa/dashboard-reports` (commit `5ba1556`)
- **Why It Happens:** QA audit reports and test artifacts have been committed locally but not pushed to `origin`, preventing teammates from viewing audit results on GitHub.
- **Recommended Solution:** Push `qa/dashboard-reports` to remote origin upon approval (`git push -u origin qa/dashboard-reports`).
- **Change Category:** Git workflow change
- **Origin Branch:** Local `qa/dashboard-reports`

### Issue C.14: Production Bundle Size Exceeds 500 kB
- **File / Component:** `vite.config.ts` and `src/App.tsx`
- **Why It Happens:** Monolithic synchronous bundling produces an 855.40 kB JS client bundle without dynamic code-splitting.
- **Recommended Solution:** Implement dynamic `React.lazy()` imports for secondary modules (e.g. `RegionalComparison`).
- **Change Category:** Frontend build configuration change
- **Origin Branch:** `main`

### Issue C.15: Global Codebase Formatting Discrepancies
- **File / Component:** 53 tracked files across `src/`, `data/`, and root configs
- **Why It Happens:** Commits made with mixed whitespace and formatting standards without pre-commit formatting checks.
- **Recommended Solution:** Execute `pnpm run format` across the repository.
- **Change Category:** Frontend code style change
- **Origin Branch:** `main`, `feature/harmonization-engine`, and `regional-analytics`

---

## D. Frontend Integration Status

### D.1 Member 5 Responsibility Ratings

#### 1. Connect the different modules into the existing dashboard: **Partially completed**
- *Evidence:* In the unmerged team branches, Raksha's multi-region comparison page is shadowed and unreachable due to route collisions with Yashaswi's branch. On the local test merge (`qa/test-merge`), all 8 modules are connected and functional, but slot 4 is misleadingly labeled `"Regional Comparison"` while opening `SensorComparison`.

#### 2. Remove misleading demo metrics: **Not completed**
- *Evidence:* Significant mock data remains in the UI: 31 hardcoded California points drive Fire Explorer (src/data.ts:31); synthetic sine formula `Math.sin((year + index) * 1.7) * 116` generates Historical Calendar values (src/App.tsx:893); hardcoded 96th percentile cards drive Anomaly Detection; modulo loops generate 365 fake dots on Data Quality.

#### 3. Make filters, region selection and navigation consistent: **Partially completed**
- *Evidence:* Regional Comparison's internal controls (scale toggle, grid resolution, and Chart C region selector) operate smoothly. However, the top-bar global region filter omits the 3 project study regions, fails to match California in Overview, and Anomaly Detection's month picker has no `onChange` handler. Sidebar navigation duplicates the label `"Regional Comparison"`.

#### 4. Fix UI issues and loading states: **Partially completed**
- *Evidence:* Root app shell cleanly catches fetch errors; `RegionalComparison.tsx` provides loading spinners, error cards, and retry buttons; `FireExplorer` renders `<EmptyState />`. However, two TypeScript compilation errors exist in `src/App.tsx`, and the top-bar leaks the raw route string `comparison_regions`.

### D.2 Cross-Member Observations

- **Three Regions on Map:** Overview map displays Western Ghats aggregated cells (92 cells). Pacific Palisades data is present in `dashboard.json` but blocked from loading due to the topbar filter mismatch (`"California"` vs `"Palisades, California"`). Punjab & Haryana map cells: **NOT CHECKED** on main map.
- **Western Ghats Harmonized Data:** Verified functional. `HarmonizedActivity` renders real proportions (76.8% observed vs 23.2% estimated) and dual line series from `harmonized_summary.json`.
- **`region_comparison.csv` Charts:** Verified functional. Successfully powers Chart A (sensor separation) and Chart B (spatial overlap) on port 8451 and 8450.
- **Sensor Agreement CSVs:** Verified functional. Powers the 6-row ground truth comparison table across Palisades, Western Ghats, and Punjab & Haryana.
- **Palisades Suspicious Cell:** Verified functional. The footnote identifying the persistent heat emitter near `-118.72°` renders cleanly on the Palisades comparison view.
- **Other pipeline/model areas:** Raw FIRMS API download streaming, model training scripts, and spatial cross-validation routines: **NOT CHECKED** (outside read-only dashboard scope).

---

## E. GitHub and Branch Status

### E.1 Remote Tracking Ref Comparison
Direct inspection via `git ls-remote --heads origin` compared with local `git rev-parse origin/<branch>`:

| Branch Name | Remote Tip Hash (`git ls-remote`) | Local Tracking Ref (`git rev-parse`) | New Remote Commits? |
|:---|:---:|:---:|:---:|
| `refs/heads/feature/harmonization-engine` | `b7898e02632c6d7bae1d42c4c801a8343c173a08` | `b7898e02632c6d7bae1d42c4c801a8343c173a08` | **No** (Exact Match) |
| `refs/heads/firetrace-pipeline-integration` | `1931a20de96d8734dbaca9832ecf2b5e4a1ba3bd` | `1931a20de96d8734dbaca9832ecf2b5e4a1ba3bd` | **No** (Exact Match) |
| `refs/heads/main` | `b233aca583d8e764c21ce74b20dfc12fbe2e8022` | `b233aca583d8e764c21ce74b20dfc12fbe2e8022` | **No** (Exact Match) |
| `refs/heads/regional-analytics` | `e552493e33ca3570915ce0b8a834b178d43a235c` | `e552493e33ca3570915ce0b8a834b178d43a235c` | **No** (Exact Match) |
| `refs/heads/qa/dashboard-reports` | *(Not on remote)* | `5ba15562f42b11a587f5b4322aaf843a03822953` | **Not Pushed** |

### E.2 Branch Synchronization Findings
1. **Zero New Remote Commits:** All remote team branches match local tracking refs 100%. No teammate has pushed un-tested code.
2. **QA Reports Unpushed:** Local branch `qa/dashboard-reports` (commit `5ba1556`) and the newly created `qa/PROJECT_AUDIT_REPORT.md` have **not been pushed** to origin.
3. **Local Main Behind:** Local branch `main` (commit `6d299ec`) is **1 commit behind** `origin/main` (`b233aca`: *"made changes in the ui"*).

---

## F. Application Status

### F.1 Execution & Startup Status
- **Dev Server (Port 8450 - Merged Build):** Started with `pnpm run dev -- --port 8450` in `../qa-test-merge-view`. Started in 280ms, answering HTTP 200.
- **Dev Server (Port 8451 - Standalone Regional):** Started with `pnpm run dev -- --port 8451` in `../qa-regional-only`. Started in 260ms, answering HTTP 200.
- **Browser Functionality:** All 8 pages render without runtime exceptions. Recharts animations and Leaflet tiles load smoothly.
- **Console Errors & Warnings:** Fresh page loads across all 8 modules produced **0 console errors** and **0 console warnings** (clean logs showing only Vite connection messages).

### F.2 Real vs Mock Data Summary
- **Real Project Data Displayed (4 Pages):**
  - **Overview (Module 1):** Real Western Ghats KPIs (1,33,605 detections, 4,616 days, 92 cells, 7.26 MW FRP), 92 map circles, annual trend chart from `dashboard.json` and `map.json`.
  - **Sensor Comparison (Module 4):** Real in-sample calibration stats and monthly timeseries from `harmonized_summary.json`.
  - **Harmonized Activity (Module 5):** Real Western Ghats model export (76.8% observed vs 23.2% estimated) from `harmonized_summary.json`.
  - **Regional Comparison (Module 8):** Real multi-region analytics from `region_comparison.csv` and `yearly_trends.csv`.
- **Mock / Synthetic Data Displayed (4 Pages):**
  - **Fire Explorer (Module 2):** 31 hardcoded California points from `src/data.ts`.
  - **Historical Calendar (Module 3):** Synthetic sine formula values from `App.tsx:893`.
  - **Anomaly Detection (Module 6):** Hardcoded 96th percentile card from `App.tsx:1270`.
  - **Data Quality (Module 7):** Static 94.2% KPI and modulo-generated 365-day grid from `App.tsx:1436`.

---

## G. Priority-Based Action Plan

### Critical Priority (Blockers / Core Navigation Breakages)
1. **Issue G.1: Routing Collision & Shadowed Component on Team Branches**  
   *File:* `src/App.tsx` (lines 1720–1728)  
   *Why It Happens:* Both branches use route identifier `"Regional Comparison"`, shadowing Raksha's component.  
   *Solution:* Rename Raksha's route key to `comparison_regions` and restore Yashaswi's route key to `Sensor Comparison`.  
   *Change Type:* Frontend change  
   *Branch:* `feature/harmonization-engine` and `regional-analytics`
2. **Issue G.2: Duplicate Sidebar Labels ("Regional Comparison") & Lost "Sensor Comparison"**  
   *File:* `src/data.ts` (line 252) and `src/App.tsx` (lines 220–230)  
   *Why It Happens:* Item 4 in `pages` was renamed to `"Regional Comparison"` while button 8 was added with the same label.  
   *Solution:* Restore item 4 in `src/data.ts` to `"Sensor Comparison"`; verify button 8 renders as "Regional Comparison".  
   *Change Type:* Frontend change  
   *Branch:* `feature/harmonization-engine` and `regional-analytics`
3. **Issue G.3: Windows NTFS Case Collision (`DATA/` vs `data/`)**  
   *File:* Filesystem directory names `DATA/` vs `data/`  
   *Why It Happens:* Branches track uppercase `DATA/` vs lowercase `data/`, causing Git merge/checkout aborts on Windows.  
   *Solution:* Standardize all branches on lowercase `data/` and rename directory in git with `git mv DATA data`.  
   *Change Type:* Git / Repository structure change  
   *Branch:* `regions-wg-punjab` and `punjab-data-parts`

### High Priority (Type Errors, Misleading Data, Broken UI Handlers)
4. **Issue G.4: Leaked Snake_Case Route Key in Topbar Title & Breadcrumb**  
   *File:* `src/App.tsx` (lines 25–27, `Topbar` component)  
   *Why It Happens:* `Topbar` directly renders raw route string `comparison_regions`.  
   *Solution:* Map route keys to display titles in `Topbar`.  
   *Change Type:* Frontend change  
   *Branch:* Local test merge `qa/test-merge`
5. **Issue G.5: Top-Bar Global Region Filter Mismatch & Broken California Condition**  
   *File:* `src/App.tsx` (lines 29–35, lines 450–453)  
   *Why It Happens:* Dropdown lists generic US regions; condition `filters.region === "Palisades, California"` never matches `"California"`.  
   *Solution:* Update dropdown to list project study regions and use `.toLowerCase().includes("california")`.  
   *Change Type:* Frontend change  
   *Branch:* `main`
6. **Issue G.6: TypeScript Compilation Error in `<ChartTooltip>`**  
   *File:* `src/App.tsx` (lines 361, 404) and `src/components/UI.tsx` (line 71)  
   *Why It Happens:* Undeclared prop `modelOutputDisclaimer` passed to `ChartTooltip`.  
   *Solution:* Add `modelOutputDisclaimer?: boolean;` to `ChartTooltip` props in `src/components/UI.tsx`.  
   *Change Type:* Frontend change  
   *Branch:* `feature/harmonization-engine`
7. **Issue G.7: Invalid `ignoreDeprecations` Configuration in `tsconfig.json`**  
   *File:* `tsconfig.json` (line 13)  
   *Why It Happens:* Value `"6.0"` rejected by TypeScript 5.9 compiler.  
   *Solution:* Update to `"ignoreDeprecations": "5.0"` or remove line.  
   *Change Type:* Frontend build configuration change  
   *Branch:* `main`
8. **Issue G.8: Inactive Month Picker in Anomaly Detection**  
   *File:* `src/App.tsx` (line 1249)  
   *Why It Happens:* `<input type="month" />` has no `onChange` listener.  
   *Solution:* Attach state binding and `onChange` handler.  
   *Change Type:* Frontend change  
   *Branch:* `main`
9. **Issue G.9: Misleading Hardcoded Demo Metrics**  
   *File:* `src/data.ts` (lines 31–231) and `src/App.tsx` (lines 886–896, 1270–1298, 1432–1475)  
   *Why It Happens:* Mock California points, synthetic sine waves, and static percentiles remain in user-facing views.  
   *Solution:* Wire real FIRMS points and aggregated pipeline metrics to these views.  
   *Change Type:* Frontend change  
   *Branch:* `main` and `firetrace-pipeline-integration`

### Medium Priority (Repository Hygiene & Bloat)
10. **Issue G.10: Committed `.pyc` Bytecode Files in Repository History**  
    *File:* 22 files under `src/**/__pycache__/` and `tests/**/__pycache__/`  
    *Why It Happens:* Python compilation cache committed without `.gitignore` rule.  
    *Solution:* Add `__pycache__/` to `.gitignore` and untrack via `git rm -r --cached "**/__pycache__"`.  
    *Change Type:* Git repository hygiene change  
    *Branch:* `feature/harmonization-engine`
11. **Issue G.11: Tracked Processed Data Payloads and ZIP Archive**  
    *File:* `data/processed/*.json` (~13 MB) and `data/processed/palisades_winter_clean_csv.zip` (166.6 KB)  
    *Why It Happens:* Pipeline outputs committed directly to Git repository.  
    *Solution:* Untrack processed JSONs and archives; publish large datasets as GitHub release assets.  
    *Change Type:* Git / Pipeline storage change  
    *Branch:* `firetrace-pipeline-integration` and `feature/harmonization-engine`
12. **Issue G.12: Committed IDE-Specific Rule Configuration**  
    *File:* `.cursor/rules/modis-viirs-harmonization.mdc`  
    *Why It Happens:* Vendor-specific editor rule committed to root.  
    *Solution:* Add `.cursor/` to `.gitignore`.  
    *Change Type:* Git configuration change  
    *Branch:* `feature/harmonization-engine`
13. **Issue G.13: Missing Upstream Publication of QA Reports Branch**  
    *File:* Branch `qa/dashboard-reports` (commit `5ba1556`)  
    *Why It Happens:* Local QA reports have not yet been pushed to origin.  
    *Solution:* Push `qa/dashboard-reports` to remote origin upon approval.  
    *Change Type:* Git workflow change  
    *Branch:* Local `qa/dashboard-reports`

### Low Priority (Optimization & Styling)
14. **Issue G.14: Production Bundle Size Exceeds 500 kB**  
    *File:* `vite.config.ts` and `src/App.tsx`  
    *Why It Happens:* Monolithic bundling yields an 855.40 kB JS chunk.  
    *Solution:* Add dynamic `React.lazy()` imports for secondary modules.  
    *Change Type:* Frontend build configuration change  
    *Branch:* `main`
15. **Issue G.15: Global Codebase Formatting Discrepancies**  
    *File:* 53 tracked files across `src/`, `data/`, and configs  
    *Why It Happens:* Mixed whitespace standards across teammates.  
    *Solution:* Run `pnpm run format` across the codebase.  
    *Change Type:* Frontend code style change  
    *Branch:* `main`, `feature/harmonization-engine`, and `regional-analytics`

---

## H. Next Steps

A numbered, sequential plan of exactly what to fix next, in order, specifying the required discipline:

1. **Resolve Route Identifier Collision (Step 1):**  
   *Action:* In `src/App.tsx`, rename Raksha's route key and click handler to `comparison_regions` and restore Yashaswi's route key to `"Sensor Comparison"`.  
   *Role:* **Frontend**  
   *Origin Branch:* `feature/harmonization-engine` and `regional-analytics`
2. **Restore Sidebar Button Labels (Step 2):**  
   *Action:* In `src/data.ts`, restore `pages[3]` to `"Sensor Comparison"` so slot 4 is labeled "Sensor Comparison" and slot 8 is labeled "Regional Comparison".  
   *Role:* **Frontend**  
   *Origin Branch:* `feature/harmonization-engine` and `regional-analytics`
3. **Normalize Case Collision on Remote Branches (Step 3):**  
   *Action:* Rename `DATA/` to `data/` via `git mv DATA data` on `regions-wg-punjab` and `punjab-data-parts` to eliminate Windows checkout aborts.  
   *Role:* **Git**  
   *Origin Branch:* `regions-wg-punjab` and `punjab-data-parts`
4. **Fix TypeScript Prop Definition in `UI.tsx` (Step 4):**  
   *Action:* Add `modelOutputDisclaimer?: boolean;` to `ChartTooltip` in `src/components/UI.tsx` to clear `TS2322` errors.  
   *Role:* **Frontend**  
   *Origin Branch:* `feature/harmonization-engine`
5. **Fix `tsconfig.json` Deprecation Flag (Step 5):**  
   *Action:* Change line 13 in `tsconfig.json` from `"ignoreDeprecations": "6.0"` to `"ignoreDeprecations": "5.0"`.  
   *Role:* **Frontend**  
   *Origin Branch:* `main`
6. **Map `comparison_regions` to Human-Readable Title in `Topbar` (Step 6):**  
   *Action:* In `src/App.tsx`, add a title mapper so `comparison_regions` renders as `"Regional Comparison"` in topbar title and breadcrumb.  
   *Role:* **Frontend**  
   *Origin Branch:* Local test merge `qa/test-merge`
7. **Fix Top-Bar Global Filter Options & Overview Condition (Step 7):**  
   *Action:* Update top-bar dropdown options to list actual study regions, and update Overview condition in `src/App.tsx` to `.toLowerCase().includes("california")`.  
   *Role:* **Frontend**  
   *Origin Branch:* `main`
8. **Attach `onChange` Handler to Month Picker (Step 8):**  
   *Action:* In `src/App.tsx:1249`, wire state binding and `onChange` handler to `<input type="month" />`.  
   *Role:* **Frontend**  
   *Origin Branch:* `main`
9. **Purge `.pyc` Cache Files & Update `.gitignore` (Step 9):**  
   *Action:* Add `__pycache__/` and `*.pyc` to root `.gitignore` and untrack cached files with `git rm -r --cached "**/__pycache__"`.  
   *Role:* **Git**  
   *Origin Branch:* `feature/harmonization-engine`
10. **Untrack Heavy Processed Payloads & ZIP Archive (Step 10):**  
    *Action:* Remove `data/processed/*.json` and ZIP archives from Git tracking; retain only static runtime payloads under `public/data/`.  
    *Role:* **Backend / Git**  
    *Origin Branch:* `firetrace-pipeline-integration` and `feature/harmonization-engine`
11. **Untrack Cursor IDE Rule File (Step 11):**  
    *Action:* Add `.cursor/` to `.gitignore` and untrack `.cursor/rules/modis-viirs-harmonization.mdc`.  
    *Role:* **Git**  
    *Origin Branch:* `feature/harmonization-engine`
12. **Connect Real Detections to Fire Explorer (Step 12):**  
    *Action:* Replace 31 mock California points in `src/data.ts` with real FIRMS detections from processed Parquet/JSON.  
    *Role:* **Frontend / Backend**  
    *Origin Branch:* `main` and `firetrace-pipeline-integration`
13. **Replace Synthetic Calendar Formula with Aggregated Observations (Step 13):**  
    *Action:* In `src/App.tsx:893`, replace the `Math.sin()` formula with real monthly detection totals.  
    *Role:* **Frontend / Backend**  
    *Origin Branch:* `main` and `firetrace-pipeline-integration`
14. **Format Repository with `oxfmt` (Step 14):**  
    *Action:* Run `pnpm run format` across all 53 files to establish consistent code styling.  
    *Role:* **Frontend**  
    *Origin Branch:* `main`, `feature/harmonization-engine`, and `regional-analytics`
15. **Publish QA Audit Reports to Remote (Step 15):**  
    *Action:* Run `git push -u origin qa/dashboard-reports` to publish all QA audit reports and test matrices for team review.  
    *Role:* **Git**  
    *Origin Branch:* Local `qa/dashboard-reports`
