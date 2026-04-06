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
    graph.rel.create  →  create_relationship()

Planned (see Feature nodes):
    graph.rel.inspect
    graph.rel.check
    graph.rel.reroute
    graph.rel.delete
    graph.integrity.duplicates
    graph.integrity.deduplicate
    graph.integrity.audit
"""

from app.bots import bot_logger as log
from app.services.neo4j_service import get_session

REQUIRES = {'neo4j'}

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

    _owned = True
    session = None
    try:
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
