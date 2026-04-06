# app/bots/bot_logger.py
#
# Bot call logger.
#
# Phase 1: file-based rotating log. Simple, no dependencies.
# Phase 2 (deferred): Neo4j call log nodes for pattern analysis.
#   Post-analysis of logs surfaces candidate chains → new higher-order bots.
#
# Log format (one JSON line per call):
#   {"ts": "ISO8601", "fn": "vera.todos.get_pending", "reason": "...", "result": "ok|error", "detail": "..."}
#
# Reason strings are ore — they record intent at call time, not baked-in purpose.
# Higher-order bots pass log_call=False to constituents — log once at top level.
# See terms file for reason vocabulary conventions.

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Log file location — relative to project root
BOT_LOG_PATH = os.path.join('app', 'logs', 'bot_calls.log')
BOT_LOG_MAX_BYTES = 1_000_000   # 1MB per file
BOT_LOG_BACKUP_COUNT = 5        # keep 5 rotated files

_logger = None


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


def call(fn_id: str, reason: str = '', result: str = 'ok', detail: str = '', persona: str=""):
    """
    Log a bot function call.

    Args:
        fn_id:   dotted library ID, e.g. 'vera.todos.get_pending'
        reason:  free text from calling persona — intent at call time
        result:  'ok' or 'error'
        detail:  optional extra context (error message, count, etc.)
    """
    entry = {
        'ts':     datetime.utcnow().isoformat() + 'Z',
        'fn':     fn_id,
        'reason': reason,
        'result': result,
    }
    if detail:
        entry['detail'] = detail
    if persona and persona != "unknown":
        entry['persona'] = persona

    _get_logger().info(json.dumps(entry))


def error(fn_id: str, reason: str = '', detail: str = ''):
    """Convenience wrapper for logging a bot error."""
    call(fn_id, reason=reason, result='error', detail=detail)
