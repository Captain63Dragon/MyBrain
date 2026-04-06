import os
import re
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, Tuple
from app.scripts.mfn_search_dir import MetaFileNodeSchema
from app.services.schema_service import load_mfn, parse_gfn, map_properties, get_src_folders
from app.shared.mfi_shared import DiscoveryMFI, write_mfi

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

def _is_unique_file_node_id(session, proposed_id: str) -> bool:
    result = session.run(
        "MATCH (n:FileNode {`FILE-NODE-id`: $id}) RETURN n",
        id=proposed_id
    )
    return result.single() is None

def suggest_secondary_id(base_id: str, checker: Callable[[str], bool], max_attempts: int = 100) -> str:
    """
    Generate a unique secondary node id from a base id.
    Format: base_id_second_01, _02, etc.
    """
    for i in range(1, max_attempts + 1):
        candidate = f"{base_id}_second_{i:02d}"
        if checker(candidate):
            return candidate
    raise ValueError(f"Could not generate unique secondary id from {base_id} after {max_attempts} attempts")


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

def suggest_file_node_id_from_result(filepath: str,
        verify_node_uniqueness: Callable[[str], bool],
        mtime: str,
        max_attempts: int = 100) -> str:
    """
    Propose a FILE-NODE id from a result MFI file entry.
    No filesystem access — uses mtime supplied by the Windows watcher.
    
    Args:
        filepath: Windows path from result MFI (not accessed, parsed only)
        verify_node_uniqueness: returns True when proposed id is available
        mtime: date string from watcher e.g. '2026_0227'
        max_attempts: maximum attempts to find unique id
    """
    from pathlib import PureWindowsPath
    stem = PureWindowsPath(filepath).stem

    result = _extract_date_from_string(stem)
    suffix = _extract_suffix_from_stem(stem)
    core = stem[:-len(suffix)] if suffix else stem

    if result is None:
        dt = datetime.strptime(mtime, "%Y_%m%d")
    else:
        dt, start, end = result
        bdate = core[:start].rstrip('-_')
        adate = core[end:].lstrip('-_')
        core = f"{bdate}-{adate}" if bdate and adate else bdate + adate

    date_part = dt.strftime("%Y%m%d")
    core = core.strip('-_')
    core_sanitized = _sanitize_id_part(core) if core else ''

    parts = []
    if core_sanitized:
        parts.append(core_sanitized)
    if suffix:
        parts.append(suffix.lstrip('_'))
    parts.append(date_part)
    proposed = '_'.join(parts)

    if verify_node_uniqueness(proposed):
        return proposed

    for i in range(1, max_attempts + 1):
        candidate = f"{proposed}_{i}"
        if verify_node_uniqueness(candidate):
            return candidate

    raise RuntimeError(f"Could not find unique id for '{filepath}' after {max_attempts} attempts")


def derive_file_node_id(filepath: str, mtime: str) -> str:
    """
    Derive the canonical FILE-NODE-id from a filepath.
    No uniqueness check — just generates the ID the file should have.
    """
    from pathlib import PureWindowsPath
    stem = PureWindowsPath(filepath).stem
    result = _extract_date_from_string(stem)
    suffix = _extract_suffix_from_stem(stem)
    core = stem[:-len(suffix)] if suffix else stem

    if result is None:
        dt = datetime.strptime(mtime, "%Y_%m%d")
    else:
        dt, start, end = result
        bdate = core[:start].rstrip('-_')
        adate = core[end:].lstrip('-_')
        core = f"{bdate}-{adate}" if bdate and adate else bdate + adate

    date_part = dt.strftime("%Y%m%d")
    core = core.strip('-_')
    core_sanitized = _sanitize_id_part(core) if core else ''

    parts = []
    if core_sanitized:
        parts.append(core_sanitized)
    if suffix:
        parts.append(suffix.lstrip('_'))
    parts.append(date_part)
    return '_'.join(parts)

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

def build_node_fields(metadata, mfn: dict) -> dict:
    """Build the flat property dict for a new FileNode."""
    fields = {
        'filepath':         metadata.filepath,
        'reviewed':         False,
        'review_priority':  mfn.get('review_priority', 5),
        'confidence_score': metadata.confidence_score,
        'pattern_matched':  metadata.pattern_matched,
    }
    for key in ('description', 'category', 'company', 'context_note'):
        val = getattr(metadata, key, '')
        if val:
            fields[key] = val
    return fields

def mfn_to_schema(mfn: dict) -> MetaFileNodeSchema:
    """Build a MetaFileNodeSchema from a live Neo4j MFN dict."""
    schema_dict = {
        'name':                  mfn.get('name', ''),
        'path':                  mfn.get('path', ''),
        'description':           mfn.get('description', ''),
        'purpose':               mfn.get('purpose', ''),
        'core_properties':       list(mfn.get('core_properties', {}).keys()),
        'optional_properties':   list(mfn.get('optional_properties', {}).keys()),
        'property_descriptions': {},
        'patterns':              json.dumps(mfn.get('patterns', [])),
        'user_review_required':  mfn.get('user_review_required', True),
        'relocatable':           mfn.get('relocatable', True),
        'review_priority':       mfn.get('review_priority', 5),
        'remove_source':         mfn.get('remove_source', {}),
        'category_inference':    mfn.get('category_inference', {}),
    }
    return MetaFileNodeSchema.from_yaml(yaml.dump(schema_dict))


def build_node_fields(metadata, mfn: dict) -> dict:
    """Build the flat property dict for a new FileNode."""
    fields = {
        'filepath':         metadata.filepath,
        'reviewed':         False,
        'review_priority':  mfn.get('review_priority', 5),
        'confidence_score': metadata.confidence_score,
        'pattern_matched':  metadata.pattern_matched,
    }
    for key in ('description', 'category', 'company', 'context_note'):
        val = getattr(metadata, key, '')
        if val:
            fields[key] = val
    return fields

def load_seed_folders(mfn_path):
    from app.services.neo4j_service import load_gfn_nodes
    import glob
    mfn_dir  = os.path.dirname(mfn_path)
    mfn_basename = os.path.basename(mfn_path)         
    type_key = mfn_basename[4:-5]    
    gfn_pattern = os.path.join(mfn_dir, f'GFN-{type_key}-*.yaml')
    gfn_path = glob.glob(gfn_pattern)
    if not gfn_path:
        raise FileNotFoundError(f"No GFN YAML found in {mfn_dir}")
    gfn_path = gfn_path[0]
    mfn    = load_mfn(mfn_path)
    nodes  = parse_gfn(gfn_path)
    # label  = mfn.get('name', 'Business Card').replace(' ', '') # fallback removed
    label = mfn.get('label')
    if not label:
        raise ValueError(f"MFN missing required 'label' field: {mfn_path}")
    mapped = [map_properties(mfn, n) for n in nodes]
    # DEBUG print(f"[debug] nodes: {len(nodes)}, mapped: {len(mapped)}")
    # if mapped:
    #     print(f"[debug] first mapped: {mapped[0]}")
    load_gfn_nodes(mfn, label, mapped)
    folders = get_src_folders(mapped)
    return folders, mfn


def dispatch_discovery(folder: str, mfn: dict) -> str:
    """
    Write a DiscoveryMFI to pending/ and create a Dispatch node.
    Returns mfi_id for SSE tracking.
    """
    from app.services.neo4j_service import create_dispatch_node
    mfn_id   = mfn.get('MFN-id', '')
    patterns = [p['pattern_value'] for p in json.loads(mfn.get('patterns', '[]'))
            if p.get('pattern_type') == 'filename_contains']
    mfi = DiscoveryMFI(mfn_id=mfn_id, source=folder, patterns=patterns)
    write_mfi(mfi)
    create_dispatch_node(mfi.mfi_id, mfi.action, mfn_id, folder)  # ⚠️ confirm signature
    return mfi.mfi_id


def manual_load(mfn_path) -> list[str]:
    """
    Load MFN + GFN into graph, dispatch a DiscoveryMFI per src_folder.
    Returns list of mfi_ids for the route to hand to the SSE stream.
    """
    folders, mfn = load_seed_folders(mfn_path)
    return [dispatch_discovery(folder, mfn) for folder in folders]