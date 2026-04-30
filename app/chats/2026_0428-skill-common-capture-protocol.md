---
name: common-capture-protocol
description: Protocol for capturing todos, notes, ideas, feature requests, and pins into the MyBrain garden. Load this skill whenever Pip needs to capture something, route it to the right pipe, or rebuild a lost template. Also load when any persona needs to know which pipe to use for a given artifact type.
---

# Common Capture Protocol

## The Two Pipes

| Pipe | Use for | How |
|---|---|---|
| Email (primary) | todos, notes, ideas, feature requests | Send to `mybrain@zaudi.com` |
| YAML pin | buscards, receipts, structured pipeline items | Drop in `E:\_Processing\incoming\` |

When in doubt: **email pipe**.

## Email Pipe

### Pip Header (required on all email captures)
```
Pip ver: 1.0 | YYYY-MM-DD | source: <session|gmail|mobile>
```

### Subject Prefix → Parser Routing
| Subject prefix | Creates |
|---|---|
| `[todo]` | Todo node |
| `[note]` | Note node |
| `[idea]` | Idea node |
| `[feature request]` | Feature request node |

---

### [todo] Template
```
Subject: [todo] <title>

Pip ver: 1.0 | YYYY-MM-DD | source: <session|gmail|mobile>

description: <What needs to be done>
status: open
priority: high | medium | low
friction: phone-call | difficult | uncertain | boring |
          waiting-on-other | hated-meeting | procrastination
due: YYYY-MM-DD
context: <Short situational note>
notes: <Qualifying details, exceptions>
```

### [note] Template
```
Subject: [note] <title>

Pip ver: 1.0 | YYYY-MM-DD | source: <session|gmail|mobile>

summary: <One line — what is this about?>
context: <Where did this come from? What prompted it?>
url: <if applicable — omit if not>
body:
<Freeform content — prose, bullets, whatever>
```

### [idea] Template
```
Subject: [idea] <title>

Pip ver: 1.0 | YYYY-MM-DD | source: <session|gmail|mobile>

summary: <One line — what is this pointing at?>
spark: <What triggered this? Article, session, observation, conversation?>
potential: <What could this become or enable?>
connects_to: <Existing node, project, or idea — or omit>
status: open
priority: high | medium | low
owner: <persona or "user">
tags: <comma-separated>
body:
<Freeform — the full thought, the excitement, the thread to pull>
```
> ⚠️ `spark`, `potential`, `connects_to` — parser update pending as of 2026-04-25.

### [feature request] Template
```
Subject: [feature request] <title>

Pip ver: 1.0 | YYYY-MM-DD | source: <session|gmail|mobile>

summary: <What should exist that doesn't? One clear sentence.>
status: open
priority: high | medium | low
pain_point: <Cost or friction of not having this — or "none">
problem: <What breaks or goes uncaptured without it?>
proposed: <What should the system do? Key behaviours.>
owners: <Persona, default: "user">
notes: <Observations, open questions>
```

---

## YAML Pin Pipe

### Naming Convention
```
{YYYY_MMDD}-{type}-{descriptor}.yaml
```

### Rules
- Drop in `E:\_Processing\incoming\`
- Any field you invent may be lost — put unknowns in `description`
- Pin types and field schemas: see Pip persona

---

## Rebuilding Lost Gmail Templates

If Gmail draft templates are missing, regenerate from this skill.
One draft per type. To: `mybrain@zaudi.com`.
Subject exactly as shown. Body = template above, verbatim.
After creating: output linked subject line as `[subject](url)` using threadId.
