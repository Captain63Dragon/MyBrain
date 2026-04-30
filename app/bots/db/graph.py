# app/bots/db/graph.py
"""
Graph utility functions — persona-agnostic relationship operations.

These functions operate on arbitrary node labels and relationship types.
They are available to any persona or process via the generic /bots/execute route.

Constraint philosophy:
    VALID_REL_TYPES is a hardcoded constant. These are stable business rules
    that do not warrant a graph round-trip on every call. The BotFunction
    params schema surfaces the enum to LLM callers at tool-load time.
    This constant is the safety net for direct calls.

Bot IDs registered in Neo4j:
    graph.rel.create   →  create_relationship()
    graph.rel.inspect  →  inspect_relationships()
    graph.rel.delete   →  delete_relationship()
    graph.rel.reroute  →  reroute_relationship()

Planned (see Feature nodes):
    graph.integrity.duplicates
    graph.integrity.deduplicate
    graph.integrity.audit
"""

from app.bots import bot_logger as log
from app.services.neo4j_service import get_session

REQUIRES = {'neo4j'}

def _serialize_props(props: dict) -> dict:
    """Convert Neo4j temporal objects to JSON-serializable strings."""
    if not props:
        return {}
    result = {}
    for k, v in props.items():
        if v is None:
            result[k] = None
        elif hasattr(v, 'iso_format'):
            result[k] = v.iso_format()
        else:
            result[k] = v
    return result

# ── Valid relationship types ──────────────────────────────────────────────────
# Hardcoded by design — stable rules, no graph round-trip needed.
# Add new types here as the schema evolves.

VALID_REL_TYPES = [
    # Vera / Todo domain
    'FOLLOWS_FROM',
    'BLOCKED_BY',
    'EVOLVED_INTO',
    'MADE_TODO',
    'ASSIGNED',
    'NUDGED',
    # Feature domain
    'LEADS_TO',
    # Vocabulary / Term domain
    'CATEGORY',
    # FileNode domain
    'COPY_OF',
    'HAS_FORMAT',
    # Note domain
    'RELATES_TO',
]


# ── graph.rel.create ──────────────────────────────────────────────────────────

GRAPH_FN_REL_CREATE = "graph.rel.create"

def create_relationship(
    source_label: str,
    source_match: dict,
    target_label: str,
    target_match: dict,
    rel_type: str,
    properties: dict = None,
    session=None,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """
    Wire a relationship between any two nodes using MERGE semantics.
    Idempotent — safe to call multiple times, no duplicates created.

    source_label:  Node label for source  e.g. 'Todo'
    source_match:  Property dict to identify source  e.g. {'todo-id': 'todo-123'}
    target_label:  Node label for target  e.g. 'Todo'
    target_match:  Property dict to identify target  e.g. {'todo-id': 'todo-456'}
    rel_type:      Relationship type — must be in VALID_REL_TYPES
    properties:    Optional properties to set on the relationship
    reason:        Logging context
    log_call:      Whether to log this call
    """
    if log_call:
        log.call(GRAPH_FN_REL_CREATE, reason=reason, detail=
            f"{source_label}{source_match} -[{rel_type}]-> {target_label}{target_match}"
        )

    # Validate rel_type
    if rel_type not in VALID_REL_TYPES:
        msg = f"Invalid rel_type '{rel_type}'. Valid types: {VALID_REL_TYPES}"
        log.error(GRAPH_FN_REL_CREATE, reason=reason, detail=msg)
        return {"error": msg}

    if not source_label or not source_match:
        return {"error": "source_label and source_match are required"}
    if not target_label or not target_match:
        return {"error": "target_label and target_match are required"}

    # Build WHERE conditions for source and target match dicts.
    # Property names are backtick-quoted in Cypher (supports hyphens).
    # Param names use underscores — hyphens in $names are parsed as subtraction.
    def _param_key(prefix: str, k: str) -> str:
        return f"{prefix}_{k.replace('-', '_').replace('.', '_')}"

    source_conditions = " AND ".join(
        f"source.`{k}` = ${_param_key('src', k)}" for k in source_match
    )
    target_conditions = " AND ".join(
        f"target.`{k}` = ${_param_key('tgt', k)}" for k in target_match
    )

    params = {}
    for k, v in source_match.items():
        params[_param_key('src', k)] = v
    for k, v in target_match.items():
        params[_param_key('tgt', k)] = v

    prop_clause = "SET r += $rel_props" if properties else ""
    if properties:
        params['rel_props'] = properties

    cypher = f"""
        MATCH (source:{source_label})
        WHERE {source_conditions}
        MATCH (target:{target_label})
        WHERE {target_conditions}
        MERGE (source)-[r:{rel_type}]->(target)
        {prop_clause}
        RETURN
            '{source_label}'   AS source_label,
            '{target_label}'   AS target_label,
            '{rel_type}'       AS rel_type,
            properties(r)      AS rel_properties
    """

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run(cypher, **params)
        record = result.single()
        if record:
            return {
                "status": "ok",
                "source_label": record["source_label"],
                "source_match": source_match,
                "target_label": record["target_label"],
                "target_match": target_match,
                "rel_type": record["rel_type"],
                "rel_properties": dict(record["rel_properties"]) if record["rel_properties"] else {},
            }
        else:
            msg = "No matching nodes found — check labels and match properties"
            log.error(GRAPH_FN_REL_CREATE, reason=reason, detail=msg)
            return {"error": msg, "source_match": source_match, "target_match": target_match}
    except Exception as e:
        log.error(GRAPH_FN_REL_CREATE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# ── graph.rel.inspect ─────────────────────────────────────────────────────────

GRAPH_FN_REL_INSPECT = "graph.rel.inspect"

def inspect_relationships(
    node_label: str,
    node_match: dict,
    rel_type: str = None,
    direction: str = "either",  # "incoming" | "outgoing" | "either"
    session=None,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """
    Return all relationships on a node, optionally filtered by type and direction.
    Read-only — no VALID_REL_TYPES check (inspect is for discovery).

    node_label:  Label of the node to inspect  e.g. 'Todo'
    node_match:  Property dict to identify node  e.g. {'todo-id': 'todo-123'}
    rel_type:    Optional — filter to this relationship type
    direction:   'incoming' | 'outgoing' | 'either' (default)
    """
    if log_call:
        log.call(GRAPH_FN_REL_INSPECT, reason=reason, detail=
            f"{node_label}{node_match} rel_type={rel_type} direction={direction}"
        )

    if not node_label or not node_match:
        return {"error": "node_label and node_match are required"}
    if direction not in ("incoming", "outgoing", "either"):
        return {"error": f"direction must be 'incoming', 'outgoing', or 'either'"}

    def _param_key(prefix: str, k: str) -> str:
        return f"{prefix}_{k.replace('-', '_').replace('.', '_')}"

    node_conditions = " AND ".join(
        f"n.`{k}` = ${_param_key('n', k)}" for k in node_match
    )
    params = {_param_key('n', k): v for k, v in node_match.items()}

    rel_filter = f":{rel_type}" if rel_type else ""

    if direction == "incoming":
        pattern = f"(other)-[r{rel_filter}]->(n)"
        other_role = "source"
    elif direction == "outgoing":
        pattern = f"(n)-[r{rel_filter}]->(other)"
        other_role = "target"
    else:
        pattern = f"(other)-[r{rel_filter}]-(n)"
        other_role = "either"

    cypher = f"""
        MATCH (n:{node_label})
        WHERE {node_conditions}
        OPTIONAL MATCH {pattern}
        RETURN
            type(r)            AS rel_type,
            '{other_role}'     AS other_role,
            labels(other)      AS other_labels,
            properties(other)  AS other_properties,
            properties(r)      AS rel_properties,
            startNode(r) = n   AS n_is_source
    """

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run(cypher, **params)
        relationships = []
        for record in result:
            if record["rel_type"] is None:
                continue  # OPTIONAL MATCH found no relationships
            rel_direction = "outgoing" if record["n_is_source"] else "incoming"
            relationships.append({
                "rel_type":         record["rel_type"],
                "direction":        rel_direction,
                "other_labels":     list(record["other_labels"]) if record["other_labels"] else [],
                "other_properties": _serialize_props(dict(record["other_properties"]) if record["other_properties"] else {}),
                "rel_properties":   _serialize_props(dict(record["rel_properties"]) if record["rel_properties"] else {}),
            })
        return {
            "node_label": node_label,
            "node_match": node_match,
            "count":      len(relationships),
            "relationships": relationships,
        }
    except Exception as e:
        log.error(GRAPH_FN_REL_INSPECT, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# ── graph.rel.delete ─────────────────────────────────────────────────────────

GRAPH_FN_REL_DELETE = "graph.rel.delete"

def delete_relationship(
    source_label: str,
    source_match: dict,
    target_label: str,
    target_match: dict,
    rel_type: str,
    session=None,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """
    Delete a relationship between two nodes.
    rel_type must be in VALID_REL_TYPES.
    Returns count of deleted relationships.
    """
    if log_call:
        log.call(GRAPH_FN_REL_DELETE, reason=reason, detail=
            f"{source_label}{source_match} -[{rel_type}]-> {target_label}{target_match}"
        )

    if rel_type not in VALID_REL_TYPES:
        msg = f"Invalid rel_type '{rel_type}'. Valid types: {VALID_REL_TYPES}"
        log.error(GRAPH_FN_REL_DELETE, reason=reason, detail=msg)
        return {"error": msg}

    if not source_label or not source_match:
        return {"error": "source_label and source_match are required"}
    if not target_label or not target_match:
        return {"error": "target_label and target_match are required"}

    def _param_key(prefix: str, k: str) -> str:
        return f"{prefix}_{k.replace('-', '_').replace('.', '_')}"

    source_conditions = " AND ".join(
        f"source.`{k}` = ${_param_key('src', k)}" for k in source_match
    )
    target_conditions = " AND ".join(
        f"target.`{k}` = ${_param_key('tgt', k)}" for k in target_match
    )

    params = {}
    for k, v in source_match.items():
        params[_param_key('src', k)] = v
    for k, v in target_match.items():
        params[_param_key('tgt', k)] = v

    cypher = f"""
        MATCH (source:{source_label})-[r:{rel_type}]->(target:{target_label})
        WHERE {source_conditions} AND {target_conditions}
        DELETE r
        RETURN count(r) AS deleted
    """

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        result = session.run(cypher, **params)
        record = result.single()
        deleted = record["deleted"] if record else 0
        return {"status": "ok", "deleted": deleted}
    except Exception as e:
        log.error(GRAPH_FN_REL_DELETE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


# ── graph.rel.reroute ─────────────────────────────────────────────────────────

GRAPH_FN_REL_REROUTE = "graph.rel.reroute"
LOG_SUBCALLS = False  # reroute logs the full picture; suppress noisy sub-call entries

def reroute_relationship(
    fixed_label: str,
    fixed_match: dict,
    old_label: str,
    old_match: dict,
    new_label: str,
    new_match: dict,
    rel_type: str,
    direction: str = "incoming",  # relative to fixed node: 'incoming' = (other)-[r]->(fixed)
    session=None,
    reason: str = "",
    log_call: bool = True,
) -> dict:
    """
    Move a relationship from one node to another, keeping the fixed end unchanged.
    Calls delete_relationship + create_relationship in the same session.
    rel_type must be in VALID_REL_TYPES.

    fixed_label/match:  The node that stays put (e.g. Todo)
    old_label/match:    Current other end to detach from (e.g. old Persona)
    new_label/match:    New other end to wire to (e.g. new Persona or User)
    direction:          Relative to fixed node — 'incoming' = (other)-[r]->(fixed)
                                                  'outgoing' = (fixed)-[r]->(other)
    """
    if log_call:
        log.call(GRAPH_FN_REL_REROUTE, reason=reason, detail=
            f"{rel_type} on {fixed_label}{fixed_match}: {old_label}{old_match} -> {new_label}{new_match}"
        )

    if rel_type not in VALID_REL_TYPES:
        msg = f"Invalid rel_type '{rel_type}'. Valid types: {VALID_REL_TYPES}"
        log.error(GRAPH_FN_REL_REROUTE, reason=reason, detail=msg)
        return {"error": msg}
    if direction not in ("incoming", "outgoing"):
        return {"error": "direction must be 'incoming' or 'outgoing'"}

    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()

        # Delete old relationship
        if direction == "incoming":
            del_result = delete_relationship(
                source_label=old_label, source_match=old_match,
                target_label=fixed_label, target_match=fixed_match,
                rel_type=rel_type, session=session, reason=reason, log_call=LOG_SUBCALLS,
            )
        else:
            del_result = delete_relationship(
                source_label=fixed_label, source_match=fixed_match,
                target_label=old_label, target_match=old_match,
                rel_type=rel_type, session=session, reason=reason, log_call=LOG_SUBCALLS,
            )
        if "error" in del_result:
            return {"error": f"delete failed: {del_result['error']}"}

        # Create new relationship
        if direction == "incoming":
            create_result = create_relationship(
                source_label=new_label, source_match=new_match,
                target_label=fixed_label, target_match=fixed_match,
                rel_type=rel_type, session=session, reason=reason, log_call=LOG_SUBCALLS,
            )
        else:
            create_result = create_relationship(
                source_label=fixed_label, source_match=fixed_match,
                target_label=new_label, target_match=new_match,
                rel_type=rel_type, session=session, reason=reason, log_call=LOG_SUBCALLS,
            )
        if "error" in create_result:
            return {"error": f"create failed: {create_result['error']}"}

        return {
            "status": "ok",
            "rel_type": rel_type,
            "fixed": {"label": fixed_label, "match": fixed_match},
            "old": {"label": old_label, "match": old_match},
            "new": {"label": new_label, "match": new_match},
            "deleted": del_result.get("deleted", 0),
        }
    except Exception as e:
        log.error(GRAPH_FN_REL_REROUTE, reason=reason, detail=str(e))
        return {"error": str(e)}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)
