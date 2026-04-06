#!/usr/bin/env python3
"""
Bot Creator

Convenience tool to create both BotFunction node and Python skeleton in one command.

Usage:
    python create_bot.py vera.todos.create \\
        --module bots.db.vera \\
        --description "Create a new todo" \\
        --param description:string:required \\
        --param priority:string:optional \\
        --param owner:string:optional
    
    python create_bot.py vera.calendar.sync \\
        --module bots.db.vera \\
        --description "Sync calendar events to todos" \\
        --param calendar_id:string:required \\
        --param color_filter:string:optional \\
        --param reason:string:optional
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.neo4j_service import get_session

def parse_param(param_str: str) -> dict:
    """Parse parameter string: name:type:required/optional"""
    parts = param_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid param format: {param_str}. Use name:type:required/optional")
    
    name, param_type, required = parts
    
    type_desc_map = {
        'string': 'String value',
        'integer': 'Integer value',
        'number': 'Numeric value',
        'boolean': 'Boolean value',
        'object': 'Object/dict value',
        'array': 'Array/list value'
    }
    
    return {
        'name': name,
        'type': param_type,
        'required': required.lower() == 'required',
        'description': type_desc_map.get(param_type, 'Value')
    }

def generate_params_schema(params: list) -> dict:
    """Generate JSON schema from parameter definitions."""
    properties = {}
    required = []
    
    # Always include session, reason, log_call
    properties['session'] = {
        'type': 'object',
        'description': 'Neo4j session'
    }
    required.append('session')
    
    for param in params:
        properties[param['name']] = {
            'type': param['type'],
            'description': param['description']
        }
        if param['required']:
            required.append(param['name'])
    
    # Always add optional params
    properties['reason'] = {
        'type': 'string',
        'description': 'Why this operation is happening'
    }
    properties['log_call'] = {
        'type': 'boolean',
        'description': 'Whether to log this call'
    }
    
    return {
        'type': 'object',
        'properties': properties,
        'required': required
    }

def create_bot_node(bot_id: str, module: str, description: str, params_schema: dict) -> bool:
    """Create BotFunction node in Neo4j."""
    # Derive function name from bot_id
    function_name = bot_id.split('.')[-1]
    
    session = get_session().__enter__()
    try:
        session.run("""
            CREATE (bf:BotFunction {
                `bot-id`: $bot_id,
                module: $module,
                function: $function,
                use_case: $description,
                params: $params,
                returns: 'dict',
                requires: ['neo4j'],
                registered: datetime()
            })
        """, bot_id=bot_id, module=module, function=function_name,
             description=description, params=json.dumps(params_schema))
        
        print(f"✓ Created BotFunction node: {bot_id}")
        return True
    except Exception as e:
        print(f"✗ Failed to create node: {e}")
        return False
    finally:
        session.__exit__(None, None, None)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    bot_id = sys.argv[1]
    
    # Parse arguments
    module = None
    description = None
    params = []
    
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == '--module':
            module = sys.argv[i + 1]
            i += 2
        elif arg == '--description':
            description = sys.argv[i + 1]
            i += 2
        elif arg == '--param':
            param = parse_param(sys.argv[i + 1])
            params.append(param)
            i += 2
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
    
    if not module:
        print("ERROR: --module required")
        sys.exit(1)
    
    if not description:
        print("ERROR: --description required")
        sys.exit(1)
    
    print("="*80)
    print(f"Creating bot: {bot_id}")
    print("="*80)
    print(f"Module: {module}")
    print(f"Description: {description}")
    print(f"Parameters: {len(params)}")
    for param in params:
        req_str = "required" if param['required'] else "optional"
        print(f"  - {param['name']}: {param['type']} ({req_str})")
    print()
    
    # Generate schema
    params_schema = generate_params_schema(params)
    
    print("Generated schema:")
    print(json.dumps(params_schema, indent=2))
    print()
    
    # Confirm
    response = input("Create this bot? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        sys.exit(0)
    
    # Create node
    if not create_bot_node(bot_id, module, description, params_schema):
        sys.exit(1)
    
    # Generate skeleton
    print("\nGenerating Python skeleton...")
    print("Run: python generate_bot.py", bot_id)
    
    # Optionally run generate_bot.py
    response = input("\nGenerate skeleton now? (y/n): ")
    if response.lower() == 'y':
        import subprocess
        subprocess.run([sys.executable, 'app/chats/generate_bot.py', bot_id])

if __name__ == '__main__':
    main()
