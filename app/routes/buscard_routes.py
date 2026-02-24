from flask import Blueprint, render_template, request, jsonify
from app.services.neo4j_service import create_nodes, create_mfn_node 
from app.services.neo4j_service import ensure_filenode_constraint, ensure_mfn_constraint
from app.services.neo4j_service import delete_file_nodes, update_file_node
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
    
@buscard_bp.route('/query/<service_key>', methods=['POST'])
def query_service(service_key):
    if service_key not in SERVICES:
        return jsonify({'error': 'Service not found'}), 404
    
    form_data = request.form.to_dict()
    # this will eventually be more than one path. Fake it for now.
    paths = [form_data['node_path']]
    filters = parse_user_search_input(form_data['property_filter'])
    
    result = search_for_file_node(paths, filters)
    return jsonify(result)

@buscard_bp.route('/node/update', methods=['POST'])
def update_node():
    data = request.json
    node_id = data.get('nodeId')
    fields = data.get('fields')
    
    if not node_id or not fields:
        return jsonify({'error': 'nodeId and fields required'}), 400
    
    result = update_file_node(node_id, fields)
    return jsonify(result)

@buscard_bp.route('/node/delete', methods=['POST'])
def delete_node():
    data = request.json
    node_ids = data.get('nodeIds')    
    result = delete_file_nodes(node_ids)
    return jsonify(result)
    
@buscard_bp.route('/node/move', methods=['POST'])
def move_node():
    data = request.json
    node_ids = data.get('nodeIds')
    destination = data.get('destination')
    # TODO: define move semantics
    return jsonify({'status': 'not implemented'})
   
@buscard_bp.route('/load')
def load():
    mfn_path = os.path.join('app', 'Schema', 'MFN-busCard.yaml')
    gfn_path = os.path.join('app', 'Schema', 'GFN-busCard-dropbox_001.yaml')
    mfn = load_mfn(mfn_path)
    nodes = parse_gfn(gfn_path)
    label = mfn.get('name', 'Business Card').replace(' ', '')
    mapped = [map_properties(mfn, n) for n in nodes]

    from app.models import neo4j
    with neo4j.driver.session() as session:
        ensure_filenode_constraint(session)
        ensure_mfn_constraint(session)
        create_mfn_node(session, mfn)
        create_nodes(session, label, mapped)

    return f"Loaded {len(mapped)} FileNodes into Neo4j label:{label}:FileNode"
