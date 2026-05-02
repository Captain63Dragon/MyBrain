# Public Server Infrastructure Proposal
**Date:** 2026-04-13 (updated from 2026-03-24)
**Status:** In Progress - Foundation Proven  
**Priority:** CRITICAL  
**Source:** 2026_0326-pin_rollup-various.md | 2026_0413 Claude session  

---

## Problem Statement

Meta mode (degraded/mobile sessions without MCP access) needs persistent scratch space and write capabilities. Current limitations:
- Calendar has TOS risks at scale for data storage
- Dropbox/filesystem = MCP-dependent (disappears in Meta mode)
- No way to create todos, save pins, or write data when tools unavailable

## Proposed Solution

Deploy web server at user's public website. `web_fetch` works in Meta mode (native, always available) and can access public HTTP endpoints.

## Architecture

```
https://your-site.com/api/meta/
  - policy-manual (GET - read policies)
  - scratch-space (GET/POST - temp storage)
  - meta-memory (GET/POST/DELETE - todos/pins)
  - vocabulary (GET - read terms)
  - session (POST - log session markers)
  - fuel-tracking (POST - log consumption)
```

## What This Enables

- **Policy Manual** lives at endpoint, readable in Meta mode
- **Scratch space** with real persistence (not Calendar TOS risk)
- **Meta memory** survives tool loss
- **Write operations** via POST (create todos, save pins)
- **Versioning, backups, logging** - full control
- **Bridge** between Meta mode and full MCP
- When tools drop, API remains accessible
- When tools return, Rex syncs API state to graph
- Server becomes **persistent backbone of OurBrain**

## Implementation Owners

- **Rex:** API design, endpoints, data models
- **Ash:** Deployment, monitoring, cron jobs
- **Vera:** API client patterns, Meta usage
- **Scientist/Iris:** Logging, analytics, fuel tracking

## Implementation Steps

1. Design API structure (endpoints, methods, schemas)
2. Choose server stack (Node, Python, Go?)
3. Define data models (Policy, Scratch, Memory)
4. Build authentication (if needed)
5. Deploy to user's site
6. Test web_fetch in Meta mode
7. Build sync layer (API ↔ graph)
8. Document usage patterns

## Dependencies

None - this is foundational infrastructure

## Blocks/Enables

**Enables:**
- Heartbeat Bot (needs API endpoint for logging)
- Scientist persona (needs data to analyze)
- Meta mode todos/pins (write capability)
- Policy Manual access in Meta mode

---

## 2026-04-13 - Foundation Proven (Claude session)

### What Was Built Today

- **Stack confirmed:** PHP on DreamHost shared hosting at zaudi.com
- **Database:** MySQL `mybrainlite` at `brain.zaudi.com` - live and accessible via phpMyAdmin
- **POST endpoint:** `https://zaudi.com/post.php` - receives JSON, writes to `payloads` table ✓
- **Email pipe:** `https://zaudi.com/mailtest.php` - PHP `mail()` sends to `mybrain@zaudi.com` ✓
- **IMAP pickup:** localhost Flask picks up email from mybrain@zaudi.com, processes, moves to Vera folder ✓
- **Full loop confirmed:** Claude Code → POST → Zaudi → email → IMAP → Flask → processed

### Key Findings

- `https://` required - plain HTTP returns DreamHost "Site Not Found"
- `web_fetch` works from Claude sessions when exact URL is provided by user
- `curl` via bash_tool bypasses web_fetch URL restrictions - usable for automation
- PHP `mail()` works same-domain with no SMTP config; `X-PHP-Originating-Script` header identifies Zaudi-originated emails for Flask routing
- Credentials in cleartext PHP = known risk, flagged for future fix (ini file outside web root)

### Email Loop Architecture (Async)

```
Vera (mobile/meta) → POST to zaudi.com
→ Zaudi writes to MySQL + sends email to mybrain@zaudi.com
→ localhost IMAP pickup (5 min polling)
→ Flask processes → POSTs response back to Zaudi
→ Vera polls get.php → retrieves response
```

Async by design - 5 min round trip acceptable for away-from-desk use case.

### Files Deployed to zaudi.com

- `hello.php` - GET health check, returns JSON + timestamp
- `post.php` - POST receiver, writes to payloads table in mybrainlite
- `mailtest.php` - GET/POST, sends test email to mybrain@zaudi.com

### Database

- Host: `brain.zaudi.com`
- DB: `mybrainlite`
- User: `mybrain`
- Table: `payloads` (id, received_at, source, payload JSON, raw TEXT)

---

## Proposed Next Steps

1. **`get.php`** - Read recent payloads back (Vera polling endpoint)
2. **`todos` table** - Mirror of Vera's active todo list, pushed after every daily
3. **Sync layer** - POSTs todo snapshot to Zaudi at end of daily run
4. **Authentication** - Simple API key header check on all endpoints (low friction, stops casual abuse)
5. **`meta-memory` endpoint** - Vera-facing read/write for pins and notes in meta mode
6. **Routing in Flask** - Use `X-PHP-Originating-Script` header to identify and route Zaudi emails
7. **Retire output.txt** - Flat file was proof of concept only, DB is ground truth now

---

**Notes:**
- Original proposal designated this as CRITICAL priority
- Solves fundamental Meta mode write problem
- Architectural breakthrough from March 24, 2026 session
- Foundation fully proven April 13, 2026 - zaudi.com is the external node
- Todo sync pipeline designed 2026-04-20 - see `2026_0420-feature-zaudi-todo-sync.md`
