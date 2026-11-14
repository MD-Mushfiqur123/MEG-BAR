"""Phase 10 - SHA-256 manifest of all frozen Paper 2 artefacts.

Walks paper2/data/structures/ and paper2/data/features/ and records size +
SHA-256 for every file (the manifest itself is excluded).

Output: paper2/data/structures/manifest.json

Run:  python3 paper2/scripts/10_manifest.py
"""

import hashlib
import json
import os
import time

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DIRS = [os.path.join(BASE, "structures"), os.path.join(BASE, "features")]


def main():
    entries = {}
    for d in DIRS:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for name in sorted(files):
                if name == "manifest.json":
                    continue
                path = os.path.join(root, name)
                rel = os.path.relpath(path, BASE)
                with open(path, "rb") as f:
                    data = f.read()
                entries[rel] = {
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
    manifest = {
        "purpose": "Paper 2 Phase 10 - frozen artefact manifest (structures + features)",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "algorithm": "sha256",
        "n_files": len(entries),
        "total_bytes": sum(e["bytes"] for e in entries.values()),
        "files": entries,
    }
    out = os.path.join(BASE, "structures", "manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print(f"wrote {out}  ({len(entries)} files, {manifest['total_bytes']} bytes)")


if __name__ == "__main__":
    main()
