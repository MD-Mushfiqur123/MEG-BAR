#!/usr/bin/env python3
"""
Package MEG-BAR deliverables:
1. Re-bundle Overleaf ZIP at C:\\Users\\mushfiqur\\Desktop\\MEG-BAR_Overleaf.zip
2. Re-sync all files to C:\\Users\\mushfiqur\\Desktop\\MUSHFIQUR_ALL_ACHIEVEMENTS\\03_Research_Papers\\MEG-BAR\\
"""

import os
import shutil
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LATEX_DIR = BASE_DIR / "latex"
DESKTOP_ZIP = Path(r"C:\Users\mushfiqur\Desktop\MEG-BAR_Overleaf.zip")
ACHIEVEMENTS_DIR = Path(r"C:\Users\mushfiqur\Desktop\MUSHFIQUR_ALL_ACHIEVEMENTS\03_Research_Papers\MEG-BAR")

def bundle_overleaf_zip():
    print(f"=== 1. PACKAGING OVERLEAF ZIP ===")
    print(f"Source: {LATEX_DIR}")
    print(f"Destination: {DESKTOP_ZIP}")

    if DESKTOP_ZIP.exists():
        DESKTOP_ZIP.unlink()
        print("Removed existing zip file.")

    with zipfile.ZipFile(DESKTOP_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in sorted(LATEX_DIR.iterdir()):
            if file_path.is_file():
                arcname = file_path.name
                size_kb = file_path.stat().st_size / 1024
                zipf.write(file_path, arcname=arcname)
                print(f"  Added: {arcname:<35} ({size_kb:.1f} KB)")

    zip_size_kb = DESKTOP_ZIP.stat().st_size / 1024
    print(f"SUCCESS: Created {DESKTOP_ZIP} ({zip_size_kb:.1f} KB)\n")

    # Verify zip content
    with zipfile.ZipFile(DESKTOP_ZIP, 'r') as zipf:
        namelist = zipf.namelist()
        print(f"Verified {len(namelist)} items in zip archive.")

def sync_achievements_archive():
    print(f"=== 2. SYNCING ACHIEVEMENTS ARCHIVE ===")
    print(f"Source: {BASE_DIR}")
    print(f"Destination: {ACHIEVEMENTS_DIR}")

    ACHIEVEMENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Walk through BASE_DIR and copy relevant files
    ignored_patterns = {'.pytest_cache', '__pycache__', '.git'}
    count = 0
    total_bytes = 0

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in ignored_patterns]
        rel_path = Path(root).relative_to(BASE_DIR)
        target_sub = ACHIEVEMENTS_DIR / rel_path
        target_sub.mkdir(parents=True, exist_ok=True)

        for file in files:
            if file.endswith('.pyc'):
                continue
            src_file = Path(root) / file
            dst_file = target_sub / file
            shutil.copy2(src_file, dst_file)
            count += 1
            total_bytes += src_file.stat().st_size

    print(f"SUCCESS: Synchronized {count} files ({total_bytes / (1024*1024):.2f} MB) to {ACHIEVEMENTS_DIR}\n")

if __name__ == "__main__":
    bundle_overleaf_zip()
    sync_achievements_archive()
    print("ALL DELIVERABLES PACKAGED AND SYNCHRONIZED SUCCESSFULLY!")
