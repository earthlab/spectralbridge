"""Command-line entry point for independent cross-run bulk analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from spectralbridge.pipelines.bulk import run_bulk_pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recursively collect completed SpectralBridge merged Parquets and "
            "calculate pooled synthetic MicaSense-to-Landsat regressions."
        )
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="A merged Parquet file or root directory tree to search recursively.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Dedicated bulk output directory (default: "
            "INPUT_PATH/spectralbridge_bulk)."
        ),
    )
    parser.add_argument(
        "--input-kind",
        choices=("full", "polygon", "both"),
        default="full",
        help="Merged table type to include. Defaults to full-pixel tables.",
    )
    parser.add_argument(
        "--minimum-reflectance",
        type=float,
        default=0.0,
        help="Inclusive lower bound for both regression variables (default: 0).",
    )
    parser.add_argument(
        "--allow-no-translation",
        action="store_true",
        help=(
            "Build the collection even when no paired MicaSense/Landsat "
            "columns exist."
        ),
    )
    parser.add_argument(
        "--row-group-size",
        type=int,
        default=50_000,
        help="Rows per output Parquet row group (default: 50000).",
    )
    parser.add_argument(
        "--memory-limit",
        default=None,
        help="Optional DuckDB memory limit such as 8GB.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Optional DuckDB worker-thread count.",
    )
    parser.add_argument(
        "--temp-directory",
        type=Path,
        default=None,
        help="Optional DuckDB spill directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild outputs even when the source inventory is unchanged.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    result = run_bulk_pipeline(
        args.input_path,
        args.output_dir,
        input_kind=args.input_kind,
        minimum_reflectance=args.minimum_reflectance,
        require_translation_pairs=not args.allow_no_translation,
        row_group_size=args.row_group_size,
        memory_limit=args.memory_limit,
        threads=args.threads,
        temp_directory=args.temp_directory,
        force=args.force,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


__all__ = ["main"]
