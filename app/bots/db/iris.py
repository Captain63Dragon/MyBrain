# app/bots/db/iris.py

import string
from app.bots import bot_logger as log

REQUIRES = set()  # No external dependencies for token measurement

# ── iris.analytics.measure.tokens ─────────────────────────────────────────────

IRIS_FN_MEASURE_TOKENS = "iris.analytics.measure.tokens"

def measure_tokens(request: str, response: str, reason: str = "", 
                   log_call: bool = True, persona: str = "unknown" ) -> dict:
    """
    Measure token estimates for request/response pairs.
    
    Called by: Iris
    Use case: Provide request and response text to estimate token count for tool calls
    Library ID: iris.analytics.measure.tokens
    Intent for future Iris: Token usage analysis for bot optimization
    Logging: pass reason= to log intent. Omit or log_call=False to suppress.
    
    Args:
        request: Request text to measure
        response: Response text to measure
        reason: Why this measurement is being made
        log_call: Whether to log this call
        persona: tool set this call came through
        
    Returns:
        dict: Token measurement breakdown with char/word/punctuation counts
    """
    if log_call and reason:
        log.call(IRIS_FN_MEASURE_TOKENS, reason=reason, persona=persona)
    
    try:
        # Measure request
        req_chars = len(request)
        req_words = len(request.split())
        req_punct = sum(1 for c in request if c in string.punctuation)
        req_tokens = int(req_chars / 4)  # ~4 chars per token estimate
        
        # Measure response
        resp_chars = len(response)
        resp_words = len(response.split())
        resp_punct = sum(1 for c in response if c in string.punctuation)
        resp_tokens = int(resp_chars / 4)  # ~4 chars per token estimate
        
        return {
            "request_chars": req_chars,
            "request_words": req_words,
            "request_punctuation": req_punct,
            "request_tokens_estimate": req_tokens,
            
            "response_chars": resp_chars,
            "response_words": resp_words,
            "response_punctuation": resp_punct,
            "response_tokens_estimate": resp_tokens,
            
            "total_tokens_estimate": req_tokens + resp_tokens
        }
    except Exception as e:
        log.error(IRIS_FN_MEASURE_TOKENS, reason=reason, detail=str(e))
        return {
            "error": str(e),
            "request_chars": 0,
            "request_words": 0,
            "request_punctuation": 0,
            "request_tokens_estimate": 0,
            "response_chars": 0,
            "response_words": 0,
            "response_punctuation": 0,
            "response_tokens_estimate": 0,
            "total_tokens_estimate": 0
        }
