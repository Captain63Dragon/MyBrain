"""
tops_service.py — TOPS local <-> Zaudi sync.

Local JSON files in tops_path() are source of truth.
Zaudi tops_sync.php is the mobile UI / display layer.
Walter's CSV feeds are append-only consume-and-clear pipes.

Files (under MFI_PATH/tops/):
  food_log.json         — source of truth for log entries
  food_log.csv          — Walter's outbound feed (append-only)
  food_library.json     — source of truth for library items
  food_library.csv      — Walter's outbound feed (append-only)

Sync directions per table:
  PULL — get_unverified from Zaudi, INSERT new keys into local JSON,
         append new rows to Walter's CSV. Existing local rows untouched.
  PUSH — collect rows where synced_at IS NULL, POST update to Zaudi,
         stamp synced_at on success, append to Walter's CSV.

Edit convention:
  Persona / UI / Mia MUST clear synced_at when modifying a row locally.
  Push key is "synced_at IS NULL" — no other change detection.

Trigger sites:
  - run_sync_cycle(auto=True)  from mail_ingestor after each poll
  - run_sync_cycle(auto=False) from /sync/zaudi/tops route (manual)

Push guard mirrors api_service:
  auto   = 1hr threshold OR dirty
  manual = 5min threshold OR dirty
"""

import csv
import json
import requests
from datetime import datetime, timezone, timedelta
from threading import Lock

from flask import current_app
from app.shared.mfi_shared import tops_path

# -- State (in-memory, intentionally non-persistent) -------------------------
_sync_in_progress = False
_dirty            = False
_last_auto_push:   'datetime | None' = None
_last_manual_push: 'datetime | None' = None
_lock = Lock()

AUTO_THRESHOLD   = timedelta(hours=1)
MANUAL_THRESHOLD = timedelta(minutes=5)

# -- Schema field maps (mirror tops_sync.php) --------------------------------
LOG_FIELDS = [
    'log_id', 'logged_at', 'category', 'venue', 'item',
    'portion_pct', 'est_calories', 'mia_rating',
    'daily_balance', 'notes', 'synced_at',
]

LIB_FIELDS = [
    'item_id', 'item_name', 'venue', 'category',
    'calories', 'unit_desc', 'verified',
    'mia_rating', 'mia_notes', 'mia_reviewed_at',
    'synced_at', 'created_at', 'updated_at',
]

TABLE_CONFIG = {
    'food_log': {
        'fields':   LOG_FIELDS,
        'key':      'log_id',
        'json':     'food_log.json',
        'csv':      'food_log.csv',
    },
    'food_library': {
        'fields':   LIB_FIELDS,
        'key':      'item_id',
        'json':     'food_library.json',
        'csv':      'food_library.csv',
    },
}


DAILY_TARGET = 1900  # matches tops_preprocessor.py

# -- Preprocessor (absorbed from tops_preprocessor.py) -----------------------
def _preprocess_log():
    """Recalculate est_calories and daily_balance in food_log.json
    using calorie values from food_library.json. Called before push."""
    from collections import defaultdict

    library = _read_json('food_library.json')
    log     = _read_json('food_log.json')
    if not log:
        return

    # Build lookup: (item_name, venue) -> calories or None
    lookup = {}
    for entry in library:
        key = (entry.get('item_name'), entry.get('venue'))
        cal = entry.get('calories')
        lookup[key] = cal if cal else None

    # Group by date
    days = defaultdict(list)
    for entry in log:
        days[entry['logged_at'][:10]].append(entry)

    for d in days:
        days[d].sort(key=lambda e: e['logged_at'])

    updated = []
    for d in sorted(days.keys()):
        running_total = 0
        day_broken    = False
        for entry in days[d]:
            key      = (entry.get('item'), entry.get('venue'))
            base_cal = lookup.get(key)
            pct      = entry.get('portion_pct', 100)
            if base_cal is not None and not day_broken:
                est = round(base_cal * (pct / 100))
                running_total += est
                entry['est_calories']  = est
                entry['daily_balance'] = DAILY_TARGET - running_total
            else:
                entry['est_calories']  = None
                entry['daily_balance'] = None
                day_broken = True
            updated.append(entry)

    _write_json('food_log.json', updated)
    print(f'[tops_service] preprocess complete — {len(updated)} log entries recalculated')


# -- Public — dirty flag -----------------------------------------------------
def mark_dirty():
    """Signal local change — next sync cycle pushes regardless of threshold."""
    global _dirty
    _dirty = True


# -- Sentinel file (persona fallback) ----------------------------------------
# Persona edits JSON then writes an empty tops_path()/sync.dirty file.
# Flask detects it at next poll, pushes, then deletes it.
DIRTY_SENTINEL = 'sync.dirty'

def _is_dirty_file() -> bool:
    try:
        return (tops_path() / DIRTY_SENTINEL).exists()
    except Exception:
        return False

def _clear_dirty_file():
    try:
        f = tops_path() / DIRTY_SENTINEL
        if f.exists():
            f.unlink()
    except Exception as e:
        print(f"[tops_service] could not clear dirty sentinel: {e}")


# -- Internal — push guard ---------------------------------------------------
def _should_push(auto: bool, now: datetime) -> bool:
    last      = _last_auto_push   if auto else _last_manual_push
    threshold = AUTO_THRESHOLD    if auto else MANUAL_THRESHOLD
    stale     = last is None or (now - last) > threshold
    return _dirty or _is_dirty_file() or stale


def _record_push(auto: bool, now: datetime):
    global _dirty, _last_auto_push, _last_manual_push
    _dirty = False
    _clear_dirty_file()
    if auto:
        _last_auto_push = now
    else:
        _last_manual_push = now


# -- Config helpers ----------------------------------------------------------
def _api_key() -> str:
    return current_app.config.get('ZAUDI_API_KEY', '')

def _base_url() -> str:
    return current_app.config.get('ZAUDI_BASE_URL', 'https://api.zaudi.com').rstrip('/')

def _headers() -> dict:
    return {'Content-Type': 'application/json', 'X-API-Key': _api_key()}

def _endpoint() -> str:
    return f"{_base_url()}/tops_sync.php"


# -- File I/O ----------------------------------------------------------------
def _ensure_dir():
    tops_path().mkdir(parents=True, exist_ok=True)


def _read_json(filename: str) -> list[dict]:
    path = tops_path() / filename
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[tops_service] read error {filename}: {e}")
        return []


def _write_json(filename: str, data: list[dict]):
    """Atomic write: tmp file then rename."""
    _ensure_dir()
    path = tops_path() / filename
    tmp  = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    tmp.replace(path)


def _append_csv(filename: str, fields: list[str], rows: list[dict]):
    """Append rows to Walter's CSV. Writes header if file is new/empty."""
    if not rows:
        return
    _ensure_dir()
    path = tops_path() / filename
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


# -- Pull --------------------------------------------------------------------
def pull(table: str) -> dict:
    """Pull unverified rows from Zaudi. INSERT new keys only — never overwrite local edits."""
    cfg = TABLE_CONFIG[table]

    try:
        resp = requests.post(
            _endpoint(),
            json={'action': 'get_unverified', 'table': table},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {'error': str(e), 'pulled': 0}

    if data.get('status') != 'ok':
        return {'error': data.get('message', 'unknown'), 'pulled': 0}

    remote_items = data.get('items') or []
    if not remote_items:
        return {'pulled': 0, 'new': 0}

    local = _read_json(cfg['json'])
    local_keys = {row.get(cfg['key']) for row in local if row.get(cfg['key'])}

    new_rows = [r for r in remote_items if r.get(cfg['key']) and r[cfg['key']] not in local_keys]

    if new_rows:
        local.extend(new_rows)
        _write_json(cfg['json'], local)
        _append_csv(cfg['csv'], cfg['fields'], new_rows)

    return {'pulled': len(remote_items), 'new': len(new_rows)}


# -- Push --------------------------------------------------------------------
def push(table: str) -> dict:
    """Push rows where synced_at IS NULL. Stamp synced_at on success."""
    cfg = TABLE_CONFIG[table]
    local = _read_json(cfg['json'])

    pending = [r for r in local if not r.get('synced_at')]
    if not pending:
        return {'pushed': 0}

    try:
        resp = requests.post(
            _endpoint(),
            json={'action': 'update', 'table': table, 'items': pending},
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {'error': str(e), 'pushed': 0}

    if data.get('status') != 'ok':
        return {'error': data.get('message', 'unknown'), 'pushed': 0}

    # Stamp synced_at on rows we just sent
    now_iso = datetime.now(timezone.utc).isoformat()
    pushed_keys = {r.get(cfg['key']) for r in pending if r.get(cfg['key'])}
    for row in local:
        if row.get(cfg['key']) in pushed_keys:
            row['synced_at'] = now_iso

    _write_json(cfg['json'], local)
    _append_csv(cfg['csv'], cfg['fields'], pending)

    return {'pushed': data.get('upserted', len(pending))}


# -- Orchestrator ------------------------------------------------------------
def run_sync_cycle(reason: str = '', auto: bool = False) -> dict:
    """Pull + push both tables. Hook target for mail_ingestor and /sync routes."""
    global _sync_in_progress

    with _lock:
        if _sync_in_progress:
            return {'status': 'skipped', 'reason': 'sync already in progress'}
        _sync_in_progress = True

    now = datetime.now(timezone.utc)
    report: dict = {'reason': reason, 'auto': auto}

    try:
        # Pull always — cheap, surfaces new items
        report['pull_log'] = pull('food_log')
        report['pull_lib'] = pull('food_library')

        # Push gated by threshold + dirty flag
        if not _should_push(auto, now):
            label = 'auto' if auto else 'manual'
            last  = _last_auto_push if auto else _last_manual_push
            report['push_skipped']     = True
            report['push_skip_reason'] = (
                f"{label} threshold not met, clean — "
                f"last push {last.isoformat() if last else 'never'}"
            )
            report['status'] = 'ok'
            return report

        _preprocess_log()
        report['push_log'] = push('food_log')
        report['push_lib'] = push('food_library')

        # Only stamp the push if at least one side succeeded
        if 'error' not in report['push_log'] or 'error' not in report['push_lib']:
            _record_push(auto, now)

        report['status'] = 'ok'
        return report

    except Exception as e:
        report['status'] = 'error'
        report['error']  = str(e)
        return report

    finally:
        with _lock:
            _sync_in_progress = False
