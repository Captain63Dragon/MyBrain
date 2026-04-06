# app/bots/io/__init__.py
#
# IO bots — filesystem, HTTP, external services.
# These bots do not require a Neo4j session but may require 'flask' or
# 'filesystem' capabilities depending on what they touch.
#
# Placeholder — first residents will be:
#   calendar.py  — Google Calendar read/write (Vera's domain)
#   tasks.py     — Google Tasks import (when pipeline is ready)
