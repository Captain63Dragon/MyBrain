"""
tops_service.py - TOPS Neo4j <-> Zaudi sync.

Neo4j is source of truth (FoodLibrary, FoodLog nodes).
Zaudi tops_sync.php is the mobile UI / display layer.

Sync directions per table:
  PULL - get_unverified from Zaudi, MERGE new keys into Neo4j.
         Existing local nodes untouched (MERGE on primary key).
  PUSH - collect nodes where synced_at IS NULL, POST to Zaudi,
         stamp synced_at on success.

Edit convention:
  Persona / UI / Mia MUST clear synced_at when modifying a node.
  Push key is "synced_at IS NULL" - no other change detection.

Trigger sites:
  - run_sync_cycle(auto=True)  from external_data_fetch after each poll
  - run_sync_cycle(auto=False) from /sync/zaudi/tops route (manual)

Push guard mirrors api_service:
  auto   = 1hr threshold OR dirty
  manual = 5min threshold OR dirty
"""

import requests
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from threading import Lock

from flask import current_app
from app.services.neo4j_service import get_session

# -- State (in-memory, intentionally non-persistent) -------------------------
_sync_in_progress = False
_dirty            = False
_last_auto_push:   'datetime | None' = None
_last_manual_push: 'datetime | None' = None
_lock = Lock()

AUTO_THRESHOLD   = timedelta(hours=1)
MANUAL_THRESHOLD = timedelta(minutes=5)

DAILY_TARGET = 1900

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
        'fields':  LOG_FIELDS,
        'key':     'log_id',
        'label':   'FoodLog',
    },
    'food_library': {
        'fields':  LIB_FIELDS,
        'key':     'item_id',
        'label':   'FoodLibrary',
    },
}


# -- Public - dirty flag -----------------------------------------------------
def mark_dirty():
    """Signal local change - next sync cycle pushes regardless of threshold."""
    global _dirty
    _dirty = True


# -- Sentinel file (persona fallback) ----------------------------------------
from app.shared.mfi_shared import tops_path

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


# -- Internal - push guard ---------------------------------------------------
def _has_pending_nodes() -> bool:
    """Check Neo4j for any unsynced nodes - source of truth for dirty state."""
    try:
        with get_session() as session:
            result = session.run("""
                MATCH (n) WHERE (n:FoodLog OR n:FoodLibrary) AND n.synced_at IS NULL
                RETURN count(n) AS pending
            """)
            return result.single()['pending'] > 0
    except Exception:
        return False

def _should_push(auto: bool, now: datetime) -> bool:
    last      = _last_auto_push   if auto else _last_manual_push
    threshold = AUTO_THRESHOLD    if auto else MANUAL_THRESHOLD
    stale     = last is None or (now - last) > threshold
    return _dirty or _is_dirty_file() or _has_pending_nodes() or stale


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


# -- Neo4j helpers -----------------------------------------------------------
def _serialize(record) -> dict:
    """Convert Neo4j temporal objects to JSON-serializable strings."""
    result = {}
    for key, value in dict(record).items():
        if value is None:
            result[key] = None
        elif hasattr(value, 'iso_format'):
            result[key] = value.iso_format()
        else:
            result[key] = value
    return result


# -- Preprocessor ------------------------------------------------------------
def _preprocess_log():
    """Recalculate est_calories and daily_balance on FoodLog nodes.
    Reads from Neo4j, processes in Python, writes back. Called before push."""

    with get_session() as session:
        # Get all log entries with their library calories
        result = session.run("""
            MATCH (log:FoodLog)
            OPTIONAL MATCH (log)-[:LOGGED_ITEM]->(lib:FoodLibrary)
            RETURN log.log_id AS log_id,
                   log.logged_at AS logged_at,
                   log.portion_pct AS portion_pct,
                   lib.calories AS lib_calories
            ORDER BY log.logged_at ASC
        """)
        entries = [dict(r) for r in result]

    if not entries:
        return

    # Group by date
    days = defaultdict(list)
    for entry in entries:
        if entry['logged_at']:
            days[str(entry['logged_at'])[:10]].append(entry)

    updates = []
    for d in sorted(days.keys()):
        running_total = 0
        day_broken    = False
        for entry in days[d]:
            base_cal = entry.get('lib_calories')
            pct      = entry.get('portion_pct') or 100
            if base_cal is not None and not day_broken:
                est = round(base_cal * (pct / 100))
                running_total += est
                updates.append({
                    'log_id':        entry['log_id'],
                    'est_calories':  est,
                    'daily_balance': DAILY_TARGET - running_total,
                })
            else:
                day_broken = True

    if not updates:
        return

    with get_session() as session:
        session.run("""
            UNWIND $updates AS u
            MATCH (log:FoodLog {log_id: u.log_id})
            SET log.est_calories  = u.est_calories,
                log.daily_balance = u.daily_balance
        """, updates=updates)

    print(f'[tops_service] preprocess complete - {len(updates)} log entries recalculated')


# -- Pull --------------------------------------------------------------------
def pull(table: str) -> dict:
    """Pull unverified rows from Zaudi. MERGE new keys into Neo4j only."""
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

    with get_session() as session:
        # Get existing keys
        result = session.run(
            f"MATCH (n:{cfg['label']}) RETURN n.{cfg['key']} AS key"
        )
        existing_keys = {r['key'] for r in result}

        new_rows = [r for r in remote_items if r.get(cfg['key']) and r[cfg['key']] not in existing_keys]

        if new_rows:
            session.run(f"""
                UNWIND $rows AS row
                CREATE (n:{cfg['label']})
                SET n = row
            """, rows=new_rows)

    return {'pulled': len(remote_items), 'new': len(new_rows)}


# -- Push --------------------------------------------------------------------
def push(table: str) -> dict:
    """Push nodes where synced_at IS NULL to Zaudi. Stamp synced_at on success."""
    cfg = TABLE_CONFIG[table]

    with get_session() as session:
        result = session.run(f"""
            MATCH (n:{cfg['label']})
            WHERE n.synced_at IS NULL
            RETURN n
        """)
        pending = [_serialize(r['n']) for r in result]

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

    # Stamp synced_at on pushed nodes
    pushed_keys = [r.get(cfg['key']) for r in pending if r.get(cfg['key'])]
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_session() as session:
        session.run(f"""
            UNWIND $keys AS key
            MATCH (n:{cfg['label']} {{{cfg['key']}: key}})
            SET n.synced_at = $now
        """, keys=pushed_keys, now=now_iso)

    return {'pushed': data.get('upserted', len(pending))}


# -- Orchestrator ------------------------------------------------------------
def run_sync_cycle(reason: str = '', auto: bool = False) -> dict:
    """Pull + push both tables."""
    global _sync_in_progress

    with _lock:
        if _sync_in_progress:
            return {'status': 'skipped', 'reason': 'sync already in progress'}
        _sync_in_progress = True

    now = datetime.now(timezone.utc)
    report: dict = {'reason': reason, 'auto': auto}

    try:
        report['pull_log'] = pull('food_log')
        report['pull_lib'] = pull('food_library')

        if not _should_push(auto, now):
            label = 'auto' if auto else 'manual'
            last  = _last_auto_push if auto else _last_manual_push
            report['push_skipped']     = True
            report['push_skip_reason'] = (
                f"{label} threshold not met, clean - "
                f"last push {last.isoformat() if last else 'never'}"
            )
            report['status'] = 'ok'
            return report

        _preprocess_log()
        report['push_log'] = push('food_log')
        report['push_lib'] = push('food_library')

        if 'error' not in report.get('push_log', {}) or 'error' not in report.get('push_lib', {}):
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
