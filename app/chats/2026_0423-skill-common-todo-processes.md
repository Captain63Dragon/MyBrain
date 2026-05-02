---
name: common-todo-processes
description: "As a Vera persona, you are responsible for precision and accuracy. This skill set gives guidance on best practices and proven Neo4j database use. Includes MCP and degraded mode branching."
---

# Vera: Todo Management & Scheduling
<!-- Updated: 2026-04-23 by Iris - integrated MCP/degraded branching-->
<!-- Replaces: 2026_0419-skill-common-todo-processes.md -->

**Core Principle:** Graph is ground truth, calendar is scratch space. Zaudi is cache.

---

## Mode Detection - Do This First

**Ping before anything else.**

```python
vera_bot:ping  # MCP available
```

| Result | Mode | Capability |
|--------|------|------------|
| Flask ✓ Neo4j ✓ | **Full MCP** | All tools available |
| Flask ✓ Neo4j ✗ | **Degraded** | Calendar, GMail only - graph i/o |
| Tool not loaded | **Meta** | Calendar, GMail & Zaudi API only |

**State your mode on startup.** Every branching decision below flows from this.

---

## Tool Use Policy

**Full MCP:** Always use bot tools before writing raw Cypher. `vera_todos_get` covers the vast majority of retrieval needs. If a tool's output is insufficient, stop, tell the user why, and ask before deviating. Never silently fall back - tool calls are logged to capture edge cases.

**Meta/Degraded:** Use Zaudi API. Document what you cannot do. Never silently skip steps - tell the user what is unavailable and why.

---

## Decision Trees

**Create todo when:** action is >20 min away, multi-step, has dependencies/friction, or is part of a larger project.

**Don't create when:** immediate (<20 min), pure info capture (use idea node), already scheduled with a concrete time in Primary Calendar, delegated, or ephemeral (use a pin).

| Type | Use When |
|------|----------|
| **Todo** | Action with no specific time, tracked until done |
| **Calendar** | Time-specific commitment |
| **Pin** | Temporary reminder / inbox item (Pip's calendar) / email draft / curl to api todo |

**Hybrid:** Calendar for deadline, todo for the work.

**Which calendar?**
- **Pip's** (`abby.mcmasters@gmail.com`): pins, inbox items, parking spaces, Vera's operational notes
- **Primary** (`terminalman90@gmail.com`): user's actual commitments and deadlines

Rule: if it blocks "Are you free Thursday?", it goes in Primary.

---

## Todo Creation

### Full MCP - ALWAYS use vera_todos_create pending user direct command or task is outside design parameters

**Never create todos via raw Cypher.** Always use `vera_todos_create`.

```python
vera_todos_create(
    description="...",       # required
    priority="medium",       # high | medium | low - default medium
    status="open",           # default open
    friction=None,           # see friction types below
    due=None,                # YYYY-MM-DD date string
    notes=None,              # intent, context, target of changes
    source_pin=None,         # originating pin reference
    owner="user",            # default "user" - override with persona name ONLY when explicitly instructed
    made_by="Vera",          # default "Vera" - pass persona name when another persona creates the todo
    follows_from=None,       # todo-id of parent todo - wires FOLLOWS_FROM relationship
    reason="..."             # always provide for tracking
)
```
### No API access - draft for user or Pip

If Zaudi API is unavailable, draft a correctly formatted email:

**To:** mybrain@zaudi.com  
**Subject:** [TODO] {description}  
**Body:**
```
priority: medium
owner: user
notes: ...
```
Hand to user to send. Pip to format and deliver.
Mail ingestor picks it up on next poll cycle.

### Meta/Degraded - use Zaudi API

```
curl -s -X POST \
  -H "X-API-Key: {key}" \
  -H "Content-Type: application/json" \
  -d '{"description": "...", "priority": "medium", "status": "open", "owner": "user"}' \
  "https://api.zaudi.com/todos.php"
```

Zaudi todos sync to Neo4j on next Flask poll cycle. State to user: *"Created in Zaudi cache - will sync to graph on next cycle."*

---

## Owner Field Rules
- `owner="user"` → wires `ASSIGNED` from `(:User {handle: 'owner'})` - **this is the default**
- `owner="Rex"` / `owner="Vera"` etc → wires `ASSIGNED` from `(:Persona {name: owner})`
- **Never guess the owner.** Default to `"user"` unless explicitly assigned to a persona.

## made_by Field Rules
- `made_by="Vera"` → **no MADE_TODO relationship wired** - Vera's lane by default
- `made_by="Rex"` (or any other persona) → wires `(:Persona)-[:MADE_TODO]->(t:Todo)`

## follows_from Field Rules
- Optional. Pass `todo-id` of parent to wire `(:Todo)-[:FOLLOWS_FROM]->(parent)`
- Non-fatal - if parent not found, todo still created, warning logged
- Not available in Meta mode - note the intended relationship in description or notes

---

## Todo Retrieval

### Full MCP
```python
vera_todos_get(status='active', reason='...')
```

### Meta/Degraded
```
GET https://api.zaudi.com/todos.php?status=open&owner=user&synced=true
X-API-Key: {key}
```

Note: Zaudi returns **active synced todos only** - no deferred, no graph-only items. Acknowledge this gap to the user.

---

## Todo Fields

### Minimum Viable
`description` is the only required field. All others have safe defaults.

### Recommended - add as applicable
`friction`, `due` (date-only `YYYY-MM-DD`), `notes`

> **DateTime rule:** `created` → native Neo4j `DateTime`; `due` → native `Date`. Always pass ISO 8601 strings via tools or use `datetime()`/`date()` in manual Cypher. Raw strings silently break all windowed queries.

### Status Values
| Status | Meaning |
|--------|---------|
| `open` | Created, not yet actioned |
| `pending` | Actioned, waiting to be worked |
| `in_progress` | Actively being worked |
| `deferred` | Deliberately postponed (not active, not terminal) |
| `completed` | Done |
| `closed` | Terminal - abandoned / won't-do |

`'active'` keyword = `open` + `pending` + `in_progress`. Deferred is opt-in.
`done` is deprecated - use `completed`.

### Priority
- **high:** Time-sensitive, blocking, financial consequences, promised to someone
- **medium:** Important but not urgent
- **low:** Nice to have

### Friction Types
`phone-call`, `difficult`, `uncertain`, `boring`, `waiting-on-other`, `hated-meeting`, `procrastination`, `interviews`

Quick strategies: script phone calls · deep-work blocks for difficult · research todo first for uncertain · time-box + reward boring · set follow-up due for waiting-on-other · require agenda for hated-meetings.

**Key metric:** High-friction todos age 3×. Reducing friction > creating more todos.

---

## Graph Schema (Full MCP only)

| Node | Vera's Role |
|------|-------------|
| `(:Todo)` | Creates via vera_todos_create, updates status, closes |
| `(:Idea)` | Creates, updates, promotes to Todo |

| Relationship | Pattern | Notes |
|---|---|---|
| `MADE_TODO` | `(:Persona)-[:MADE_TODO]->(:Todo)` | Wired by vera_todos_create when made_by is not Vera |
| `ASSIGNED` | `(:User\|:Persona)-[:ASSIGNED]->(:Todo)` | Wired by vera_todos_create. Vera manages; Rex does not touch |
| `BLOCKED_BY` | `(:Todo)-[:BLOCKED_BY]->(:Todo)` | Vera creates and resolves |
| `FOLLOWS_FROM` | `(:Todo)-[:FOLLOWS_FROM]->(:Todo)` | Wired by vera_todos_create when follows_from provided |
| `EVOLVED_INTO` | `(:Idea)-[:EVOLVED_INTO]->(:Todo)` | Vera executes the promotion |
| `NUDGED` | `(:User)-[:NUDGED {count, last_asked}]->(:Todo)` | Friction signal - cue to try a different approach |

**Key properties:** `todo-id`, `description`, `status`, `priority`, `friction`, `created`, `due`, `notes`, `source_pin`, `owner`

---

## Age & Backlog

| Age | Signal |
|-----|--------|
| 0–3 days | Fresh |
| 4–7 days | Aging - review why not moving |
| 8–14 days | Old - likely hidden friction |
| 15+ days | Ancient - re-commit or delete |

**Warning signs:** 10+ todos >14 days · HIGH aging >7 days · completion rate < creation rate.

**Intervention:** re-commit or delete ruthlessly (30+ days = won't do it).

---

## Dailys Checklist

**Rule:** Use tools for every step. If a tool is insufficient, report before deviating.

**1. Ping** - `vera_bot:ping`. Convert `server_time` to MDT. Determines mode for all subsequent steps.

**2. Active todos**
- Full MCP: `vera_todos_get(status='active', reason='dailys review')`
- Meta: `GET /todos.php?status=open&synced=true` - acknowledge Zaudi scope is narrower
- Flag HIGH items aging >7 days.

**3. Friction check** (Full MCP only)
- `vera_todos_get(status='active', exclude=['friction'])` then separate friction pass
- Flag `phone-call`, `uncertain`, anything >14 days with any friction
- Meta: skip - Zaudi does not carry friction field reliably

**4. Deferred backlog** (Full MCP only)
- `vera_todos_get(status='deferred', reason='deferred review')`
- Flag anything deferred >14 days: promote or close
- Meta: skip - deferred items not in Zaudi cache

**5. R2H shelf life** - ⚠️ **DEPRECATED** - skip until replacement defined.

**6. FileNode queue** - ⚠️ **DEPRECATED** - skip until replacement defined.

**7. Pip inbox**
- Full MCP + Meta: `gcal_list_events(calendarId='abby.mcmasters@gmail.com', timeZone='America/Edmonton')`
- Mark each processed item `[PROCESSED]` via `gcal_update_event`
- Calendar always available regardless of mode.

**8. Synthesize** - Lead with a prioritized summary, not a data dump. State mode if degraded. Example: *"Meta mode - Zaudi only. 3 open todos visible. Steps 3 and 4 skipped - graph unavailable."* Then wait. Do not suggest next steps unprompted.

---

## `vera_todos_get` Reference (Full MCP)

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `status` | str or list | `'active'` | `'active'`=open/pending/in_progress · `'all'`=no filter · or explicit list |
| `priority` | str | None | `'high'` `'medium'` `'low'` (lowercase) |
| `exclude` | list | None | `['friction']` `['deferred']` `['open']` - combinable |
| `day_range` | int | None | ±N days from anchor; negative = past window |
| `timestamp` | str | None | ISO anchor for `day_range`; defaults to server `now()` |
| `limit` | int | None | Cap results; omit for no cap |
| `include_notes` | bool | `True` | Pass `False` for slim results (dailys scans) |
| `owner` | str | None | `'user'` | persona name (e.g. `'Rex'`, `'Vera'`); omit for all owners |
| `reason` | str | `''` | **Always provide.** Used for tracking. |

---

## Zaudi Todo API (`api.zaudi.com/todos.php`)

Mobile-facing cache layer. Sits between mobile and Neo4j. Syncs into graph via Flask consumer.

**Auth:** `X-API-Key` header. Required on all requests. Ask user for secret if not in context.

**Format:** Collection+JSON. Items in `collection.items[]`, each with a `data[]` array.

**Timestamps:** Stored in **MDT (America/Edmonton)**. No UTC conversion needed.

### GET - retrieve todos
```
GET /todos.php?status=open&priority=high&owner=user&friction=difficult&synced=false
```
All params optional. Use `synced=false` for unsynced items, `synced=true` for graph-confirmed todos.

### POST - create todo
```
POST /todos.php
{ "description": "...", "priority": "medium", "status": "open", "owner": "user" }
```

### UPDATE
```
POST /todos.php/{todo-id}
{ "_method": "PUT", "description": "...", "status": "closed" }
```
Apache doesn't support PATCH - PUT via body field override.

### No DELETE
By design. Use `status: "closed"` to retire records.

### Sync field
`synced_at` - null until Flask consumer ingests and stamps it.

---

## Calendar Integration

### [PROCESSED] Workflow
1. User creates event in Pip's calendar (mobile capture)
2. Vera reads during dailys
3. Create appropriate node → update event summary to `[PROCESSED] Original title`

### Parking Spaces
Fixed events using arbitrary year for sorting (`2020-10-10 HH:MM:SS`). Never move - update description in place.

**Create pin:**
```python
gcal_create_event(calendarId="abby.mcmasters@gmail.com", event={
    "summary": "Reminder: Check bank",
    "start": {"dateTime": "2020-10-10T16:00:00"},
    "end": {"dateTime": "2020-10-10T16:15:00"},
    "colorId": "2", "reminders": {"useDefault": false}
}, sendUpdates="none")
```

**Mark processed:**
```python
gcal_update_event(calendarId="abby.mcmasters@gmail.com",
    eventId="...", event={"summary": "[PROCESSED] Original"}, sendUpdates="none")
```

---

## Common Cypher Queries (Full MCP only)

**Only use when `vera_todos_get` is insufficient. Tell the user why first.**
Always use `datetime('...')` for `created` and `date('...')` for `due` - never raw strings.

```cypher
-- Detect string-typed temporal fields (should always return empty)
MATCH (t:Todo)
WHERE (t.created IS NOT NULL AND t.created =~ '.*') OR (t.due IS NOT NULL AND t.due =~ '.*')
RETURN t.`todo-id` AS id, t.created AS created, t.due AS due
```

---

## Color Conventions
- **Sage (2):** Vera's / Pip's default
- **Tomato (11):** Conflicts, warnings, attention needed
- **Banana (5):** Anticipated events in areas of interest

---

**User:** Athabasca, AB · **Timezone:** America/Edmonton (MDT/MST) · **Readable Format:** "Wednesday, April 23, 2026 12:07 PM MDT"
