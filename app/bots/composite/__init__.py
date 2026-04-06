# app/bots/composite/__init__.py
#
# Composite bots — orchestrators that call other bots.
# Log once at this level. Pass log_call=False to all constituent calls.
# Declare REQUIRES as the union of all constituent REQUIRES.
#
# Pattern:
#   def run_vera_daily_brief(session=None, reason="", log_call=True):
#       if log_call and reason:
#           log.call("vera.composite.daily_brief", reason=reason)
#       todos   = get_pending_todos(session=session, log_call=False)
#       friction = get_friction_todos(session=session, log_call=False)
#       r2hodo  = get_unsubmitted_r2hodo(session=session, log_call=False)
#       ...
#
# Placeholder — first resident will be:
#   vera.py  — vera.composite.daily_brief, vera.composite.session_start
