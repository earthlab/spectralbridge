"""Discovery and compact extraction for completed normal-pipeline outputs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import traceback
from typing import Any, Iterable

import duckdb
import pyarrow.parquet as pq

from spectralbridge.file_types import NEONReflectanceFile
from spectralbridge.sensor_pairs import MICASENSE_LANDSAT_PAIRS

from .dataset import quote_identifier, quote_path
from .models import BulkAnalysisPaths, FlightlineRecord, SourceFileRecord
from .provenance import canonical_json, signature_sha256, write_json_atomic, write_text_atomic


LOGGER = logging.getLogger(__name__)
EXTRACTION_SCHEMA_VERSION = 1

_SENSOR_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "MicaSense_to-match_OLI_and_OLI-2",
        ("micasense_to_match_oli_oli2", "micasense-to-match_oli_and_oli-2"),
    ),
    (
        "MicaSense_to-match_TM_and_ETM+",
        ("micasense_to_match_tm_etm+", "micasense-to-match_tm_and_etm+"),
    ),
    ("Landsat_9_OLI-2", ("landsat_oli2", "landsat_9_oli-2")),
    ("Landsat_8_OLI", ("landsat_oli", "landsat_8_oli")),
    ("Landsat_7_ETM+", ("landsat_etm+", "landsat_7_etm+")),
    ("Landsat_5_TM", ("landsat_tm", "landsat_5_tm")),
)


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _canonical_identity(directory: Path) -> dict[str, str]:
    parsed = NEONReflectanceFile.from_filename(f"{directory.name}.h5")
    if not parsed.site or not parsed.date:
        raise ValueError(f"Incomplete canonical NEON identity: {directory.name}")
    acquisition_date = (
        f"{parsed.date[:4]}-{parsed.date[4:6]}-{parsed.date[6:8]}"
    )
    return {
        "canonical_flightline_id": directory.name,
        "site": parsed.site,
        "acquisition_date": acquisition_date,
    }


def find_canonical_flightline_directories(
    input_path: str | Path,
    *,
    exclude_dir: str | Path | None = None,
) -> list[Path]:
    """Find canonical inner flightline directories, ignoring outer names."""

    root = Path(input_path).expanduser().resolve()
    if not root.is_dir():
        return []
    excluded = Path(exclude_dir).expanduser().resolve() if exclude_dir else None
    candidates = [root, *(path for path in root.rglob("*") if path.is_dir())]
    found: list[Path] = []
    for directory in candidates:
        if excluded is not None and _path_is_within(directory, excluded):
            continue
        try:
            _canonical_identity(directory)
        except ValueError:
            continue
        found.append(directory)
    return sorted(set(found))


def _sensor_from_name(path: Path) -> str | None:
    lowered = path.name.lower()
    if path.suffix.lower() != ".img" or "_undarkened_envi" in lowered:
        return None
    for sensor, patterns in _SENSOR_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            return sensor
    return None


def _small_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _raster_metadata(img: Path, hdr: Path) -> dict[str, Any]:
    import rasterio

    if not hdr.is_file() or hdr.stat().st_size == 0:
        raise ValueError(f"missing or empty ENVI header: {hdr.name}")
    with rasterio.open(img) as dataset:
        if dataset.width < 1 or dataset.height < 1 or dataset.count < 1:
            raise ValueError(f"invalid ENVI dimensions: {img.name}")
        metadata = {
            "rows": int(dataset.height),
            "columns": int(dataset.width),
            "bands": int(dataset.count),
            "crs": dataset.crs.to_string() if dataset.crs else None,
            "transform": tuple(float(value) for value in dataset.transform),
            "nodata": dataset.nodata,
        }
    img_stat = img.stat()
    hdr_stat = hdr.stat()
    signature = {
        "image_path": img.resolve().as_posix(),
        "image_size_bytes": int(img_stat.st_size),
        "image_modified_time_ns": int(img_stat.st_mtime_ns),
        "header_path": hdr.resolve().as_posix(),
        "header_size_bytes": int(hdr_stat.st_size),
        "header_modified_time_ns": int(hdr_stat.st_mtime_ns),
        "header_sha256": _small_file_sha256(hdr),
        "raster_metadata": metadata,
    }
    return {**metadata, **signature, "source_signature_sha256": signature_sha256(signature)}


def _qa_inventory(directory: Path) -> tuple[list[str], str, dict[str, dict[str, Any]]]:
    qa_files = sorted(
        path
        for path in directory.rglob("*.json")
        if "qa" in path.relative_to(directory).as_posix().lower()
        and path.stat().st_size <= 5 * 1024 * 1024
    )
    details: dict[str, dict[str, Any]] = {}
    for path in qa_files:
        relative = path.relative_to(directory).as_posix()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            details[relative] = {"status": "unreadable", "metrics": {}}
            continue
        values: list[str] = []
        metrics: dict[str, int | float] = {}
        stack: list[tuple[str, Any]] = [("", payload)]
        while stack:
            prefix, value = stack.pop()
            if isinstance(value, dict):
                for key, item in value.items():
                    field = f"{prefix}.{key}".strip(".")
                    if key.lower() in {"status", "overall_status", "qa_status"}:
                        values.append(str(item).lower())
                    elif isinstance(item, (dict, list)):
                        stack.append((field, item))
                    elif (
                        isinstance(item, (int, float))
                        and not isinstance(item, bool)
                        and any(
                            token in key.lower()
                            for token in ("nodata", "no_data", "invalid", "fraction")
                        )
                        and len(metrics) < 100
                    ):
                        metrics[field] = item
            elif isinstance(value, list):
                stack.extend((prefix, item) for item in value[:200])
        joined = " ".join(values)
        status = (
            "fail"
            if "fail" in joined
            else "warn"
            if "warn" in joined
            else "pass"
            if values
            else "unknown"
        )
        details[relative] = {"status": status, "metrics": metrics}
    observed_statuses = {item["status"] for item in details.values()}
    overall = (
        "missing"
        if not qa_files
        else "fail"
        if "fail" in observed_statuses
        else "warn"
        if {"warn", "unreadable", "unknown"} & observed_statuses
        else "pass"
    )
    return [path.relative_to(directory).as_posix() for path in qa_files], overall, details


def _translation_eligibility(targets: dict[str, dict[str, Any]]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for micasense, landsat_sensors in MICASENSE_LANDSAT_PAIRS.items():
        for landsat in landsat_sensors:
            result[f"{micasense}=>{landsat}"] = (
                micasense in targets and landsat in targets
            )
    return result


def _source_record(
    *,
    root: Path,
    directory: Path,
    canonical_id: str,
    site: str,
    acquisition_date: str,
    candidate_id: str,
    path: Path,
    role: str,
    sensor: str | None,
    status: str,
    reason: str | None,
    metadata: dict[str, Any] | None,
    qa_status: str,
) -> SourceFileRecord:
    relative = path.relative_to(root).as_posix()
    stat = path.stat()
    return SourceFileRecord(
        source_id=hashlib.sha256(relative.encode("utf-8")).hexdigest()[:20],
        candidate_id=candidate_id,
        canonical_flightline_id=canonical_id,
        identity_source="canonical_flightline_directory",
        site=site,
        acquisition_date=acquisition_date,
        source_directory=directory.as_posix(),
        source_path=path.as_posix(),
        relative_path=relative,
        input_kind="flightline_output",
        status=status,
        reason=reason,
        row_count=None,
        column_count=(int(metadata["bands"]) if metadata else None),
        size_bytes=int(stat.st_size),
        modified_time_ns=int(stat.st_mtime_ns),
        schema_sha256=None,
        available_sensors_json=canonical_json([sensor] if sensor else []),
        translation_eligible=False,
        product_role=role,
        sensor_name=sensor,
        header_path=str(path.with_suffix(".hdr")),
        dimensions_json=canonical_json(
            {
                key: metadata[key]
                for key in ("rows", "columns", "bands", "crs", "transform", "nodata")
            }
            if metadata
            else {}
        ),
        source_signature_sha256=(
            str(metadata["source_signature_sha256"]) if metadata else None
        ),
        qa_status=qa_status,
    )


def discover_completed_flightlines(
    input_path: str | Path,
    *,
    exclude_dir: str | Path | None = None,
) -> tuple[list[SourceFileRecord], list[FlightlineRecord]]:
    """Inventory completed flightline folders without reading raster pixels."""

    root = Path(input_path).expanduser().resolve()
    directories = find_canonical_flightline_directories(root, exclude_dir=exclude_dir)
    sources: list[SourceFileRecord] = []
    flightlines: list[FlightlineRecord] = []
    for directory in directories:
        identity = _canonical_identity(directory)
        canonical_id = identity["canonical_flightline_id"]
        candidate_id = hashlib.sha256(
            f"{directory.as_posix()}::{canonical_id}".encode("utf-8")
        ).hexdigest()[:20]
        qa_files, qa_status, stage_statuses = _qa_inventory(directory)
        files = sorted(path for path in directory.rglob("*") if path.is_file())
        source_bytes = sum(int(path.stat().st_size) for path in files)
        metadata_files = [
            path.relative_to(directory).as_posix()
            for path in files
            if path.suffix.lower() in {".json", ".csv", ".toml", ".yaml", ".yml"}
        ]

        raw_candidates = [
            path
            for path in files
            if path.suffix.lower() == ".img"
            and path.name.lower().endswith("reflectance_envi.img")
            and "brdfandtopo_corrected" not in path.name.lower()
            and "_resampled_" not in path.name.lower()
        ]
        for raw_img in raw_candidates:
            try:
                raw_metadata = _raster_metadata(raw_img, raw_img.with_suffix(".hdr"))
            except Exception as exc:
                raw_reason = f"invalid raw ENVI product: {type(exc).__name__}: {exc}"
                raw_metadata = None
            else:
                raw_reason = None
            raw_record = _source_record(
                root=root,
                directory=directory,
                canonical_id=canonical_id,
                site=identity["site"],
                acquisition_date=identity["acquisition_date"],
                candidate_id=candidate_id,
                path=raw_img,
                role="raw_envi",
                sensor=None,
                status="available" if raw_metadata else "rejected",
                reason=raw_reason,
                metadata=raw_metadata,
                qa_status=qa_status,
            )
            sources.append(raw_record)

        corrected_candidates = [
            path
            for path in files
            if path.suffix.lower() == ".img"
            and "brdfandtopo_corrected_envi" in path.name.lower()
        ]
        corrected: dict[str, Any] = {}
        reasons: list[str] = []
        if len(corrected_candidates) != 1:
            reasons.append(
                "missing corrected ENVI product"
                if not corrected_candidates
                else "multiple corrected ENVI products"
            )
        else:
            corrected_img = corrected_candidates[0]
            try:
                corrected = _raster_metadata(corrected_img, corrected_img.with_suffix(".hdr"))
            except Exception as exc:
                reasons.append(f"invalid corrected ENVI product: {type(exc).__name__}: {exc}")
                sources.append(
                    _source_record(
                        root=root,
                        directory=directory,
                        canonical_id=canonical_id,
                        site=identity["site"],
                        acquisition_date=identity["acquisition_date"],
                        candidate_id=candidate_id,
                        path=corrected_img,
                        role="corrected_envi",
                        sensor=None,
                        status="rejected",
                        reason=reasons[-1],
                        metadata=None,
                        qa_status=qa_status,
                    )
                )
            else:
                record = _source_record(
                    root=root,
                    directory=directory,
                    canonical_id=canonical_id,
                    site=identity["site"],
                    acquisition_date=identity["acquisition_date"],
                    candidate_id=candidate_id,
                    path=corrected_img,
                    role="corrected_envi",
                    sensor=None,
                    status="available",
                    reason=None,
                    metadata=corrected,
                    qa_status=qa_status,
                )
                sources.append(record)

        by_sensor: dict[str, list[Path]] = defaultdict(list)
        for path in files:
            sensor = _sensor_from_name(path)
            if sensor:
                by_sensor[sensor].append(path)
        targets: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        for sensor, candidates in sorted(by_sensor.items()):
            if len(candidates) != 1:
                missing.append(f"ambiguous target product: {sensor}")
                continue
            img = candidates[0]
            try:
                target = _raster_metadata(img, img.with_suffix(".hdr"))
            except Exception as exc:
                reason = f"invalid target product {sensor}: {type(exc).__name__}: {exc}"
                missing.append(reason)
                sources.append(
                    _source_record(
                        root=root,
                        directory=directory,
                        canonical_id=canonical_id,
                        site=identity["site"],
                        acquisition_date=identity["acquisition_date"],
                        candidate_id=candidate_id,
                        path=img,
                        role="target_sensor_envi",
                        sensor=sensor,
                        status="rejected",
                        reason=reason,
                        metadata=None,
                        qa_status=qa_status,
                    )
                )
                continue
            targets[sensor] = {"image": img.as_posix(), "header": img.with_suffix(".hdr").as_posix(), **target}
            record = _source_record(
                root=root,
                directory=directory,
                canonical_id=canonical_id,
                site=identity["site"],
                acquisition_date=identity["acquisition_date"],
                candidate_id=candidate_id,
                path=img,
                role="target_sensor_envi",
                sensor=sensor,
                status="available",
                reason=None,
                metadata=target,
                qa_status=qa_status,
            )
            sources.append(record)

        if corrected:
            alignment_keys = ("rows", "columns", "crs", "transform")
            for sensor, target in list(targets.items()):
                if any(target[key] != corrected[key] for key in alignment_keys):
                    alignment_reason = (
                        "target product is not spatially aligned with corrected ENVI: "
                        f"{sensor}"
                    )
                    missing.append(alignment_reason)
                    sources = [
                        replace(record, status="rejected", reason=alignment_reason)
                        if record.candidate_id == candidate_id
                        and record.sensor_name == sensor
                        else record
                        for record in sources
                    ]
                    del targets[sensor]

        eligibility = _translation_eligibility(targets)
        translation_eligible = any(eligibility.values())
        if not translation_eligible:
            reasons.append("no complete wavelength-matched MicaSense/Landsat target pair")
        selected_sensors = sorted(
            {
                sensor
                for pair, eligible in eligibility.items()
                if eligible
                for sensor in pair.split("=>")
            }
        )
        representative = next(
            (targets[sensor] for sensor in selected_sensors if sensor in targets),
            None,
        )
        pixel_count = (
            int(representative["rows"]) * int(representative["columns"])
            if representative
            else 0
        )
        selected_band_count = sum(int(targets[sensor]["bands"]) for sensor in selected_sensors)
        estimated_cache_bytes = pixel_count * (24 + 4 * selected_band_count)
        stages = ["brdf_topographic_correction", "spectral_convolution"]
        if qa_files:
            stages.append("qa")
        if raw_candidates:
            stages.append("envi_export")
        provenance = {
            "input_root": root.as_posix(),
            "source_directory": directory.as_posix(),
            "outer_storage_path": directory.parent.as_posix(),
            "outer_directory_names_are_scientific_identifiers": False,
            "identity_authority": "canonical_flightline_directory",
            "source_signature_policy": "path_size_mtime_header_sha256_and_envi_metadata",
        }
        flightlines.append(
            FlightlineRecord(
                candidate_id=candidate_id,
                canonical_flightline_id=canonical_id,
                identity_source="canonical_flightline_directory",
                site=identity["site"],
                acquisition_date=identity["acquisition_date"],
                acquisition_year=int(identity["acquisition_date"][:4]),
                source_directory=directory.as_posix(),
                canonical_merged_parquet=None,
                polygon_merged_parquet=None,
                selected_source_ids_json=canonical_json(
                    [
                        source.source_id
                        for source in sources
                        if source.candidate_id == candidate_id
                        and source.status == "available"
                    ]
                ),
                selected_source_paths_json=canonical_json(
                    [targets[sensor]["image"] for sensor in selected_sensors]
                ),
                qa_products_json=canonical_json(qa_files),
                metadata_products_json=canonical_json(metadata_files),
                available_sensors_json=canonical_json(sorted(targets)),
                processing_stages_json=canonical_json(sorted(stages)),
                row_count=None,
                size_bytes=sum(int(targets[sensor]["image_size_bytes"]) for sensor in selected_sensors),
                source_directory_size_bytes=source_bytes,
                schema_fingerprints_json="[]",
                brightness_state_json="{}",
                correction_state_json=canonical_json({"corrected_product_present": bool(corrected)}),
                translation_eligible=translation_eligible,
                status="rejected" if reasons else "accepted",
                rejection_reason="; ".join(reasons) or None,
                duplicate_status="unique",
                duplicate_candidate_count=1,
                source_provenance_json=canonical_json(provenance),
                input_mode="flightline_outputs",
                corrected_product_json=canonical_json(corrected),
                target_products_json=canonical_json(targets),
                qa_status=qa_status,
                stage_qa_status_json=canonical_json(stage_statuses),
                missing_products_json=canonical_json(missing),
                analysis_eligibility_json=canonical_json(eligibility),
                estimated_cache_bytes=estimated_cache_bytes,
                cache_observations=None,
                extraction_status="pending" if not reasons else "not_eligible",
            )
        )

    by_id: dict[str, list[int]] = defaultdict(list)
    for index, flightline in enumerate(flightlines):
        if flightline.status == "accepted" and flightline.canonical_flightline_id:
            by_id[flightline.canonical_flightline_id].append(index)
    for indices in by_id.values():
        if len({flightlines[index].source_directory for index in indices}) < 2:
            continue
        for index in indices:
            flightline = flightlines[index]
            flightlines[index] = replace(
                flightline,
                status="duplicate_excluded",
                rejection_reason="canonical flightline ID occurs in multiple source directories; all candidates are excluded",
                duplicate_status="duplicate_canonical_id",
                duplicate_candidate_count=len(indices),
                extraction_status="not_eligible",
            )
    status_by_candidate = {item.candidate_id: item.status for item in flightlines}
    final_sources = [
        replace(
            source,
            status=(
                "duplicate_excluded"
                if status_by_candidate.get(source.candidate_id) == "duplicate_excluded"
                else source.status
            ),
        )
        for source in sources
    ]
    return sorted(final_sources, key=lambda item: item.relative_path), sorted(
        flightlines,
        key=lambda item: (item.canonical_flightline_id or "", item.source_directory),
    )


def _schema_fingerprint(path: Path) -> str:
    schema = pq.read_schema(path)
    fields = [(field.name, str(field.type), field.nullable) for field in schema]
    return signature_sha256(fields)


def _extract_sensor(
    sensor: str,
    product: dict[str, Any],
    output: Path,
    *,
    chunk_size: int,
) -> Path:
    from spectralbridge.parquet_export import (
        _write_parquet_chunks,
        read_envi_in_chunks,
    )

    chunks = read_envi_in_chunks(
        Path(product["image"]),
        Path(product["header"]),
        Path(product["image"]).name,
        chunk_size=chunk_size,
    )

    def logged_chunks() -> Iterable[Any]:
        for index, chunk in enumerate(chunks, start=1):
            LOGGER.info("Bulk extraction %s chunk %d (%d rows)", sensor, index, len(chunk))
            yield chunk

    context = getattr(chunks, "context", None)
    _write_parquet_chunks(
        output,
        logged_chunks(),
        "bulk_target",
        context=context,
        row_group_size=chunk_size,
    )
    return output


def _merge_sensor_caches(sensor_files: dict[str, Path], output: Path) -> Path:
    aliases = {sensor: f"s{index}" for index, sensor in enumerate(sorted(sensor_files))}
    select = ["pixel_id"]
    metadata_columns = ("row", "col", "x", "y", "lon", "lat", "epsg", "crs")
    for column in metadata_columns:
        expressions = ", ".join(
            f"{alias}.{quote_identifier(column)}" for alias in aliases.values()
        )
        select.append(f"COALESCE({expressions}) AS {quote_identifier(column)}")
    for sensor in sorted(sensor_files):
        alias = aliases[sensor]
        schema = pq.read_schema(sensor_files[sensor])
        spectral = [name for name in schema.names if re.search(r"_b\d+_wl\d+nm$", name)]
        for index, column in enumerate(spectral, start=1):
            select.append(
                f"{alias}.{quote_identifier(column)} AS "
                f"{quote_identifier(f'{sensor}_band_{index}')}"
            )
    first_sensor = sorted(sensor_files)[0]
    first_alias = aliases[first_sensor]
    from_sql = (
        f"read_parquet('{quote_path(sensor_files[first_sensor])}') {first_alias}"
    )
    for sensor in sorted(sensor_files)[1:]:
        alias = aliases[sensor]
        from_sql += (
            f" FULL OUTER JOIN read_parquet('{quote_path(sensor_files[sensor])}') "
            f"{alias} USING (pixel_id)"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    with duckdb.connect() as con:
        con.execute(
            f"COPY (SELECT {', '.join(select)} FROM {from_sql} ORDER BY pixel_id) "
            f"TO '{quote_path(temporary)}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    pq.read_schema(temporary)
    temporary.replace(output)
    return output


def extract_flightline_cache(
    flightline: FlightlineRecord,
    paths: BulkAnalysisPaths,
    *,
    analysis_run_id: str,
    chunk_size: int,
    force: bool = False,
) -> tuple[SourceFileRecord, FlightlineRecord]:
    """Create or reuse one compact observation cache from target ENVI products."""

    if not flightline.canonical_flightline_id:
        raise ValueError("Cannot extract a flightline without canonical identity")
    targets = json.loads(flightline.target_products_json)
    eligibility = json.loads(flightline.analysis_eligibility_json)
    selected = sorted(
        {
            sensor
            for pair, eligible in eligibility.items()
            if eligible
            for sensor in pair.split("=>")
        }
    )
    if not selected:
        raise ValueError("No eligible target-sensor pair is available")
    cache_dir = paths.cache_dir / flightline.canonical_flightline_id
    observations = cache_dir / "observations.parquet"
    metadata_path = cache_dir / "extraction_metadata.json"
    status_path = cache_dir / "status.json"
    signature_payload = {
        "schema_version": EXTRACTION_SCHEMA_VERSION,
        "canonical_flightline_id": flightline.canonical_flightline_id,
        "selected_sensors": selected,
        "source_signatures": {
            sensor: targets[sensor]["source_signature_sha256"] for sensor in selected
        },
        "chunk_size": chunk_size,
    }
    extraction_signature = signature_sha256(signature_payload)
    if not force and observations.is_file() and metadata_path.is_file():
        try:
            previous = json.loads(metadata_path.read_text(encoding="utf-8"))
            reusable = (
                previous.get("extraction_signature_sha256") == extraction_signature
                and pq.read_schema(observations) is not None
            )
        except Exception:
            reusable = False
        if reusable:
            row_count = int(pq.ParquetFile(observations).metadata.num_rows)
            source = _cache_source_record(flightline, observations, row_count)
            return source, replace(
                flightline,
                row_count=row_count,
                size_bytes=int(observations.stat().st_size),
                schema_fingerprints_json=canonical_json([source.schema_sha256]),
                cache_observations=observations.as_posix(),
                extraction_status="reused",
            )

    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        for existing in cache_dir.glob("*.parquet"):
            existing.unlink()
        sensor_files: dict[str, Path] = {}
        for sensor in selected:
            output = cache_dir / (re.sub(r"[^A-Za-z0-9]+", "_", sensor).strip("_") + ".parquet")
            if output.exists():
                output.unlink()
            LOGGER.info("Extracting %s for %s", sensor, flightline.canonical_flightline_id)
            sensor_files[sensor] = _extract_sensor(
                sensor, targets[sensor], output, chunk_size=chunk_size
            )
        _merge_sensor_caches(sensor_files, observations)
        row_count = int(pq.ParquetFile(observations).metadata.num_rows)
        metadata = {
            **signature_payload,
            "extraction_signature_sha256": extraction_signature,
            "analysis_run_id": analysis_run_id,
            "source_directory": flightline.source_directory,
            "source_products": {sensor: targets[sensor] for sensor in selected},
            "spectralbridge_version": _spectralbridge_version(),
            "git_commit": os.environ.get("GITHUB_SHA"),
            "validity_filters": ["finite", "not ENVI nodata"],
            "output": observations.as_posix(),
            "row_count": row_count,
            "output_schema_sha256": _schema_fingerprint(observations),
        }
        write_json_atomic(metadata_path, metadata)
        write_json_atomic(
            status_path,
            {"status": "success", "extraction_signature_sha256": extraction_signature},
        )
    except Exception as exc:
        write_json_atomic(
            status_path,
            {
                "status": "failure",
                "error_type": type(exc).__name__,
                "reason": str(exc),
            },
        )
        write_text_atomic(
            paths.logs_dir / f"{flightline.canonical_flightline_id}_extraction.log",
            traceback.format_exc(),
        )
        raise
    source = _cache_source_record(flightline, observations, row_count)
    return source, replace(
        flightline,
        row_count=row_count,
        size_bytes=int(observations.stat().st_size),
        schema_fingerprints_json=canonical_json([source.schema_sha256]),
        cache_observations=observations.as_posix(),
        extraction_status="success",
    )


def _spectralbridge_version() -> str:
    import spectralbridge

    return spectralbridge.__version__


def _cache_source_record(
    flightline: FlightlineRecord,
    observations: Path,
    row_count: int,
) -> SourceFileRecord:
    stat = observations.stat()
    relative = observations.parent.name + "/" + observations.name
    sensors = json.loads(flightline.available_sensors_json)
    return SourceFileRecord(
        source_id=hashlib.sha256(observations.as_posix().encode("utf-8")).hexdigest()[:20],
        candidate_id=flightline.candidate_id,
        canonical_flightline_id=flightline.canonical_flightline_id,
        identity_source=flightline.identity_source,
        site=flightline.site,
        acquisition_date=flightline.acquisition_date,
        source_directory=flightline.source_directory,
        source_path=observations.as_posix(),
        relative_path=f"cache/{relative}",
        input_kind="full",
        status="accepted",
        reason=None,
        row_count=row_count,
        column_count=len(pq.read_schema(observations).names),
        size_bytes=int(stat.st_size),
        modified_time_ns=int(stat.st_mtime_ns),
        schema_sha256=_schema_fingerprint(observations),
        available_sensors_json=canonical_json(sensors),
        translation_eligible=True,
        product_role="derived_observations",
        dimensions_json=canonical_json({"rows": row_count}),
        source_signature_sha256=_schema_fingerprint(observations),
        qa_status=flightline.qa_status,
    )


__all__ = [
    "EXTRACTION_SCHEMA_VERSION",
    "discover_completed_flightlines",
    "extract_flightline_cache",
    "find_canonical_flightline_directories",
]
