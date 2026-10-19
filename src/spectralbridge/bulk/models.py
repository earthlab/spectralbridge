"""Data contracts for production bulk analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


BULK_SCHEMA_VERSION = 9
BulkInputKind = Literal["full", "polygon", "both"]
BulkInputMode = Literal["auto", "flightline_outputs", "merged_parquet"]


@dataclass(frozen=True)
class SourceFileRecord:
    """One source product discovered in the read-only input tree.

    Attributes
    ----------
    source_id : str
        Deterministic catalog key for this source, candidate directory or exclusion record; not a new ecological sampling unit.
    candidate_id : str
        Deterministic catalog key for this source, candidate directory or exclusion record; not a new ecological sampling unit.
    canonical_flightline_id : str | None
        Canonical scientific flightline identifier; histories from the same underlying flight must retain this identity.
    identity_source : str | None
        Parser or manifest provenance explaining how the scientific flightline identity was recovered.
    site : str | None
        Scientific site code recovered from the canonical identity or manifest, not an arbitrary outer directory name.
    acquisition_date : str | None
        ISO acquisition date associated with this scientific flightline; None indicates unavailable metadata.
    source_directory : str
        Authoritative local source directory; bulk consumers treat its completed products as immutable.
    source_path : str
        Backing input product path retained for traceability and restart checks.
    relative_path : str
        Source path relative to the catalog input root for portable provenance.
    input_kind : str
        Select eligible 'full', 'polygon', or 'both' table products; discovery still records companions for transparency.
    status : str
        Recorded stage-specific outcome or eligibility state; inspect reason/detail and the relevant workflow before interpreting it scientifically.
    reason : str | None
        Explicit reason for exclusion, failure or unavailable status; None when no reason applies.
    row_count : int | None
        Recorded table dimension; None means the dimension could not be established.
    column_count : int | None
        Recorded table dimension; None means the dimension could not be established.
    size_bytes : int
        Size or estimated storage requirement in bytes; estimates describe planned artifacts rather than guaranteed disk use.
    modified_time_ns : int
        Recorded filesystem modification timestamp in nanoseconds for source-change detection.
    schema_sha256 : str | None
        SHA-256 fingerprint of the recorded schema or source identity used for provenance/restart validation.
    available_sensors_json : str
        JSON-encoded available sensors retained in compact catalog rows; decode before inspecting nested fields.
    translation_eligible : bool
        Whether the recorded product satisfies the corresponding translation availability/eligibility or producer-to-bulk gate; does not certify empirical sensor calibration.
    product_role : str, default='merged_parquet'
        Scientific role of this product within the analysis profile, distinct from its storage format.
    sensor_name : str | None, default=None
        Canonical sensor identity used to match registered products and translation relationships.
    header_path : str | None, default=None
        Companion raster header path needed to interpret dimensions, wavelengths and georeferencing.
    dimensions_json : str, default='{}'
        JSON-encoded dimensions retained in compact catalog rows; decode before inspecting nested fields.
    source_signature_sha256 : str | None, default=None
        SHA-256 fingerprint of the recorded schema or source identity used for provenance/restart validation.
    qa_status : str | None, default=None
        Recorded QA classification; missing or not-evaluated status is not a pass.
    reason_code : str | None, default=None
        Machine-readable exclusion/review reason from the workflow vocabulary.
    matching_group : str | None, default=None
        Registry key declaring products that can be paired on common spatial/observational support.
    processing_stage : str | None, default=None
        Recorded processing lineage, such as raw, corrected or translated; stages are not silently interchangeable.
    wavelengths_json : str, default='[]'
        JSON-encoded wavelengths retained in compact catalog rows; decode before inspecting nested fields.
    dtype : str | None, default=None
        Recorded numerical storage dtype of the source product.
    product_key : str | None, default=None
        Unique registry key identifying this descriptor or translation relationship.
    storage_format : str | None, default=None
        Persisted representation such as raster or tabular storage, independent of scientific semantics.
    product_semantics : str | None, default=None
        Declared meaning of the product values and their role in the evidence chain.
    extraction_mode : str | None, default=None
        'full' writes pixel Parquet, 'polygon' requires polygons; None preserves the entry point's documented default extraction behavior.
    schema_json : str, default='[]'
        JSON-encoded schema retained in compact catalog rows; decode before inspecting nested fields.
    """

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
    product_key: str | None = None
    storage_format: str | None = None
    product_semantics: str | None = None
    extraction_mode: str | None = None
    schema_json: str = "[]"


@dataclass(frozen=True)
class FlightlineRecord:
    """Canonical scientific unit recovered from one source directory.

    Attributes
    ----------
    candidate_id : str
        Deterministic catalog key for this source, candidate directory or exclusion record; not a new ecological sampling unit.
    canonical_flightline_id : str | None
        Canonical scientific flightline identifier; histories from the same underlying flight must retain this identity.
    identity_source : str | None
        Parser or manifest provenance explaining how the scientific flightline identity was recovered.
    site : str | None
        Scientific site code recovered from the canonical identity or manifest, not an arbitrary outer directory name.
    acquisition_date : str | None
        ISO acquisition date associated with this scientific flightline; None indicates unavailable metadata.
    acquisition_year : int | None
        Calendar acquisition year used for inventory grouping and completeness checks.
    source_directory : str
        Authoritative local source directory; bulk consumers treat its completed products as immutable.
    canonical_merged_parquet : str | None
        Authoritative existing merged product path, or None when the corresponding full/polygon table is unavailable.
    polygon_merged_parquet : str | None
        Authoritative existing merged product path, or None when the corresponding full/polygon table is unavailable.
    selected_source_ids_json : str
        JSON-encoded selected source ids retained in compact catalog rows; decode before inspecting nested fields.
    selected_source_paths_json : str
        JSON-encoded selected source paths retained in compact catalog rows; decode before inspecting nested fields.
    qa_products_json : str
        JSON-encoded qa products retained in compact catalog rows; decode before inspecting nested fields.
    metadata_products_json : str
        JSON-encoded metadata products retained in compact catalog rows; decode before inspecting nested fields.
    available_sensors_json : str
        JSON-encoded available sensors retained in compact catalog rows; decode before inspecting nested fields.
    processing_stages_json : str
        JSON-encoded processing stages retained in compact catalog rows; decode before inspecting nested fields.
    row_count : int | None
        Recorded table dimension; None means the dimension could not be established.
    size_bytes : int
        Size or estimated storage requirement in bytes; estimates describe planned artifacts rather than guaranteed disk use.
    source_directory_size_bytes : int
        Size or estimated storage requirement in bytes; estimates describe planned artifacts rather than guaranteed disk use.
    schema_fingerprints_json : str
        JSON-encoded schema fingerprints retained in compact catalog rows; decode before inspecting nested fields.
    brightness_state_json : str
        JSON-encoded brightness state retained in compact catalog rows; decode before inspecting nested fields.
    correction_state_json : str
        JSON-encoded correction state retained in compact catalog rows; decode before inspecting nested fields.
    translation_eligible : bool
        Whether the recorded product satisfies the corresponding translation availability/eligibility or producer-to-bulk gate; does not certify empirical sensor calibration.
    status : str
        Recorded stage-specific outcome or eligibility state; inspect reason/detail and the relevant workflow before interpreting it scientifically.
    rejection_reason : str | None
        Explicit reason for exclusion, failure or unavailable status; None when no reason applies.
    duplicate_status : str
        Recorded stage-specific outcome or eligibility state; inspect reason/detail and the relevant workflow before interpreting it scientifically.
    duplicate_candidate_count : int
        Number of candidate directories sharing the canonical scientific flightline identity.
    source_provenance_json : str
        JSON-encoded source provenance retained in compact catalog rows; decode before inspecting nested fields.
    input_mode : str, default='merged_parquet'
        'auto' prefers completed flightline directories and falls back to merged Parquets; alternatives are 'flightline_outputs' and 'merged_parquet'.
    corrected_product_json : str, default='{}'
        JSON-encoded corrected product retained in compact catalog rows; decode before inspecting nested fields.
    target_products_json : str, default='{}'
        JSON-encoded target products retained in compact catalog rows; decode before inspecting nested fields.
    qa_status : str, default='missing'
        Recorded QA classification; missing or not-evaluated status is not a pass.
    stage_qa_status_json : str, default='{}'
        JSON-encoded stage qa status retained in compact catalog rows; decode before inspecting nested fields.
    missing_products_json : str, default='[]'
        JSON-encoded missing products retained in compact catalog rows; decode before inspecting nested fields.
    analysis_eligibility_json : str, default='{}'
        JSON-encoded analysis eligibility retained in compact catalog rows; decode before inspecting nested fields.
    estimated_cache_bytes : int, default=0
        Size or estimated storage requirement in bytes; estimates describe planned artifacts rather than guaranteed disk use.
    estimated_analysis_output_bytes : int, default=0
        Size or estimated storage requirement in bytes; estimates describe planned artifacts rather than guaranteed disk use.
    estimated_materialized_pixel_bytes : int, default=0
        Size or estimated storage requirement in bytes; estimates describe planned artifacts rather than guaranteed disk use.
    cache_observations : str | None, default=None
        Optional path to explicitly materialized pixel observations; absent from ordinary compact bulk analysis.
    extraction_status : str, default='not_required'
        Recorded stage-specific outcome or eligibility state; inspect reason/detail and the relevant workflow before interpreting it scientifically.
    analysis_profile : str, default='translation'
        Registered analysis profile name or AnalysisProfile controlling required products and permissible sensor pairs.
    processing_completeness : str, default='unknown'
        Recorded assessment of required product completeness under the selected analysis profile.
    product_availability_json : str, default='{}'
        JSON-encoded product availability retained in compact catalog rows; decode before inspecting nested fields.
    exclusion_reason_codes_json : str, default='[]'
        JSON-encoded exclusion reason codes retained in compact catalog rows; decode before inspecting nested fields.
    exclusion_context_json : str, default='[]'
        JSON-encoded exclusion context retained in compact catalog rows; decode before inspecting nested fields.
    translation_available : bool, default=False
        Whether the recorded product satisfies the corresponding translation availability/eligibility or producer-to-bulk gate; does not certify empirical sensor calibration.
    translation_availability_json : str, default='{}'
        JSON-encoded translation availability retained in compact catalog rows; decode before inspecting nested fields.
    scientific_status : str, default='not_evaluated'
        Recorded stage-specific outcome or eligibility state; inspect reason/detail and the relevant workflow before interpreting it scientifically.
    scientific_blockers_json : str, default='[]'
        JSON-encoded scientific blockers retained in compact catalog rows; decode before inspecting nested fields.
    """

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
    estimated_analysis_output_bytes: int = 0
    estimated_materialized_pixel_bytes: int = 0
    cache_observations: str | None = None
    extraction_status: str = "not_required"
    analysis_profile: str = "translation"
    processing_completeness: str = "unknown"
    product_availability_json: str = "{}"
    exclusion_reason_codes_json: str = "[]"
    exclusion_context_json: str = "[]"
    translation_available: bool = False
    translation_availability_json: str = "{}"
    scientific_status: str = "not_evaluated"
    scientific_blockers_json: str = "[]"


@dataclass(frozen=True)
class ExclusionRecord:
    """One deterministic, machine-readable bulk exclusion.

    Attributes
    ----------
    exclusion_id : str
        Deterministic catalog key for this source, candidate directory or exclusion record; not a new ecological sampling unit.
    canonical_flightline_id : str | None
        Canonical scientific flightline identifier; histories from the same underlying flight must retain this identity.
    source_path : str
        Backing input product path retained for traceability and restart checks.
    site : str | None
        Scientific site code recovered from the canonical identity or manifest, not an arbitrary outer directory name.
    acquisition_date : str | None
        ISO acquisition date associated with this scientific flightline; None indicates unavailable metadata.
    analysis_profile : str
        Registered analysis profile name or AnalysisProfile controlling required products and permissible sensor pairs.
    product_role : str | None
        Scientific role of this product within the analysis profile, distinct from its storage format.
    sensor_name : str | None
        Canonical sensor identity used to match registered products and translation relationships.
    offending_files_json : str
        JSON-encoded offending files retained in compact catalog rows; decode before inspecting nested fields.
    reason_code : str
        Machine-readable exclusion/review reason from the workflow vocabulary.
    detail : str
        Human-readable context supporting the exclusion or decision record.
    processing_stage : str | None
        Recorded processing lineage, such as raw, corrected or translated; stages are not silently interchangeable.
    """

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
    """Canonical, isolated output paths for one bulk-analysis run.

    Attributes
    ----------
    output_dir : Path
        Directory for generated products; bulk outputs must be outside the read-only input tree.
    """

    output_dir: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_dir", Path(self.output_dir))

    @property
    def catalog_dir(self) -> Path:
        """Resolve the canonical catalog dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'catalog'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "catalog"

    @property
    def database_dir(self) -> Path:
        """Resolve the canonical database dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'database'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "database"

    @property
    def cache_dir(self) -> Path:
        """Legacy pixel-materialization directory; unused by normal analysis."""

        return self.output_dir / "cache"

    @property
    def statistics_dir(self) -> Path:
        """Resolve the canonical statistics dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'statistics'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "statistics"

    @property
    def flightline_statistics_dir(self) -> Path:
        """Resolve the canonical flightline statistics dir location.

        Returns
        -------
        Path
            Path computed as ``self.statistics_dir / 'flightlines'``. Accessing this property does not create or validate the artifact.
        """

        return self.statistics_dir / "flightlines"

    @property
    def sufficient_statistics(self) -> Path:
        """Resolve the canonical sufficient statistics location.

        Returns
        -------
        Path
            Path computed as ``self.statistics_dir / 'translation_sufficient_statistics.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.statistics_dir / "translation_sufficient_statistics.parquet"

    @property
    def diagnostic_sample(self) -> Path:
        """Resolve the canonical diagnostic sample location.

        Returns
        -------
        Path
            Path computed as ``self.statistics_dir / 'diagnostic_sample.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.statistics_dir / "diagnostic_sample.parquet"

    @property
    def analyses_dir(self) -> Path:
        """Resolve the canonical analyses dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'analyses'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "analyses"

    @property
    def coefficients_dir(self) -> Path:
        """Resolve the canonical coefficients dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'coefficients'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "coefficients"

    @property
    def tables_dir(self) -> Path:
        """Resolve the canonical tables dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'tables'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "tables"

    @property
    def figures_dir(self) -> Path:
        """Resolve the canonical figures dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'figures'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "figures"

    @property
    def reports_dir(self) -> Path:
        """Resolve the canonical reports dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'reports'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "reports"

    @property
    def logs_dir(self) -> Path:
        """Resolve the canonical logs dir location.

        Returns
        -------
        Path
            Path computed as ``self.output_dir / 'logs'``. Accessing this property does not create or validate the artifact.
        """

        return self.output_dir / "logs"

    @property
    def flightlines(self) -> Path:
        """Resolve the canonical flightlines location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'flightlines.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "flightlines.parquet"

    @property
    def source_files(self) -> Path:
        """Resolve the canonical source files location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'source_files.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "source_files.parquet"

    @property
    def source_products(self) -> Path:
        """Resolve the canonical source products location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'source_products.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "source_products.parquet"

    @property
    def duplicates(self) -> Path:
        """Resolve the canonical duplicates location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'duplicates.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "duplicates.parquet"

    @property
    def rejected_sources(self) -> Path:
        """Resolve the canonical rejected sources location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'rejected_sources.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "rejected_sources.parquet"

    @property
    def exclusions(self) -> Path:
        """Resolve the canonical exclusions location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'exclusions.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "exclusions.parquet"

    @property
    def exclusions_json(self) -> Path:
        """Resolve the canonical exclusions json location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'exclusions.json'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "exclusions.json"

    @property
    def exclusions_csv(self) -> Path:
        """Resolve the canonical exclusions csv location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'exclusions.csv'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "exclusions.csv"

    @property
    def manifest(self) -> Path:
        """Resolve the canonical manifest location.

        Returns
        -------
        Path
            Path computed as ``self.catalog_dir / 'bulk_manifest.json'``. Accessing this property does not create or validate the artifact.
        """

        return self.catalog_dir / "bulk_manifest.json"

    @property
    def database(self) -> Path:
        """Resolve the canonical database location.

        Returns
        -------
        Path
            Path computed as ``self.database_dir / 'spectralbridge_bulk.duckdb'``. Accessing this property does not create or validate the artifact.
        """

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
        """Resolve the canonical coefficients parquet location.

        Returns
        -------
        Path
            Path computed as ``self.coefficients_dir / 'candidate_translation_coefficients.parquet'``. Accessing this property does not create or validate the artifact.
        """

        return self.coefficients_dir / "candidate_translation_coefficients.parquet"

    @property
    def coefficients_json(self) -> Path:
        """Resolve the canonical coefficients json location.

        Returns
        -------
        Path
            Path computed as ``self.coefficients_dir / 'candidate_translation_coefficients.json'``. Accessing this property does not create or validate the artifact.
        """

        return self.coefficients_dir / "candidate_translation_coefficients.json"

    @property
    def analysis_decisions(self) -> Path:
        """Resolve the canonical analysis decisions location.

        Returns
        -------
        Path
            Path computed as ``self.reports_dir / 'analysis_decisions.json'``. Accessing this property does not create or validate the artifact.
        """

        return self.reports_dir / "analysis_decisions.json"

    @property
    def campaign_summary(self) -> Path:
        """Resolve the canonical campaign summary location.

        Returns
        -------
        Path
            Path computed as ``self.reports_dir / 'campaign_summary.md'``. Accessing this property does not create or validate the artifact.
        """

        return self.reports_dir / "campaign_summary.md"

    def ensure_directories(self) -> None:
        """Create the canonical output directory hierarchy.

        Returns
        -------
        None
            No return value; validation raises on unsupported configuration and directory creation persists the canonical hierarchy.
        """

        for directory in (
            self.catalog_dir,
            self.statistics_dir,
            self.flightline_statistics_dir,
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
