"""Production-scale catalog, virtual dataset, and population analyses."""

from .analyses import (
    run_dataset_census,
    run_leave_one_site_out,
    run_sensor_translation,
    run_spectral_library_analysis,
    SpectralLibraryPlotConfig,
    inspect_spectral_library,
    inspect_spectral_library_preflight,
)
from .catalog import build_bulk_catalog, canonical_identity_from_product, discover_bulk_sources
from .models import (
    BULK_SCHEMA_VERSION,
    BulkAnalysisPaths,
    BulkInputKind,
    BulkInputMode,
    BulkSource,
    ExclusionRecord,
    FlightlineRecord,
    SourceFileRecord,
)
from .identity import FlightlineIdentity, FlightlineIdentityParser
from .harmonized import build_harmonized_dataset
from .registry import (
    AnalysisProfile,
    ProductDescriptor,
    ProductRegistry,
    TranslationPair,
)
from .results import (
    BULK_RESULTS_SCHEMA_VERSION,
    BulkResultsConfig,
    BulkResultsPaths,
    summarize_bulk_results,
)

__all__ = [
    "BULK_SCHEMA_VERSION",
    "BULK_RESULTS_SCHEMA_VERSION",
    "BulkAnalysisPaths",
    "BulkInputKind",
    "BulkInputMode",
    "BulkSource",
    "BulkResultsConfig",
    "BulkResultsPaths",
    "ExclusionRecord",
    "FlightlineIdentity",
    "FlightlineIdentityParser",
    "FlightlineRecord",
    "SourceFileRecord",
    "AnalysisProfile",
    "ProductDescriptor",
    "ProductRegistry",
    "TranslationPair",
    "SpectralLibraryPlotConfig",
    "build_bulk_catalog",
    "build_harmonized_dataset",
    "canonical_identity_from_product",
    "discover_bulk_sources",
    "run_dataset_census",
    "run_leave_one_site_out",
    "run_sensor_translation",
    "inspect_spectral_library",
    "inspect_spectral_library_preflight",
    "run_spectral_library_analysis",
    "summarize_bulk_results",
]
