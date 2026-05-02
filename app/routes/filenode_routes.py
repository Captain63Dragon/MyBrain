# app/routes/filenode_routes.py
# Generic FileNode query route - MFN-agnostic.
# Handles review UI queries for any FileNode type (BusinessCard, R2HOdo, etc.)
# Dispatch and process remain in their own blueprint (buscard_routes, r2hodo_routes).

from flask import Blueprint, request, jsonify
from app.services.neo4j_service import search_for_file_node
from app.services.schema_service import parse_user_search_input
from app import SERVICES

filenode_bp = Blueprint('filenode', __name__, url_prefix='/filenode')


@filenode_bp.route('/query/<service_key>', methods=['POST'])
def query_filenode(service_key):
    if service_key not in SERVICES:
        return jsonify({'error': f'Service not found: {service_key}'}), 404

    form_data = request.form.to_dict()
    mfn_id  = form_data.get('mfn_id')
    paths   = [form_data['node_path']] if form_data.get('node_path') else []
    filters = parse_user_search_input(form_data.get('property_filter', ''))

    print(f"[filenode/query] mfn_id={mfn_id}")
    print(f"[filenode/query] paths={paths}")
    print(f"[filenode/query] filters={filters}")

    result = search_for_file_node(paths, filters, mfn_id)

    print(f"[filenode/query] result count={len(result)}")
    return jsonify(result)
