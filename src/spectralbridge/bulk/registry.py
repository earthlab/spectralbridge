"""Generic product, translation-pair, and analysis-profile contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Sequence

from spectralbridge.sensor_pairs import SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY


@dataclass(frozen=True)
class ProductDescriptor:
    """Recognize and describe one persisted raster-product convention."""

    key: str
    product_role: str
    filename_patterns: tuple[str, ...]
    sensor_name: str | None = None
    matching_group: str | None = None
    processing_stage: str | None = None
    expected_band_count: int | None = None
    header_required: bool = True
    include_undarkened: bool = False

    def matches(self, path: str | Path) -> bool:
        name = Path(path).name
        if Path(path).suffix.lower() != ".img":
            return False
        if not self.include_undarkened and "_undarkened_envi" in name.lower():
            return False
        return any(re.search(pattern, name, re.IGNORECASE) for pattern in self.filename_patterns)


@dataclass(frozen=True)
class TranslationPair:
    """A scientifically defined relationship between two sensor products."""

    key: str
    source_sensor: str
    target_sensor: str
    matching_group: str
    band_pairs: tuple[tuple[int, int], ...] = ()
    expected_source_bands: int | None = None
    expected_target_bands: int | None = None
    evidence_boundary: str | None = None


@dataclass(frozen=True)
class AnalysisProfile:
    """Product and integrity requirements for one bulk analysis."""

    name: str
    required_product_roles: tuple[str, ...] = ()
    optional_product_roles: tuple[str, ...] = (
        "raw_hyperspectral",
        "corrected_hyperspectral",
        "qa",
        "metadata",
    )
    allowed_sensors: tuple[str, ...] | None = None
    allowed_matching_groups: tuple[str, ...] | None = None
    require_translation_pair: bool = False
    require_qa: bool = False
    require_original_hyperspectral: bool = False
    require_corrected_hyperspectral: bool = False
    require_nonzero_files: bool = True
    require_readable_metadata: bool = True
    require_valid_dimensions: bool = True
    require_compatible_band_schema: bool = True


@dataclass(frozen=True)
class ProductRegistry:
    """Immutable registry used by discovery, extraction, and analysis."""

    products: tuple[ProductDescriptor, ...]
    translation_pairs: tuple[TranslationPair, ...]

    def recognize(self, path: str | Path) -> ProductDescriptor | None:
        matches = [descriptor for descriptor in self.products if descriptor.matches(path)]
        if len(matches) > 1:
            keys = ", ".join(descriptor.key for descriptor in matches)
            raise ValueError(f"product matches multiple descriptors ({keys}): {path}")
        return matches[0] if matches else None

    def product_for_sensor(self, sensor_name: str) -> ProductDescriptor | None:
        return next(
            (
                descriptor
                for descriptor in self.products
                if descriptor.sensor_name == sensor_name
            ),
            None,
        )

    def select_pairs(
        self,
        *,
        sensors: Sequence[str] | None = None,
        translation_pairs: Sequence[str | TranslationPair] | None = None,
        allowed_sensors: Sequence[str] | None = None,
        allowed_matching_groups: Sequence[str] | None = None,
        allow_empty: bool = False,
    ) -> tuple[TranslationPair, ...]:
        by_key = {pair.key: pair for pair in self.translation_pairs}
        if translation_pairs is not None:
            selected: list[TranslationPair] = []
            for value in translation_pairs:
                if isinstance(value, TranslationPair):
                    selected.append(value)
                else:
                    try:
                        selected.append(by_key[value])
                    except KeyError as exc:
                        raise ValueError(f"Unknown translation pair: {value}") from exc
        else:
            selected = list(self.translation_pairs)
        if sensors is not None:
            requested = set(sensors)
            selected = [
                pair
                for pair in selected
                if pair.source_sensor in requested and pair.target_sensor in requested
            ]
        if allowed_sensors is not None:
            allowed = set(allowed_sensors)
            selected = [
                pair
                for pair in selected
                if pair.source_sensor in allowed and pair.target_sensor in allowed
            ]
        if allowed_matching_groups is not None:
            allowed_groups = set(allowed_matching_groups)
            selected = [
                pair for pair in selected if pair.matching_group in allowed_groups
            ]
        if not selected and not allow_empty:
            raise ValueError("No translation pairs match the requested selection")
        return tuple(selected)


TRANSLATION_PROFILE = AnalysisProfile(
    name="translation",
    required_product_roles=("target_sensor",),
    require_translation_pair=True,
)

ANALYSIS_PROFILES = {TRANSLATION_PROFILE.name: TRANSLATION_PROFILE}


def resolve_analysis_profile(value: str | AnalysisProfile) -> AnalysisProfile:
    if isinstance(value, AnalysisProfile):
        return value
    try:
        return ANALYSIS_PROFILES[value]
    except KeyError as exc:
        raise ValueError(f"Unknown bulk analysis profile: {value}") from exc


_BUILTIN_PRODUCTS = (
    ProductDescriptor(
        key="raw_hyperspectral_envi",
        product_role="raw_hyperspectral",
        filename_patterns=(r"_reflectance_envi\.img$",),
        processing_stage="envi_export",
    ),
    ProductDescriptor(
        key="corrected_hyperspectral_envi",
        product_role="corrected_hyperspectral",
        filename_patterns=(r"_brdfandtopo_corrected_envi\.img$",),
        processing_stage="brdf_topographic_correction",
    ),
    ProductDescriptor(
        key="micasense_matched_oli",
        product_role="target_sensor",
        sensor_name="MicaSense_to-match_OLI_and_OLI-2",
        matching_group="oli_reflective",
        filename_patterns=(
            r"_micasense_to_match_oli_oli2_envi\.img$",
            r"_micasense-to-match_oli_and_oli-2(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        expected_band_count=6,
    ),
    ProductDescriptor(
        key="micasense_matched_tm_etm",
        product_role="target_sensor",
        sensor_name="MicaSense_to-match_TM_and_ETM+",
        matching_group="tm_etm_reflective",
        filename_patterns=(
            r"_micasense_to_match_tm_etm\+_envi\.img$",
            r"_micasense-to-match_tm_and_etm\+(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        expected_band_count=6,
    ),
    ProductDescriptor(
        key="landsat_9_oli2",
        product_role="target_sensor",
        sensor_name="Landsat_9_OLI-2",
        matching_group="oli_reflective",
        filename_patterns=(r"_landsat_oli2_envi\.img$", r"_landsat_9_oli-2(?:_envi)?\.img$"),
        processing_stage="spectral_convolution",
        expected_band_count=7,
    ),
    ProductDescriptor(
        key="landsat_8_oli",
        product_role="target_sensor",
        sensor_name="Landsat_8_OLI",
        matching_group="oli_reflective",
        filename_patterns=(r"_landsat_oli_envi\.img$", r"_landsat_8_oli(?:_envi)?\.img$"),
        processing_stage="spectral_convolution",
        expected_band_count=7,
    ),
    ProductDescriptor(
        key="landsat_7_etm",
        product_role="target_sensor",
        sensor_name="Landsat_7_ETM+",
        matching_group="tm_etm_reflective",
        filename_patterns=(r"_landsat_etm\+_envi\.img$", r"_landsat_7_etm\+(?:_envi)?\.img$"),
        processing_stage="spectral_convolution",
        expected_band_count=6,
    ),
    ProductDescriptor(
        key="landsat_5_tm",
        product_role="target_sensor",
        sensor_name="Landsat_5_TM",
        matching_group="tm_etm_reflective",
        filename_patterns=(r"_landsat_tm_envi\.img$", r"_landsat_5_tm(?:_envi)?\.img$"),
        processing_stage="spectral_convolution",
        expected_band_count=6,
    ),
)

_BUILTIN_PAIRS = tuple(
    TranslationPair(
        key=f"{source}__to__{target}",
        source_sensor=source,
        target_sensor=target,
        matching_group=group,
        # Preserve the package's current 1:1 band-index convention. Registries
        # may supply different explicit mappings for other product families.
        band_pairs=tuple((index, index) for index in range(1, 7)),
        expected_source_bands=6,
        expected_target_bands=7 if group == "oli_reflective" else 6,
        evidence_boundary=SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
    )
    for source, targets, group in (
        (
            "MicaSense_to-match_TM_and_ETM+",
            ("Landsat_5_TM", "Landsat_7_ETM+"),
            "tm_etm_reflective",
        ),
        (
            "MicaSense_to-match_OLI_and_OLI-2",
            ("Landsat_8_OLI", "Landsat_9_OLI-2"),
            "oli_reflective",
        ),
    )
    for target in targets
)

DEFAULT_PRODUCT_REGISTRY = ProductRegistry(
    products=_BUILTIN_PRODUCTS,
    translation_pairs=_BUILTIN_PAIRS,
)


__all__ = [
    "ANALYSIS_PROFILES",
    "DEFAULT_PRODUCT_REGISTRY",
    "TRANSLATION_PROFILE",
    "AnalysisProfile",
    "ProductDescriptor",
    "ProductRegistry",
    "TranslationPair",
    "resolve_analysis_profile",
]
