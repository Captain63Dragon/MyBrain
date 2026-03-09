# Services required to work with Graph database Neo4j.
from app.models import neo4j
from pathlib import Path
import json
from datetime import datetime
from app.scripts.mfn_search_dir import BusinessCardEvaluator
from app.services.schema_service import load_mfn, parse_gfn, map_properties
from app.services.mfi_broker import push_result
from app.services.filesystem_service import (
    mfn_to_schema, 
    build_node_fields, 
    suggest_file_node_id,
    suggest_secondary_id,
    derive_file_node_id,
)


from app.shared.mfi_shared import (
    decode,
    completed_path,
    move_to_processing,
    CopyResultMFI,
)


def ensure_filenode_constraint(session):
    """Ensure the FILE-NODE-id uniqueness constraint exists on FileNode label"""
    try:
        session.write_transaction(
            lambda tx: tx.run(
                "CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (f:FileNode) REQUIRE f.`FILE-NODE-id` IS UNIQUE"
            )
        )
        return True
    except Exception as e:
        print(f"Warning: Could not create FileNode constraint: {e}")
        return False

def ensure_mfn_constraint(session):
    """Ensure the MFN-id uniqueness constraint exists on MetaFileNode label"""
    try:
        session.write_transaction(
            lambda tx: tx.run(
                "CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (m:MetaFileNode) REQUIRE m.`MFN-id` IS UNIQUE"
            )
        )
        return True
    except Exception as e:
        print(f"Warning: Could not create MetaFileNode constraint: {e}")
        return False

def serialize_mfn_node(mfn):
    """
    Serialize a loaded MFN yaml dict into flat Neo4j-compatible properties.
    core_properties and optional_properties are dicts — serialize as JSON strings.
    system_properties is a list — stays as native Neo4j list.
    Legacy/pipeline fields included as-is with fallback serialization.
    """
    json_fields = {
        'core_properties', 'optional_properties',
        'remove_source', 'system_properties'
    }
    # system_properties is a list — Neo4j can store it natively
    list_fields = {
        'system_properties'
    }
    skip_fields = {
        'META-FILE-NODE'
    }

    props = {}
    for k, v in mfn.items():
        if k in skip_fields:
            continue
        if k in list_fields:
            props[k] = v if isinstance(v, list) else [v]
        elif k in json_fields:
            props[k] = json.dumps(v)
        elif isinstance(v, (dict, list)):
            props[k] = json.dumps(v)
        else:
            props[k] = v

    return props


def create_mfn_node(session, mfn):
    """
    Create or update a MetaFileNode in Neo4j from a loaded MFN dict.
    Labels: MetaFileNode (universal) + Meta{Name} (specific)
    e.g. MetaFileNode:MetaBusinessCard
    """
    name = mfn.get('name', 'Unknown').replace(' ', '')
    specific_label = f"Meta{name}"
    node_id = mfn.get('MFN-id')

    props = serialize_mfn_node(mfn)
    props.pop('MFN-id', None)

    for k, v in list(props.items()):
        if isinstance(v, str) and v.strip() == '':
            props[k] = None

    session.write_transaction(
        lambda tx, nid=node_id, p=props: tx.run(
            f"MERGE (m:MetaFileNode:{specific_label} {{`MFN-id`: $nid}}) SET m += $p",
            nid=nid, p=p
        )
    )

# Given a node label like BusinessCard and a list of nodes to create from a Grouped-File-Node yaml source file
# generate the Cypher and execute to load into the Neo4j database
def create_nodes(session, label, nodes):
    """Create or update nodes with given label"""
    for n in nodes:
        nid = n.get("FILE-NODE-id")
        props = n.copy()
        props.pop("FILE-NODE-id", None)
        # convert any empty strings to None to avoid clutter
        for k, v in list(props.items()):
            if isinstance(v, str) and v.strip() == "":
                props[k] = None
        session.write_transaction(lambda tx, file_node_id=nid, props=props: tx.run(
            f"MERGE (b:{label}:FileNode {{`FILE-NODE-id`:$file_node_id}}) SET b += $props", 
            file_node_id=file_node_id, props=props
        ))


def create_node( session, label, node):
    create_nodes( session, label, [node])

def create_nodes_with_relationships(session, label: str, nodes: list):
    for n in nodes:
        related = n.pop('_related', [])
        print(f"[import] {n.get('FILE-NODE-id')} — related: {len(related)}")        
        # create master node
        create_nodes(session, label, [n])
        
        # create stubs and wire relationships
        for entry in related:
            rel_type = entry['relationship']
            stub = entry['node'].copy()
            
            # create stub node
            create_nodes(session, label, [stub])
            
            # wire relationship
            stub_id = stub.get('FILE-NODE-id')
            master_id = n.get('FILE-NODE-id')
            
            session.write_transaction(lambda tx, sid=stub_id, mid=master_id, rt=rel_type: tx.run(
                f"""
                MATCH (stub:FileNode {{`FILE-NODE-id`: $stub_id}})
                MATCH (master:FileNode {{`FILE-NODE-id`: $master_id}})
                MERGE (stub)-[:{rt}]->(master)
                """,
                stub_id=sid,
                master_id=mid
            ))
    
def verify_FNid_exists(self, node_id):
    """Verify FILE-NODE-id exists in database"""
def verify_FNid_exists(node_id):
    if not node_id:
        return False, "Node ID is null"
    
    query = """
    MATCH (n:FileNode)
    WHERE n.`FILE-NODE-id` = $node_id
    RETURN count(n) as count
    """
    
    with neo4j.get_session() as session:
        result = session.run(query, node_id=node_id)
        record = result.single()
        count = record["count"] if record else 0
        
        if count > 0:
            return True, f"Node ID exists in database: {node_id} (count: {count})"
        else:
            return False, f"Node ID not found in database: {node_id}"

def get_file_nodes():
    """Retrieve all FileNode records"""
    query = """
    MATCH (n:FileNode) 
    RETURN n.`FILE-NODE-id` as id, 
            n.`META-FILE-NODE` as meta, 
            n.filepath as fpath, 
            n.path as mpath
    """
    with neo4j.get_session() as session:
        result = session.run(query)
        return [dict(record) for record in result]

def get_mfn_patterns(mfn_id: str) -> list:
    """Extract filename_contains patterns from a MetaFileNode."""
    with neo4j.get_session() as session:
        mfn = get_mfn(mfn_id, session)
        if not mfn:
            return []
        return [p['pattern_value'] for p in mfn.get('patterns', [])
                if p.get('pattern_type') == 'filename_contains']

def search_for_file_node(search_paths=None, properties=None):
    """Retrieve all paths and filenodes matching search criteria.
    
    Args:
        search_paths: list of path patterns to search, or None for defaults
        properties: dict of {property_key: search_value} filters
    
    Returns:
        List of matching nodes with their properties
    """
    if search_paths is None:
        # search_paths = get_default_search_paths()  # your "usual places"
        search_paths = ["C:\\Users\\termi\\dropbox\\"]
    if properties is None:
        # This generates all nodes in these paths
        properties = {}
    query, params = build_filenode_search_query(search_paths, properties)
    debug_query = query
    for key, value in params.items():
        debug_query = debug_query.replace(f'${key}', f"'{value}'")
    # print(f"Debug query with substitutions:\n{debug_query}")
    # Execute and return results
    with neo4j.get_session() as session:
        result = session.run(query, parameters=params)
        records = [record.data() for record in result]    

        mfn_result = session.run(
            "MATCH (m:MetaFileNode {`MFN-id`: 'BusinessCard_20260121'}) RETURN m"
        ).single()
        mfn = {'meta_file_node': dict(mfn_result['m'])} if mfn_result else {}

    return [{'debug_query': debug_query}] + ([mfn] if mfn else []) + records

def scan_directory_to_nodes(scan_path: str, mfn_id: str, min_confidence: float = 0.5) -> dict:
    with neo4j.get_session() as session:

        mfn = get_mfn(mfn_id, session)
        if not mfn:
            return {'error': f'MFN not found: {mfn_id}'}

        schema    = mfn_to_schema(mfn)
        evaluator = BusinessCardEvaluator(schema)
        matches   = evaluator.evaluate_directory(scan_path, min_confidence=min_confidence)

        results = {'created': [], 'exists': [], 'errors': []}

        for metadata in matches:
            try:
                checker = lambda pid: not verify_FNid_exists(pid)[0]
                node_id = suggest_file_node_id(metadata.filepath, checker)

                exists, _ = verify_FNid_exists(node_id)
                if exists:
                    bucket = 'exists'
                else:
                    fields = build_node_fields(metadata, mfn)
                    create_node(session, 'BusinessCard', {**fields, 'FILE-NODE-id': node_id})
                    bucket = 'created'

            except Exception as e:
                bucket = 'errors'
                results[bucket].append({
                    'node_id':    getattr(metadata, 'filename', 'unknown'),
                    'filename':   metadata.filename,
                    'confidence': metadata.confidence_score,
                    'error':      str(e),
                })
                continue

            results[bucket].append({
                'node_id':    node_id,
                'filename':   metadata.filename,
                'confidence': metadata.confidence_score,
            })

        return {
            'status':  'ok',
            'mfn_id':  mfn_id,
            'path':    scan_path,
            'matched': len(matches),
            'created': len(results['created']),
            'exists':  len(results['exists']),
            'errors':  len(results['errors']),
            'detail':  results,
        }

def get_mfn(mfn_id: str, session) -> dict | None:
    """Pull a MetaFileNode from Neo4j, deserialize JSON string fields."""
    result = session.run(
        "MATCH (m:MetaFileNode {`MFN-id`: $id}) RETURN m",
        id=mfn_id
    )
    record = result.single()
    if not record:
        return None
    props = dict(record['m'])
    for field in ('core_properties', 'optional_properties', 'patterns', 'remove_source'):
        if field in props and isinstance(props[field], str):
            try:
                props[field] = json.loads(props[field])
            except json.JSONDecodeError:
                pass
    return props


def build_filenode_search_query(search_paths, properties, return_fields=None):
    """Build Cypher query dynamically based on filters
    
        Example query:
        MATCH (f:FileNode)
        WHERE f.filepath STARTS WITH 'C:\\Users\\termi\\Dropbox\\'
          AND toLower(f.company) CONTAINS toLower('toyota')
        RETURN f.filepath, f.`FILE-NODE-id`, f.company, f
    """
    
    # Base MATCH
    query_parts = ["MATCH (fnode:FileNode)"]
    
    # WHERE clauses
    where_clauses = ["NOT fnode:MetaBusinessCard"]
    params = {}
    
    # Add path filters
    if search_paths:
        # For multiple paths, use OR
        path_conditions = " OR ".join([
            f"toLower(fnode.filepath) STARTS WITH toLower($path{i})" 
            for i in range(len(search_paths))
        ])
        where_clauses.append(f"({path_conditions})")
        for i, path in enumerate(search_paths):
            params[f'path{i}'] = path
    
    # Add property filters
    for key, value in properties.items():
        param_name = f"prop_{key}"
        where_clauses.append(f"toLower(fnode.`{key}`) CONTAINS toLower(${param_name})")
        params[param_name] = value
    
    # Combine WHERE
    if where_clauses:
        query_parts.append("WHERE " + " AND ".join(where_clauses))
    
    # RETURN clause
    # if return_fields is None:
    #     return_fields = ['filepath', 'FILE-NODE-id', 'company']
    
    # return_items = [f"fnode.`{field}`" for field in return_fields] + ['fnode']
    # query_parts.append("RETURN " + ", ".join(return_items))
    query_parts.append("RETURN fnode")
    
    query = "\n".join(query_parts)
    return query, params

def delete_file_node(node_id):
    return delete_file_nodes([node_id])

def delete_file_nodes(node_ids):
    if not node_ids:
        return {'status': 'error', 'message': 'No node IDs provided'}
    
    query = """
        MATCH (n:FileNode)
        WHERE n.`FILE-NODE-id` IN $node_ids
        WITH collect(n) as nodes, count(n) as deleted
        FOREACH (n in nodes | DETACH DELETE n)
        RETURN deleted
    """
    with neo4j.get_session() as session:
        result = session.run(query, parameters={'node_ids': node_ids})
        record = result.single()
        deleted_count = record['deleted'] if record else 0
    
    return {'status': 'ok', 'deleted': deleted_count}

def update_file_node(node_id, fields):
    query = """
        MATCH (n:FileNode)
        WHERE n.`FILE-NODE-id` = $node_id
        SET n += $fields
        RETURN n
    """
    with neo4j.get_session() as session:
        result = session.run(query, parameters={'node_id': node_id, 'fields': fields})
        record = result.single()
        return {'status': 'ok'} if record else {'status': 'error', 'message': 'Node not found'}


def normalize_path_for_cypher(path_string):
    """Convert path to Cypher-ready string matching Windows format in DB"""
    normalized = Path(path_string)
    
    # Escape backslashes for Cypher (\ becomes \\)
    cypher_path = str(normalized).replace('\\', '\\\\')
    
    # Ensure trailing double-backslash
    if not cypher_path.endswith('\\\\'):
        cypher_path += '\\\\'
    
    return cypher_path

def write_os_result(session, mfi, status: str, errors: list, created_node_id: str = ''):
    session.run("""
        MATCH (d:Dispatch {`mfi-id`: $source_mfi_id})
        WHERE NOT (d)-[:RESULTED_IN]->()
        CREATE (r:OSResult {
            mfi_id:          $mfi_id,
            status:          $status,
            intent:          $intent,
            node_id:         $node_id,
            created_node_id: $created_node_id,
            errors:          $errors,
            error_count:     $error_count,
            created:         $created
        })
        CREATE (d)-[:RESULTED_IN]->(r)
        SET d.status = $status
    """,
        source_mfi_id    = mfi.source_mfi_id,
        mfi_id           = mfi.mfi_id,
        status           = status,
        intent           = mfi.intent,
        node_id          = mfi.node_id,
        created_node_id  = created_node_id,
        errors           = errors,
        error_count      = len(errors),
        created          = datetime.now().isoformat()
    )

def create_dispatch_node(mfi_id: str, action: str, mfn_id: str, source: str) -> dict:
    """
    Create a Dispatch node in Neo4j when an MFI is written to pending.
    Links to the MFN that orchestrated it.
    """
    query = """
        MATCH (m:MetaFileNode {`MFN-id`: $mfn_id})
        CREATE (d:Dispatch {
            `mfi-id`:   $mfi_id,
            action:     $action,
            source:     $source,
            status:     'pending',
            created:    $created
        })
        CREATE (m)-[:ORCHESTRATES]->(d)
        RETURN d
    """
    with neo4j.get_session() as session:
        result = session.run(query,
            mfi_id=mfi_id,
            action=action,
            mfn_id=mfn_id,
            source=source,
            created=datetime.now().isoformat()
        )
        record = result.single()
        return {'status': 'ok'} if record else {'status': 'error'}
    
def make_checker(session):
    # create a closure that uses the passed in session to check for existing nodes
    def checker(pid):
        result = session.run(
            "MATCH (n:FileNode {`FILE-NODE-id`: $id}) RETURN n",
            id=pid
        )
        return result.single() is None
    return checker

def process_discovery_results() -> dict:
    """
    Read completed/ folder, process scan_directory_result MFI files.
    For each matched file: create FileNode, link to Dispatch via CREATED.
    Create OSResult node, link to Dispatch via RESULTED_IN.
    """
    from app.shared.mfi_shared import (
        decode, completed_path, DiscoveryResultMFI
    )

    completed = completed_path()
    print(f"Looking in: {completed}")
    if not completed.exists():
        return {'status': 'ok', 'processed': 0, 'message': 'completed/ empty'}

    mfi_files = list(completed.glob('*.mfi'))
    print(f"Files found: {mfi_files}")
    if not mfi_files:
        return {'status': 'ok', 'processed': 0, 'message': 'nothing to process'}

    summary = {'processed': 0, 'nodes_created': 0, 'errors': []}

    with neo4j.get_session() as session:
        checker = make_checker(session)
        for mfi_path in mfi_files:
            try:
                dispatch_summary = {'nodes_created': 0,'collisions': [],'errors': [],'insitu': []}
                mfi = decode(str(mfi_path))
                print(f"Decoded: {type(mfi).__name__} - {mfi.action}")
                print(f"isinstance check: {isinstance(mfi, DiscoveryResultMFI)}")

                if not isinstance(mfi, DiscoveryResultMFI):
                    continue                    # not ours — leave it

                # ── Process each matched file ─────────────────────────────────
                for file_entry in mfi.files:
                    try:
                        node_id = derive_file_node_id(file_entry['filepath'], file_entry.get('mtime', ''))
                        print(f"[discovery] filepath: {file_entry['filepath']}")
                        print(f"[discovery] generated node_id: {node_id}")

                        already_exists = not checker(node_id)
                        print(f"[discovery] exists={already_exists}")

                        fields = {
                            'filepath':        file_entry['filepath'],
                            'reviewed':        False,
                            'review_priority': 5,
                            'pattern_matched': file_entry.get('mask_matched', ''),
                            'descriptor':      file_entry.get('descriptor', ''),
                            'date':            file_entry.get('date') or file_entry.get('mtime', ''),
                        }

                        print(f"[discovery] fields: {fields}")
                        print(f"[discovery] source_mfi_id: {mfi.source_mfi_id}")

                        result = session.run("""
                            MATCH (n:FileNode {filepath: $filepath})-[:INSITU_COPY_OF]->()
                            RETURN n
                        """, filepath=file_entry['filepath'])

                        if result.single():
                            print(f"[discovery] INSITU — skipping: {node_id}")
                            dispatch_summary.setdefault('insitu', []).append(node_id)
                            continue

                        session.run("""
                            MATCH (d:Dispatch {`mfi-id`: $source_mfi_id})
                            MERGE (n:FileNode {`FILE-NODE-id`: $node_id})
                            ON CREATE SET n += $fields, n:`BusinessCard`
                            CREATE (d)-[:CREATED]->(n)
                            RETURN n
                        """,
                            source_mfi_id = mfi.source_mfi_id,
                            node_id       = node_id,
                            fields        = fields
                        )

                        if already_exists:
                            dispatch_summary.setdefault('collisions', []).append(node_id)
                            print(f"[discovery] COLLISION: {node_id}")
                        else:
                            dispatch_summary['nodes_created'] += 1
                            print(f"[discovery] CREATED: {node_id}")

                    except Exception as e:
                        print(f"[discovery] ERROR: {file_entry.get('filepath')} — {e}")
                        dispatch_summary['errors'].append({
                            'filepath': file_entry.get('filepath', 'unknown'),
                            'error':    str(e)
                        })

                # ── OSResult — after all file work, before unlink ─────────────
                status = 'failure(s)' if dispatch_summary.get('errors') else 'completed'
                session.run("""
                    MATCH (d:Dispatch {`mfi-id`: $source_mfi_id})
                    WHERE NOT (d)-[:RESULTED_IN]->()
                    CREATE (r:OSResult {
                        mfi_id:          $mfi_id,
                        status:          $status,
                        file_count:      $file_count,
                        nodes_created:   $nodes_created,
                        collisions:      $collisions,
                        collision_count: $collision_count,
                        errors:          $errors,
                        error_count:     $error_count,
                        created:         $created
                    })
                    CREATE (d)-[:RESULTED_IN]->(r)
                    SET d.status = $status
                    RETURN r
                """,
                    source_mfi_id   = mfi.source_mfi_id,
                    mfi_id          = mfi.mfi_id,
                    file_count      = len(mfi.files),
                    nodes_created   = dispatch_summary.get('nodes_created', 0),
                    collisions      = dispatch_summary.get('collisions', []),
                    collision_count = len(dispatch_summary.get('collisions', [])),
                    errors          = [e['error'] for e in dispatch_summary.get('errors', [])],
                    error_count     = len(dispatch_summary.get('errors', [])),
                    status          = status,
                    created         = datetime.now().isoformat()
                )
                push_result(mfi.mfi_id, {
                    'status':        status,
                    'nodes_created': dispatch_summary.get('nodes_created', 0),
                    'collisions':    len(dispatch_summary.get('collisions', [])),
                    'errors':        len(dispatch_summary.get('errors', []))
                })

                mfi_path.unlink()               # after graph work — no ghost state
                summary['processed'] += 1

            except Exception as e:
                summary['errors'].append({
                    'file': mfi_path.name,
                    'error': str(e)
                })

    summary['status'] = 'ok'
    return summary

def process_copy_results() -> dict:
    """
    Read completed/ folder, process copy_result MFI files.
    Branches on intent:
        insitu_copy   — update original filepath, create stub node, INSITU_COPY_OF
        master_source — source is master, create secondary at target, COPY_OF
        master_target — target is master, update master filepath, create secondary at source, COPY_OF
    """
    from app.shared.mfi_shared import (
        decode, move_to_processing, completed_path, CopyResultMFI
    )

    completed = completed_path()
    if not completed.exists():
        return {'status': 'ok', 'processed': 0, 'message': 'completed/ empty'}

    mfi_files = list(completed.glob('*.mfi'))
    if not mfi_files:
        return {'status': 'ok', 'processed': 0, 'message': 'nothing to process'}

    summary = {'processed': 0, 'errors': []}

    with neo4j.get_session() as session:
        checker = make_checker(session)
        for mfi_path in mfi_files:
            try:
                mfi = decode(str(mfi_path))
                if not isinstance(mfi, CopyResultMFI):
                    continue
                mfi_path.unlink()
                if not mfi.success:
                    err = mfi.error
                    print(f"[copy] OS failed: {err}")
                    write_os_result(session, mfi, status='failed', errors=[err])
                    push_result(mfi.mfi_id, {'status': 'failed', 'intent': mfi.intent, 'error': err})
                    summary['errors'].append({'mfi': mfi_path.name, 'error': err})
                    summary['processed'] += 1
                    continue

                matched = session.run("""
                    MATCH (n:FileNode {`FILE-NODE-id`: $node_id})
                    RETURN count(n) AS matched
                """, node_id=mfi.node_id).single()['matched']

                if matched == 0:
                    err = f"Node not found in graph: {mfi.node_id}"
                    print(f"[copy] {err}")
                    write_os_result(session, mfi, status='failed', errors=[err])
                    push_result(mfi.mfi_id, {'status': 'failed', 'intent': mfi.intent, 'error': err})
                    summary['errors'].append({'mfi': mfi_path.name, 'error': err})
                    summary['processed'] += 1
                    continue

                if mfi.intent == 'insitu_copy':
                    created_node_id = mfi.node_id + '_insitu'

                    session.run("""
                        MATCH (original:FileNode {`FILE-NODE-id`: $node_id})
                        SET original.filepath = $target
                        MERGE (stub:FileNode {`FILE-NODE-id`: $stub_id})
                        ON CREATE SET stub.filepath = $source,
                                      stub.reviewed = true,
                                      stub.review_priority = 0
                        MERGE (stub)-[:INSITU_COPY_OF]->(original)
                        WITH stub
                        MATCH (d:Dispatch {`mfi-id`: $source_mfi_id})
                        CREATE (d)-[:CREATED]->(stub)
                    """,
                        node_id       = mfi.node_id,
                        stub_id       = created_node_id,
                        source        = mfi.source,
                        target        = mfi.target,
                        source_mfi_id = mfi.source_mfi_id,
                    )
                    print(f"[copy] insitu_copy: {mfi.node_id} → stub: {created_node_id}")

                elif mfi.intent == 'master_source':
                    created_node_id = suggest_secondary_id(mfi.node_id, checker)

                    session.run("""
                        MATCH (master:FileNode {`FILE-NODE-id`: $node_id})
                        MERGE (secondary:FileNode {`FILE-NODE-id`: $secondary_id})
                        ON CREATE SET secondary.filepath = $target,
                                      secondary.reviewed = true,
                                      secondary.review_priority = 0
                        MERGE (secondary)-[:COPY_OF]->(master)
                        WITH secondary
                        MATCH (d:Dispatch {`mfi-id`: $source_mfi_id})
                        CREATE (d)-[:CREATED]->(secondary)
                    """,
                        node_id       = mfi.node_id,
                        secondary_id  = created_node_id,
                        target        = mfi.target,
                        source_mfi_id = mfi.source_mfi_id,
                    )
                    print(f"[copy] master_source: {mfi.node_id} → secondary: {created_node_id}")

                elif mfi.intent == 'master_target':
                    created_node_id = suggest_secondary_id(mfi.node_id, checker)

                    session.run("""
                        MATCH (master:FileNode {`FILE-NODE-id`: $node_id})
                        SET master.filepath = $target
                        MERGE (secondary:FileNode {`FILE-NODE-id`: $secondary_id})
                        ON CREATE SET secondary.filepath = $source,
                                      secondary.reviewed = true,
                                      secondary.review_priority = 0
                        MERGE (secondary)-[:COPY_OF]->(master)
                        WITH secondary
                        MATCH (d:Dispatch {`mfi-id`: $source_mfi_id})
                        CREATE (d)-[:CREATED]->(secondary)
                    """,
                        node_id       = mfi.node_id,
                        secondary_id  = created_node_id,
                        source        = mfi.source,
                        target        = mfi.target,
                        source_mfi_id = mfi.source_mfi_id,
                    )
                    print(f"[copy] master_target: {mfi.node_id} → secondary: {created_node_id}")

                else:
                    print(f"[copy] Unknown intent: {mfi.intent} — skipping")
                    summary['errors'].append({'mfi': mfi_path.name, 'error': f"Unknown intent: {mfi.intent}"})
                    summary['processed'] += 1
                    continue                    # no Dispatch to link — no OSResult

                write_os_result(session, mfi, status='completed', errors=[],
                                created_node_id=created_node_id)
                push_result(mfi.mfi_id, {
                    'status': 'completed', 
                    'intent': mfi.intent, 
                    'node_id': mfi.node_id, 
                    'created_node_id': created_node_id
                })
                summary['processed'] += 1
                
            except Exception as e:
                print(f"[copy] ERROR: {mfi_path.name} — {e}")
                summary['errors'].append({'file': mfi_path.name, 'error': str(e)})

    summary['status'] = 'ok'
    return summary

def process_move_results() -> dict:
    """
    Read completed/ folder, process move_result MFI files.
    Branches on intent:
        move    — update filepath on existing node
        archive — update filepath + set archived flag
    """
    from app.shared.mfi_shared import (
        decode, completed_path, MoveResultMFI
    )

    completed = completed_path()
    if not completed.exists():
        return {'status': 'ok', 'processed': 0, 'message': 'completed/ empty'}

    mfi_files = list(completed.glob('*.mfi'))
    if not mfi_files:
        return {'status': 'ok', 'processed': 0, 'message': 'nothing to process'}

    summary = {'processed': 0, 'errors': []}

    with neo4j.get_session() as session:
        for mfi_path in mfi_files:
            try:
                mfi = decode(str(mfi_path))
                if not isinstance(mfi, MoveResultMFI):
                    continue
                mfi_path.unlink() 
                if not mfi.success:
                    print(f"[move] Skipping failed move: {mfi.error}")
                    summary['errors'].append({'mfi': mfi_path.name, 'error': mfi.error})
                    move_to_processing(mfi_path)
                    summary['processed'] += 1
                    continue

                if mfi.intent == 'move':
                    result = session.run("""
                        MATCH (n:FileNode {`FILE-NODE-id`: $node_id})
                        SET n.filepath = $target
                        RETURN count(n) AS matched
                    """, node_id=mfi.node_id, target=mfi.target)

                elif mfi.intent == 'archive':
                    result = session.run("""
                        MATCH (n:FileNode {`FILE-NODE-id`: $node_id})
                        SET n.filepath = $target,
                            n.archived  = true
                        RETURN count(n) AS matched
                    """, node_id=mfi.node_id, target=mfi.target)

                else:
                    print(f"[move] Unknown intent: {mfi.intent} — skipping")
                    summary['errors'].append({'mfi': mfi_path.name, 'error': f"Unknown intent: {mfi.intent}"})
                    summary['processed'] += 1
                    continue                    # no Dispatch to link — no OSResult

                matched = result.single()['matched']
                if matched == 0:
                    err = f"Node not found in graph: {mfi.node_id}"
                    print(f"[move] {err}")
                    write_os_result(session, mfi, status='failed', errors=[err])
                    push_result(mfi.mfi_id, {'status': 'failed', 'intent': mfi.intent, 'error': err})
                    summary['errors'].append({'mfi': mfi_path.name, 'error': err})
                    summary['processed'] += 1
                    continue

                print(f"[move] {mfi.intent}: {mfi.node_id} → {mfi.target}")
                write_os_result(session, mfi, status='completed', errors=[])
                push_result(mfi.mfi_id, {'status': 'completed', 'intent': mfi.intent, 'node_id': mfi.node_id})
                summary['processed'] += 1

            except Exception as e:
                print(f"[move] ERROR: {mfi_path.name} — {e}")
                summary['errors'].append({'file': mfi_path.name, 'error': str(e)})
                
    summary['status'] = 'ok'
    return summary

def load_gfn_nodes(mfn: dict, label: str, mapped: list[dict]):
    with neo4j.get_session() as session:
        ensure_filenode_constraint(session)
        ensure_mfn_constraint(session)
        create_mfn_node(session, mfn)
        create_nodes_with_relationships(session, label, mapped)
       
def get_export_nodes() -> list:
    with neo4j.get_session() as session:
        result = session.run("""
            MATCH (n:FileNode)
            WHERE NOT (n)-[:INSITU_COPY_OF]->()
              AND NOT (n)-[:COPY_OF]->()
            OPTIONAL MATCH (stub)-[r:INSITU_COPY_OF|COPY_OF]->(n)
            RETURN n, 
                   collect(
                     CASE WHEN stub IS NOT NULL 
                     THEN {rel: type(r), stub: properties(stub), stub_id: stub.`FILE-NODE-id`} 
                     ELSE NULL END
                   ) as related
            ORDER BY n.`FILE-NODE-id`
        """)
        rows = []
        for record in result:
            node = dict(record['n'])
            related = [r for r in record['related'] if r is not None]
            rows.append({'node': node, 'related': related})
    return rows