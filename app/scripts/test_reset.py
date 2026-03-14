"""
MyBrain Test Reset Script
Usage: python app/scripts/test_reset.py
Creates test directories and places empty PDF files in correct locations.
Run before each test cycle to restore known state.
"""

import sys
import os
from pathlib import Path

# Test locations
TEST_DIR     = Path('C:/Users/termi/MyBrain-test')
ARCHIVE_DIR  = Path('C:/Users/termi/MyBrain-test-archive')
BACKUP_DIR   = Path('C:/Users/termi/MyBrain-test-backup')

# Files and their starting locations
TEST_FILES = [
    (TEST_DIR,   '2026_0101-busCard-test-alpha.pdf'),    # stays in place
    (TEST_DIR,   '2026_0101-busCard-test-beta.pdf'),     # insitu copy to archive
    (TEST_DIR,   '2026_0101-busCard-test-gamma.pdf'),    # move to backup 
    (TEST_DIR,   '2026_0101-busCard-test-delta.pdf'),    # missed.. stays in place for now.
    (TEST_DIR,   '2026_0101-busCard-test-epsilon.pdf'),  # copy master in source location. One to backup, one to archive
    (BACKUP_DIR, '2026_0101-busCard-test-zeta.pdf'),     # copy master in target location. Master in archive, stub in backup
]

def clean_mfi_queues():
    """Wipe all test MFI files from pending/processing/completed."""
    from dotenv import load_dotenv
    load_dotenv()
    
    mfi_root = Path(os.getenv('MFI_PATH', 'C:/Users/termi/MetaFileQueues'))
    folders = ['pending', 'processing', 'completed']
    
    print("\nCleaning MFI queues...")
    for folder in folders:
        queue = mfi_root / folder
        if not queue.exists():
            continue
        for f in queue.glob('*.mfi'):
            f.unlink()
            print(f"  Removed: {f}")
        for f in queue.glob('*.mft'):
            f.unlink()
            print(f"  Removed: {f}")
    print("MFI queues clean.")

def create_empty_pdf(filepath: Path):
    """Create a minimal valid PDF file."""
    filepath.write_bytes(
        b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
        b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n'
        b'xref\n0 4\n0000000000 65535 f\n'
        b'trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF\n'
    )

def reset():
    clean_mfi_queues()
    print("Creating test directories...")
    for d in [TEST_DIR, ARCHIVE_DIR, BACKUP_DIR]:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  {d}")

    print("\nCleaning existing test files...")
    for d in [TEST_DIR, ARCHIVE_DIR, BACKUP_DIR]:
        for f in d.glob('*busCard-test-*'):
            f.unlink()
            print(f"  Removed: {f}")

    print("\nCreating test files...")
    for directory, filename in TEST_FILES:
        filepath = directory / filename
        create_empty_pdf(filepath)
        print(f"  Created: {filepath}")

    print("\nReset complete.")
    print(f"  {TEST_DIR} — {len([f for f in TEST_DIR.glob('*.pdf')])} files")
    print(f"  {ARCHIVE_DIR} — {len([f for f in ARCHIVE_DIR.glob('*.pdf')])} files")
    print(f"  {BACKUP_DIR} — {len([f for f in BACKUP_DIR.glob('*.pdf')])} files")

if __name__ == '__main__':
    reset()
# ```
# Run it with:
# ```
# python app/scripts/test_reset.py