# Feature: IMAP Email Capture Pipeline
# Created: 2026-04-05 by Ash
# Status: Proposal

---

## Overview

Two distinct IMAP-based pipelines into MyBrain. Both use curl over imaps, polled by
Windows scheduled task. Both delete on pull — stack behavior, not archive.

---

## Lane 1 — Primary Inbox Monitor

**Address:** User's primary email (Dreamhost)
**Access:** Read-only observation. Gmail also syncs this inbox — do not disturb that.
**Mode:** Persona-mediated. Vera receives triage output.
**Trigger:** Cron poll, headers first. Fetch body only for flagged messages.

**Behavior:**
- Pull headers (SUBJECT, FROM, DATE) via curl IMAP
- Preprocessing script scores/triages — sender, subject keywords, urgency signals
- Summarizes actionable items into a structured `.md`
- Drops to `Dropbox\Incoming` — existing watcher picks up from there
- UID tracked in flat file — never reprocess, never delete from primary inbox

**Constraint:** No deletes, no moves on primary inbox. UID file is the only state written.

---

## Lane 2 — Direct Capture Pipe (Stack)

**Address:** Dedicated Dreamhost address (e.g. pip@zaudi.com, vera@zaudi.com)
**Mode:** No persona in the middle. User IS the persona.
**Trigger:** Cron poll on UID sequence.
**On pull:** Message is deleted from mailbox. Stack consumed.

### Routing — TO address is the router

| To | Lane |
|---|---|
| `pip@zaudi.com` | Capture lane — Pip formats, drops pin to Incoming |
| `vera@zaudi.com` | Direct processing — Vera acts, may write to graph |

### Routing — Subject prefix is the intent signal

| Prefix | Intent |
|---|---|
| `[IDEA:]` | Create Idea node — Vera's domain |
| `[TODO:]` | Create Todo node — Vera's domain |
| `[PIN:]` | Pip formats and drops to Incoming |
| *(no prefix)* | Forwarded email — triage, body + user instructions above forward boundary |

### Forwarded Email Format
User adds instructions **above** the forward boundary line. Parser splits on the
standard forward header (`---------- Forwarded message ---------` or equivalent).

```
Part 1 (above boundary): User instructions / Vera directives
Part 2 (below boundary): Original email content
```

---

## Access Methods

Polling via curl was considered for testing but is not the target architecture.
Three cleaner approaches surfaced:

### Option A — Gmail API (Lane 1 preferred)
Gmail already syncs the primary Dreamhost inbox. Google MCP is already connected.
Rex queries Gmail MCP directly — no curl, no credentials on disk, no polling script.
Lane 1 is largely solved by what already exists.

### Option B — Inbound Webhook (Lane 2 preferred)
Dreamhost forwards `pip@zaudi.com` / `vera@zaudi.com` to a webhook service.
Service parses the email and POSTs structured JSON to a Flask endpoint.
- **Mailgun inbound routing** — free tier, push not poll, clean JSON payload
- **Cloudflare Email Workers** — more control, no third party, routes to Flask
No polling, no cron, no UID tracking needed.

### Option C — Flask `/imap/poll` endpoint (fallback)
Add a poll route to Flask. Credentials stay inside the container.
Windows scheduled task or browser button just pokes `POST /imap/poll`.
Simpler than raw curl scripts. UID tracking still needed.

---

## Browser + Phone Access

Flask is already network-accessible. Docker compose binds `"5000:5000"` with no
explicit address — Docker defaults to `0.0.0.0` on the Windows host.

**On home WiFi:** `http://192.168.x.x:5000` from phone browser. Already works.
Get the IP via `ipconfig` on the Windows host. Windows Firewall may need port 5000
allowed for private networks.

**Outside home network:** Tailscale. One install on Windows host, phone joins tailnet.
Stable private URL from anywhere. No port forwarding, no public exposure.

**UI trigger:** A "Check Mail" button in the existing frontend calling `/imap/poll`
fits the existing pattern. SSE already in place — results could stream back in real time.

---

## Infrastructure (Ash)

### Credentials
- Dedicated app password per mailbox. Not the master account password.
- Stored in a credential file with restricted permissions — not in script source.
- curl reads via `--netrc-file` or environment variable.

### UID Tracking
- Flat file per mailbox: `last_uid_pip.txt`, `last_uid_primary.txt`
- Poll fetches UIDs > last seen. Update file on successful pull.
- On Lane 2: delete message by UID after successful parse and drop.

### curl pattern (headers only, UID-based)
```bash
curl -u "$CREDS" --netrc-file .netrc -s \
  "imaps://imap.dreamhost.com/INBOX" \
  --request "UID SEARCH UID $LAST_UID:*"
```
Fetch body only after UID list obtained and filtered.

### Cron
- Windows Scheduled Task — runs every 5–15 min depending on urgency feel
- Separate tasks per mailbox (primary, pip, vera) for independent failure handling
- Logs to `app/logs/imap_poller.log` — rotating, not permanent

### Output
- Parsed result written as `.md` to `C:\Users\termi\Dropbox\Incoming\`
- Filename: `{date}-{source}-{intent}.md` e.g. `2026_0405-vera-idea.md`
- Existing watcher handles from there — no new downstream infrastructure needed

---

## Build Owners

| Component | Owner |
|---|---|
| curl poller script | Rex |
| Subject/body parser | Rex |
| Vera integration (Idea/Todo write) | Vera / Rex |
| Pip pin formatter | Pip / Rex |
| Cron task + credential handling | Ash |
| Dreamhost mailbox setup | User |

---

## Open Questions

- Mailbox names final? (`pip@zaudi.com`, `vera@zaudi.com`) — confirm before creating on Dreamhost
- Poll interval — 5 min or 15 min?
- Primary inbox: LLM triage call (cost) vs rule-based (simpler)? 
- Should Lane 2 have a `[NOTE:]` prefix for freeform capture that isn't an Idea or Todo?

---

## Related
- `2026_0316-proposal-queue-design.md` — existing queue design
- Pip's calendar pipe — conceptual predecessor to Lane 2
- `Dropbox\Incoming` watcher — downstream, no changes needed
