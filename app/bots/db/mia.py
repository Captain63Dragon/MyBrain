# app/bots/db/mia.py
# Mia bot - TOPS food library and log operations
# Mirrors vera.py pattern

from app.bots import bot_logger as log
from app.services.neo4j_service import get_session
from app.bots.db.graph import create_relationship

REQUIRES = {'neo4j'}


def _serialize_record(record: dict) -> dict:
    """Convert Neo4j temporal objects to JSON-serializable strings."""
    result = {}
    for key, value in record.items():
        if value is None:
            result[key] = None
        elif hasattr(value, 'iso_format'):
            result[key] = value.iso_format()
        else:
            result[key] = value
    return result


# -- mia.tops_library.create -------------------------------------------------

MIA_FN_LIBRARY_CREATE = "mia.tops_library.create"

def create_library_item(
    session=None,
    item_name: str = None,
    venue: str = None,
    category: str = None,
    calories: int = None,
    unit_desc: str = None,
    verified: int = 0,
    mia_rating: str = None,
    mia_notes: str = None,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """Create a FoodLibrary node. item_id auto-generated as lib-{timestamp}."""
    if not item_name:
        return {"error": "item_name is required"}

    if log_call and reason:
        log.call(MIA_FN_LIBRARY_CREATE, reason=reason, detail=f"item_name={item_name}")

    import time
    item_id = f"lib-{int(time.time() * 1000)}"

    props = {
        "item_id":   item_id,
        "item_name": item_name,
        "verified":  verified,
    }
    if venue:            props["venue"]      = venue
    if category:         props["category"]   = category
    if calories is not None: props["calories"] = calories
    if unit_desc:        props["unit_desc"]  = unit_desc
    if mia_rating:       props["mia_rating"] = mia_rating
    if mia_notes:        props["mia_notes"]  = mia_notes

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run("""
            CREATE (lib:FoodLibrary $props)
            SET lib.created_at = datetime(),
                lib.updated_at = datetime(),
                lib.mia_reviewed_at = null
            RETURN lib
        """, props=props)
        record = result.single()
        if not record:
            return {"error": "FoodLibrary creation failed"}
        return _serialize_record(dict(record["lib"]))
    except Exception as e:
        log.error(MIA_FN_LIBRARY_CREATE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# -- mia.tops_library.get ----------------------------------------------------

MIA_FN_LIBRARY_GET = "mia.tops_library.get"

def get_library_items(
    session=None,
    category: str = None,
    venue: str = None,
    verified: int = None,
    unreviewed_only: bool = False,
    limit: int = None,
    reason: str = "",
    log_call: bool = True,
) -> list[dict]:
    """Query FoodLibrary nodes. Filter by category, venue, verified, or unreviewed."""
    if log_call and reason:
        log.call(MIA_FN_LIBRARY_GET, reason=reason)

    conditions = []
    params = {}

    if category:
        conditions.append("lib.category = $category")
        params["category"] = category
    if venue:
        conditions.append("lib.venue = $venue")
        params["venue"] = venue
    if verified is not None:
        conditions.append("lib.verified = $verified")
        params["verified"] = verified
    if unreviewed_only:
        conditions.append("lib.mia_reviewed_at IS NULL")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    limit_clause = f"LIMIT {limit}" if limit else ""

    cypher = f"""
        MATCH (lib:FoodLibrary)
        {where_clause}
        RETURN lib
        ORDER BY lib.item_name ASC
        {limit_clause}
    """

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run(cypher, **params)
        return [_serialize_record(dict(r["lib"])) for r in result]
    except Exception as e:
        log.error(MIA_FN_LIBRARY_GET, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# -- mia.tops_library.update -------------------------------------------------

MIA_FN_LIBRARY_UPDATE = "mia.tops_library.update"

def update_library_item(
    session=None,
    item_id: str = None,
    updates: dict = None,
    provisional: bool = False,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """Update a FoodLibrary node. Clears synced_at (joins push queue) unless provisional=True."""
    if not item_id or not updates:
        return {"error": "item_id and updates are required"}

    if log_call and reason:
        log.call(MIA_FN_LIBRARY_UPDATE, reason=reason, detail=f"item_id={item_id}")

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        if not provisional:
            updates['synced_at'] = None
        result = session.run("""
            MATCH (lib:FoodLibrary {item_id: $item_id})
            SET lib += $updates, lib.updated_at = datetime()
            RETURN lib
        """, item_id=item_id, updates=updates)
        record = result.single()
        if not record:
            return {"error": f"FoodLibrary item not found: {item_id}"}
        return _serialize_record(dict(record["lib"]))
    except Exception as e:
        log.error(MIA_FN_LIBRARY_UPDATE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# -- mia.tops_log.create -----------------------------------------------------

MIA_FN_LOG_CREATE = "mia.tops_log.create"

def create_log_entry(
    session=None,
    item_id: str = None,
    logged_at: str = None,
    category: str = None,
    venue: str = None,
    item: str = None,
    portion_pct: int = 100,
    est_calories: int = None,
    daily_balance: int = None,
    mia_rating: str = None,
    notes: str = None,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """Create a FoodLog node and wire [:LOGGED_ITEM] to FoodLibrary if item_id provided.
    Relationship is non-fatal -- log entry created even if library item not found.
    """
    if not item:
        return {"error": "item is required"}

    if log_call and reason:
        log.call(MIA_FN_LOG_CREATE, reason=reason, detail=f"item={item}")

    import time
    log_id = f"log-{int(time.time() * 1000)}"

    props = {
        "log_id":      log_id,
        "item":        item,
        "portion_pct": portion_pct,
    }
    if logged_at:            props["logged_at"]      = logged_at
    if category:             props["category"]       = category
    if venue:                props["venue"]           = venue
    if est_calories is not None: props["est_calories"] = est_calories
    if daily_balance is not None: props["daily_balance"] = daily_balance
    if mia_rating:           props["mia_rating"]     = mia_rating
    if notes:                props["notes"]           = notes

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()

        result = session.run("""
            CREATE (log:FoodLog $props)
            SET log.synced_at = datetime()
            RETURN log
        """, props=props)
        record = result.single()
        if not record:
            return {"error": "FoodLog creation failed"}

        # Wire LOGGED_ITEM -- non-fatal if library item not found
        if item_id:
            with log.sub_call():
                rel_result = create_relationship(
                    source_label="FoodLog",     source_match={"log_id": log_id},
                    target_label="FoodLibrary", target_match={"item_id": item_id},
                    rel_type="LOGGED_ITEM",
                    session=session, reason=reason, log_call=log_call,
                )
            if "error" in rel_result:
                log.error(MIA_FN_LOG_CREATE, reason=reason, detail=f"LOGGED_ITEM not wired: item_id={item_id} not found -- continuing")

        return _serialize_record(dict(record["log"]))

    except Exception as e:
        log.error(MIA_FN_LOG_CREATE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# -- mia.tops_log.get --------------------------------------------------------

MIA_FN_LOG_GET = "mia.tops_log.get"

def get_log_entries(
    session=None,
    date: str = None,
    category: str = None,
    venue: str = None,
    unreviewed_only: bool = False,
    day_range: int = None,
    limit: int = None,
    reason: str = "",
    log_call: bool = True,
) -> list[dict]:
    """Query FoodLog nodes. Filter by date, category, venue, or unreviewed.
    date: 'YYYY-MM-DD' string -- matches logged_at prefix.
    day_range: last N days from now.
    """
    if log_call and reason:
        log.call(MIA_FN_LOG_GET, reason=reason)

    conditions = []
    params = {}

    if date:
        conditions.append("log.logged_at STARTS WITH $date")
        params["date"] = date
    if category:
        conditions.append("log.category = $category")
        params["category"] = category
    if venue:
        conditions.append("log.venue = $venue")
        params["venue"] = venue
    if unreviewed_only:
        conditions.append("log.mia_rating IS NULL")
    if day_range is not None:
        conditions.append(f"log.synced_at >= datetime() - duration({{days: {day_range}}})")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    limit_clause = f"LIMIT {limit}" if limit else ""

    cypher = f"""
        MATCH (log:FoodLog)
        {where_clause}
        OPTIONAL MATCH (log)-[:LOGGED_ITEM]->(lib:FoodLibrary)
        RETURN log, lib.item_id AS library_item_id, lib.calories AS library_calories
        ORDER BY log.logged_at DESC
        {limit_clause}
    """

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run(cypher, **params)
        rows = []
        for r in result:
            entry = _serialize_record(dict(r["log"]))
            entry["library_item_id"]  = r["library_item_id"]
            entry["library_calories"] = r["library_calories"]
            rows.append(entry)
        return rows
    except Exception as e:
        log.error(MIA_FN_LOG_GET, reason=reason, detail=str(e))
        return []
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# -- mia.tops_log.update -----------------------------------------------------

MIA_FN_LOG_UPDATE = "mia.tops_log.update"

def update_log_entry(
    session=None,
    log_id: str = None,
    updates: dict = None,
    provisional: bool = False,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """Update a FoodLog node. Clears synced_at (joins push queue) unless provisional=True."""
    if not log_id or not updates:
        return {"error": "log_id and updates are required"}

    if log_call and reason:
        log.call(MIA_FN_LOG_UPDATE, reason=reason, detail=f"log_id={log_id}")

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        if not provisional:
            updates['synced_at'] = None
        result = session.run("""
            MATCH (log:FoodLog {log_id: $log_id})
            SET log += $updates
            RETURN log
        """, log_id=log_id, updates=updates)
        record = result.single()
        if not record:
            return {"error": f"FoodLog entry not found: {log_id}"}
        return _serialize_record(dict(record["log"]))
    except Exception as e:
        log.error(MIA_FN_LOG_UPDATE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)
