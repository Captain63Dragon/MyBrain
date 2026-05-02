"""
extract_attachments.py - Standalone script to extract attachments from a raw .eml file.
Calls mail_service.extract_attachments() - no duplication.

Usage:
    # By uid_hash (looks up in archive-raw/):
    venv\Scripts\python app\scripts\extract_attachments.py b02c2bb6cead538aa2ca2988166bd54c

    # By full path:
    venv\Scripts\python app\scripts\extract_attachments.py C:\path\to\file.eml

Outputs extracted files to MFI_PATH/email/attachments/ (flat, indexed).
Prints each saved file path.

Run from codebase root.
"""
import sys
from pathlib import Path

# ── Bootstrap app context ──────────────────────────────────────────────────────
# Add codebase root to path so app imports work
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.shared.mfi_shared import email_archive_path
from app.services.mail_service import extract_attachments


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_attachments.py <uid_hash | /path/to/file.eml>")
        sys.exit(1)

    arg = sys.argv[1]

    # Resolve to a Path
    p = Path(arg)
    if not p.exists():
        # Try treating as uid_hash - look up in archive-raw/
        candidate = email_archive_path() / f"{arg}.eml"
        if candidate.exists():
            p = candidate
        else:
            print(f"File not found: {arg}")
            print(f"Also checked: {candidate}")
            sys.exit(1)

    uid_hash = p.stem  # filename without extension = uid_hash
    raw_bytes = p.read_bytes()

    print(f"Processing: {p.name}")
    extracted = extract_attachments(raw_bytes, uid_hash)

    if not extracted:
        print("No extractable attachments found.")
    else:
        print(f"\n{len(extracted)} attachment(s) extracted:")
        for a in extracted:
            print(f"  {a['path']}  ({a['type']}, {a['size']} bytes)")
            if a.get('content_id'):
                print(f"    content-id: {a['content_id']}")


if __name__ == '__main__':
    main()