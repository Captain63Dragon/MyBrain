import os
import re
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, Tuple


def _extract_date_from_string(s: str) -> Optional[Tuple[datetime, int, int]]:
    """Try several filename date patterns and return a datetime.date if found.
    This is aware of format but doesn't care about location. Cannonically it will be at the start of the filename if I created it but other file sources often use something like a date.
    Note this is not a deep dive. What is generate if 14901002 is found? Not likely year=1490! """
    # Patterns: 2026_0101, 20260101, 2026-01-01
    patterns = [
        r"(\d{4})_(\d{2})(\d{2})",
        r"(\d{4})(\d{2})(\d{2})",
        r"(\d{4})-(\d{2})-(\d{2})",
    ]

    for pat in patterns:
        m = re.search(pat, s)
        if m:
            try:
                year, month, day = m.groups()
                dt = datetime(int(year), int (month), int(day))
                # check year range against hard coded min/max for my files
                if not (1981 <= dt.year <= 2050): # Future me curses me!
                    continue
                return (dt, m.start(), m.end())
            except (ValueError, OverflowError):
                continue

    return None


def _extract_suffix_from_stem(stem: str) -> str:
    """Extract trailing suffix like _001 from a filename stem. Returns empty string if none.
    Note: stem does not include path(?) or extension.
    """
    m = re.search(r"(_\d{1,})$", stem)
    return m.group(1) if m else ""


def _sanitize_id_part(s: str) -> str:
    """Make an ID-safe string: lowercase, replace spaces with underscores, remove unsafe chars."""
    # save = s
    s = s.strip().lower()
    s = s.replace(' ', '_')
    s = re.sub(r"[^a-z0-9_\-]", '', s)
    # print (f"Sanitize: str [{save}], sanitized [{s}]")
    return s


def suggest_file_node_id(filepath: str,
        verify_node_uniqueness: Callable[[str], bool],
        max_attempts: int = 100,
        raise_on_missing: bool = True) -> Optional[str]:
    """
    Propose a FILE-NODE id for `filepath` and ensure uniqueness.

    Strategy:
    - Prefer a date extracted from the filename (patterns like 2026_0101 or 20260101).
    - If no date in filename, use filesystem modified time (mtime). If mtime equals ctime
      the creation time may be used (on some platforms ctime==mtime).
    - Preserve a trailing numeric suffix from the filename (e.g. `_001`).
    - Include a sanitized short form of the name (filename without date/suffix) if present.
    - Call `verify_node_uniqueness(proposed_id)`; if it's not unique, append an increment
      (`_1`, `_2`, ...) until unique or `max_attempts` is reached.

    Args:
        filepath: path to the file to generate an id for.
        verify_node_uniqueness: callable that returns True when the proposed id is unique/available.
        max_attempts: maximum numeric suffix attempts to find a unique id.

    Returns:
        A unique id string.

    Raises:
        RuntimeError: if a unique id could not be found within `max_attempts`.
    """
    p = Path(filepath)
    # Fail early if file does not exist
    if not p.exists():
        if raise_on_missing:
            raise FileNotFoundError(f"File not found: {filepath}")
        return None

    stem = p.stem

    # First try to extract date from within the filename
    result = _extract_date_from_string(stem) # will be None if not found.
        
    # is there a cannonical _001 before the extension? 
    # Note: will also match _something or _0000001, .. it isn't fussy.
    suffix = _extract_suffix_from_stem(stem)
    if suffix:
        core = stem[: -len(suffix)]
    else:
        core = stem

    # 2) If no date found, fall back to filesystem timestamps
    if result is None:
        try:
            mtime = os.path.getmtime(filepath)
            ctime = os.path.getctime(filepath)
            # prefer modified time; keep as datetime.date
            chosen = mtime if mtime else ctime
            dt = datetime.fromtimestamp(chosen)
        except Exception:
            # timestamps failed despite file existing — re-raise
            raise
    else: # this safely removes the date ish string found.
        dt, start, end = result
        bdate = core[:start].rstrip('-_')
        adate = core[end:].lstrip('-_')
        if bdate and adate:
            core = f"{bdate}-{adate}" # and clears out '--' or '-_' etc.
        else:
            # we don't care which is empty string. Order preserved.
            core = bdate + adate

    # populate the date part, whereever it came from
    date_part = dt.strftime("%Y%m%d")

    core = core.strip('-_')
    core_sanitized = _sanitize_id_part(core) if core else ''

    # Build base proposed id
    parts = []
    if core_sanitized:
        parts.append(core_sanitized)
    if suffix:
        parts.append(suffix.lstrip('_'))
    parts.append(date_part)
    proposed = '_'.join(parts)

    # Ensure uniqueness by asking the provided verifier
    if verify_node_uniqueness(proposed):
        return proposed

    # Not unique -> try appending incremental counter
    for i in range(1, max_attempts + 1):
        candidate = f"{proposed}_{i}"
        if verify_node_uniqueness(candidate):
            return candidate

    raise RuntimeError(f"Could not find unique id for '{filepath}' after {max_attempts} attempts")

def verify_meta_path(self, meta_path):
    """Verify meta path exists and has read/write access"""
    if not meta_path:
        return False, "Meta path is null"
    
    path = Path(meta_path)
    
    if not path.exists():
        return False, f"Path does not exist: {meta_path}"
    
    if not path.is_dir():
        return False, f"Path is not a directory: {meta_path}"
    
    # Check read access
    if not os.access(path, os.R_OK):
        return False, f"No read access: {meta_path}"
    
    # Check write access
    if not os.access(path, os.W_OK):
        return False, f"No write access: {meta_path}"
        
    return True, f"Valid meta path: {meta_path}"

def verify_file_in_meta_path(self, file_path, meta_path):
    """Verify file exists within the meta path"""
    if not file_path:
        return False, "File path is null"
    if not meta_path:
        return False, "Meta path is null - cannot verify file location"
    file = Path(file_path)
    meta = Path(meta_path)
    
    # Check if file exists
    if not file.exists():
        return False, f"File does not exist: {file_path}"
    
    # Check if file is within meta path
    try:
        file.resolve().relative_to(meta.resolve())
        return True, f"File exists in meta path: {file_path}"
    except ValueError:
        return False, f"File is not in meta path: {file_path} not in {meta_path}"

