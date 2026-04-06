# app/bots/db/vera.py

from app.bots import bot_logger as log
from app.services.neo4j_service import get_session
from app.shared.datetime_utils import to_neo4j as parse_timestamp, to_python as parse_to_datetime

REQUIRES = {'neo4j'}

def _serialize_record(record: dict) -> dict:
    """Convert Neo4j temporal objects to JSON-serializable strings."""
    result = {}
    for key, value in record.items():
        if value is None:
            result[key] = None
        elif hasattr(value, 'iso_format'):  # Neo4j DateTime, Date, Time
            result[key] = value.iso_format()
        else:
            result[key] = value
    return result

# ── vera.todos.get_pending ────────────────────────────────────────────────────

VERA_FN_TODOS_PENDING = "vera.todos.get_pending"

def get_pending_todos(session=None, reason: str = "", log_call: bool = True) -> list[dict]:
    """[DEPRECATED] Use get_todos() instead."""
    if log_call and reason:
        log.call(VERA_FN_TODOS_PENDING, reason=reason)
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run("""
            MATCH (t:Todo)
            WHERE t.status <> 'done'
            RETURN t.`todo-id` AS id, t.description AS description,
                   t.priority AS priority, t.owner AS owner,
                   t.friction AS friction, t.status AS status,
                   t.created AS created, t.due AS due
            ORDER BY t.priority DESC, t.created ASC
        """)
        return [_serialize_record(dict(r)) for r in result]
    except Exception as e:
        log.error(VERA_FN_TODOS_PENDING, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)

# ── vera.todos.get_friction_items ─────────────────────────────────────────────

VERA_FN_TODOS_FRICTION = "vera.todos.get_friction_items"
DEFAULT_FRICTION_TYPES = ["phone-call", "difficult", "waiting-on-other", "hated-meeting"]

def get_friction_todos(session=None, friction_types: list[str] = None, reason: str = "", log_call: bool = True) -> list[dict]:
    """[DEPRECATED] Use get_todos(exclude=['friction']) or get_todos() with friction filtering instead."""
    if log_call and reason:
        log.call(VERA_FN_TODOS_FRICTION, reason=reason)
    if friction_types is None:
        friction_types = DEFAULT_FRICTION_TYPES
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run("""
            MATCH (t:Todo)
            WHERE t.status <> 'done' AND t.friction IN $friction_types
            RETURN t.`todo-id` AS id, t.description AS description,
                   t.priority AS priority, t.owner AS owner,
                   t.friction AS friction, t.status AS status,
                   t.created AS created, t.due AS due
            ORDER BY t.priority DESC, t.created ASC
        """, friction_types=friction_types)
        return [_serialize_record(dict(r)) for r in result]
    except Exception as e:
        log.error(VERA_FN_TODOS_FRICTION, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)

# ── vera.filenodes.get_unreviewed ─────────────────────────────────────────────

VERA_FN_FILENODES_UNREVIEWED = "vera.filenodes.get_unreviewed"

def get_unreviewed_filenodes(session=None, mfn_type: str = None, reason: str = "", log_call: bool = True) -> list[dict]:
    """Get unreviewed FileNodes."""
    if log_call and reason:
        log.call(VERA_FN_FILENODES_UNREVIEWED, reason=reason)
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        if mfn_type:
            result = session.run(f"""
                MATCH (f:FileNode:{mfn_type})
                WHERE f.reviewed = false OR f.reviewed IS NULL
                RETURN f.`FILE-NODE-id` AS id, f.filepath AS filepath,
                       f.review_priority AS review_priority, f.created AS created
                ORDER BY f.review_priority DESC
            """)
        else:
            result = session.run("""
                MATCH (f:FileNode)
                WHERE f.reviewed = false OR f.reviewed IS NULL
                RETURN f.`FILE-NODE-id` AS id, f.filepath AS filepath,
                       f.review_priority AS review_priority, f.created AS created,
                       labels(f) AS labels
                ORDER BY f.review_priority DESC
            """)
        return [_serialize_record(dict(r)) for r in result]
    except Exception as e:
        log.error(VERA_FN_FILENODES_UNREVIEWED, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)

# ── vera.r2hodo.get_unsubmitted ───────────────────────────────────────────────

VERA_FN_R2HODO_UNSUBMITTED = "vera.r2hodo.get_unsubmitted"

def get_unsubmitted_r2hodo(session=None, reason: str = "", log_call: bool = True) -> list[dict]:
    """Get unsubmitted R2HOdo trips."""
    if log_call and reason:
        log.call(VERA_FN_R2HODO_UNSUBMITTED, reason=reason)
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run("""
            MATCH (f:R2HOdo)
            WHERE f.dispatcher_submitted = false OR f.treasurer_submitted = false
               OR f.dispatcher_submitted IS NULL OR f.treasurer_submitted IS NULL
            RETURN f.`FILE-NODE-id` AS id, f.patient_name AS patient_name,
                   f.trip_date AS trip_date, f.distance_km AS distance_km,
                   f.dispatcher_submitted AS dispatcher_submitted,
                   f.treasurer_submitted AS treasurer_submitted
            ORDER BY f.trip_date ASC
        """)
        return [_serialize_record(dict(r)) for r in result]
    except Exception as e:
        log.error(VERA_FN_R2HODO_UNSUBMITTED, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)

# ── vera.ideas.get_pending ────────────────────────────────────────────────────

VERA_FN_IDEAS_PENDING = "vera.ideas.get_pending"

def get_pending_ideas(session=None, reason: str = "", log_call: bool = True) -> list[dict]:
    """Get pending ideas."""
    if log_call and reason:
        log.call(VERA_FN_IDEAS_PENDING, reason=reason)
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run("""
            MATCH (i:Idea)
            WHERE NOT i.status IN ['done', 'promoted', 'dismissed']
            RETURN i.`idea-id` AS id, i.description AS description,
                   i.status AS status, i.created AS created
            ORDER BY i.created ASC
        """)
        return [_serialize_record(dict(r)) for r in result]
    except Exception as e:
        log.error(VERA_FN_IDEAS_PENDING, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)

# ── vera.todos.get ───────────────────────────────────────────────────────────

VERA_FN_TODOS_GET = "vera.todos.get"
ACTIVE_STATUSES = ['open', 'pending', 'in_progress']
VALID_PRIORITIES = ['high', 'medium', 'low']
VALID_FRICTION = ['phone-call', 'difficult', 'uncertain', 'boring', 'waiting-on-other', 'hated-meeting']

def get_todos(
    session=None,
    status: 'str | list | None' = 'active',
    priority: 'str | None' = None,
    exclude: 'list | None' = None,
    day_range: 'int | None' = None,
    timestamp: 'str | None' = None,
    limit: 'int | None' = None,
    reason: str = "",
    log_call: bool = True,
) -> list[dict]:
    """Flexible todo query. Use for any todo retrieval — daily review, priority
    triage, friction checks, deferred backlog, or time-windowed lookups.
    Replaces get_pending_todos and get_friction_todos.

    status:    'active' (open/pending/in_progress) | 'all' | explicit list
    priority:  'HIGH' | 'MEDIUM' | 'LOW' | None (all)
    exclude:   list of ['friction', 'deferred', 'open']
    day_range: +-N days relative to timestamp (or now); negative = past window
    timestamp: ISO anchor for day_range; defaults to now()
    limit:     cap on results; None = no cap
    """
    # Resolve status keyword
    if status == 'active':
        status_list = ACTIVE_STATUSES
    elif status in ('all', None):
        status_list = None
    elif isinstance(status, str):
        status_list = [status]
    else:
        status_list = list(status)

    if log_call:
        parts = [f"status={status}"]
        if priority:                parts.append(f"priority={priority}")
        if exclude:                 parts.append(f"exclude={exclude}")
        if day_range is not None:   parts.append(f"day_range={day_range}")
        if timestamp:               parts.append(f"anchor={timestamp}")
        if limit:                   parts.append(f"limit={limit}")
        log.call(VERA_FN_TODOS_GET, reason=reason, detail=" | ".join(parts))

    exclude = exclude or []
    conditions = []
    params = {}

    if status_list is not None:
        conditions.append("t.status IN $status_list")
        params['status_list'] = status_list

    if 'deferred' in exclude:
        conditions.append("t.status <> 'deferred'")

    if 'open' in exclude:
        conditions.append("t.status <> 'open'")

    if priority:
        priority = priority.lower()  # Enforce lowercase — stored values are lowercase
        conditions.append("t.priority = $priority")
        params['priority'] = priority

    if 'friction' in exclude:
        conditions.append("(t.friction IS NULL OR t.friction = 'none')")

    # Day range window
    if day_range is not None:
        parsed = parse_timestamp(timestamp) if timestamp else None
        anchor_expr = "datetime($anchor)" if parsed else "datetime()"
        if parsed:
            params['anchor'] = parsed
        if day_range < 0:
            conditions.append(f"t.created >= {anchor_expr} + duration({{days: {day_range}}})")
            conditions.append(f"t.created <= {anchor_expr}")
        else:
            conditions.append(f"t.created >= {anchor_expr}")
            conditions.append(f"t.created <= {anchor_expr} + duration({{days: {day_range}}})")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    limit_clause = f"LIMIT {limit}" if limit else ""

    cypher = f"""
        MATCH (t:Todo)
        {where_clause}
        RETURN t.`todo-id` AS id, t.description AS description,
               t.priority AS priority, t.friction AS friction,
               t.status AS status, t.created AS created, t.due AS due
        ORDER BY
          CASE t.priority
            WHEN 'high' THEN 1
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
          END ASC,
          t.created ASC
        {limit_clause}
    """

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run(cypher, **params)
        return [_serialize_record(dict(r)) for r in result]
    except Exception as e:
        log.error(VERA_FN_TODOS_GET, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)

# ── vera.todos.update ─────────────────────────────────────────────────────────

VERA_FN_TODOS_UPDATE = "vera.todos.update"

def update_todo(session=None, todo_id: str = None, updates: dict = None, reason: str = "", log_call: bool = True) -> dict:
    """Update todo node properties (status, priority, friction, etc.)."""
    if log_call and reason:
        log.call(VERA_FN_TODOS_UPDATE, reason=reason)
    
    if not todo_id or not updates:
        log.error(VERA_FN_TODOS_UPDATE, reason=reason, detail="Missing todo_id or updates")
        return {"error": "Missing required parameters: todo_id and updates"}

    # Enforce lowercase priority before write
    if 'priority' in updates and updates['priority']:
        updates['priority'] = updates['priority'].lower()

    # Coerce created through to_python — Neo4j driver converts Python datetime to native DateTime type
    # due is date-only and stays as a string
    if 'created' in updates and updates['created']:
        parsed = parse_to_datetime(updates['created'])
        if parsed:
            updates['created'] = parsed
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run("""
            MATCH (t:Todo {`todo-id`: $todo_id})
            SET t += $updates
            RETURN t.`todo-id` AS id, t.description AS description,
                   t.priority AS priority, t.owner AS owner,
                   t.friction AS friction, t.status AS status,
                   t.created AS created, t.due AS due
        """, todo_id=todo_id, updates=updates)
        record = result.single()
        if record:
            return _serialize_record(dict(record))
        else:
            log.error(VERA_FN_TODOS_UPDATE, reason=reason, detail=f"Todo not found: {todo_id}")
            return {"error": f"Todo not found: {todo_id}"}
    except Exception as e:
        log.error(VERA_FN_TODOS_UPDATE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)