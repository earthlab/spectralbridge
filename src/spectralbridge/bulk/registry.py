"""Generic product, translation-pair, and analysis-profile contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Sequence

from spectralbridge.sensor_pairs import (
    SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
    wavelength_matched_band_pairs,
)


@dataclass(frozen=True)
class ProductDescriptor:
    """Recognize and describe one persisted raster-product convention.

    Attributes
    ----------
    key : str
        Unique registry key identifying this descriptor or translation relationship.
    product_role : str
        Scientific role of this product within the analysis profile, distinct from its storage format.
    filename_patterns : tuple[str, ...]
        Recognized canonical filename glob patterns; matching does not alone establish scientific eligibility.
    sensor_name : str | None, default=None
        Canonical sensor identity used to match registered products and translation relationships.
    matching_group : str | None, default=None
        Registry key declaring products that can be paired on common spatial/observational support.
    processing_stage : str | None, default=None
        Recorded processing lineage, such as raw, corrected or translated; stages are not silently interchangeable.
    product_semantics : str | None, default=None
        Declared meaning of the product values and their role in the evidence chain.
    extraction_mode : str | None, default=None
        'full' writes pixel Parquet, 'polygon' requires polygons; None preserves the entry point's documented default extraction behavior.
    expected_band_count : int | None, default=None
        Required number of spectral bands under this descriptor; metadata and actual products are validated separately.
    header_required : bool, default=True
        Require a companion raster header for this product descriptor.
    include_undarkened : bool, default=False
        Include the matching undarkened product convention when recognizing these filenames.
    """

    key: str
    product_role: str
    filename_patterns: tuple[str, ...]
    sensor_name: str | None = None
    matching_group: str | None = None
    processing_stage: str | None = None
    product_semantics: str | None = None
    extraction_mode: str | None = None
    expected_band_count: int | None = None
    header_required: bool = True
    include_undarkened: bool = False

    def matches(self, path: str | Path) -> bool:
        """Check whether the filename matches this registered product convention.

        Parameters
        ----------
        path : str | Path
            Existing source path to match against registered canonical filename patterns.

        Returns
        -------
        bool
            Whether the recorded state satisfies this method's predicate; no source processing is performed.
        """

        name = Path(path).name
        if Path(path).suffix.lower() != ".img":
            return False
        if not self.include_undarkened and "_undarkened_envi" in name.lower():
            return False
        return any(re.search(pattern, name, re.IGNORECASE) for pattern in self.filename_patterns)


@dataclass(frozen=True)
class TabularProductDescriptor:
    """Recognize one canonical per-flight tabular product convention.

    Tabular products are catalog inputs, not implicit regression inputs.  The
    descriptor keeps storage layout separate from the raster relationship used
    by the bounded statistics reader.

    Attributes
    ----------
    key : str
        Unique registry key identifying this descriptor or translation relationship.
    product_role : str
        Scientific role of this product within the analysis profile, distinct from its storage format.
    filename_patterns : tuple[str, ...]
        Recognized canonical filename glob patterns; matching does not alone establish scientific eligibility.
    sensor_name : str | None, default=None
        Canonical sensor identity used to match registered products and translation relationships.
    processing_stage : str | None, default=None
        Recorded processing lineage, such as raw, corrected or translated; stages are not silently interchangeable.
    product_semantics : str | None, default=None
        Declared meaning of the product values and their role in the evidence chain.
    extraction_mode : str | None, default=None
        'full' writes pixel Parquet, 'polygon' requires polygons; None preserves the entry point's documented default extraction behavior.
    expected_spectral_band_count : int | None, default=None
        Required number of spectral bands under this descriptor; metadata and actual products are validated separately.
    required_columns : tuple[str, ...], default=()
        Required tabular column names for metadata validation; not a request to materialize all observation rows.
    """

    key: str
    product_role: str
    filename_patterns: tuple[str, ...]
    sensor_name: str | None = None
    processing_stage: str | None = None
    product_semantics: str | None = None
    extraction_mode: str | None = None
    expected_spectral_band_count: int | None = None
    required_columns: tuple[str, ...] = ()

    def matches(self, path: str | Path) -> bool:
        """Check whether the filename matches this registered product convention.

        Parameters
        ----------
        path : str | Path
            Existing source path to match against registered canonical filename patterns.

        Returns
        -------
        bool
            Whether the recorded state satisfies this method's predicate; no source processing is performed.
        """

        name = Path(path).name
        if Path(path).suffix.lower() != ".parquet":
            return False
        return any(re.search(pattern, name, re.IGNORECASE) for pattern in self.filename_patterns)


@dataclass(frozen=True)
class TranslationPair:
    """A scientifically defined relationship between two sensor products.

    Attributes
    ----------
    key : str
        Unique registry key identifying this descriptor or translation relationship.
    source_sensor : str
        Canonical sensor identity used to match registered products and translation relationships.
    target_sensor : str
        Canonical target sensor key present in the reviewed drone coefficient registry.
    matching_group : str
        Registry key declaring products that can be paired on common spatial/observational support.
    band_pairs : tuple[tuple[int, int], ...], default=()
        Explicit source/target band relationships in the registry convention; preserve their declared index convention.
    expected_source_bands : int | None, default=None
        Declared source/target band-count contract for this registered translation relationship.
    expected_target_bands : int | None, default=None
        Declared source/target band-count contract for this registered translation relationship.
    compatible_target_band_counts : tuple[int, ...], default=()
        Declared source/target band-count contract for this registered translation relationship.
    evidence_boundary : str | None, default=None
        Scientific limitation attached to this relationship; common-source synthetic products do not become independent calibration observations.
    """

    key: str
    source_sensor: str
    target_sensor: str
    matching_group: str
    band_pairs: tuple[tuple[int, int], ...] = ()
    expected_source_bands: int | None = None
    expected_target_bands: int | None = None
    compatible_target_band_counts: tuple[int, ...] = ()
    evidence_boundary: str | None = None


@dataclass(frozen=True)
class AnalysisProfile:
    """Product and integrity requirements for one bulk analysis.

    Attributes
    ----------
    name : str
        Stable parser/profile identifier used in configuration and provenance.
    required_product_roles : tuple[str, ...], default=()
        Product roles required or additionally recognized by this analysis profile.
    optional_product_roles : tuple[str, ...], default=('raw_hyperspectral', 'corrected_hyperspectral', 'qa', 'metadata')
        Product roles required or additionally recognized by this analysis profile.
    allowed_sensors : tuple[str, ...] | None, default=None
        Optional registry restrictions on sensor identities or common-support matching groups.
    allowed_matching_groups : tuple[str, ...] | None, default=None
        Optional registry restrictions on sensor identities or common-support matching groups.
    require_translation_pair : bool, default=False
        Require at least one compatible registered translation relationship for eligibility.
    require_qa : bool, default=False
        Require the profile's QA artifacts during source validation.
    require_original_hyperspectral : bool, default=False
        Require the corresponding original/corrected hyperspectral source role for this profile.
    require_corrected_hyperspectral : bool, default=False
        Require the corresponding original/corrected hyperspectral source role for this profile.
    require_nonzero_files : bool, default=True
        Reject zero-byte product artifacts during completeness validation.
    require_readable_metadata : bool, default=True
        Require metadata to be readable before admitting a candidate.
    require_valid_dimensions : bool, default=True
        Require compatible positive raster dimensions during validation.
    require_compatible_band_schema : bool, default=True
        Require product band metadata to satisfy the selected relationship contract.
    """

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
    """Immutable registry used by discovery, extraction, and analysis.

    Attributes
    ----------
    products : tuple[ProductDescriptor, ...]
        Immutable collection of raster/tabular descriptors recognized by this registry.
    translation_pairs : tuple[TranslationPair, ...]
        Explicit registered source-to-target relationships to analyze; None uses the selected registry/profile defaults.
    tabular_products : tuple[TabularProductDescriptor, ...], default=()
        Immutable collection of raster/tabular descriptors recognized by this registry.
    """

    products: tuple[ProductDescriptor, ...]
    translation_pairs: tuple[TranslationPair, ...]
    tabular_products: tuple[TabularProductDescriptor, ...] = ()

    def recognize(self, path: str | Path) -> ProductDescriptor | None:
        """Return the raster descriptor matching this product filename.

        Parameters
        ----------
        path : str | Path
            Existing source path to match against registered canonical filename patterns.

        Returns
        -------
        ProductDescriptor | None
            Matching raster ProductDescriptor, or None when no filename convention matches.
        """

        matches = [descriptor for descriptor in self.products if descriptor.matches(path)]
        if len(matches) > 1:
            keys = ", ".join(descriptor.key for descriptor in matches)
            raise ValueError(f"product matches multiple descriptors ({keys}): {path}")
        return matches[0] if matches else None

    def product_for_sensor(self, sensor_name: str) -> ProductDescriptor | None:
        """Return the registered raster descriptor for a sensor identity.

        Parameters
        ----------
        sensor_name : str
            Canonical sensor identity used to match registered products and translation relationships.

        Returns
        -------
        ProductDescriptor | None
            ProductDescriptor for the requested canonical sensor name, or None when no descriptor exists.
        """

        return next(
            (
                descriptor
                for descriptor in self.products
                if descriptor.sensor_name == sensor_name
            ),
            None,
        )

    def recognize_tabular(self, path: str | Path) -> TabularProductDescriptor | None:
        """Return the tabular descriptor matching this product filename.

        Parameters
        ----------
        path : str | Path
            Existing source path to match against registered canonical filename patterns.

        Returns
        -------
        TabularProductDescriptor | None
            Matching TabularProductDescriptor, or None when no tabular filename convention matches.
        """

        matches = [
            descriptor for descriptor in self.tabular_products if descriptor.matches(path)
        ]
        if len(matches) > 1:
            keys = ", ".join(descriptor.key for descriptor in matches)
            raise ValueError(
                f"tabular product matches multiple descriptors ({keys}): {path}"
            )
        return matches[0] if matches else None

    def select_pairs(
        self,
        *,
        sensors: Sequence[str] | None = None,
        translation_pairs: Sequence[str | TranslationPair] | None = None,
        allowed_sensors: Sequence[str] | None = None,
        allowed_matching_groups: Sequence[str] | None = None,
        allow_empty: bool = False,
    ) -> tuple[TranslationPair, ...]:
        """Resolve and validate the requested registered sensor relationships.

        Parameters
        ----------
        sensors : Sequence[str] | None
            Optional sensor-name selection passed to the product registry; None retains profile-compatible sensors.
        translation_pairs : Sequence[str | TranslationPair] | None
            Explicit registered source-to-target relationships to analyze; None uses the selected registry/profile defaults.
        allowed_sensors : Sequence[str] | None
            Optional registry restrictions on sensor identities or common-support matching groups.
        allowed_matching_groups : Sequence[str] | None
            Optional registry restrictions on sensor identities or common-support matching groups.
        allow_empty : bool
            Allow an empty relationship selection rather than raising an error.

        Returns
        -------
        tuple[TranslationPair, ...]
            Ordered tuple of compatible TranslationPair records selected from this registry.

        Raises
        ------
        ValueError
            If option values violate the configuration or relationship-selection contract.
        """

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
    """Resolve a registered profile name or retain an explicit AnalysisProfile; reject unknown names."""

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
        product_semantics="raw_hyperspectral_observation",
    ),
    ProductDescriptor(
        key="corrected_hyperspectral_envi",
        product_role="corrected_hyperspectral",
        filename_patterns=(r"_brdfandtopo_corrected_envi\.img$",),
        processing_stage="brdf_topographic_correction",
        product_semantics="corrected_hyperspectral_observation",
    ),
    ProductDescriptor(
        key="micasense_matched_oli",
        product_role="target_sensor",
        sensor_name="MicaSense_to-match_OLI_and_OLI-2",
        matching_group="oli_reflective",
        filename_patterns=(
            r"(?<!_)_micasense_to_match_oli_oli2_envi\.img$",
            r"_micasense-to-match_oli_and_oli-2(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        product_semantics="synthetic_convolution",
        expected_band_count=5,
    ),
    ProductDescriptor(
        key="micasense_matched_tm_etm",
        product_role="target_sensor",
        sensor_name="MicaSense_to-match_TM_and_ETM+",
        matching_group="tm_etm_reflective",
        filename_patterns=(
            r"(?<!_)_micasense_to_match_tm_etm\+_envi\.img$",
            r"_micasense-to-match_tm_and_etm\+(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        product_semantics="synthetic_convolution",
        expected_band_count=4,
    ),
    ProductDescriptor(
        key="landsat_9_oli2",
        product_role="target_sensor",
        sensor_name="Landsat_9_OLI-2",
        matching_group="oli_reflective",
        filename_patterns=(
            r"(?<!_)_landsat_oli2_envi\.img$",
            r"_landsat_9_oli-2(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        product_semantics="synthetic_convolution",
        expected_band_count=7,
    ),
    ProductDescriptor(
        key="landsat_8_oli",
        product_role="target_sensor",
        sensor_name="Landsat_8_OLI",
        matching_group="oli_reflective",
        filename_patterns=(
            r"(?<!_)_landsat_oli_envi\.img$",
            r"_landsat_8_oli(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        product_semantics="synthetic_convolution",
        expected_band_count=7,
    ),
    ProductDescriptor(
        key="landsat_7_etm",
        product_role="target_sensor",
        sensor_name="Landsat_7_ETM+",
        matching_group="tm_etm_reflective",
        filename_patterns=(
            r"(?<!_)_landsat_etm\+_envi\.img$",
            r"_landsat_7_etm\+(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        product_semantics="synthetic_convolution",
        expected_band_count=6,
    ),
    ProductDescriptor(
        key="landsat_5_tm",
        product_role="target_sensor",
        sensor_name="Landsat_5_TM",
        matching_group="tm_etm_reflective",
        filename_patterns=(
            r"(?<!_)_landsat_tm_envi\.img$",
            r"_landsat_5_tm(?:_envi)?\.img$",
        ),
        processing_stage="spectral_convolution",
        product_semantics="synthetic_convolution",
        expected_band_count=6,
    ),
    ProductDescriptor(
        key="drone_micasense_matched_oli",
        product_role="target_sensor",
        sensor_name="MicaSense_to-match_OLI_and_OLI-2",
        matching_group="oli_reflective",
        filename_patterns=(r"__micasense_to_match_oli_oli2_envi\.img$",),
        processing_stage="affine_cross_sensor_translation_input",
        product_semantics="matched_native_application_input",
        expected_band_count=5,
    ),
    ProductDescriptor(
        key="drone_micasense_matched_tm_etm",
        product_role="target_sensor",
        sensor_name="MicaSense_to-match_TM_and_ETM+",
        matching_group="tm_etm_reflective",
        filename_patterns=(r"__micasense_to_match_tm_etm\+_envi\.img$",),
        processing_stage="affine_cross_sensor_translation_input",
        product_semantics="matched_native_application_input",
        expected_band_count=4,
    ),
    ProductDescriptor(
        key="drone_landsat_like_9_oli2",
        product_role="target_sensor",
        sensor_name="Landsat_9_OLI-2",
        matching_group="oli_reflective",
        filename_patterns=(r"__landsat_like_landsat_oli2_translated_envi\.img$",),
        processing_stage="affine_cross_sensor_translation",
        product_semantics="landsat_like_translated",
        expected_band_count=5,
    ),
    ProductDescriptor(
        key="drone_landsat_like_8_oli",
        product_role="target_sensor",
        sensor_name="Landsat_8_OLI",
        matching_group="oli_reflective",
        filename_patterns=(r"__landsat_like_landsat_oli_translated_envi\.img$",),
        processing_stage="affine_cross_sensor_translation",
        product_semantics="landsat_like_translated",
        expected_band_count=5,
    ),
    ProductDescriptor(
        key="drone_landsat_like_7_etm",
        product_role="target_sensor",
        sensor_name="Landsat_7_ETM+",
        matching_group="tm_etm_reflective",
        filename_patterns=(r"__landsat_like_landsat_etm\+_translated_envi\.img$",),
        processing_stage="affine_cross_sensor_translation",
        product_semantics="landsat_like_translated",
        expected_band_count=4,
    ),
    ProductDescriptor(
        key="drone_landsat_like_5_tm",
        product_role="target_sensor",
        sensor_name="Landsat_5_TM",
        matching_group="tm_etm_reflective",
        filename_patterns=(r"__landsat_like_landsat_tm_translated_envi\.img$",),
        processing_stage="affine_cross_sensor_translation",
        product_semantics="landsat_like_translated",
        expected_band_count=4,
    ),
)

_BUILTIN_PAIRS = tuple(
    TranslationPair(
        key=f"{source}__to__{target}",
        source_sensor=source,
        target_sensor=target,
        matching_group=group,
        # Band numbers are sensor-local. Resolve shared spectral identities
        # against the packaged center wavelengths and passbands instead of
        # assuming equal band numbers across instruments.
        band_pairs=wavelength_matched_band_pairs(source, target),
        expected_source_bands=source_bands,
        expected_target_bands=7 if group == "oli_reflective" else 6,
        compatible_target_band_counts=(
            source_bands,
            7 if group == "oli_reflective" else 6,
        ),
        evidence_boundary=SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
    )
    for source, targets, group, source_bands in (
        (
            "MicaSense_to-match_TM_and_ETM+",
            ("Landsat_5_TM", "Landsat_7_ETM+"),
            "tm_etm_reflective",
            4,
        ),
        (
            "MicaSense_to-match_OLI_and_OLI-2",
            ("Landsat_8_OLI", "Landsat_9_OLI-2"),
            "oli_reflective",
            5,
        ),
    )
    for target in targets
)


_DRONE_TRANSLATED_TABLES = tuple(
    descriptor
    for sensor, slug in (
        ("Landsat_5_TM", r"landsat_tm"),
        ("Landsat_7_ETM+", r"landsat_etm\+"),
        ("Landsat_8_OLI", r"landsat_oli"),
        ("Landsat_9_OLI-2", r"landsat_oli2"),
    )
    for descriptor in (
        TabularProductDescriptor(
            key=f"drone_{sensor.lower().replace('+', 'plus').replace('-', '_')}_full",
            product_role="translated_tabular",
            sensor_name=sensor,
            filename_patterns=(
                rf"__landsat_like_{slug}_translated_envi\.parquet$",
            ),
            processing_stage="affine_cross_sensor_translation",
            product_semantics="landsat_like_translated",
            extraction_mode="full",
            expected_spectral_band_count=(
                5 if sensor in {"Landsat_8_OLI", "Landsat_9_OLI-2"} else 4
            ),
            required_columns=(
                "pixel_id",
                "translated_product_semantics",
                "translation_pair",
                "translation_source_sensor",
                "translation_target_sensor",
                "translation_coefficient_sha256",
                "translation_evidence_boundary",
            ),
        ),
        TabularProductDescriptor(
            key=f"drone_{sensor.lower().replace('+', 'plus').replace('-', '_')}_polygon",
            product_role="translated_tabular",
            sensor_name=sensor,
            filename_patterns=(
                rf"__landsat_like_{slug}_translated_envi__polygons\.parquet$",
            ),
            processing_stage="affine_cross_sensor_translation",
            product_semantics="landsat_like_translated",
            extraction_mode="polygon",
            expected_spectral_band_count=(
                5 if sensor in {"Landsat_8_OLI", "Landsat_9_OLI-2"} else 4
            ),
            required_columns=(
                "pixel_id",
                "translated_product_semantics",
                "translation_pair",
                "translation_source_sensor",
                "translation_target_sensor",
                "translation_coefficient_sha256",
                "translation_evidence_boundary",
            ),
        ),
    )
)


_BUILTIN_TABULAR_PRODUCTS = (
    TabularProductDescriptor(
        key="drone_corrected_native_full",
        product_role="native_corrected_tabular",
        filename_patterns=(r"__(?!landsat_like_)[^/]*full\.parquet$",),
        sensor_name="MicaSense_native_corrected",
        processing_stage="tabular_extraction",
        product_semantics="native_corrected_observation",
        extraction_mode="full",
    ),
    TabularProductDescriptor(
        key="drone_corrected_native_polygon",
        product_role="native_corrected_tabular",
        filename_patterns=(r"(?<!translated_envi)__polygons\.parquet$",),
        sensor_name="MicaSense_native_corrected",
        processing_stage="polygon_extraction",
        product_semantics="native_corrected_observation",
        extraction_mode="polygon",
    ),
    TabularProductDescriptor(
        key="drone_polygon_index",
        product_role="auxiliary_tabular",
        filename_patterns=(r"__polygon_index\.parquet$",),
        processing_stage="polygon_index",
        product_semantics="spatial_index",
        extraction_mode="polygon",
    ),
    TabularProductDescriptor(
        key="drone_landsat_like_combined",
        product_role="combined_translated_tabular",
        filename_patterns=(
            r"__landsat_like_(?:combined|merged)(?:_envi)?(?:__polygons)?\.parquet$",
        ),
        processing_stage="tabular_combination",
        product_semantics="landsat_like_translated_collection",
    ),
    *_DRONE_TRANSLATED_TABLES,
)

DEFAULT_PRODUCT_REGISTRY = ProductRegistry(
    products=_BUILTIN_PRODUCTS,
    translation_pairs=_BUILTIN_PAIRS,
    tabular_products=_BUILTIN_TABULAR_PRODUCTS,
)


__all__ = [
    "ANALYSIS_PROFILES",
    "DEFAULT_PRODUCT_REGISTRY",
    "TRANSLATION_PROFILE",
    "AnalysisProfile",
    "ProductDescriptor",
    "ProductRegistry",
    "TabularProductDescriptor",
    "TranslationPair",
    "resolve_analysis_profile",
]
