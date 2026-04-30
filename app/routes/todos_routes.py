# app/routes/todos_routes.py

from flask import Blueprint, jsonify, request
from app.bots.db.vera import get_todos, update_todo
from app.services.neo4j_service import get_session
from app.services.api_service import mark_dirty
from datetime import datetime, timezone

todos_bp = Blueprint('todos', __name__, url_prefix='/todos')


@todos_bp.route('/owners', methods=['GET'])
def get_owners():
    """Return user + all Persona names for owner filter dropdown."""
    with get_session() as session:
        result = session.run("MATCH (p:Persona) RETURN p.name AS name ORDER BY p.name")
        personas = [r['name'] for r in result if r['name']]
    return jsonify(['user'] + personas)


@todos_bp.route('/score-policies', methods=['GET'])
def get_score_policies():
    """Return list of available ScoringPolicy nodes for sort dropdown."""
    with get_session() as session:
        result = session.run(
            "MATCH (p:ScoringPolicy) RETURN p.`policy_id` AS policy_id, p.description AS description ORDER BY p.version"
        )
        policies = [{'policy_id': r['policy_id'], 'description': r['description']} for r in result]
    return jsonify(policies)


@todos_bp.route('/query', methods=['POST'])
def query_todos():
    from app.services.scoring_service import get_scoring_policy, score_todo

    data = request.get_json() or {}
    owner = data.get('owner')
    now = datetime.now(timezone.utc)

    result = get_todos(
        status=data.get('status', 'active'),
        priority=data.get('priority'),
        exclude=data.get('exclude'),
        day_range=data.get('day_range'),
        timestamp=data.get('timestamp'),
        limit=data.get('limit'),
        include_notes=data.get('include_notes', True),
        reason='ui-todos-query',
        log_call=False
    )
    if owner:
        result = [t for t in result if t.get('owner') == owner]

    # Score every todo — always, regardless of sort mode
    with get_session() as session:
        policy = get_scoring_policy(session)

    if policy:
        for todo in result:
            score, nudge = score_todo(todo, policy, now)
            todo['score'] = score
            todo['nudge'] = nudge
    else:
        for todo in result:
            todo['score'] = None
            todo['nudge'] = False

    return jsonify(result)


@todos_bp.route('/update', methods=['POST'])
def update_todo_route():
    data = request.get_json() or {}
    todo_id = data.get('todo_id')
    updates = data.get('updates', {})
    if not todo_id or not updates:
        return jsonify({'error': 'todo_id and updates required'}), 400
    result = update_todo(
        todo_id=todo_id,
        updates=updates,
        reason='ui-todos-update',
        log_call=False
    )
    if 'error' not in result:
        mark_dirty()
    return jsonify(result)
