# app/bots/db/rex.py

from app.bots import bot_logger as log
from app.services.neo4j_service import get_session

REQUIRES = {'neo4j'}
REX_FN_BOT_REGISTRY = "rex.bots.load"

def load_bot_registry(session=None, reason: str = "", log_call: bool = True) -> dict:
    """Query Neo4j for BotFunction nodes - gets logged like any other bot call."""
    if log_call and reason:
        log.call(REX_FN_BOT_REGISTRY, reason=reason)
    
    _owned = session is None
    try:
        if _owned:
            session = get_session().__enter__()
        
        # The Neo4j query from /bots/list endpoint
        result = session.run("""
            MATCH (bf:BotFunction)
            RETURN bf.`bot-id` AS `bot-id`,
                   bf.use_case AS use_case,
                   bf.params AS params,
                   bf.module AS module,
                   bf.function AS function,
                   bf.deprecated AS deprecated
            ORDER BY bf.`bot-id`
        """)
        
        bots = []
        for record in result:
            bots.append({
                "bot-id": record["bot-id"],
                "use_case": record["use_case"],
                "params": record["params"],
                "module": record["module"],
                "function": record["function"],
                "deprecated": record["deprecated"]
            })
        
        return {"bots": bots, "count": len(bots)}
        
    finally:
        if _owned:
            session.__exit__(None, None, None)