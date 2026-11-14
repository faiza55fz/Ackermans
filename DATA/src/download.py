#!/usr/bin/env python3
"""
src/download.py - Resumable NASA FIRMS active-fire data downloader with seasonal windowing.

Downloads active fire data (MODIS and VIIRS) by region, sensor, and 5-day windows.
Respects FIRMS rate limits, logs failed requests safely, and saves raw data
by region, sensor, and year in CSV format.
"""

import os
import sys
import time
import json
import io
import calendar
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pandas as pd

# ==============================================================================
# NAMED CONSTANTS & SETTINGS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
LOGS_DIR = BASE_DIR / "logs"
FAILURES_LOG_FILE = LOGS_DIR / "download_failures.csv"

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
AVAILABILITY_URL = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv"
STATUS_URL = "https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status"

MAX_DAY_RANGE = 5
DEFAULT_PAUSE_SECONDS = 0.10
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0
DEFAULT_MAX_WORKERS = 4

# Transaction planning estimates: ~8 transactions per 5-day request
TX_PER_REQUEST_ESTIMATE = 8
SAFE_TX_CEILING = 4900
TX_RESUME_TARGET = 1000

# Bounding boxes as (west, south, east, north) in lon/lat
REGIONS = {
    "palisades_la": {
        "bbox": (-118.75, 33.95, -118.40, 34.20),
        "name": "Pacific Palisades, Los Angeles, USA"
    },
    "western_ghats_karnataka": {
        "bbox": (74.0, 13.3, 76.1, 15.8),
        "name": "Western Ghats, Karnataka, India"
    },
    "punjab_haryana": {
        "bbox": (73.8, 27.6, 77.7, 32.6),
        "name": "Punjab & Haryana, India"
    },
    "nsw_victoria_au": {
        "bbox": (140.9, -39.2, 154.0, -28.1),
        "name": "New South Wales & Victoria, Australia"
    }
}

REGIONS_ORDER = [
    "palisades_la",
    "western_ghats_karnataka",
    "punjab_haryana",
    "nsw_victoria_au"
]

# FULL YEAR DOWNLOAD POLICY (no seasonal window restrictions)
# All dates from sensor launch to current date / cutoff are downloaded.


# Sensor definitions and date parameters
SENSOR_CONFIGS = {
    "MODIS": {
        "streams": [
            {
                "stream_id": "MODIS",
                "sp_source": "MODIS_SP",
                "nrt_source": "MODIS_NRT",
                "start_date": "2000-11-01",
                "end_date": None,  # today
                "satellites": ["Terra", "Aqua"]
            }
        ],
        "default_columns": [
            "latitude", "longitude", "brightness", "scan", "track",
            "acq_date", "acq_time", "satellite", "instrument", "confidence",
            "version", "bright_t31", "frp", "daynight", "type", "processing"
        ]
    },
    "VIIRS": {
        "streams": [
            {
                "stream_id": "VIIRS_SNPP",
                "sp_source": "VIIRS_SNPP_SP",
                "nrt_source": "VIIRS_SNPP_NRT",
                "start_date": "2012-01-20",
                "end_date": "2026-11-02",  # FIRMS archive cutoff
                "satellites": ["N"]
            },
            {
                "stream_id": "VIIRS_NOAA20",
                "sp_source": "VIIRS_NOAA20_SP",
                "nrt_source": "VIIRS_NOAA20_NRT",
                "start_date": "2018-04-01",
                "end_date": None,  # today
                "satellites": ["N20"]
            },
            {
                "stream_id": "VIIRS_NOAA21",
                "sp_source": "VIIRS_NOAA21_SP",
                "nrt_source": "VIIRS_NOAA21_NRT",
                "start_date": "2023-03-01",
                "end_date": None,  # today
                "satellites": ["N21"]
            }
        ],
        "default_columns": [
            "latitude", "longitude", "bright_ti4", "scan", "track",
            "acq_date", "acq_time", "satellite", "instrument", "confidence",
            "version", "bright_ti5", "frp", "daynight", "type", "processing"
        ]
    }
}


# ==============================================================================
# CREDENTIALS & SAFE ENVIRONMENT HANDLING
# ==============================================================================
def get_map_key() -> str:
    """Retrieve FIRMS MAP_KEY without ever printing or logging it."""
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as reg_key:
                val, _ = winreg.QueryValueEx(reg_key, "FIRMS_MAP_KEY")
                key = str(val).strip()
        except Exception:
            pass

    if not key:
        print("ERROR: FIRMS_MAP_KEY environment variable is missing.", file=sys.stderr)
        print("Please set FIRMS_MAP_KEY before running this script.", file=sys.stderr)
        sys.exit(1)
    return key


def log_failure(region: str, sensor: str, start_date: str, error_msg: str):
    """Safely log failed API windows to logs/download_failures.csv without logging the key or URL."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    clean_error = error_msg.replace(",", ";").replace("\n", " ").strip()
    file_exists = FAILURES_LOG_FILE.exists()

    with open(FAILURES_LOG_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("region,sensor,start_date,error\n")
        f.write(f"{region},{sensor},{start_date},{clean_error}\n")


# ==============================================================================
# DATA AVAILABILITY & TRANSACTION TRACKING
# ==============================================================================
def fetch_data_availability(map_key: str, session: requests.Session) -> dict:
    """Query FIRMS data availability endpoint to determine exact SP vs NRT date boundaries."""
    url = f"{AVAILABILITY_URL}/{map_key}/all"
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text))
            avail = {}
            for _, row in df.iterrows():
                data_id = str(row["data_id"]).strip()
                avail[data_id] = {
                    "min_date": str(row["min_date"]).strip(),
                    "max_date": str(row["max_date"]).strip()
                }
            return avail
    except Exception as e:
        print(f"Warning: Could not fetch data availability ({e}), using default dates.")
    return {}


def check_transaction_status(map_key: str, session: requests.Session) -> dict:
    """Check current transaction usage from FIRMS mapkey_status endpoint."""
    url = f"{STATUS_URL}/?MAP_KEY={map_key}"
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def wait_for_transaction_capacity(map_key: str, session: requests.Session, target_below: int = TX_RESUME_TARGET):
    """Wait for rolling 10-minute transaction count to drop below target_below."""
    print(f"\n[RATE-LIMIT THROTTLE] Holding for 10-minute rolling window to reset below {target_below:,}...")
    while True:
        status = check_transaction_status(map_key, session)
        curr = status.get("current_transactions", 5000)
        lim = status.get("transaction_limit", 5000)
        print(f"  [WINDOW STATUS] Transactions used: {curr:,} / {lim:,} (Waiting for < {target_below:,})")
        if curr < target_below:
            print(f"  [RESUMING] Available capacity restored ({curr:,} used). Resuming downloads...\n")
            return
        time.sleep(20)


# ==============================================================================
# MANIFEST & RESUMABILITY
# ==============================================================================
def load_manifest(manifest_path: Path) -> dict:
    """Load or initialize manifest tracking completed years and windows."""
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"completed_years": [], "completed_windows": []}


def save_manifest(manifest_path: Path, manifest_data: dict):
    """Atomically save manifest tracking progress."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = manifest_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    temp_path.replace(manifest_path)


# ==============================================================================
# FULL YEAR WINDOW GENERATION
# ==============================================================================
def generate_windows(
    region_id: str,
    sensor_id: str,
    year: int,
    stream_start: date,
    stream_end: date
):
    """
    Generate non-overlapping 5-day windows covering the full calendar year
    for a given stream, bounded by stream_start and stream_end.
    """
    yr_start = date(year, 1, 1)
    yr_end = date(year, 12, 31)

    act_start = max(yr_start, stream_start)
    act_end = min(yr_end, stream_end)

    if act_start > act_end:
        return

    cur = act_start
    while cur <= act_end:
        window_days = min(MAX_DAY_RANGE, (act_end - cur).days + 1)
        yield cur.strftime("%Y-%m-%d"), window_days
        cur += timedelta(days=window_days)


# ==============================================================================
# WINDOW DOWNLOAD WORKER
# ==============================================================================
def fetch_window(
    map_key: str,
    source: str,
    bbox_str: str,
    start_date_str: str,
    day_range: int,
    session: requests.Session,
    retries: int = MAX_RETRIES
) -> tuple[int, list[dict], str]:
    """
    Fetch a single 5-day window from the FIRMS Area API.
    Returns: (status_code, list_of_records, error_message)
    """
    url = f"{FIRMS_BASE_URL}/{map_key}/{source}/{bbox_str}/{day_range}/{start_date_str}"
    last_err = ""

    for attempt in range(retries):
        try:
            r = session.get(url, timeout=25)
            text = r.text.strip()
            if "transaction limit" in text.lower() or "limit exceeded" in text.lower() or r.status_code == 429:
                return 429, [], "Transaction limit reached"

            if r.status_code == 200:
                if not text:
                    return 200, [], ""
                df = pd.read_csv(io.StringIO(text))
                records = df.to_dict(orient="records")
                return 200, records, ""
            else:
                last_err = f"HTTP {r.status_code}: {text[:100]}"
        except Exception as e:
            last_err = f"Exception: {str(e)[:100]}"

        if attempt < retries - 1:
            time.sleep(BACKOFF_FACTOR ** attempt)

    return 500, [], last_err


# ==============================================================================
# SENSOR & REGION DOWNLOAD ORCHESTRATION
# ==============================================================================
def download_stream_year(
    map_key: str,
    region_id: str,
    sensor_id: str,
    stream: dict,
    year: int,
    bbox_str: str,
    availability: dict,
    session: requests.Session,
    manifest: dict,
    manifest_path: Path,
    max_workers: int = DEFAULT_MAX_WORKERS
) -> tuple[list[dict], bool]:
    """
    Download active fire data for one stream within a specific calendar year.
    Returns: (list_of_records, limit_hit_flag)
    """
    stream_id = stream["stream_id"]
    sp_source = stream["sp_source"]
    nrt_source = stream["nrt_source"]

    sp_max_str = availability.get(sp_source, {}).get("max_date", "2026-08-31")
    sp_max_date = datetime.strptime(sp_max_str, "%Y-%m-%d").date()

    stream_start = datetime.strptime(stream["start_date"], "%Y-%m-%d").date()
    stream_end_cfg = stream["end_date"]
    if stream_end_cfg:
        stream_end = datetime.strptime(stream_end_cfg, "%Y-%m-%d").date()
    else:
        stream_end = date.today()

    # Collect pending windows based on full-year calendar
    pending_tasks = []
    for d_str, day_span in generate_windows(region_id, sensor_id, year, stream_start, stream_end):
        w_id = f"{stream_id}_{d_str}_{day_span}"
        if w_id in manifest["completed_windows"]:
            continue
        w_date = datetime.strptime(d_str, "%Y-%m-%d").date()
        if w_date <= sp_max_date:
            source = sp_source
            proc = "SP"
        else:
            source = nrt_source
            proc = "NRT"
        pending_tasks.append((w_id, source, proc, d_str, day_span))

    if not pending_tasks:
        return [], False

    records_collected = []
    limit_hit = False

    def fetch_task(item):
        w_id, source, proc, d_str, day_span = item
        time.sleep(DEFAULT_PAUSE_SECONDS)
        code, recs, err = fetch_window(map_key, source, bbox_str, d_str, day_span, session)
        return w_id, d_str, proc, code, recs, err

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_task, item): item for item in pending_tasks}
        for fut in as_completed(futures):
            w_id, d_str, proc, code, recs, err = fut.result()
            if code == 200:
                for r in recs:
                    r["processing"] = proc
                records_collected.extend(recs)
                manifest["completed_windows"].append(w_id)
            elif code == 429 or "transaction limit" in err.lower():
                print(f"\n[ALERT] Transaction limit reached while downloading {stream_id} ({d_str}).")
                log_failure(region_id, stream_id, d_str, err)
                limit_hit = True
                save_manifest(manifest_path, manifest)
                executor.shutdown(wait=False, cancel_futures=True)
                break
            else:
                log_failure(region_id, stream_id, d_str, err)
                manifest["completed_windows"].append(w_id)

    save_manifest(manifest_path, manifest)
    return records_collected, limit_hit


def download_sensor(
    map_key: str,
    region_id: str,
    sensor_id: str,
    availability: dict,
    session: requests.Session,
    max_workers: int = DEFAULT_MAX_WORKERS,
    wait_on_limit: bool = True
) -> bool:
    """
    Download full seasonal date ranges for a sensor in a region, saving one CSV per year.
    Returns: True if complete, False if stopped.
    """
    bbox = REGIONS[region_id]["bbox"]
    bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    sensor_cfg = SENSOR_CONFIGS[sensor_id]
    default_cols = sensor_cfg["default_columns"]

    raw_sensor_dir = DATA_RAW_DIR / region_id / sensor_id
    raw_sensor_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_sensor_dir / ".download_manifest.json"
    manifest = load_manifest(manifest_path)

    all_starts = [datetime.strptime(s["start_date"], "%Y-%m-%d").date() for s in sensor_cfg["streams"]]
    min_year = min(d.year for d in all_starts)
    max_year = date.today().year

    print(f"\n>>> Starting download for Region: {region_id} | Sensor: {sensor_id} (Years {min_year}-{max_year})")

    year = min_year
    while year <= max_year:
        year_file = raw_sensor_dir / f"{year}.csv"

        # Collect all windows for this year across streams
        all_year_windows = []
        for stream in sensor_cfg["streams"]:
            s_start = datetime.strptime(stream["start_date"], "%Y-%m-%d").date()
            s_end = datetime.strptime(stream["end_date"], "%Y-%m-%d").date() if stream["end_date"] else date.today()
            for d_str, day_span in generate_windows(region_id, sensor_id, year, s_start, s_end):
                all_year_windows.append(f"{stream['stream_id']}_{d_str}_{day_span}")

        completed_set = set(manifest.get("completed_windows", []))
        if all_year_windows and all(w in completed_set for w in all_year_windows) and year_file.exists():
            year += 1
            continue

        # Rate-limiting safety check before starting year
        if wait_on_limit:
            stat = check_transaction_status(map_key, session)
            curr_tx = stat.get("current_transactions", 0)
            if curr_tx >= SAFE_TX_CEILING:
                print(f"[RATE-LIMIT] Current usage {curr_tx:,} approaching limit. Cooling down...")
                wait_for_transaction_capacity(map_key, session, target_below=TX_RESUME_TARGET)

        year_records = []
        if year_file.exists():
            try:
                df_existing = pd.read_csv(year_file)
                year_records = df_existing.to_dict(orient="records")
            except Exception:
                year_records = []

        year_limit_hit = False
        for stream in sensor_cfg["streams"]:
            new_records, limit_hit = download_stream_year(
                map_key=map_key,
                region_id=region_id,
                sensor_id=sensor_id,
                stream=stream,
                year=year,
                bbox_str=bbox_str,
                availability=availability,
                session=session,
                manifest=manifest,
                manifest_path=manifest_path,
                max_workers=max_workers
            )
            year_records.extend(new_records)
            if limit_hit:
                year_limit_hit = True
                break

        # Save/update year CSV
        if year_records:
            df_year = pd.DataFrame(year_records)
            for col in default_cols:
                if col not in df_year.columns:
                    df_year[col] = None
            cols = [c for c in default_cols if c in df_year.columns] + [c for c in df_year.columns if c not in default_cols]
            df_year = df_year[cols]
            # Deduplicate by key coordinates and acq datetime
            dedup_cols = [c for c in ["latitude", "longitude", "acq_date", "acq_time", "satellite"] if c in df_year.columns]
            if dedup_cols:
                df_year = df_year.drop_duplicates(subset=dedup_cols)
            df_year.to_csv(year_file, index=False)
        else:
            df_empty = pd.DataFrame(columns=default_cols)
            df_empty.to_csv(year_file, index=False)

        if year_limit_hit:
            if wait_on_limit:
                print(f"[PAUSED] Progress saved cleanly for {year}. Waiting for limit reset...")
                wait_for_transaction_capacity(map_key, session, target_below=TX_RESUME_TARGET)
                continue
            else:
                print(f"[PAUSED] Progress saved cleanly for {year}. Rerun later to resume.")
                return False

        completed_set = set(manifest.get("completed_windows", []))
        if all_year_windows and all(w in completed_set for w in all_year_windows):
            if year not in manifest["completed_years"]:
                manifest["completed_years"].append(year)
            save_manifest(manifest_path, manifest)
        print(f"  [DONE] Year {year}: {len(year_records)} detections saved -> {year_file.name}")
        year += 1

    return True


# ==============================================================================
# SUMMARY TABLE GENERATION
# ==============================================================================
def print_summary_table(region_filter: str = None, sensor_filter: str = None):
    """
    Print table of: region, sensor, number of files, number of rows, first date, last date.
    """
    rows = []
    if not DATA_RAW_DIR.exists():
        print("No raw data found.")
        return

    regions = [region_filter] if region_filter and region_filter != "all" else REGIONS_ORDER
    sensors = [sensor_filter] if sensor_filter and sensor_filter != "all" else list(SENSOR_CONFIGS.keys())

    for reg in regions:
        reg_dir = DATA_RAW_DIR / reg
        if not reg_dir.exists():
            continue
        for sens in sensors:
            sens_dir = reg_dir / sens
            if not sens_dir.exists():
                continue
            csv_files = sorted(list(sens_dir.glob("*.csv")))
            num_files = len(csv_files)
            total_rows = 0
            all_dates = []

            for f in csv_files:
                try:
                    df = pd.read_csv(f)
                    total_rows += len(df)
                    if "acq_date" in df.columns and len(df) > 0:
                        valid_dates = df["acq_date"].dropna().astype(str).tolist()
                        all_dates.extend(valid_dates)
                except Exception:
                    pass

            first_date = min(all_dates) if all_dates else "None"
            last_date = max(all_dates) if all_dates else "None"

            rows.append({
                "Region": reg,
                "Sensor": sens,
                "Files": num_files,
                "Rows": total_rows,
                "First Date": first_date,
                "Last Date": last_date
            })

    if rows:
        df_summary = pd.DataFrame(rows)
        print("\n" + "=" * 80)
        print("RAW DATA DOWNLOAD SUMMARY")
        print("=" * 80)
        print(df_summary.to_string(index=False))
        print("=" * 80 + "\n")
    else:
        print("No downloaded files found matching criteria.")


# ==============================================================================
# CLI ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Download NASA FIRMS active fire data.")
    parser.add_argument("--region", choices=REGIONS_ORDER + ["all"], default="palisades_la",
                        help="Region identifier or 'all'")
    parser.add_argument("--sensor", choices=list(SENSOR_CONFIGS.keys()) + ["all"], default="all",
                        help="Sensor identifier ('MODIS', 'VIIRS', or 'all')")
    parser.add_argument("--all", action="store_true", help="Download all regions and all sensors")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS,
                        help=f"Concurrent worker threads (default: {DEFAULT_MAX_WORKERS})")
    parser.add_argument("--wait-on-limit", action="store_true", default=True,
                        help="Wait automatically if FIRMS transaction limit is hit until window rolls off")
    parser.add_argument("--summary-only", action="store_true", help="Print summary of downloaded data and exit")

    args = parser.parse_args()

    if args.summary_only:
        print_summary_table(args.region, args.sensor)
        return

    map_key = get_map_key()
    session = requests.Session()

    stat = check_transaction_status(map_key, session)
    if stat:
        print(f"FIRMS API Key Status: Limit = {stat.get('transaction_limit')}, Current Used = {stat.get('current_transactions')}")

    availability = fetch_data_availability(map_key, session)

    target_regions = REGIONS_ORDER if (args.all or args.region == "all") else [args.region]
    target_sensors = list(SENSOR_CONFIGS.keys()) if (args.all or args.sensor == "all") else [args.sensor]

    for reg in target_regions:
        for sens in target_sensors:
            success = download_sensor(
                map_key=map_key,
                region_id=reg,
                sensor_id=sens,
                availability=availability,
                session=session,
                max_workers=args.workers,
                wait_on_limit=args.wait_on_limit
            )
            if not success:
                print(f"[STOPPING] Execution halted due to API transaction limit. Progress saved.")
                sys.exit(0)

    print_summary_table(args.region if not args.all else "all", args.sensor if not args.all else "all")


if __name__ == "__main__":
    main()
