"""Production-scale catalog, virtual dataset, and population analyses."""

from .analyses import (
    run_dataset_census,
    run_leave_one_site_out,
    run_sensor_translation,
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
from .registry import (
    AnalysisProfile,
    ProductDescriptor,
    ProductRegistry,
    TranslationPair,
)

__all__ = [
    "BULK_SCHEMA_VERSION",
    "BulkAnalysisPaths",
    "BulkInputKind",
    "BulkInputMode",
    "BulkSource",
    "ExclusionRecord",
    "FlightlineIdentity",
    "FlightlineIdentityParser",
    "FlightlineRecord",
    "SourceFileRecord",
    "AnalysisProfile",
    "ProductDescriptor",
    "ProductRegistry",
    "TranslationPair",
    "build_bulk_catalog",
    "canonical_identity_from_product",
    "discover_bulk_sources",
    "run_dataset_census",
    "run_leave_one_site_out",
    "run_sensor_translation",
]
