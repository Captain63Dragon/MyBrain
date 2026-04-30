# app/bots/bot_logger.py
#
# Bot call logger.
#
# Phase 1: file-based rotating log. Simple, no dependencies.
# Phase 2 (deferred): Neo4j call log nodes for pattern analysis.
#   Post-analysis of logs surfaces candidate chains -> new higher-order bots.
#
# Log format (one JSON line per call):
#   {"ts": "ISO8601", "fn": "[N]vera.todos.get", "reason": "...", "result": "ok|error", "detail": "..."}
#
# Chain depth prefix:
#   [0] = top-level call from persona/MCP
#   [1] = bot called by another bot (sub-call)
#   [2] = bot called by [1], etc.
#
# Usage:
#   log.call(FN_ID, reason=...)               # top-level, auto-prefixed [0]
#   with log.sub_call():                      # wraps a sub-bot call
#       inner_bot(log_call=True, ...)         # inner call auto-prefixed [1]
#
# Reason strings are ore -- they record intent at call time, not baked-in purpose.
# Higher-order bots pass log_call=False to constituents -- log once at top level.
# See terms file for reason vocabulary conventions.

import json
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Log file location -- relative to project root
BOT_LOG_PATH = os.path.join('app', 'logs', 'bot_calls.log')
BOT_LOG_MAX_BYTES = 1_000_000   # 1MB per file
BOT_LOG_BACKUP_COUNT = 5        # keep 5 rotated files

_logger = None

# Thread-local call depth tracking
_depth = threading.local()


def _get_logger():
    global _logger
    if _logger is not None:
        return _logger

    os.makedirs(os.path.dirname(BOT_LOG_PATH), exist_ok=True)

    _logger = logging.getLogger('bot_calls')
    _logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if module is reloaded
    if not _logger.handlers:
        handler = RotatingFileHandler(
            BOT_LOG_PATH,
            maxBytes=BOT_LOG_MAX_BYTES,
            backupCount=BOT_LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        _logger.addHandler(handler)

    return _logger


def _current_depth() -> int:
    """Return current call depth (0 = top-level persona/MCP call)."""
    return getattr(_depth, 'level', 0)


def reset_depth() -> None:
    """Reset call depth to 0. Call at the start of each incoming request."""
    _depth.level = 0


@contextmanager
def sub_call():
    """
    Context manager to mark a block as a sub-bot call (depth + 1).
    Use when a bot function directly calls another bot that logs itself.

    Example:
        with log.sub_call():
            create_relationship(..., log_call=True)
        # create_relationship's log entry will be prefixed [1]
    """
    _depth.level = _current_depth() + 1
    try:
        yield
    finally:
        _depth.level = _current_depth() - 1


def call(fn_id: str, reason: str = '', result: str = 'ok', detail: str = '', persona: str = ''):
    """
    Log a bot function call.

    The fn_id is auto-prefixed with the current chain depth [N] unless it
    already carries a prefix. Depth 0 = top-level persona/MCP call.
    Depth 1+ = called from within another bot.

    Args:
        fn_id:   dotted library ID, e.g. 'vera.todos.get_pending'
        reason:  free text from calling persona -- intent at call time
        result:  'ok' or 'error'
        detail:  optional extra context (error message, count, etc.)
        persona: persona name if known
    """
    # Auto-prefix if no depth bracket already present
    if not fn_id.startswith('['):
        fn_id = f'[{_current_depth()}]{fn_id}'

    entry = {
        'ts':     datetime.utcnow().isoformat() + 'Z',
        'fn':     fn_id,
        'reason': reason,
        'result': result,
    }
    if detail:
        entry['detail'] = detail
    if persona and persona != 'unknown':
        entry['persona'] = persona

    _get_logger().info(json.dumps(entry))


def error(fn_id: str, reason: str = '', detail: str = ''):
    """Convenience wrapper for logging a bot error."""
    call(fn_id, reason=reason, result='error', detail=detail)
