"""
mfi_service.py — Meta File Instruction messaging layer.

Shared by both the Flask/container side and the Windows host scripts.
Zero framework dependencies — stdlib and yaml only.

Folder convention (set via MFI_PATH environment variable):
    pending/      UI out-box,     Windows in-box
    processing/   atomic lock,    work in progress
    completed/    Windows out-box, UI in-box

File convention:
    *.mft  — being written, ignored by both sides
    *.mfi  — complete, ready to process
    
Filename prefix determines action type:
    discovery_YYYYMMDD_NNN.mfi
    move_YYYYMMDD_NNN.mfi
    archive_YYYYMMDD_NNN.mfi
"""

import os
import re
import yaml
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Path resolution — works on both sides of the divide
# ---------------------------------------------------------------------------

def get_mfi_root() -> Path:
    """
    Resolve MFI root from environment.
    Inside container: /mfi (mounted volume)
    Windows host:     C:/Users/termi/MetaFileQueues (from .env)
    """
    path = os.environ.get('MFI_PATH')
    if not path:
        raise EnvironmentError("MFI_PATH environment variable not set")
    return Path(path)


def pending_path() -> Path:
    return get_mfi_root() / 'pending'

def processing_path() -> Path:
    return get_mfi_root() / 'processing'

def completed_path() -> Path:
    return get_mfi_root() / 'completed'


# ---------------------------------------------------------------------------
# Base and action-specific dataclasses — data only, no logic
# ---------------------------------------------------------------------------

@dataclass
class MFIBase:
    """Fields common to every MFI regardless of action type."""
    mfi_id:   str = ""
    action:   str = ""
    created:  str = ""
    status:   str = "pending"


@dataclass
class DiscoveryMFI(MFIBase):
    """Instruction to scan a directory for files matching an MFN pattern."""
    action:   str = "scan_directory"
    mfn_id:   str = ""
    source:   str = ""
    patterns: list = field(default_factory=list)  # e.g. ['busCard', 'BusCard', 'busCardish']
    
@dataclass
class DiscoveryResultMFI(MFIBase):
    """Result of a directory scan — one entry per matched file."""
    action:        str = "scan_directory_result"
    source_mfi_id: str = ""
    mfn_id:        str = ""
    files:         list = field(default_factory=list)
    # each file: {filepath, date, mask_matched, descriptor}

@dataclass
class CopyMFI(MFIBase):
    action:   str = "copy"
    source:   str = ""
    target:   str = ""
    node_id:  str = ""
    mfn_id:   str = ""
    intent:   str = ""  # 'insitu_copy', 'copy'

@dataclass
class CopyResultMFI(MFIBase):
    action:        str = "copy_result"
    source_mfi_id: str = ""
    node_id:       str = ""
    mfn_id:        str = ""
    source:        str = ""
    target:        str = ""
    intent:        str = ""
    success:       bool = False
    error:         str = ""

@dataclass
class MoveMFI(MFIBase):
    """Instruction to move a file from source to target."""
    action:   str = "move"
    mfn_id:   str = ""
    source:   str = ""
    target:   str = ""
    node_id:  str = ""
    intent:   str = ""  # 'move', 'archive'

@dataclass
class MoveResultMFI(MFIBase):
    """Result of a move operation."""
    action:        str = "move_result"
    source_mfi_id: str = ""
    mfn_id:        str = ""
    node_id:       str = ""
    source:        str = ""
    target:        str = ""
    intent:        str = ""
    success:       bool = False
    error:         str = ""
    
# ---------------------------------------------------------------------------
# Registry — prefix to class mapping, extend here for new action types
# ---------------------------------------------------------------------------

ACTION_REGISTRY = {
    'scan_directory':        DiscoveryMFI,
    'scan_directory_result': DiscoveryResultMFI,
    'move':                  MoveMFI,
    'move_result':           MoveResultMFI,
    'copy':                  CopyMFI,
    'copy_result':           CopyResultMFI,
}    

# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def generate_mfi_id(action: str) -> str:
    """
    Generate a unique filename stem for an MFI file.
    Format: action_YYYY_MMDD_HHMMSS_ffffff
    Microsecond precision makes collision probability negligible.
    """
    timestamp = datetime.now().strftime("%Y_%m%d_%H%M%S_%f")
    return f"{action}_{timestamp}"

# ---------------------------------------------------------------------------
# Encode / decode — outside the classes, operate on them
# ---------------------------------------------------------------------------

def encode(mfi: MFIBase) -> str:
    """Serialize an MFI dataclass to a YAML string."""
    return yaml.dump(asdict(mfi), default_flow_style=False, allow_unicode=True)


def decode(filepath: str) -> MFIBase:
    """
    Read an .mfi file and deserialize to the appropriate MFI dataclass.
    Routes by filename prefix via ACTION_REGISTRY.
    """
    p = Path(filepath)
    # Strip the timestamp suffix — everything before _YYYY is the action name
    stem = p.stem
    # Find where the date starts: _YYYY pattern
    match = re.search(r'_\d{4}_', stem)
    action = stem[:match.start()].lower() if match else stem.lower()

    cls = ACTION_REGISTRY.get(action)
    if not cls:
        raise ValueError(f"Unknown MFI action '{action}' in file: {filepath}")

    with open(p, 'r') as f:
        data = yaml.safe_load(f)

    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# File operations — atomic write, folder transitions
# ---------------------------------------------------------------------------

def write_mfi(mfi: MFIBase, folder: Optional[Path] = None) -> Path:
    """
    Write an MFI to the pending folder atomically.
    Writes as .mft first, renames to .mfi — both sides ignore .mft.
    Returns the final .mfi path.
    """
    if folder is None:
        folder = pending_path()

    folder.mkdir(parents=True, exist_ok=True)

    if not mfi.mfi_id:
        mfi.mfi_id = generate_mfi_id(mfi.action)
    if not mfi.created:
        mfi.created = datetime.now().isoformat()

    tmp_path  = folder / f"{mfi.mfi_id}.mft"
    final_path = folder / f"{mfi.mfi_id}.mfi"

    tmp_path.write_text(encode(mfi), encoding='utf-8')
    tmp_path.rename(final_path)  # atomic on same filesystem

    return final_path


def read_pending() -> list[Path]:
    """Return all .mfi files in pending/, oldest first. Ignores .mft."""
    folder = pending_path()
    if not folder.exists():
        return []
    return sorted(folder.glob('*.mfi'))


def move_to_processing(filepath: Path) -> Path:
    """Atomically claim an .mfi file by moving it to processing/."""
    dest = processing_path() / filepath.name
    processing_path().mkdir(parents=True, exist_ok=True)
    filepath.rename(dest)
    return dest


def move_to_completed(filepath: Path) -> Path:
    """Move a processed .mfi file to completed/."""
    dest = completed_path() / filepath.name
    completed_path().mkdir(parents=True, exist_ok=True)
    filepath.rename(dest)
    return dest


def mark_failed(filepath: Path) -> Path:
    """Rename file with .failed extension in processing/ for inspection."""
    dest = filepath.with_suffix('.failed')
    filepath.rename(dest)
    return dest