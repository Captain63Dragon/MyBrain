# MyBrain — Project Summary for Next Context

## The Philosophy (Read This First)
MyBrain is a personal information operating system built on top of Windows.
The filesystem is treated as a dumb block store — a broken database with no 
relationships, no queries, no transactions. Neo4j is the authoritative layer.
Files live on disk. Meaning lives in the graph.

### The Walled Garden Model
Three tiers of file existence:

* **Wild Files** — unvetted raw material. Dropbox, camera rolls, desktops.
  They prompt ingestion. They don't owe you anything afterward.
* **The Garden** — curated, intentional, protected. E:\Reference and equivalents.
  Files that have been ingested, named, and enriched. Worth backing up.
* **The Node** — ground truth. The annotation, the relationship, the meaning.
  "Met while getting plaster" lives here safely, independent of the file's location.

The node owns its truth. The file does its best. The wild doesn't owe you anything.
This eliminates "shell game" anxiety — stop trying to maintain truth on both sides
simultaneously across a hostile environment.

### The Divide
Browsers cannot access the local filesystem. Docker containers have limited,
explicitly mounted access to Windows. Dynamic paths cannot be reliably mounted.
This is a fundamental architectural constraint, not a bug to fix.

---

## Tech Stack
* Neo4j graph database in Docker container
* Flask Python server in Docker container  
* Vanilla JS/HTML/CSS frontend
* Windows host running scripts and scheduled tasks
* Shared codebase — both container and Windows scripts import from same repo

---

## The MFI Protocol (Meta File Instruction)
A file-based messaging protocol bridges the divide. Think of them as socket 
messages — but file-based so you can see exactly what is happening at every step.
Both sides communicate via .mfi files (YAML format) written atomically 
(.mft → .mfi rename).

Three shared folders mounted as a Docker volume:
    C:/Users/termi/MetaFileQueues/    (Windows host)
    /mfi/                             (Docker container)
        pending/      UI out-box,     Windows in-box
        processing/   atomic lock,    work in progress
        completed/    Windows out-box, UI in-box

### MFI Classes (app/shared/mfi_shared.py)
All pure Python, no framework dependencies, importable by both Flask and Windows:

    MFIBase               — common fields: mfi_id, action, created, status
    DiscoveryMFI          — scan directory for matching files
    DiscoveryResultMFI    — results of directory scan, one entry per file
    CopyMFI               — copy a file, intent field carries semantics
    CopyResultMFI         — result of copy, echoes intent for processor
    MoveMFI               — move a file, intent field carries semantics
    MoveResultMFI         — result of move, echoes intent for processor

### Intent Field (cargo pattern)
Windows handlers don't care about intent — they just copy or move.
Intent is cargo passed through to the Flask result processor which branches on it:

    CopyMFI intents:
        insitu_copy    — copy + create stub node + INSITU_COPY_OF relationship
        master_source  — copy, source node is master, create _second_01 at target
        master_target  — copy, target node is master, update filepath, create _second_01 at source

    MoveMFI intents:
        move           — move file, update filepath on existing node
        archive        — move file, update filepath + set archived=true on node

---

## Graph Schema

    (MetaFileNode)-[:ORCHESTRATES]->(Dispatch)
    (Dispatch)-[:CONFIRMED_BY]->(OSResult)
    (Dispatch)-[:CREATED]->(FileNode)
    (FileNode)-[:INSITU_COPY_OF]->(FileNode)   ← stub points to master
    (FileNode)-[:COPY_OF]->(FileNode)           ← secondary points to master

### Node Semantics
* **Master node** — full metadata, unqualified id, authoritative filepath
* **Insitu stub** — lightweight, _insitu suffix, filepath = mobile/convenience location
* **Secondary copy** — lightweight, _second_01/_second_02 suffix, COPY_OF → master
* **Dispatch** — issued command, created simultaneously with MFI write
* **OSResult** — summary after processing, linked to Dispatch via CONFIRMED_BY
* **MetaFileNode** — policy engine and orchestrator, holds schema + rules for FileNode type

### Node ID Conventions
    buscard_test_beta_20260101          ← master, discovery-born
    buscard_test_beta_20260101_insitu   ← insitu stub
    buscard_test_beta_20260101_second_01 ← first secondary copy
    buscard_test_beta_20260101_second_02 ← second secondary copy

---

## API Endpoints (buscard_routes.py)

    POST /buscard/dispatch         — queue any action, action in payload
    POST /buscard/process          — process completed results, action in payload

### Dispatch actions:
    discovery          — write DiscoveryMFI, create Dispatch
    insitu_copy        — write CopyMFI(intent=insitu_copy), create Dispatch
    copy_master_source — write CopyMFI(intent=master_source), create Dispatch
    copy_master_target — write CopyMFI(intent=master_target), create Dispatch
    move               — write MoveMFI(intent=move), create Dispatch
    archive            — write MoveMFI(intent=archive), create Dispatch

### Process actions:
    discovery          — process_discovery_results()
    copy               — process_copy_results()  (all copy intents)
    move               — process_move_results()  (move + archive intents)

---

## Project Structure
    app/
        __init__.py
        routes/
            buscard_routes.py
        services/
            neo4j_service.py
            filesystem_service.py
        shared/
            __init__.py
            mfi_shared.py
        scripts/
            mfn_search_dir.py
            mfi_watcher.py
            test_reset.py        ← creates/resets test file fixtures + cleans MFI queues

---

## Current State — What Works
* Full discovery pipeline: scan → watcher → process → FileNodes in graph
* Full insitu_copy pipeline: dispatch → watcher → process → stub node + INSITU_COPY_OF
* Full move pipeline: dispatch → watcher → process → filepath update
* Archive intent: same as move + archived=true flag
* master_source / master_target copy: plumbing complete
* INSITU filter in process_discovery_results() — skips insitu stubs on re-discovery
* Test reset script with MFI queue cleanup
* JS faker with all action types wired

## Where We Are
Mid test cycle. Happy path test complete using:
    C:\Users\termi\MyBrain-test\        — mobile/source (test stand-in for Dropbox)
    C:\Users\termi\MyBrain-test-archive\ — garden/archive
    C:\Users\termi\MyBrain-test-backup\  — backup location

Test files:
    alpha   — discovery only, stays in test
    beta    — insitu_copy: test → test-archive, stub stays in test
    gamma   — move: test → test-backup
    delta   — archive: test → test-archive
    epsilon — copy_master_source x2: master in test, _second_01 to archive, _second_02 to backup
    zeta    — copy_master_target: source in test-backup, master promoted to test-archive

---

## Pinned TODOs (Next Steps in Priority Order)

### Immediate / In Progress
1. **Complete testing for common edge case errors ** 

### Near Term
2. **GFN Export** — GET /buscard/export. Single YAML file:
   # FILE-NODEs section — full nodes in source YAML format
   # INSITU-NODES section — stub nodes with insitu_copy_of field carrying relationship
   Use MFN schema for field order. Include reviewed flag. Skip pipeline fields.
   Importer deferred — export first, build importer when restore is needed.

3. **Delete action** — atomic dispatch, same MFI pipeline as copy and move.
   Single node or bulk (e.g. all secondaries of a master via COPY_OF relationship).

4. **File hash (MD5)** — compute at discovery time in watcher while filesystem accessible.
   Store as `file_hash` on FileNode. Enhance make_checker() to check ID + hash combination:
   - Neither exists → new file, create node
   - ID exists, hash matches → collision, handle as before  
   - ID exists, hash differs → same name/date, different file, suffix it
   - Hash exists, ID differs → duplicate file under different name, flag it
   Computed once at ingestion, never recomputed. Node holds the credential.

5. **Audit/verification script** — Windows side. For each garden FileNode (excluding stubs
   and secondaries), check filepath exists and hash matches. Four outcomes:
   file+hash match (good), file exists hash differs (corrupted/substituted),
   file missing (ghost), hash matches different path (moved without telling graph).

### Later
6. **ContainerChron** — Flask-side poller watching completed/ automatically
   rather than manually triggered process calls.

7. **Bulk copy/move** — This may occur naturally using multiple triggers of single endpoint.

### Architectural / Future
9. **PathRoot nodes** — reusable path anchors for insitu policy.
   (MFN)-[:TREATS_AS_INSITU]->(PathRoot {path: "C:\Users\termi\Dropbox"})
   Currently stored as JSON array on MFN. Migrate when sharing across MFNs is needed.

10. **Dispatch lifecycle** — resolved state when all PENDING_* relationships fulfilled.
    Ghost detection — unconfirmed Dispatch nodes after timeout.

11. **Wire patterns from MFN into discovery scan JS** — remove hardcoded patterns hack.

12. **Review queue service** — left panel surfacing FileNodes where reviewed=false,
    ordered by review_priority.

---

## Key Architectural Rules (Do Not Break)
* `+=` Cypher is sacred for node updates
* `normalize_path_for_cypher()` for Cypher string literals ONLY, not parameterized queries
* `make_checker(session)` not `verify_FNid_exists()` inside open sessions
* `__init__.py` imports inside `create_app()` — critical for Windows scripts to import
  app.shared without triggering Flask/Neo4j/routes chain
* Result files in completed/ are unlinked after processing (not moved to processing)
* Instruction files in completed/ are audit trail — left untouched by processor
* Intent is cargo — Windows handlers ignore it, Flask result processor branches on it

## Test Fixtures (Cypher)
    Wipe all except MFN:
        MATCH (n) WHERE NOT n:MetaFileNode DETACH DELETE n
    Check insitu relationships:
        MATCH (stub:FileNode)-[:INSITU_COPY_OF]->(original:FileNode)
        RETURN stub, original
    Check secondary relationships:
        MATCH (secondary:FileNode)-[:COPY_OF]->(master:FileNode)
        RETURN secondary, master