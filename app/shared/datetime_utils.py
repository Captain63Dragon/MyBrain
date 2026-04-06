# app/shared/datetime_utils.py
"""
Datetime conversion utilities.

Architecture:
    Source (any format Vera/LLM might produce)
        → _parse_any()  →  Python datetime (UTC-aware)
        → to_*(dt)      →  target format string

Internal parser (_parse_any) does the heavy lifting once.
Named converters handle specific target systems.

Source formats handled:
    - ISO 8601 + Z suffix          "2026-03-27T22:02:20Z"
    - ISO 8601 + explicit offset   "2026-03-27T22:02:20+00:00"
    - ISO 8601 with milliseconds   "2026-03-27T22:02:20.000Z"
    - MDT / MST offsets            "2026-03-27T16:02:20-06:00"
    - Space separator              "2026-03-27 22:02:20"
    - Date only                    "2026-03-27"
    - Unix timestamp (int/float)   1743112940  or  1743112940.5
    - Human readable (via dateutil) "March 27, 2026"

Conversion targets:
    to_neo4j()   → ISO 8601 with explicit offset  (tested ✓)
    to_gcal()    → RFC 3339                        (NOT TESTED)
    to_display() → Human-readable local string     (NOT TESTED)
    to_python()  → Python datetime object          (NOT TESTED)

All public functions return None on failure — callers should handle gracefully.
"""

import re
from datetime import datetime, timezone

# ── Internal parser ───────────────────────────────────────────────────────────

def _parse_any(value) -> datetime | None:
    """
    Parse any timestamp Vera might produce into a UTC-aware Python datetime.
    Internal use only — call the to_*() converters instead.
    Returns None if unparseable.
    """
    if value is None:
        return None

    # Numeric unix timestamp
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None

    if not isinstance(value, str):
        return None

    s = value.strip()

    # Strip milliseconds/microseconds before offset or Z
    s = re.sub(r'(\d{2}:\d{2}:\d{2})\.\d+', r'\1', s)

    # Replace Z suffix with +00:00
    s = re.sub(r'Z$', '+00:00', s)

    # Replace space separator with T
    s = re.sub(r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', r'\1T\2', s)

    # Date only — append midnight UTC
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        s = s + 'T00:00:00+00:00'

    # Try Python's fromisoformat
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    # Fallback: dateutil (handles human-readable and ambiguous formats)
    try:
        from dateutil import parser as dateutil_parser
        dt = dateutil_parser.parse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    return None


def _offset_str(dt: datetime) -> str:
    """Format the UTC offset of a datetime as ±HH:MM."""
    offset = dt.utcoffset()
    total_seconds = int(offset.total_seconds())
    sign = '+' if total_seconds >= 0 else '-'
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f'{sign}{hours:02d}:{minutes:02d}'


# ── Conversion targets ────────────────────────────────────────────────────────

def to_neo4j(value) -> str | None:
    """
    Source: any format (see module docstring)
    Target: Neo4j datetime() compatible ISO 8601 with explicit offset
    Example: "2026-03-27T22:02:20+00:00"

    TESTED ✓ — Claude → Neo4j path verified 2026-04-03
    """
    dt = _parse_any(value)
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + _offset_str(dt)


def to_gcal(value) -> str | None:
    """
    Source: any format (see module docstring)
    Target: Google Calendar RFC 3339 format
    Example: "2026-03-27T22:02:20+00:00"

    NOT TESTED — RFC 3339 and Neo4j ISO formats are structurally identical
    but GCal may have additional requirements (e.g. timeZone field handling).
    Verify before relying on this in production.
    """
    dt = _parse_any(value)
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + _offset_str(dt)


def to_display(value, tz=None) -> str | None:
    """
    Source: any format (see module docstring)
    Target: Human-readable local string
    Example: "Wednesday, April 3, 2026 4:19 PM MDT"

    NOT TESTED — tz parameter handling and locale formatting unverified.
    tz: a datetime.timezone or pytz/zoneinfo timezone object; defaults to UTC.
    """
    dt = _parse_any(value)
    if dt is None:
        return None
    if tz:
        try:
            dt = dt.astimezone(tz)
        except Exception:
            pass
    return dt.strftime('%A, %B %-d, %Y %-I:%M %p %Z').strip()


def to_python(value) -> datetime | None:
    """
    Source: any format (see module docstring)
    Target: Python timezone-aware datetime object

    NOT TESTED — confirm tzinfo preservation for downstream consumers.
    """
    return _parse_any(value)
