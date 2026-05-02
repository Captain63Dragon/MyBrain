# app/bots/dispatch/iris.py
#
# Iris dispatch bots - write MFI instructions to the pipeline queue.
# Call MFI and graph service layer directly; no HTTP round-trip.
#
# Registered in graph as BotFunction nodes under the 'iris' namespace.

from app.bots import bot_logger as log
from app.shared.mfi_shared import (
    DiscoveryMFI, CopyMFI, MoveMFI, write_mfi
)
from app.services.neo4j_service import create_dispatch_node

REQUIRES = set()  # filesystem + graph only; no Neo4j session needed for queries

ALLOWED_ACTIONS = {
    'discovery', 'move', 'archive',
    'insitu_copy', 'copy_master_source', 'copy_master_target'
}

BOT_ID = "iris.buscard.dispatch"


def buscard_dispatch(
    action: str,
    mfn_id: str,
    source: str = '',
    target: str = '',
    node_id: str = '',
    patterns: list = None,
    files: list = None,
    reason: str = '',
    log_call: bool = True,
) -> dict:
    """Dispatch a buscard pipeline action.

    Discovery - two modes:
      (1) Directory scan: provide source (dir path) and optionally patterns
          to override the MFN mask.
      (2) File list: provide files (list of absolute paths) to skip
          scanning entirely. files takes priority over patterns.

    Move/archive/copy actions: provide source, target, node_id as usual.
    """
    if action not in ALLOWED_ACTIONS:
        return {'error': f'Action not permitted: {action}'}

    if log_call:
        log.call(BOT_ID, reason=reason, detail=f"action={action} mfn_id={mfn_id}")

    patterns = patterns or []
    files = files or []

    try:
        if action == 'discovery':
            if not source and not files:
                return {'error': 'discovery requires source (directory) or files (list)'}
            mfi = DiscoveryMFI(
                mfn_id=mfn_id,
                source=source,
                patterns=patterns,
                files=files,
            )

        elif action in ('insitu_copy', 'copy_master_source', 'copy_master_target'):
            if not all([source, target, node_id]):
                return {'error': f'{action} requires source, target, and node_id'}
            intent_map = {
                'insitu_copy':        'insitu_copy',
                'copy_master_source': 'master_source',
                'copy_master_target': 'master_target',
            }
            mfi = CopyMFI(
                source=source, target=target,
                node_id=node_id, mfn_id=mfn_id,
                intent=intent_map[action],
            )

        elif action in ('move', 'archive'):
            if not all([source, target, node_id]):
                return {'error': f'{action} requires source, target, and node_id'}
            mfi = MoveMFI(
                source=source, target=target,
                node_id=node_id, mfn_id=mfn_id,
                intent=action,
            )

        else:
            return {'error': f'Unknown action: {action}'}

        write_mfi(mfi)
        create_dispatch_node(mfi.mfi_id, mfi.action, mfn_id, source)

        return {
            'status': 'queued',
            'mfi_id': mfi.mfi_id,
            'action': action,
            'intent': getattr(mfi, 'intent', ''),
        }

    except Exception as e:
        log.error(BOT_ID, reason=reason, detail=str(e))
        return {'error': str(e)}
