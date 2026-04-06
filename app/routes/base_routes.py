from flask import Blueprint, jsonify, request
from app.services.neo4j_service import get_all_mfns, ping_neo4j

base_bp = Blueprint('base', __name__)

@base_bp.route('/mfn/list', methods=['GET'])
def list_mfns():
    return jsonify(get_all_mfns())

@base_bp.route('/ping', methods=['GET'])
def ping():
    neo4j_time = ping_neo4j()
    neo4j_status = 'ok' if neo4j_time else 'error'
    return jsonify({
        'status': neo4j_status,
        'neo4j': neo4j_status,
        'server_time': neo4j_time
    })

@base_bp.route('/bots/register', methods=['POST'])
def register_bots():
    """Register all bots in app/bots/ directory to graph."""
    from app.bots.composite.rex import register_bots as do_register
    
    data = request.get_json() or {}
    reason = data.get('reason', 'manual registration via API')
    
    result = do_register(reason=reason)
    return jsonify(result)

# ── Vera's bot endpoints ──────────────────────────────────────────────────────

@base_bp.route('/bots/vera/todos/pending', methods=['POST'])
def vera_todos_pending():
    """Get all pending todos."""
    from app.bots.db.vera import get_pending_todos
    
    data = request.get_json() or {}
    reason = data.get('reason', '')
    
    result = get_pending_todos(reason=reason)
    return jsonify(result)

@base_bp.route('/bots/vera/todos/friction', methods=['POST'])
def vera_todos_friction():
    """Get todos with friction."""
    from app.bots.db.vera import get_friction_todos
    
    data = request.get_json() or {}
    reason = data.get('reason', '')
    friction_types = data.get('friction_types')
    
    result = get_friction_todos(friction_types=friction_types, reason=reason)
    return jsonify(result)

@base_bp.route('/bots/vera/filenodes/unreviewed', methods=['POST'])
def vera_filenodes_unreviewed():
    """Get unreviewed FileNodes."""
    from app.bots.db.vera import get_unreviewed_filenodes
    
    data = request.get_json() or {}
    reason = data.get('reason', '')
    mfn_type = data.get('mfn_type')
    
    result = get_unreviewed_filenodes(mfn_type=mfn_type, reason=reason)
    return jsonify(result)

@base_bp.route('/bots/vera/r2hodo/unsubmitted', methods=['POST'])
def vera_r2hodo_unsubmitted():
    """Get unsubmitted R2HOdo trips."""
    from app.bots.db.vera import get_unsubmitted_r2hodo
    
    data = request.get_json() or {}
    reason = data.get('reason', '')
    
    result = get_unsubmitted_r2hodo(reason=reason)
    return jsonify(result)

@base_bp.route('/bots/vera/ideas/pending', methods=['POST'])
def vera_ideas_pending():
    """Get pending ideas."""
    from app.bots.db.vera import get_pending_ideas
    
    data = request.get_json() or {}
    reason = data.get('reason', '')
    
    result = get_pending_ideas(reason=reason)
    return jsonify(result)
