"""Orchestration for the independent production bulk-analysis pipeline.

Discovery, the virtual DuckDB dataset, provenance, and scientific analyses
live under the dedicated spectralbridge.bulk package.
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import asdict, replace
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import math
import os
from pathlib import Path
from typing import Any, Sequence

import duckdb
import pyarrow.parquet as pq

from spectralbridge import __version__

from spectralbridge.bulk.analyses import (
    run_dataset_census,
    run_leave_one_site_out,
    run_sensor_translation,
)
from spectralbridge.bulk.analyses.streaming_translation import (
    run_streaming_translation_analyses,
)
from spectralbridge.bulk.analyses.spectral_library import (
    SpectralLibraryPaths,
    SpectralLibraryPlotConfig,
    inspect_spectral_library,
    inspect_spectral_library_preflight,
    run_spectral_library_analysis,
)
from spectralbridge.bulk.catalog import (
    build_bulk_catalog,
    catalog_signature_records,
    discover_bulk_sources,
)
from spectralbridge.bulk.dataset import create_bulk_database, finalize_bulk_database
from spectralbridge.bulk.exclusions import build_exclusion_records
from spectralbridge.bulk.flightline_outputs import (
    discover_completed_flightlines,
    extract_flightline_cache,
    find_canonical_flightline_directories,
)
from spectralbridge.bulk.models import (
    BULK_SCHEMA_VERSION,
    BulkAnalysisPaths,
    BulkInputKind,
    BulkInputMode,
    BulkSource,
    FlightlineRecord,
    SourceFileRecord,
)
from spectralbridge.bulk.provenance import signature_sha256, write_json_atomic
from spectralbridge.bulk.streaming import (
    compute_flightline_statistics,
    write_diagnostic_sample,
    write_statistics,
)
from spectralbridge.bulk.identity import (
    DEFAULT_IDENTITY_PARSERS,
    FlightlineIdentityParser,
)
from spectralbridge.bulk.registry import (
    DEFAULT_PRODUCT_REGISTRY,
    AnalysisProfile,
    ProductRegistry,
    TranslationPair,
    resolve_analysis_profile,
)


LOGGER = logging.getLogger(__name__)


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _prepare_output_directory(paths: BulkAnalysisPaths) -> None:
    output = paths.output_dir
    if output.exists() and not output.is_dir():
        raise NotADirectoryError(f"Bulk output path is not a directory: {output}")
    if output.exists() and any(output.iterdir()) and not paths.manifest.is_file():
        raise FileExistsError(
            "Bulk output directory is not empty and does not contain a recognized "
            f"bulk manifest: {output}. Choose a fresh output directory."
        )
    paths.ensure_directories()


def _input_signature(
    *,
    root: Path,
    paths: BulkAnalysisPaths,
    input_kind: BulkInputKind,
    input_mode: BulkInputMode,
    minimum_reflectance: float,
    materialize_observations: bool,
    row_group_size: int,
    preflight_only: bool,
    require_translation_pairs: bool,
    extraction_chunk_size: int,
    extraction_workers: int,
    diagnostic_sample_size: int,
    diagnostic_seed: int,
    spectral_library_schema: dict[str, Any] | None,
    spectral_library_config: SpectralLibraryPlotConfig,
    make_summary_plots: bool,
    make_full_spectral_reports: bool,
    analysis_profile: AnalysisProfile,
    product_registry: ProductRegistry,
    identity_parsers: Sequence[FlightlineIdentityParser],
    translation_pairs: tuple[TranslationPair, ...],
    on_invalid: str,
    source_files: list[SourceFileRecord],
    flightlines: list[FlightlineRecord],
) -> dict[str, Any]:
    return {
        "bulk_schema_version": BULK_SCHEMA_VERSION,
        "input_path": root.as_posix(),
        "output_dir": paths.output_dir.as_posix(),
        "input_kind": input_kind,
        "input_mode": input_mode,
        "minimum_reflectance": minimum_reflectance,
        "materialize_observations": materialize_observations,
        "row_group_size": row_group_size if materialize_observations else None,
        "preflight_only": preflight_only,
        "require_translation_pairs": require_translation_pairs,
        "extraction_chunk_size": extraction_chunk_size,
        "extraction_workers": extraction_workers,
        "diagnostic_sample_size": diagnostic_sample_size,
        "diagnostic_seed": diagnostic_seed,
        "spectral_library_schema": spectral_library_schema,
        "spectral_library_config": (
            asdict(spectral_library_config) if spectral_library_schema else None
        ),
        "make_summary_plots": make_summary_plots,
        "make_full_spectral_reports": make_full_spectral_reports,
        "analysis_profile": asdict(analysis_profile),
        "product_registry": [asdict(item) for item in product_registry.products],
        "identity_parsers": [parser.name for parser in identity_parsers],
        "translation_pairs": [asdict(item) for item in translation_pairs],
        "on_invalid": on_invalid,
        "catalog": catalog_signature_records(source_files, flightlines),
    }


def _relative_output(paths: BulkAnalysisPaths, path: Path) -> str:
    return path.relative_to(paths.output_dir).as_posix()


def _outputs_are_valid(
    paths: BulkAnalysisPaths,
    *,
    materialize_observations: bool,
    preflight_only: bool,
    input_mode: str,
    spectral_library_requested: bool,
    make_summary_plots: bool,
    make_full_spectral_reports: bool,
) -> bool:
    required = [
        paths.flightlines,
        paths.source_files,
        paths.source_products,
        paths.exclusions,
        paths.exclusions_json,
        paths.exclusions_csv,
        paths.duplicates,
        paths.rejected_sources,
        paths.database,
        paths.manifest,
        paths.analyses_dir / "dataset_census" / "dataset_census.parquet",
        paths.analyses_dir / "dataset_census" / "dataset_census.json",
        paths.analyses_dir / "dataset_census" / "dataset_census.md",
    ]
    if materialize_observations:
        required.append(paths.observations)
    if not preflight_only:
        required.extend(
            [
                paths.coefficients_parquet,
                paths.coefficients_json,
                paths.analyses_dir / "sensor_translation" / "pixel_pooled.parquet",
                paths.analyses_dir / "sensor_translation" / "per_flightline.parquet",
                paths.analyses_dir / "sensor_translation" / "per_site.parquet",
                paths.analyses_dir
                / "sensor_translation"
                / "flightline_balanced.parquet",
                paths.analyses_dir / "sensor_translation" / "site_balanced.parquet",
                paths.analyses_dir
                / "leave_one_site_out"
                / "leave_one_site_out.parquet",
            ]
        )
        if input_mode == "flightline_outputs" and not materialize_observations:
            required.append(paths.sufficient_statistics)
        if spectral_library_requested:
            spectral_paths = SpectralLibraryPaths.from_bulk_paths(paths)
            required.extend(
                [
                    spectral_paths.species_summary,
                    spectral_paths.species_band_summary,
                    spectral_paths.species_quantiles,
                    spectral_paths.species_medians,
                    spectral_paths.group_counts,
                    spectral_paths.species_plot_ranges,
                    spectral_paths.extreme_spectra,
                    spectral_paths.metadata,
                ]
            )
            if make_summary_plots or make_full_spectral_reports:
                required.extend(
                    [
                        spectral_paths.species_median_report,
                        spectral_paths.observation_counts,
                    ]
                )
            if make_full_spectral_reports:
                required.extend(
                    [
                        spectral_paths.species_variability,
                        spectral_paths.species_variability_full_range,
                        spectral_paths.species_quantile_report,
                    ]
                )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    try:
        if not preflight_only and spectral_library_requested:
            spectral_metadata = json.loads(
                SpectralLibraryPaths.from_bulk_paths(paths).metadata.read_text(
                    encoding="utf-8"
                )
            )
            if any(
                not Path(report["path"]).is_file()
                or Path(report["path"]).stat().st_size == 0
                for report in spectral_metadata.get("reports", {}).values()
            ):
                return False
        for parquet in (
            paths.flightlines,
            paths.source_files,
            paths.source_products,
            paths.exclusions,
            paths.duplicates,
            paths.rejected_sources,
        ):
            pq.read_schema(parquet)
        with duckdb.connect(str(paths.database), read_only=True) as con:
            con.execute("SELECT * FROM flightlines LIMIT 0").fetchall()
            con.execute("SELECT * FROM bulk_sources LIMIT 0").fetchall()
            con.execute("SELECT * FROM bulk_observations LIMIT 0").fetchall()
            con.execute("SELECT * FROM dataset_census_summary LIMIT 0").fetchall()
            if input_mode == "flightline_outputs" and not materialize_observations:
                con.execute(
                    "SELECT * FROM translation_sufficient_statistics LIMIT 0"
                ).fetchall()
            if not preflight_only:
                con.execute(
                    "SELECT * FROM candidate_translation_coefficients LIMIT 0"
                ).fetchall()
                con.execute(
                    "SELECT * FROM translation_leave_one_site_out LIMIT 0"
                ).fetchall()
                if spectral_library_requested:
                    con.execute(
                        "SELECT * FROM spectral_library_species_summary LIMIT 0"
                    ).fetchall()
                    con.execute(
                        "SELECT * FROM spectral_library_species_quantiles LIMIT 0"
                    ).fetchall()
                    con.execute(
                        "SELECT * FROM spectral_library_species_plot_ranges LIMIT 0"
                    ).fetchall()
                    con.execute(
                        "SELECT * FROM spectral_library_extreme_spectra LIMIT 0"
                    ).fetchall()
    except Exception:
        return False
    return True


def _result(
    paths: BulkAnalysisPaths,
    *,
    input_path: Path,
    status: str,
    accepted_flightline_count: int,
    duplicate_count: int,
    rejected_count: int,
    row_count: int,
    translation_pair_count: int,
    materialize_observations: bool,
    preflight_only: bool,
    input_mode: str,
    analysis_profile: AnalysisProfile,
    translation_pairs: tuple[TranslationPair, ...],
    diagnostic_sample_size: int,
    spectral_library_schema: dict[str, Any] | None,
    spectral_library_preflight: dict[str, Any] | None,
    spectral_library_requested: bool,
) -> dict[str, Any]:
    try:
        census = json.loads(
            (
                paths.analyses_dir
                / "dataset_census"
                / "dataset_census.json"
            ).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        census = {}
    spectral_paths = SpectralLibraryPaths.from_bulk_paths(paths)
    spectral_library_result = None
    if spectral_library_requested:
        try:
            spectral_library_result = json.loads(
                spectral_paths.metadata.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "status": status,
        "accepted_flightline_count": accepted_flightline_count,
        "source_count": accepted_flightline_count,
        "duplicate_count": duplicate_count,
        "rejected_source_count": rejected_count,
        "row_count": row_count,
        "translation_pair_count": translation_pair_count,
        "regression_count": translation_pair_count,
        "preflight_only": preflight_only,
        "input_mode": input_mode,
        "analysis": analysis_profile.name,
        "spectralbridge_version": __version__,
        "selected_translation_pairs": [item.key for item in translation_pairs],
        "materialized_observations": (
            str(paths.observations) if materialize_observations else None
        ),
        "observations": str(paths.observations) if materialize_observations else None,
        "flightlines": str(paths.flightlines),
        "source_files": str(paths.source_files),
        "source_products": str(paths.source_products),
        "exclusions": str(paths.exclusions),
        "exclusions_json": str(paths.exclusions_json),
        "exclusions_csv": str(paths.exclusions_csv),
        "cache": str(paths.cache_dir),
        "sufficient_statistics": (
            str(paths.sufficient_statistics)
            if paths.sufficient_statistics.is_file()
            else None
        ),
        "diagnostic_sample": (
            str(paths.diagnostic_sample)
            if diagnostic_sample_size and paths.diagnostic_sample.is_file()
            else None
        ),
        "source_catalog": str(paths.source_files),
        "duplicates": str(paths.duplicates),
        "rejected_sources": str(paths.rejected_sources),
        "coefficients_parquet": (
            None if preflight_only else str(paths.coefficients_parquet)
        ),
        "coefficients_json": None if preflight_only else str(paths.coefficients_json),
        "database": str(paths.database),
        "manifest": str(paths.manifest),
        "spectral_library": spectral_library_result,
        "preflight": {
            "source_root": input_path.as_posix(),
            "output_root": paths.output_dir.as_posix(),
            "analysis_profile": analysis_profile.name,
            "required_product_roles": list(
                analysis_profile.required_product_roles
            ),
            "optional_product_roles": list(
                analysis_profile.optional_product_roles
            ),
            "translation_pairs": [item.key for item in translation_pairs],
            "discovered_flightlines": int(
                census.get("candidate_flightline_records", 0)
            ),
            "accepted_flightlines": accepted_flightline_count,
            "duplicate_candidates": duplicate_count,
            "excluded_flightlines": rejected_count + duplicate_count,
            "selected_observation_rows": row_count,
            "selected_source_bytes": int(census.get("selected_source_bytes", 0)),
            "estimated_analysis_output_bytes": int(
                census.get("estimated_analysis_output_bytes", 0)
            ),
            "estimated_diagnostic_sample_bytes": diagnostic_sample_size * 64,
            "estimated_temporary_disk_bytes": (
                int(census.get("estimated_materialized_pixel_bytes", 0))
                if materialize_observations
                else 0
            ),
            "materialized_pixel_dataset": bool(materialize_observations),
            "estimated_materialized_pixel_bytes": (
                int(census.get("estimated_materialized_pixel_bytes", 0))
                if materialize_observations
                else 0
            ),
            "available_sensors": census.get("sensors", []),
            "available_translation_pairs": census.get(
                "available_translation_pairs", []
            ),
            "exclusion_counts_by_reason": census.get(
                "exclusion_counts_by_reason", {}
            ),
            "spectralbridge_version": __version__,
            "source_products": str(paths.source_products),
            "exclusions": str(paths.exclusions),
            "database": str(paths.database),
            "census": census,
            "spectral_library_schema": spectral_library_schema,
            "spectral_library": spectral_library_preflight,
        },
    }


def run_bulk_pipeline(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    input_kind: BulkInputKind = "full",
    input_mode: BulkInputMode = "auto",
    analysis: str | AnalysisProfile = "translation",
    sensors: tuple[str, ...] | list[str] | None = None,
    translation_pairs: Sequence[str | TranslationPair] | None = None,
    product_registry: ProductRegistry = DEFAULT_PRODUCT_REGISTRY,
    identity_parsers: Sequence[FlightlineIdentityParser] = DEFAULT_IDENTITY_PARSERS,
    on_invalid: str = "exclude",
    minimum_reflectance: float = 0.0,
    require_translation_pairs: bool = True,
    materialize_observations: bool = False,
    row_group_size: int = 50_000,
    memory_limit: str | None = None,
    threads: int | None = None,
    temp_directory: str | Path | None = None,
    preflight_only: bool = False,
    extraction_chunk_size: int = 2048,
    extraction_workers: int = 1,
    diagnostic_sample_size: int = 0,
    diagnostic_seed: int = 0,
    spectral_library: str | Path | None = None,
    make_summary_plots: bool = False,
    make_full_spectral_reports: bool = False,
    spectral_library_config: SpectralLibraryPlotConfig | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Catalog completed flightlines and run population analyses.

    The source tree is treated as read only. Scientific identity is recovered
    through configurable identity parsers, never arbitrary outer run-folder
    names. Duplicate flightline IDs in different source directories are
    cataloged and excluded from analysis.

    ``input_mode='auto'`` prefers canonical completed-flightline directories
    and falls back to prebuilt merged Parquets. Completed-flightline mode needs
    only the target products required by the selected profile and relationship;
    it reads them in bounded chunks and writes only compact, restart-safe
    sufficient statistics beneath ``output_dir``. Pixel observations are
    materialized only when ``materialize_observations=True`` is explicitly set.
    """

    root = Path(input_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Bulk input path does not exist: {root}")
    if output_dir is None:
        raise ValueError(
            "output_dir is required so bulk products are isolated from the "
            "read-only source tree"
        )
    resolved_output = Path(output_dir).expanduser().resolve()
    source_boundary = root if root.is_dir() else root.parent
    if _path_is_within(resolved_output, source_boundary):
        raise ValueError(
            "output_dir must be outside the read-only bulk input directory"
        )
    temporary_dir = (
        Path(temp_directory).expanduser().resolve()
        if temp_directory is not None
        else None
    )
    if temporary_dir is not None and _path_is_within(
        temporary_dir, source_boundary
    ):
        raise ValueError(
            "temp_directory must be outside the read-only bulk input directory"
        )
    if input_kind not in {"full", "polygon", "both"}:
        raise ValueError("input_kind must be 'full', 'polygon', or 'both'")
    if input_mode not in {"auto", "flightline_outputs", "merged_parquet"}:
        raise ValueError(
            "input_mode must be 'auto', 'flightline_outputs', or 'merged_parquet'"
        )
    if on_invalid not in {"exclude", "error"}:
        raise ValueError("on_invalid must be 'exclude' or 'error'")
    analysis_profile = resolve_analysis_profile(analysis)
    if not require_translation_pairs and analysis_profile.require_translation_pair:
        analysis_profile = replace(
            analysis_profile,
            required_product_roles=tuple(
                role
                for role in analysis_profile.required_product_roles
                if role != "target_sensor"
            ),
            require_translation_pair=False,
        )
    selected_pairs = product_registry.select_pairs(
        sensors=sensors,
        translation_pairs=translation_pairs,
        allowed_sensors=analysis_profile.allowed_sensors,
        allowed_matching_groups=analysis_profile.allowed_matching_groups,
        allow_empty=not analysis_profile.require_translation_pair,
    )
    minimum_reflectance = float(minimum_reflectance)
    if not math.isfinite(minimum_reflectance):
        raise ValueError("minimum_reflectance must be finite")
    if row_group_size < 1:
        raise ValueError("row_group_size must be at least 1")
    if threads is not None and threads < 1:
        raise ValueError("threads must be at least 1")
    if extraction_chunk_size < 1:
        raise ValueError("extraction_chunk_size must be at least 1")
    if extraction_workers < 1:
        raise ValueError("extraction_workers must be at least 1")
    if diagnostic_sample_size < 0:
        raise ValueError("diagnostic_sample_size must be at least 0")
    plot_config = spectral_library_config or SpectralLibraryPlotConfig()
    plot_config.validate()
    if (make_summary_plots or make_full_spectral_reports) and spectral_library is None:
        raise ValueError(
            "spectral_library is required when spectral-library plots are requested"
        )

    paths = BulkAnalysisPaths(resolved_output)
    _prepare_output_directory(paths)
    spectral_schema = (
        inspect_spectral_library(
            spectral_library,
            species_field=plot_config.species_field,
            spectral_stage=plot_config.spectral_stage,
        )
        if spectral_library is not None
        else None
    )
    if spectral_schema is not None and _path_is_within(
        spectral_schema.source, resolved_output
    ):
        raise ValueError("spectral_library must be outside the bulk output directory")
    spectral_schema_payload = spectral_schema.to_dict() if spectral_schema else None
    spectral_preflight_payload = (
        inspect_spectral_library_preflight(
            spectral_schema.source,
            config=plot_config,
        )
        if spectral_schema is not None
        else None
    )
    resolved_input_mode: BulkInputMode
    if input_mode == "auto":
        resolved_input_mode = (
            "flightline_outputs"
            if find_canonical_flightline_directories(
                root,
                exclude_dir=resolved_output,
                identity_parsers=identity_parsers,
            )
            else "merged_parquet"
        )
    else:
        resolved_input_mode = input_mode
    if resolved_input_mode == "flightline_outputs":
        if input_kind != "full":
            raise ValueError(
                "input_kind='polygon'/'both' applies only to merged_parquet mode"
            )
        source_files, flightlines = discover_completed_flightlines(
            root,
            exclude_dir=resolved_output,
            analysis_profile=analysis_profile,
            product_registry=product_registry,
            identity_parsers=identity_parsers,
            sensors=sensors,
            translation_pairs=selected_pairs,
        )
    else:
        source_files, flightlines = build_bulk_catalog(
            root,
            input_kind=input_kind,
            exclude_dir=resolved_output,
            analysis_profile=analysis_profile,
            product_registry=product_registry,
            identity_parsers=identity_parsers,
            sensors=sensors,
            translation_pairs=selected_pairs,
        )
    signature = _input_signature(
        root=root,
        paths=paths,
        input_kind=input_kind,
        input_mode=resolved_input_mode,
        minimum_reflectance=minimum_reflectance,
        materialize_observations=materialize_observations,
        row_group_size=row_group_size,
        preflight_only=preflight_only,
        require_translation_pairs=require_translation_pairs,
        extraction_chunk_size=extraction_chunk_size,
        extraction_workers=extraction_workers,
        diagnostic_sample_size=diagnostic_sample_size,
        diagnostic_seed=diagnostic_seed,
        spectral_library_schema=spectral_schema_payload,
        spectral_library_config=plot_config,
        make_summary_plots=make_summary_plots,
        make_full_spectral_reports=make_full_spectral_reports,
        analysis_profile=analysis_profile,
        product_registry=product_registry,
        identity_parsers=identity_parsers,
        translation_pairs=selected_pairs,
        on_invalid=on_invalid,
        source_files=source_files,
        flightlines=flightlines,
    )
    analysis_run_id = signature_sha256(signature)
    if not force and paths.manifest.is_file():
        try:
            previous = json.loads(paths.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
        if (
            previous.get("status") == "complete"
            and previous.get("input_signature_sha256") == analysis_run_id
            and _outputs_are_valid(
                paths,
                materialize_observations=materialize_observations,
                preflight_only=preflight_only,
                input_mode=resolved_input_mode,
                spectral_library_requested=spectral_schema is not None,
                make_summary_plots=make_summary_plots,
                make_full_spectral_reports=make_full_spectral_reports,
            )
        ):
            counts = previous["counts"]
            return _result(
                paths,
                input_path=root,
                status="reused",
                accepted_flightline_count=int(counts["accepted_flightlines"]),
                duplicate_count=int(counts["duplicate_candidates"]),
                rejected_count=int(counts["rejected_flightlines"]),
                row_count=int(counts["accepted_rows"]),
                translation_pair_count=int(counts["translation_pairs"]),
                materialize_observations=materialize_observations,
                preflight_only=preflight_only,
                input_mode=resolved_input_mode,
                analysis_profile=analysis_profile,
                translation_pairs=selected_pairs,
                diagnostic_sample_size=diagnostic_sample_size,
                spectral_library_schema=spectral_schema_payload,
                spectral_library_preflight=spectral_preflight_payload,
                spectral_library_requested=spectral_schema is not None,
            )

    statistics_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    if (
        resolved_input_mode == "flightline_outputs"
        and not preflight_only
        and materialize_observations
    ):
        extracted_sources: list[SourceFileRecord] = []
        updated: dict[str, FlightlineRecord] = {}

        def extract_one(
            item: FlightlineRecord,
        ) -> tuple[SourceFileRecord, FlightlineRecord]:
            return extract_flightline_cache(
                item,
                paths,
                analysis_run_id=analysis_run_id,
                chunk_size=extraction_chunk_size,
                translation_pairs=selected_pairs,
                force=force,
            )

        eligible = [item for item in flightlines if item.status == "accepted"]
        if extraction_workers == 1:
            for index, item in enumerate(eligible, start=1):
                LOGGER.info(
                    "Bulk extraction flightline %d/%d: %s",
                    index,
                    len(eligible),
                    item.canonical_flightline_id,
                )
                try:
                    source, refreshed = extract_one(item)
                except Exception as exc:
                    LOGGER.exception(
                        "Bulk extraction failed for %s; continuing",
                        item.canonical_flightline_id,
                    )
                    updated[item.candidate_id] = replace(
                        item,
                        status="rejected",
                        rejection_reason=f"extraction failed: {type(exc).__name__}: {exc}",
                        extraction_status="failure",
                        exclusion_reason_codes_json=json.dumps(
                            ["extraction_failure"]
                        ),
                        exclusion_context_json=json.dumps(
                            [
                                {
                                    "reason_code": "extraction_failure",
                                    "detail": str(exc),
                                    "processing_stage": "bulk_extraction",
                                }
                            ]
                        ),
                    )
                else:
                    extracted_sources.append(source)
                    updated[item.candidate_id] = refreshed
        else:
            with ThreadPoolExecutor(max_workers=extraction_workers) as pool:
                futures = {pool.submit(extract_one, item): item for item in eligible}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        source, refreshed = future.result()
                    except Exception as exc:
                        LOGGER.exception(
                            "Bulk extraction failed for %s; continuing",
                            item.canonical_flightline_id,
                        )
                        updated[item.candidate_id] = replace(
                            item,
                            status="rejected",
                            rejection_reason=(
                                f"extraction failed: {type(exc).__name__}: {exc}"
                            ),
                            extraction_status="failure",
                            exclusion_reason_codes_json=json.dumps(
                                ["extraction_failure"]
                            ),
                            exclusion_context_json=json.dumps(
                                [
                                    {
                                        "reason_code": "extraction_failure",
                                        "detail": str(exc),
                                        "processing_stage": "bulk_extraction",
                                    }
                                ]
                            ),
                        )
                    else:
                        extracted_sources.append(source)
                        updated[item.candidate_id] = refreshed
        flightlines = [updated.get(item.candidate_id, item) for item in flightlines]
        source_files = [*source_files, *extracted_sources]

    elif resolved_input_mode == "flightline_outputs" and not preflight_only:
        updated = {}
        eligible = sorted(
            (item for item in flightlines if item.status == "accepted"),
            key=lambda item: item.canonical_flightline_id or "",
        )
        quota_by_candidate = {
            item.candidate_id: diagnostic_sample_size // max(1, len(eligible))
            + (index < diagnostic_sample_size % max(1, len(eligible)))
            for index, item in enumerate(eligible)
        }

        def analyze_one(
            item: FlightlineRecord,
        ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], FlightlineRecord]:
            return compute_flightline_statistics(
                item,
                paths,
                chunk_size=extraction_chunk_size,
                minimum_reflectance=minimum_reflectance,
                translation_pairs=selected_pairs,
                diagnostic_sample_size=quota_by_candidate[item.candidate_id],
                diagnostic_seed=diagnostic_seed,
                force=force,
            )

        def record_failure(item: FlightlineRecord, exc: Exception) -> None:
            updated[item.candidate_id] = replace(
                item,
                status="rejected",
                rejection_reason=(
                    f"streaming statistics failed: {type(exc).__name__}: {exc}"
                ),
                extraction_status="statistics_failure",
                exclusion_reason_codes_json=json.dumps(["analysis_failure"]),
                exclusion_context_json=json.dumps(
                    [
                        {
                            "reason_code": "analysis_failure",
                            "detail": str(exc),
                            "processing_stage": "bulk_streaming_statistics",
                        }
                    ]
                ),
            )

        if extraction_workers == 1:
            for index, item in enumerate(eligible, start=1):
                LOGGER.info(
                    "Bulk streaming statistics flightline %d/%d: %s",
                    index,
                    len(eligible),
                    item.canonical_flightline_id,
                )
                try:
                    rows, samples, refreshed = analyze_one(item)
                except Exception as exc:
                    LOGGER.exception(
                        "Bulk streaming statistics failed for %s; continuing",
                        item.canonical_flightline_id,
                    )
                    record_failure(item, exc)
                else:
                    statistics_rows.extend(rows)
                    diagnostic_rows.extend(samples)
                    updated[item.candidate_id] = refreshed
        else:
            with ThreadPoolExecutor(max_workers=extraction_workers) as pool:
                futures = {pool.submit(analyze_one, item): item for item in eligible}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        rows, samples, refreshed = future.result()
                    except Exception as exc:
                        LOGGER.exception(
                            "Bulk streaming statistics failed for %s; continuing",
                            item.canonical_flightline_id,
                        )
                        record_failure(item, exc)
                    else:
                        statistics_rows.extend(rows)
                        diagnostic_rows.extend(samples)
                        updated[item.candidate_id] = refreshed
        flightlines = [updated.get(item.candidate_id, item) for item in flightlines]
        accepted_ids = {
            item.canonical_flightline_id
            for item in flightlines
            if item.status == "accepted"
        }
        statistics_rows = [
            row for row in statistics_rows if row["flightline_id"] in accepted_ids
        ]
        diagnostic_rows = [
            row for row in diagnostic_rows if row["flightline_id"] in accepted_ids
        ]
        statistics_rows.sort(
            key=lambda row: (
                row["flightline_id"],
                row["translation_pair"],
                row["band_index"],
            )
        )
        diagnostic_rows.sort(
            key=lambda row: (
                row["flightline_id"],
                row["translation_pair"],
                row["band_index"],
                row["pixel_id"],
            )
        )
        write_statistics(paths.sufficient_statistics, statistics_rows)
        if diagnostic_sample_size:
            write_diagnostic_sample(paths.diagnostic_sample, diagnostic_rows)
        elif paths.diagnostic_sample.exists():
            paths.diagnostic_sample.unlink()

    accepted_flightlines = [
        item for item in flightlines if item.status == "accepted"
    ]
    duplicate_flightlines = [
        item for item in flightlines if item.status == "duplicate_excluded"
    ]
    rejected_flightlines = [
        item for item in flightlines if item.status == "rejected"
    ]
    accepted_sources = [item for item in source_files if item.status == "accepted"]
    exclusions = build_exclusion_records(source_files, flightlines)
    accepted_rows = (
        sum(int(item.row_count or 0) for item in accepted_flightlines)
        if resolved_input_mode == "flightline_outputs" and not materialize_observations
        else sum(int(item.row_count or 0) for item in accepted_sources)
    )
    execution = {
        "threads": threads,
        "memory_limit": memory_limit,
        "temp_directory": str(temporary_dir) if temporary_dir else None,
    }
    building_manifest = {
        "schema_version": BULK_SCHEMA_VERSION,
        "pipeline": "spectralbridge_bulk_population_analysis",
        "status": "building",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_run_id": analysis_run_id,
        "input_signature_sha256": analysis_run_id,
        "input_signature": signature,
        "execution": execution,
        "spectralbridge_version": __version__,
        "git_commit": os.environ.get("GITHUB_SHA"),
    }
    write_json_atomic(paths.manifest, building_manifest)

    metadata = {
        "schema_version": BULK_SCHEMA_VERSION,
        "analysis_run_id": analysis_run_id,
        "input_path": root.as_posix(),
        "input_kind": input_kind,
        "input_mode": resolved_input_mode,
        "source_data_policy": "read_only",
        "identity_policy": (
            "canonical_flightline_directory_not_outer_folder"
            if resolved_input_mode == "flightline_outputs"
            else "canonical_product_filename_not_outer_folder"
        ),
        "duplicate_policy": "exclude_all_duplicate_canonical_id_candidates",
        "materialize_observations": materialize_observations,
        "minimum_reflectance": minimum_reflectance,
        "extraction_chunk_size": extraction_chunk_size,
        "extraction_workers": extraction_workers,
        "diagnostic_sample_size": diagnostic_sample_size,
        "diagnostic_seed": diagnostic_seed,
        "spectral_library_schema": spectral_schema_payload,
        "spectral_library_preflight": spectral_preflight_payload,
        "spectral_library_config": asdict(plot_config) if spectral_schema else None,
        "make_summary_plots": make_summary_plots,
        "make_full_spectral_reports": make_full_spectral_reports,
        "analysis_engine": (
            "streaming_mergeable_sufficient_statistics"
            if resolved_input_mode == "flightline_outputs"
            and not materialize_observations
            else "virtual_or_explicit_observations"
        ),
        "analysis_profile": asdict(analysis_profile),
        "selected_translation_pairs": [asdict(item) for item in selected_pairs],
        "on_invalid": on_invalid,
    }
    con, temporary_database = create_bulk_database(
        paths,
        source_files,
        flightlines,
        exclusions,
        sufficient_statistics=(
            paths.sufficient_statistics
            if resolved_input_mode == "flightline_outputs"
            and not preflight_only
            and not materialize_observations
            else None
        ),
        metadata=metadata,
        materialize_observations=materialize_observations,
        row_group_size=row_group_size,
        memory_limit=memory_limit,
        threads=threads,
        temp_directory=temporary_dir,
    )
    translation: dict[str, Any] = {"pair_count": 0, "candidate_count": 0}
    loso: dict[str, Any] = {"result_count": 0}
    spectral_library_result: dict[str, Any] | None = None
    try:
        census = run_dataset_census(
            con,
            paths,
            analysis_run_id=analysis_run_id,
            reuse_existing=not force,
        )
        eligible_count = sum(
            item.status == "accepted" and item.translation_eligible
            for item in flightlines
        )
        if not preflight_only and require_translation_pairs and eligible_count == 0:
            raise ValueError(
                "No accepted canonical flightline contains a compatible "
                "requested sensor translation pair. The catalog and census "
                f"were written to {paths.output_dir}."
            )
        if (
            not preflight_only
            and resolved_input_mode == "flightline_outputs"
            and not materialize_observations
        ):
            translation, loso = run_streaming_translation_analyses(
                con,
                paths,
                analysis_run_id=analysis_run_id,
                statistics_rows=statistics_rows,
                flightlines=flightlines,
                minimum_reflectance=minimum_reflectance,
                chunk_size=extraction_chunk_size,
                translation_pairs=selected_pairs,
                reuse_existing=not force,
            )
        elif not preflight_only:
            translation = run_sensor_translation(
                con,
                paths,
                analysis_run_id=analysis_run_id,
                minimum_reflectance=minimum_reflectance,
                translation_pairs=selected_pairs,
                reuse_existing=not force,
            )
            loso = run_leave_one_site_out(
                con,
                paths,
                analysis_run_id=analysis_run_id,
                minimum_reflectance=minimum_reflectance,
                translation_pairs=selected_pairs,
                reuse_existing=not force,
            )
        if not preflight_only and spectral_schema is not None:
            spectral_library_result = run_spectral_library_analysis(
                con,
                paths,
                spectral_library=spectral_schema.source,
                analysis_run_id=analysis_run_id,
                config=plot_config,
                make_summary_plots=make_summary_plots,
                make_full_spectral_reports=make_full_spectral_reports,
            )
        finalize_bulk_database(con, temporary_database, paths.database)
    except Exception:
        try:
            con.close()
        except Exception:
            pass
        raise

    counts = {
        "candidate_source_directories": census["summary"][
            "candidate_source_directories"
        ],
        "accepted_flightlines": len(accepted_flightlines),
        "duplicate_candidates": len(duplicate_flightlines),
        "rejected_flightlines": len(rejected_flightlines),
        "accepted_rows": accepted_rows,
        "translation_pairs": int(translation["pair_count"]),
        "candidate_coefficients": int(translation["candidate_count"]),
        "leave_one_site_out_results": int(loso["result_count"]),
        "spectral_library_species": int(
            (spectral_library_result or {}).get("species_count", 0)
        ),
    }
    complete_manifest = {
        **building_manifest,
        "status": "complete",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "outputs": {
            "flightlines": _relative_output(paths, paths.flightlines),
            "source_files": _relative_output(paths, paths.source_files),
            "source_products": _relative_output(paths, paths.source_products),
            "exclusions": _relative_output(paths, paths.exclusions),
            "exclusions_json": _relative_output(paths, paths.exclusions_json),
            "exclusions_csv": _relative_output(paths, paths.exclusions_csv),
            "cache": _relative_output(paths, paths.cache_dir),
            "sufficient_statistics": (
                _relative_output(paths, paths.sufficient_statistics)
                if paths.sufficient_statistics.is_file()
                else None
            ),
            "diagnostic_sample": (
                _relative_output(paths, paths.diagnostic_sample)
                if diagnostic_sample_size and paths.diagnostic_sample.is_file()
                else None
            ),
            "duplicates": _relative_output(paths, paths.duplicates),
            "rejected_sources": _relative_output(paths, paths.rejected_sources),
            "database": _relative_output(paths, paths.database),
            "materialized_observations": (
                _relative_output(paths, paths.observations)
                if materialize_observations
                else None
            ),
            "dataset_census": _relative_output(
                paths,
                paths.analyses_dir / "dataset_census" / "dataset_census.json",
            ),
            "candidate_coefficients": (
                None
                if preflight_only
                else _relative_output(paths, paths.coefficients_parquet)
            ),
            "leave_one_site_out": (
                None
                if preflight_only
                else _relative_output(
                    paths,
                    paths.analyses_dir
                    / "leave_one_site_out"
                    / "leave_one_site_out.parquet",
                )
            ),
            "spectral_library": (
                _relative_output(
                    paths,
                    SpectralLibraryPaths.from_bulk_paths(paths).metadata,
                )
                if spectral_library_result is not None
                else None
            ),
        },
    }
    write_json_atomic(paths.manifest, complete_manifest)
    if on_invalid == "error" and (
        rejected_flightlines or duplicate_flightlines
    ):
        raise ValueError(
            "Bulk validation excluded "
            f"{len(rejected_flightlines) + len(duplicate_flightlines)} "
            "flightline candidate(s); see "
            f"{paths.exclusions}"
        )
    LOGGER.info(
        "Bulk population analysis completed: %d accepted flightlines, "
        "%d duplicate candidates, %d rejected records, %d rows",
        len(accepted_flightlines),
        len(duplicate_flightlines),
        len(rejected_flightlines),
        accepted_rows,
    )
    return _result(
        paths,
        input_path=root,
        status="created",
        accepted_flightline_count=len(accepted_flightlines),
        duplicate_count=len(duplicate_flightlines),
        rejected_count=len(rejected_flightlines),
        row_count=accepted_rows,
        translation_pair_count=int(translation["pair_count"]),
        materialize_observations=materialize_observations,
        preflight_only=preflight_only,
        input_mode=resolved_input_mode,
        analysis_profile=analysis_profile,
        translation_pairs=selected_pairs,
        diagnostic_sample_size=diagnostic_sample_size,
        spectral_library_schema=spectral_schema_payload,
        spectral_library_preflight=spectral_preflight_payload,
        spectral_library_requested=spectral_schema is not None,
    )


__all__ = [
    "BULK_SCHEMA_VERSION",
    "BulkAnalysisPaths",
    "BulkInputKind",
    "BulkInputMode",
    "BulkSource",
    "FlightlineRecord",
    "SourceFileRecord",
    "discover_bulk_sources",
    "run_bulk_pipeline",
]
