"""
api_service.py — External API client layer.
Handles all communication with api.zaudi.com.

Sync cycle (two calls to todo_sync.php):
  1. get_unprocessed_todos() — begin lock, claim fresh rows, return fresh + stranded
  2. [Flask] process fresh rows via vera create_todo
  3. [Flask] get_todos_for_sync() — pull active todos from Neo4j, score, rank, cap
  4. commit_todos(todos) — bulk upsert into todos_new, drop, rename

Trigger sites:
  - run_sync_cycle() called from /sync/zaudi/todos (manual, auto=False)
  - run_sync_cycle(auto=True) called from mail_ingestor after _poll()

Push guard:
  - auto=True  (ingestor, every 5min):  push if dirty OR last_push > 1hr
  - auto=False (manual/UI, on demand):  push if dirty OR last_push > 5min
  Dirty flag set by mark_dirty() — called by bots_routes after successful execution.
  Cleared after every successful push. None last_push → push fires (safe restart default).

Re-entrancy guard: _sync_in_progress prevents concurrent cycles.
vera_todos_create does NOT trigger a standalone push during sync — ingest owns it.
"""

import requests
from datetime import datetime, timezone, timedelta
from flask import current_app

from app.models import neo4j
from app.bots.db.vera import create_todo, _serialize_record

# ── Re-entrancy guard ─────────────────────────────────────────────────────────
_sync_in_progress = False

# ── Push guard state (in-memory, intentionally non-persistent) ────────────────
_dirty            = False
_last_auto_push:   'datetime | None' = None
_last_manual_push: 'datetime | None' = None

AUTO_THRESHOLD   = timedelta(hours=1)
MANUAL_THRESHOLD = timedelta(minutes=5)


def mark_dirty():
    """Signal that a write occurred — next sync cycle should push regardless of threshold.
    Called by bots_routes after any successful bot execution.
    Direct Neo4j writes (outside /bots/execute) are not detectable here —
    they are caught by whichever threshold fires next.
    """
    global _dirty
    _dirty = True


def _should_push(auto: bool, now: datetime) -> bool:
    """True if the push step should run this cycle."""
    last      = _last_auto_push   if auto else _last_manual_push
    threshold = AUTO_THRESHOLD    if auto else MANUAL_THRESHOLD
    stale     = last is None or (now - last) > threshold
    return _dirty or stale


def _record_push(auto: bool, now: datetime):
    """Stamp last push timestamp and clear dirty flag."""
    global _dirty, _last_auto_push, _last_manual_push
    _dirty = False
    if auto:
        _last_auto_push = now
    else:
        _last_manual_push = now


# ── Config helpers ────────────────────────────────────────────────────────────

def _api_key() -> str:
    return current_app.config.get('ZAUDI_API_KEY', '')

def _base_url() -> str:
    return current_app.config.get('ZAUDI_BASE_URL', 'https://api.zaudi.com').rstrip('/')

def _headers() -> dict:
    return {
        'Content-Type': 'application/json',
        'X-API-Key': _api_key(),
    }


# ── Collection+JSON parser ────────────────────────────────────────────────────

def _parse_item(item: dict) -> dict:
    """Flatten a Collection+JSON item data array into a plain dict."""
    return {entry['name']: entry['value'] for entry in item.get('data', [])}

def _item_rel(item: dict) -> str:
    """Extract rel value from item links (fresh | stranded)."""
    links = item.get('links', [])
    return links[0].get('rel', '') if links else ''

def _parse_response(resp: requests.Response) -> dict:
    """Parse Collection+JSON response. Returns raw collection dict."""
    resp.raise_for_status()
    return resp.json().get('collection', {})


# ── Side A — Ingest (Zaudi → Neo4j) ──────────────────────────────────────────

def get_unprocessed_todos() -> tuple[list[dict], list[dict], dict]:
    """
    Call todo_sync.php get_unprocessed.
    Begins lock: renames todos → todos_processing, creates todos_new.
    Claims fresh rows (processing stamp). Identifies stranded (crash victims).

    Returns: (fresh, stranded, meta)
      fresh    — newly claimed, to be ingested via create_todo
      stranded — crash victims, go directly to failure list
      meta     — orphan flag, counts
    """
    url  = f"{_base_url()}/todo_sync.php"
    resp = requests.post(url, json={'action': 'get_unprocessed'}, headers=_headers(), timeout=15)
    collection = _parse_response(resp)

    items    = collection.get('items', [])
    meta_raw = collection.get('meta', [])
    meta     = {m['name']: m['value'] for m in meta_raw}

    fresh    = [_parse_item(i) for i in items if _item_rel(i) == 'fresh']
    stranded = [_parse_item(i) for i in items if _item_rel(i) == 'stranded']

    return fresh, stranded, meta


def commit_todos(todos: list[dict]) -> dict:
    """
    Call todo_sync.php commit with full todo payload.
    PHP: bulk upserts into todos_new, drops todos_processing, renames todos_new → todos.

    todos: list of dicts with Neo4j-canonical todo-ids.
           synced_at should be ISO timestamp for validated todos, None for failures.

    Returns: meta dict with status, upserted count, time.
    """
    url  = f"{_base_url()}/todo_sync.php"
    resp = requests.post(
        url,
        json={'action': 'commit', 'todos': todos},
        headers=_headers(),
        timeout=30,
    )
    collection = _parse_response(resp)
    meta_raw   = collection.get('meta', [])
    return {m['name']: m['value'] for m in meta_raw}


# ── Side B — Push (Neo4j → Zaudi) ────────────────────────────────────────────

def get_todos_for_sync(limit: int = 100) -> list[dict]:
    from app.services.scoring_service import get_scoring_policy, score_and_rank

    active_statuses = ['open', 'pending', 'in_progress']
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    with neo4j.get_session() as session:
        policy = get_scoring_policy(session)
        # print(f"[get_todos_for_sync] policy found: {policy is not None}")

        result = session.run("""
            MATCH (t:Todo)
            WHERE t.status IN $statuses
            RETURN
                t.`todo-id`    AS todo_id,
                t.description  AS description,
                t.priority     AS priority,
                t.status       AS status,
                t.friction     AS friction,
                t.created      AS created,
                t.due          AS due,
                t.owner        AS owner,
                t.source_pin   AS source_pin,
                t.notes        AS notes
        """, statuses=active_statuses)

        rows = [dict(r) for r in result]
        # print(f"[get_todos_for_sync] raw rows: {len(rows)}")

    if policy:
        rows = score_and_rank(rows, policy, now, limit=limit)
        # print(f"[get_todos_for_sync] after scoring: {len(rows)}")
    else:
        rows = sorted(rows, key=lambda t: str(t.get('created') or ''), reverse=True)[:limit]
        # print(f"[get_todos_for_sync] no policy, sorted: {len(rows)}")

    clean = []
    for row in rows:
        row = _serialize_record(row)
        row.pop('score', None)
        row.pop('nudge', None)
        row['synced_at'] = now_iso
        clean.append(row)

    print(f"[get_todos_for_sync] returning: {len(clean)}")
    return clean


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_sync_cycle(reason: str = '', auto: bool = False) -> dict:
    global _sync_in_progress
    if _sync_in_progress:
        return {'status': 'skipped', 'reason': 'sync already in progress'}

    _sync_in_progress = True
    now = datetime.now(timezone.utc)

    report = {
        'fresh_count':    0,
        'stranded_count': 0,
        'success_count':  0,
        'failure_count':  0,
        'committed':      0,
        'push_skipped':   False,
    }

    # Push guard — check BEFORE touching any tables.
    # If not dirty and threshold not met, exit completely.
    # The lock must never fire unless we are committed to a full cycle.
    if not _should_push(auto, now):
        label = 'auto' if auto else 'manual'
        last  = _last_auto_push if auto else _last_manual_push
        _sync_in_progress = False
        return {
            'status':           'guarded',
            'push_skipped':     True,
            'push_skip_reason': f"{label} threshold not met, clean — last push {last.isoformat() if last else 'never'}",
        }

    try:
        # Step 1 — begin lock, claim rows
        fresh, stranded, meta = get_unprocessed_todos()
        report['fresh_count']    = len(fresh)
        report['stranded_count'] = len(stranded)
        report['orphan']         = meta.get('orphan', False)

        failures = []

        # Step 2 — ingest fresh rows
        for item in fresh:
            result = create_todo(
                description = item.get('description'),
                priority    = item.get('priority', 'medium'),
                status      = item.get('status', 'open'),
                friction    = item.get('friction'),
                due         = item.get('due'),
                notes       = item.get('notes'),
                source_pin  = item.get('source_pin'),
                owner       = item.get('owner', 'user'),
                made_by     = 'Vera',
                reason      = reason or 'API sync - new todo ingest',
            )
            if 'error' in result:
                failures.append(item)
                report['failure_count'] += 1
            else:
                report['success_count'] += 1

        # Step 3 — stranded rows go straight to failures
        failures.extend(stranded)
        report['failure_count'] += len(stranded)

        # Build failure payload
        failure_payload = []
        for f in failures:
            failure_payload.append({
                'todo_id':     f.get('todo_id'),
                'description': f.get('description'),
                'priority':    f.get('priority', 'medium'),
                'status':      f.get('status', 'open'),
                'friction':    f.get('friction'),
                'created':     f.get('created'),
                'due':         f.get('due'),
                'owner':       f.get('owner', 'user'),
                'source_pin':  f.get('source_pin'),
                'notes':       f.get('notes'),
                'synced_at':   None,
            })

        # Step 4 — push guard already passed at top of cycle — always push
        neo4j_todos = get_todos_for_sync(limit=100)
        payload = neo4j_todos + failure_payload
        _record_push(auto, now)
        commit_result = commit_todos(payload)
        report['committed'] = commit_result.get('upserted', 0)
        report['status']    = commit_result.get('status', 'unknown')

    except Exception as e:
        report['status'] = 'error'
        report['error']  = str(e)

    finally:
        _sync_in_progress = False

    return report