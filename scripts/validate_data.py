"""
FireTrace Pilot Pipeline - Preliminary Data Validation Tool
Implements robust validation for coordinates, timestamps, pixel dimensions, FRP, and missing values.
Strictly distinguishes between fatal defects (quarantine) and valid records with optional missing fields.
Rejects NaN and +/-Inf. Preserves original raw values without forced defaults.
Documented UTC acquisition time assumption per NASA FIRMS specification.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    parsed_lat: Optional[float] = None
    parsed_lng: Optional[float] = None
    parsed_iso_timestamp: Optional[str] = None
    parsed_scan: Optional[float] = None
    parsed_track: Optional[float] = None
    parsed_frp: Optional[float] = None
    scan_track_available: bool = False


def is_invalid_numeric_str(val_str: str) -> bool:
    """Checks for NaN and Infinity strings that float() would otherwise parse."""
    val_clean = val_str.strip().lower()
    return val_clean in ("nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity")


def validate_coordinates(
    lat_val: Any, lng_val: Any
) -> Tuple[bool, Optional[float], Optional[float], Optional[str]]:
    """
    Validates WGS-84 latitude and longitude coordinates.
    Rejects NaN, +Inf, -Inf, missing values, and out-of-range floats.
    Preserves exact floating-point precision without rounding.
    """
    if lat_val is None or str(lat_val).strip() == "":
        return False, None, None, "Missing latitude coordinate"
    if lng_val is None or str(lng_val).strip() == "":
        return False, None, None, "Missing longitude coordinate"

    str_lat = str(lat_val).strip()
    str_lng = str(lng_val).strip()

    if is_invalid_numeric_str(str_lat) or is_invalid_numeric_str(str_lng):
        return False, None, None, f"Coordinates contain NaN or Infinity: lat='{lat_val}', lng='{lng_val}'"

    try:
        lat = float(str_lat)
        lng = float(str_lng)
    except (ValueError, TypeError):
        return False, None, None, f"Non-numeric coordinates: lat='{lat_val}', lng='{lng_val}'"

    if math.isnan(lat) or math.isinf(lat) or math.isnan(lng) or math.isinf(lng):
        return False, None, None, f"Coordinates resolved to NaN or Infinity: lat={lat}, lng={lng}"

    if not (-90.0 <= lat <= 90.0):
        return False, lat, lng, f"Latitude {lat} out of valid geographic range [-90.0, 90.0]"
    if not (-180.0 <= lng <= 180.0):
        return False, lat, lng, f"Longitude {lng} out of valid geographic range [-180.0, 180.0]"

    return True, lat, lng, None


def validate_timestamp(
    date_str: Any, time_str: Any
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates acquisition date (YYYY-MM-DD) and military time (HHMM).
    NASA FIRMS active fire products report acq_time strictly in UTC.
    Constructs an ISO-8601 UTC timestamp string with documented UTC assumption.
    Does not assume or apply local timezone conversions.
    """
    if not date_str or str(date_str).strip() == "":
        return False, None, "Missing acq_date"
    if time_str is None or str(time_str).strip() == "":
        return False, None, "Missing acq_time"

    clean_date = str(date_str).strip()
    raw_time = str(time_str).strip()

      # NASA FIRMS military time must contain exactly 3 or 4 digits.
    if not raw_time.isdigit() or len(raw_time) not in (3, 4):
        return False, None, (
            f"Malformed military acq_time: '{raw_time}'. "
            "Expected 3 or 4 numeric digits."
        )

    clean_time = raw_time.zfill(4)

    try:
        datetime.strptime(clean_date, "%Y-%m-%d")
    except ValueError:
        return False, None, f"Invalid date format: '{clean_date}' (expected YYYY-MM-DD)"

    try:
        hour = int(clean_time[:2])
        minute = int(clean_time[2:])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return False, None, f"Invalid military time: '{clean_time}' (hour 0-23, min 0-59)"
    except (ValueError, IndexError):
        return False, None, f"Unparseable military time: '{clean_time}'"

    # Per NASA FIRMS documentation, acq_time is recorded in UTC.
    iso_timestamp = f"{clean_date}T{hour:02d}:{minute:02d}:00Z"
    return True, iso_timestamp, None


def validate_datetime_utc(value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates an ISO-8601 timestamp with an explicit timezone.
    Normalizes the timestamp to UTC without modifying the raw input.
    """
    if value is None or str(value).strip() == "":
        return False, None, "Missing datetime_utc"

    raw_value = str(value).strip()

    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return False, None, "datetime_utc must include an explicit timezone"

        utc_timestamp = parsed.astimezone(timezone.utc)
        normalized = utc_timestamp.isoformat().replace("+00:00", "Z")

        return True, normalized, None

    except ValueError:
        return False, None, f"Invalid ISO-8601 datetime_utc: '{raw_value}'"

def validate_pixel_dimensions(
    scan_val: Any, track_val: Any
) -> Tuple[bool, Optional[float], Optional[float], Optional[str], bool]:
    """
    Validates pixel ground dimensions in kilometers (scan and track).
    Returns: (is_valid, parsed_scan, parsed_track, error_message, is_available)

    Missing scan/track fields are treated as unavailable, not invalid. Any
    populated field must still contain a finite, positive numeric value.
    Rejects NaN, +Inf, -Inf, non-numeric, negative, and zero values.
    Preserves exact floating-point values without rounding.
    """
    scan_populated = scan_val is not None and str(scan_val).strip() != ""
    track_populated = track_val is not None and str(track_val).strip() != ""
    scan: Optional[float] = None
    track: Optional[float] = None

    for name, value, populated in (
        ("scan", scan_val, scan_populated),
        ("track", track_val, track_populated),
    ):
        if not populated:
            continue

        value_str = str(value).strip()
        if is_invalid_numeric_str(value_str):
            return False, scan, track, f"{name} dimension contains NaN or Inf: '{value}'", scan_populated and track_populated

        try:
            parsed_value = float(value_str)
        except (ValueError, TypeError):
            return False, scan, track, f"Non-numeric {name} dimension: '{value}'", scan_populated and track_populated

        if math.isnan(parsed_value) or math.isinf(parsed_value):
            return False, scan, track, f"{name} dimension resolved to NaN or Inf: {parsed_value}", scan_populated and track_populated
        if parsed_value <= 0.0:
            return False, scan, track, f"Non-positive {name} ground dimension: {parsed_value} km", scan_populated and track_populated

        if name == "scan":
            scan = parsed_value
        else:
            track = parsed_value

    return True, scan, track, None, scan_populated and track_populated


def validate_frp(frp_val: Any) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validates Fire Radiative Power (MW).
    Rejects NaN, +Inf, -Inf, and negative values.
    Returns (True, None, None) if unpopulated (optional in some provisional products).
    """
    if frp_val is None or str(frp_val).strip() == "":
        return True, None, None

    str_frp = str(frp_val).strip()
    if is_invalid_numeric_str(str_frp):
        return False, None, f"FRP contains NaN or Infinity: '{frp_val}'"

    try:
        frp = float(str_frp)
    except (ValueError, TypeError):
        return False, None, f"Non-numeric FRP value: '{frp_val}'"

    if math.isnan(frp) or math.isinf(frp):
        return False, None, f"FRP resolved to NaN or Infinity: {frp}"

    if frp < 0.0:
        return False, frp, f"Negative FRP value: {frp} MW"

    return True, frp, None


def validate_raw_record(record: Dict[str, Any]) -> RecordValidationResult:
    """
    Comprehensive record validator that:
    1. Distinguishes fatal defects (quarantine) from non-fatal warnings (accepted).
    2. Strictly validates coordinates and timestamps.
    3. Rejects NaN, Inf, and negative FRP.
    4. Handles scan/track without assuming fixed values.
    5. Preserves all raw values.
    """
    issues: List[ValidationIssue] = []

    # 1. Coordinates Validation (FATAL if invalid)
    lat_key = next((k for k in record if k.lower() in ("latitude", "lat")), None)
    lng_key = next((k for k in record if k.lower() in ("longitude", "lng", "lon")), None)
    raw_lat = record.get(lat_key) if lat_key else None
    raw_lng = record.get(lng_key) if lng_key else None

    lat_valid, parsed_lat, parsed_lng, lat_err = validate_coordinates(raw_lat, raw_lng)
    if not lat_valid:
        issues.append(
            ValidationIssue(
                field="coordinates",
                issue_type="FATAL",
                message=lat_err or "Invalid coordinates",
                raw_value={"latitude": raw_lat, "longitude": raw_lng},
            )
        )
    # 2. Timestamp Validation (FATAL if invalid)
    datetime_key = next(
        (k for k in record if k.lower() == "datetime_utc"),
        None,
    )

    if datetime_key:
        raw_datetime = record.get(datetime_key)
        time_valid, parsed_iso_ts, time_err = validate_datetime_utc(
            raw_datetime
        )
        timestamp_raw = {"datetime_utc": raw_datetime}
    else:
        date_key = next(
            (k for k in record if k.lower() in ("acq_date", "date")),
            None,
        )
        time_key = next(
            (k for k in record if k.lower() in ("acq_time", "time")),
            None,
        )

        raw_date = record.get(date_key) if date_key else None
        raw_time = record.get(time_key) if time_key else None

        time_valid, parsed_iso_ts, time_err = validate_timestamp(
            raw_date, raw_time
        )
        timestamp_raw = {
            "acq_date": raw_date,
            "acq_time": raw_time,
        }

    if not time_valid:
        issues.append(
            ValidationIssue(
                field="timestamp",
                issue_type="FATAL",
                message=time_err or "Invalid timestamp",
                raw_value=timestamp_raw,
            )
        )

    # 3. Pixel Ground Dimensions Validation (FATAL if present but corrupt/negative; WARNING if absent)
    scan_key = next((k for k in record if k.lower() == "scan"), None)
    track_key = next((k for k in record if k.lower() == "track"), None)
    raw_scan = record.get(scan_key) if scan_key else None
    raw_track = record.get(track_key) if track_key else None

    dim_valid, parsed_scan, parsed_track, dim_err, dims_available = validate_pixel_dimensions(raw_scan, raw_track)
    if not dim_valid:
        issues.append(
            ValidationIssue(
                field="scan/track",
                issue_type="FATAL",
                message=dim_err or "Invalid pixel ground dimensions",
                raw_value={"scan": raw_scan, "track": raw_track},
            )
        )
    elif not dims_available:
        issues.append(
            ValidationIssue(
                field="scan/track",
                issue_type="WARNING",
                message="Pixel ground dimensions (scan/track) are not available in this record",
                raw_value={"scan": raw_scan, "track": raw_track},
            )
        )
    # 4. Fire Radiative Power Validation (FATAL if negative or NaN; WARNING if unpopulated)
    frp_key = next((k for k in record if k.lower() == "frp"), None)
    raw_frp = record.get(frp_key) if frp_key else None
    frp_valid, parsed_frp, frp_err = validate_frp(raw_frp)
    if not frp_valid:
        issues.append(
            ValidationIssue(
                field="frp",
                issue_type="FATAL",
                message=frp_err or "Invalid FRP",
                raw_value=raw_frp,
            )
        )
    elif parsed_frp is None:
        issues.append(
            ValidationIssue(
                field="frp",
                issue_type="WARNING",
                message="FRP is unpopulated in this record",
                raw_value=raw_frp,
            )
        )

    # 5. Non-critical optional fields (WARNING only)
    type_key = next((k for k in record if k.lower() == "type"), None)
    if not type_key or record.get(type_key) in (None, ""):
        issues.append(
            ValidationIssue(
                field="type",
                issue_type="WARNING",
                message="Optional 'type' field is unpopulated",
                raw_value=record.get(type_key),
            )
        )

    daynight_key = next((k for k in record if k.lower() in ("daynight", "day_night")), None)
    raw_dn = record.get(daynight_key) if daynight_key else None
    if raw_dn and str(raw_dn).strip().upper() not in ("D", "N"):
        issues.append(
            ValidationIssue(
                field="daynight",
                issue_type="WARNING",
                message=f"Non-standard daynight code: '{raw_dn}'",
                raw_value=raw_dn,
            )
        )

    has_fatal = any(issue.issue_type == "FATAL" for issue in issues)
    return RecordValidationResult(
        is_valid=not has_fatal,
        is_fatal=has_fatal,
        issues=issues,
        parsed_lat=parsed_lat,
        parsed_lng=parsed_lng,
        parsed_iso_timestamp=parsed_iso_ts,
        parsed_scan=parsed_scan,
        parsed_track=parsed_track,
        parsed_frp=parsed_frp,
        scan_track_available=dims_available,
    )


def compute_dataset_spatial_bounds(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes observed min/max spatial coordinates for boundary extent verification.
    Rejects NaN and Inf values during bounds computation.
    """
    lats: List[float] = []
    lngs: List[float] = []

    for r in records:
        lat_k = next((k for k in r if k.lower() in ("latitude", "lat")), None)
        lng_k = next((k for k in r if k.lower() in ("longitude", "lng", "lon")), None)
        if lat_k and lng_k:
            valid, lat, lng, _ = validate_coordinates(r[lat_k], r[lng_k])
            if valid and lat is not None and lng is not None:
                lats.append(lat)
                lngs.append(lng)

    if not lats or not lngs:
        return {
            "has_spatial_data": False,
            "min_lat": None,
            "max_lat": None,
            "min_lng": None,
            "max_lng": None,
        }

    return {
        "has_spatial_data": True,
        "record_count_with_coords": len(lats),
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lng": min(lngs),
        "max_lng": max(lngs),
        "center_lat": (min(lats) + max(lats)) / 2.0,
        "center_lng": (min(lngs) + max(lngs)) / 2.0,
        "center_definition": "bounding_box_midpoint",
    }
