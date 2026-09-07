"""Command-line entry point for independent cross-run bulk analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from spectralbridge.bulk import SpectralLibraryPlotConfig
from spectralbridge.pipelines.bulk import run_bulk_pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Catalog completed SpectralBridge flightlines and run bounded, "
            "read-in-place hierarchical translation analyses."
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
        "--analysis",
        default="translation",
        help="Analysis profile name (default: translation).",
    )
    parser.add_argument(
        "--sensor",
        action="append",
        dest="sensors",
        default=None,
        help=(
            "Limit translation to pairs containing only the named sensors. "
            "Repeat for each sensor in the desired relationship."
        ),
    )
    parser.add_argument(
        "--translation-pair",
        action="append",
        dest="translation_pairs",
        default=None,
        help="Built-in translation-pair key to select; may be repeated.",
    )
    parser.add_argument(
        "--on-invalid",
        choices=("exclude", "error"),
        default="exclude",
        help="Exclude invalid flightlines (default) or report and raise an error.",
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
            "Build the collection even when no requested translation columns exist."
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
        help="Concurrent flightline readers (default: 1, conservative for I/O).",
    )
    parser.add_argument(
        "--extraction-chunk-size",
        type=int,
        default=2048,
        help="Maximum ENVI streaming-window edge (default: 2048).",
    )
    parser.add_argument(
        "--diagnostic-sample-size",
        type=int,
        default=0,
        help="Optional global maximum number of sampled pixel pairs (default: 0).",
    )
    parser.add_argument(
        "--diagnostic-seed",
        type=int,
        default=0,
        help="Seed for deterministic bounded diagnostic sampling (default: 0).",
    )
    parser.add_argument(
        "--spectral-library",
        type=Path,
        default=None,
        help="Existing merged polygon spectral-library Parquet to read in place.",
    )
    parser.add_argument(
        "--make-summary-plots",
        action="store_true",
        help="Create compact species-median and observation-count PDFs.",
    )
    parser.add_argument(
        "--make-full-spectral-reports",
        action="store_true",
        help="Explicitly create the expensive multipage trace and hierarchy PDFs.",
    )
    parser.add_argument(
        "--spectral-stage",
        default=None,
        help="Wavelength-bearing column prefix to plot, such as corr.",
    )
    parser.add_argument(
        "--species-field",
        default=None,
        help="Species column override when it cannot be detected safely.",
    )
    parser.add_argument(
        "--species-sort",
        choices=("count_desc", "alphabetical"),
        default="count_desc",
        help="Species panel ordering (default: count_desc).",
    )
    parser.add_argument(
        "--spectral-panels-per-page",
        type=int,
        default=4,
        help="Readable panels per multipage PDF page (default: 4).",
    )
    parser.add_argument(
        "--spectral-trace-batch-size",
        type=int,
        default=2_000,
        help="Maximum spectra held in one plotting batch (default: 2000).",
    )
    parser.add_argument(
        "--spectral-summary-band-batch-size",
        type=int,
        default=32,
        help="Maximum bands summarized per DuckDB pass (default: 32).",
    )
    parser.add_argument(
        "--spectral-max-traces-per-group",
        type=int,
        default=None,
        help="Explicit deterministic per-group trace cap; default renders every trace.",
    )
    parser.add_argument(
        "--spectral-sampling-seed",
        type=int,
        default=0,
        help="Seed used only with an explicit per-group trace cap.",
    )
    parser.add_argument(
        "--spectral-raster-dpi",
        type=int,
        default=150,
        help="DPI for the rasterized low-alpha trace layer (default: 150).",
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
    spectral_config = SpectralLibraryPlotConfig(
        species_field=args.species_field,
        spectral_stage=args.spectral_stage,
        species_sort=args.species_sort,
        panels_per_page=args.spectral_panels_per_page,
        trace_batch_size=args.spectral_trace_batch_size,
        summary_band_batch_size=args.spectral_summary_band_batch_size,
        max_traces_per_group=args.spectral_max_traces_per_group,
        sampling_seed=args.spectral_sampling_seed,
        raster_dpi=args.spectral_raster_dpi,
    )
    result = run_bulk_pipeline(
        args.input_path,
        args.output_dir,
        input_kind=args.input_kind,
        input_mode=args.input_mode,
        analysis=args.analysis,
        sensors=args.sensors,
        translation_pairs=args.translation_pairs,
        on_invalid=args.on_invalid,
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
        diagnostic_sample_size=args.diagnostic_sample_size,
        diagnostic_seed=args.diagnostic_seed,
        spectral_library=args.spectral_library,
        make_summary_plots=args.make_summary_plots,
        make_full_spectral_reports=args.make_full_spectral_reports,
        spectral_library_config=spectral_config,
        force=args.force,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


__all__ = ["main"]
