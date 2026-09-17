#!/usr/bin/env python3
"""Compare local pipeline outputs vs CyVerse (gocmd ls), ignoring .h5 and .csv.

Run from the spectralbridge repo root on JupyterHub::

    cd /home/jovyan/data-store/spectralbridge
    python scripts/compare_gocmd_upload.py \\
      --local-dirs NEON_TM_1 NEON_TM_2 \\
      --remote-root /iplant/home/shared/earthlab/macrosystems/Processed_NEON_TM_July_2026

``gocmd ls`` returns plain text. This script parses indented file names and
``C-`` collection lines, then diffs against the local tree.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_REMOTE_ROOT = (
    "/iplant/home/shared/earthlab/macrosystems/Processed_NEON_TM_July_2026"
)

# Skip these suffixes / name patterns when checking "did science products upload?"
SKIP_SUFFIXES = {".h5", ".csv"}
SKIP_DIR_NAMES = {".duckdb_tmp", "__pycache__", ".ipynb_checkpoints"}
SKIP_NAME_SUBSTRINGS = (".duckdb_tmp",)


_FILE_LINE = re.compile(r"^\s{2,}(?!C-\s)(\S.*\S|\S)\s*$")
_COLL_LINE = re.compile(r"^\s*C-\s+(?P<path>\S+)\s*$")
_HEADER_LINE = re.compile(r"^(?P<path>/iplant/\S+):\s*$")


def _should_skip_local(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in SKIP_DIR_NAMES for part in rel_parts):
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    name = path.name.lower()
    if any(s in name for s in SKIP_NAME_SUBSTRINGS):
        return True
    if path.is_symlink() and path.suffix.lower() == ".h5":
        return True
    return False


def _local_files(local_dir: Path) -> dict[str, Path]:
    """Map relative posix path -> absolute path for files we care about."""

    out: dict[str, Path] = {}
    for p in local_dir.rglob("*"):
        if not p.is_file() and not p.is_symlink():
            continue
        # Treat symlink-to-file as a file entry
        if p.is_dir():
            continue
        if _should_skip_local(p, local_dir):
            continue
        rel = p.relative_to(local_dir).as_posix()
        out[rel] = p
    return out


def _normalize_remote(path: str) -> str:
    """Prefer /iplant/... ; also accept i:/iplant/..."""
    p = path.strip().rstrip("/")
    if p.startswith("i:"):
        p = p[2:]
    if not p.startswith("/"):
        p = "/" + p
    return p


def _run_gocmd_ls(gocmd: Path, remote_path: str, *, debug: bool = False) -> str:
    remote_path = _normalize_remote(remote_path)
    cmd = [str(gocmd), "ls", remote_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if debug:
        print(f"--- raw gocmd ls {remote_path!r} (rc={proc.returncode}) ---")
        if proc.stdout:
            print(proc.stdout.rstrip() or "(empty stdout)")
        else:
            print("(empty stdout)")
        if proc.stderr:
            print("--- stderr ---")
            print(proc.stderr.rstrip())
        print("--- end raw ---")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"gocmd ls failed ({proc.returncode}) for {remote_path}:\n{err}")
    # Some gocmd builds print the listing on stderr
    text = proc.stdout or ""
    if not text.strip() and proc.stderr and "/iplant/" in proc.stderr:
        text = proc.stderr
    return text


def _parse_gocmd_ls(text: str) -> tuple[set[str], set[str]]:
    """Return (relative_file_paths, collection_basenames) from gocmd ls text.

    ``gocmd ls`` on a directory typically looks like::

        /iplant/.../flightline:
          file_a.img
          file_b.parquet
          C- /iplant/.../flightline/qa_plots

    For a single-level listing we store filenames as their basename.
    For recursive listings that print multiple headers, we rebuild paths
    relative to the first header root.
    """

    files: set[str] = set()
    collections: set[str] = set()
    current_dir: str | None = None
    root_dir: str | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue

        header = _HEADER_LINE.match(line)
        if header:
            current_dir = header.group("path").rstrip("/")
            if root_dir is None:
                root_dir = current_dir
            continue

        coll = _COLL_LINE.match(line)
        if coll:
            full = coll.group("path").rstrip("/")
            collections.add(Path(full).name)
            # Also record as a relative folder path if under root
            if root_dir and full.startswith(root_dir + "/"):
                collections.add(full[len(root_dir) + 1 :])
            elif root_dir and full == root_dir:
                pass
            continue

        # Indented file entry (basename only in non-recursive ls)
        file_m = _FILE_LINE.match(line)
        if file_m and not line.strip().startswith("C-"):
            name = file_m.group(1).strip()
            # Skip weird progress / noise
            if name.endswith(":"):
                continue
            if current_dir and root_dir:
                if current_dir == root_dir:
                    files.add(name)
                elif current_dir.startswith(root_dir + "/"):
                    rel_dir = current_dir[len(root_dir) + 1 :]
                    files.add(f"{rel_dir}/{name}")
                else:
                    files.add(name)
            else:
                files.add(name)
            continue

        # Sometimes entries are printed without a trailing header context
        # as absolute paths — keep basename.
        if line.startswith("/iplant/") and not line.endswith(":"):
            files.add(Path(line.strip()).name)

    return files, collections


def _list_remote_tree(gocmd: Path, remote_dir: str, *, debug: bool = False) -> set[str]:
    """List remote files under ``remote_dir`` (one-level + known subfolders).

    Strategy:
      1. ls the flightline / top folder
      2. For each collection found (e.g. qa_plots), ls that too and prefix paths
    """

    text = _run_gocmd_ls(gocmd, remote_dir, debug=debug)
    files, collections = _parse_gocmd_ls(text)
    remote_files = set(files)

    # Expand one level of subcollections (qa_plots, etc.)
    for coll in sorted(collections):
        # collections set may contain bare names or relative paths
        if "/" in coll:
            remote_coll = f"{remote_dir.rstrip('/')}/{coll}"
            prefix = coll
        else:
            remote_coll = f"{remote_dir.rstrip('/')}/{coll}"
            prefix = coll
        try:
            sub_text = _run_gocmd_ls(gocmd, remote_coll, debug=debug)
        except RuntimeError as exc:
            print(f"  ⚠️  could not ls collection {remote_coll}: {exc}")
            continue
        sub_files, sub_colls = _parse_gocmd_ls(sub_text)
        for name in sub_files:
            remote_files.add(f"{prefix}/{name}")
        for sc in sub_colls:
            # record nested collection presence only
            remote_files.add(f"{prefix}/{sc}/")

    return remote_files


def _is_skipped_remote_name(name: str) -> bool:
    lower = name.lower()
    if lower.endswith(".h5") or lower.endswith(".csv"):
        return True
    if ".duckdb_tmp" in lower:
        return True
    return False


def compare_one(local_dir: Path, remote_dir: str, gocmd: Path, *, debug: bool = False) -> int:
    print("=" * 80)
    print(f"LOCAL : {local_dir}")
    print(f"REMOTE: {remote_dir}")
    print("=" * 80)

    if not local_dir.is_dir():
        print(f"❌ Local directory missing: {local_dir}")
        return 1

    local_map = _local_files(local_dir)
    print(f"Local files to check (excluding .h5/.csv/.duckdb_tmp): {len(local_map)}")

    try:
        remote_files = _list_remote_tree(gocmd, remote_dir, debug=debug)
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    remote_files = {f for f in remote_files if not _is_skipped_remote_name(f)}
    print(f"Remote files/collections parsed (excluding .h5/.csv): {len(remote_files)}")
    if not remote_files and not debug:
        print(
            "  (0 remote files — re-run with --debug to dump raw gocmd ls, "
            "or check whether this remote path exists)"
        )

    missing = sorted(rel for rel in local_map if rel not in remote_files)
    # Extra remote files that aren't on local (informational)
    extra = sorted(
        rf
        for rf in remote_files
        if not rf.endswith("/") and rf not in local_map
    )

    if not missing:
        print("✅ All checked local files are present on CyVerse (names match).")
    else:
        print(f"❌ Missing on CyVerse ({len(missing)}):")
        for rel in missing:
            size = local_map[rel].stat().st_size if local_map[rel].exists() else -1
            print(f"  - {rel}  (local size={size})")

    if extra:
        print(f"ℹ️  On CyVerse but not in local check set ({len(extra)}):")
        for rel in extra[:30]:
            print(f"  + {rel}")
        if len(extra) > 30:
            print(f"  ... and {len(extra) - 30} more")

    # Explicit note about skipped locals
    skipped_h5_csv = [
        p.relative_to(local_dir).as_posix()
        for p in local_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SKIP_SUFFIXES
    ]
    if skipped_h5_csv:
        print(f"⏭️  Skipped local .h5/.csv ({len(skipped_h5_csv)}):")
        for rel in sorted(skipped_h5_csv)[:20]:
            print(f"  ~ {rel}")
        if len(skipped_h5_csv) > 20:
            print(f"  ... and {len(skipped_h5_csv) - 20} more")

    print()
    return 1 if missing else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local-dirs",
        nargs="+",
        default=["NEON_TM_1", "NEON_TM_2"],
        help="Local directories under cwd to check",
    )
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument(
        "--gocmd",
        type=Path,
        default=Path("./gocmd"),
        help="Path to gocmd binary",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print raw gocmd ls stdout/stderr",
    )
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    gocmd = args.gocmd
    if not gocmd.is_file():
        # try repo-relative
        alt = cwd / "gocmd"
        if alt.is_file():
            gocmd = alt
        else:
            print(f"❌ gocmd not found at {args.gocmd} (cwd={cwd})", file=sys.stderr)
            return 2

    rc = 0
    for name in args.local_dirs:
        local_dir = (cwd / name).resolve()
        remote_dir = _normalize_remote(f"{args.remote_root.rstrip('/')}/{name}")

        if not local_dir.is_dir():
            print(f"❌ Local directory missing: {local_dir}")
            rc = max(rc, 1)
            continue

        flightline_dirs = sorted(
            child
            for child in local_dir.iterdir()
            if child.is_dir()
            and not child.name.startswith(".")
            and child.name not in SKIP_DIR_NAMES
        )

        if flightline_dirs:
            # Batch folder: compare each flightline directory to its remote twin
            for child in flightline_dirs:
                child_remote = _normalize_remote(f"{remote_dir}/{child.name}")
                rc = max(rc, compare_one(child, child_remote, gocmd, debug=args.debug))
        else:
            # Single folder of products
            rc = max(rc, compare_one(local_dir, remote_dir, gocmd, debug=args.debug))

    if rc == 0:
        print("🎉 Summary: no missing non-H5/non-CSV files detected.")
    else:
        print("⚠️  Summary: some files are missing on CyVerse (see above).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
