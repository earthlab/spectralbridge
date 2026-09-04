"""Orchestration for the independent production bulk-analysis pipeline.

Discovery, the virtual DuckDB dataset, provenance, and scientific analyses
live under the dedicated spectralbridge.bulk package.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq

from spectralbridge.bulk.analyses import (
    run_dataset_census,
    run_leave_one_site_out,
    run_sensor_translation,
)
from spectralbridge.bulk.catalog import (
    build_bulk_catalog,
    catalog_signature_records,
    discover_bulk_sources,
)
from spectralbridge.bulk.dataset import create_bulk_database, finalize_bulk_database
from spectralbridge.bulk.models import (
    BULK_SCHEMA_VERSION,
    BulkAnalysisPaths,
    BulkInputKind,
    BulkSource,
    FlightlineRecord,
    SourceFileRecord,
)
from spectralbridge.bulk.provenance import signature_sha256, write_json_atomic


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
    minimum_reflectance: float,
    materialize_observations: bool,
    row_group_size: int,
    preflight_only: bool,
    require_translation_pairs: bool,
    source_files: list[SourceFileRecord],
    flightlines: list[FlightlineRecord],
) -> dict[str, Any]:
    return {
        "bulk_schema_version": BULK_SCHEMA_VERSION,
        "input_path": root.as_posix(),
        "output_dir": paths.output_dir.as_posix(),
        "input_kind": input_kind,
        "minimum_reflectance": minimum_reflectance,
        "materialize_observations": materialize_observations,
        "row_group_size": row_group_size if materialize_observations else None,
        "preflight_only": preflight_only,
        "require_translation_pairs": require_translation_pairs,
        "catalog": catalog_signature_records(source_files, flightlines),
    }


def _relative_output(paths: BulkAnalysisPaths, path: Path) -> str:
    return path.relative_to(paths.output_dir).as_posix()


def _outputs_are_valid(
    paths: BulkAnalysisPaths,
    *,
    materialize_observations: bool,
    preflight_only: bool,
) -> bool:
    required = [
        paths.flightlines,
        paths.source_files,
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
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    try:
        for parquet in (
            paths.flightlines,
            paths.source_files,
            paths.duplicates,
            paths.rejected_sources,
        ):
            pq.read_schema(parquet)
        with duckdb.connect(str(paths.database), read_only=True) as con:
            con.execute("SELECT * FROM flightlines LIMIT 0").fetchall()
            con.execute("SELECT * FROM bulk_sources LIMIT 0").fetchall()
            con.execute("SELECT * FROM bulk_observations LIMIT 0").fetchall()
            con.execute("SELECT * FROM dataset_census_summary LIMIT 0").fetchall()
            if not preflight_only:
                con.execute(
                    "SELECT * FROM candidate_translation_coefficients LIMIT 0"
                ).fetchall()
                con.execute(
                    "SELECT * FROM translation_leave_one_site_out LIMIT 0"
                ).fetchall()
    except Exception:
        return False
    return True


def _result(
    paths: BulkAnalysisPaths,
    *,
    status: str,
    accepted_flightline_count: int,
    duplicate_count: int,
    rejected_count: int,
    row_count: int,
    translation_pair_count: int,
    materialize_observations: bool,
    preflight_only: bool,
) -> dict[str, Any]:
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
        "materialized_observations": (
            str(paths.observations) if materialize_observations else None
        ),
        "observations": str(paths.observations) if materialize_observations else None,
        "flightlines": str(paths.flightlines),
        "source_files": str(paths.source_files),
        "source_catalog": str(paths.source_files),
        "duplicates": str(paths.duplicates),
        "rejected_sources": str(paths.rejected_sources),
        "coefficients_parquet": (
            None if preflight_only else str(paths.coefficients_parquet)
        ),
        "coefficients_json": None if preflight_only else str(paths.coefficients_json),
        "database": str(paths.database),
        "manifest": str(paths.manifest),
    }


def run_bulk_pipeline(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    input_kind: BulkInputKind = "full",
    minimum_reflectance: float = 0.0,
    require_translation_pairs: bool = True,
    materialize_observations: bool = False,
    row_group_size: int = 50_000,
    memory_limit: str | None = None,
    threads: int | None = None,
    temp_directory: str | Path | None = None,
    preflight_only: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Catalog completed flightlines and run population analyses.

    The source tree is treated as read only. Canonical identity is recovered
    from SpectralBridge product filenames, never arbitrary outer run-folder
    names. Duplicate canonical flightline IDs in different source directories
    are cataloged and excluded from analysis.

    By default, bulk_observations is a DuckDB view over the accepted source
    Parquets. Set materialize_observations only when a portable super-Parquet
    is explicitly required and sufficient disk is available.
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
    minimum_reflectance = float(minimum_reflectance)
    if not math.isfinite(minimum_reflectance):
        raise ValueError("minimum_reflectance must be finite")
    if row_group_size < 1:
        raise ValueError("row_group_size must be at least 1")
    if threads is not None and threads < 1:
        raise ValueError("threads must be at least 1")

    paths = BulkAnalysisPaths(resolved_output)
    _prepare_output_directory(paths)
    source_files, flightlines = build_bulk_catalog(
        root,
        input_kind=input_kind,
        exclude_dir=resolved_output,
    )
    signature = _input_signature(
        root=root,
        paths=paths,
        input_kind=input_kind,
        minimum_reflectance=minimum_reflectance,
        materialize_observations=materialize_observations,
        row_group_size=row_group_size,
        preflight_only=preflight_only,
        require_translation_pairs=require_translation_pairs,
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
            )
        ):
            counts = previous["counts"]
            return _result(
                paths,
                status="reused",
                accepted_flightline_count=int(counts["accepted_flightlines"]),
                duplicate_count=int(counts["duplicate_candidates"]),
                rejected_count=int(counts["rejected_flightlines"]),
                row_count=int(counts["accepted_rows"]),
                translation_pair_count=int(counts["translation_pairs"]),
                materialize_observations=materialize_observations,
                preflight_only=preflight_only,
            )

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
    accepted_rows = sum(int(item.row_count or 0) for item in accepted_sources)
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
    }
    write_json_atomic(paths.manifest, building_manifest)

    metadata = {
        "schema_version": BULK_SCHEMA_VERSION,
        "analysis_run_id": analysis_run_id,
        "input_path": root.as_posix(),
        "input_kind": input_kind,
        "source_data_policy": "read_only",
        "identity_policy": "canonical_product_filename_not_outer_folder",
        "duplicate_policy": "exclude_all_duplicate_canonical_id_candidates",
        "materialize_observations": materialize_observations,
        "minimum_reflectance": minimum_reflectance,
    }
    con, temporary_database = create_bulk_database(
        paths,
        source_files,
        flightlines,
        metadata=metadata,
        materialize_observations=materialize_observations,
        row_group_size=row_group_size,
        memory_limit=memory_limit,
        threads=threads,
        temp_directory=temporary_dir,
    )
    translation: dict[str, Any] = {"pair_count": 0, "candidate_count": 0}
    loso: dict[str, Any] = {"result_count": 0}
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
                "synthetic MicaSense/Landsat band pair. The catalog and census "
                f"were written to {paths.output_dir}."
            )
        if not preflight_only:
            translation = run_sensor_translation(
                con,
                paths,
                analysis_run_id=analysis_run_id,
                minimum_reflectance=minimum_reflectance,
                reuse_existing=not force,
            )
            loso = run_leave_one_site_out(
                con,
                paths,
                analysis_run_id=analysis_run_id,
                minimum_reflectance=minimum_reflectance,
                reuse_existing=not force,
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
    }
    complete_manifest = {
        **building_manifest,
        "status": "complete",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "outputs": {
            "flightlines": _relative_output(paths, paths.flightlines),
            "source_files": _relative_output(paths, paths.source_files),
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
        },
    }
    write_json_atomic(paths.manifest, complete_manifest)
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
        status="created",
        accepted_flightline_count=len(accepted_flightlines),
        duplicate_count=len(duplicate_flightlines),
        rejected_count=len(rejected_flightlines),
        row_count=accepted_rows,
        translation_pair_count=int(translation["pair_count"]),
        materialize_observations=materialize_observations,
        preflight_only=preflight_only,
    )


__all__ = [
    "BULK_SCHEMA_VERSION",
    "BulkAnalysisPaths",
    "BulkInputKind",
    "BulkSource",
    "FlightlineRecord",
    "SourceFileRecord",
    "discover_bulk_sources",
    "run_bulk_pipeline",
]
