"""
email_routes.py (or add to base_routes.py)

Endpoint: POST /email/extract-attachments
Extracts attachments from a raw .eml in archive-raw/ to the attachments staging folder.
Calls mail_service.extract_attachments() - no duplication.

curl example:
    curl -s -X POST http://localhost:5000/email/extract-attachments \
         -H "Content-Type: application/json" \
         -d '{"uid_hash": "b02c2bb6cead538aa2ca2988166bd54c"}'

Returns:
    {
        "uid_hash": "b02c2bb6...",
        "source": "/path/to/archive-raw/b02c2bb6....eml",
        "extracted": [
            {
                "name": "b02c2bb6..._001.jpeg",
                "type": "image/jpeg",
                "size": 12345,
                "path": "C:\\...\\attachments\\b02c2bb6..._001.jpeg",
                "content_id": "picReceipt"
            }
        ],
        "count": 1
    }
"""

from flask import Blueprint, jsonify
from pathlib import Path

from app.shared.mfi_shared import email_archive_path
from app.services.mail_service import extract_attachments

email_bp = Blueprint('email', __name__)


@email_bp.route('/email/extract-attachments/<uid_hash>', methods=['GET'])
def extract_email_attachments(uid_hash):
    uid_hash = uid_hash.strip()

    if not uid_hash:
        return jsonify({'error': 'uid_hash required'}), 400

    eml_path = email_archive_path() / f"{uid_hash}.eml"
    if not eml_path.exists():
        return jsonify({'error': f'eml not found: {uid_hash}.eml'}), 404

    try:
        raw_bytes = eml_path.read_bytes()
        extracted = extract_attachments(raw_bytes, uid_hash)
        return jsonify({
            'uid_hash':  uid_hash,
            'source':    str(eml_path),
            'extracted': extracted,
            'count':     len(extracted),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500