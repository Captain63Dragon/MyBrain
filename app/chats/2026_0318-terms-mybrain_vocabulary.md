# MyBrain — Terms and Vocabulary
# Status: Formation — actively evolving
# Updated: 2026-03-18 by Rex
# Home: app/chats/ until stable, then app/planning/

---

## Purpose
A shared vocabulary for all personas, bots, scripts, and the owner.
Ambiguous terms cause token burn and drift. Precise terms compress.
When a term appears below, use it as defined. When a new term earns a definition, add it here.

---

## Core Terms

### Pin (note term Pin is overloaded and context sensitive. See calendar pin, yaml pin, etc)
A Pip-formatted YAML file. Structured capture of raw input — a letter, a ramble,
a photo, a todo idea. The output of Pip's work. Not a todo. Not a node. A seed.
Lives in incoming until processed. Becomes something else downstream.

Delivery routes (all valid):
- File dropped to `E:\_Processing\incoming\` or `C:\Users\termi\Dropbox\Incoming`
- Google Drive sync (pending Drive for Desktop + Pin MFN)
- Google Calendar event with Drive attachment (proposed)

### Todo
An actionable item with a next step. Lives in the graph as a `(:Todo)` node.
Vera's domain. Has owner, priority, friction, status. Not a pin. Not an idea.
Created by: Vera (implied, no MADE_TODO), Rex (MADE_TODO signals Vera), Pip via pin.

### Idea
Not yet actionable. Worth holding. May evolve into a Todo.
Vera manages. `(:Idea)` node. Status: raw → developing → shelved → promoted.

### FeatureRequest
A proposed change to the MyBrain codebase or graph schema.
Lives in `app/planning/` as a markdown doc AND as a `(:FeatureRequest)` node.
Rex implements. Vera or owner requests.

### Reference
Fileable information. No action required. Pipeline absorbs it to the graph.

### Pin (as verb)
The act of Pip capturing something. "Pip pinned it" = Pip formatted and dropped a YAML file.
Not to be confused with the file itself in ambiguous context.

---

## Pipeline Terms

### MFI (Meta File Instruction)
The file-based messaging protocol bridging Docker and Windows.
YAML files (.mfi) written atomically. Three folders: pending, processing, completed.
The pipe between Flask and Windows filesystem.

### MFN (MetaFileNode)
Policy engine in the graph. Defines schema, patterns, garden path for a file type.
`MFN-id` in graph, `META-FILE-NODE` in YAML header. Known inconsistency, deferred.

### FileNode
A file that has been ingested. Two labels: `FileNode` + MFN type (e.g. `BusinessCard`).
Lives in the graph. The node is the truth. The file is the delivery mechanism.

### Garden
Curated, protected files on `E:\`. Files that have been ingested and named.
Contrast with Wild (unvetted, Dropbox/camera roll) and Node (graph truth, file-independent).

### Wild
Unvetted raw material. Dropbox root, camera rolls, desktops.
Prompts ingestion. Doesn't owe you anything afterward.

### Discovery
The pipeline action that finds files matching an MFN's patterns and creates FileNodes.
Must include patterns from the MFN — empty patterns = no matches.

---

## Persona Terms

### Meta
A session with no MCP access. Design only. No ping, no graph writes, no filesystem.
Pins are the output of Meta. Drop them in incoming when not Meta.
Usage: "We are Meta" = current session is design-only.

### Channel
Who surfaced a todo — not who owns the underlying intent.
Owner is always the ultimate source of all todos.
Channels: Rex (MADE_TODO), Vera (implied), Pip (source_pin property).

### Ore / Nugget
Ore = raw material, bulk context, unrefined ideas (e.g. a full chat log).
Nugget = the compressed, actionable extract (e.g. a summary, a spec, a todo).
Fuel efficiency principle: always compress ore to nugget. Verbose is a failure mode.

### Crucible
The process of refining ore into nuggets. Usually a Meta session or a review with the owner.
"Cook it in the crucible" = reason about it together until the pattern is clear.

### Fuel / Fuel Efficiency
Tokens are fuel. Every round trip through a full Claude context costs fuel.
Bots handle rote (cheap). Personas handle edges (expensive but necessary).
Goal: compress pipelines so personas spend tokens on judgment, not boilerplate.

---

## Bot Library Terms

### Bot
A named, reusable function in a persona's library. Handles rote work.
Named with dotted namespace: `vera.todos.get_pending`, `pip.capture.clarify`.
Has: library ID, type hints, intent comment, reason parameter, log suppression flag.

### Library ID
The dotted namespace identifier for a bot function. e.g. `vera.todos.get_pending`.
Stored as a constant (`VERA_FN = "vera.todos.get_pending"`) in the function file.
Used by the logging facility to track call patterns.

### Reason Parameter
A string passed by the calling persona at runtime documenting *why* this call was made.
Not baked into the function — comes from context. Logged for post-analysis.
Example: `reason="session.open — inbox check before triage"`
Empty or absent = call suppressed from log.

### Higher-Order Bot
A bot that calls other bots. Logs once at its own level.
Constituent calls pass `log_call=False` to stay silent.
Candidate for creation when the log reveals a persona always calls A → B → C together.

### Reason Vocabulary (emerging conventions)
Prefix reason strings for pattern matching:
  session.open      — called at start of session
  post.assign       — called after an assignment to verify
  verify            — checking state before action
  triage.friction   — surfacing stalled items
  routine.morning   — part of morning triage chain

---

## File Naming Conventions

### General pattern
`YYYY_MMDD-{type}-{slug}.md`
Date first. Type second. Slug is lowercase, underscores, descriptive but short.

### Types in use
| Type | Folder | Description |
|---|---|---|
| `summary` | `app/chats/` | Session delta or full project context |
| `persona` | `app/chats/` | Persona definition file |
| `terms` | `app/chats/` (formation) → `app/planning/` (stable) | Vocabulary |
| `proposal` | `app/planning/` | Design proposal, open for review |
| `spec` | `app/planning/` | Accepted design, implementation-ready |
| `feature` | `app/planning/` | FeatureRequest document |
| `pin` | incoming folders | Pip-formatted YAML capture |

### Notes
- `chat-` prefix is legacy — was redundant when chats/ held only summaries. Now retired.
- Existing files with `chat-` prefix are grandfathered. Rename on next meaningful edit.
- `ping.md` in chats/ is a utility file — no convention needed.
- Planning files with date at wrong end or .txt extension are legacy, assess and retire.

---

## Folder Roles

| Folder | Purpose |
|---|---|
| `app/chats/` | Runtime context — personas, summaries, formation docs |
| `app/planning/` | Design context — proposals, specs, terms, feature requests |
| `app/Schema/` | MFN and GFN YAML definitions |
| `E:\_Processing\incoming\` | Pin landing zone — watcher monitors |
| `C:\Users\termi\Dropbox\Incoming` | Dropbox pin landing zone |
| `C:\Users\termi\Dropbox\Saves\` | Primary saves — all discovered |
| `E:\BusinessCards\` | Garden — BusinessCard files |
| `E:\R2Hope\` | Garden — R2HOdo files |
