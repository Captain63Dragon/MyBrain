# app/bots/composite/rex.py
#
# Rex's composite bot library.
#
# These are orchestrator bots that coordinate system-level operations.

import os
import re
import json
from datetime import datetime
from pathlib import Path
from app.bots import bot_logger as log
from app.services.neo4j_service import get_session

# ── Capability declaration ────────────────────────────────────────────────────
REQUIRES = {'neo4j', 'filesystem'}


# ── rex.admin.register_bots ───────────────────────────────────────────────────

REX_FN_REGISTER_BOTS = "rex.admin.register_bots"

def register_bots(session=None, reason: str = "", log_call: bool = True) -> dict:
    """
    Called by: Rex
    Use case: Scan app/bots/ directory tree and sync BotFunction nodes to graph
    Library ID: rex.admin.register_bots
    Returns: {registered: int, updated: int, errors: list}
    
    Walks app/bots/ directory, parses bot files, and creates/updates
    (:BotFunction) nodes with metadata extracted from code and docstrings.
    """
    if log_call and reason:
        log.call(REX_FN_REGISTER_BOTS, reason=reason)
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        
        registered = 0
        updated = 0
        errors = []
        
        # Get project root (assuming this file is in app/bots/composite/)
        project_root = Path(__file__).parent.parent.parent.parent
        bots_dir = project_root / "app" / "bots"
        
        # Walk the bots directory
        for root, dirs, files in os.walk(bots_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for filename in files:
                # Only process .py files, skip __init__.py and this file
                if not filename.endswith('.py') or filename == '__init__.py' or filename == 'rex.py':
                    continue
                
                filepath = Path(root) / filename
                try:
                    # Extract bot metadata from file
                    bots_data = _parse_bot_file(filepath, bots_dir)
                    
                    for bot_data in bots_data:
                        # Serialize params JSON Schema to string for Neo4j storage
                        bot_data['params'] = json.dumps(bot_data['params'])
                        
                        # MERGE bot node
                        result = session.run("""
                            MERGE (b:BotFunction {`bot-id`: $bot_id})
                            SET b.module = $module,
                                b.function = $function,
                                b.requires = $requires,
                                b.use_case = $use_case,
                                b.params = $params,
                                b.returns = $returns,
                                b.registered = datetime()
                            RETURN b, 
                                   CASE WHEN b.registered IS NULL THEN 'created' ELSE 'updated' END AS action
                        """, **bot_data)
                        
                        record = result.single()
                        if record:
                            if record['action'] == 'created':
                                registered += 1
                            else:
                                updated += 1
                
                except Exception as e:
                    errors.append(f"{filepath.name}: {str(e)}")
        
        return {
            'registered': registered,
            'updated': updated,
            'errors': errors
        }
    
    except Exception as e:
        log.error(REX_FN_REGISTER_BOTS, reason=reason, detail=str(e))
        return {'registered': 0, 'updated': 0, 'errors': [str(e)]}
    
    finally:
        if _owned and session:
            session.__exit__(None, None, None)


def _py_type_to_json_schema(type_hint: str) -> dict:
    """
    Convert a Python type annotation string to a JSON Schema property object.

    Handles simple types, Optional/None unions, and basic generics (list[str]).
    Returns {} for ambiguous unions (e.g. str | list | None) - unconstrained
    is better than wrong.

    Internal params (session, log_call) should be stripped before calling this;
    they are never passed by callers and must not appear in the schema.
    """
    # Strip surrounding quotes and whitespace (type hints written as strings:
    # status: 'str | list | None' = ... )
    type_hint = type_hint.strip().strip("'\"")

    # Split union, drop None - we don't use JSON Schema nullable in this system
    parts = [p.strip() for p in type_hint.split('|') if p.strip().lower() != 'none']

    if not parts:
        return {}

    # Ambiguous union (more than one non-None type) - leave unconstrained
    if len(parts) > 1:
        return {}

    raw = parts[0].lower()

    # Handle generics: list[str], list[dict], etc.
    base = raw.split('[')[0].strip()

    TYPE_MAP = {
        'str':   'string',
        'int':   'integer',
        'float': 'number',
        'bool':  'boolean',
        'dict':  'object',
        'list':  'array',
    }

    json_type = TYPE_MAP.get(base)
    if json_type is None:
        return {}  # 'any' or unknown - unconstrained

    if base == 'list' and '[' in raw:
        inner_raw = raw[raw.index('[') + 1: raw.rindex(']')].strip()
        inner_json = TYPE_MAP.get(inner_raw)
        if inner_json:
            return {'type': 'array', 'items': {'type': inner_json}}

    return {'type': json_type}


# Params that are infrastructure - never exposed in the MCP tool schema.
_INTERNAL_PARAMS = {'session', 'log_call'}


def _parse_bot_file(filepath: Path, bots_dir: Path) -> list[dict]:
    """
    Parse a bot Python file and extract metadata for all bot functions.

    Produces a proper JSON Schema object for each bot's params field:
        {"type": "object", "required": [...], "properties": {...}}

    Rules:
    - All params captured (not just those with defaults).
    - Params without defaults are added to "required".
    - session and log_call are excluded - internal infrastructure.
    - Python type annotations are mapped to JSON Schema types.
    - Ambiguous unions (e.g. str | list | None) become {} (unconstrained).

    Bot-id constants must follow the naming convention:
        SOMETHING_FN_SOMETHING = "bot.id.here"   (standard)
        BOT_ID = "bot.id.here"                   (single-bot files)

    Returns list of bot metadata dicts, one per bot function found in file.
    """
    bots = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Derive module path from filepath
    # e.g., app/bots/db/vera.py -> app.bots.db.vera
    relative_path = filepath.relative_to(bots_dir.parent)
    module = str(relative_path.with_suffix('')).replace(os.sep, '.')

    # Find all bot-id constant definitions.
    # Matches: SOME_FN_CONSTANT = "bot.id"  (standard multi-bot files)
    #          BOT_ID = "bot.id"             (single-bot files like dispatch/iris.py)
    bot_id_pattern = r'^([A-Z0-9_]+_FN[A-Z0-9_]*|BOT_ID)\s*=\s*["\']([a-z.0-9_]+)["\']'
    bot_ids = re.findall(bot_id_pattern, content, re.MULTILINE)

    # For each bot-id, find its corresponding function
    for constant_name, bot_id in bot_ids:
        function_pattern = rf'{re.escape(constant_name)}.*?^def\s+(\w+)\s*\((.*?)\)\s*->\s*([^:]+):'
        match = re.search(function_pattern, content, re.MULTILINE | re.DOTALL)

        if not match:
            continue

        function_name = match.group(1)
        params_str = match.group(2)
        returns_str = match.group(3).strip()

        # Extract docstring - look for "Use case:" line
        docstring_pattern = rf'def\s+{re.escape(function_name)}.*?"""(.*?)"""'
        doc_match = re.search(docstring_pattern, content, re.DOTALL)

        use_case = ""
        if doc_match:
            docstring = doc_match.group(1)
            use_case_match = re.search(r'Use case:\s*(.+?)(?:\n|$)', docstring)
            if use_case_match:
                use_case = use_case_match.group(1).strip()

        # Build JSON Schema from parameter list.
        # Captures ALL params; tracks required (no default) vs optional (has default).
        properties = {}
        required = []

        if params_str:
            param_parts = [p.strip() for p in params_str.split(',') if p.strip()]
            for part in param_parts:
                has_default = '=' in part
                name_type_str = part.split('=')[0].strip()

                if ':' in name_type_str:
                    name = name_type_str.split(':')[0].strip()
                    type_hint = name_type_str.split(':', 1)[1].strip()
                else:
                    name = name_type_str.strip()
                    type_hint = 'any'

                if not name or name in _INTERNAL_PARAMS:
                    continue

                prop = _py_type_to_json_schema(type_hint)
                properties[name] = prop

                if not has_default:
                    required.append(name)

        input_schema = {'type': 'object', 'properties': properties}
        if required:
            input_schema['required'] = required

        # Find REQUIRES set in file (one per file)
        requires = []
        requires_match = re.search(r'REQUIRES\s*=\s*\{([^}]+)\}', content)
        if requires_match:
            requires_content = requires_match.group(1)
            requires = re.findall(r'["\']([^"\']+)["\']', requires_content)

        bots.append({
            'bot_id': bot_id,
            'module': module,
            'function': function_name,
            'requires': requires,
            'use_case': use_case,
            'params': input_schema,
            'returns': returns_str
        })

    return bots
