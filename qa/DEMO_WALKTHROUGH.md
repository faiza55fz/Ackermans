# FireTrace Demo Walkthrough & 5-Minute Pitch Script

**Challenge:** NASA Space Apps Challenge – *Harmonizing MODIS and VIIRS Fire Hotspots into a Burning Activity Calendar*  
**Audience:** Hackathon Judges, Technical Evaluators, Geospatial Data Scientists  
**Demo Architecture:**
- **Primary Live App (`http://localhost:8443/`):** Core dashboard featuring real Western Ghats harmonization data, geospatial grid analytics, and model estimates.
- **Regional Deep-Dive App (`http://localhost:8444/`):** Multi-region comparison engine (Palisades, Western Ghats, Punjab & Haryana).

---

## 5-Minute Pitch Chronological Run-Sheet

```
  [0:00] ─── Mission & The Multi-Decade Satellite Problem ─── [0:45]
  [0:45] ─── Overview: Real Geospatial Intelligence (Port 8443) ─── [1:45]
  [1:45] ─── The Harmonization Engine: Calibrating MODIS to VIIRS ─── [2:45]
  [2:45] ─── Multi-Region Validation: Pacific, Tropics & Agriculture (Port 8444) ─── [3:45]
  [3:45] ─── Scientific Transparency & Data Quality ─── [4:30]
  [4:30] ─── Conclusion & Judge Q&A ─── [5:00]
```

---

### [0:00 – 0:45] Act 1: The NASA Fire Data Dilemma
- **What to Display:** `http://localhost:8443/` (Overview Page)
- **What to Say:**
  > *"Judges, NASA’s earth observation program gives us over 24 years of active fire data. But there is a fundamental scientific challenge: MODIS on Terra and Aqua launched in 2000 with a 1 km pixel footprint. In 2012, VIIRS launched with a much finer 375 m resolution and high nighttime sensitivity. When NOAA-20 and NOAA-21 were added, raw detections surged dramatically.*  
  > *If scientists look at raw detection counts, it looks like wildfires exploded overnight. It’s an artifact of satellite sensor upgrades, not an explosion of fire. **FireTrace solves this.** We built a mathematically grounded harmonization pipeline that bridges MODIS and VIIRS into a consistent, long-term burning activity calendar."*

---

### [0:45 – 1:45] Act 2: Overview & Geospatial Intelligence
- **What to Click on `:8443`:** Stay on **Overview**. Point to the 4 KPI cards, then hover over the map circles.
- **What to Say:**
  > *"Here on our Overview dashboard, we aren't showing mock data. This is connected directly to our processed NASA FIRMS dataset for the Western Ghats—one of the world's most critical biodiversity hotspots.*  
  > *Notice our KPIs:*
  > - *Over **133,605 clean detections** across **4,616 observation days** spanning 2000 to late 2026.*
  > - *Aggregated into **92 spatial grid cells** at 0.25° resolution.*
  > - *A mean Fire Radiative Power of **7.26 Megawatts**.*  
  > *Notice the map below: circles are dynamically scaled to the square root of detection volume and color-coded. Cells in orange represent dual-sensor consensus where both MODIS and VIIRS confirmed burning activity."*

---

### [1:45 – 2:45] Act 3: The Harmonization Engine
- **What to Click on `:8443`:** Click **Harmonized Activity** in the sidebar.
- **What to Say:**
  > *"How does the bridge actually work? Let’s navigate to Harmonized Fire Activity.*  
  > *We formulated an overlapping cell-day calibration model during the 2012–2024 co-observation window. As you see here:*
  > - ***76.8% of records** are directly observed.*
  > - ***23.2% of pre-2012 historical records** are estimated using our trained regressor ($R^2 \approx 0.84$).*  
  > *Look at our interactive timeseries: the orange line is observed MODIS, the cyan is observed VIIRS, and the solid gold line is our model-estimated VIIRS and calibrated FRP. This allows climate researchers to analyze fire frequency across a quarter-century baseline without sensor bias."*

---

### [2:45 – 3:45] Act 4: Multi-Region Validation Across Three Continents / Eco-Zones
- **What to Click:** Switch browser tab to `http://localhost:8444/` (Regional Comparison).
- **What to Say & Do:**
  > *"A harmonization model is only as good as its geographical generalizability. We tested our pipeline across three vastly distinct fire regimes:*
  > 1. ***Pacific Palisades, California:** Mediterranean wildland-urban interface with extreme winter wind-driven fire risk. Notice our footnote flagging a fixed low-power heat emitter near -118.72°.*
  > *(Switch dropdown to Western Ghats)*
  > 2. ***Western Ghats, Karnataka:** Tropical deciduous forest with concentrated dry-season burning in February and March.*
  > *(Switch dropdown to Punjab & Haryana)*
  > 3. ***Punjab & Haryana, India:** The global epicenter of post-monsoon agricultural stubble burning. Look at the October and November peaks—sharp, repetitive, and massive.*  
  > *With our toggle controls, judges can view counts on a logarithmic scale or switch between coarse 0.05° and high-resolution 0.01° grid cells to inspect sub-kilometer sensor agreement."*

---

### [3:45 – 4:30] Act 5: Scientific Integrity & Data Quality
- **What to Click on `:8443`:** Click **Data Quality** in the sidebar.
- **What to Say:**
  > *"We built FireTrace with scientific rigor at its foundation:*
  > - *We strictly separated standard science processing (SP) from Near Real-Time (NRT) data, deduplicating the boundary seamlessly.*
  > - *We explicitly mark 2026 as an incomplete year so partial data is never misrepresented.*
  > - *Every estimated metric carries our prominent **'Experimental Model Output'** disclaimer badge, upholding NASA's open-science standards."*

---

### [4:30 – 5:00] Act 6: Closing & Technical Highlights
- **What to Say:**
  > *"To summarize: FireTrace bridges two eras of Earth observation—turning 24 years of fragmented satellite hotspots into an actionable, harmonized burning calendar. The code is modular, tested with automated test suites, and ready for deployment.*  
  > *Thank you, and we'd be thrilled to answer your questions!"*

---

## Technical Tactical Guide for the Presenter

### What NOT to Click on Port 8443
> [!IMPORTANT]
> **Do NOT click the "Regional Comparison" button on port 8443 during the live pitch!**  
> The sidebar navigation displays duplicate "Regional Comparison" buttons (at positions 4 and 8), which is a known integration issue to avoid clicking during the demo.  
> Because of a known integration routing clash between Yashaswi's and Raksha's branches (BUG-001), clicking that button on port 8443 opens the internal sensor metric view instead of Raksha's multi-region analytics.  
> **Always show Regional Comparison in the dedicated tab on `http://localhost:8444/`!**

### If a Judge Asks About the Routing Bug:
> *"During our QA integration testing, we detected a naming collision between teammate branches where two modules shared the 'Regional Comparison' route key. Our QA protocol isolated Raksha’s page on an independent port for validation while documenting the fix in our bug report. Restoring the route is a single-line ternary adjustment."*
