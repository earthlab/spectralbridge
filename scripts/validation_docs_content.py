"""Structured explanatory content for generated validation documentation.

Campaign JSON remains the source of observed values and statuses. This module
contains only the human interpretation needed to explain those observations.
Keeping prose here makes generated pages reproducible and lets tests detect a
new validation field that has not yet been documented.
"""

from __future__ import annotations

from dataclasses import dataclass


REAL_RUN = "artifacts/r10c-l002-20210915"


@dataclass(frozen=True)
class FieldGuide:
    """Meaning of one recorded input or diagnostic field."""

    name: str
    meaning: str


@dataclass(frozen=True)
class CheckGuide:
    """Interpretation contract for one Boolean or status check."""

    name: str
    question: str
    pass_condition: str
    review_if_not_pass: str


@dataclass(frozen=True)
class ImageGuide:
    """One checked-in real-run figure used as documentation evidence."""

    path: str
    alt: str
    caption: str


@dataclass(frozen=True)
class ModuleGuide:
    """Publication-facing explanation of one offline validation module."""

    purpose: str
    implementation: str
    inputs: tuple[FieldGuide, ...]
    checks: tuple[CheckGuide, ...]
    diagnostics: tuple[FieldGuide, ...]
    establishes: str
    does_not_establish: str
    stage_qa_link: str
    images: tuple[ImageGuide, ...]


MODULE_GUIDES: dict[str, ModuleGuide] = {
    "neon_download": ModuleGuide(
        purpose=(
            "Exercise the restart-safe acquisition contract: a valid local HDF5 "
            "must be discovered at its canonical path and reused without a network request."
        ),
        implementation="`stage_download_h5` in `spectralbridge.pipelines.pipeline`",
        inputs=(
            FieldGuide("domain", "NEON domain encoded in the flightline identity."),
            FieldGuide(
                "site_code", "Site code varied across representative NEON domains."
            ),
            FieldGuide(
                "year_month", "Acquisition month used by the download interface."
            ),
        ),
        checks=(
            CheckGuide(
                "canonical_path_returned",
                "Did discovery return the exact expected HDF5 path?",
                "The returned path equals the pre-created canonical artifact path.",
                "Inspect flightline naming, base-folder selection, and path helpers.",
            ),
            CheckGuide(
                "nonempty_h5_reused",
                "Was an existing non-empty source reused byte-for-byte?",
                "Modification time and SHA-256 are unchanged and no network call occurs.",
                "Treat a rewrite or attempted download as a restart-safety regression.",
            ),
        ),
        diagnostics=(
            FieldGuide(
                "artifact_reused_unchanged", "Combined timestamp/hash reuse result."
            ),
            FieldGuide(
                "network_contacted", "Whether this offline case contacted NEON."
            ),
            FieldGuide(
                "output_bytes", "Persisted source size; zero bytes are invalid."
            ),
            FieldGuide("sha256", "Full-file digest used by the small offline fixture."),
        ),
        establishes="Local discovery and reuse behavior across several site/date identities.",
        does_not_establish=(
            "NEON authentication, API availability, retry behavior, or transfer integrity over the network."
        ),
        stage_qa_link="stage-qa-guide.md#acquisition",
        images=(
            ImageGuide(
                f"{REAL_RUN}/qa/stages/00_acquisition/overview.png",
                "R10C acquisition artifact inventory",
                "The real R10C acquisition stage records the 2.4 GB HDF5 and embeds site, domain, flightline, and date in the figure.",
            ),
        ),
    ),
    "h5_to_envi": ModuleGuide(
        purpose=(
            "Verify that a NEON-layout HDF5 reflectance cube becomes a band-sequential "
            "float32 ENVI image with matching dimensions, values, and a readable header."
        ),
        implementation="`neon_to_envi_no_hytools` and `EnviWriter`",
        inputs=(
            FieldGuide(
                "shape_y_x_b", "Varies lines, samples, and spectral band count."
            ),
            FieldGuide(
                "brightness_offset", "Exercises zero and small explicit export offsets."
            ),
            FieldGuide("site_code", "Varies realistic flightline naming metadata."),
        ),
        checks=(
            CheckGuide(
                "shape_preserved",
                "Did conversion preserve lines, samples, and bands?",
                "The reconstructed ENVI array has the same Y×X×band shape as the source.",
                "Inspect axis order, header dimensions, and BSQ serialization.",
            ),
            CheckGuide(
                "float32_bsq_values_preserved",
                "Do stored values match an independent expected array?",
                "Maximum absolute error is at most `1e-7` after applying the configured offset.",
                "Inspect scaling, axis transposition, datatype, and chunk writes.",
            ),
            CheckGuide(
                "header_written",
                "Was a non-empty ENVI header produced?",
                "The `.hdr` exists and contains bytes.",
                "Do not run downstream correction until dimensions and metadata parse correctly.",
            ),
        ),
        diagnostics=(
            FieldGuide("shape", "Observed ENVI shape after independent read-back."),
            FieldGuide(
                "max_absolute_error", "Largest source-versus-output value difference."
            ),
            FieldGuide(
                "output_bytes", "ENVI image size used to catch incomplete writes."
            ),
            FieldGuide(
                "header_bytes", "Header size used as a minimal persistence check."
            ),
        ),
        establishes="Small-cube axis, datatype, value, and header contracts.",
        does_not_establish=(
            "Performance on full flightlines or completeness of every provider-specific HDF5 metadata field."
        ),
        stage_qa_link="stage-qa-guide.md#input-reflectance",
        images=(
            ImageGuide(
                f"{REAL_RUN}/qa/stages/01_input_data/overview.png",
                "R10C input reflectance overview",
                "The real exported ENVI is reviewed spatially and spectrally after scale and NoData metadata are applied.",
            ),
        ),
    ),
    "topographic_correction": ModuleGuide(
        purpose=(
            "Apply SCS+C to controlled synthetic terrain and confirm that correction "
            "reduces the injected reflectance relationship with illumination geometry."
        ),
        implementation="`calc_cosine_i` and `apply_topo_correct`",
        inputs=(
            FieldGuide(
                "slope_max_degrees", "Varies terrain from gentle to steeper slopes."
            ),
            FieldGuide(
                "scale_factor", "Alternates unit reflectance and 10,000-scaled storage."
            ),
            FieldGuide("shape_y_x_b", "Varies spatial dimensions and band count."),
        ),
        checks=(
            CheckGuide(
                "shape_preserved",
                "Does correction retain the cube shape?",
                "Corrected and input arrays have identical dimensions.",
                "Inspect band/spatial axis handling and tile assembly.",
            ),
            CheckGuide(
                "all_values_finite",
                "Did valid synthetic support remain numerically defined?",
                "All corrected values are finite for this no-NoData fixture.",
                "Inspect divisions, invalid geometry, and correction-factor bounds.",
            ),
            CheckGuide(
                "terrain_correlation_reduced",
                "Did SCS+C reduce the deliberately injected illumination dependence?",
                "Absolute correlation with cosine incidence is lower after correction.",
                "Review coefficients and geometry; this check is directional, not an accuracy threshold.",
            ),
        ),
        diagnostics=(
            FieldGuide(
                "incidence_correlation_before",
                "Absolute pre-correction geometry correlation.",
            ),
            FieldGuide(
                "incidence_correlation_after",
                "Absolute post-correction geometry correlation.",
            ),
            FieldGuide("correlation_reduction", "Before minus after correlation."),
            FieldGuide("finite_percent", "Percent of corrected cells that are finite."),
            FieldGuide(
                "mean_absolute_change",
                "Average correction magnitude in unit reflectance.",
            ),
        ),
        establishes="Numerical shape, scaling, finite-value, and directional decorrelation behavior.",
        does_not_establish="Ecological signal preservation or optimal correction on real terrain.",
        stage_qa_link="stage-qa-guide.md#brdf-and-topographic-correction",
        images=(
            ImageGuide(
                f"{REAL_RUN}/qa/stages/03_brdf_topographic_correction/overview.png",
                "R10C before and after correction overview",
                "Matched maps and spectra show the combined persisted BRDF/topographic result; the pipeline does not store a topo-only intermediate.",
            ),
        ),
    ),
    "brdf_correction": ModuleGuide(
        purpose=(
            "Use a neutral BRDF model as an identity contract across view angles, "
            "storage scales, cube sizes, and band counts."
        ),
        implementation="`apply_brdf_correct`",
        inputs=(
            FieldGuide(
                "view_zenith_degrees", "Varies view geometry from nadir to 28°."
            ),
            FieldGuide(
                "scale_factor", "Alternates unit and scaled reflectance storage."
            ),
            FieldGuide("shape_y_x_b", "Varies spatial dimensions and band count."),
        ),
        checks=(
            CheckGuide(
                "shape_preserved",
                "Does BRDF application retain the cube shape?",
                "Output and input dimensions match exactly.",
                "Inspect band axis and tile assembly.",
            ),
            CheckGuide(
                "neutral_model_is_identity",
                "Does an iso=1, vol=0, geo=0 model leave reflectance unchanged?",
                "Input and output agree within `1e-5` stored units.",
                "Any drift indicates a kernel, scaling, or factor-application regression.",
            ),
            CheckGuide(
                "dtype_preserved",
                "Does correction retain the float32 output contract?",
                "The output dtype is float32.",
                "Review memory allocation and NumPy promotion before accepting larger files.",
            ),
        ),
        diagnostics=(
            FieldGuide(
                "max_absolute_error_stored_units", "Largest identity-model difference."
            ),
            FieldGuide(
                "finite_percent", "Percent of numerically defined corrected values."
            ),
            FieldGuide(
                "output_min_unitless",
                "Minimum output after conversion to unit reflectance.",
            ),
            FieldGuide(
                "output_max_unitless",
                "Maximum output after conversion to unit reflectance.",
            ),
        ),
        establishes="Neutral-model invariance and basic numerical stability.",
        does_not_establish="Accuracy of fitted BRDF coefficients for real angular sampling.",
        stage_qa_link="stage-qa-guide.md#correction-parameters",
        images=(
            ImageGuide(
                f"{REAL_RUN}/qa/stages/02_correction_parameters/overview.png",
                "R10C correction parameter profiles",
                "The real run displays fitted BRDF profiles and unfiltered geometry summaries; four fields are marked for range review.",
            ),
        ),
    ),
    "sensor_convolution": ModuleGuide(
        purpose=(
            "Compare spectral convolution with an independently calculated weighted "
            "average while varying source and target band counts."
        ),
        implementation="`resample_chunk_to_sensor`",
        inputs=(
            FieldGuide(
                "input_shape_y_x_b", "Varies spatial size and source wavelength count."
            ),
            FieldGuide(
                "target_band_count", "Varies the number of target spectral responses."
            ),
        ),
        checks=(
            CheckGuide(
                "output_band_count_correct",
                "Does output contain one band per supplied response function?",
                "The final axis equals the target response count.",
                "Inspect response iteration and output allocation.",
            ),
            CheckGuide(
                "weighted_average_matches_reference",
                "Does convolution match an independent normalized-weight calculation?",
                "Maximum absolute difference is at most `2e-7`.",
                "Inspect response normalization, wavelength alignment, and axis order.",
            ),
            CheckGuide(
                "dtype_is_float32",
                "Does convolution retain the expected compact datatype?",
                "Output dtype is float32.",
                "Review NumPy promotion and memory cost.",
            ),
        ),
        diagnostics=(
            FieldGuide("output_shape", "Observed target cube dimensions."),
            FieldGuide(
                "max_absolute_error", "Difference from the independent reference."
            ),
            FieldGuide("output_min", "Minimum convolved reflectance in the fixture."),
            FieldGuide("output_max", "Maximum convolved reflectance in the fixture."),
        ),
        establishes="Band-count, weighting, precision, and dtype contracts.",
        does_not_establish="Scientific adequacy of a particular sensor response curve.",
        stage_qa_link="stage-qa-guide.md#spectral-convolution-and-brightness",
        images=(
            ImageGuide(
                f"{REAL_RUN}/qa/stages/04_spectral_convolution/overview.png",
                "R10C convolved sensor overview",
                "The real stage uses the same spatial/spectral support diagnostics as other reflectance products.",
            ),
            ImageGuide(
                f"{REAL_RUN}/qa/stages/04_spectral_convolution/brightness.png",
                "R10C Landsat ETM+ brightness audit",
                "Configured and fitted brightness adjustments overlap; this verifies application, not scientific optimality of the coefficients.",
            ),
        ),
    ),
    "parquet_csv": ModuleGuide(
        purpose=(
            "Extract every synthetic raster pixel to Parquet, export a CSV copy, and "
            "verify row, coordinate, and spectral-column parity."
        ),
        implementation="`build_parquet_from_envi` and `_export_csv_copy_from_parquet`",
        inputs=(
            FieldGuide("shape_b_y_x", "Varies band, row, and column counts."),
            FieldGuide("chunk_size", "Varies extraction batch boundaries."),
        ),
        checks=(
            CheckGuide(
                "all_pixels_exported",
                "Is there one table row per raster pixel?",
                "Parquet row count equals rows × columns.",
                "Inspect chunk boundaries, pixel indexing, and filtering.",
            ),
            CheckGuide(
                "coordinate_columns_present",
                "Are spatial identity fields present?",
                "Required row, column, x, and y fields exist.",
                "A table without coordinates cannot be reliably traced back to the raster.",
            ),
            CheckGuide(
                "spectral_band_count_matches",
                "Is there one spectral column per input band?",
                "Detected spectral-column count equals the cube band count.",
                "Inspect naming, schema construction, and wavelength metadata.",
            ),
            CheckGuide(
                "csv_row_count_matches",
                "Does CSV conversion preserve table length?",
                "CSV and Parquet row counts match.",
                "Inspect streaming conversion and header handling.",
            ),
        ),
        diagnostics=(
            FieldGuide("parquet_rows", "Rows written to Parquet."),
            FieldGuide("csv_rows", "Rows read back from CSV."),
            FieldGuide("spectral_column_count", "Detected reflectance columns."),
            FieldGuide("column_count", "Total output schema width."),
            FieldGuide("parquet_bytes", "Persisted Parquet size."),
            FieldGuide("csv_bytes", "Persisted CSV size."),
        ),
        establishes="Chunk-independent row and schema preservation through extraction and CSV export.",
        does_not_establish="Correct polygon membership on every real geometry or scientific translation accuracy.",
        stage_qa_link="stage-qa-guide.md#parquet-extraction-and-merge",
        images=(
            ImageGuide(
                f"{REAL_RUN}/qa/stages/05_analysis_tables/overview.png",
                "R10C Parquet extraction and merge overview",
                "The real run compares rows, schema width, and file size for 18 readable extracted and merged tables.",
            ),
        ),
    ),
    "save_restart": ModuleGuide(
        purpose=(
            "Write one ENVI cube in separate row chunks, reconstruct it exactly, and "
            "prove that reading a reusable artifact does not modify it."
        ),
        implementation="`EnviWriter` plus deterministic artifact hashing",
        inputs=(
            FieldGuide("shape_y_x_b", "Varies spatial dimensions and band count."),
            FieldGuide("chunk_split_row", "Moves the internal write boundary."),
        ),
        checks=(
            CheckGuide(
                "chunked_write_reconstructs_cube",
                "Do independent writes reconstruct the original cube?",
                "Maximum absolute read-back error is zero.",
                "Inspect file offsets, axis order, and partial-write bounds.",
            ),
            CheckGuide(
                "expected_byte_count",
                "Is the binary artifact complete for its declared shape and dtype?",
                "File bytes equal the exact float32 shape-derived count.",
                "Treat mismatch as truncation, padding, or header/data disagreement.",
            ),
            CheckGuide(
                "read_does_not_mutate_artifact",
                "Is inspection itself non-destructive?",
                "SHA-256 is identical before and after read-back.",
                "Investigate accidental write mode or hidden repair behavior.",
            ),
        ),
        diagnostics=(
            FieldGuide("chunk_split_row", "Boundary between the two writes."),
            FieldGuide("image_bytes", "Observed binary size."),
            FieldGuide("max_absolute_error", "Largest reconstruction difference."),
            FieldGuide("sha256", "Post-read content digest."),
        ),
        establishes="Deterministic chunk writes, complete files, and non-mutating reads.",
        does_not_establish="Recovery from process termination during a write or distributed-filesystem failures.",
        stage_qa_link="stage-qa-guide.md#acquisition",
        images=(
            ImageGuide(
                f"{REAL_RUN}/qa/combined/pipeline_evolution.png",
                "R10C pipeline evolution summary",
                "Restart-safe stage files allow the combined report to compare persisted outputs without rerunning corrections.",
            ),
        ),
    ),
    "qa_plots": ModuleGuide(
        purpose=(
            "Inject known correction deltas and NoData patterns, render QA, and confirm "
            "that both image and JSON diagnostics record the intended signal."
        ),
        implementation="`render_flightline_panel` and its machine-readable QA payload",
        inputs=(
            FieldGuide(
                "correction_delta", "Varies positive, negative, and zero changes."
            ),
            FieldGuide(
                "nodata_fraction", "Varies injected invalid support from 0% to 25%."
            ),
            FieldGuide("shape_b_y_x", "Varies bands and spatial dimensions."),
        ),
        checks=(
            CheckGuide(
                "png_written",
                "Was a non-empty visual QA artifact written?",
                "PNG exists and contains bytes.",
                "Inspect rendering dependencies, output paths, and figure closure.",
            ),
            CheckGuide(
                "json_written",
                "Was a non-empty machine-readable companion written?",
                "JSON exists and contains bytes.",
                "Do not rely on the image alone; investigate serialization or path errors.",
            ),
            CheckGuide(
                "band_count_reported",
                "Does QA describe the supplied spectral dimension?",
                "Reported band count equals the fixture band count.",
                "Inspect header parsing and cube orientation.",
            ),
            CheckGuide(
                "delta_diagnostic_matches_input",
                "Does the reported correction magnitude recover the injected change?",
                "Median reported delta matches the known delta within numerical tolerance.",
                "Inspect NoData exclusion, scale conversion, and before/after pairing.",
            ),
        ),
        diagnostics=(
            FieldGuide("png_bytes", "Rendered image size."),
            FieldGuide("json_bytes", "Machine-readable report size."),
            FieldGuide(
                "median_reported_delta", "Recovered median after-minus-before change."
            ),
            FieldGuide("reported_valid_percent", "QA-reported valid support."),
            FieldGuide("issue_count", "Number of report findings retained for review."),
        ),
        establishes="Artifact generation and recovery of deliberately injected diagnostic signals.",
        does_not_establish="Human legibility across every display or scientific acceptability of a correction.",
        stage_qa_link="stage-qa-guide.md",
        images=(
            ImageGuide(
                f"{REAL_RUN}/legacy-qa.png",
                "R10C legacy QA panel",
                "The compatibility panel remains available alongside the more focused stage reports.",
            ),
        ),
    ),
}


STAGE_CHECK_GUIDES: dict[str, CheckGuide] = {
    "output_exists:*": CheckGuide(
        "output_exists:*",
        "Does every declared canonical output exist?",
        "Each expected file is present at the recorded path.",
        "A missing output is a stage failure; inspect the stage log before trusting downstream files.",
    ),
    "within_footprint_valid_reflectance_fraction": CheckGuide(
        "within_footprint_valid_reflectance_fraction",
        "How complete is spectral support inside the observed flight footprint?",
        "Above 0.90 passes; 0.70–0.90 warns; at or below 0.70 fails.",
        "Separate real missing support from rectangular background outside the flight track.",
    ),
    "negative_reflectance_fraction": CheckGuide(
        "negative_reflectance_fraction",
        "How often is valid reflectance negative?",
        "Below 0.01 passes; 0.01–0.05 warns; at or above 0.05 fails.",
        "Review scaling, correction behavior, shadows, and wavelength-specific artifacts.",
    ),
    "usable_band_reflectance_above_1_2_fraction": CheckGuide(
        "usable_band_reflectance_above_1_2_fraction",
        "How often do wavelengths not already labeled poor-quality exceed 1.2?",
        "Below 0.01 passes; 0.01–0.05 warns; at or above 0.05 fails.",
        "Inspect scaling and spectral regions; all-band values remain separately reported.",
    ),
    "known_bad_spectral_bands_retained": CheckGuide(
        "known_bad_spectral_bands_retained",
        "Were established poor-quality wavelength regions recognized and retained?",
        "No labeled bands passes; retained labeled bands warn deliberately.",
        "The warning is a review label, not a request to delete or mask the data.",
    ),
    "geometry_field_fraction": CheckGuide(
        "geometry_field_fraction",
        "Are all six correction geometry summaries present?",
        "At least 0.99 passes; 0.50–0.99 warns; at or below 0.50 fails.",
        "Missing geometry limits correction reproducibility and interpretation.",
    ),
    "persisted_geometry_physical_range_review": CheckGuide(
        "persisted_geometry_physical_range_review",
        "Do persisted min/mean/max summaries lie within physical radian ranges?",
        "Zero fields requiring review passes; any out-of-range field warns.",
        "Values stay unfiltered; investigate NoData contamination before changing correction logic.",
    ),
    "absolute_correction_q99": CheckGuide(
        "absolute_correction_q99",
        "Is the extreme correction magnitude bounded?",
        "Below 0.20 reflectance passes; 0.20–0.50 warns; at or above 0.50 fails.",
        "Review spatial support and affected wavelengths for overcorrection.",
    ),
    "maximum_chunk_seam_score_after": CheckGuide(
        "maximum_chunk_seam_score_after",
        "Are gradients at application boundaries larger than ordinary neighboring gradients?",
        "Below 1.5 passes; 1.5–2.5 warns; at or above 2.5 fails.",
        "A genuine landscape edge can coincide with a boundary, so inspect the map before concluding it is computational.",
    ),
    "brightness_coefficient_application:*": CheckGuide(
        "brightness_coefficient_application:*",
        "Does each persisted Landsat before/after pair reproduce its configured gain?",
        "Maximum absolute fitted gain error at or below `1e-4` passes.",
        "Failure means application drift; passing does not prove that the empirical coefficient is scientifically optimal.",
    ),
    "readable_parquet_outputs": CheckGuide(
        "readable_parquet_outputs",
        "Can DuckDB read at least one declared Parquet product?",
        "One or more readable tables passes; none fails.",
        "Inspect incomplete files, schema problems, and discovery paths.",
    ),
}


STAGE_GUIDES = (
    {
        "stage_id": "acquisition",
        "heading": "Acquisition",
        "purpose": "Confirm that the source artifact exists and record bounded provenance before reading reflectance.",
        "images": MODULE_GUIDES["neon_download"].images,
    },
    {
        "stage_id": "input_data",
        "heading": "Input reflectance",
        "purpose": "Establish spatial and spectral support before correction while distinguishing the observed footprint from rectangular background.",
        "images": MODULE_GUIDES["h5_to_envi"].images,
    },
    {
        "stage_id": "correction_parameters",
        "heading": "Correction parameters",
        "purpose": "Review correction geometry coverage, physical ranges, and persisted BRDF coefficient profiles without filtering them.",
        "images": MODULE_GUIDES["brdf_correction"].images,
    },
    {
        "stage_id": "brdf_topographic_correction",
        "heading": "BRDF and topographic correction",
        "purpose": "Compare matched before/after products for support, magnitude, spectral behavior, and computational seams.",
        "images": MODULE_GUIDES["topographic_correction"].images,
    },
    {
        "stage_id": "spectral_convolution",
        "heading": "Spectral convolution and brightness",
        "purpose": "Check convolved reflectance support and independently audit every persisted Landsat brightness adjustment.",
        "images": MODULE_GUIDES["sensor_convolution"].images,
    },
    {
        "stage_id": "analysis_tables",
        "heading": "Parquet extraction and merge",
        "purpose": "Verify declared analysis products, DuckDB readability, row counts, schema width, and extracted-versus-merged structure.",
        "images": MODULE_GUIDES["parquet_csv"].images,
    },
)


def stage_check_guide_key(check_id: str) -> str:
    """Normalize artifact- and sensor-specific check IDs to documented families."""

    if check_id.startswith("output_exists:"):
        return "output_exists:*"
    if check_id.startswith("brightness_coefficient_application:"):
        return "brightness_coefficient_application:*"
    return check_id


__all__ = [
    "CheckGuide",
    "FieldGuide",
    "ImageGuide",
    "MODULE_GUIDES",
    "ModuleGuide",
    "REAL_RUN",
    "STAGE_CHECK_GUIDES",
    "STAGE_GUIDES",
    "stage_check_guide_key",
]
