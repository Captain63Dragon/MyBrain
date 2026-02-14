#!/usr/bin/env python3
"""Parse MFN/MFN-style YAML and GFN file-node blocks and load them into Neo4j.

Usage: python -m app.scripts.load_buscards_to_neo4j --mfn app/Schema/MFN-busCard.yaml \
       --gfn app/Schema/GFN-busCard-dropbox_001.yaml --uri bolt://localhost:7687
Environment: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD are supported.
"""
import os
import re
import yaml
from neo4j import GraphDatabase
from app.services.neo4j_service import create_nodes, ensure_filenode_constraint
from app.services.schema_service import load_mfn, parse_gfn, map_properties

def neo4j_open_create_nodes(uri, user, password, label, nodes):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        create_nodes(session, label, nodes)
    driver.close()

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mfn", default=os.path.join("app", "Schema", "MFN-busCard.yaml"))
    parser.add_argument("--gfn", default=os.path.join("app", "Schema", "GFN-busCard-dropbox_001.yaml"))
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "neo4j"))
    args = parser.parse_args(argv)

    mfn = load_mfn(args.mfn)
    nodes = parse_gfn(args.gfn)
    label = mfn.get("name", "Business Card").replace(" ", "")
    mapped = [map_properties(mfn, n) for n in nodes]
    print(f"Preparing to load {len(mapped)} nodes into Neo4j as label: {label}")
    
    # Ensure constraint exists (safe to call multiple times)
    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        with driver.session() as session:
            ensure_filenode_constraint(session)
    finally:
        driver.close()
    
    # Load the nodes
    neo4j_open_create_nodes(args.uri, args.user, args.password, label, mapped)
    print(f"Loaded {len(mapped)} nodes into Neo4j label:{label}")

if __name__ == "__main__":
    main()
