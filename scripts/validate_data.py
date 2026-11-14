"""
FireTrace Pilot Pipeline - Preliminary Data Validation Tool
Implements validation checks for coordinates, timestamps, pixel dimensions, FRP, and missing values.
Distinguishes between fatal defects (quarantine) and valid records with optional missing fields.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationIssue:
    field: str
    issue_type: str  # "FATAL" or "WARNING"
    message: str
    raw_value: Any


@dataclass
class RecordValidationResult:
    is_valid: bool
    is_fatal: bool
    issues: List[ValidationIssue] = field(default_factory=list)


def validate_coordinates(lat_val: Any, lng_val: Any) -> Tuple[bool, Optional[float], Optional[float], Optional[str]]:
    """
    Validates WGS-84 latitude and longitude coordinates.
    Returns: (is_valid, parsed_lat, parsed_lng, error_message)
    """
    if lat_val is None or str(lat_val).strip() == "":
        return False, None, None, "Missing latitude"
    if lng_val is None or str(lng_val).strip() == "":
        return False, None, None, "Missing longitude"

    try:
        lat = float(lat_val)
        lng = float(lng_val)
    except (ValueError, TypeError):
        return False, None, None, f"Non-numeric coordinates: lat='{lat_val}', lng='{lng_val}'"

    if not (-90.0 <= lat <= 90.0):
        return False, lat, lng, f"Latitude {lat} out of range [-90.0, 90.0]"
    if not (-180.0 <= lng <= 180.0):
        return False, lat, lng, f"Longitude {lng} out of range [-180.0, 180.0]"

    return True, lat, lng, None


def validate_timestamp(date_str: Any, time_str: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates acquisition date (YYYY-MM-DD) and military time (HHMM).
    Returns: (is_valid, iso_utc_string, error_message)
    """
    if not date_str or str(date_str).strip() == "":
        return False, None, "Missing acq_date"
    if time_str is None or str(time_str).strip() == "":
        return False, None, "Missing acq_time"

    clean_date = str(date_str).strip()
    clean_time = str(time_str).strip().zfill(4)  # e.g., '425' -> '0425'

    try:
        # Validate date format YYYY-MM-DD
        dt_date = datetime.strptime(clean_date, "%Y-%m-%d")
    except ValueError:
        return False, None, f"Invalid date format: '{clean_date}' (expected YYYY-MM-DD)"

    try:
        hour = int(clean_time[:2])
        minute = int(clean_time[2:])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return False, None, f"Invalid military time: '{clean_time}' (hour 0-23, min 0-59)"
    except (ValueError, IndexError):
        return False, None, f"Unparseable military time: '{clean_time}'"

    iso_timestamp = f"{clean_date}T{str(hour).zfill(2)}:{str(minute).zfill(2)}:00Z"
    return True, iso_timestamp, None


def validate_pixel_dimensions(scan_val: Any, track_val: Any) -> Tuple[bool, Optional[float], Optional[float], Optional[str]]:
    """
    Validates pixel ground dimensions in kilometers.
    Scan and track must be positive, non-zero floats.
    Does NOT hardcode universal fixed sizes; accepts variable NASA algorithm outputs.
    """
    if scan_val is None or str(scan_val).strip() == "":
        return False, None, None, "Missing scan dimension"
    if track_val is None or str(track_val).strip() == "":
        return False, None, None, "Missing track dimension"

    try:
        scan = float(scan_val)
        track = float(track_val)
    except (ValueError, TypeError):
        return False, None, None, f"Non-numeric pixel dimensions: scan='{scan_val}', track='{track_val}'"

    if scan <= 0.0:
        return False, scan, track, f"Non-positive scan dimension: {scan}"
    if track <= 0.0:
        return False, scan, track, f"Non-positive track dimension: {track}"

    return True, scan, track, None


def validate_frp(frp_val: Any) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validates Fire Radiative Power (MW).
    Must be a non-negative float.
    """
    if frp_val is None or str(frp_val).strip() == "":
        # Some provisional records lack FRP; accepted as non-fatal missing
        return True, None, None

    try:
        frp = float(frp_val)
    except (ValueError, TypeError):
        return False, None, f"Non-numeric FRP value: '{frp_val}'"

    if frp < 0.0:
        return False, frp, f"Negative FRP value: {frp}"

    return True, frp, None


def validate_raw_record(record: Dict[str, Any]) -> RecordValidationResult:
    """
    Comprehensive record validator that distinguishes fatal defects from optional missing fields.
    """
    issues: List[ValidationIssue] = []

    # 1. Coordinate check (FATAL)
    lat_key = next((k for k in record if k.lower() in ("latitude", "lat")), None)
    lng_key = next((k for k in record if k.lower() in ("longitude", "lng", "lon")), None)

    lat_valid, _, _, lat_err = validate_coordinates(
        record.get(lat_key) if lat_key else None,
        record.get(lng_key) if lng_key else None,
    )
    if not lat_valid:
        issues.append(ValidationIssue(field="coordinates", issue_type="FATAL", message=lat_err or "Invalid coords", raw_value=(record.get(lat_key), record.get(lng_key))))

    # 2. Timestamp check (FATAL)
    date_key = next((k for k in record if k.lower() in ("acq_date", "date")), None)
    time_key = next((k for k in record if k.lower() in ("acq_time", "time")), None)

    time_valid, _, time_err = validate_timestamp(
        record.get(date_key) if date_key else None,
        record.get(time_key) if time_key else None,
    )
    if not time_valid:
        issues.append(ValidationIssue(field="timestamp", issue_type="FATAL", message=time_err or "Invalid timestamp", raw_value=(record.get(date_key), record.get(time_key))))

    # 3. Pixel dimensions check (FATAL)
    scan_key = next((k for k in record if k.lower() == "scan"), None)
    track_key = next((k for k in record if k.lower() == "track"), None)
    if scan_key and track_key:
        dim_valid, _, _, dim_err = validate_pixel_dimensions(record.get(scan_key), record.get(track_key))
        if not dim_valid:
            issues.append(ValidationIssue(field="scan/track", issue_type="FATAL", message=dim_err or "Invalid dimensions", raw_value=(record.get(scan_key), record.get(track_key))))

    # 4. FRP check (FATAL if negative; WARNING if unpopulated)
    frp_key = next((k for k in record if k.lower() == "frp"), None)
    if frp_key:
        frp_valid, _, frp_err = validate_frp(record.get(frp_key))
        if not frp_valid:
            issues.append(ValidationIssue(field="frp", issue_type="FATAL", message=frp_err or "Invalid FRP", raw_value=record.get(frp_key)))

    # 5. Non-critical optional fields (WARNING only, not fatal)
    type_key = next((k for k in record if k.lower() == "type"), None)
    if not type_key or record.get(type_key) in (None, ""):
        issues.append(ValidationIssue(field="type", issue_type="WARNING", message="Optional 'type' attribute is unpopulated", raw_value=record.get(type_key)))

    has_fatal = any(issue.issue_type == "FATAL" for issue in issues)
    return RecordValidationResult(
        is_valid=not has_fatal,
        is_fatal=has_fatal,
        issues=issues,
    )


def compute_dataset_spatial_bounds(records: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Computes min/max spatial coordinates for boundary verification.
    """
    lats: List[float] = []
    lngs: List[float] = []

    for r in records:
        lat_k = next((k for k in r if k.lower() in ("latitude", "lat")), None)
        lng_k = next((k for k in r if k.lower() in ("longitude", "lng", "lon")), None)
        if lat_k and lng_k:
            try:
                lats.append(float(r[lat_k]))
                lngs.append(float(r[lng_k]))
            except (ValueError, TypeError):
                continue

    if not lats or not lngs:
        return {}

    return {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lng": min(lngs),
        "max_lng": max(lngs),
        "center_lat": (min(lats) + max(lats)) / 2.0,
        "center_lng": (min(lngs) + max(lngs)) / 2.0,
    }
