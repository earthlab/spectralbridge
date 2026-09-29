# Module vignette 6: process drone imagery

**Notebook:** [View the drone notebook in the repository](https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/06_drone_pipeline.ipynb). GitHub displays the cells; clone or download the file to run them.

Use this module for local drone TIFF packages or HDF5 inputs. Discovery is
recursive, the original package remains traceable, and TIFF inputs enter the
same established HDF5, ENVI, topographic, and BRDF correction machinery.

## Scientific branches

```text
DRONE
TIFF + ancillary + manifest
  -> working H5 -> ENVI -> topo/BRDF -> corrected MicaSense
  -> affine cross-sensor translation -> Landsat-like raster
  -> full or polygon spectral library -> QA

NORMAL NEON
NEON H5 -> ENVI -> topo/BRDF -> corrected hyperspectral
  -> spectral convolution -> Landsat-like raster
  -> full or polygon spectral library -> QA

OPTIONAL VALIDATION
actual Landsat
            \
drone-like --- actual-Landsat grid -> pairwise QA
            /
NEON-like
```

The paths are shared through corrected ENVI and then diverge. Drone data use
reviewed affine coefficients derived by the independent bulk workflow. NEON
hyperspectral data use spectral convolution. The corrected native MicaSense
raster remains a first-class output and is never overwritten. A translated
product is Landsat-like; it is not an actual Landsat observation.

## Prepare inputs and coefficients

Place valid drone HDF5 files or reflectance TIFF packages under one input
directory. TIFF packages may include aligned terrain/view sidecars and are
matched to the bundled field manifest unless `drone_manifest_path` overrides
it. See the [detailed tutorial](../tutorials/micasense-to-landsat.md) for the
complete TIFF contract.

Production translation consumes a static, versioned registry generated from
the completed compact bulk output. It does not fit coefficients. The production
weighting is fixed to `site_balanced`, reflecting intended transfer to new
flightlines and sites rather than optimization of the pooled pixel fit.
SpectralBridge validates equation direction, sensor identities, the exact 18
physical pair-band mappings, wavelengths, finite coefficients, confidence, and
bulk-run provenance before writing a translated product.

## Run it

```python
from spectralbridge import run_drone_pipeline

results = run_drone_pipeline(
    input_h5_dir="drone_inputs",
    output_dir="drone_outputs",
    polygon_path="plots.geojson",
    extraction_mode="polygon",
    apply_topo=True,
    apply_brdf=True,
    apply_translation=True,
    translation_strict=False,
    drone_manifest_timezone="UTC",
)

print(results["processed"])
print(results["translation_outputs"])
print(results["matched_source_outputs"])
```

`run_drone_pipeline()` now treats missing requested products as an incomplete
run, rather than returning a successful-looking result. It validates the
working H5, raw and corrected ENVI pairs, requested full or polygon Parquet,
every requested translated target and library, stage/provenance JSON, flight QA,
and the final report. Requested topo and BRDF corrections must actually be
applied. A failure raises `DronePipelineIncompleteError`; its `results`
attribute and `drone_qa_summary.json` retain per-flight reasons. Set
`raise_on_incomplete=False` only when intentionally collecting a structured
partial batch result. A polygon run with no intersecting pixels is incomplete,
not a successful extraction. Optional actual-Landsat comparison remains
non-blocking when no acceptable observation is available. Flights whose
required scientific geometry cannot be validated or safely repaired are
reported separately in `results["blocked"]`; they are not mislabeled as
software failures.

Use `extraction_mode="full"` for all corrected pixels. Omitting
`extraction_mode` preserves the earlier behavior: polygon extraction when a
polygon is supplied, otherwise raster and QA outputs only. Translation remains
opt-in and uses the packaged site-balanced registry by default. It checks
corrected input values against the bulk fit's numeric domain before writing;
apparently fractional input is refused rather than silently rescaled. Normal
mode writes `caution`
bands with warnings, while `translation_strict=True` refuses them. A `reject`
coefficient is never applied.

## Standalone and comparison QA

Every translated run produces per-target translation JSON and PNG diagnostics
without NEON or network access. They show band mapping, coefficient evidence,
corrected-versus-translated values, reflectance shifts, valid fractions,
nodata preservation, and unusual translated values.

Set `landsat_qa=True` to request an overlapping Landsat Collection 2 Level 2
scene from Microsoft Planetary Computer. Install this optional support with:

```bash
python -m pip install "earthlab-spectralbridge[landsat]"
```

Alternatively, use `landsat_product="landsat_stack.tif"` to supply an
analysis-ready multiband raster or a previously cached observation manifest.
The comparison selects the closest acceptable scene within
`landsat_search_days`, applies the Landsat QA pixel mask, and aggregates the
translated drone product onto the actual Landsat grid using valid-aware area
averaging. Failed searches, cloud rejection, or insufficient overlap are
recorded as optional-QA limitations and do not fail the core drone run.

Add `comparison_neon_product="neon_landsat_like.img"` to compare an existing
normal-pipeline NEON product on the same Landsat support. The three reported
pairs are drone-like versus actual, NEON-like versus actual, and drone-like
versus NEON-like. NEON is optional and is never processed by drone code.

## Restart and outputs

Solar geometry deserves a separate review before accepting corrected products.
The original HDF5 or TIFF package is authoritative and read-only. Discovery
ignores generated `__working.h5` files. Every run starts from the original
source, then reuses or rebuilds the derived working copy according to its stage
signature. Passing a working H5 as a source is rejected because it loses the
provenance needed to decide whether a repair remains valid.

For HDF5 input, the working-copy stage compares embedded solar arrays with an
independent scene-center position computed from the acquisition datetime and
georeference. A valid array is preserved. A missing or materially inconsistent
array is replaced **only in the working copy** when the datetime has an explicit
timezone, scene coordinates are valid, the expected sun is above the horizon,
and manifest provenance authorizes the repair. The canonical
`Solar_Zenith_Angle` and `Solar_Azimuth_Angle` datasets are then used by
topographic/BRDF correction. The source H5 fingerprint is verified before and
after repair. If those conditions are not met, the flight is
`blocked_scientific` instead of being silently corrected with questionable
geometry.

For TIFF input, aligned solar rasters take precedence over explicit scalar
angles, which take precedence over manifest-derived geometry. Naive manifest
times are localized with `drone_manifest_timezone` (default `"UTC"`); pass a
verified IANA zone when the campaign used local civil time. Ambiguous DST
times, malformed dates, missing coordinates, conflicting duplicate manifest
rows, and below-horizon solutions block the affected flight while the campaign
continues.

Each flight audit records source and UTC-normalized acquisition time, timezone,
coordinate source and scene center, embedded and expected angle summaries,
zenith and circular-azimuth residuals, validation status, geometry actually
used, repair decision/reason, and source fingerprint. The calculation reuses the package's
approximate [NOAA-style solar-position equations](https://gml.noaa.gov/grad/solcalc/solareqns.PDF),
not a precise ephemeris. The 5° validation tolerance is inclusive and applies
to zenith plus circular azimuth residuals. These are workflow validation bounds,
not universal calibration limits, and the code never substitutes
`90 - angle` as an undocumented repair.

On a production VM, inspect existing working H5 files without rerunning
corrections or rewriting products:

```bash
PYTHONPATH=src python scripts/diagnose_drone_solar_geometry.py \
  /home/jovyan/data-store/SpectralBridge_Drone_2023_2024_Production/flight_outputs \
  --output /home/jovyan/data-store/SpectralBridge_Drone_2023_2024_Production/solar_validation/solar_geometry.csv \
  --candidate-timezone UTC --candidate-timezone America/Denver
```

The two timezone candidates in the CSV are hypothetical interpretations until
the field manifest's convention is independently verified. Review source
dataset units, scale/fill attributes, collection date, scene CRS, and circular
residuals together. A filename/manifest date mismatch requires provenance
review because a package filename need not be the acquisition date.

Valid working H5, corrected ENVI, translated ENVI, and translated Parquet
products are reused when their inputs and translation signatures match.
Legacy H5 sun-angle arrays under `Reflectance/Metadata`, including nested
`to-sun_*` datasets, are exposed through lightweight links in the *working*
copy; source H5 files are not changed. Continue a campaign by rerunning the
same command against the original input root and same output root. Missing or
signature-invalid stages resume from the first incomplete stage. Do not set
`overwrite=True` for an ordinary continuation.

Each completed flight directory contains `spectralbridge_flightline.json` and
matched native-MicaSense/Landsat-like ENVI pairs. Consequently
`run_bulk_pipeline(drone_outputs, ..., input_mode="auto")` discovers completed
drone flights directly; no manual rename or campaign-wide pixel merge is
needed. Per-flight Parquets remain authoritative. Set `merge_extractions=True`
only when a legacy consumer explicitly requires the optional run-level merged
tables.

Start bulk work with `preflight_only=True`. Bulk inventories the per-flight
Parquet footers, schemas, row counts, sizes, QA state, sensors, and translation
availability without scanning pixels or writing into the drone tree. The
translated Landsat-like products are applications of an existing coefficient
registry, not independent Landsat observations, so the ordinary drone campaign
is analyzed as `derived_application_verification`. Bulk writes compact fits and
LOSO outputs to verify application consistency, with coefficient metadata marked
`diagnostic_application_verification_only`. Do not feed those circular
diagnostics back into the registry or interpret them as empirical calibration.
The canonical shared-band contracts are 4 bands for TM/ETM+ and 5 for
OLI/OLI-2; the 6/7-band contracts remain specific to NEON convolution products.

With full extraction, the six canonical per-flight analysis tables are the
native corrected `__full.parquet`, four sensor-specific
`__landsat_like_<target>_translated_envi.parquet` tables, and the optional
combined Landsat-like table used by validated production packaging. Polygon
extraction uses the corresponding `__polygons.parquet` forms. Every translated
table carries the translation pair, source/target sensor, coefficient hash, and
evidence-boundary columns; bulk validates these fields from the Parquet schema.

| Artifact | Role | Regeneration rule |
| --- | --- | --- |
| Original H5/TIFF package | Authoritative immutable input | Never generated or modified |
| `__working.h5` | Derived, restartable bridge and repair target | Reuse only when source/config/solar signature matches |
| ENVI, translation, extraction, and QA outputs | Derived scientific products | Reuse only when their stage contracts validate |
| `spectralbridge_flightline.json` and stage/provenance JSON | Identity and audit contract | Required and deterministic |

Optional Landsat failure does not invalidate or recompute core products. See
[outputs and naming](../pipeline/outputs.md) for the complete contract, and
review every QA JSON before treating a coefficient application as trustworthy.

## Continue

- [Review QA outputs](qa-and-analysis.md)
- [Extract polygon spectra](polygon-extraction.md)
- [Detailed MicaSense tutorial](../tutorials/micasense-to-landsat.md)
- [Package architecture](../dev/architecture.md)
