# SpectralBridge drone pipeline: three-site integration report

Date: 2026-11-04. Branch: `codex/prepare-2.3.0rc2`. Package: `2.3.0rc2`.
Baseline commit: `bb3da46bea0a4295ca3152a9f607ed17140575f1`; working-tree changes are
recorded in the source manifests. This is not a committed/released revision.

**Available source stages completed for Gordon, Goldhill and Ruby. The full
end-to-end objective remains incomplete.** The user explicitly deferred the new
location tables. Physical calibration remains unverified independently of that
deferral. Both requested corrections stayed enabled in the production attempts;
all three attempts stopped at the existing radiometry gate. No corrected,
translated or approved-library product was certified, and no production outputs
were uploaded.

The [10-page scientific report](output/pdf/spectralbridge-drone-three-site-validation.pdf)
contains source/prepared RGB, red and red-edge maps for each site, all-band
numerical diagnostics, polygon signal comparisons and the actual stage ledger.
Every rendered page was visually inspected. The figures compare source
preparation; they do not substitute for the requested corrected-image assessment.

## Sources and transfer results

Live discovery used the authenticated GoCommands client and actual contents of
`/iplant/home/shared/earthlab/macrosystems/field-data/uas-packages`.
No historical 10 cm raster was used as the radiometric source.

| Site | Package | Original-package orthomosaic | Original dimensions | Verified inputs |
| --- | --- | --- | --- | ---: |
| Gordon | `AOP-GORDON-08-14-23-ExportPackage` | `AOP-GORDON-8-14-23-M300_ORTHO.tif` | 2,765 × 3,918 | 14 |
| Goldhill | `AOP-GOLDHILL-08-14-23-ExportPackage` | `AOP-GOLDHILL-08-14-23_ORTHO.tif` | 2,646 × 3,747 | 15 |
| Ruby | `AOP-Ruby-08-14-23-ExportPackage` | `AOP-RUBY-08-14-23-ORTHO_CLIPPED.tif` | 1,242 × 2,354 | 19 |

All **48 inputs** have remote MD5 checksums verified and local SHA-256/MD5
records. After staging the case-distinct Goldhill terrain files separately, all
48 were exercised again through checksum-aware reuse with downloads forbidden.
Original orthomosaic hashes remain unchanged. Inputs include the selected
orthomosaic, terrain alternatives, source reports and small metadata files;
unneeded LAS archives were not transferred.

Ruby's only selected ORTHO is explicitly a **spatially clipped export**. This
run does not establish that a full unclipped original exists in the package.
The SD1/SD2 photo metadata remain source metadata, not substitutes for the new
location tables. Package dates/stems preserve original provenance; they must not
be read as independently verified acquisition dates. Source manifests preserve
the relevant field-manifest rows and the explicit UTC interpretation used by the
existing pipeline; the actual camera clock zone remains unverified.

Machine-readable evidence is in
[`provenance/drone-three-site-integration/2026-11-04/`](provenance/drone-three-site-integration/2026-11-04/):

- `{site}_remote_selection.json`: logical source paths, alternatives, sizes,
  remote checksums and selection rationale.
- `{site}_transfers.json`: transfer identities, local destinations and hashes.
- `{site}_source_manifest.json`: original/prepared raster profiles, wavelengths,
  encoding, associated inputs, deferred table status, acquisition records,
  software hashes and processing configuration. A copy accompanies each site's
  outputs.
- `available_product_verification.json`: real transfer reuse, unchanged sources,
  exact raster comparison counts and first production blocking reasons.
- `available_output_catalog.json`: sizes and checksums for 108 available derived
  files totaling 3,910,320,459 bytes; source downloads are excluded.
- `stage_ledger.json`, processing logs, full-band CSV and compact polygon CSV.

## Configuration and validation

All three orthomosaics are north-up, unrotated, projected metre rasters in
EPSG:26913 with ten UInt16 spectral bands plus declared alpha band 11. Native
pixel sizes are approximately 8.063, 8.443 and 8.315 cm, respectively.

The numerical derivative uses **`stored = DN * 10000 / 65535`**, zero offset,
no scene min/max adjustment and no numerical clipping. It is Float32 with
alpha-aware bilinear resampling, nearest-neighbor footprint support and NaN
missing values. Original files are immutable. Existing recorded 10 cm grids
were used solely as spatial comparison support; all spectral values come from
the original-package imagery. The grid reference and its hash are recorded.

Wavelengths are `444, 475, 531, 560, 650, 668, 705, 717, 740, 862 nm` under the
established MicaSense Dual package convention. The TIFFs do not independently
declare wavelengths or physical calibration. The fixed 0–10,000 numerical range
**does not establish physical reflectance**. Radiometry remains `UNSUPPORTED`,
with unknown physical scale and offset; the TIFF, HDF5 and ENVI provenance retain
that limitation.

Preparation holds one full spectral band plus source/target masks and warp
buffers rather than the whole ten-band cube. RAM scales with raster area;
this helper is not a window-bounded resampler. Ten band reads/warps and bounded
checksum passes are explicit. No ordinary pixel-scale analytical Parquet cache
was introduced. Existing HDF5/ENVI conversion and exact output verification are
chunked. Spatial polygon indexes are intentional existing pipeline products.

The researcher source remains
`Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg`.
Half-diameter definitions, IDs, recorded cover/PFT/site attributes and source
references are retained. Descriptive DN polygon summaries are labeled
`DESCRIPTIVE_DN_NOT_APPROVED_LIBRARY`; no approved physical spectral library was
created.

## Stage completion

| Stage | Gordon | Goldhill | Ruby |
| --- | --- | --- | --- |
| Original-package discovery / verified staging | Complete | Complete | Complete; clipped source noted |
| Orthomosaic validation / 10 cm numeric preparation | Complete with calibration limitation | Complete with calibration limitation | Complete with calibration limitation |
| Working HDF5 / raw ENVI | Complete; restart reused | Complete; restart reused | Complete; restart reused |
| Standard source-only QA | Generated; scientific status `not_evaluated` | Same | Same |
| Half-diameter spatial polygon index | 58 polygons / 32,930 pixels | 158 / 144,749 | 86 / 22,684 |
| Camera-table validation/reconstruction | Deferred by user | Deferred by user | Deferred by user |
| Requested topographic + BRDF correction | Scientifically blocked | Scientifically blocked | Scientifically blocked |
| Translation / approved spectral library | Dependency blocked | Dependency blocked | Dependency blocked |
| Corrected artifact assessment | Not evaluable | Not evaluable | Not evaluable |
| Production upload / remote output verification | Not attempted | Not attempted | Not attempted |

The exact first blocking reason for every requested production run is:

> Radiometry UNSUPPORTED: authoritative physical scale, offset, units and provenance required (Original UInt16 DN; fixed numerical encoding; physical calibration unavailable).

The preparation run explicitly requests no corrections or translation. Its normal
`__corrected` ENVI filename therefore holds an **uncorrected identity copy**,
with correction flags false; the name alone does not establish a correction.
The separate `requested_pipeline_attempt` enables topography, BRDF and translation
and requests polygon extraction. Its machine-readable status is `incomplete`,
with one scientific block and no unexpected processing failure per site.

All **145,758,170 finite ENVI values** exactly match the prepared TIFFs, with
matching missing-data positions, dimensions, projected CRS and affine transforms:
58,984,010 Gordon; 66,839,440 Goldhill; 19,934,720 Ruby. These checks operate in
bounded windows. Repeated real runs reuse the working HDF5 and raw ENVI products;
preparation also verifies source/config/output identity before reuse.

## QA and artifact assessment

Existing standard QA figures, debug summaries, dashboards/reports and QA JSON
were generated through `run_drone_pipeline`; they were not replaced by the
additional report. Requested blocked runs also have standard status summaries.
Source-only QA is explicitly scientifically unevaluated. Standard plots may
retain generic reflectance-oriented labels; their stored DN values must not be
interpreted as calibrated reflectance. Zero raw-to-identity differences are
expected and are not evidence of successful correction.

Additional diagnostics evaluate every native/prepared pixel in every spectral
band: finite/missing counts, extrema, 1st/99th percentiles, medians, interquartile
ranges and 99th-percentile adjacent-pixel jumps in both image directions.
Display-only RGB uses a shared square-root stretch and fixed 0–16,384 DN-equivalent
range; red (650 nm) and red-edge (717 nm) maps use the same fixed scalar scale and
shared within-site map limits. Alpha background is excluded explicitly. Display
bounds never alter analytical summaries.

At 650 nm, prepared/native distribution medians differ by approximately **+0.22%
Gordon, +0.06% Goldhill and +0.05% Ruby**. These are distributions on different
spatial grids/supports, not pixelwise calibration residuals. Source structures
remain visible in the prepared maps; a full seam/striping exclusion is not
claimed. Cross-site signal differences are descriptive and uncalibrated.

**Harmful correction artifacts cannot be assessed in this run.** No eligible
corrected products exist, so topographic/BRDF/combined maps, correction factors,
view-angle distributions, fitting support, conditioning and polygon correction
changes are unavailable. Earlier experimental Goldhill results were not reused
as if generated by this integration test.

## Integration changes and tests

Changes extend existing modules; there is no separate scientific correction
implementation:

1. `remote.py`: opt-in detailed GoCommands JSON listings, checksum-verified
   get/put flags, correct MD5/SHA-256 interpretation and atomic resumable generic
   file staging. Default existing CLI arguments remain compatible.
2. `drone_production.py`: original-package inspection/staging, ambiguity reporting,
   explicit clipped-source status and stable remote-path hash directories for
   case-distinct local paths. Upload validation can require remote checksums;
   size-only evidence is explicitly weaker. Camera-table validation checks
   required columns, finite coordinates, identifiers, timestamps, explicit metre
   CRS and raster overlap without automatic CRS relabeling.
3. `pipelines/drone.py`: restart-safe original-orthomosaic preparation;
   uncalibrated source-only QA remains `not_evaluated`; explicitly uncorrected
   identity products can be resumed through matching stage provenance. Physical
   correction requests still require valid physical radiometry.

Regression coverage includes actual listing shape, conflicting replicas,
checksum algorithms, same-size corruption, failed atomic transfers, naming
variation, single-package input, ambiguity, case-distinct terrain, alpha/zero
handling, source immutability, stale preprocessing signatures, wrong/missing
camera CRS, strict upload integrity, scientific status and uncalibrated
identity restart with requested corrections still blocked.

Final verification:

- **957 passed, 9 skipped, 0 failures/errors** in the full source suite
  (`966` collected; Python 3.12). The documented optional/external/legacy skips
  remain explicit in `tests-full.xml`; this is not a new installed-artifact matrix.
- **88 passed** in focused intake plus drone-pipeline/restart verification.
- Full `ruff check src tests` passed.
- API reference generation/freshness, documentation links and strict MkDocs
  verification are recorded with the final checks in the evidence directory.
- PDF rendered to ten pages and every page visually inspected.

No NEON scientific implementation was changed by this integration work. Earlier
RC2 stabilization changes remain intact. The new working-tree changes postdate
the archived exact wheel/sdist; their earlier artifact certificates apply only
to those older bytes. A replacement candidate needs the release artifact gates
before publication. No release, tag, merge or commit was performed.

## Reproduce and resume

Run from the repository with the package/environment installed and an initialized
GoCommands login. No credentials belong in scripts or manifests.

```bash
python provenance/drone-three-site-integration/2026-11-04/run_intake.py \
  --gocmd /path/to/gocmd
python provenance/drone-three-site-integration/2026-11-04/run_available_stages.py
python provenance/drone-three-site-integration/2026-11-04/verify_available_products.py
python provenance/drone-three-site-integration/2026-11-04/build_diagnostics.py
python provenance/drone-three-site-integration/2026-11-04/finalize_evidence.py
python provenance/drone-three-site-integration/2026-11-04/build_report.py
```

The intake accepts `--source` (root collection or one flight package), `--site`,
`--staging-dir` and `--evidence-dir`. The preparation/diagnostic scripts are the
recorded three-site integration recipe using repository data and the explicitly
recorded comparison grids; they are not a new general correction pipeline.
Generic helpers accept other package roots and output paths. The PDF builder
requires ReportLab/Pillow, and diagnostics use the normal scientific environment.
The existing PDF can be reviewed without rerunning anything.

Large inputs, prepared TIFFs and existing pipeline output hierarchies are under
`archive/local/drone-three-site-integration/2026-11-04/` (intentionally Gitignored).
The available derived catalog is reproducible from those local files. Production
outputs do not have a remote location yet: **none was uploaded**, consistent with
the request to upload only successfully completed and validated sites. No
historical Data Store products were overwritten.

## Remaining issues and release implications

| Class | Finding | Consequence / next action |
| --- | --- | --- |
| BLOCKER for full integration objective | No eligible corrected production chain | Complete scientific inputs, rerun corrections/translation/library QA, then upload into a new hierarchy and verify remote checksums before declaring E2E success. |
| IMPORTANT | Goldhill lowercase `dtm.tif` is unreadable despite a valid transfer checksum | Keep it excluded; choose and independently validate an appropriate terrain input. The separate uppercase DTM opens. |
| IMPORTANT | P177 runtime changes follow the earlier frozen RC2 artifacts | Build/test a replacement release candidate before publication; preserve the old byte-specific evidence. |
| DEFER, user-pending input | New location tables not ready | Discover and validate them when supplied; do not substitute older metadata silently. |
| DEFER, scientific limitation | Physical calibration and actual mosaic contributors remain unverified | Supply an accepted physical scale/offset with provenance; keep inferred geometry experimental and enforce existing acceptance criteria. |

The missing scientific inputs are not automatically software defects or reasons
to reopen unrelated scientific redevelopment. This task finishes the available
source-stage validation and leaves a reproducible, explicitly incomplete
production test ready to resume. The next recommended task is to supply/approve
the scientific inputs, then run the dependent stages and remote completion gates.
