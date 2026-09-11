# Package Architecture

This page describes how SpectralBridge is organized internally. Understanding this structure helps contributors extend the pipeline or integrate new sensors without breaking guarantees.

---

## Design philosophy and invariants

- **Reproducibility first.** Pipeline behavior is predictable and restart-safe; stages skip when valid outputs already exist instead of recomputing.
- **Fixed ordering.** `process_one_flightline` and `go_forth_and_multiply` orchestrate the same sequence: ENVI export → BRDF/topographic parameter build → BRDF+topo correction → sensor convolution/resampling → Parquet exports → DuckDB merge → QA panels.
- **File contracts.** `FlightlinePaths` centralizes filenames and directories; stages communicate only through these artifacts. Required outputs depend on the requested extraction path: correction and convolution persist ENVI products before optional full or polygon table extraction.
- **Outputs are the API.** Functions return little; correctness is expressed through on-disk ENVI/Parquet and QA files that can be inspected or reused.

---

## Pipeline architecture (high level)

- **Stages** are pure file transforms. Each consumes a known input set and writes ENVI, Parquet, and JSON/PNG sidecars. Stages do not mutate shared state.
- **Orchestration** happens in `pipelines/pipeline.py` via `process_one_flightline` (single flightline) and `go_forth_and_multiply` (batch). Both rely on `FlightlinePaths` to resolve paths and naming before delegating work.
- **Communication** between stages is file-based. The BRDF+topo-corrected ENVI is always the source for sensor resampling; Parquet exports derive from both raw and corrected ENVI; the merged Parquet and QA summaries consume all earlier artifacts.
- **Restart safety** is achieved because each stage validates its outputs and returns early when they already exist. Partial runs can be resumed without recomputation or corrupting prior files.

---

## Directory structure (Python package)

- `spectralbridge/pipelines/`: orchestration entry points and Ray helpers
- `spectralbridge/exports/`: ENVI export helpers
- `spectralbridge/io/`: schema and I/O helpers (e.g., NEON schema resolution)
- `spectralbridge/utils/`: shared utilities, naming/path helpers, memory management
- `spectralbridge/data/`: spectral metadata and calibration tables
  - `landsat_band_parameters.json`: band centers/FWHM used for resampling
  - `brightness/*.json`: brightness adjustments between Landsat and MicaSense
  - `hyperspectral_bands.json`: reference metadata for hyperspectral inputs
- `spectralbridge/qa_plots.py` and `spectralbridge/sensor_panel_plots.py`: QA visualization utilities
- `spectralbridge/standard_resample.py`: spectral resampling and coefficients
- `spectralbridge/pipelines/bulk.py`: independent bulk orchestration
- `spectralbridge/bulk/`: canonical catalog, virtual DuckDB dataset,
  provenance, and modular population analyses
- `spectralbridge/pipelines/drone.py`: local TIFF/HDF5 orchestration through
  corrected native MicaSense, optional coefficient translation, extraction,
  and QA
- `spectralbridge/drone_translation.py`: validated bulk-coefficient consumer,
  wavelength mapping, affine raster transform, and translated-library
  provenance
- `spectralbridge/landsat_validation.py`: optional STAC/supplied Landsat
  observations, QA masking, common-grid aggregation, and pairwise metrics

### Drone and normal NEON branches

The two pathways deliberately share the established HDF5 → ENVI →
topographic/BRDF correction machinery. They diverge after corrected ENVI:

```text
corrected ENVI
  |
  +-- NEON hyperspectral -> convolution -> target-sensor products
  |
  +-- drone MicaSense -> affine translation -> Landsat-like products
```

Drone translation is opt-in. It consumes reviewed candidate coefficients from
the independent bulk pipeline and requires an explicit weighting family. The
consumer validates the recorded source-to-target equation and sensor/band
orientation, maps source bands by wavelength, writes a distinct translated
ENVI pair, and retains corrected native MicaSense unchanged. Polygon and
full-pixel paths reuse the existing extraction infrastructure, then add
translation provenance columns without creating a parallel table model.

Standalone drone QA does not require a NEON flight or network service. An
optional validation branch can search Microsoft Planetary Computer STAC or use
a supplied Landsat raster. It aggregates translated drone and optional
normal-pipeline NEON products to the actual Landsat grid before comparison.
Scene absence, cloud rejection, and insufficient overlap are QA limitations,
not core-pipeline failures.

The drone path records stage signatures beside the working H5, native ENVI,
and corrected ENVI products. A valid output is reused only when its source
fingerprint and relevant configuration still match; an orphaned or corrupt
file is not a checkpoint. Translation and translated-library stages retain
their coefficient/source signatures. `render_drone_qa_report` is an independent
final stage that reads the run audit and existing QA artifacts, not source
rasters.

### Independent bulk analysis

`run_bulk_pipeline` is downstream of completed per-flightline workflows rather
than another stage inside them. Scientific identity is resolved by an
extensible parser layer: a generic per-flightline manifest and canonical NEON
names are the installed conventions, while outer compute/storage folders never
define identity. A product registry centralizes filename recognition and
metadata expectations. Analysis profiles separate processing completeness from
product availability and analysis eligibility, and translation-pair descriptors
define arbitrary source/target band relationships.

Validation is atomic per flightline. Invalid units and duplicate identities are
excluded with stable reason codes while valid units continue by default. The
translation profile can consume only its requested target ENVI products, read
them in aligned bounded windows, and persist only mergeable per-flightline
sufficient statistics. Site/global/balanced models aggregate those compact
checkpoints and LOSO training subtracts held-out site moments from global
moments. Prebuilt merged Parquets remain a read-in-place compatibility input;
pixel-level dataset construction is a separate explicit operation.
Catalog/preflight, dataset census, statistics, translation, and validation are
independent layers. The workflow never calls or mutates the NEON and drone
orchestrators.

`summarize_bulk_results` is a fourth, post-run interpretation layer. It depends
only on the completed manifest and compact candidate, per-flightline, per-site,
and LOSO result Parquets. It derives weighting comparisons, coefficient
heterogeneity, held-out-site performance, and review flags without reopening
rasters or sufficient-statistics checkpoints. Input file fingerprints and a
configuration signature make its outputs restart-safe. Review thresholds are
kept in `BulkResultsConfig` and are explicitly screening criteria rather than
universal calibration acceptance rules.

The streaming coefficient and LOSO calculations form one deliberately coupled
stage because exact MAE and held-out evaluation share the bounded second source
pass. Its signature covers compact flightline moments, requested pairs,
threshold, and chunk configuration. Results interpretation then has separate
compact-summary, diagnostic, publication, and final-report stages.

### Debuggable stage boundaries

The intentionally small public API remains `run_drone_pipeline`,
`run_bulk_pipeline`, and `summarize_bulk_results`. Maintainers can rerun major
stages directly without duplicating orchestration:

- Drone preparation/export/correction:
  `_prepare_drone_source_working_h5`, `export_h5_to_envi`, and
  `apply_drone_corrections`.
- Drone translation/library/QA: `load_drone_translation_plans`,
  `apply_drone_translation`, `enrich_translated_spectral_library`,
  `render_drone_translation_qa`, and `render_drone_qa_report`.
- Optional external validation: `acquire_landsat_observation`,
  `load_supplied_landsat_observation`, and `compare_landsat_common_support`.
- Bulk discovery/checkpoints/models: `discover_completed_flightlines`,
  `compute_flightline_statistics`, and `run_streaming_translation_analyses`.
- Bulk interpretation: `summarize_bulk_results`, with internal reporting
  functions independently rendering the summary, diagnostics, publication
  panels, and final PDF from compact tables.

An underscore marks protected/internal infrastructure rather than an unstable
file contract. The documented on-disk artifacts remain the primary interface.

Optional spectral-library reporting also reads its merged polygon Parquet in
place. Its visualization-validity policy is distinct from regression validity:
selected bands must be present, finite, and not equal to known nodata sentinels,
while finite negative corrected reflectance remains visible by default. Compact
analytical summaries preserve actual valid extrema. Robust and full plot ranges
are separate rendering metadata, and bounded extreme-spectrum records provide
traceability without introducing an observation cache.

An optional visualization branch accepts an already merged polygon spectral
library as a second read-only input. A schema adapter selects one coherent set
of wavelength-bearing columns, then DuckDB scans only the species, hierarchy,
and current band batch needed for each calculation. Compact species/band
summaries and approximate quantiles are persistent scientific products; the
original spectra are never copied. Plotting streams one group in bounded Arrow
batches into fixed-size raster trace layers while axes, labels, and median lines
remain vector PDF elements. Summary PDFs and the expensive multipage trace
suite are separate opt-in operations.

---

## Extending the system safely

### Adding or modifying a target sensor
- Update spectral definitions in `spectralbridge/data/landsat_band_parameters.json` (or analogous table for the new sensor) and ensure resampling logic in `standard_resample.py` knows how to consume them.
- Confirm `get_flightline_products` and `FlightlinePaths` generate filenames for the new sensor; preserve ENVI, extraction-specific Parquet, and QA contracts.
- Add tests that validate band definitions and resampled outputs; do not bypass the existing stage ordering.

### Updating brightness or translation coefficients
- Fixed percentage brightness adjustments live under
  `spectralbridge/data/brightness/` and are loaded via `brightness_config`.
- Pooled synthetic translation slopes and intercepts are bulk-pipeline outputs,
  not packaged brightness tables. Preserve their manifest and source catalog
  when reviewing or promoting a coefficient set.
- Keep JSON schemas and key names stable; update dependent tests and
  documentation when either coefficient contract changes.

### Modifying QA outputs
- QA panels and JSON summaries are produced after merging outputs. Filenames such as `<flight_id>_qa.png` and `<flight_id>_qa.json` are assumed by docs and CI.
- If adding metrics or changing formats, ensure `_qa.png` and `_qa.json` remain available and update the QA tests under `tests/test_qa` accordingly.
- Maintain quick-mode rendering used in CI fixtures so drift checks continue to pass.

---

## Relationship to scientific reproducibility

- The repository encodes the workflow described in the RSE manuscript; artifacts (ENVI, Parquet, QA) are the evidence trail for analyses.
- Centralized naming, stage ordering, and idempotent execution make runs auditable and repeatable across environments.
- Contributors are expected to preserve these invariants so published and future analyses can be reproduced from the same on-disk products.

---

## Next steps

- [Contributing & development workflow](contributing.md)
- [Guidelines for AI/Codex edits](codex-guidelines.md)
- [Architecture audit](architecture-audit.md)
