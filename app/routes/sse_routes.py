import time
import json
from flask import Blueprint, request, Response, stream_with_context, jsonify
from app.services.mfi_broker import pop_result, _result_queue

sse_bp = Blueprint('sse', __name__, url_prefix='/sse')

@sse_bp.route('/watch', methods=['GET'])
def sse_watch():
    mfi_ids = request.args.get('mfi_ids', '')
    if not mfi_ids:
        return jsonify({'error': 'mfi_ids required'}), 400

    id_list = [m.strip() for m in mfi_ids.split(',') if m.strip()]
    timeout = 60  # seconds
    poll_interval = 1.0

    def generate():
        pending = set(id_list)
        elapsed = 0
        while pending and elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval
            # DEBUG print(f"[sse] polling for {pending}, elapsed={elapsed}")
            # DEBUG print(f"[sse] queue contents: {list(_result_queue.keys())}")
            for mfi_id in list(pending):
                result = pop_result(mfi_id)
                # DEBUG print(f"[SSE] pop_result", mfi_id, result)
                if result is not None:
                    payload = json.dumps({'mfi_id': mfi_id, **result})
                    yield f"data: {payload}\n\n"
                    pending.discard(mfi_id)
            if not pending:
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                return
        # timeout
        for mfi_id in pending:
            yield f"data: {json.dumps({'mfi_id': mfi_id, 'status': 'timeout'})}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    