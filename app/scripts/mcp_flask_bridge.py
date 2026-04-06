"""
MCP Flask Bridge with Heavy Instrumentation
"""
import sys
import os
import json
import requests
import argparse
import traceback
from datetime import datetime, timezone
from pathlib import Path
from mcp import Tool, stdio_server
from mcp.server import Server

# Logging to file
LOG_FILE = Path(__file__).parent.parent / "logs" / "mcp_bridge.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")
            f.flush()
    except Exception as e:
        sys.stderr.write(f"Log error: {e}\n")

def log_json(label, obj):
    """Log a JSON object with pretty formatting."""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {label}\n")
            f.write(json.dumps(obj, indent=2) + "\n")
            f.flush()
    except Exception as e:
        sys.stderr.write(f"Log error: {e}\n")

# Parse persona argument before logging starts
parser = argparse.ArgumentParser()
parser.add_argument('--persona', required=True, choices=['vera', 'iris', 'rex', 'ash'],
                    help='Persona to filter bots for')
args = parser.parse_args()
PERSONA = args.persona

PID  = os.getpid()
PPID = os.getppid()
log(f"=== MCP Bridge Starting | persona={PERSONA.upper()} | pid={PID} | ppid={PPID} | argv={sys.argv} ===")

FLASK_BASE = "http://localhost:5000"
ALLOWED_BUSCARD_ACTIONS = {"discovery", "move", "archive", "insitu_copy", "copy_master_source", "copy_master_target"}
ALLOWED_R2HODO_ACTIONS  = {"discovery"}

def flask_get(path):
    try:
        return requests.get(f"{FLASK_BASE}{path}", timeout=5).json()
    except Exception as e:
        return {"error": str(e)}

def flask_post(path, payload):
    try:
        return requests.post(f"{FLASK_BASE}{path}", json=payload, timeout=10).json()
    except Exception as e:
        return {"error": str(e)}

def send(obj):
    # log_json("SENDING TO DESKTOP:", obj)
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def tool_result(call_id, content):
    send({"jsonrpc": "2.0", "id": call_id, "result": {"content": [{"type": "text", "text": json.dumps(content, indent=2)}]}})

def tool_error(call_id, message):
    send({"jsonrpc": "2.0", "id": call_id, "error": {"code": -32000, "message": message}})

# Static tool assignments - which persona gets which tool
# Use 'all' for universal tools (e.g., ping)
# Tools not listed here are deprecated and won't be loaded
# Extra bot prefixes per persona — loaded in addition to the persona's own prefix.
# Use this for shared namespaces that belong to a specific bridge, not all bridges.
PERSONA_EXTRA_PREFIXES = {
    'iris': ['graph.'],
}

STATIC_TOOL_ASSIGNMENTS = {
    'ping': 'all',
    'mfn_list': 'iris',
    'bots_register': 'iris',
    'buscard_dispatch': 'iris',
    'r2hodo_dispatch': 'iris'
    # TODO: change iris to rex when migrating tools 
    # buscard_process: DEPRECATED - not assigned to anyone
    # r2hodo_process: DEPRECATED - not assigned to anyone
}

# Static tools definitions
STATIC_TOOLS = [
    {"name": "ping", "description": "Ping Flask + Neo4j", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "mfn_list", "description": "List MFN types", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "bots_register", "description": "Register bots", "inputSchema": {"type": "object", "properties": {"reason": {"type": "string"}}}},
    {"name": "buscard_dispatch", "description": "Dispatch buscard", "inputSchema": {"type": "object", "required": ["action", "mfn_id"], "properties": {"action": {"type": "string", "enum": ["discovery", "move", "archive", "insitu_copy", "copy_master_source", "copy_master_target"]}, "mfn_id": {"type": "string"}, "source": {"type": "string"}, "target": {"type": "string"}, "node_id": {"type": "string"}, "patterns": {"type": "array"}}}},
    {"name": "buscard_process", "description": "Process buscards", "inputSchema": {"type": "object", "required": ["action"], "properties": {"action": {"type": "string", "enum": ["discovery", "copy", "move"]}}}},
    {"name": "r2hodo_dispatch", "description": "Dispatch R2HOdo", "inputSchema": {"type": "object", "required": ["action", "mfn_id"], "properties": {"action": {"type": "string", "enum": ["discovery"]}, "mfn_id": {"type": "string"}, "source": {"type": "string"}, "patterns": {"type": "array"}}}},
    {"name": "r2hodo_process", "description": "Process R2HOdo", "inputSchema": {"type": "object", "required": ["action"], "properties": {"action": {"type": "string", "enum": ["discovery"]}}}}
]

TOOLS = []  # List[Tool]
BOT_TOOLS = []


def tool_from_dict(defn):
    return Tool(
        name=defn["name"],
        title=defn.get("name"),
        description=defn.get("description"),
        inputSchema=defn.get("inputSchema", {"type": "object", "properties": {}}),
    )

def load_bot_tools_from_registry():
    """Query Neo4j for BotFunction nodes and dynamically generate MCP tools."""
    log(f"Loading bot tools from Neo4j registry for persona: {PERSONA}")
    
    try:
        response = flask_get("/bots/list")
        # log_json("Flask /bots/list response:", response)
        
        if "error" in response:
            log(f"Failed to load bots from registry: {response['error']}")
            log("Continuing with static tools only")
            return []
        
        bots = response.get("bots", [])
        log(f"Found {len(bots)} total bots in registry")
        
        # Filter bots by persona prefix + universal namespaces
        persona_prefix = f"{PERSONA}."
        extra_prefixes = PERSONA_EXTRA_PREFIXES.get(PERSONA, [])
        persona_bots = [
            b for b in bots
            if b.get("bot-id", "").startswith(persona_prefix)
            or any(b.get("bot-id", "").startswith(p) for p in extra_prefixes)
        ]
        log(f"Filtered to {len(persona_bots)} bots for {PERSONA}")
        
        dynamic_tools = []
        for bot in persona_bots:
            bot_id = bot.get("bot-id")

            if bot.get("deprecated"):
                log(f"  Skipping deprecated bot: {bot_id}")
                continue
            use_case = bot.get("use_case", "No description")
            params_json = bot.get("params", "{}")
            
            log(f"Processing bot: {bot_id}")
            log(f"  Raw params JSON: {params_json}")

            try:
                params_schema = json.loads(params_json)
                # log_json(f"  Parsed params schema for {bot_id}:", params_schema)
                
                tool_name = bot_id.replace(".", "_")
                tool = Tool(
                    name=tool_name,
                    title=tool_name,
                    description=use_case,
                    inputSchema=params_schema,
                )

                # log_json(f"  Generated MCP tool for {bot_id}:", tool)

                dynamic_tools.append(tool)
                BOT_TOOLS.append(tool_name)
                log(f"  ✓ Registered bot tool: {tool_name}")
                
            except json.JSONDecodeError as e:
                log(f"  ✗ WARNING: Invalid JSON in params for {bot_id}: {e}")
                continue
        
        return dynamic_tools
        
    except Exception as e:
        log(f"ERROR loading bots from registry: {e}")
        import traceback
        log(traceback.format_exc())
        return []

def init_tools():
    """Initialize TOOLS list with static tools + dynamic bot tools."""
    global TOOLS

    # Filter static tools by persona assignment
    assigned_static_tools = [
        t for t in STATIC_TOOLS 
        if t['name'] in STATIC_TOOL_ASSIGNMENTS 
        and (STATIC_TOOL_ASSIGNMENTS[t['name']] == 'all' or STATIC_TOOL_ASSIGNMENTS[t['name']] == PERSONA)
    ]
    
    TOOLS = [tool_from_dict(t) for t in assigned_static_tools]
    log(f"Loaded {len(TOOLS)} assigned static tools for {PERSONA}")

    dynamic_tool_objs = load_bot_tools_from_registry()
    TOOLS.extend(dynamic_tool_objs)

    log(f"Total tools registered: {len(TOOLS)} ({len(assigned_static_tools)} static + {len(dynamic_tool_objs)} bots)")
    log("=" * 80)
    log("FINAL TOOLS ARRAY:")
    for i, t in enumerate(TOOLS, 1):
        log(f"  {i}. {t.name}")
    log("=" * 80)

def execute_tool_by_name(name, args, caller="unknown"):
    log(f"[execute_tool_by_name] ENTER pid={PID} caller={caller} tool={name}")

    if name in BOT_TOOLS:
        # Map bot tool names to their hardcoded Flask routes (legacy Vera bots)
        bot_routes = {
            "vera_todos_get_pending": "/bots/vera/todos/pending",
            "vera_todos_get_friction_items": "/bots/vera/todos/friction",
            "vera_filenodes_get_unreviewed": "/bots/vera/filenodes/unreviewed",
            "vera_r2hodo_get_unsubmitted": "/bots/vera/r2hodo/unsubmitted",
            "vera_ideas_get_pending": "/bots/vera/ideas/pending",
        }
        
        route = bot_routes.get(name)
        
        if route:
            # Use legacy hardcoded route for Vera bots
            log(f"  Routing to legacy endpoint: {route}")
            result = flask_post(route, args)
        else:
            # Use generic /bots/execute endpoint for new bots
            bot_id = name.replace("_", ".")  # "iris_analytics_measure_tokens" -> "iris.analytics.measure.tokens"
            log(f"  Routing to /bots/execute with bot_id: {bot_id}")
            result = flask_post("/bots/execute", {
                "bot_id": bot_id, 
                "params": {**args, "persona": PERSONA}  # Add persona to params
            })
        
        if isinstance(result, dict) and "error" in result:
            raise RuntimeError(result["error"])
        return result

    if name == "ping":
        return flask_get("/ping")
    elif name == "mfn_list":
        return flask_get("/mfn/list")
    elif name == "bots_register":
        return flask_post("/bots/register", args)
    elif name == "buscard_dispatch":
        if args.get("action") not in ALLOWED_BUSCARD_ACTIONS:
            raise RuntimeError("Action not permitted")
        return flask_post("/buscard/dispatch", args)
    elif name == "buscard_process":
        return flask_post("/buscard/process", args)
    elif name == "r2hodo_dispatch":
        if args.get("action") not in ALLOWED_R2HODO_ACTIONS:
            raise RuntimeError("Action not permitted")
        return flask_post("/r2hodo/dispatch", args)
    elif name == "r2hodo_process":
        return flask_post("/r2hodo/process", args)
    else:
        raise RuntimeError(f"Unknown tool: {name}")


def handle_tool_call(call_id, name, args):
    log(f"[SYNC handle_tool_call] ENTER — SYNC PATH IS ALIVE! call_id={call_id} tool={name}")
    try:
        result = execute_tool_by_name(name, args, caller=f"sync:{call_id}")
        tool_result(call_id, result)
    except Exception as e:
        tool_error(call_id, str(e))

async def run_mcp_server():
    log(f"run_mcp_server() starting | pid={PID} | ppid={PPID}")

    server = Server(name=f"mcp-{PERSONA}-bridge", version="1.0.0")

    @server.list_tools()
    async def list_tools():
        log(f"list_tools() returning {len(TOOLS)} tools")
        return TOOLS

    @server.call_tool()
    async def on_call_tool(tool_name, arguments):
        arguments = arguments or {}
        result = execute_tool_by_name(tool_name, arguments, caller="async")
        # Wrap result in MCP content format
        return [{"type": "text", "text": json.dumps(result, indent=2)}]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

# Dead code that is NOT called by Claude on startup. 
def main():
    log("main() starting, waiting for MCP messages")
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue

        log("=" * 80)
        log(f"RAW INPUT FROM DESKTOP: {raw}")

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            log(f"JSON decode error: {e}")
            continue

        method = msg.get("method")
        msg_id = msg.get("id")
        log(f"Method: {method}, ID: {msg_id}")

        if method == "initialize":
            log("Handling initialize request")
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mcp-flask-bridge", "version": "1.0.0"},
                },
            })
        elif method == "tools/list":
            log(f"Handling tools/list request - sending {len(TOOLS)} tools")
            response = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
            send(response)
        elif method == "tools/call":
            params = msg.get("params", {})
            handle_tool_call(msg_id, params.get("name"), params.get("arguments", {}))
        elif method == "notifications/initialized":
            log("Received notifications/initialized")
        else:
            log(f"Unknown method: {method}")
            if msg_id is not None:
                send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})

if __name__ == "__main__":
    try:
        init_tools()
        import anyio
        anyio.run(run_mcp_server)
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
