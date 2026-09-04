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
            "Catalog completed SpectralBridge flightlines, expose a virtual "
            "DuckDB population, and run hierarchical synthetic translation analyses."
        )
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help=(
            "A completed-flightline archive, merged Parquet, or directory tree "
            "to discover recursively."
        ),
    )
    parser.add_argument(
        "--input-mode",
        choices=("auto", "flightline_outputs", "merged_parquet"),
        default="auto",
        help=(
            "Input contract. Auto prefers canonical completed-flightline folders "
            "and falls back to merged Parquets."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help=(
            "Fresh bulk output directory outside the read-only input tree."
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
        help=(
            "Rows per optional materialized observation Parquet row group "
            "(default: 50000)."
        ),
    )
    parser.add_argument(
        "--materialize-observations",
        action="store_true",
        help=(
            "Write a portable super-Parquet. Disabled by default because it may "
            "require multi-terabyte disk space."
        ),
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
        "--extraction-workers",
        type=int,
        default=1,
        help="Concurrent flightline extractions (default: 1, conservative for I/O).",
    )
    parser.add_argument(
        "--extraction-chunk-size",
        type=int,
        default=2048,
        help="Maximum ENVI window edge and Parquet row-group size (default: 2048).",
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
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Write catalogs and the metadata-only dataset census, then stop.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    result = run_bulk_pipeline(
        args.input_path,
        args.output_dir,
        input_kind=args.input_kind,
        input_mode=args.input_mode,
        minimum_reflectance=args.minimum_reflectance,
        require_translation_pairs=not args.allow_no_translation,
        materialize_observations=args.materialize_observations,
        row_group_size=args.row_group_size,
        memory_limit=args.memory_limit,
        threads=args.threads,
        temp_directory=args.temp_directory,
        preflight_only=args.preflight_only,
        extraction_workers=args.extraction_workers,
        extraction_chunk_size=args.extraction_chunk_size,
        force=args.force,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


__all__ = ["main"]
