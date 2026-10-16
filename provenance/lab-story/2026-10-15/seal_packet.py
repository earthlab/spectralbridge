"""Seal the final editorial packet without changing its scientific sources."""

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
DEST = BASE / "packet_manifest.json"


def main():
    evidence = json.loads((BASE / "evidence_manifest.json").read_text())
    files = [
        p
        for p in BASE.rglob("*")
        if p.is_file() and p != DEST and "__pycache__" not in p.parts
    ]
    files.append(REPO / evidence["pdf"])
    hashes = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(files)
    }
    DEST.write_text(
        json.dumps(
            {"status": "complete", "date": "2026-10-15", "files": hashes}, indent=2
        )
        + "\n"
    )
    for name, digest in hashes.items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest, name
    print(f"Sealed and verified {len(hashes)} packet files.")


if __name__ == "__main__":
    main()
