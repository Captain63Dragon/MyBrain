## MCP Function Cheat Sheet
<!-- Updated: 2026-04-29 by Iris -->
<!-- Replaces: 2026_0409-cheatsheet.md -->

### Flask
| Function | Use |
|---|---|
| `vera_bot:ping` | Check Flask + Neo4j status. Do this on start. |
| `vera_bot:mfn_list` | List registered MetaFileNode types. |

### Vera Bot — use tool_search (limit=20) for full list
| Function | Use |
|---|---|
| `vera_todos_get` | Primary todo retrieval. Supports `status`, `priority`, `exclude`, `day_range`, `timestamp`, `limit`, `include_notes`, `reason`. See skill. |
| `vera_todos_create` | Create todo node + wire ASSIGNED. `owner` defaults to `'user'`. See skill for full params. |
| `vera_todos_update` | Update todo node. |
|---|---|
| Function | Deprecated |
| `vera_todos_get_pending` | Get pending todo nodes (use qualified vera_todos_get). |
| `vera_todos_get_friction_items` | Filtered by friction_types ( as above, legacy). |
| `vera_ideas_get_pending` | Get pending idea nodes (as above, legacy). |
| `vera_filenodes_get_unreviewed` | Get unreviewed file nodes. ( currently disabled )|
| `vera_r2hodo_get_unsubmitted` | Get unsubmitted R2HOdo items. ( currently disabled )|

### Neo4j
| Function | Use |
|---|---|
| `neo4j:execute_query` | Run any Cypher query. Required: `query` string. |
| `neo4j:execute_query` | Run timestamp query if Ping tool not loaded |
| `neo4j:create_node` | Create a node. Required: `label`, `properties` object. |
| `neo4j:create_relationship` | Link two nodes. Required: `fromNodeId`, `toNodeId`, `type`. |

> **Friction & status values:** See `common-todo-processes` skill - ground truth.

### Iris Bot — pipeline dispatch
| Function | Use |
|---|---|
| `iris_bot:buscard_dispatch` | Dispatch buscard action: discovery, move, archive, insitu_copy, copy_master_source, copy_master_target |
| `iris_bot:r2hodo_dispatch` | Dispatch R2HOdo action: discovery |
| `iris_bot:bots_register` | Register all bots from graph to bridge |

### Iris Analytics
| Function | Use |
|---|---|
| `iris.analytics.measure.tokens` | Estimate token usage from request/response text. ~4 chars/token. Returns char, word, punctuation, token counts for request, response, and total. |

> **Watcher required:** Any dispatch (move, discovery, copy) requires `mfi_watcher.py --watch` running on Windows host.
> Run from codebase root: `venv\Scripts\python app\scripts\mfi_watcher.py --watch`

### Filesystem — Windows Path Notes
> **Editing Windows-path files — follow this order, do not skip ahead:**
> 1. `filesystem:edit_file` — **always try this first.** Exact text match, surgical, no line numbers needed. Works on `D:\` and `E:\` paths.
> 2. `filesystem:write_file` — **fallback only.** Full rewrite. Use when edit_file cannot find a stable anchor. Do NOT use for small or single-line changes.
> 3. `str_replace` — **NEVER on Windows paths.** Container-only. Will fail silently or error on `D:\` and `E:\` paths.
>
> Jumping to `write_file` for a one-line change is always wrong. Use `edit_file`.

### Startup (As directed via fire up protocol)
| Step | Action |
|---|---|
| 1 | `vera_bot:ping` — Flask + Neo4j status |
| 2 | `filesystem:read_text_file` on `app/chats/ping.md` — confirms filesystem MCP |
| 3 | `filesystem:list_directory` on `app/chats/` — find newest `yyyy_mmdd-summary.md` |
| 4 | `filesystem:read_text_file` on that summary — load project state |
