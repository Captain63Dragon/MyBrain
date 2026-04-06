#!/usr/bin/env python3
"""
Bot Skeleton Generator

Generates Python function skeletons from BotFunction nodes in Neo4j.
Preserves business logic between === BUSINESS LOGIC START/END === markers.

Usage:
    python generate_bot.py vera.todos.update
    python generate_bot.py vera.todos.update --regenerate
    python generate_bot.py vera.todos.create --output bots/db/vera.py
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.neo4j_service import get_session

def get_bot_definition(bot_id: str) -> dict:
    """Query Neo4j for BotFunction node."""
    session = get_session().__enter__()
    try:
        result = session.run("""
            MATCH (bf:BotFunction {`bot-id`: $bot_id})
            RETURN bf.`bot-id` AS bot_id,
                   bf.module AS module,
                   bf.function AS function,
                   bf.use_case AS use_case,
                   bf.params AS params,
                   bf.returns AS returns
        """, bot_id=bot_id)
        
        record = result.single()
        if not record:
            return None
        
        return {
            'bot_id': record['bot_id'],
            'module': record['module'],
            'function': record['function'],
            'use_case': record['use_case'],
            'params': json.loads(record['params']),
            'returns': record['returns']
        }
    finally:
        session.__exit__(None, None, None)

def parse_params_schema(params_schema: dict) -> dict:
    """Parse JSON schema into function signature components."""
    properties = params_schema.get('properties', {})
    required = set(params_schema.get('required', []))
    
    signature_params = []
    
    for param_name, param_def in properties.items():
        param_type = param_def.get('type', 'Any')
        
        # Map JSON schema types to Python types
        type_map = {
            'string': 'str',
            'number': 'float',
            'integer': 'int',
            'boolean': 'bool',
            'object': 'dict',
            'array': 'list'
        }
        
        py_type = type_map.get(param_type, 'Any')
        
        # Build parameter with type hint and default
        if param_name in required:
            if param_name == 'session':
                # Session is special - optional None default
                signature_params.append(f"{param_name}: {py_type} = None")
            else:
                # Required params without defaults
                signature_params.append(f"{param_name}: {py_type} = None")
        else:
            # Optional params with defaults
            if py_type == 'str':
                default = '""'
            elif py_type == 'bool':
                default = 'True' if param_name == 'log_call' else 'False'
            elif py_type == 'dict':
                default = 'None'
            elif py_type == 'list':
                default = 'None'
            else:
                default = 'None'
            
            signature_params.append(f"{param_name}: {py_type} = {default}")
    
    return {
        'params': signature_params,
        'required': required,
        'properties': properties
    }

def generate_function_skeleton(bot_def: dict, preserve_logic: str = None) -> str:
    """Generate Python function skeleton with boilerplate."""
    
    bot_id = bot_def['bot_id']
    function_name = bot_def['function']
    use_case = bot_def['use_case']
    params_schema = bot_def['params']
    returns = bot_def['returns']
    
    # Parse params
    parsed = parse_params_schema(params_schema)
    signature = ', '.join(parsed['params'])
    
    # Generate constant name
    const_name = f"{bot_def['module'].split('.')[-1].upper()}_FN_{function_name.upper()}"
    
    # Build docstring with parameter descriptions
    param_docs = []
    for param_name, param_def in parsed['properties'].items():
        desc = param_def.get('description', '')
        required = 'Required' if param_name in parsed['required'] else 'Optional'
        param_docs.append(f"    {param_name}: {desc} ({required})")
    
    param_section = '\n'.join(param_docs) if param_docs else '    None'
    
    # Generate validation for required params
    required_params = [p for p in parsed['required'] if p != 'session']
    if required_params:
        checks = ' or '.join([f'not {p}' for p in required_params])
        missing_list = ', '.join(required_params)
        validation_block = f'''
    # AUTO-GENERATED: Validation
    if {checks}:
        log.error({const_name}, reason=reason, detail="Missing required: {missing_list}")
        return {{"error": "Missing required parameters: {missing_list}"}}
'''
    else:
        validation_block = ''
    
    # Business logic section
    if preserve_logic:
        business_logic = preserve_logic
    else:
        business_logic = '''
        # TODO: Implement Cypher query here
        result = session.run("""
            -- Your Cypher query
            MATCH (n) RETURN n LIMIT 1
        """)
        
        # TODO: Process result
        return {"status": "not_implemented"}
'''
    
    # Generate skeleton
    skeleton = f'''
# ── {bot_id} {'─' * (80 - len(bot_id) - 4)}

{const_name} = "{bot_id}"

def {function_name}({signature}) -> {returns}:
    """
    {use_case}
    
    AUTO-GENERATED from BotFunction registry.
    Last generated: {datetime.utcnow().isoformat()}Z
    
    Parameters:
{param_section}
    
    Returns:
        {returns}
    """
    # AUTO-GENERATED: Logging
    if log_call and reason:
        log.call({const_name}, reason=reason)
{validation_block}
    # AUTO-GENERATED: Session management
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        
        # === BUSINESS LOGIC START ===
        # Developer implements domain logic here
        # This section is preserved across regenerations
{business_logic}
        # === BUSINESS LOGIC END ===
        
    except Exception as e:
        log.error({const_name}, reason=reason, detail=str(e))
        return {{"error": str(e)}}
    finally:
        if _owned and session:
            session.__exit__(None, None, None)
'''
    
    return skeleton

def extract_business_logic(existing_code: str, function_name: str) -> str:
    """Extract business logic from existing function."""
    # Find the function
    pattern = rf'def {function_name}\([^)]*\).*?(?=\ndef |\Z)'
    match = re.search(pattern, existing_code, re.DOTALL)
    
    if not match:
        return None
    
    function_body = match.group(0)
    
    # Extract between markers
    start_marker = '# === BUSINESS LOGIC START ==='
    end_marker = '# === BUSINESS LOGIC END ==='
    
    start_idx = function_body.find(start_marker)
    end_idx = function_body.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        return None
    
    # Get content between markers
    logic = function_body[start_idx + len(start_marker):end_idx].strip()
    
    return logic

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_bot.py <bot-id> [--regenerate] [--output <file>]")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    regenerate = '--regenerate' in sys.argv
    
    # Get output file
    if '--output' in sys.argv:
        output_idx = sys.argv.index('--output')
        output_file = Path(sys.argv[output_idx + 1])
    else:
        output_file = None
    
    print(f"Generating skeleton for bot: {bot_id}")
    
    # Get bot definition from Neo4j
    bot_def = get_bot_definition(bot_id)
    if not bot_def:
        print(f"ERROR: Bot not found in registry: {bot_id}")
        sys.exit(1)
    
    print(f"Found bot: {bot_def['function']} in {bot_def['module']}")
    
    # Determine output file
    if not output_file:
        # Derive from module path
        module_parts = bot_def['module'].split('.')
        output_file = Path('app') / '/'.join(module_parts[1:]) / f"{module_parts[-1]}.py"
    
    print(f"Output file: {output_file}")
    
    # If regenerating, try to preserve business logic
    preserved_logic = None
    if regenerate and output_file.exists():
        print("Regenerating - preserving business logic...")
        existing_code = output_file.read_text()
        preserved_logic = extract_business_logic(existing_code, bot_def['function'])
        
        if preserved_logic:
            print("✓ Business logic preserved")
        else:
            print("⚠ No business logic markers found - generating fresh")
    
    # Generate skeleton
    skeleton = generate_function_skeleton(bot_def, preserved_logic)
    
    print("\n" + "="*80)
    print("GENERATED SKELETON:")
    print("="*80)
    print(skeleton)
    print("="*80)
    
    # Ask to append
    response = input("\nAppend this to the output file? (y/n): ")
    if response.lower() == 'y':
        with open(output_file, 'a') as f:
            f.write(skeleton)
        print(f"✓ Appended to {output_file}")
    else:
        print("Cancelled")

if __name__ == '__main__':
    main()
