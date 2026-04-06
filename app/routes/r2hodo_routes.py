import os
from flask import Blueprint, render_template, request, jsonify
from app.services.filesystem_service import manual_load
from app.services.neo4j_service import search_for_file_node
from app.services.schema_service import parse_user_search_input
from app import SERVICES
r2hodo_bp = Blueprint('r2hodo', __name__, url_prefix='/r2hodo')


@r2hodo_bp.route('/load-manual', methods=['GET'])
def load_manual():
    mfn_path = os.path.join('app', 'Schema', 'MFN-r2hodo.yaml')
    mfi_ids = manual_load(mfn_path)
    return jsonify({'mfi_ids': mfi_ids})

@r2hodo_bp.route('/query/<service_key>', methods=['POST'])
def query_service(service_key):
    print(f"[/query/{service_key}] POST")
    if service_key not in SERVICES:
        return jsonify({'error': 'Service not found'}), 404
    
    form_data = request.form.to_dict()
    mfn_id = form_data.get('mfn_id')
    paths = [form_data['node_path']]
    filters = parse_user_search_input(form_data['property_filter'])
    
    print(f"[/r2hodo/query/{service_key}] {mfn_id}")
    result = search_for_file_node(paths, filters, mfn_id)
    return jsonify(result)