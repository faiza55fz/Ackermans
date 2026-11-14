# NASA FIRMS Active Fire Data Pipeline (MODIS & VIIRS)

This project provides an automated, resumable data extraction, cleaning, and quality-assurance pipeline for NASA FIRMS (Fire Information for Resource Management System) active fire detection products (MODIS and VIIRS).

All operations and scripts are housed inside `DATA/`.

---

## Directory Structure

```text
DATA/
├── src/
│   ├── download.py        # Resumable API downloader respecting FIRMS rate limits
│   ├── ingest.py          # Data standardizer, confidence filter, and Parquet exporter
│   └── checks.py          # Rigorous sanity verification and report generator
├── data/
│   ├── raw/               # Raw untouched CSV downloads grouped by region, sensor, and year
│   └── clean/             # Cleaned Parquet datasets and dropped low-confidence logs
│       └── csv/           # Cleaned CSV mirrors of all datasets
│   └── notebooks/
│   └── 01_inspect.ipynb   # Exploratory inspection comparing MODIS vs VIIRS schemas
├── reports/               # Generated sanity check markdown reports and PNG plots
├── logs/
│   └── download_failures.csv  # Log of any failed API calls (sanitized: MAP_KEY omitted)
├── run_all.py             # End-to-end master runner executing the full pipeline
├── PROGRESS.md            # Checklist of project milestones and verification status
├── requirements.txt       # Python package dependencies
└── README.md              # Documentation and execution instructions
```

---

## Prerequisites & Installation

1. **Python Environment:**
   A Python 3.11+ virtual environment is created at `DATA/.venv`.

   ```bash
   # From the DATA directory:
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **FIRMS MAP_KEY Configuration:**
   You must set your NASA FIRMS `MAP_KEY` as an environment variable before running any download commands:

   - **Windows PowerShell:**
     ```powershell
     $env:FIRMS_MAP_KEY = "your_actual_firms_map_key"
     ```
   - **Windows Command Prompt:**
     ```cmd
     set FIRMS_MAP_KEY=your_actual_firms_map_key
     ```
   - **Persistent across sessions (Windows):**
     ```powershell
     [System.Environment]::SetEnvironmentVariable('FIRMS_MAP_KEY', 'your_actual_firms_map_key', 'User')
     ```

   > **Security Note:** The scripts strictly protect your `MAP_KEY`. It is read dynamically from `FIRMS_MAP_KEY` and is never printed, logged, or saved to disk.

---

## Step-by-Step Execution Guide

### 1. Download Fire Detections (`src/download.py`)
Downloads historical (Standard Processing - SP) and recent (Near Real-Time - NRT) detections in rolling 5-day chunks, with retry backoff, transaction limit handling, and resumption capability.

```bash
# Run test call / specific region:
python src/download.py --region palisades_la --sensor VIIRS_SNPP

# Run all sensors for a region:
python src/download.py --region palisades_la

# Run all configured regions and sensors:
python src/download.py --all
```

### 2. Ingest and Clean Detections (`src/ingest.py`)
Standardizes column headers, applies sensor-specific confidence filtering (MODIS confidence $\ge 30$; VIIRS drop 'low'), records dropped detections to CSV, derives UTC timestamps, and saves clean Parquets.

```bash
# Ingest single region:
python src/ingest.py --region palisades_la

# Ingest all regions:
python src/ingest.py --all
```

### 3. Run Sanity Checks (`src/checks.py`)
Verifies bounding boxes, null counts, non-negative FRP, sensor start date validity, and row count reconciliation.

```bash
python src/checks.py --region palisades_la
```

### 4. Run Everything in Order (`run_all.py`)
Runs download, ingest, sanity checks, and visualizations end-to-end, halting if any check fails:

```bash
python run_all.py
```

---

## How to test the pipeline on the current data

To test the pipeline directly using the included cleaned test data for `palisades_la` (no API key or `download.py` required):

1. **Set up the Python Virtual Environment:**
   ```bash
   cd DATA
   python -m venv .venv
   
   # Activate environment:
   # On Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Verification & Checks (WITHOUT running `download.py`):**
   - **Comprehensive Data Verification:**
     ```bash
     python verify.py
     ```
     Verifies schema (23 columns), 0 duplicates, coordinate boundaries, date bounds, satellite counts, and the January 2025 Palisades wildfire spike.

   - **Sanity Verification Suite:**
     ```bash
     python src/checks.py --region palisades_la
     ```
     Executes all 7 sanity checks and outputs a markdown report to `reports/sanity_palisades_la.md`.

   - **Generate Slide 2 Plot:**
     ```bash
     python src/plot.py --region palisades_la
     ```
     Generates the 200 dpi presentation chart at `reports/slide2_hotspots_per_year_by_sensor_palisades_la.png` with sensor transition annotations.

