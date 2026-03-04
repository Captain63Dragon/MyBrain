"""
mfi_broker — Flask-side background thread.
Watches completed/ for result MFIs, routes to the correct processor,
records processed mfi_ids in the result queue for SSE consumers.
Dead letters pruned daily.
"""
import time
import threading

# ── Result queue ───────────────────────────────────────────────────────────────
# One writer (mfi_broker), many readers (SSE streams)
# Key: mfi_id, Value: { result: dict, created: float }
_result_queue = {}
_queue_lock   = threading.Lock()

def push_result(mfi_id: str, result: dict):
    with _queue_lock:
        _result_queue[mfi_id] = {'result': result, 'created': time.time()}
        print(f"[mfi_broker] push_result: {mfi_id} — queue depth: {len(_result_queue)}")

def pop_result(mfi_id: str) -> dict | None:
    """Return and remove result if present, None if not yet ready."""
    with _queue_lock:
        entry = _result_queue.pop(mfi_id, None)
        return entry['result'] if entry else None

def peek_result(mfi_id: str) -> bool:
    """Check if a result is ready without consuming it."""
    with _queue_lock:
        return mfi_id in _result_queue


# ── Prune ──────────────────────────────────────────────────────────────────────
PRUNE_INTERVAL = 86400  # run prune once per day
PRUNE_MAX_AGE  = 86400  # entries older than 24 hours are stale
_last_prune    = time.time()

def _prune_queue():
    global _last_prune
    now = time.time()
    if now - _last_prune < PRUNE_INTERVAL:
        return
    with _queue_lock:
        stale = [k for k, v in _result_queue.items()
                 if now - v['created'] > PRUNE_MAX_AGE]
        for k in stale:
            _result_queue.pop(k)
        if stale:
            print(f"[mfi_broker] pruned {len(stale)} stale queue entries")
    _last_prune = now


# ── Broker loop ────────────────────────────────────────────────────────────────
POLL_INTERVAL = 2  # seconds

def _mfi_broker_loop():
    from app.shared.mfi_shared import (
        decode, completed_path,
        DiscoveryResultMFI, CopyResultMFI, MoveResultMFI
    )
    from app.services.neo4j_service import (
        process_discovery_results,
        process_copy_results,
        process_move_results
    )

    print("[mfi_broker] started")

    while True:
        try:
            completed = completed_path()
            if completed.exists():
                mfi_files = list(completed.glob('*.mfi'))
                processable = [f for f in mfi_files if isinstance(decode(str(f)), 
                    (DiscoveryResultMFI, CopyResultMFI, MoveResultMFI))]
                if processable:
                    print(f"[mfi_broker] {len(processable)} of {len(mfi_files)} result MFI(s) to process")
                if mfi_files:
                    # Peek at types to decide which processors to run
                    types = []
                    for f in mfi_files:
                        try:
                            types.append(type(decode(str(f))))
                        except Exception:
                            pass

                    if DiscoveryResultMFI in types:
                        result = process_discovery_results()
                        print(f"[mfi_broker] discovery: {result}")

                    if CopyResultMFI in types:
                        result = process_copy_results()
                        print(f"[mfi_broker] copy: {result}")

                    if MoveResultMFI in types:
                        result = process_move_results()
                        print(f"[mfi_broker] move: {result}")

            _prune_queue()

        except Exception as e:
            print(f"[mfi_broker] ERROR: {e}")

        time.sleep(POLL_INTERVAL)


def start_mfi_broker():
    thread = threading.Thread(target=_mfi_broker_loop, daemon=True, name='mfi_broker')
    thread.start()
    print("[mfi_broker] thread launched")