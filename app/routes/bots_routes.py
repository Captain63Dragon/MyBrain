import importlib
from flask import Blueprint, jsonify, request
from app.bots.db.vera import (
    get_pending_todos,
    get_friction_todos,
    get_unreviewed_filenodes,
    get_unsubmitted_r2hodo,
    get_pending_ideas,
    update_todo
)
from app.bots.db.rex import load_bot_registry
from app.services.neo4j_service import get_session

bots_bp = Blueprint('bots', __name__)

@bots_bp.route('/bots/list', methods=['GET'])
def list_bots():
    """List all registered bots - routes through bot execution for logging."""
    result = load_bot_registry(reason="Tool initialization - registry_query")
    return jsonify(result)
        
@bots_bp.route('/bots/vera/todos/pending', methods=['POST'])
def vera_todos_pending():
    """Get all pending todos."""
    data = request.get_json() or {}
    reason = data.get('reason', 'MCP call via bridge')
    result = get_pending_todos(reason=reason)
    return jsonify(result)

@bots_bp.route('/bots/vera/todos/friction', methods=['POST'])
def vera_todos_friction():
    """Get todos with friction."""
    data = request.get_json() or {}
    reason = data.get('reason', 'MCP call via bridge')
    friction_types = data.get('friction_types')
    result = get_friction_todos(friction_types=friction_types, reason=reason)
    return jsonify(result)

@bots_bp.route('/bots/vera/filenodes/unreviewed', methods=['POST'])
def vera_filenodes_unreviewed():
    """Get unreviewed FileNodes."""
    data = request.get_json() or {}
    reason = data.get('reason', 'MCP call via bridge')
    mfn_type = data.get('mfn_type')
    result = get_unreviewed_filenodes(mfn_type=mfn_type, reason=reason)
    return jsonify(result)

@bots_bp.route('/bots/vera/r2hodo/unsubmitted', methods=['POST'])
def vera_r2hodo_unsubmitted():
    """Get unsubmitted R2HOdo trips."""
    data = request.get_json() or {}
    reason = data.get('reason', 'MCP call via bridge')
    result = get_unsubmitted_r2hodo(reason=reason)
    return jsonify(result)

@bots_bp.route('/bots/vera/ideas/pending', methods=['POST'])
def vera_ideas_pending():
    """Get pending Ideas."""
    data = request.get_json() or {}
    reason = data.get('reason', 'MCP call via bridge')
    result = get_pending_ideas(reason=reason)
    return jsonify(result)

@bots_bp.route('/bots/vera/todos/update', methods=['POST'])
def vera_todos_update():
    """Update a todo with new values."""
    data = request.get_json() or {}
    todo_id = data.get('todo_id')
    updates = data.get('updates', {})
    reason = data.get('reason', 'MCP call via bridge')
    log_call = data.get('log_call', True)
    result = update_todo(todo_id=todo_id, updates=updates, reason=reason, log_call=log_call)
    return jsonify(result)

@bots_bp.route('/bots/execute', methods=['POST'])
def execute_bot():
    """Generic bot executor - dynamically routes to any registered bot."""
    data = request.get_json() or {}
    bot_id = data.get('bot_id')
    params = data.get('params', {})
    
    if not bot_id:
        return jsonify({"error": "bot_id required"}), 400
    
    # Query Neo4j for bot metadata
    with get_session() as session:
        result = session.run("""
            MATCH (b:BotFunction {`bot-id`: $bot_id})
            RETURN b.module AS module, b.function AS function
        """, bot_id=bot_id)
        record = result.single()
        
        if not record:
            return jsonify({"error": f"Bot not found: {bot_id}"}), 404
        
        module_path = record['module']
        function_name = record['function']
    
    if not module_path or not function_name:
        return jsonify({"error": f"Bot {bot_id} missing module or function metadata"}), 500
    
    try:
        # Dynamic import and execution
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        params.pop('persona', None)  # Strip bridge-injected metadata — bot functions don't accept this
        result = func(**params)
        return jsonify(result)
    except ImportError as e:
        return jsonify({"error": f"Failed to import {module_path}: {str(e)}"}), 500
    except AttributeError as e:
        return jsonify({"error": f"Function {function_name} not found in {module_path}: {str(e)}"}), 500
    except TypeError as e:
        return jsonify({"error": f"Invalid parameters for {bot_id}: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Execution failed for {bot_id}: {str(e)}"}), 500
