"""Data contracts for production bulk analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


BULK_SCHEMA_VERSION = 4
BulkInputKind = Literal["full", "polygon", "both"]
BulkInputMode = Literal["auto", "flightline_outputs", "merged_parquet"]


@dataclass(frozen=True)
class SourceFileRecord:
    """One source product discovered in the read-only input tree."""

    source_id: str
    candidate_id: str
    canonical_flightline_id: str | None
    identity_source: str | None
    site: str | None
    acquisition_date: str | None
    source_directory: str
    source_path: str
    relative_path: str
    input_kind: str
    status: str
    reason: str | None
    row_count: int | None
    column_count: int | None
    size_bytes: int
    modified_time_ns: int
    schema_sha256: str | None
    available_sensors_json: str
    translation_eligible: bool
    product_role: str = "merged_parquet"
    sensor_name: str | None = None
    header_path: str | None = None
    dimensions_json: str = "{}"
    source_signature_sha256: str | None = None
    qa_status: str | None = None
    reason_code: str | None = None
    matching_group: str | None = None
    processing_stage: str | None = None
    wavelengths_json: str = "[]"
    dtype: str | None = None


@dataclass(frozen=True)
class FlightlineRecord:
    """Canonical scientific unit recovered from one source directory."""

    candidate_id: str
    canonical_flightline_id: str | None
    identity_source: str | None
    site: str | None
    acquisition_date: str | None
    acquisition_year: int | None
    source_directory: str
    canonical_merged_parquet: str | None
    polygon_merged_parquet: str | None
    selected_source_ids_json: str
    selected_source_paths_json: str
    qa_products_json: str
    metadata_products_json: str
    available_sensors_json: str
    processing_stages_json: str
    row_count: int | None
    size_bytes: int
    source_directory_size_bytes: int
    schema_fingerprints_json: str
    brightness_state_json: str
    correction_state_json: str
    translation_eligible: bool
    status: str
    rejection_reason: str | None
    duplicate_status: str
    duplicate_candidate_count: int
    source_provenance_json: str
    input_mode: str = "merged_parquet"
    corrected_product_json: str = "{}"
    target_products_json: str = "{}"
    qa_status: str = "missing"
    stage_qa_status_json: str = "{}"
    missing_products_json: str = "[]"
    analysis_eligibility_json: str = "{}"
    estimated_cache_bytes: int = 0
    cache_observations: str | None = None
    extraction_status: str = "not_required"
    analysis_profile: str = "translation"
    processing_completeness: str = "unknown"
    product_availability_json: str = "{}"
    exclusion_reason_codes_json: str = "[]"
    exclusion_context_json: str = "[]"


@dataclass(frozen=True)
class ExclusionRecord:
    """One deterministic, machine-readable bulk exclusion."""

    exclusion_id: str
    canonical_flightline_id: str | None
    source_path: str
    site: str | None
    acquisition_date: str | None
    analysis_profile: str
    product_role: str | None
    sensor_name: str | None
    offending_files_json: str
    reason_code: str
    detail: str
    processing_stage: str | None


@dataclass(frozen=True)
class BulkAnalysisPaths:
    """Canonical, isolated output paths for one bulk-analysis run."""

    output_dir: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_dir", Path(self.output_dir))

    @property
    def catalog_dir(self) -> Path:
        return self.output_dir / "catalog"

    @property
    def database_dir(self) -> Path:
        return self.output_dir / "database"

    @property
    def cache_dir(self) -> Path:
        return self.output_dir / "cache"

    @property
    def analyses_dir(self) -> Path:
        return self.output_dir / "analyses"

    @property
    def coefficients_dir(self) -> Path:
        return self.output_dir / "coefficients"

    @property
    def tables_dir(self) -> Path:
        return self.output_dir / "tables"

    @property
    def figures_dir(self) -> Path:
        return self.output_dir / "figures"

    @property
    def reports_dir(self) -> Path:
        return self.output_dir / "reports"

    @property
    def logs_dir(self) -> Path:
        return self.output_dir / "logs"

    @property
    def flightlines(self) -> Path:
        return self.catalog_dir / "flightlines.parquet"

    @property
    def source_files(self) -> Path:
        return self.catalog_dir / "source_files.parquet"

    @property
    def source_products(self) -> Path:
        return self.catalog_dir / "source_products.parquet"

    @property
    def duplicates(self) -> Path:
        return self.catalog_dir / "duplicates.parquet"

    @property
    def rejected_sources(self) -> Path:
        return self.catalog_dir / "rejected_sources.parquet"

    @property
    def exclusions(self) -> Path:
        return self.catalog_dir / "exclusions.parquet"

    @property
    def exclusions_json(self) -> Path:
        return self.catalog_dir / "exclusions.json"

    @property
    def exclusions_csv(self) -> Path:
        return self.catalog_dir / "exclusions.csv"

    @property
    def manifest(self) -> Path:
        return self.catalog_dir / "bulk_manifest.json"

    @property
    def database(self) -> Path:
        return self.database_dir / "spectralbridge_bulk.duckdb"

    @property
    def observations(self) -> Path:
        """Optional portable materialization; absent in the default mode."""

        return self.database_dir / "bulk_observations.parquet"

    @property
    def source_catalog(self) -> Path:
        """Compatibility alias for the source-file catalog."""

        return self.source_files

    @property
    def coefficients_parquet(self) -> Path:
        return self.coefficients_dir / "candidate_translation_coefficients.parquet"

    @property
    def coefficients_json(self) -> Path:
        return self.coefficients_dir / "candidate_translation_coefficients.json"

    def ensure_directories(self) -> None:
        for directory in (
            self.catalog_dir,
            self.cache_dir,
            self.database_dir,
            self.analyses_dir,
            self.coefficients_dir,
            self.tables_dir,
            self.figures_dir,
            self.reports_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


# Backward-compatible public name from the first bulk implementation.
BulkSource = SourceFileRecord


__all__ = [
    "BULK_SCHEMA_VERSION",
    "BulkAnalysisPaths",
    "BulkInputKind",
    "BulkInputMode",
    "BulkSource",
    "ExclusionRecord",
    "FlightlineRecord",
    "SourceFileRecord",
]
