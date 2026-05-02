"""
tops_seed.py - One-time seed of TOPS data from JSON files into Neo4j.

Reads food_library.json and food_log.json from MetaFileQueues/tops/
and bulk-inserts into Neo4j as FoodLibrary and FoodLog nodes.
Wires [:LOGGED_ITEM] relationships where item names match library entries.

Run once. Safe to re-run - uses MERGE on primary keys to avoid duplicates.
"""
import json
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.neo4j_service import get_session

TOPS_PATH = Path(r'C:\Users\termi\MetaFileQueues\tops')
LIBRARY_FILE = TOPS_PATH / 'food_library.json'
LOG_FILE     = TOPS_PATH / 'food_log.json'


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def seed_library(session, items: list[dict]) -> int:
    result = session.run("""
        UNWIND $rows AS row
        MERGE (lib:FoodLibrary {item_id: row.item_id})
        SET lib = row
        RETURN count(lib) AS count
    """, rows=items)
    return result.single()['count']


def seed_log(session, entries: list[dict]) -> int:
    result = session.run("""
        UNWIND $rows AS row
        MERGE (log:FoodLog {log_id: row.log_id})
        SET log = row
        RETURN count(log) AS count
    """, rows=entries)
    return result.single()['count']


def wire_relationships(session) -> int:
    """Wire [:LOGGED_ITEM] from FoodLog to FoodLibrary by matching item name + venue."""
    result = session.run("""
        MATCH (log:FoodLog)
        MATCH (lib:FoodLibrary)
        WHERE log.item = lib.item_name
          AND log.venue = lib.venue
          AND NOT (log)-[:LOGGED_ITEM]->(lib)
        CREATE (log)-[:LOGGED_ITEM]->(lib)
        RETURN count(*) AS count
    """)
    return result.single()['count']


def run():
    print("[tops_seed] loading JSON files...")
    library = load_json(LIBRARY_FILE)
    log     = load_json(LOG_FILE)
    print(f"[tops_seed] {len(library)} library items, {len(log)} log entries")

    with get_session() as session:
        lib_count = seed_library(session, library)
        print(f"[tops_seed] FoodLibrary: {lib_count} nodes merged")

        log_count = seed_log(session, log)
        print(f"[tops_seed] FoodLog: {log_count} nodes merged")

        rel_count = wire_relationships(session)
        print(f"[tops_seed] [:LOGGED_ITEM] relationships wired: {rel_count}")

    print("[tops_seed] done.")


if __name__ == '__main__':
    run()
