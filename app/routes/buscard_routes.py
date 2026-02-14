from flask import Blueprint, render_template, request, jsonify
from app.services.neo4j_service import create_nodes, ensure_filenode_constraint
from app.services.neo4j_service import normalize_path_for_cypher, search_for_file_node
from app.services.schema_service import load_mfn, parse_gfn, map_properties, parse_user_search_input
import json
import os

buscard_bp = Blueprint('buscard', __name__, url_prefix='/buscard')

# Simple service registry - just titles and template names
SERVICES = {
    'search_database': {
        'title': 'Search Database',
        'template': 'search_database.html'
    },
    'review_filenode': {
        'title': 'Review FileNode',
        'template': 'review_filenode.html'
    }
}

@buscard_bp.route('/show')
@buscard_bp.route('/show/<label>')
def show(label='BusnessCard'):
    # Return a JSON list of sample business card nodes or MetaBusinessCard if label is meta
    if not label == 'BusinessCard' and label.lower() == 'meta':
        label = 'MetaBusinessCard'
    else:
        label = 'BusinessCard'
    results = []
    from app.models import neo4j
    with neo4j.get_session() as session:
        # print (f"SHOW ROUTE: {neo4j}, {session}")
        res = session.run(f"MATCH (b:{label}) RETURN b LIMIT 50")
        for record in res:
            node = record['b']
            results.append(dict(node))
    return jsonify(results)

@buscard_bp.route('/gui/')
def index():
    return render_template('base.html', services=SERVICES)

# This was the old way of loading the service. Now these templates are added by base.html statically
@buscard_bp.route('/service/<service_key>')
def load_service(service_key):
    if service_key not in SERVICES:
        return jsonify({'error': 'Service not found'}), 404
    service = SERVICES[service_key]
    print (f"Show service key: '{service_key}' at {service['template']}")
    # Render just the service template fragment and return to caller
    return render_template(service['template'], service=service)

@buscard_bp.route('/submit/<service_key>', methods=['POST'])
def submit_service(service_key):
    # Handle service-specific logic here
    form_data = request.form.to_dict()
    # print (f"form_data: {form_data}")
    # this will eventually be more than one path. Fake it for now.
    paths = [ form_data['node_path'] ]
    filters = parse_user_search_input(form_data['property_filter'])
    service = SERVICES[service_key]
    # print (f"Got POST service key: '{service_key}' at {service['template']}")
    
    result = search_for_file_node(paths, filters)
    # print (f"Is this result empty? {result}")
    return jsonify(result)
    

@buscard_bp.route('/load')
def load():
    # Parse MFN and GFN and load nodes into Neo4j for testing
    mfn_path = os.path.join('app', 'Schema', 'MFN-busCard.yaml')
    gfn_path = os.path.join('app', 'Schema', 'GFN-busCard-dropbox_001.yaml')
    mfn = load_mfn(mfn_path)
    nodes = parse_gfn(gfn_path)
    label = mfn.get('name', 'Business Card').replace(' ', '')
    meta_label = f"Meta{label}"
    mapped = [map_properties(mfn, n) for n in nodes]

    from app.models import neo4j
    with neo4j.driver.session() as session:
        # Ensure constraint exists first
        ensure_filenode_constraint(session)
        
        # Create/update the nodes
        # Normalize the MFN into a proper single-file-node dict and
        # serialize any nested structures (Neo4j node properties must be scalars or lists)
        meta_node = map_properties(mfn, mfn)
        create_nodes(session, meta_label, [meta_node])  # fake a single node with the multi add function
        create_nodes(session, label, mapped)

    return f"Loaded {len(mapped)} FileNodes into Neo4j label:{label}:FileNode"
    

