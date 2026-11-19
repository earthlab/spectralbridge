#!/usr/bin/env python3
"""Verify shared bytes, or explicitly refresh the manifest after a reviewed update.

Uses only Python's standard library. Never treats virtual environments or caches
as shareable deliverables. Run with --verify or --write from any working directory.
"""

import argparse
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "SHA256SUMS.txt"
EXCLUDED = {".venv", "__pycache__", ".git", ".pytest_cache", ".mplconfig", ".DS_Store"}


def entries():
    return {
        str(path.relative_to(HERE).as_posix()): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(HERE.rglob("*"))
        if path.is_file()
        and path != MANIFEST
        and not EXCLUDED.intersection(path.relative_to(HERE).parts)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="Record current reviewed files"
    )
    mode.add_argument(
        "--verify", action="store_true", help="Fail on missing, changed or extra files"
    )
    args = parser.parse_args()
    actual = entries()
    if args.write:
        MANIFEST.write_text(
            "".join(f"{digest}  {name}\n" for name, digest in actual.items())
        )
        print(f"Recorded {len(actual)} files in {MANIFEST.name}")
    else:
        expected = {}
        for line in MANIFEST.read_text().splitlines():
            digest, name = line.split("  ", 1)
            expected[name] = digest
        if expected != actual:
            for name in sorted(set(expected) | set(actual)):
                if expected.get(name) != actual.get(name):
                    print(f"Missing, changed or unrecorded: {name}")
            raise SystemExit(1)
        print(f"Verified {len(actual)} files")


if __name__ == "__main__":
    main()
