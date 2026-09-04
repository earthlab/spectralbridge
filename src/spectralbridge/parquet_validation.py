"""Package-local validation for SpectralBridge Parquet sidecars."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Sequence

import pyarrow.parquet as pq


def is_ok_columns(columns: Sequence[str]) -> bool:
    """Return whether spectral columns are named and ordered per stage."""

    spectral = [column for column in columns if "_wl" in column]
    last_seen: dict[str, int] = {}
    for column in spectral:
        match = re.search(r"(.+)_b\d+_wl(\d+)nm$", column)
        if match is None:
            return False
        stage, wavelength_text = match.group(1), match.group(2)
        wavelength = int(wavelength_text)
        if wavelength < last_seen.get(stage, -1):
            return False
        last_seen[stage] = wavelength
    return True


def collect_issues(root: Path) -> list[tuple[str, str]]:
    """Return validation issues for every direct Parquet child of ``root``."""

    issues: list[tuple[str, str]] = []
    for parquet_path in sorted(Path(root).glob("*.parquet")):
        columns: list[str] | None = None
        try:
            columns = list(pq.read_schema(parquet_path).names)
        except Exception as exc:
            try:
                # Preserve support for the lightweight JSON fixture historically
                # accepted by the repository validator.
                data = json.loads(parquet_path.read_text(encoding="utf-8"))
                names = data.get("columns")
                if isinstance(names, list):
                    columns = [str(name) for name in names]
            except Exception:
                columns = None
            if columns is None:
                issues.append(
                    (
                        parquet_path.name,
                        "unable to read schema "
                        f"({exc}). Delete or regenerate this file.",
                    )
                )
                continue
        if "lon" not in columns or "lat" not in columns:
            issues.append(
                (
                    parquet_path.name,
                    "missing lat/lon (rerun the pipeline or use the installed "
                    "longitude/latitude repair API)",
                )
            )
            continue
        if not is_ok_columns(columns):
            issues.append(
                (parquet_path.name, "spectral columns unsorted or misnamed")
            )
    return issues


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the installed Parquet-validator command line."""

    parser = argparse.ArgumentParser(
        description="Validate Parquet sidecars produced by SpectralBridge."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory containing Parquet files to validate.",
    )
    parser.add_argument(
        "--soft",
        action="store_true",
        help="Report invalid files but exit with status 0 instead of 1.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Validate one directory and return a command-line status code."""

    args = parse_args(argv)
    issues = collect_issues(Path(args.path))
    if issues:
        print("❌ Issues found:")
        for name, message in issues:
            print(" -", name, "→", message)
        return 0 if args.soft else 1

    print("✅ All parquet files look consistent.")
    return 0


__all__ = ["collect_issues", "is_ok_columns", "main", "parse_args"]

