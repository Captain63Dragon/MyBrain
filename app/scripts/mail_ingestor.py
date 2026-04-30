"""
mail_ingestor — Flask-side background thread.
Polls mybrain@zaudi.com (DreamHost IMAP) for UNSEEN messages.
For each message:
  1. Write raw .eml to email/archive-raw/  (source of truth)
  2. Copy to Processed/Vera on IMAP server
  3. Flag Deleted in INBOX + Expunge
  4. Route — tagged emails only, via mail_service

After poll completes (regardless of email count):
  5. Sync todos to Zaudi via api_service.run_sync_cycle(auto=True)
     auto=True applies the 1hr push guard — dirty flag overrides.

Credentials: ~/.netrc (machine imap.dreamhost.com)
Paths: MFI_PATH/email/archive-raw/ and MFI_PATH/email/vera-queue/
"""
import hashlib
import imaplib
import netrc
import time
import threading
from pathlib import Path

from app.shared.mfi_shared import email_archive_path, email_queue_path

# ── Configuration ─────────────────────────────────────────────────────────────
HOST          = 'imap.dreamhost.com'
IMAP_INBOX    = 'INBOX'
IMAP_DEST     = 'INBOX.Processed.Vera'
POLL_INTERVAL = 300

# App instance — set by start_mail_ingestor(), used for app context in thread
_app = None


# ── Path helpers ──────────────────────────────────────────────────────────────
def _ensure_paths():
    """Create archive-raw and vera-queue root. Subfolders created dynamically by mail_service."""
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
    """Create Processed/Vera on server if it doesn't exist."""
    status, folders = mail.list()
    if status != 'OK':
        return
    exists = any(IMAP_DEST.encode() in (f or b'') for f in folders)
    if not exists:
        mail.create(IMAP_DEST)
        print(f"[mail_ingestor] created IMAP folder: {IMAP_DEST}")


def _copy_flag_expunge(mail: imaplib.IMAP4_SSL, uid: bytes):
    """Copy to Processed/Vera, flag Deleted in INBOX, expunge."""
    status, result = mail.uid('copy', uid, IMAP_DEST)
    if status != 'OK':
        raise RuntimeError(f"COPY failed for UID {uid.decode()}: {result}")
    mail.uid('store', uid, '+FLAGS', r'(\Deleted)')
    mail.expunge()


# ── Main poll ─────────────────────────────────────────────────────────────────
def _poll():
    """One IMAP session: fetch UNSEEN, archive, move."""
    username, password = _get_credentials()
    try:
        with imaplib.IMAP4_SSL(HOST) as mail:
            mail.login(username, password)
            _ensure_dest_folder(mail)
            mail.select(IMAP_INBOX)

            status, search_data = mail.uid('search', None, 'UNSEEN')
            if status != 'OK':
                print("[mail_ingestor] SEARCH failed")
                return

            uids = search_data[0].split()
            if not uids:
                return

            print(f"[mail_ingestor] {len(uids)} UNSEEN message(s)")

            for uid in uids:
                uid_str = uid.decode()
                try:
                    status, fetch_data = mail.uid('fetch', uid, '(RFC822)')
                    if status != 'OK' or not fetch_data or fetch_data[0] is None:
                        print(f"[mail_ingestor] fetch failed: UID {uid_str}")
                        continue

                    raw_bytes = fetch_data[0][1]

                    # 1. Local write — source of truth
                    uid_hash = hashlib.md5(raw_bytes).hexdigest()
                    eml_path = email_archive_path() / f"{uid_hash}.eml"
                    if eml_path.exists():
                        print(f"[mail_ingestor] duplicate, skipping: {uid_hash}.eml")
                        _copy_flag_expunge(mail, uid)
                        continue

                    eml_path.write_bytes(raw_bytes)
                    print(f"[mail_ingestor] archived: {uid_hash}.eml")

                    # 2. Server-side move (only after local write confirmed)
                    _copy_flag_expunge(mail, uid)

                    # 3. Route — tagged emails only
                    from app.services.mail_service import route
                    route(raw_bytes, uid_hash)

                except Exception as e:
                    print(f"[mail_ingestor] ERROR processing UID {uid_str}: {e}")

    except Exception as e:
        print(f"[mail_ingestor] connection error: {e}")


# ── Thread ────────────────────────────────────────────────────────────────────
def _mail_ingestor_loop():
    _ensure_paths()
    print("[mail_ingestor] started")
    while True:
        with _app.app_context():
            try:
                _poll()
            except Exception as e:
                print(f"[mail_ingestor] loop error: {e}")

            # Sync todos to Zaudi after every poll — auto=True applies 1hr guard
            try:
                from app.services.api_service import run_sync_cycle
                result = run_sync_cycle(reason='triggered by mail_ingestor poll', auto=True)
                if result.get('push_skipped'):
                    print(f"[mail_ingestor] sync: ok — push deferred")
                else:
                    print(f"[mail_ingestor] sync ok | {result}")
            except Exception as e:
                print(f"[mail_ingestor] sync error: {e}")

            # Sync TOPS (food_log + food_library) — same auto=True 1hr guard
            try:
                from app.services.tops_service import run_sync_cycle as tops_sync
                tresult = tops_sync(reason='triggered by mail_ingestor poll', auto=True)
                if tresult.get('push_skipped'):
                    print(f"[mail_ingestor] tops sync: ok — push deferred")
                else:
                    print(f"[mail_ingestor] tops sync ok | {tresult}")
            except Exception as e:
                print(f"[mail_ingestor] tops sync error: {e}")

        time.sleep(POLL_INTERVAL)


def start_mail_ingestor(app):
    global _app
    _app = app
    thread = threading.Thread(target=_mail_ingestor_loop, daemon=True, name='mail_ingestor')
    thread.start()
    print("[mail_ingestor] thread launched")
