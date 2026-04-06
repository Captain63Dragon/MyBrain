# Queue Design Spec
**Date:** 2026-03-16
**Revised:** 2026-03-17 by Vera
**Author:** Vera
**Status:** Active — reflects implemented graph state

---

## Core Principle

> **Pipeline and compression.** Strip the clutter. Identify the nuggets.
> Track what matters. Annotate what doesn't speak for itself.

The queue is a typed, relational, living graph of intent.
Pip fills the hopper. Vera triages and watches. Rex writes and builds.
Walter handles finance. The owner decides. Nothing slips.

---

## Item Types

| Type | Description | Channel |
|---|---|---|
| `Todo` | Actionable. Has a next step. | Pin, Rex discovery, Vera observation |
| `Idea` | Not yet actionable. Worth holding. | Vera |
| `Reference` | Fileable. No action required. | Pipeline to graph |

Pip does not classify. Pip captures. Triage is Vera's job.

---

## Vera's Domain — Schema

### Nodes Vera creates and manages
- `(:Todo)` — creates, updates status, closes
- `(:Idea)` — creates, updates status, promotes to Todo

### Relationships Vera owns
```
(:Persona)-[:MADE_TODO]->(:Todo)       — channel, not source. Conscious origin only.
                                         Pin-originated todos: use source_pin property.
(:User)-[:ASSIGNED]->(:Todo)           — ownership. Vera creates, removes, reassigns.
(:Todo)-[:BLOCKED_BY]->(:Todo)         — state. Vera creates and resolves.
(:Idea)-[:EVOLVED_INTO]->(:Todo)       — promotion. Vera executes.
(:User)-[:NUDGED {count, last_asked}]->(:Todo)  — friction tracking. Not blame.
```

### Todo node — key properties
```
todo-id, description, status, priority, owner, friction, created
source_pin   — filename of originating pin. Pip implied, not recorded as a node.
```

### Retention
Everything is kept. `status = 'done'` closes a todo. Nothing is deleted.
The graph is the audit trail.

### Already-done items
Do not enter the queue. Pip drops a note; it becomes a Reference or annotation. 
The queue is for open intent only.

---

## Channels, Not Sources

The owner is master of the system. All todos ultimately trace to owner intent.
Channel = who surfaced it:
- **Pin** → `source_pin` on the Todo node. Pip implied.
- **Rex** → `(:Persona {name:'Rex'})-[:MADE_TODO]->(:Todo)` when uncovered in code/work.
- **Vera** → `(:Persona {name:'Vera'})-[:MADE_TODO]->(:Todo)` when spotted in scheduling review.

Rex drops todos unassigned. Vera triages and assigns.

---

## Friction Field

`friction` on Todo captures *why* something stalls:
- `none` — desk task, no resistance
- `phone-call` — requires calling someone
- `difficult` — emotionally or logistically hard
- `waiting-on-other` — blocked by someone else

Any todo with `phone-call` or `difficult` open more than 7 days: Vera escalates every session.
NUDGED tracks how many times. Vera uses charm before she leans on the count.

---

## What Is Not In Scope
- Walter's financial queue — separate concern
- Pip's capture format — upstream of this spec
- Multi-user — single owner, single room

---

*Vera — 2026-03-17*
