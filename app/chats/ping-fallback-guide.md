# Ping Fallback Guide
So you've been instructed to Ping.
Attempt `vera_bot:ping`. If tool is loaded report as instructed.  
Normal response:
```json
{
  "status": "ok",
  "neo4j": "ok",
  "server_time": "2026-03-29T00:27:11.202000000+00:00"
}
If something fails...
Case 2. FLASK OK, NEO4J DOWN "neo4j": "error: connection refused"
Neo4j is unavailable. Timestamp came from Tool. Node work will fail.

Case 3. VERA_BOT TOOL UNAVAILABLE → NEO4J AVAILABLE
`vera_bot:ping` not loaded or fails to load, ie tool not in list.  
`neo4j:execute_query` with timestamp query
```cypher
RETURN datetime() AS server_time
If Neo4j responds, report "vera_bot down, Neo4j ok" with a Time zone aware timestamp
If Neo4j also fails, proceed to degraded mode.

Case 4. META MODE (NO MCP with EMAIL and CALENDAR only)
In mobile or otherwise degraded session, Fallback procedure:
1. Create 15-min temp event in Pip's calendar (no reminders, sendUpdates: "none")
2. Extract `created` timestamp from response (UTC)
3. Delete temp event by ID
Report "Meta mode - Calendar/mail only" or "Degraded mode - no MCP" with time zone timestamp if found.
