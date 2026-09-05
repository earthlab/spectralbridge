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
from typing import Any, Iterable, Sequence

import duckdb
import pyarrow.parquet as pq

from .dataset import quote_identifier, quote_path
from .identity import (
    DEFAULT_IDENTITY_PARSERS,
    FlightlineIdentityParser,
    resolve_flightline_identity,
)
from .models import BulkAnalysisPaths, FlightlineRecord, SourceFileRecord
from .provenance import canonical_json, signature_sha256, write_json_atomic, write_text_atomic
from .registry import (
    DEFAULT_PRODUCT_REGISTRY,
    AnalysisProfile,
    ProductDescriptor,
    ProductRegistry,
    TranslationPair,
    resolve_analysis_profile,
)


LOGGER = logging.getLogger(__name__)
EXTRACTION_SCHEMA_VERSION = 1


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


class ProductValidationError(ValueError):
    """Validation failure with a stable machine-readable reason code."""

    def __init__(self, reason_code: str, detail: str) -> None:
        super().__init__(detail)
        self.reason_code = reason_code


def find_canonical_flightline_directories(
    input_path: str | Path,
    *,
    exclude_dir: str | Path | None = None,
    identity_parsers: Sequence[
        FlightlineIdentityParser
    ] = DEFAULT_IDENTITY_PARSERS,
) -> list[Path]:
    """Find scientifically identifiable flightline directories recursively."""

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
            identity = resolve_flightline_identity(
                directory, parsers=identity_parsers
            )
        except (OSError, ValueError):
            continue
        if identity is not None:
            found.append(directory)
    return sorted(set(found))


def _small_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _raster_metadata(
    img: Path,
    hdr: Path,
    *,
    descriptor: ProductDescriptor,
    profile: AnalysisProfile,
) -> dict[str, Any]:
    import rasterio
    from spectralbridge.exports.schema_utils import parse_envi_wavelengths_nm

    try:
        img_stat = img.stat()
    except FileNotFoundError as exc:
        raise ProductValidationError(
            "transient_source_disappeared", f"source disappeared during discovery: {img}"
        ) from exc
    if profile.require_nonzero_files and img_stat.st_size == 0:
        raise ProductValidationError("zero_byte_file", f"zero-byte raster: {img.name}")
    if descriptor.header_required:
        try:
            hdr_stat = hdr.stat()
        except FileNotFoundError as exc:
            raise ProductValidationError(
                "missing_sidecar", f"missing ENVI header: {hdr.name}"
            ) from exc
        if profile.require_nonzero_files and hdr_stat.st_size == 0:
            raise ProductValidationError(
                "zero_byte_file", f"zero-byte ENVI header: {hdr.name}"
            )
    else:
        hdr_stat = None
    try:
        with rasterio.open(img) as dataset:
            if (
                profile.require_valid_dimensions
                and (dataset.width < 1 or dataset.height < 1 or dataset.count < 1)
            ):
                raise ProductValidationError(
                    "invalid_dimensions", f"invalid ENVI dimensions: {img.name}"
                )
            metadata = {
                "rows": int(dataset.height),
                "columns": int(dataset.width),
                "bands": int(dataset.count),
                "crs": dataset.crs.to_string() if dataset.crs else None,
                "transform": tuple(float(value) for value in dataset.transform),
                "nodata": dataset.nodata,
                "dtype": dataset.dtypes[0] if dataset.dtypes else None,
            }
    except ProductValidationError:
        raise
    except Exception as exc:
        raise ProductValidationError(
            "unreadable_metadata",
            f"unreadable ENVI metadata for {img.name}: {type(exc).__name__}: {exc}",
        ) from exc
    if (
        profile.require_compatible_band_schema
        and descriptor.expected_band_count is not None
        and metadata["bands"] != descriptor.expected_band_count
    ):
        raise ProductValidationError(
            "incompatible_band_schema",
            f"{descriptor.sensor_name or descriptor.key} expected "
            f"{descriptor.expected_band_count} bands but found {metadata['bands']}",
        )
    header_text = ""
    if hdr_stat is not None:
        try:
            header_text = hdr.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            raise ProductValidationError(
                "unreadable_metadata", f"cannot read ENVI header: {hdr.name}"
            ) from exc
    wavelengths = parse_envi_wavelengths_nm(header_text) if header_text else None
    signature = {
        "image_path": img.resolve().as_posix(),
        "image_size_bytes": int(img_stat.st_size),
        "image_modified_time_ns": int(img_stat.st_mtime_ns),
        "header_path": hdr.resolve().as_posix(),
        "header_size_bytes": int(hdr_stat.st_size) if hdr_stat else None,
        "header_modified_time_ns": int(hdr_stat.st_mtime_ns) if hdr_stat else None,
        "header_sha256": _small_file_sha256(hdr) if hdr_stat else None,
        "raster_metadata": metadata,
    }
    return {
        **metadata,
        **signature,
        "wavelengths_nm": wavelengths or [],
        "source_signature_sha256": signature_sha256(signature),
    }


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


def _translation_eligibility(
    targets: dict[str, dict[str, Any]],
    pairs: Sequence[TranslationPair],
) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for pair in pairs:
        source = targets.get(pair.source_sensor)
        target = targets.get(pair.target_sensor)
        compatible = source is not None and target is not None
        if compatible:
            compatible = (
                source.get("matching_group") == pair.matching_group
                and target.get("matching_group") == pair.matching_group
                and all(
                    source[key] == target[key]
                    for key in ("rows", "columns", "crs", "transform")
                )
            )
        if compatible and pair.band_pairs:
            compatible = (
                max(source_band for source_band, _ in pair.band_pairs)
                <= int(source["bands"])
                and max(target_band for _, target_band in pair.band_pairs)
                <= int(target["bands"])
            )
        if compatible and pair.expected_source_bands is not None:
            compatible = int(source["bands"]) == pair.expected_source_bands
        if compatible and pair.expected_target_bands is not None:
            compatible = int(target["bands"]) == pair.expected_target_bands
        result[pair.key] = bool(compatible)
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
    identity_source: str = "canonical_flightline_directory",
    reason_code: str | None = None,
    matching_group: str | None = None,
    processing_stage: str | None = None,
) -> SourceFileRecord:
    relative = path.relative_to(root).as_posix()
    try:
        stat = path.stat()
        size_bytes = int(stat.st_size)
        modified_time_ns = int(stat.st_mtime_ns)
    except FileNotFoundError:
        size_bytes = 0
        modified_time_ns = 0
    return SourceFileRecord(
        source_id=hashlib.sha256(relative.encode("utf-8")).hexdigest()[:20],
        candidate_id=candidate_id,
        canonical_flightline_id=canonical_id,
        identity_source=identity_source,
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
        size_bytes=size_bytes,
        modified_time_ns=modified_time_ns,
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
        reason_code=reason_code,
        matching_group=matching_group,
        processing_stage=processing_stage,
        wavelengths_json=canonical_json(metadata.get("wavelengths_nm", []) if metadata else []),
        dtype=str(metadata.get("dtype")) if metadata and metadata.get("dtype") else None,
    )


def discover_completed_flightlines(
    input_path: str | Path,
    *,
    exclude_dir: str | Path | None = None,
    analysis_profile: str | AnalysisProfile = "translation",
    product_registry: ProductRegistry = DEFAULT_PRODUCT_REGISTRY,
    identity_parsers: Sequence[
        FlightlineIdentityParser
    ] = DEFAULT_IDENTITY_PARSERS,
    sensors: Sequence[str] | None = None,
    translation_pairs: Sequence[str | TranslationPair] | None = None,
) -> tuple[list[SourceFileRecord], list[FlightlineRecord]]:
    """Inventory identifiable flightlines without reading raster pixels."""

    root = Path(input_path).expanduser().resolve()
    profile = resolve_analysis_profile(analysis_profile)
    pairs = product_registry.select_pairs(
        sensors=sensors,
        translation_pairs=translation_pairs,
        allowed_sensors=profile.allowed_sensors,
        allowed_matching_groups=profile.allowed_matching_groups,
        allow_empty=not profile.require_translation_pair,
    )
    directories = find_canonical_flightline_directories(
        root,
        exclude_dir=exclude_dir,
        identity_parsers=identity_parsers,
    )
    sources: list[SourceFileRecord] = []
    flightlines: list[FlightlineRecord] = []
    for directory in directories:
        identity = resolve_flightline_identity(directory, parsers=identity_parsers)
        if identity is None:  # pragma: no cover - already resolved above
            continue
        canonical_id = identity.flightline_id
        candidate_id = hashlib.sha256(
            f"{directory.as_posix()}::{canonical_id}".encode("utf-8")
        ).hexdigest()[:20]
        qa_files, qa_status, stage_statuses = _qa_inventory(directory)
        try:
            candidates = sorted(directory.rglob("*"))
        except (OSError, PermissionError):
            candidates = []
        files: list[Path] = []
        source_bytes = 0
        for path in candidates:
            try:
                if not path.is_file():
                    continue
                files.append(path)
                source_bytes += int(path.stat().st_size)
            except (FileNotFoundError, OSError):
                continue
        metadata_files = [
            path.relative_to(directory).as_posix()
            for path in files
            if path.suffix.lower() in {".json", ".csv", ".toml", ".yaml", ".yml"}
        ]

        by_descriptor: dict[str, list[Path]] = defaultdict(list)
        for path in files:
            descriptor = product_registry.recognize(path)
            if descriptor is not None:
                by_descriptor[descriptor.key].append(path)

        product_availability: dict[str, dict[str, Any]] = {}
        valid_products: dict[str, dict[str, Any]] = {}
        valid_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
        source_records_start = len(sources)
        for descriptor in product_registry.products:
            product_candidates = by_descriptor.get(descriptor.key, [])
            availability = {
                "product_role": descriptor.product_role,
                "sensor_name": descriptor.sensor_name,
                "candidate_count": len(product_candidates),
                "valid_count": 0,
                "status": "missing" if not product_candidates else "candidate",
            }
            product_availability[descriptor.key] = availability
            if len(product_candidates) > 1:
                availability["status"] = "duplicate"
                for path in product_candidates:
                    sources.append(
                        _source_record(
                            root=root,
                            directory=directory,
                            canonical_id=canonical_id,
                            site=identity.site or "",
                            acquisition_date=identity.acquisition_date or "",
                            candidate_id=candidate_id,
                            path=path,
                            role=descriptor.product_role,
                            sensor=descriptor.sensor_name,
                            status="rejected",
                            reason=(
                                "multiple products match descriptor "
                                f"{descriptor.key}"
                            ),
                            metadata=None,
                            qa_status=qa_status,
                            identity_source=identity.identity_source,
                            reason_code="duplicate_product",
                            matching_group=descriptor.matching_group,
                            processing_stage=descriptor.processing_stage,
                        )
                    )
                continue
            if not product_candidates:
                continue
            path = product_candidates[0]
            try:
                metadata = _raster_metadata(
                    path,
                    path.with_suffix(".hdr"),
                    descriptor=descriptor,
                    profile=profile,
                )
            except ProductValidationError as exc:
                status = "rejected"
                reason = str(exc)
                reason_code = exc.reason_code
                metadata = None
                availability["status"] = reason_code
            else:
                status = "available"
                reason = None
                reason_code = None
                metadata.update(
                    {
                        "image": path.as_posix(),
                        "header": path.with_suffix(".hdr").as_posix(),
                        "product_key": descriptor.key,
                        "product_role": descriptor.product_role,
                        "sensor_name": descriptor.sensor_name,
                        "matching_group": descriptor.matching_group,
                        "processing_stage": descriptor.processing_stage,
                    }
                )
                availability["status"] = "available"
                availability["valid_count"] = 1
                valid_by_role[descriptor.product_role].append(metadata)
                if descriptor.sensor_name:
                    valid_products[descriptor.sensor_name] = metadata
            sources.append(
                _source_record(
                    root=root,
                    directory=directory,
                    canonical_id=canonical_id,
                    site=identity.site or "",
                    acquisition_date=identity.acquisition_date or "",
                    candidate_id=candidate_id,
                    path=path,
                    role=descriptor.product_role,
                    sensor=descriptor.sensor_name,
                    status=status,
                    reason=reason,
                    metadata=metadata,
                    qa_status=qa_status,
                    identity_source=identity.identity_source,
                    reason_code=reason_code,
                    matching_group=descriptor.matching_group,
                    processing_stage=descriptor.processing_stage,
                )
            )

        corrected = next(
            iter(valid_by_role.get("corrected_hyperspectral", [])), {}
        )
        targets = valid_products
        eligibility = _translation_eligibility(targets, pairs)
        eligible_pairs = [pair for pair in pairs if eligibility[pair.key]]
        selected_sensors = sorted(
            {
                sensor
                for pair in eligible_pairs
                for sensor in (pair.source_sensor, pair.target_sensor)
            }
        )

        exclusion_codes: list[str] = []
        exclusion_contexts: list[dict[str, Any]] = []

        def exclude(
            reason_code: str,
            detail: str,
            *,
            product_role: str | None = None,
            sensor_name: str | None = None,
            processing_stage: str | None = None,
            offending_files: Sequence[str] = (),
        ) -> None:
            if reason_code not in exclusion_codes:
                exclusion_codes.append(reason_code)
            exclusion_contexts.append(
                {
                    "reason_code": reason_code,
                    "detail": detail,
                    "product_role": product_role,
                    "sensor_name": sensor_name,
                    "processing_stage": processing_stage,
                    "offending_files": list(offending_files),
                }
            )

        required_roles = set(profile.required_product_roles)
        if profile.require_original_hyperspectral:
            required_roles.add("raw_hyperspectral")
        if profile.require_corrected_hyperspectral:
            required_roles.add("corrected_hyperspectral")
        requested_sensor_names = {
            sensor
            for pair in pairs
            for sensor in (pair.source_sensor, pair.target_sensor)
        }
        required_product_keys = {
            descriptor.key
            for descriptor in product_registry.products
            if (
                descriptor.sensor_name in requested_sensor_names
                or (
                    descriptor.product_role in required_roles
                    and descriptor.product_role != "target_sensor"
                )
            )
        }
        for role in sorted(required_roles - set(valid_by_role)):
            exclude(
                "missing_required_product",
                f"analysis profile {profile.name!r} requires product role {role!r}",
                product_role=role,
            )
        if profile.require_qa and not qa_files:
            exclude(
                "missing_required_product",
                f"analysis profile {profile.name!r} requires QA metadata",
                product_role="qa",
                processing_stage="qa",
            )
        if profile.require_translation_pair and not eligible_pairs:
            available = ", ".join(sorted(targets)) or "none"
            exclude(
                "incomplete_translation_pair",
                "no requested compatible translation pair is complete; "
                f"available sensors: {available}",
                product_role="target_sensor",
                processing_stage="spectral_convolution",
            )

        raw_present = bool(valid_by_role.get("raw_hyperspectral"))
        corrected_present = bool(valid_by_role.get("corrected_hyperspectral"))
        if raw_present and corrected_present and targets:
            processing_completeness = "complete"
        elif targets and not (raw_present or corrected_present):
            processing_completeness = "minimal_analysis_archive"
        elif targets or corrected_present or raw_present:
            processing_completeness = "partial"
        else:
            processing_completeness = "incomplete"

        translation_eligible = bool(eligible_pairs)
        representative = next(
            (targets[sensor] for sensor in selected_sensors if sensor in targets),
            None,
        )
        pixel_count = (
            int(representative["rows"]) * int(representative["columns"])
            if representative
            else 0
        )
        selected_band_count = sum(
            int(targets[sensor]["bands"])
            for sensor in selected_sensors
            if sensor in targets
        )
        estimated_cache_bytes = pixel_count * (24 + 4 * selected_band_count)
        stages = sorted(
            {
                str(product["processing_stage"])
                for products in valid_by_role.values()
                for product in products
                if product.get("processing_stage")
            }
            | ({"qa"} if qa_files else set())
        )
        provenance = {
            "input_root": root.as_posix(),
            "source_directory": directory.as_posix(),
            "outer_storage_path": directory.parent.as_posix(),
            "outer_directory_names_are_scientific_identifiers": False,
            "identity_authority": identity.identity_source,
            "source_signature_policy": (
                "path_size_mtime_header_sha256_and_envi_metadata"
            ),
            "product_registry_keys": [
                descriptor.key for descriptor in product_registry.products
            ],
            "selected_translation_pairs": [pair.key for pair in pairs],
        }
        candidate_sources = sources[source_records_start:]
        flightlines.append(
            FlightlineRecord(
                candidate_id=candidate_id,
                canonical_flightline_id=canonical_id,
                identity_source=identity.identity_source,
                site=identity.site,
                acquisition_date=identity.acquisition_date,
                acquisition_year=(
                    int(identity.acquisition_date[:4])
                    if identity.acquisition_date
                    else None
                ),
                source_directory=directory.as_posix(),
                canonical_merged_parquet=None,
                polygon_merged_parquet=None,
                selected_source_ids_json=canonical_json(
                    [
                        source.source_id
                        for source in candidate_sources
                        if source.status == "available"
                        and source.sensor_name in selected_sensors
                    ]
                ),
                selected_source_paths_json=canonical_json(
                    [targets[sensor]["image"] for sensor in selected_sensors]
                ),
                qa_products_json=canonical_json(qa_files),
                metadata_products_json=canonical_json(metadata_files),
                available_sensors_json=canonical_json(sorted(targets)),
                processing_stages_json=canonical_json(stages),
                row_count=None,
                size_bytes=sum(
                    int(targets[sensor]["image_size_bytes"])
                    for sensor in selected_sensors
                ),
                source_directory_size_bytes=source_bytes,
                schema_fingerprints_json="[]",
                brightness_state_json="{}",
                correction_state_json=canonical_json(
                    {"corrected_product_present": corrected_present}
                ),
                translation_eligible=translation_eligible,
                status="rejected" if exclusion_codes else "accepted",
                rejection_reason=(
                    "; ".join(
                        context["detail"] for context in exclusion_contexts
                    )
                    or None
                ),
                duplicate_status="unique",
                duplicate_candidate_count=1,
                source_provenance_json=canonical_json(provenance),
                input_mode="flightline_outputs",
                corrected_product_json=canonical_json(corrected),
                target_products_json=canonical_json(targets),
                qa_status=qa_status,
                stage_qa_status_json=canonical_json(stage_statuses),
                missing_products_json=canonical_json(
                    [
                        key
                        for key, availability in product_availability.items()
                        if key in required_product_keys
                        and availability["status"] != "available"
                    ]
                ),
                analysis_eligibility_json=canonical_json(eligibility),
                estimated_cache_bytes=estimated_cache_bytes,
                cache_observations=None,
                extraction_status=(
                    "pending" if not exclusion_codes else "not_eligible"
                ),
                analysis_profile=profile.name,
                processing_completeness=processing_completeness,
                product_availability_json=canonical_json(product_availability),
                exclusion_reason_codes_json=canonical_json(exclusion_codes),
                exclusion_context_json=canonical_json(exclusion_contexts),
            )
        )

    by_id: dict[str, list[int]] = defaultdict(list)
    for index, flightline in enumerate(flightlines):
        if flightline.canonical_flightline_id:
            by_id[flightline.canonical_flightline_id].append(index)
    for indices in by_id.values():
        if len({flightlines[index].source_directory for index in indices}) < 2:
            continue
        for index in indices:
            flightline = flightlines[index]
            detail = (
                "scientific flightline ID occurs in multiple source directories; "
                "all candidates are excluded"
            )
            existing_codes = json.loads(flightline.exclusion_reason_codes_json)
            existing_contexts = json.loads(flightline.exclusion_context_json)
            flightlines[index] = replace(
                flightline,
                status="duplicate_excluded",
                rejection_reason="; ".join(
                    value
                    for value in (flightline.rejection_reason, detail)
                    if value
                ),
                duplicate_status="duplicate_canonical_id",
                duplicate_candidate_count=len(indices),
                extraction_status="not_eligible",
                exclusion_reason_codes_json=canonical_json(
                    sorted({*existing_codes, "duplicate_scientific_identity"})
                ),
                exclusion_context_json=canonical_json(
                    [
                        *existing_contexts,
                        {
                            "reason_code": "duplicate_scientific_identity",
                            "detail": detail,
                            "offending_files": [flightline.source_directory],
                        }
                    ]
                ),
            )
    status_by_candidate = {item.candidate_id: item.status for item in flightlines}
    final_sources = [
        replace(
            source,
            status=(
                "duplicate_excluded"
                if status_by_candidate.get(source.candidate_id)
                == "duplicate_excluded"
                else source.status
            ),
            reason_code=(
                "duplicate_scientific_identity"
                if status_by_candidate.get(source.candidate_id)
                == "duplicate_excluded"
                and source.reason_code is None
                else source.reason_code
            ),
        )
        for source in sources
    ]
    return sorted(final_sources, key=lambda item: item.relative_path), sorted(
        flightlines,
        key=lambda item: (
            item.canonical_flightline_id or "",
            item.source_directory,
        ),
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
    translation_pairs: Sequence[TranslationPair],
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
            for pair in translation_pairs
            if eligibility.get(pair.key)
            for sensor in (pair.source_sensor, pair.target_sensor)
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
        "translation_pairs": [
            {
                "key": pair.key,
                "source_sensor": pair.source_sensor,
                "target_sensor": pair.target_sensor,
                "matching_group": pair.matching_group,
                "band_pairs": pair.band_pairs,
            }
            for pair in translation_pairs
            if eligibility.get(pair.key)
        ],
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
