import importlib
from flask import Blueprint, jsonify, request
from app.bots.db.rex import load_bot_registry
from app.bots import bot_logger as log
from app.services.neo4j_service import get_session
from app.services.api_service import mark_dirty

bots_bp = Blueprint('bots', __name__)

@bots_bp.route('/bots/list', methods=['GET'])
def list_bots():
    """List all registered bots - routes through bot execution for logging."""
    result = load_bot_registry(reason="Tool initialization - registry_query", log_call=False)
    return jsonify(result)
        
@bots_bp.route('/bots/execute', methods=['POST'])
def execute_bot():
    """Generic bot executor - dynamically routes to any registered bot."""
    # Reset chain depth at the start of each request — ensures [0] for top-level calls
    log.reset_depth()

    data = request.get_json() or {}
    bot_id = data.get('bot_id')
    params = data.get('params', {})

    if not bot_id:
        return jsonify({"error": "bot_id required"}), 400

    # Detect origin before stripping persona
    # Bridge always injects persona — browser UI never does
    is_ui = 'persona' not in params
    params.pop('persona', None)
    if is_ui:
        params['log_call'] = False

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
        result = func(**params)

        # Post-execution: mark dirty + update call counters on BotFunction node
        mark_dirty()
        try:
            counter_field = 'ui_call_count'    if is_ui else 'persona_call_count'
            stamp_field   = 'ui_last_call'     if is_ui else 'persona_last_call'
            with get_session() as session:
                session.run(f"""
                    MATCH (b:BotFunction {{`bot-id`: $bot_id}})
                    SET b.{counter_field} = coalesce(b.{counter_field}, 0) + 1,
                        b.{stamp_field} = datetime()
                """, bot_id=bot_id)
        except Exception:
            pass  # Counter failure is non-fatal

        return jsonify(result)
    except ImportError as e:
        return jsonify({"error": f"Failed to import {module_path}: {str(e)}"}), 500
    except AttributeError as e:
        return jsonify({"error": f"Function {function_name} not found in {module_path}: {str(e)}"}), 500
    except TypeError as e:
        return jsonify({"error": f"Invalid parameters for {bot_id}: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Execution failed for {bot_id}: {str(e)}"}), 500
