#!/usr/bin/env python3
"""Site-specific maintainer upload utility; not a SpectralBridge entry point.

Call from a notebook or the shell with one or more local sources and one
CyVerse destination as the last argument. A source may be a folder or a
single file. gocmd progress and mkdir warnings are suppressed.

Notebook::

    from move_folders_from_instance_to_remote import run_transfer

    run_transfer(
        "/home/jovyan/data-store/spectralbridge/NIWO_a01",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines",
    )
    run_transfer(
        "/home/jovyan/data-store/spectralbridge/NIWO_a01",
        "/home/jovyan/data-store/spectralbridge/NIWO_a02",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines",
    )

Shell::

    python move_folders_from_instance_to_remote.py SOURCE [SOURCE ...] DESTINATION
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# When True, skip remote files that already match local size (``--diff
# --no_hash``) and overwrite without prompting when the size differs (``-f``).
SKIP_EXISTING = True

# Extra filename suffixes to omit from upload. Leave empty to include CSVs.
SKIP_SUFFIXES: set[str] = set()

# Jupyter autosaves and other non-product directories.
SKIP_DIR_NAMES = {".duckdb_tmp", ".ipynb_checkpoints", "__pycache__"}

# Failed ``gocmd put`` rows for the current invocation.
FAILURE_LOG = Path("gocmd_upload_failures.log")


def gocmd_exists() -> None:
    if not Path("./gocmd").exists():
        raise RuntimeError("ERROR: ./gocmd binary not found here.")


def _remote_parent_chain(path: str) -> list[str]:
    """Return remote folders from shallowest to deepest.

    CyVerse paths look like ``i:/iplant/home/shared/...``. Some ``gocmd mkdir``
    setups do not create intermediate folders recursively, so nested QA paths
    like ``.../qa/stages/00_acquisition`` need every ancestor created first.
    """
    normalized = path.rstrip("/")
    if not normalized:
        return []

    parts = normalized.split("/")
    if len(parts) < 2:
        return [normalized]

    chain: list[str] = []
    current = parts[0]
    for part in parts[1:]:
        current = f"{current}/{part}"
        chain.append(current)
    return chain


def ensure_remote_folder(path: str) -> None:
    for folder in _remote_parent_chain(path):
        subprocess.run(
            ["./gocmd", "mkdir", folder],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _is_jupyter_checkpoint(name: str) -> bool:
    """True for Jupyter autosaves like ``overview-checkpoint.png``."""
    stem = Path(name).stem.lower()
    return stem.endswith("-checkpoint") or ".ipynb_checkpoints" in name


def collect_files(local_root: Path) -> list[Path]:
    """Recursively collect files, excluding DuckDB temp and Jupyter checkpoints."""
    file_list: list[Path] = []

    for root, dirs, files in os.walk(local_root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        root_path = Path(root)
        for f in files:
            path = root_path / f
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            if _is_jupyter_checkpoint(f):
                continue
            file_list.append(path)

    return file_list


def record_failure(local_file: Path, remote_file: str, reason: str) -> None:
    """Append one failure line and close the log immediately."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp}\t{reason}\t{local_file}\t{remote_file}\n"
    with FAILURE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
    print(f"FAILED ({reason}): {local_file.name}", flush=True)
    print(f"  recorded in {FAILURE_LOG.resolve()}", flush=True)


def reset_failure_log() -> None:
    """Replace any prior log so each transfer run starts fresh."""
    if FAILURE_LOG.exists():
        FAILURE_LOG.unlink()


def upload_file(local_file: Path, remote_file: str, label: str) -> bool:
    """Upload one file. Print only the filename; keep gocmd output off-screen."""
    print(f"Transferring {label}: {local_file.name}", flush=True)

    remote_parent = remote_file.rsplit("/", 1)[0]
    ensure_remote_folder(remote_parent)

    cmd = ["./gocmd", "put", "--quiet", "--icat", "-f"]
    if SKIP_EXISTING:
        cmd.extend(["--diff", "--no_hash"])
    cmd.extend([str(local_file), remote_parent + "/"])

    try:
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        record_failure(local_file, remote_file, f"exception:{type(exc).__name__}:{exc}")
        return False

    if result.returncode != 0:
        reason = f"rc={result.returncode}"
        err = (result.stderr or "").strip()
        if err:
            reason = f"{reason}:{err.splitlines()[-1][:200]}"
        record_failure(local_file, remote_file, reason)
        return False
    return True


def upload_source(local_path: str, destination: str) -> list[Path]:
    """Upload a folder (recursive) or a single file into ``destination``."""
    path = Path(local_path).resolve()
    dest = destination.rstrip("/")

    if path.is_file():
        if path.suffix.lower() in SKIP_SUFFIXES or _is_jupyter_checkpoint(path.name):
            print(f"Skipping {path.name}", flush=True)
            return []
        remote_path = f"{dest}/{path.name}"
        print(f"Source: {path}", flush=True)
        print(f"Remote: {remote_path}", flush=True)
        print("Files to transfer: 1", flush=True)
        ensure_remote_folder(dest)
        if not upload_file(path, remote_path, "1/1"):
            return [path]
        return []

    if not path.is_dir():
        print(f"ERROR: source missing: {path}", flush=True)
        return [path]

    folder_name = path.name
    remote_target = f"{dest}/{folder_name}"
    ensure_remote_folder(remote_target)
    return upload_folder_contents(str(path), remote_target)


def upload_folder_contents(local_folder: str, remote_root: str) -> list[Path]:
    local_folder = Path(local_folder).resolve()
    all_files = collect_files(local_folder)
    print(f"Source: {local_folder}", flush=True)
    print(f"Remote: {remote_root}", flush=True)
    print(f"Files to transfer: {len(all_files)}", flush=True)

    failed: list[Path] = []
    total = len(all_files)
    for i, f in enumerate(all_files, start=1):
        rel_path = f.relative_to(local_folder)
        remote_path = f"{remote_root}/{rel_path.as_posix()}"
        if not upload_file(f, remote_path, f"{i}/{total}"):
            failed.append(f)

    if failed:
        print(f"Failed {len(failed)} file(s) in {local_folder.name}", flush=True)
    return failed


def run_transfer(*paths: str) -> int:
    """Upload one or more sources; the last argument is the CyVerse destination.

    Returns 0 on full success, 1 if any file failed. Intended for notebooks.
    """
    if len(paths) < 2:
        print("ERROR: need at least one source and a destination", flush=True)
        return 2

    *sources, destination = paths
    gocmd_exists()
    reset_failure_log()

    print("BEGIN TRANSFER", flush=True)
    for i, src in enumerate(sources, start=1):
        print(f"Source {i}: {src}", flush=True)
    print(f"Destination: {destination}", flush=True)
    print(f"Failure log: {FAILURE_LOG.resolve()}", flush=True)

    ensure_remote_folder(destination)

    all_failed: list[Path] = []
    for src in sources:
        all_failed.extend(upload_source(src, destination))

    if all_failed:
        print(f"FINISHED WITH {len(all_failed)} FAILURE(S). See {FAILURE_LOG.resolve()}", flush=True)
        return 1

    print("ALL TRANSFERS COMPLETED SUCCESSFULLY", flush=True)
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload one or more local folders or files to CyVerse. "
            "The last argument is the destination; everything before it is a source."
        )
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="SOURCE [SOURCE ...] DESTINATION",
    )
    args = parser.parse_args(argv)
    if len(args.paths) < 2:
        parser.error("need at least one source and a destination")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return run_transfer(*args.paths)


if __name__ == "__main__":
    sys.exit(main())
