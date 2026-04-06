# app/bots/__init__.py
#
# Bot library for MyBrain persona automation.
#
# Structure:
#   bots/db/        — bots that require a Neo4j session
#   bots/io/        — bots that use filesystem, HTTP, or external services
#   bots/composite/ — bots that call other bots (orchestrators)
#
# All bots follow the standard signature:
#   def bot_name(session=None, reason="", log_call=True) -> result
#
# Capability gating via BotContext:
#   context = BotContext.from_ping()   # auto-detect from Flask ping
#   context = BotContext.meta()        # explicit Meta-safe context
#   if not context.can_run(REQUIRES):  # check before calling
#       return
#
# Session rule exception:
#   Database bots call neo4j_service.get_session() directly.
#   This is the controlled exception to the sessions-in-neo4j_service rule.
#   Session lifecycle is still managed in neo4j_service — bots just request one.
