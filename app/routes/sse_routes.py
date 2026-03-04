import time
import threading
from flask import Blueprint, Response, stream_with_context

sse_bp = Blueprint('sse', __name__, url_prefix='/sse')

# Simple in-memory event queue for the test
# Key: stream_id, Value: list of pending messages
_queues = {}
_queues_lock = threading.Lock()

def _push(stream_id, message):
    with _queues_lock:
        if stream_id in _queues:
            _queues[stream_id].append(message)

def _background_task(stream_id):
    """Simulate 5 steps of work, 1 second apart."""
    for i in range(1, 6):
        time.sleep(1)
        _push(stream_id, f"Step {i} of 5 complete")
    _push(stream_id, "__done__")

@sse_bp.route('/test-start', methods=['POST'])
def test_start():
    stream_id = 'test'
    with _queues_lock:
        _queues[stream_id] = []
    thread = threading.Thread(target=_background_task, args=(stream_id,), daemon=True)
    thread.start()
    return {'status': 'ok', 'stream_id': stream_id}

@sse_bp.route('/test-stream/<stream_id>')
def test_stream(stream_id):
    def generate():
        while True:
            time.sleep(0.2)
            with _queues_lock:
                if stream_id not in _queues:
                    yield "data: __error__\n\n"
                    return
                messages = _queues[stream_id][:]
                _queues[stream_id] = []

            for msg in messages:
                yield f"data: {msg}\n\n"
                if msg == "__done__":
                    with _queues_lock:
                        _queues.pop(stream_id, None)
                    return

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'   # important for nginx proxies
        }
    )