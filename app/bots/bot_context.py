# app/bots/bot_context.py
#
# BotContext — environment awareness and capability gating.
#
# Every bot declares what it REQUIRES. BotContext decides if those
# capabilities are available before the bot attempts to run.
# This allows bots to fail gracefully in Meta sessions (no MCP/Flask)
# rather than discovering the gap mid-chain.
#
# Capability flags:
#   'neo4j'   — Neo4j session available (requires MCP or direct bolt)
#   'flask'   — Flask HTTP reachable (requires MCP + running container)
#   'filesystem' — Filesystem MCP mounted and readable
#
# Meta-safe bots declare REQUIRES = set() or only 'neo4j' if they
# receive a session from a parent context that already confirmed capability.

import requests

# Flask ping endpoint — same as flask:ping MCP tool target
FLASK_PING_URL = "http://localhost:5000/ping"
FLASK_PING_TIMEOUT = 3  # seconds


class BotContext:
    """
    Holds detected capabilities for the current session.
    Bots call context.can_run(REQUIRES) before executing.
    """

    def __init__(self, capabilities: set):
        self.capabilities = capabilities

    @classmethod
    def from_ping(cls) -> 'BotContext':
        """
        Auto-detect capabilities by probing Flask ping.
        If Flask responds: flask + neo4j available.
        If Flask unreachable: neither available (Meta mode).
        """
        capabilities = set()
        try:
            resp = requests.get(FLASK_PING_URL, timeout=FLASK_PING_TIMEOUT)
            data = resp.json()
            if data.get('status') == 'ok':
                capabilities.add('flask')
            if data.get('neo4j') == 'ok':
                capabilities.add('neo4j')
        except Exception:
            # Flask unreachable — Meta mode, no capabilities
            pass
        return cls(capabilities)

    @classmethod
    def meta(cls) -> 'BotContext':
        """
        Explicit Meta-safe context — no capabilities declared.
        Use when calling from a session known to have no MCP.
        """
        return cls(set())

    @classmethod
    def full(cls) -> 'BotContext':
        """
        Full Desktop context — all capabilities assumed available.
        Use when MCP has already been confirmed (e.g. after ping:ping).
        """
        return cls({'neo4j', 'flask', 'filesystem'})

    def can_run(self, requires: set) -> tuple[bool, str]:
        """
        Check if this context satisfies a bot's REQUIRES set.
        Returns (True, '') or (False, reason_string).
        """
        missing = requires - self.capabilities
        if not missing:
            return True, ''
        return False, f"Missing capabilities: {', '.join(sorted(missing))}"

    def __repr__(self):
        return f"BotContext(capabilities={self.capabilities})"
