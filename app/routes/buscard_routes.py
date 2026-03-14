from flask import Blueprint, render_template, request, jsonify
from app.services.neo4j_service import (
    create_nodes,
    create_mfn_node,
    ensure_filenode_constraint,
    ensure_mfn_constraint,
    delete_file_nodes,
    update_file_node,
    process_discovery_results,
    search_for_file_node,
    process_copy_results,
    process_move_results,
    create_dispatch_node,
)
from app.services.schema_service import load_mfn, parse_gfn, map_properties, parse_user_search_input
from app.shared.mfi_shared import DiscoveryMFI, write_mfi
from app.shared.mfi_shared import CopyMFI, MoveMFI
from pathlib import Path
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

@buscard_bp.route('/dispatch', methods=['POST'])
def dispatch_action():
    data    = request.json or {}
    action  = data.get('action')
    mfn_id  = data.get('mfn_id')
    node_id = data.get('node_id')

    if not action:
        return jsonify({'error': 'action is required'}), 400
    if action == 'discovery':
        if not mfn_id:
            return jsonify({'error': 'discovery requires mfn_id'}), 400
    else:
        if not all([mfn_id, node_id]):
            return jsonify({'error': 'mfn_id and node_id are required'}), 400
    if action == 'insitu_copy':
        source = data.get('source')
        target = data.get('target')
        if not all([source, target]):
            return jsonify({'error': 'insitu_copy requires source and target'}), 400
        mfi = CopyMFI(source=source, target=target, node_id=node_id, mfn_id=mfn_id, intent='insitu_copy')

    elif action == 'copy_master_source':
        source = data.get('source')
        target = data.get('target')
        if not all([source, target]):
            return jsonify({'error': 'copy requires source and target'}), 400
        mfi = CopyMFI(source=source, target=target, node_id=node_id, mfn_id=mfn_id, intent='master_source')

    elif action == 'copy_master_target':
        source = data.get('source')
        target = data.get('target')
        if not all([source, target]):
            return jsonify({'error': 'copy requires source and target'}), 400
        mfi = CopyMFI(source=source, target=target, node_id=node_id, mfn_id=mfn_id, intent='master_target')

    elif action == 'move':
        source = data.get('source')
        target = data.get('target')
        intent = data.get('intent', 'move')
        if not all([source, target]):
            return jsonify({'error': 'move requires source and target'}), 400
        mfi = MoveMFI(source=source, target=target, node_id=node_id, mfn_id=mfn_id, intent=intent)

    elif action == 'archive':
        source = data.get('source')
        target = data.get('target')
        if not all([source, target]):
            return jsonify({'error': 'archive requires source and target'}), 400
        mfi = MoveMFI(source=source, target=target, node_id=node_id, mfn_id=mfn_id, intent='archive')

    elif action == 'discovery':
        scan_path = data.get('source')
        patterns  = data.get('patterns', [])
        if not scan_path:
            return jsonify({'error': 'discovery requires source'}), 400
        mfi = DiscoveryMFI(mfn_id=mfn_id, source=scan_path, patterns=patterns)

    else:
        return jsonify({'error': f'Unknown action: {action}'}), 400

    written = write_mfi(mfi)
    create_dispatch_node(mfi.mfi_id, mfi.action, mfn_id, data.get('source', ''))

    return jsonify({'status': 'queued', 'mfi_id': mfi.mfi_id, 'action': action, 'intent': getattr(mfi, 'intent', ''), 'action': action})

@buscard_bp.route('/process', methods=['POST'])
def process_action():
    data   = request.json or {}
    action = data.get('action')

    if not action:
        return jsonify({'error': 'action is required'}), 400

    if action == 'discovery':
        result = process_discovery_results()

    elif action == 'copy':
        result = process_copy_results()

    elif action == 'move':
        result = process_move_results()

    else:
        return jsonify({'error': f'Unknown action: {action}'}), 400

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
   
@buscard_bp.route('/load-manual', methods=['GET'])
def load_manual():
    from app.services.filesystem_service import manual_load
    mfn_path = os.path.join('app', 'Schema', 'MFN-busCard.yaml')
    mfi_ids  = manual_load(mfn_path)
    return jsonify({'mfi_ids': mfi_ids})

@buscard_bp.route('/export', methods=['GET'])
def export_gfn():
    from app.services.neo4j_service import get_export_nodes
    from app.services.schema_service import serialize_gfn
    import os

    try:
        mfn_path = os.path.join('app', 'Schema', 'MFN-busCard.yaml')
        export_dir = Path(os.path.dirname(mfn_path))
        
        rows = get_export_nodes()
        mfn = load_mfn(mfn_path)
        yaml_str = serialize_gfn(rows, mfn)

        existing = sorted(export_dir.glob("GFN-busCard-dropbox_*.yaml"))
        next_version = len(existing) + 1
        versioned_name = f"GFN-busCard-dropbox_{next_version:03d}.yaml"
        versioned_path = export_dir / versioned_name
        active_path = export_dir / "GFN-busCard-dropbox_000.yaml"

        versioned_path.write_text(yaml_str, encoding='utf-8')
        active_path.write_text(yaml_str, encoding='utf-8')

        return jsonify({
            'status': 'ok',
            'records': len(rows),
            'versioned': versioned_name,
            'active': 'GFN-busCard-dropbox_000.yaml'
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@buscard_bp.route('/load')
def load():
    mfn_path = os.path.join('app', 'Schema', 'MFN-busCard.yaml')
    gfn_path = os.path.join('app', 'Schema', 'GFN-busCard-dropbox.yaml')
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
