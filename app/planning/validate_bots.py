#!/usr/bin/env python3
"""
Bot Registry Validator

Validates that Python bot functions match their BotFunction node definitions in Neo4j.

Usage:
    python validate_bots.py
    python validate_bots.py --bot vera.todos.update
    python validate_bots.py --verbose
"""

import sys
import json
import ast
import inspect
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.neo4j_service import get_session

def get_all_bot_definitions() -> List[dict]:
    """Query Neo4j for all BotFunction nodes."""
    session = get_session().__enter__()
    try:
        result = session.run("""
            MATCH (bf:BotFunction)
            RETURN bf.`bot-id` AS bot_id,
                   bf.module AS module,
                   bf.function AS function,
                   bf.params AS params
            ORDER BY bf.`bot-id`
        """)
        
        bots = []
        for record in result:
            bots.append({
                'bot_id': record['bot_id'],
                'module': record['module'],
                'function': record['function'],
                'params': json.loads(record['params'])
            })
        return bots
    finally:
        session.__exit__(None, None, None)

def load_module_functions(module_path: str) -> Dict[str, inspect.Signature]:
    """Load function signatures from a Python module."""
    # Convert module path to file path
    parts = module_path.split('.')
    file_path = Path('app') / '/'.join(parts[1:]) / f"{parts[-1]}.py"
    
    if not file_path.exists():
        return {}
    
    # Parse the file with AST
    code = file_path.read_text()
    tree = ast.parse(code)
    
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Extract function signature
            params = []
            for arg in node.args.args:
                param_name = arg.arg
                # Try to extract type annotation
                type_hint = None
                if arg.annotation:
                    if isinstance(arg.annotation, ast.Name):
                        type_hint = arg.annotation.id
                    elif isinstance(arg.annotation, ast.Constant):
                        type_hint = str(arg.annotation.value)
                
                params.append((param_name, type_hint))
            
            functions[node.name] = params
    
    return functions

def validate_bot(bot_def: dict, module_functions: Dict) -> Tuple[bool, List[str]]:
    """Validate a single bot against its implementation."""
    errors = []
    
    function_name = bot_def['function']
    params_schema = bot_def['params']
    
    # Check if function exists
    if function_name not in module_functions:
        errors.append(f"Function '{function_name}' not found in module {bot_def['module']}")
        return False, errors
    
    # Get actual function parameters
    actual_params = dict(module_functions[function_name])
    
    # Get expected parameters from schema
    expected_properties = params_schema.get('properties', {})
    required_params = set(params_schema.get('required', []))
    
    # Check all expected params exist
    for param_name in expected_properties.keys():
        if param_name not in actual_params:
            errors.append(f"Missing parameter: {param_name}")
    
    # Check for extra params (warning only)
    for param_name in actual_params.keys():
        if param_name not in expected_properties:
            errors.append(f"WARNING: Extra parameter not in schema: {param_name}")
    
    # Check required parameters
    for req_param in required_params:
        if req_param not in actual_params:
            errors.append(f"Missing required parameter: {req_param}")
    
    # Type checking (if annotations present)
    type_map = {
        'string': 'str',
        'number': 'float',
        'integer': 'int',
        'boolean': 'bool',
        'object': 'dict',
        'array': 'list'
    }
    
    for param_name, param_def in expected_properties.items():
        if param_name in actual_params:
            expected_type = type_map.get(param_def.get('type'), None)
            actual_type = actual_params[param_name]
            
            if actual_type and expected_type and actual_type != expected_type:
                errors.append(f"Type mismatch for {param_name}: expected {expected_type}, got {actual_type}")
    
    return len(errors) == 0, errors

def main():
    verbose = '--verbose' in sys.argv
    specific_bot = None
    
    if '--bot' in sys.argv:
        bot_idx = sys.argv.index('--bot')
        specific_bot = sys.argv[bot_idx + 1]
    
    print("="*80)
    print("BOT REGISTRY VALIDATOR")
    print("="*80)
    
    # Get all bot definitions
    all_bots = get_all_bot_definitions()
    
    if specific_bot:
        all_bots = [b for b in all_bots if b['bot_id'] == specific_bot]
        if not all_bots:
            print(f"ERROR: Bot not found: {specific_bot}")
            sys.exit(1)
    
    print(f"\nValidating {len(all_bots)} bots...\n")
    
    # Group by module
    bots_by_module = {}
    for bot in all_bots:
        module = bot['module']
        if module not in bots_by_module:
            bots_by_module[module] = []
        bots_by_module[module].append(bot)
    
    total_errors = 0
    valid_count = 0
    
    for module, bots in bots_by_module.items():
        print(f"Module: {module}")
        
        # Load module functions
        module_functions = load_module_functions(module)
        
        if not module_functions:
            print(f"  ⚠ WARNING: Could not load module or no functions found")
            total_errors += len(bots)
            continue
        
        for bot in bots:
            is_valid, errors = validate_bot(bot, module_functions)
            
            if is_valid:
                print(f"  ✓ {bot['bot_id']}")
                valid_count += 1
            else:
                print(f"  ✗ {bot['bot_id']}")
                for error in errors:
                    print(f"      {error}")
                total_errors += 1
        
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total bots: {len(all_bots)}")
    print(f"Valid: {valid_count}")
    print(f"Errors: {total_errors}")
    
    if total_errors > 0:
        print("\n⚠ Validation failed. Run generate_bot.py to fix mismatches.")
        sys.exit(1)
    else:
        print("\n✓ All bots valid!")

if __name__ == '__main__':
    main()
