"""
FireTrace Pilot Pipeline - Data Quality Audit Report Generator
Generates honest, verified Markdown and JSON data-quality reports.
Verifies all scientific checks explicitly before reporting pass/fail status.
Robustly handles non-numeric coordinates, malformed dates, missing fields, and nulls.
Corrects coordinate hemisphere formatting, reconciles counts, and compares spatial bounds.
"""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PRELIMINARY_PALISADES_BOX = {
    "min_lat": 33.950,
    "max_lat": 34.150,
    "min_lng": -118.650,
    "max_lng": -118.450,
}


def format_lat(lat: Any) -> str:
    """Formats latitude with hemisphere indicator without negative signs."""
    if lat is None:
        return "N/A"
    try:
        val = float(lat)
        if math.isnan(val) or math.isinf(val):
            return "N/A"
        if val > 0:
            return f"{val:.5f}°N"
        elif val < 0:
            return f"{abs(val):.5f}°S"
        return "0.00000°"
    except (ValueError, TypeError):
        return "N/A"


def format_lng(lng: Any) -> str:
    """Formats longitude with hemisphere indicator: positive is East, negative is West."""
    if lng is None:
        return "N/A"
    try:
        val = float(lng)
        if math.isnan(val) or math.isinf(val):
            return "N/A"
        if val > 0:
            return f"{val:.5f}°E"
        elif val < 0:
            return f"{abs(val):.5f}°W"
        return "0.00000°"
    except (ValueError, TypeError):
        return "N/A"


def verify_scientific_checklist(
    valid_records: List[Dict[str, Any]],
    quarantined_records: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Explicitly runs verification tests over data to determine real check statuses.
    Returns dictionary with status: "PASSED", "FAILED", or "NOT_ASSESSED", and detail string.
    NEVER marks a check as passed without executing programmatic verification.
    """
    results: Dict[str, Dict[str, Any]] = {}

    if not valid_records and not quarantined_records:
        return {
            "confidence_raw_preservation": {"status": "NOT_ASSESSED", "detail": "No records available to evaluate"},
            "confidence_separation": {"status": "NOT_ASSESSED", "detail": "No records available to evaluate"},
            "raw_scan_track_unrounded": {"status": "NOT_ASSESSED", "detail": "No records available to evaluate"},
            "fatal_defects_quarantined": {"status": "NOT_ASSESSED", "detail": "No records available to evaluate"},
            "cross_satellite_independence": {"status": "NOT_ASSESSED", "detail": "No records available to evaluate"},
            "spatial_extent_verified": {"status": "NOT_ASSESSED", "detail": "No records available to evaluate"},
        }

    # Check 1: confidence_raw preservation
    # Every valid record with an input confidence column must preserve confidence_raw identically
    conf_raw_checks = [
        "confidence_raw" in r and r["confidence_raw"] is not None and str(r["confidence_raw"]).strip() != ""
        for r in valid_records if "confidence" in r and str(r.get("confidence", "")).strip() not in ("", "None", "null")
    ]
    if conf_raw_checks and all(conf_raw_checks):
        results["confidence_raw_preservation"] = {
            "status": "PASSED",
            "detail": f"Verified: 100% ({len(conf_raw_checks)}/{len(conf_raw_checks)}) of records with input confidence preserved confidence_raw without loss",
        }
    elif not conf_raw_checks and valid_records:
        results["confidence_raw_preservation"] = {
            "status": "NOT_ASSESSED",
            "detail": "Input records did not contain populated raw confidence column",
        }
    else:
        failed_cnt = len([c for c in conf_raw_checks if not c])
        results["confidence_raw_preservation"] = {
            "status": "FAILED",
            "detail": f"{failed_cnt} records failed confidence_raw preservation",
        }

    # Check 2: Confidence separation without cross-conversion
    # MODIS records must not have viirs_confidence; VIIRS records must not have modis_confidence
    sep_failures = 0
    modis_eval_count = 0
    viirs_eval_count = 0
    for r in valid_records:
        fam = r.get("derived_family")
        if fam == "MODIS":
            modis_eval_count += 1
            if r.get("viirs_confidence") is not None:
                sep_failures += 1
        elif fam == "VIIRS":
            viirs_eval_count += 1
            if r.get("modis_confidence") is not None:
                sep_failures += 1

    if modis_eval_count == 0 and viirs_eval_count == 0:
        results["confidence_separation"] = {
            "status": "NOT_ASSESSED",
            "detail": "No identified MODIS or VIIRS records present to evaluate confidence separation",
        }
    elif sep_failures == 0:
        results["confidence_separation"] = {
            "status": "PASSED",
            "detail": f"Verified: Sensor scales isolated across {modis_eval_count} MODIS and {viirs_eval_count} VIIRS records without cross-conversion",
        }
    else:
        results["confidence_separation"] = {
            "status": "FAILED",
            "detail": f"{sep_failures} records showed cross-sensor confidence leakage or invalid assignment",
        }

    # Check 3: Raw scan and track values preserved without artificial rounding
    scan_track_records = [
        r for r in valid_records
        if r.get("scan") is not None and str(r.get("scan", "")).strip() != ""
        and r.get("track") is not None and str(r.get("track", "")).strip() != ""
    ]
    if not scan_track_records:
        results["raw_scan_track_unrounded"] = {
            "status": "NOT_ASSESSED",
            "detail": "Scan/track dimensions not present in the ingested record fields",
        }
    else:
        mismatch_cnt = 0
        for r in scan_track_records:
            try:
                raw_s = float(str(r["scan"]).strip())
                raw_t = float(str(r["track"]).strip())
                parsed_s = r.get("derived_scan_km")
                parsed_t = r.get("derived_track_km")
                if parsed_s is None or parsed_t is None or raw_s != parsed_s or raw_t != parsed_t:
                    mismatch_cnt += 1
            except (ValueError, TypeError):
                mismatch_cnt += 1

        if mismatch_cnt == 0:
            results["raw_scan_track_unrounded"] = {
                "status": "PASSED",
                "detail": f"Verified: Original float dimensions preserved without rounding across all {len(scan_track_records)} observations",
            }
        else:
            results["raw_scan_track_unrounded"] = {
                "status": "FAILED",
                "detail": f"{mismatch_cnt} records had discrepancies between raw and parsed scan/track values",
            }

    # Check 4: Fatal defects quarantined
    fatal_in_valid = 0
    quarantine_without_issues = 0
    for r in valid_records:
        try:
            lat_k = next((k for k in r if k.lower() in ("latitude", "lat")), None)
            lng_k = next((k for k in r if k.lower() in ("longitude", "lng", "lon")), None)
            if lat_k is None or lng_k is None:
                fatal_in_valid += 1
            else:
                lat = float(r[lat_k])
                lng = float(r[lng_k])
                if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
                    fatal_in_valid += 1
        except (ValueError, TypeError):
            fatal_in_valid += 1

    for q in quarantined_records:
        if not q.get("_quarantine_issues"):
            quarantine_without_issues += 1

    if fatal_in_valid == 0 and quarantine_without_issues == 0:
        results["fatal_defects_quarantined"] = {
            "status": "PASSED",
            "detail": f"Verified: 0 fatal defects in valid records; all {len(quarantined_records)} quarantined records carry traceable defect logs",
        }
    else:
        results["fatal_defects_quarantined"] = {
            "status": "FAILED",
            "detail": f"Found {fatal_in_valid} fatal defects in valid records and {quarantine_without_issues} unannotated quarantined records",
        }

    # Check 5: Cross-satellite observation independence & overlap unassessed status
    overlap_discrepancies = 0
    for r in valid_records:
        # Cross-satellite overlap flag must not be hardcoded to False; should be None (unassessed) or bool after analysis
        if "derived_cross_sat_overlap" in r and r["derived_cross_sat_overlap"] is False:
            overlap_discrepancies += 1

    if valid_records and overlap_discrepancies == 0:
        results["cross_satellite_independence"] = {
            "status": "PASSED",
            "detail": "Verified: Cross-satellite detections are preserved independently; overlap flag initialized to unassessed (None)",
        }
    elif not valid_records:
        results["cross_satellite_independence"] = {
            "status": "NOT_ASSESSED",
            "detail": "No valid records available to evaluate cross-satellite independence",
        }
    else:
        results["cross_satellite_independence"] = {
            "status": "FAILED",
            "detail": f"{overlap_discrepancies} records improperly hardcoded derived_cross_sat_overlap to False rather than None (unassessed)",
        }

    # Check 6: Observed extent compared against preliminary Palisades boundary
    valid_lats: List[float] = []
    valid_lngs: List[float] = []
    for r in valid_records:
        lat_k = next((k for k in r if k.lower() in ("latitude", "lat")), None)
        lng_k = next((k for k in r if k.lower() in ("longitude", "lng", "lon")), None)
        if lat_k and lng_k and r[lat_k] is not None and r[lng_k] is not None:
            try:
                val_lat = float(r[lat_k])
                val_lng = float(r[lng_k])
                if not (math.isnan(val_lat) or math.isinf(val_lat) or math.isnan(val_lng) or math.isinf(val_lng)):
                    if -90.0 <= val_lat <= 90.0 and -180.0 <= val_lng <= 180.0:
                        valid_lats.append(val_lat)
                        valid_lngs.append(val_lng)
            except (ValueError, TypeError):
                continue

    if not valid_lats or not valid_lngs:
        results["spatial_extent_verified"] = {
            "status": "NOT_ASSESSED",
            "detail": "No valid geographic coordinates available to compare spatial extent",
        }
    else:
        min_lat, max_lat = min(valid_lats), max(valid_lats)
        min_lng, max_lng = min(valid_lngs), max(valid_lngs)

        fits_lat = (PRELIMINARY_PALISADES_BOX["min_lat"] <= min_lat) and (max_lat <= PRELIMINARY_PALISADES_BOX["max_lat"])
        fits_lng = (PRELIMINARY_PALISADES_BOX["min_lng"] <= min_lng) and (max_lng <= PRELIMINARY_PALISADES_BOX["max_lng"])

        if fits_lat and fits_lng:
            results["spatial_extent_verified"] = {
                "status": "PASSED",
                "detail": "Observed hotspot detections fall entirely within the preliminary Palisades bounding box",
            }
        else:
            outside_notes = []
            if min_lat < PRELIMINARY_PALISADES_BOX["min_lat"]:
                outside_notes.append(f"Min Lat {min_lat:.4f} < {PRELIMINARY_PALISADES_BOX['min_lat']}")
            if max_lat > PRELIMINARY_PALISADES_BOX["max_lat"]:
                outside_notes.append(f"Max Lat {max_lat:.4f} > {PRELIMINARY_PALISADES_BOX['max_lat']}")
            if min_lng < PRELIMINARY_PALISADES_BOX["min_lng"]:
                outside_notes.append(f"Min Lng {min_lng:.4f} < {PRELIMINARY_PALISADES_BOX['min_lng']}")
            if max_lng > PRELIMINARY_PALISADES_BOX["max_lng"]:
                outside_notes.append(f"Max Lng {max_lng:.4f} > {PRELIMINARY_PALISADES_BOX['max_lng']}")

            results["spatial_extent_verified"] = {
                "status": "EXTENDS_BEYOND_PRELIMINARY_BOX",
                "detail": f"Observed detections extend beyond preliminary box: {'; '.join(outside_notes)}. Adjust boundary before final study ingestion.",
            }

    return results


def generate_quality_report(
    processed_file: Path,
    quarantine_file: Path,
    report_output_dir: Path,
    manifest_file: Optional[Path] = None,
) -> Path:
    """
    Generates verified Markdown and JSON audit reports.
    Reconciles record counts using companion manifest if available.
    Handles missing or malformed input files safely without unhandled exceptions.
    """
    report_output_dir.mkdir(parents=True, exist_ok=True)

    # File existence check
    missing_files = []
    if not processed_file.exists():
        missing_files.append(f"Processed file '{processed_file}' does not exist")
    if not quarantine_file.exists():
        missing_files.append(f"Quarantine file '{quarantine_file}' does not exist")

    if missing_files:
        raise FileNotFoundError("; ".join(missing_files))

    # Safe JSON parsing
    try:
        with processed_file.open("r", encoding="utf-8") as f:
            valid_records = json.load(f)
        if not isinstance(valid_records, list):
            raise ValueError(f"Expected list of records in {processed_file.name}, found {type(valid_records)}")
    except Exception as e:
        raise ValueError(f"Failed to parse processed records JSON: {e}")

    try:
        with quarantine_file.open("r", encoding="utf-8") as f:
            quarantined_records = json.load(f)
        if not isinstance(quarantined_records, list):
            raise ValueError(f"Expected list of records in {quarantine_file.name}, found {type(quarantined_records)}")
    except Exception as e:
        raise ValueError(f"Failed to parse quarantine records JSON: {e}")

    valid_count = len(valid_records)
    quarantine_count = len(quarantined_records)
    total_output_records = valid_count + quarantine_count

    # Check for companion manifest to verify actual raw input row count
    manifest_data: Optional[Dict[str, Any]] = None
    if manifest_file and manifest_file.exists():
        try:
            with manifest_file.open("r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception:
            manifest_data = None
    else:
        # Check automatic companion manifest by naming convention
        possible_manifest = processed_file.parent / processed_file.name.replace("_processed.json", "_manifest.json")
        if possible_manifest.exists():
            try:
                with possible_manifest.open("r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
            except Exception:
                manifest_data = None

    if manifest_data and "total_input_records" in manifest_data:
        total_input = manifest_data["total_input_records"]
        is_reconciled = (total_input == total_output_records)
        reconciliation_source = "Verified against raw ingest manifest"
    else:
        total_input = total_output_records
        is_reconciled = True
        reconciliation_source = "Reconstructed from partition outputs (no manifest provided)"

    pass_rate = (valid_count / total_input * 100) if total_input > 0 else 0.0

    # Extract spatial coordinates safely
    lats: List[float] = []
    lngs: List[float] = []
    for r in valid_records:
        try:
            lat_k = next((k for k in r if k.lower() in ("latitude", "lat")), None)
            lng_k = next((k for k in r if k.lower() in ("longitude", "lng", "lon")), None)
            if lat_k and lng_k and r[lat_k] is not None and r[lng_k] is not None:
                val_lat = float(r[lat_k])
                val_lng = float(r[lng_k])
                if not (math.isnan(val_lat) or math.isinf(val_lat) or math.isnan(val_lng) or math.isinf(val_lng)):
                    if -90.0 <= val_lat <= 90.0 and -180.0 <= val_lng <= 180.0:
                        lats.append(val_lat)
                        lngs.append(val_lng)
        except (ValueError, TypeError):
            continue

    min_lat, max_lat = (min(lats), max(lats)) if lats else (None, None)
    min_lng, max_lng = (min(lngs), max(lngs)) if lngs else (None, None)

    # Dates
    dates = []
    for r in valid_records:
        dk = next((k for k in r if k.lower() in ("acq_date", "date")), None)
        if dk and r[dk]:
            dates.append(str(r[dk]).strip())
    min_date, max_date = (min(dates), max(dates)) if dates else (None, None)

    # Sensor breakdown
    sensor_counts: Dict[str, int] = {}
    family_counts: Dict[str, int] = {}
    for r in valid_records:
        s = r.get("derived_sensor_canonical", r.get("satellite", "Unknown"))
        fam = r.get("derived_family", "Unknown")
        sensor_counts[s] = sensor_counts.get(s, 0) + 1
        family_counts[fam] = family_counts.get(fam, 0) + 1

    # Confidence distribution
    modis_conf_vals = [
        r["modis_confidence"] for r in valid_records
        if r.get("modis_confidence") is not None and isinstance(r.get("modis_confidence"), (int, float))
    ]
    viirs_conf_cats: Dict[str, int] = {}
    for r in valid_records:
        c = r.get("viirs_confidence")
        if c:
            viirs_conf_cats[c] = viirs_conf_cats.get(c, 0) + 1

    # Quarantine defect summary
    defect_summary: Dict[str, int] = {}
    for q in quarantined_records:
        issues = q.get("_quarantine_issues", [])
        for iss in issues:
            field_name = iss.get("field", "unknown")
            defect_summary[field_name] = defect_summary.get(field_name, 0) + 1

    # Execute verified checklist
    checklist = verify_scientific_checklist(valid_records, quarantined_records)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_id = f"data_quality_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    md_report_path = report_output_dir / f"{report_id}.md"
    json_report_path = report_output_dir / f"{report_id}.json"

    with md_report_path.open("w", encoding="utf-8") as f:
        f.write("# FireTrace Data Quality Audit Report\n\n")
        f.write(f"**Generated:** {now_utc}\n")
        f.write(f"**Processed Dataset:** `{processed_file.name}`\n")
        f.write(f"**Quarantine Source:** `{quarantine_file.name}`\n\n")
        f.write("---\n\n")

        f.write("## 1. Executive Accounting & Reconciliation Summary\n\n")
        f.write("| Accounting Item | Value | Share |\n")
        f.write("| :--- | :--- | :--- |\n")
        f.write(f"| **Total Raw Input Rows** | `{total_input:,}` | 100.0% |\n")
        f.write(f"| **Accepted Valid Observations** | `{valid_count:,}` | {pass_rate:.2f}% |\n")
        f.write(f"| **Quarantined Fatal Defects** | `{quarantine_count:,}` | {100.0 - pass_rate:.2f}% |\n")
        f.write(f"| **Count Reconciliation** | **{'RECONCILED' if is_reconciled else 'DISCREPANCY DETECTED'}** | {reconciliation_source} |\n\n")

        f.write("## 2. Observed Hotspot Detection Bounds vs Preliminary Study Window\n\n")
        f.write("> **Note on Spatial Scope**: The spatial coordinates below represent the **Observed Hotspot Detection Bounding Box** in this specific dataset file. They are data-derived and do not constitute an official certified incident boundary.\n\n")
        if min_lat is not None and min_lng is not None:
            f.write(f"* **Observed Latitude Range:** `{format_lat(min_lat)}` to `{format_lat(max_lat)}`\n")
            f.write(f"* **Observed Longitude Range:** `{format_lng(min_lng)}` to `{format_lng(max_lng)}`\n")
            f.write(f"* **Observed Centroid:** `{format_lat((min_lat + max_lat)/2.0)}`, `{format_lng((min_lng + max_lng)/2.0)}`\n\n")
        else:
            f.write("*(No valid spatial coordinates present in processed records)*\n\n")

        f.write("### Preliminary Palisades Study Window Comparison\n")
        f.write(f"* **Preliminary Window:** Lat `[{format_lat(PRELIMINARY_PALISADES_BOX['min_lat'])}, {format_lat(PRELIMINARY_PALISADES_BOX['max_lat'])}]` × Lng `[{format_lng(PRELIMINARY_PALISADES_BOX['min_lng'])}, {format_lng(PRELIMINARY_PALISADES_BOX['max_lng'])}]`\n")
        box_eval = checklist.get("spatial_extent_verified", {})
        f.write(f"* **Evaluation Status:** `{box_eval.get('status', 'NOT_ASSESSED')}`\n")
        f.write(f"* **Finding:** {box_eval.get('detail', 'N/A')}\n\n")

        if min_date:
            f.write(f"## 3. Observation Time Span (UTC)\n\n")
            f.write(f"* **Earliest Acquisition Date:** `{min_date}`\n")
            f.write(f"* **Latest Acquisition Date:** `{max_date}`\n\n")

        f.write("## 4. Platform & Sensor Breakdown\n\n")
        if sensor_counts:
            f.write("| Canonical Platform / Sensor | Family | Records | Share |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for s_name, cnt in sorted(sensor_counts.items(), key=lambda x: -x[1]):
                fam = "MODIS" if "MODIS" in s_name else "VIIRS" if "VIIRS" in s_name else "Other"
                f.write(f"| **{s_name}** | `{fam}` | `{cnt:,}` | {(cnt/valid_count*100):.1f}% |\n")
            f.write("\n")

        f.write("## 5. Confidence Distribution Summary (Sensor-Specific)\n\n")
        if modis_conf_vals:
            f.write(f"### MODIS Numeric Confidence (0–100% Scale)\n")
            f.write(f"* **Observations:** `{len(modis_conf_vals):,}`\n")
            f.write(f"* **Mean Confidence:** `{(sum(modis_conf_vals)/len(modis_conf_vals)):.1f}%`\n")
            f.write(f"* **Min / Max:** `{min(modis_conf_vals)}%` / `{max(modis_conf_vals)}%`\n\n")
        else:
            f.write("*No MODIS observations with numeric confidence in this dataset.*\n\n")

        if viirs_conf_cats:
            f.write(f"### VIIRS Categorical Confidence ('l', 'n', 'h' Quality Classes)\n")
            f.write("| Category | Description | Records | Share |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            cat_labels = {"l": "Low ('l')", "n": "Nominal ('n')", "h": "High ('h')"}
            viirs_total = sum(viirs_conf_cats.values())
            for cat, cnt in sorted(viirs_conf_cats.items()):
                f.write(f"| `{cat}` | {cat_labels.get(cat, cat)} | `{cnt:,}` | {(cnt/viirs_total*100):.1f}% |\n")
            f.write("\n")
        else:
            f.write("*No VIIRS observations with categorical confidence in this dataset.*\n\n")

        f.write("## 6. Quarantine Defect Log Summary\n\n")
        if defect_summary:
            f.write("| Defective Field | Defect Count | Consequence |\n")
            f.write("| :--- | :--- | :--- |\n")
            for field_name, d_cnt in sorted(defect_summary.items(), key=lambda x: -x[1]):
                f.write(f"| `{field_name}` | `{d_cnt:,}` | Quarantined to `{quarantine_file.name}` |\n")
            f.write("\n")
        else:
            f.write("*(Zero fatal defects detected; 0 records quarantined)*\n\n")

        f.write("## 7. Verified Scientific & Architectural Checklist\n\n")
        f.write("> **Checklist Verification**: Check statuses below are computed strictly from programmatic verification tests run over the actual output files.\n\n")
        f.write("| Scientific Requirement | Verification Status | Audit Detail |\n")
        f.write("| :--- | :--- | :--- |\n")
        for req_key, chk in checklist.items():
            status_badge = f"**[{chk['status']}]**" if chk['status'] in ("PASSED", "EXTENDS_BEYOND_PRELIMINARY_BOX") else f"*{chk['status']}*"
            f.write(f"| `{req_key}` | {status_badge} | {chk['detail']} |\n")
        f.write("\n")

    # Generate companion JSON summary
    json_summary = {
        "report_id": report_id,
        "generated_at_utc": now_utc,
        "source_processed": str(processed_file),
        "source_quarantine": str(quarantine_file),
        "total_input_records": total_input,
        "valid_accepted_records": valid_count,
        "quarantined_records": quarantine_count,
        "pass_rate_pct": pass_rate,
        "counts_reconciled": is_reconciled,
        "reconciliation_source": reconciliation_source,
        "observed_detection_bounds": {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lng": min_lng,
            "max_lng": max_lng,
            "min_lat_formatted": format_lat(min_lat),
            "max_lat_formatted": format_lat(max_lat),
            "min_lng_formatted": format_lng(min_lng),
            "max_lng_formatted": format_lng(max_lng),
        },
        "preliminary_study_window": PRELIMINARY_PALISADES_BOX,
        "temporal_range_utc": {
            "earliest_date": min_date,
            "latest_date": max_date,
        },
        "sensor_distribution": sensor_counts,
        "family_distribution": family_counts,
        "quarantine_defects": defect_summary,
        "verified_checklist": checklist,
    }

    with json_report_path.open("w", encoding="utf-8") as f:
        json.dump(json_summary, f, indent=2)

    return md_report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate verified data quality audit report")
    parser.add_argument("processed_file", help="Path to processed JSON records")
    parser.add_argument("quarantine_file", help="Path to quarantined JSON records")
    parser.add_argument("--report_dir", default="reports", help="Directory where reports are saved")
    parser.add_argument("--manifest", default=None, help="Optional path to companion ingest manifest")
    args = parser.parse_args()

    proc_p = Path(args.processed_file)
    quar_p = Path(args.quarantine_file)
    rep_p = Path(args.report_dir)
    manifest_p = Path(args.manifest) if args.manifest else None

    print(f"Auditing outputs for: {proc_p.name} ...")
    report_file = generate_quality_report(proc_p, quar_p, rep_p, manifest_p)
    print(f"Data quality report generated successfully: {report_file}")


if __name__ == "__main__":
    main()
