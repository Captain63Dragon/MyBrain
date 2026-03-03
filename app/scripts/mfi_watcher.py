"""
mfi_watcher.py — Windows-side MFI instruction processor.

Watches pending/ for .mfi files, claims them, executes actions,
writes results to completed/.

Usage:
    python -m app.scripts.mfi_watcher           # process all pending, exit
    python -m app.scripts.mfi_watcher --watch   # loop continuously

Zero container dependencies — stdlib, yaml, pathlib only.
"""

import re
import time
import argparse
from pathlib import Path
import shutil
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.shared.mfi_shared import (
    decode,
    encode,
    write_mfi,
    move_to_processing,
    move_to_completed,
    mark_failed,
    read_pending,
    DiscoveryMFI,
    DiscoveryResultMFI,
    CopyMFI,
    CopyResultMFI,
    MoveMFI, 
    MoveResultMFI,
)


def _make_result(cls, **kwargs):
    """Create a result dataclass with a `created` timestamp.

    Usage: _make_result(CopyResultMFI, source_mfi_id=..., status='failed', success=False)
    """
    payload = dict(kwargs)
    payload.setdefault('created', datetime.now().isoformat())
    return cls(**payload)


# ---------------------------------------------------------------------------
# Filename parsing — extract what the filename gives for free
# ---------------------------------------------------------------------------

def parse_filename(filename: str, mask_matched: str) -> dict:
    """
    Extract metadata from a matched filename.
    Returns date (YYYY_MMDD), mask_matched, and descriptor verbatim from filename.

    Example:
        2026_0202-busCard-postscript.pdf
        → date: '2026_0202', mask_matched: 'busCard', descriptor: 'postscript'
    """
    stem = Path(filename).stem

    # Extract date prefix YYYY_MMDD verbatim
    date_match = re.match(r'^(\d{4}_\d{4})-?', stem)
    date = date_match.group(1) if date_match else ''
    remainder = stem[date_match.end():] if date_match else stem

    # Remove the mask from remainder
    descriptor = re.sub(re.escape(mask_matched), '', remainder, flags=re.IGNORECASE)
    descriptor = descriptor.strip('-_')

    return {
        'date':         date,
        'mask_matched': mask_matched,
        'descriptor':   descriptor,
    }

def handle_copy(mfi: CopyMFI) -> CopyResultMFI:
    """
    Copy a file from source to target.
    Returns a CopyResultMFI with success/failure details.
    Intent is cargo — passed through for Flask result processor.
    """
    source = Path(mfi.source)
    target = Path(mfi.target)

    base = dict(
        source_mfi_id = mfi.mfi_id,
        node_id       = mfi.node_id,
        mfn_id        = mfi.mfn_id,
        source        = mfi.source,
        target        = mfi.target,
        intent        = mfi.intent,
    )

    if not source.exists():
        return _make_result(CopyResultMFI, **{**base, 'status': 'failed', 'success': False, 'error': f"Source file not found: {source}"})
    if target.exists():
        return _make_result(CopyResultMFI, **{**base, 'status': 'failed', 'success': False, 'error': f"Target already exists : {target}"})

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(target))
        return _make_result(CopyResultMFI, **{**base, 'status': 'completed', 'success': True})

    except Exception as e:
        return _make_result(CopyResultMFI, **{**base, 'status': 'failed', 'success': False, 'error': str(e)})

# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def handle_discovery(mfi: DiscoveryMFI) -> DiscoveryResultMFI:
    """
    Scan source directory for files matching any of the MFI patterns.
    Returns a DiscoveryResultMFI with one entry per matched file.
    """
    source = Path(mfi.source)
    patterns = mfi.patterns  # list of strings e.g. ['busCard', 'BusCard']

    if not source.exists():
        raise FileNotFoundError(f"Source directory not found: {source}")

    matched_files = []

    for filepath in source.iterdir():
        if not filepath.is_file():
            continue

        filename = filepath.name
        for mask in patterns:
            if mask in filename:
                entry = parse_filename(filename, mask)
                entry['filepath'] = str(filepath)
                entry['mtime'] = datetime.fromtimestamp(
                    filepath.stat().st_mtime
                ).strftime("%Y_%m%d")
                matched_files.append(entry)
                break  # first mask match wins

    return _make_result(DiscoveryResultMFI,
                        source_mfi_id = mfi.mfi_id,
                        mfn_id        = mfi.mfn_id,
                        status        = 'completed',
                        files         = matched_files)

def handle_move(mfi: MoveMFI) -> MoveResultMFI:
    """
    Move a file from source to target.
    Intent is cargo — passed through for Flask result processor.
    """
    source = Path(mfi.source)
    target = Path(mfi.target)

    base = dict(
        source_mfi_id = mfi.mfi_id,
        node_id       = mfi.node_id,
        mfn_id        = mfi.mfn_id,
        source        = mfi.source,
        target        = mfi.target,
        intent        = mfi.intent,
        created       = datetime.now().isoformat(),
    )

    if not source.exists():
        return MoveResultMFI(**base, status='failed', success=False,
                             error=f"Source file not found: {source}")

    if target.exists():
        return MoveResultMFI(**base, status='failed', success=False,
                             error=f"Target already exists: {target}")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        return MoveResultMFI(**base, status='completed', success=True, error='')

    except Exception as e:
        return MoveResultMFI(**base, status='failed', success=False, error=str(e))


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

ACTION_HANDLERS = {
    'scan_directory': handle_discovery,
    'copy':           handle_copy,
    'move':           handle_move,
}


def process_mfi(filepath: Path):
    """Claim, execute, and complete a single MFI file."""
    print(f"Claiming: {filepath.name}")
    processing_file = move_to_processing(filepath)

    try:
        mfi = decode(str(processing_file))
        handler = ACTION_HANDLERS.get(mfi.action)

        if not handler:
            raise ValueError(f"No handler for action: {mfi.action}")

        result = handler(mfi)
        write_mfi(result, folder=processing_file.parent.parent / 'completed')

        move_to_completed(processing_file)
        if hasattr(result, 'files'):
            print(f"Completed: {filepath.name} → {len(result.files)} files matched")
        else:
            print(f"Completed: {filepath.name} → {result.action} success={result.success}")
            
    except Exception as e:
        mark_failed(processing_file)
        print(f"Failed: {filepath.name} — {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(watch: bool = False, interval: int = 10):
    """Process pending MFI files. Optionally loop."""
    print("MFI Watcher started.")
    while True:
        pending = read_pending()
        if pending:
            for filepath in pending:
                process_mfi(filepath)
        else:
            if not watch:
                print("No pending MFI files. Exiting.")
                break
            print(f"Nothing pending. Checking again in {interval}s...")

        if not watch:
            break
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MFI Watcher — process pending MFI instructions')
    parser.add_argument('--watch', action='store_true', help='Loop continuously, polling for new MFI files')
    parser.add_argument('--interval', type=int, default=10, help='Poll interval in seconds (default: 10)')
    args = parser.parse_args()
    run(watch=args.watch, interval=args.interval)