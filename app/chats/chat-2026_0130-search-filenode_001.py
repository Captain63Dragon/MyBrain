# initial draft that searches based on my prototype 

def search_for_file_node(search_paths=None, properties=None):
    """Retrieve all paths and filenodes matching search criteria.
    
    Args:
        search_paths: list of path patterns to search, or None for defaults
        properties: dict of {property_key: search_value} filters
    
    Returns:
        List of matching nodes with their properties
    """
    if search_paths is None:
        search_paths = get_default_search_paths()  # your "usual places"
    
    if properties is None:
        properties = {}
    
    # Build Cypher query
    query = build_file_search_query(search_paths, properties)
    
    # Execute and return results
    with neo4j_driver.session() as session:
        result = session.run(query, parameters={'props': properties, 'paths': search_paths})
        return [record.data() for record in result]
    
def parse_user_search_input(raw_input):
    """Convert user's 'key:value, key2:value2' into dict"""
    properties = {}
    if not raw_input:
        return properties
    
    pairs = raw_input.split(',')
    for pair in pairs:
        if ':' in pair:
            key, value = pair.split(':', 1)  # split on first : only
            properties[key.strip()] = value.strip()
    
    return properties
    
    ##################### 
#  Sample cypher version with parameters
# MATCH (f:FileNode)
# WHERE f.filepath STARTS WITH $search_path
#   AND toLower(f.company) CONTAINS toLower($company_search)
# RETURN f.filepath, f.`FILE-NODE-id`, f.company, f
### where parameters are like
# parameters = {
#     'search_path': 'C:\\Users\\termi\\Dropbox\\',
#     'company_search': 'Gateway Toyota'
# }


# Code to break the query string into parts we can fill in

def build_file_search_query(search_paths, properties, return_fields=None):
    """Build Cypher query dynamically based on filters"""
    
    # Base MATCH
    query_parts = ["MATCH (f:FileNode)"]
    
    # WHERE clauses
    where_clauses = ["NOT f:MetaFileNode"]
    params = {}
    
    # Add path filters
    if search_paths:
        # For multiple paths, use OR
        path_conditions = " OR ".join([
            f"f.filepath STARTS WITH $path{i}" 
            for i in range(len(search_paths))
        ])
        where_clauses.append(f"({path_conditions})")
        for i, path in enumerate(search_paths):
            params[f'path{i}'] = path
    
    # Add property filters
    for key, value in properties.items():
        param_name = f"prop_{key}"
        where_clauses.append(f"toLower(f.`{key}`) CONTAINS toLower(${param_name})")
        params[param_name] = value
    
    # Combine WHERE
    if where_clauses:
        query_parts.append("WHERE " + " AND ".join(where_clauses))
    
    # RETURN clause
    if return_fields is None:
        return_fields = ['filepath', 'FILE-NODE-id', 'company']
    
    return_items = [f"f.`{field}`" for field in return_fields] + ['f']
    query_parts.append("RETURN " + ", ".join(return_items))
    
    query = "\n".join(query_parts)
    return query, params

### with how it is used as such:

# query, params = build_file_search_query(
#     search_paths=['C:\\Users\\termi\\Dropbox\\'],
#     properties={'company': 'Gateway Toyota'},
#     return_fields=['filepath', 'FILE-NODE-id', 'company']
# )
# result = session.run(query, params)

### correcting paths to be ready for cypher query generation.
from pathlib import Path

def normalize_path_for_cypher(path_string):
    """Convert path to Cypher-ready string matching Windows format in DB"""
    normalized = Path(path_string)
    
    # Escape backslashes for Cypher (\ becomes \\)
    cypher_path = str(normalized).replace('\\', '\\\\')
    
    # Ensure trailing double-backslash
    if not cypher_path.endswith('\\\\'):
        cypher_path += '\\\\'
    
    return cypher_path
