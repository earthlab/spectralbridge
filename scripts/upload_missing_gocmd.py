#!/usr/bin/env python3
"""Upload all NEON_TM_5 products to CyVerse, one ``gocmd put`` at a time.

Local layout expected::

    NEON_TM_5/
      <flight_id>.h5                  # often a symlink — real file is uploaded
      <flight_id>/
        <products...>
        qa_plots/
          ...

Creates remote collections with ``gocmd mkdir`` as needed. Skips
``.duckdb_tmp`` / ``__pycache__`` / checkpoints. No ``gocmd ls`` parsing.

Run from repo root::

    cd /home/jovyan/data-store/spectralbridge
    python scripts/upload_missing_gocmd.py --dry-run
    python scripts/upload_missing_gocmd.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


LOCAL_ROOT = Path("NEON_TM_5")
REMOTE_ROOT = (
    "/iplant/home/shared/earthlab/macrosystems/Processed_NEON_TM_July_2026/NEON_TM_5"
)

FLIGHT_ID = "NEON_D10_R10C_DP1_L005-1_20210915_directional_reflectance"

SKIP_DIR_NAMES = {".duckdb_tmp", "__pycache__", ".ipynb_checkpoints"}


def _normalize_remote(path: str) -> str:
    p = path.strip().rstrip("/")
    if p.startswith("i:"):
        p = p[2:]
    if not p.startswith("/"):
        p = "/" + p
    return p


def _should_skip(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in SKIP_DIR_NAMES for part in rel_parts):
        return True
    if ".duckdb_tmp" in path.name.lower():
        return True
    return False


def _resolve_upload_source(path: Path) -> Path:
    """Follow symlinks so gocmd gets a real file (needed for .h5)."""
    if path.is_symlink():
        target = path.resolve()
        if not target.is_file():
            raise FileNotFoundError(f"Broken symlink: {path} -> {target}")
        return target
    return path


def _collect_jobs(local_root: Path, remote_root: str) -> list[tuple[Path, str]]:
    """Build (local_real_file, remote_object_path) jobs preserving relative layout."""
    jobs: list[tuple[Path, str]] = []
    for path in sorted(local_root.rglob("*")):
        if path.is_dir():
            continue
        if not (path.is_file() or path.is_symlink()):
            continue
        if _should_skip(path, local_root):
            continue
        rel = path.relative_to(local_root).as_posix()
        src = _resolve_upload_source(path)
        remote = f"{remote_root.rstrip('/')}/{rel}"
        jobs.append((src, remote))
    return jobs


def _run(cmd: list[str], *, dry_run: bool) -> int:
    print(f"→ {' '.join(cmd)}")
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


def _ensure_remote_dirs(
    gocmd: Path,
    remote_root: str,
    remote_paths: list[str],
    *,
    dry_run: bool,
) -> None:
    """``gocmd mkdir`` each unique parent collection under remote_root (depth order)."""
    root = _normalize_remote(remote_root)
    needed: set[str] = {root}

    for remote in remote_paths:
        parent = _normalize_remote(str(Path(remote).parent))
        if parent == root or parent.startswith(root + "/"):
            rel = parent[len(root) :].lstrip("/")
            cur = root
            if rel:
                for piece in rel.split("/"):
                    cur = f"{cur}/{piece}"
                    needed.add(cur)

    ordered = sorted(needed, key=lambda p: p.count("/"))
    print(f"\nEnsuring {len(ordered)} remote collections exist…")
    for d in ordered:
        rc = _run([str(gocmd), "mkdir", d], dry_run=dry_run)
        if rc not in (0,) and not dry_run:
            print(f"  (mkdir rc={rc} for {d} — continuing if collection already exists)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gocmd", type=Path, default=Path("./gocmd"))
    parser.add_argument("--local-root", type=Path, default=LOCAL_ROOT)
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-csv",
        action="store_true",
        help="Skip *.csv uploads",
    )
    parser.add_argument(
        "--skip-h5",
        action="store_true",
        help="Skip *.h5 uploads",
    )
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    gocmd = args.gocmd if args.gocmd.is_file() else cwd / "gocmd"
    if not gocmd.is_file():
        print(f"❌ gocmd not found at {args.gocmd}", file=sys.stderr)
        return 2

    local_root = args.local_root
    if not local_root.is_absolute():
        local_root = (cwd / local_root).resolve()
    if not local_root.is_dir():
        print(f"❌ Local root missing: {local_root}", file=sys.stderr)
        return 2

    remote_root = _normalize_remote(args.remote_root)

    # Sanity: expected flightline folder
    flight_dir = local_root / FLIGHT_ID
    if not flight_dir.is_dir():
        print(f"⚠️  Expected flightline dir missing: {flight_dir}")

    jobs = _collect_jobs(local_root, remote_root)
    if args.skip_csv:
        jobs = [(s, r) for s, r in jobs if not r.lower().endswith(".csv")]
    if args.skip_h5:
        jobs = [(s, r) for s, r in jobs if not r.lower().endswith(".h5")]

    if not jobs:
        print("❌ No files found to upload.")
        return 1

    print(f"LOCAL : {local_root}")
    print(f"REMOTE: {remote_root}")
    print(f"Files to upload: {len(jobs)}")
    total = 0
    for src, remote in jobs:
        size = src.stat().st_size
        total += size
        print(f"  - {Path(remote).name}  ({size} bytes)  ← {src}")
    print(f"Total: {total / (1024**3):.2f} GiB")

    _ensure_remote_dirs(
        gocmd, remote_root, [r for _, r in jobs], dry_run=args.dry_run
    )

    if args.dry_run:
        print("\nDry run — no uploads performed.")
        return 0

    failed: list[str] = []
    for i, (src, remote) in enumerate(jobs, start=1):
        # Ensure immediate parent exists (qa_plots etc.)
        parent = _normalize_remote(str(Path(remote).parent))
        _run([str(gocmd), "mkdir", parent], dry_run=False)

        cmd = [str(gocmd), "put", str(src), remote]
        print(f"\n[{i}/{len(jobs)}] {' '.join(cmd)}")
        t0 = time.time()
        rc = subprocess.run(cmd).returncode
        dt = time.time() - t0
        if rc != 0:
            print(f"  ❌ failed (rc={rc}) after {dt:.1f}s")
            failed.append(remote)
        else:
            print(f"  ✅ done in {dt:.1f}s")

    if failed:
        print(f"\n⚠️  Failed ({len(failed)}):")
        for r in failed:
            print(f"  - {r}")
        return 1

    print("\n🎉 All NEON_TM_5 files uploaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
