"""Structured exclusion records for population-safe bulk processing."""

from __future__ import annotations

import hashlib
import json
from typing import Sequence

from .models import ExclusionRecord, FlightlineRecord, SourceFileRecord
from .provenance import canonical_json


KNOWN_REASON_CODES = frozenset(
    {
        "missing_required_product",
        "missing_sidecar",
        "zero_byte_file",
        "duplicate_product",
        "unreadable_metadata",
        "invalid_dimensions",
        "incompatible_band_schema",
        "incomplete_translation_pair",
        "duplicate_scientific_identity",
        "extraction_failure",
        "identity_unresolved",
        "transient_source_disappeared",
        "invalid_source",
    }
)


def _identifier(parts: Sequence[str]) -> str:
    return hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()[:24]


def build_exclusion_records(
    source_files: Sequence[SourceFileRecord],
    flightlines: Sequence[FlightlineRecord],
) -> list[ExclusionRecord]:
    """Build deterministic exclusions from product and flightline validation."""

    records: list[ExclusionRecord] = []
    seen: set[tuple[str, str, str]] = set()
    by_candidate = {item.candidate_id: item for item in flightlines}

    def append(
        *,
        flightline: FlightlineRecord,
        source_path: str,
        product_role: str | None,
        sensor_name: str | None,
        reason_code: str,
        detail: str,
        processing_stage: str | None,
        offending_files: Sequence[str],
    ) -> None:
        normalized = reason_code if reason_code in KNOWN_REASON_CODES else "invalid_source"
        key = (flightline.candidate_id, source_path, normalized)
        if key in seen:
            return
        seen.add(key)
        records.append(
            ExclusionRecord(
                exclusion_id=_identifier(key),
                canonical_flightline_id=flightline.canonical_flightline_id,
                source_path=source_path,
                site=flightline.site,
                acquisition_date=flightline.acquisition_date,
                analysis_profile=flightline.analysis_profile,
                product_role=product_role,
                sensor_name=sensor_name,
                offending_files_json=canonical_json(list(offending_files)),
                reason_code=normalized,
                detail=detail,
                processing_stage=processing_stage,
            )
        )

    for source in source_files:
        if source.status not in {"rejected", "duplicate_excluded"}:
            continue
        flightline = by_candidate.get(source.candidate_id)
        if flightline is None:
            continue
        append(
            flightline=flightline,
            source_path=source.source_path,
            product_role=source.product_role,
            sensor_name=source.sensor_name,
            reason_code=source.reason_code or "invalid_source",
            detail=source.reason or "source product is invalid",
            processing_stage=source.processing_stage,
            offending_files=[source.source_path],
        )

    for flightline in flightlines:
        if flightline.status == "accepted":
            continue
        try:
            codes = json.loads(flightline.exclusion_reason_codes_json)
        except json.JSONDecodeError:
            codes = []
        if not codes:
            codes = [
                "duplicate_scientific_identity"
                if flightline.status == "duplicate_excluded"
                else "invalid_source"
            ]
        try:
            contexts = json.loads(flightline.exclusion_context_json)
        except json.JSONDecodeError:
            contexts = []
        context_by_code = {
            item.get("reason_code"): item
            for item in contexts
            if isinstance(item, dict) and item.get("reason_code")
        }
        for code in codes:
            context = context_by_code.get(code, {})
            offending = context.get("offending_files") or []
            append(
                flightline=flightline,
                source_path=flightline.source_directory,
                product_role=context.get("product_role"),
                sensor_name=context.get("sensor_name"),
                reason_code=str(code),
                detail=str(
                    context.get("detail")
                    or flightline.rejection_reason
                    or "flightline is not eligible"
                ),
                processing_stage=context.get("processing_stage"),
                offending_files=[str(item) for item in offending],
            )
    return sorted(
        records,
        key=lambda item: (
            item.canonical_flightline_id or "",
            item.reason_code,
            item.source_path,
        ),
    )


__all__ = ["KNOWN_REASON_CODES", "build_exclusion_records"]
