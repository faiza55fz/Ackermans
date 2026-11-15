# FireTrace Dashboard QA Bug Report

**Test Run:** NASA Space Apps Hackathon Integration Testing  
**Date:** 2026-11-15  
**Merged Target Branch:** `qa/test-merge` (derived from `origin/main` + `origin/firetrace-pipeline-integration` + `origin/regional-analytics` + `origin/feature/harmonization-engine`)  
**Standalone Branch:** `origin/regional-analytics` (tested in `../qa-regional-only`)  

---

## Executive Bug Summary

| Bug ID | Severity | Category | Component / File | Title / Summary | Status |
|---|---|---|---|---|---|
| **BUG-001** | **Major** | Routing / Navigation | `src/App.tsx`, `src/data.ts` | Routing collision & sidebar label duplication: "Regional Comparison" appears twice in sidebar; intercepts Raksha's component; "Sensor Comparison" label lost | **OPEN / UNRESOLVED on Team Branches** (Proposed fix verified locally only) |
| **BUG-002** | **Minor** | UI / Global Filter | `src/App.tsx` (Header Filter), Modules 1–8 | Top-bar global region filter lists only 4 US/global options, omitting the 3 project study regions; inconsistent behavior across pages | Confirmed in UI & Code Audit |
| **BUG-003** | **Minor** | Repo Hygiene | `src/`, `tests/` | 22 compiled Python cache files (`.pyc`) committed into git repository | Confirmed in Git Tree |
| **BUG-004** | **Minor** | Repo Hygiene | `data/processed/`, `data/data/clean/` | Large generated data outputs (~14.5 MB) and ZIP archive committed into git repository | Confirmed in Git Tree |
| **BUG-005** | **Minor** | Repo Hygiene | `.cursor/rules/` | IDE-specific editor rule file committed to root directory | Confirmed in Git Tree |
| **BUG-006** | **Trivial** | Chart Visualization | `src/components/RegionalComparison.tsx` | Logarithmic scale on Chart A produces visual gaps for zero-detection years | Handled via UI Note |
| **BUG-007** | **Minor** | Cross-Platform / Git | Root directory `DATA/` vs `data/` | Windows NTFS case-insensitivity collision between branches tracking `DATA/` vs `data/` | Confirmed during Git Merge |

---

## Detailed Bug Reports

### BUG-001 [Major]: Routing Collision & Sidebar Label Duplication in Merged Code

- **Severity:** Major (Breaks expected navigation flow and completely blocks access to Raksha's Regional Comparison page in merged build; duplicates sidebar button labels)
- **Affected Files:**
  - `src/App.tsx` (lines 1717–1728, sidebar navigation buttons lines 212–230)
  - `src/data.ts` (line defining `pages` array, position 4)
- **Branch Authors Involved:**
  - **Yashaswi** (`origin/feature/harmonization-engine`, commit `b7898e0`)
  - **Raksha K R** (`origin/regional-analytics`, commit `e552493`)

#### Description
In `src/App.tsx` and `src/data.ts`, two conflicting changes occurred regarding the page identifier `"Regional Comparison"`:
1. **Yashaswi's change:** Refactored `SensorComparison` to consume harmonization summary data, but renamed its page router condition from `page === "Sensor Comparison"` to `page === "Regional Comparison"`:
   ```tsx
   ) : page === "Regional Comparison" ? (
     <SensorComparison summary={projectData!.harmonizedSummary} />
   ) : page === "Harmonized Activity" ? (
   ```
   Crucially, Yashaswi also renamed the 4th item in the `pages` array in `src/data.ts` from `"Sensor Comparison"` to `"Regional Comparison"`.
2. **Raksha's change:** Added a brand new `<RegionalComparison />` component and added a route at the bottom of the ternary chain:
   ```tsx
   ) : (page as string) === "Regional Comparison" ? (
     <RegionalComparison />
   ) : (
     <DataQuality filters={filters} />
   );
   ```
   Raksha also appended a dedicated button labeled `"Regional Comparison"` at the bottom of the sidebar.

#### Observed Behavior in Merged UI (Before Proposed Rename)
1. **Sidebar Button Labels in Order:**
   1. `Overview`
   2. `Fire Explorer`
   3. `Historical Calendar`
   4. `Regional Comparison` *(Slot 4, rendered from `pages[3]` in `src/data.ts`)*
   5. `Harmonized Activity`
   6. `Anomaly Detection`
   7. `Data Quality`
   8. `Regional Comparison` *(Slot 8, rendered from Raksha's button in `src/App.tsx`)*
2. **Duplication & Missing Label:**
   - The label `"Regional Comparison"` appears **TWICE** in the sidebar (slot 4 and slot 8).
   - The label `"Sensor Comparison"` appears **ZERO times** (completely lost).
3. **Shadowed Component:**
   Clicking *either* `"Regional Comparison"` button sets `page = "Regional Comparison"`. In the ternary router in `src/App.tsx`, Yashaswi's condition is evaluated first, so the application renders Yashaswi's `<SensorComparison />` ("Cross-sensor analysis · Observed and estimated detections / FRP").
4. Raksha's `<RegionalComparison />` component is **never mounted** and is unreachable dead code in the merged build.

#### Observed Behavior After the Proposed Rename (`comparison_regions`)
When testing the proposed route rename (`page = "comparison_regions"`) for Raksha's component:
1. **Routing Works:** Clicking button 8 successfully opens Raksha's multi-region analytics.
2. **Sidebar Labels STILL Duplicated:** The sidebar navigation still displays two buttons labeled `"Regional Comparison"`:
   - Position 4 is labeled `"Regional Comparison"` (rendered from `pages[3]` in `src/data.ts`).
   - Position 8 is labeled `"Regional Comparison"` (rendered from `<span>Regional Comparison</span>` in `src/App.tsx`).
3. **Correction to Previous Assumption:** Sensor Comparison does **NOT** stay on the 4th slot under its own name. When clicking the 4th button, Yashaswi's `<SensorComparison />` mounts, but the user sees a button labeled `"Regional Comparison"`. Having two identically labeled buttons that open completely different pages is confusing and misleading.

#### Evidence
- Screenshot: qa/screenshots/merged_regional_comparison_click.png shows Raksha's multi-region comparison table and charts mounting properly after routing to `comparison_regions`.
- Screenshot: qa/screenshots/04_sensor_comparison.png shows Yashaswi's `<SensorComparison />` opened by clicking the 4th sidebar button (which is labelled "Regional Comparison").

#### Proposed Fix & Ownership
- **Current Status:** **OPEN / UNRESOLVED on Team Branches.** Both remote branches (`origin/feature/harmonization-engine` and `origin/regional-analytics`) still contain this collision.
- **Fix Ownership:** Jointly owned by **Yashaswi** (`feature/harmonization-engine`) and **Raksha K R** (`regional-analytics`).
- **Complete Fix Requirements (Two Steps):**
  1. **Rename Raksha's route key to `comparison_regions`:**
     In `src/App.tsx`:
     ```tsx
     // Sidebar button (lines ~220-230):
     <button
       className={(page as string) === "comparison_regions" ? "active" : ""}
       onClick={() => {
         setPage("comparison_regions" as PageName);
         closeMobile();
         window.scrollTo(0, 0);
       }}
       title={collapsed ? "Regional Comparison" : undefined}
     >
       <BarChart3 size={18} />
       {!collapsed && <span>Regional Comparison</span>}
       {(page as string) === "comparison_regions" && <i />}
     </button>

     // Router ternary (line ~1725):
     ) : (page as string) === "comparison_regions" ? (
       <RegionalComparison />
     ) : (
     ```
  2. **Restore "Sensor Comparison" label and route for Slot 4:**
     In `src/data.ts`:
     Change `pages[3]` from `"Regional Comparison"` back to `"Sensor Comparison"`.
     In `src/App.tsx` (line ~1717):
     Change router condition back to `page === "Sensor Comparison"`.

> [!NOTE]
> The route rename was evaluated as a **proposed fix verified only on a local test branch (`qa/test-merge`)**. It demonstrated that renaming the route allows both pages to co-exist without collision. However, this fix has **NOT** been pushed or merged into any team remote branch, so upstream branches still contain the bug.

---

### BUG-002 [Minor]: Top-Bar Global Region Filter Mismatch & Cross-Page Audit

- **Severity:** Minor (UI / Filter inconsistency and geographical scope mismatch)
- **Affected File:** src/App.tsx (Header Filter `<select>` and state `filters.region`)
- **Associated Modules:** Modules 1 through 8
- **Introduced By:** Original dashboard shell / Raksha (`regional-analytics`)

#### Description
The top navigation bar of the application contains a global region dropdown. An inspection of `src/App.tsx` reveals that it offers only 4 hardcoded options:
1. `Western United States` (value: `"all"`)
2. `California` (value: `"ca"`)
3. `Pacific Northwest` (value: `"pnw"`)
4. `Global` (value: `"global"`)

**Critical Deficiency:** The dropdown does **NOT** list any of the project's actual target study regions:
- `Pacific Palisades, California` (`palisades_la`)
- `Western Ghats, Karnataka, India` (`western_ghats_karnataka`)
- `Punjab & Haryana, India` (`punjab_haryana`)

#### Comprehensive Page-by-Page Impact Audit:
1. **Module 1 (Overview - `Overview.tsx`):**
   - The component performs an ad-hoc mapping based on `filters.region`.
   - If `filters.region === "ca"`, it attempts to load `palisades_la`.
   - For all other options (`"all"`, `"pnw"`, `"global"`), it unconditionally falls back to loading `western_ghats_karnataka`. Selecting "Global" or "Pacific Northwest" still displays Western Ghats data.
2. **Module 2 (Fire Explorer - `FireExplorer.tsx`):**
   - Uses the filter to restrict hotspot bounding boxes to US coordinates. Non-US hotspots (Western Ghats, Punjab & Haryana) are excluded from the interactive map view.
3. **Module 3 (Historical Calendar - `HistoricalCalendar.tsx`):**
   - Displays calendar activity based on mock data; does not dynamically switch between the three target regions.
4. **Module 4 (Sensor Comparison - `SensorComparison.tsx`):**
   - Renders sensor agreement metrics for whichever dataset is currently loaded in memory; completely ignores the top-bar dropdown.
5. **Module 5 (Harmonized Activity - `HarmonizedActivity.tsx`):**
   - Directly renders the Western Ghats harmonization export (`harmonized_summary.json`); completely ignores the top-bar selection.
6. **Module 6 (Anomaly Detection - `AnomalyDetection.tsx`):**
   - Receives the `filters` prop for text display, but anomaly cards and threshold calculations operate on static mock profiles.
7. **Module 7 (Data Quality - `DataQuality.tsx`):**
   - Receives `filters` prop; sensor confidence breakdown remains static.
8. **Module 8 (Regional Comparison - `RegionalComparison.tsx`):**
   - **Completely ignores** the top-bar global filter.
   - `RegionalComparison.tsx` provides its own internal region selector inside Chart C (allowing selection of Pacific Palisades, Western Ghats Karnataka, and Punjab & Haryana).
   - Consequently, when viewing Regional Comparison, the top-bar badge remains stuck displaying `"Western United States"` and `"Jan 2000 — Aug 2024"`, which directly contradicts the multi-continental data displayed on the page.

#### Evidence
- Screenshot: qa/screenshots/regional_topbar_issue.png highlights the contradictory top-bar badge on the Regional Comparison page.

#### Recommended Fix
1. Update the top-bar dropdown options in `src/App.tsx` to list the actual project study regions:
   `Western Ghats (India)`, `Punjab & Haryana (India)`, and `Pacific Palisades (USA)`.
2. On `RegionalComparison`, hide the global filter badges or display a contextual badge: `"Multi-Region Benchmark · 2000–2026"`.

---

### BUG-003 [Minor]: Committed `.pyc` Bytecode Files in Repository

- **Severity:** Minor (Repository Hygiene)
- **Affected Directories:**
  - `src/__pycache__/`
  - `src/export/__pycache__/`
  - `src/grid/__pycache__/`
  - `src/models/__pycache__/`
  - `src/validate/__pycache__/`
  - `tests/__pycache__/`
- **Count:** 22 tracked compiled `.pyc` files (including Python 3.14 and multiple pytest versions `pytest-9.1.1.pyc`, `pytest-9.2.0.pyc`).
- **Introduced By:** Yashaswi (`origin/feature/harmonization-engine`)

#### Recommended Fix
Add `__pycache__/` and `*.pyc` to root `.gitignore` and untrack existing files with:
`git rm -r --cached "**/__pycache__"`

---

### BUG-004 [Minor]: Tracked Processed Data Files and ZIP Archive in Source Control

- **Severity:** Minor (Repository Hygiene & Bloat)
- **Affected Files:**
  - `data/processed/palisades_winter_clean_csv.zip` (166.6 KB)
  - `data/processed/palisades_la_combined_processed.json` (6.56 MB)
  - `data/processed/palisades_la_VIIRS_processed.json` (5.94 MB)
  - `data/processed/palisades_la_MODIS_processed.json` (610.8 KB)
  - `data/data/clean/palisades_la_*.parquet` (3 files, LFS pointers/data)
  - Total tracked data footprint: ~14.5 MB
- **Introduced By:** Faiza & Fatima (`firetrace-pipeline-integration`), Yashaswi (`feature/harmonization-engine`)

#### Note on 25 MB Limit
An audit via `git ls-tree -r -l HEAD` confirmed that **zero** files exceed the 25 MB threshold (the single largest tracked file is `palisades_la_combined_processed.json` at 6.56 MB). However, generated processed JSONs and ZIP archives should be published as release assets rather than tracked in Git history.

---

### BUG-005 [Minor]: IDE-Specific Editor Rules Committed to Root

- **Severity:** Minor (Repository Hygiene)
- **Affected File:** `.cursor/rules/modis-viirs-harmonization.mdc`
- **Introduced By:** Yashaswi (`origin/feature/harmonization-engine`)
- **Impact:** Vendor-specific IDE configuration should be placed in user-level configuration or added to `.gitignore`.

---

### BUG-006 [Trivial]: Logarithmic Scale Disconnect on Zero-Detection Years

- **Severity:** Trivial / Documented Limitation
- **Affected File:** src/components/RegionalComparison.tsx
- **Observation:** When toggling to Log10 Scale on Chart A (Unique Hotspot Cells by Sensor), years with zero detections cannot be mathematically plotted on a logarithmic axis ($\log_{10}(0)$ is undefined), appearing as visual breaks in the line series.
- **Mitigation:** Raksha already included an inline alert badge explaining: *"Years with 0 detections cannot be represented on a logarithmic scale and are shown as visual gaps in the line plot."*

---

### BUG-007 [Minor]: File System Case Collision (`DATA/` vs `data/`) on Windows NTFS

- **Severity:** Minor (Build & Merge Blocker on Windows host environments)
- **Affected Paths:** `DATA/` (uppercase) vs `data/` (lowercase)
- **Branches Tracking Uppercase `DATA/`:**
  - `origin/regions-wg-punjab`
  - `origin/punjab-data-parts`
- **Branches Tracking Lowercase `data/`:**
  - `origin/firetrace-pipeline-integration`
  - `origin/feature/harmonization-engine`
  - `origin/main`

#### Description & Root Cause
Windows file systems (NTFS and FAT32) are case-preserving but case-insensitive. When an untracked directory `DATA/data/clean/` exists locally on disk (generated during pipeline runs or checked out from an uppercase branch), and Git subsequently attempts to merge or check out a branch tracking lowercase `data/data/clean/` (such as `firetrace-pipeline-integration`), Git recognizes that both paths refer to the same physical directory on Windows.
Git detects that checking out files under `data/data/clean/...` would overwrite untracked files in `DATA/data/clean/...` and aborts the operation with:
```
error: The following untracked working tree files would be overwritten by merge:
    data/data/clean/palisades_la_MODIS_clean.parquet
    data/data/clean/palisades_la_VIIRS_clean.parquet
    data/data/clean/palisades_la_combined_clean.parquet
Please move or remove them before you merge.
Aborting
```

#### Workaround & Resolution
1. **QA Isolation Workaround:** Safely renamed the untracked directory to `_LOCAL_DATA_BACKUP/`. Because `_LOCAL_DATA_BACKUP/` does not share any name variation with `data/`, Git merged cleanly without any data loss.
2. **Upstream Recommendation:** All team branches must standardize on lowercase `data/`. The uppercase `DATA/` directory in `regions-wg-punjab` and `punjab-data-parts` must be migrated to lowercase `data/` to prevent checkout failures on Windows developer workstations.

---

## Test Evidence & Screenshot Verification Audit

### Selector Correction Note
During the initial automated test harness run, screenshots of the Regional Comparison page were captured using a generic `document.querySelector('select')`. In the DOM, this selected the header bar's global region dropdown (`filters.region`, containing "Western United States", "California", etc.) rather than the region selector inside Chart C in `RegionalComparison.tsx`, and the script did not scroll down to Chart C. As a consequence, changing the dropdown value did not trigger Chart C re-renders, and the captured screenshots showed identical above-the-fold views.

**Corrective Action Taken:**
1. Re-engineered the test harness script (`fix_standalone_screenshots.mjs`) to specifically select Chart C's `<select>` element (identified by `option[value="palisades"]`).
2. Script dispatches change events, verifies that the heading in the DOM updates to match the selected region, and scrolls Chart C and the data comparison table into full viewport view.
3. Captured Module 4 (`04_sensor_comparison.png`) by clicking the 4th sidebar button by position.
4. Audited all 12 screenshots with SHA-256 hashes to guarantee 100% uniqueness.

### Complete Screenshot Evidence Catalog

| # | Filename | Size (Bytes) | SHA-256 Hash | Target Module / Content Verified |
|---|---|---|---|---|
| 1 | `01_overview.png` | 269,233 | `8CEF76E67E5A64B1B0570E636A5972BD36A4A6A98802CE688578B4E1DD5B58E9` | Module 1: Overview KPIs, Western Ghats map circles, trend chart |
| 2 | `02_fire_explorer.png` | 259,612 | `1B30205A06AB4FA217C8F43EB5012DAF130C5D676188EDD2B5E0F7426B51B296` | Module 2: Fire Explorer map workspace, clustering, drawing controls |
| 3 | `03_historical_calendar.png` | 215,414 | `0A4EDE63AC0076A2C23B7151FBD802490FCC3E3A54B6C9C0BDAF9877913F011D` | Module 3: Historical Activity Calendar matrix (2000–2024) |
| 4 | `04_sensor_comparison.png` | 271,759 | `C9569CA481B4B60C71246829FC0BA60FB4A71BD27BEFF856666C81BB6119CCAE` | Module 4: Sensor Comparison (opened by clicking 4th sidebar button) |
| 5 | `05_harmonized_activity.png` | 257,489 | `9B545562B9C924D86DA06F301E04CCBBED66D191AA60A30AF15FD81624B489EB` | Module 5: Harmonized Fire Activity timeseries & proportion cards |
| 6 | `06_anomaly_detection.png` | 244,119 | `07FF5628D7994A2CFFFB7E13E64DA1B4504FDC131BB1FC34680F982D91EA3407` | Module 6: Anomaly Detection pattern intelligence cards & sliders |
| 7 | `07_data_quality.png` | 217,356 | `0950BE2DC94CD9917DAAA80AD73801F8726CB858361F29BFFEA71643530E9159` | Module 7: Data Quality transparency metrics & sensor uptime |
| 8 | `merged_regional_comparison_click.png` | 271,806 | `21E891B71F08428C5475854F9F41621885C4D07C2D768452FA2587B4B9B40676` | Merged Build (`:8443`): Raksha's component mounted via `comparison_regions` |
| 9 | `regional_standalone_palisades.png` | 318,199 | `6E9E9DE186E0A3FAC747350CF1AA085B88D3610FBC383FCC35D09C020968B893` | Standalone (`:8444`): Chart C & table for Pacific Palisades (2005–2026) |
| 10 | `regional_standalone_western_ghats.png` | 319,839 | `9E69B9001491D4E9E13D30D3FCDC9A3B49AAF9933B478FCE9FD6261BA3B6C7DB` | Standalone (`:8444`): Chart C & table for Western Ghats Karnataka (2000–2026) |
| 11 | `regional_standalone_punjab_haryana.png` | 321,060 | `8F81CD340FE6EA22B7C3FC51DDAFAAEC61E818B86495DCE83771F5F1744391E6` | Standalone (`:8444`): Chart C & table for Punjab & Haryana (2000–2026) |
| 12 | `regional_topbar_issue.png` | 301,023 | `2868BDCD1D55ABDE9B6CC78C115C8C58C2D006259212FD9C173FD932D4B189A6` | Standalone (`:8444`): Top-bar filter badge mismatch on Regional page |
