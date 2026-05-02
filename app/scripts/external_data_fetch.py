"""
external_data_fetch - Flask-side background thread.
Polls external temporary storage sources and pulls data into MyBrain.

Current intake pipes:
  1. mybrain@zaudi.com (DreamHost IMAP) - tagged emails → vera-queue
  2. Todos sync to Zaudi via api_service
  3. TOPS sync (food_log + food_library) via tops_service

For each IMAP message:
  1. Write raw .eml to email/archive-raw/  (source of truth)
  2. Copy to Processed/Vera on IMAP server
  3. Flag Deleted in INBOX + Expunge
  4. Route - tagged emails only, via mail_service

After poll completes (regardless of email count):
  5. Sync todos to Zaudi via api_service.run_sync_cycle(auto=True)
  6. Sync TOPS via tops_service.run_sync_cycle(auto=True)

Credentials: ~/.netrc (machine imap.dreamhost.com)
Paths: MFI_PATH/email/archive-raw/ and MFI_PATH/email/vera-queue/
"""
import hashlib
import imaplib
import json
import logging
import netrc
import os
import time
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.shared.mfi_shared import email_archive_path, email_queue_path

# ── Configuration ─────────────────────────────────────────────────────────────
HOST          = 'imap.dreamhost.com'
IMAP_INBOX    = 'INBOX'
IMAP_DEST     = 'INBOX.Processed.Vera'
POLL_INTERVAL = 300

_app = None

# ── Logger ────────────────────────────────────────────────────────────────────
_logger = None

def _get_logger():
    global _logger
    if _logger is not None:
        return _logger

    log_path = os.path.join('app', 'logs', 'fetch.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    _logger = logging.getLogger('external_data_fetch')
    _logger.setLevel(logging.INFO)

    if not _logger.handlers:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        _logger.addHandler(handler)

    return _logger


def _log(event: str, detail: str = '', level: str = 'info'):
    entry = {
        'ts':    datetime.now(timezone.utc).isoformat(),
        'event': event,
    }
    if detail:
        entry['detail'] = detail

    line = json.dumps(entry)
    logger = _get_logger()
    if level == 'error':
        logger.error(line)
    else:
        logger.info(line)


# ── Path helpers ──────────────────────────────────────────────────────────────
def _ensure_paths():
    email_archive_path().mkdir(parents=True, exist_ok=True)
    email_queue_path().mkdir(parents=True, exist_ok=True)


# ── Credentials ───────────────────────────────────────────────────────────────
def _get_credentials():
    try:
        secrets = netrc.netrc().authenticators(HOST)
        if not secrets:
            raise RuntimeError(f"No .netrc entry for {HOST}")
        username, _, password = secrets
        return username, password
    except (FileNotFoundError, netrc.NetrcParseError) as e:
        raise RuntimeError(f".netrc error: {e}")


# ── IMAP helpers ──────────────────────────────────────────────────────────────
def _ensure_dest_folder(mail: imaplib.IMAP4_SSL):
    status, folders = mail.list()
    if status != 'OK':
        return
    exists = any(IMAP_DEST.encode() in (f or b'') for f in folders)
    if not exists:
        mail.create(IMAP_DEST)
        _log('imap.folder.created', IMAP_DEST)


def _copy_flag_expunge(mail: imaplib.IMAP4_SSL, uid: bytes):
    status, result = mail.uid('copy', uid, IMAP_DEST)
    if status != 'OK':
        raise RuntimeError(f"COPY failed for UID {uid.decode()}: {result}")
    mail.uid('store', uid, '+FLAGS', r'(\Deleted)')
    mail.expunge()


# ── Main poll ─────────────────────────────────────────────────────────────────
def _poll() -> int:
    """One IMAP session. Returns count of messages processed."""
    username, password = _get_credentials()
    processed = 0
    try:
        with imaplib.IMAP4_SSL(HOST) as mail:
            mail.login(username, password)
            _ensure_dest_folder(mail)
            mail.select(IMAP_INBOX)

            status, search_data = mail.uid('search', None, 'UNSEEN')
            if status != 'OK':
                _log('imap.search.failed', level='error')
                return 0

            uids = search_data[0].split()
            if not uids:
                return 0

            _log('imap.unseen', f"{len(uids)} message(s)")

            for uid in uids:
                uid_str = uid.decode()
                try:
                    status, fetch_data = mail.uid('fetch', uid, '(RFC822)')
                    if status != 'OK' or not fetch_data or fetch_data[0] is None:
                        _log('imap.fetch.failed', f"UID {uid_str}", level='error')
                        continue

                    raw_bytes = fetch_data[0][1]
                    uid_hash  = hashlib.md5(raw_bytes).hexdigest()
                    eml_path  = email_archive_path() / f"{uid_hash}.eml"

                    if eml_path.exists():
                        _log('imap.duplicate.skipped', uid_hash)
                        _copy_flag_expunge(mail, uid)
                        continue

                    eml_path.write_bytes(raw_bytes)
                    _copy_flag_expunge(mail, uid)

                    from app.services.mail_service import route
                    route(raw_bytes, uid_hash)

                    _log('imap.message.processed', uid_hash)
                    processed += 1

                except Exception as e:
                    _log('imap.message.error', f"UID {uid_str}: {e}", level='error')

    except Exception as e:
        _log('imap.connection.error', str(e), level='error')

    return processed


# ── Thread ────────────────────────────────────────────────────────────────────
def _fetch_loop():
    _ensure_paths()
    _log('fetch.started')

    while True:
        with _app.app_context():
            _log('cycle.start')

            # IMAP
            try:
                count = _poll()
                if count:
                    _log('cycle.imap', f"{count} processed")
            except Exception as e:
                _log('cycle.imap.error', str(e), level='error')

            # Todos sync
            try:
                from app.services.api_service import run_sync_cycle
                result = run_sync_cycle(reason='fetch cycle', auto=True)
                if result.get('push_skipped'):
                    _log('cycle.todos', 'deferred')
                else:
                    _log('cycle.todos', f"pushed={result.get('committed', 0)} fresh={result.get('fresh_count', 0)} stranded={result.get('stranded_count', 0)} failures={result.get('failure_count', 0)} status={result.get('status')}")
            except Exception as e:
                _log('cycle.todos.error', str(e), level='error')

            # TOPS sync
            try:
                from app.services.tops_service import run_sync_cycle as tops_sync
                tresult = tops_sync(reason='fetch cycle', auto=True)
                if tresult.get('push_skipped'):
                    _log('cycle.tops', "deferred")
                else:
                    log_push = tresult.get('push_log', {})
                    lib_push = tresult.get('push_lib', {})
                    log_pull = tresult.get('pull_log', {})
                    lib_pull = tresult.get('pull_lib', {})
                    _log('cycle.tops',
                         f"log pushed={log_push.get('pushed', 0)} lib pushed={lib_push.get('pushed', 0)} "
                         f"log pulled_new={log_pull.get('new', 0)} lib pulled_new={lib_pull.get('new', 0)} "
                         f"status={tresult.get('status')}")
            except Exception as e:
                _log('cycle.tops.error', str(e), level='error')

            _log('cycle.end', datetime.now(timezone.utc).isoformat())

        time.sleep(POLL_INTERVAL)


def start_external_data_fetch(app):
    global _app
    _app = app
    thread = threading.Thread(target=_fetch_loop, daemon=True, name='external_data_fetch')
    thread.start()
    _log('fetch.thread.launched')
