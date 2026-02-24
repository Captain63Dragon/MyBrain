# Services required to work with Graph database Neo4j.
from app.models import neo4j
from pathlib import Path
import json

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

def search_for_file_node(search_paths=None, properties=None):
    """Retrieve all paths and filenodes matching search criteria.
    
    Args:
        search_paths: list of path patterns to search, or None for defaults
        properties: dict of {property_key: search_value} filters
    
    Returns:
        List of matching nodes with their properties
    """
    if search_paths is None:
        search_paths = ["C:\\Users\\termi\\dropbox\\"]
    if properties is None:
        properties = {}

    query, params = build_filenode_search_query(search_paths, properties)
    debug_query = query
    for key, value in params.items():
        debug_query = debug_query.replace(f'${key}', f"'{value}'")

    with neo4j.get_session() as session:
        result = session.run(query, parameters=params)
        records = [record.data() for record in result]

        # TODO: MFN-id should be derived from context when multiple MFN types exist
        mfn_result = session.run(
            "MATCH (m:MetaFileNode {`MFN-id`: 'BusinessCard_20260121'}) RETURN m"
        ).single()
        mfn = {'meta_file_node': dict(mfn_result['m'])} if mfn_result else {}

    return [{'debug_query': debug_query}] + ([mfn] if mfn else []) + records

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
