"""Read-only discovery and canonical flightline catalog construction."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pyarrow.parquet as pq

from spectralbridge.file_types import NEONReflectanceFile

from .identity import (
    DEFAULT_IDENTITY_PARSERS,
    FlightlineIdentityParser,
    resolve_flightline_identity,
)
from .models import BulkInputKind, FlightlineRecord, SourceFileRecord
from .provenance import canonical_json
from .registry import (
    DEFAULT_PRODUCT_REGISTRY,
    AnalysisProfile,
    ProductRegistry,
    TranslationPair,
    resolve_analysis_profile,
)


_FULL_SUFFIX = "_merged_pixel_extraction.parquet"
_POLYGON_SUFFIX = "_polygons_merged_pixel_extraction.parquet"
_RESERVED_OBSERVATION_COLUMNS = {
    "bulk_source_path",
    "bulk_source_relative_path",
    "bulk_source_kind",
    "bulk_source_id",
    "bulk_flightline_id",
    "bulk_site",
    "bulk_acquisition_date",
}
_MAX_METADATA_BYTES = 5 * 1024 * 1024
_MAX_STATE_ITEMS = 200


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _classify_merged_parquet(path: Path) -> str | None:
    if path.name.endswith(_POLYGON_SUFFIX):
        return "polygon"
    if path.name.endswith(_FULL_SUFFIX):
        return "full"
    return None


def _canonical_stem(path: Path, input_kind: str) -> str:
    suffix = _POLYGON_SUFFIX if input_kind == "polygon" else _FULL_SUFFIX
    return path.name[: -len(suffix)]


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def canonical_identity_from_product(
    path: str | Path,
    *,
    identity_parsers: Sequence[
        FlightlineIdentityParser
    ] = DEFAULT_IDENTITY_PARSERS,
) -> dict[str, str | None]:
    """Recover scientific identity from a canonical merged-product filename.

    Outer folder names are intentionally ignored. A product whose filename
    cannot be parsed as a NEON reflectance identity is rejected rather than
    assigned a guessed identity.
    """

    product = Path(path)
    input_kind = _classify_merged_parquet(product)
    if input_kind is None:
        raise ValueError(f"Not a canonical merged Parquet product: {product.name}")
    canonical_id = _canonical_stem(product, input_kind)
    try:
        parsed = NEONReflectanceFile.from_filename(f"{canonical_id}.h5")
    except ValueError:
        identity = resolve_flightline_identity(
            product.parent, parsers=identity_parsers
        )
        if identity is None:
            raise ValueError(
                "scientific flightline identity could not be recovered from "
                f"product filename or parent manifest: {product.name!r}"
            )
        return {
            "canonical_flightline_id": identity.flightline_id,
            "identity_source": identity.identity_source,
            "site": identity.site,
            "acquisition_date": identity.acquisition_date,
        }
    return {
        "canonical_flightline_id": canonical_id,
        "identity_source": "canonical_product_filename",
        "site": parsed.site,
        "acquisition_date": _iso_date(parsed.date),
    }


def _band_map(columns: Sequence[str]) -> dict[str, set[int]]:
    mapped: dict[str, set[int]] = {}
    for column in columns:
        label, separator, suffix = column.rpartition("_band_")
        if separator and suffix.isdigit():
            mapped.setdefault(label, set()).add(int(suffix))
    return mapped


def _available_sensors(columns: Sequence[str]) -> list[str]:
    return sorted(_band_map(columns))


def _has_translation_pair(
    columns: Sequence[str], pairs: Sequence[TranslationPair]
) -> bool:
    bandmap = _band_map(columns)
    for pair in pairs:
        if pair.band_pairs:
            if any(
                source_band in bandmap.get(pair.source_sensor, set())
                and target_band in bandmap.get(pair.target_sensor, set())
                for source_band, target_band in pair.band_pairs
            ):
                return True
        elif bandmap.get(pair.source_sensor, set()) & bandmap.get(
            pair.target_sensor, set()
        ):
            return True
    return False


def _schema_fingerprint(schema: Any) -> str:
    fields = [(field.name, str(field.type), field.nullable) for field in schema]
    return hashlib.sha256(canonical_json(fields).encode("utf-8")).hexdigest()


def _candidate_paths(root: Path) -> tuple[list[Path], Path]:
    if root.is_file():
        return [root], root.parent
    if root.is_dir():
        return sorted(root.rglob("*.parquet")), root
    raise ValueError(f"Bulk input must be a file or directory: {root}")


def discover_bulk_sources(
    input_path: str | Path,
    *,
    input_kind: BulkInputKind = "full",
    exclude_dir: str | Path | None = None,
    product_registry: ProductRegistry = DEFAULT_PRODUCT_REGISTRY,
    sensors: Sequence[str] | None = None,
    translation_pairs: Sequence[str | TranslationPair] | None = None,
    identity_parsers: Sequence[
        FlightlineIdentityParser
    ] = DEFAULT_IDENTITY_PARSERS,
) -> list[SourceFileRecord]:
    """Recursively inventory full and polygon merged-Parquet candidates.

    Both product kinds are cataloged so companion availability is visible.
    ``input_kind`` controls later scientific selection, not discovery. Invalid
    candidates remain explicit rejected records.
    """

    root = Path(input_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Bulk input path does not exist: {root}")
    if input_kind not in {"full", "polygon", "both"}:
        raise ValueError("input_kind must be 'full', 'polygon', or 'both'")
    excluded = Path(exclude_dir).expanduser().resolve() if exclude_dir else None
    pairs = product_registry.select_pairs(
        sensors=sensors,
        translation_pairs=translation_pairs,
    )
    candidates, relative_root = _candidate_paths(root)
    records: list[SourceFileRecord] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if excluded is not None and _path_is_within(resolved, excluded):
            continue
        source_kind = _classify_merged_parquet(resolved)
        if source_kind is None:
            continue
        stat = resolved.stat()
        try:
            relative_path = resolved.relative_to(relative_root).as_posix()
        except ValueError:
            relative_path = resolved.name
        source_id = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:20]
        identity: dict[str, str | None] = {
            "canonical_flightline_id": None,
            "identity_source": None,
            "site": None,
            "acquisition_date": None,
        }
        reasons: list[str] = []
        reason_code: str | None = None
        try:
            identity = canonical_identity_from_product(
                resolved, identity_parsers=identity_parsers
            )
        except ValueError as exc:
            reasons.append(str(exc))
            reason_code = "identity_unresolved"

        row_count: int | None = None
        column_count: int | None = None
        schema_sha256: str | None = None
        sensors: list[str] = []
        translation_eligible = False
        try:
            if stat.st_size == 0:
                raise ValueError("zero-byte Parquet product")
            parquet_file = pq.ParquetFile(resolved)
            schema = parquet_file.schema_arrow
            columns = schema.names
            reserved = sorted(_RESERVED_OBSERVATION_COLUMNS.intersection(columns))
            if reserved:
                raise ValueError(
                    "source uses bulk-reserved column name(s): " + ", ".join(reserved)
                )
            row_count = int(parquet_file.metadata.num_rows)
            column_count = len(columns)
            schema_sha256 = _schema_fingerprint(schema)
            sensors = _available_sensors(columns)
            translation_eligible = _has_translation_pair(columns, pairs)
        except Exception as exc:
            reasons.append(f"{type(exc).__name__}: {exc}")
            if reason_code is None:
                reason_code = (
                    "zero_byte_file" if stat.st_size == 0 else "unreadable_metadata"
                )

        canonical_id = identity["canonical_flightline_id"]
        candidate_key = f"{resolved.parent.as_posix()}::{canonical_id or source_id}"
        candidate_id = hashlib.sha256(candidate_key.encode("utf-8")).hexdigest()[:20]
        records.append(
            SourceFileRecord(
                source_id=source_id,
                candidate_id=candidate_id,
                canonical_flightline_id=canonical_id,
                identity_source=identity["identity_source"],
                site=identity["site"],
                acquisition_date=identity["acquisition_date"],
                source_directory=resolved.parent.as_posix(),
                source_path=resolved.as_posix(),
                relative_path=relative_path,
                input_kind=source_kind,
                status="rejected" if reasons else "candidate",
                reason="; ".join(reasons) or None,
                row_count=row_count,
                column_count=column_count,
                size_bytes=int(stat.st_size),
                modified_time_ns=int(stat.st_mtime_ns),
                schema_sha256=schema_sha256,
                available_sensors_json=canonical_json(sensors),
                translation_eligible=translation_eligible,
                reason_code=reason_code,
                processing_stage="analysis_tables",
            )
        )
    return records


def _walk_json_items(
    value: Any,
    *,
    prefix: str = "",
    keywords: tuple[str, ...],
    output: dict[str, Any],
) -> None:
    if len(output) >= _MAX_STATE_ITEMS:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lowered = path.lower()
            if any(keyword in lowered for keyword in keywords) and not isinstance(
                item, (dict, list)
            ):
                output[path] = item
            _walk_json_items(
                item,
                prefix=path,
                keywords=keywords,
                output=output,
            )
    elif isinstance(value, list):
        for index, item in enumerate(value[:50]):
            _walk_json_items(
                item,
                prefix=f"{prefix}[{index}]",
                keywords=keywords,
                output=output,
            )


def _related_product_inventory(source_directory: Path) -> dict[str, Any]:
    qa_products: list[str] = []
    metadata_products: list[str] = []
    brightness_state: dict[str, Any] = {}
    correction_state: dict[str, Any] = {}
    stages = {"analysis_tables"}
    source_directory_size_bytes = 0
    try:
        products = sorted(path for path in source_directory.rglob("*") if path.is_file())
    except (OSError, PermissionError):
        products = []
    for product in products:
        try:
            source_directory_size_bytes += int(product.stat().st_size)
        except OSError:
            pass
        relative = product.relative_to(source_directory).as_posix()
        lowered = relative.lower()
        if "/qa/" in f"/{lowered}" or "_qa." in lowered or lowered.startswith("qa/"):
            qa_products.append(relative)
            stages.add("qa")
        if product.suffix.lower() in {".json", ".csv", ".toml", ".yaml", ".yml"} and (
            "manifest" in lowered
            or "metadata" in lowered
            or "brdf" in lowered
            or "correct" in lowered
            or "qa/" in lowered
        ):
            metadata_products.append(relative)
        if product.suffix.lower() in {".h5", ".hdf5"}:
            stages.add("input_data")
        if lowered.endswith("_envi.img") and "corrected" not in lowered and "resampl" not in lowered:
            stages.add("envi_export")
        if "brdfandtopo_corrected" in lowered:
            stages.add("brdf_topographic_correction")
        if "resampl" in lowered or "landsat" in lowered or "micasense" in lowered:
            stages.add("spectral_convolution")
        if product.suffix.lower() != ".json":
            continue
        try:
            if product.stat().st_size > _MAX_METADATA_BYTES:
                continue
            payload = json.loads(product.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        relative_brightness: dict[str, Any] = {}
        relative_correction: dict[str, Any] = {}
        _walk_json_items(
            payload,
            keywords=("brightness", "coefficient_source"),
            output=relative_brightness,
        )
        _walk_json_items(
            payload,
            keywords=("brdf", "topo", "correction_mode", "apply_mode", "ndvi"),
            output=relative_correction,
        )
        if relative_brightness:
            brightness_state[relative] = relative_brightness
        if relative_correction:
            correction_state[relative] = relative_correction
    return {
        "qa_products": qa_products,
        "metadata_products": metadata_products,
        "brightness_state": brightness_state,
        "correction_state": correction_state,
        "processing_stages": sorted(stages),
        "source_directory_size_bytes": source_directory_size_bytes,
    }


def _selected_kinds(input_kind: BulkInputKind) -> set[str]:
    return {"full", "polygon"} if input_kind == "both" else {input_kind}


def build_bulk_catalog(
    input_path: str | Path,
    *,
    input_kind: BulkInputKind = "full",
    exclude_dir: str | Path | None = None,
    analysis_profile: str | AnalysisProfile = "translation",
    product_registry: ProductRegistry = DEFAULT_PRODUCT_REGISTRY,
    sensors: Sequence[str] | None = None,
    translation_pairs: Sequence[str | TranslationPair] | None = None,
    identity_parsers: Sequence[
        FlightlineIdentityParser
    ] = DEFAULT_IDENTITY_PARSERS,
) -> tuple[list[SourceFileRecord], list[FlightlineRecord]]:
    """Build source-file and canonical-flightline catalogs.

    Duplicate canonical IDs in different source directories are explicitly
    excluded. Multiple different IDs in one machine/run directory remain
    independent scientific flightlines.
    """

    root = Path(input_path).expanduser().resolve()
    profile = resolve_analysis_profile(analysis_profile)
    pairs = product_registry.select_pairs(
        sensors=sensors,
        translation_pairs=translation_pairs,
        allowed_sensors=profile.allowed_sensors,
        allowed_matching_groups=profile.allowed_matching_groups,
        allow_empty=not profile.require_translation_pair,
    )
    source_records = discover_bulk_sources(
        root,
        input_kind=input_kind,
        exclude_dir=exclude_dir,
        product_registry=product_registry,
        sensors=sensors,
        translation_pairs=pairs,
        identity_parsers=identity_parsers,
    )
    grouped: dict[tuple[str, str], list[SourceFileRecord]] = defaultdict(list)
    unresolved: list[SourceFileRecord] = []
    for record in source_records:
        if record.canonical_flightline_id is None:
            unresolved.append(record)
        else:
            grouped[(record.source_directory, record.canonical_flightline_id)].append(record)

    selected_kinds = _selected_kinds(input_kind)
    flightlines: list[FlightlineRecord] = []
    selection_by_candidate: dict[str, set[str]] = {}
    related_by_directory: dict[str, dict[str, Any]] = {}
    for (source_directory, canonical_id), records in sorted(grouped.items()):
        by_kind: dict[str, list[SourceFileRecord]] = defaultdict(list)
        for record in records:
            by_kind[record.input_kind].append(record)
        selected = [record for record in records if record.input_kind in selected_kinds]
        selected_ids = {record.source_id for record in selected}
        selection_by_candidate[records[0].candidate_id] = selected_ids
        reasons: list[str] = []
        reason_codes: list[str] = []
        if not selected:
            reasons.append(f"missing selected {input_kind} merged product")
            reason_codes.append("missing_required_product")
        for kind in selected_kinds:
            if len(by_kind.get(kind, [])) > 1:
                reasons.append(f"multiple {kind} merged products in one source directory")
                reason_codes.append("duplicate_product")
        invalid_selected = [record for record in selected if record.status == "rejected"]
        if invalid_selected:
            reasons.extend(record.reason or "invalid source" for record in invalid_selected)
            reason_codes.extend(
                record.reason_code or "invalid_source" for record in invalid_selected
            )
        readable_selected = [record for record in selected if record.status != "rejected"]
        available_sensors = sorted(
            {
                sensor
                for record in readable_selected
                for sensor in json.loads(record.available_sensors_json)
            }
        )
        pair_eligible = any(
            record.translation_eligible for record in readable_selected
        )
        if profile.require_translation_pair and readable_selected and not pair_eligible:
            reasons.append("no requested compatible translation pair is present")
            reason_codes.append("incomplete_translation_pair")
        if source_directory not in related_by_directory:
            related_by_directory[source_directory] = _related_product_inventory(
                Path(source_directory)
            )
        related = related_by_directory[source_directory]
        selected_paths = [record.source_path for record in readable_selected]
        selected_row_count = (
            sum(int(record.row_count or 0) for record in readable_selected)
            if readable_selected
            else None
        )
        acquisition_date = records[0].acquisition_date
        acquisition_year = int(acquisition_date[:4]) if acquisition_date else None
        provenance = {
            "input_root": root.as_posix(),
            "source_directory": source_directory,
            "identity_authority": records[0].identity_source,
            "outer_directory_names_are_scientific_identifiers": False,
        }
        flightlines.append(
            FlightlineRecord(
                candidate_id=records[0].candidate_id,
                canonical_flightline_id=canonical_id,
                identity_source=records[0].identity_source,
                site=records[0].site,
                acquisition_date=acquisition_date,
                acquisition_year=acquisition_year,
                source_directory=source_directory,
                canonical_merged_parquet=(
                    by_kind["full"][0].source_path if len(by_kind.get("full", [])) == 1 else None
                ),
                polygon_merged_parquet=(
                    by_kind["polygon"][0].source_path
                    if len(by_kind.get("polygon", [])) == 1
                    else None
                ),
                selected_source_ids_json=canonical_json(
                    [record.source_id for record in readable_selected]
                ),
                selected_source_paths_json=canonical_json(selected_paths),
                qa_products_json=canonical_json(related["qa_products"]),
                metadata_products_json=canonical_json(related["metadata_products"]),
                available_sensors_json=canonical_json(available_sensors),
                processing_stages_json=canonical_json(related["processing_stages"]),
                row_count=selected_row_count,
                size_bytes=sum(record.size_bytes for record in readable_selected),
                source_directory_size_bytes=related[
                    "source_directory_size_bytes"
                ],
                schema_fingerprints_json=canonical_json(
                    sorted(
                        {
                            record.schema_sha256
                            for record in readable_selected
                            if record.schema_sha256
                        }
                    )
                ),
                brightness_state_json=canonical_json(related["brightness_state"]),
                correction_state_json=canonical_json(related["correction_state"]),
                translation_eligible=pair_eligible,
                status="rejected" if reasons else "accepted",
                rejection_reason="; ".join(reasons) or None,
                duplicate_status="unique",
                duplicate_candidate_count=1,
                source_provenance_json=canonical_json(provenance),
                analysis_profile=profile.name,
                processing_completeness="analysis_table_available",
                product_availability_json=canonical_json(
                    {
                        "merged_parquet": {
                            "candidate_count": len(selected),
                            "valid_count": len(readable_selected),
                        }
                    }
                ),
                exclusion_reason_codes_json=canonical_json(
                    sorted(set(reason_codes))
                ),
                exclusion_context_json=canonical_json(
                    [
                        {
                            "reason_code": code,
                            "detail": detail,
                            "product_role": "merged_parquet",
                            "processing_stage": "analysis_tables",
                            "offending_files": [record.source_path for record in selected],
                        }
                        for code, detail in zip(reason_codes, reasons)
                    ]
                ),
            )
        )

    for record in unresolved:
        if record.source_directory not in related_by_directory:
            related_by_directory[record.source_directory] = _related_product_inventory(
                Path(record.source_directory)
            )
        related = related_by_directory[record.source_directory]
        flightlines.append(
            FlightlineRecord(
                candidate_id=record.candidate_id,
                canonical_flightline_id=None,
                identity_source=None,
                site=None,
                acquisition_date=None,
                acquisition_year=None,
                source_directory=record.source_directory,
                canonical_merged_parquet=(record.source_path if record.input_kind == "full" else None),
                polygon_merged_parquet=(
                    record.source_path if record.input_kind == "polygon" else None
                ),
                selected_source_ids_json="[]",
                selected_source_paths_json="[]",
                qa_products_json=canonical_json(related["qa_products"]),
                metadata_products_json=canonical_json(related["metadata_products"]),
                available_sensors_json=record.available_sensors_json,
                processing_stages_json=canonical_json(related["processing_stages"]),
                row_count=record.row_count,
                size_bytes=record.size_bytes,
                source_directory_size_bytes=related[
                    "source_directory_size_bytes"
                ],
                schema_fingerprints_json=canonical_json(
                    [record.schema_sha256] if record.schema_sha256 else []
                ),
                brightness_state_json=canonical_json(related["brightness_state"]),
                correction_state_json=canonical_json(related["correction_state"]),
                translation_eligible=False,
                status="rejected",
                rejection_reason=record.reason or "canonical identity unresolved",
                duplicate_status="not_evaluated",
                duplicate_candidate_count=0,
                source_provenance_json=canonical_json(
                    {"input_root": root.as_posix(), "source_path": record.source_path}
                ),
                analysis_profile=profile.name,
                processing_completeness="unknown",
                product_availability_json="{}",
                exclusion_reason_codes_json=canonical_json(
                    [record.reason_code or "identity_unresolved"]
                ),
                exclusion_context_json=canonical_json(
                    [
                        {
                            "reason_code": record.reason_code
                            or "identity_unresolved",
                            "detail": record.reason
                            or "scientific identity unresolved",
                            "product_role": "merged_parquet",
                            "processing_stage": "analysis_tables",
                            "offending_files": [record.source_path],
                        }
                    ]
                ),
            )
        )

    eligible_by_id: dict[str, list[int]] = defaultdict(list)
    for index, flightline in enumerate(flightlines):
        if flightline.canonical_flightline_id:
            eligible_by_id[flightline.canonical_flightline_id].append(index)
    for indices in eligible_by_id.values():
        source_directories = {flightlines[index].source_directory for index in indices}
        if len(source_directories) < 2:
            continue
        for index in indices:
            flightline = flightlines[index]
            detail = (
                "scientific flightline ID occurs in multiple source directories; "
                "all candidates are excluded pending explicit duplicate resolution"
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

    flightline_by_candidate = {item.candidate_id: item for item in flightlines}
    final_sources: list[SourceFileRecord] = []
    for record in source_records:
        flightline = flightline_by_candidate.get(record.candidate_id)
        if record.status == "rejected" or flightline is None:
            final_sources.append(record)
            continue
        selected_ids = selection_by_candidate.get(record.candidate_id, set())
        if record.source_id not in selected_ids:
            final_sources.append(replace(record, status="companion_not_selected"))
        elif flightline.status == "accepted":
            final_sources.append(replace(record, status="accepted"))
        elif flightline.status == "duplicate_excluded":
            final_sources.append(
                replace(
                    record,
                    status="duplicate_excluded",
                    reason=flightline.rejection_reason,
                    reason_code="duplicate_scientific_identity",
                )
            )
        else:
            final_sources.append(
                replace(
                    record,
                    status="rejected",
                    reason=flightline.rejection_reason,
                    reason_code=(
                        json.loads(flightline.exclusion_reason_codes_json)[0]
                        if json.loads(flightline.exclusion_reason_codes_json)
                        else "invalid_source"
                    ),
                )
            )

    return (
        sorted(final_sources, key=lambda item: item.relative_path),
        sorted(
            flightlines,
            key=lambda item: (
                item.canonical_flightline_id or "",
                item.source_directory,
            ),
        ),
    )


def catalog_signature_records(
    source_files: Iterable[SourceFileRecord],
    flightlines: Iterable[FlightlineRecord],
) -> dict[str, list[dict[str, Any]]]:
    """Return deterministic manifest-ready catalog records."""

    return {
        "source_files": [asdict(record) for record in source_files],
        "flightlines": [asdict(record) for record in flightlines],
    }


__all__ = [
    "build_bulk_catalog",
    "canonical_identity_from_product",
    "catalog_signature_records",
    "discover_bulk_sources",
]
