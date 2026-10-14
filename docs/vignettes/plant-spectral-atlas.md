# A plant-balanced corrected spectral atlas

Use this workflow for a polygon library whose merged columns contain several
native wavelength grids. It is separate from the existing pixel-level spectral
library reports. The original Parquet is read in place and never copied or edited.

```bash
python examples/plant_spectral_atlas.py \
  Aug_2026_all_polygons_merged_pixel_extraction.parquet \
  --output artifacts/plant_spectral_atlas --min-plants 10
```

```python
from spectralbridge.plant_spectral_atlas import run_plant_spectral_atlas

audit = run_plant_spectral_atlas(
    "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    "artifacts/plant_spectral_atlas",
    min_plants_per_species=10,
    plant_field="GlobalID",
    flight_field="flight_id",
    source_field="source_image",
    species_field="species",
)
```

## What the supplied data establish

The 2026-10-13 audit of the supplied August 2026 merged library found 85,706
pixel rows, 45,880 labeled rows, 57 distinct labels, and 122 flight/source pairs.
`reference_product` is consistently `brdfandtopo_corrected_envi`; `source_image`
and `source_parquet` identify the corrected raster and extraction source.
These are NEON flight products, not the MicaSense or Landsat-like derived
representations elsewhere in the same table. The library does not identify
physical instrument serial numbers; grid identity alone cannot establish which
instrument flew. The labeled polygons span NIWO, WREF and YELL.

| Native grid | Flights | Bands | Wavelength range (nm) | Rounded spacing (nm) |
| --- | ---: | ---: | --- | --- |
| 1 | 59 | 426 | 382–2511 | 5 or 6 |
| 2 | 23 | 426 | 382–2510 | 5 or 6 |
| 3 | 40 | 426 | 384–2512 | 5 or 6 |

The corrected union has 1,140 **distinct** wavelength columns. Each pixel has
exactly 426 finite values: 426 / 1,140 = 37.3684%. Missingness comes entirely
from schema union in this supplied file, not atmospheric removal or individual
missing bands. Some native grids reuse precisely the same band/wavelength
column; others shift by one or two nm. There are no duplicate nominal
wavelengths encoded by separate corrected columns in this file. Band indices
repeat across the merged schema, so selecting by band number globally is unsafe.

Atmospheric regions contain finite values and zeros. The largest pixel value
is 621,788.625 at 1369 nm, backed by YELL flight L073 on 2023-07-19; another
reaches 564,722.5625 at 1870 nm. The 1350–1450 and 1800–2000 nm audit windows
have about 15.8% and 16.8% zeros, respectively. No `-9999` sentinel occurs.
Between 400 and 1300 nm, the maximum is 14,999.6143. These are measured values
from this file, not package constants or scientific acceptance thresholds.

[NEON's spectral-signature guidance](https://www.neonscience.org/resources/learning-hub/tutorials/plot-spec-sig-tiles-python)
identifies water-vapor windows around 1340–1445 and 1790–1955 nm.
The atlas explicitly excludes 1340–1450 and 1790–2000 nm, covering those windows
and the supplied request's approximate bounds. Exclusion is a documented
analysis choice; it does not repair or overwrite the source. Native plant
medians and pixel-band diagnostics retain these regions for inspection.

## Independent replication and harmonization

`polygon_id` is a local extraction index, not an independent-plant identifier.
The 8,845 labeled plant/flight/polygon observations correspond to **2,496**
distinct `GlobalID` polygons. Many appear across flights and dates; counting
all 8,845 as independent plants would exaggerate replication. All 57 labels
occur in multiple flights (2–102 flights per label). Labels are preserved
verbatim; conflicting labels within a GlobalID cause failure.

1. Within each GlobalID/flight/source/local-polygon observation, compute a
   per-band pixel median. Use only corrected columns with finite values in
   that source. Require unique ordered wavelengths and native band indices.
2. Interpolate onto 385–2510 nm at 5 nm spacing, the rounded common range of
   the three grids. Only adjacent finite native samples at most 8 nm apart
   can support interpolation. Excluded samples and missing native bands break
   segments. Never extrapolate or interpolate across an excluded window.
3. Take the median across repeated flight/polygon observations of each
   GlobalID at each common wavelength. Every observation has equal weight,
   regardless of pixel count. Each final plant has exactly one trace.
4. Compute species medians and interquartile envelopes across those plants.
   No pixel-count weights, scaling, standardization, normalization, clipping,
   or blanket removal of finite negative values or zeros is applied.

The 5 nm grid is comparable to native spacing; rounded integer wavelength
labels cannot recover the original sub-nm calibration or band response.
Linear interpolation is a transparent approximation to spectral values, not
spectral-response convolution or empirical inter-sensor calibration.

All 2,496 labeled plants survive. Every plant is finite at all supported common
wavelengths; 84.507% of the full target grid remains finite, with the remaining
15.493% deliberately excluded. The main atlas includes 22 species and 1,886
independent polygons at a threshold of ten plants. Genus-only labels do not
count as identified species in the main panel. The 55-panel supplementary
atlas includes all identified labels, including genus-only and small samples;
Other and Unidentified remain in diagnostic tables.

## Outputs, inspection, and limits

The output directory contains:

- `flight_source_grids.csv`: native columns, wavelengths, spacing, source and
  row counts for every flight/source.
- `native_band_statistics.csv`, `band_extremes.csv`: pixel-level zeros,
  quantiles and source-traceable band maxima, including excluded bands.
- `plant_flight_native_spectra.parquet`: unmasked native pixel medians as
  paired wavelength/value lists, plus polygon and source provenance.
- `plant_flight_spectra.parquet`: common-grid spectra for individual observations.
- `plant_harmonized_spectra.parquet`: one row per independent GlobalID,
  species, repeated-observation/pixel counts, and backing flight identities.
- `species_sample_sizes.csv`, `species_flight_counts.csv`,
  `species_median_spectra.parquet`: independent counts, flight occurrence,
  and medians across plants.
- `common_coverage.csv`, `wavelength_coverage.pdf` and `.png`: supported
  plant/observation counts and all three native grids.
- `species_atlas` and `supplementary_atlas`, each as PDF, SVG and 350 dpi PNG.
- `audit.json`, `manifest.json`: counts, choices, source/implementation hashes,
  and output checksums for verification and reuse.

The PDF and SVG contain vector traces, envelopes, labels and axes. Every faint
trace is an independent polygon, the dark line is the species median, the
subtle envelope is the plant-level IQR, and gray windows have no traces.
All panels share wavelength axes and full finite value limits without trimming
extreme plants. Native values remain labeled as stored spectral units: Parquet
has no scale metadata. Package correction/export code preserves stored units;
although NEON normally uses scaled reflectance, the source headers are needed
to certify a conversion for this particular archive.

Visual inspection of the actual main and supplementary exports checks ordered,
continuous supported segments, no blank panels, and no merged-grid spikes.
The observed rise into the near infrared and lower shortwave-infrared values
are consistent across the dominant labeled canopy groups; visual shape alone
does not validate field identification, correction accuracy, or plant purity.
The analysis preserves field labels, and GlobalID identifies a polygon presumed
to represent an individual plant. Some polygons could contain mixed crowns.
Equal observation medians also summarize acquisition dates/geometry; they are
not a time-invariant physiological measurement. The retained shortwave edge
can contain zeros or abrupt native noise, which remains visible and traceable.

Spectral reads are projected in batches of 32 columns; pixel tables are never
materialized as an additional cache. Memory scales with metadata rows, one
spectral batch, and the much smaller observation-by-union-band matrix. Progress
reports each band batch. Completed outputs are reused only when input,
implementation, options, and all output hashes match. Rebuilds stage results
before publication and write the completion manifest last. An interrupted
publication will fail checksum validation and be rebuilt on restart.
Large supplied data and generated derivatives are ignored by Git. Run the
regression tests with `pytest -q tests/test_plant_spectral_atlas.py`.

## Raw, corrected, darkened, and sensor comparison layouts

```bash
python examples/plant_spectral_comparison.py \
  Aug_2026_all_polygons_merged_pixel_extraction.parquet \
  --output artifacts/plant_spectral_atlas/comparisons --min-plants 10
```

```python
from spectralbridge.plant_spectral_comparison import run_plant_comparison_atlas

result = run_plant_comparison_atlas(
    "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    "artifacts/plant_spectral_atlas/comparisons",
    min_plants_per_species=10,
    dpi=350,
)
```

This creates the three requested layouts, each in PDF, SVG and 350 dpi PNG:

| File stem | Layout |
| --- | --- |
| `raw_corrected_darkened_rows` | One species per row; raw NEON, corrected NEON, darkened derived sensor bands as columns |
| `three_panel_atlas` | One alphabetical species per row with raw, corrected and darkened aligned as columns; identical to `raw_corrected_darkened_rows` |
| `landsat_neon_drone_rows` | One species per row; darkened OLI-like, corrected NEON, darkened MicaSense-like columns |
| `raw_atlas`, `corrected_atlas`, `darkened_atlas` | Separate single-product atlases; one alphabetical species per row |

Rows represent species; individual plants remain faint traces inside each cell.
For sensor products, trace vertices are the discrete native band centers. The 22-species cohort contains exactly the same
1,886 independent GlobalID plants in every layout. The underlying matched table
retains all 2,496 labeled polygons, including labels excluded from main panels.
The threshold uses matched independent plant counts. Species names are
alphabetized in every comparison layout; each species occupies its own row.
The three stage columns refer to the same species on each row, rather than
placing several species inside a separate raw/corrected/darkened atlas block.

The raw audit found the same three native 426-band grids as corrected spectra,
with 37.3684% finite union-schema entries and all 426 native bands present for
every pixel. Raw spectra get their own source-column audit, pixel medians,
gap-preserving harmonization, and equal-observation aggregation. Selecting raw
never reuses corrected spectral values.

`olioli` has seven bands; `micasense` has ten bands. Every selected sensor band
is finite for every supplied pixel. These columns are the final brightness-
adjusted products, distinguished from their `*_undarkened` counterparts by the
package's source/export contracts. Their values are read as supplied. The
comparison does not apply brightness coefficients a second time.

The Landsat and drone columns are **NEON-derived sensor representations**, not
independent satellite or drone measurements. NEON is the corrected hyperspectral
reference in that layout. In the darkened column, OLI uses blue-gray solid traces and MicaSense uses muted
brown dashed traces. Each faint trace belongs to one plant; stronger traces are
species medians and vertical bars at band centers show the plant-level IQR.
Following the requested trace styling, adjacent band centers are joined visually.
The vertices remain the seven or ten supplied band samples: no additional
wavelength samples, smoothing, scaling or analytical interpolation are created.
Missing band values remain NaN and break individual traces. Connections across
wide intervals are plotting guides, not measured continuous hyperspectral
reflectance. Exact common band centers are retained rather than forcing seven
or ten bands onto the hyperspectral 5 nm grid. OLI and MicaSense therefore
have intentionally different wavelength coverage on the shared 385–2510 nm axes.

All layouts use the same full finite y limits across the matched plants and all
four selected products. No plant receives pixel-count weights, and no extrema
are clipped. Remaining sharp terminal rises are present in native observations:
for GlobalID `9805c5ef-679b-4644-95c6-fd8c55054b4e` (*Acer circinatum*), the raw
2502/2507/2512 nm medians are 1344/3032/7353 in WREF L054-2 and
1275/2830/11694 in WREF L055-1, both acquired 2023-06-28. Corrected spectra also
retain that rise. These examples identify native terminal-band behavior rather
than merged-schema spikes; the originating rasters/headers would be needed to
determine its physical or processing cause.

The `products/{raw,corr,olioli,micasense}/` directories contain separately audited
plant/flight and independent-plant tables, native wavelength grids, band
statistics, species medians, and checksum manifests. These are compact polygon
and plant derivatives, not pixel caches. `matched_plants.parquet` and
`matched_species_sample_sizes.csv` identify the common cohort;
`plotted_species_medians.parquet` records the exact medians and per-band counts
used in the row layout. `comparison_audit.json` records unmatched counts,
stages, band counts, species order, full plotting bounds, and provenance.
The supplied file loses no plants when matching the four products.

Stage aggregation checkpoints are independently reusable. Figure rebuilds are
staged, and `comparison_manifest.json` is published last; reuse verifies source,
implementation, options, and all figure/table checksums. The existing ignored
atlas directory also covers these new large outputs. The earlier corrected-only
atlas remains in its original directory.

## Regional views from source-table names

After the comparison analysis has completed, regional analysis reuses its compact
plant spectra and reads only identity/provenance columns from the source library:

```bash
python examples/plant_spectral_regions.py \
  Aug_2026_all_polygons_merged_pixel_extraction.parquet \
  --comparisons artifacts/plant_spectral_atlas/comparisons \
  --output artifacts/plant_spectral_atlas/comparisons/regional \
  --min-plants 10
```

```python
from spectralbridge.plant_spectral_regions import run_regional_plant_atlas

regional = run_regional_plant_atlas(
    "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    "artifacts/plant_spectral_atlas/comparisons",
    "artifacts/plant_spectral_atlas/comparisons/regional",
    min_plants_per_species=10,
)
```

The source of the region code is the **source table's basename**. For example,
`NEON_D13_NIWO_DP1_..._polygons_merged_pixel_extraction.parquet` identifies NIWO.
Parent directories are not used to guess the region. Each extracted code is
cross-checked against `flight_id` and populated `aop_site` metadata. The descriptive
ecoregion names below come directly from the supplied `ecoregion` column. They
are preserved as supplied, rather than inferred from geographic coordinates.
A site is the grouping unit here; its ecoregion label does not imply that one
sampled site represents an entire ecoregion population.

The audit resolves all 122 source tables and all 2,496 labeled independent plants
without disagreements or unknown sites. Every GlobalID belongs to exactly one
site, so its previously aggregated spectrum can be reused without mixing sites.
A library containing a GlobalID that spans sites fails explicitly.

| Site | Supplied ecoregion label | Source tables/flights | Matched labeled plants | Species meeting within-site minimum 10 | Plants in those species |
| --- | --- | ---: | ---: | ---: | ---: |
| NIWO | SouthernRockies | 32 | 1,223 | 12 | 964 |
| WREF | Cascades | 40 | 704 | 10 | 540 |
| YELL | MiddleRockies | 50 | 569 | 8 | 354 |

The threshold applies **within each site**, never to a species' pooled count.
The union of qualifying species has 21 species; the earlier pooled atlas has
22. For example, a pooled total of ten or more plants does not qualify a species
at any site where its own sample is below ten. Other, Unidentified, and genus-only
labels remain in count tables but are excluded from these main figures.

Each `regional/{NIWO,WREF,YELL}/` directory contains all six earlier layouts:
raw/corrected/darkened species rows, Landsat/NEON/drone species rows, the
`three_panel_atlas` alias of the aligned three-column layout, and standalone
raw, corrected, and darkened atlases. Each species occupies its own row. Within
a site, each layout uses the same matched independent plants and alphabetical
species order. Every
site uses the same wavelength axes and full finite y limits, computed across
all qualifying regional species/plant cohorts and the four products. Sensor traces connect discrete native band centers visually without creating
new spectral samples; NEON atmospheric exclusions remain gaps.

`corrected_by_region_rows.{pdf,png,svg}` directly compares sites: species are
rows and NIWO, WREF, YELL are columns. A cell shows its own plant traces, median,
IQR, and sample size when it meets the threshold. Other cells say either
“No sampled plants” or “n = …; below minimum 10.” Absence from this extraction
sample is not evidence of biological absence. Species names are alphabetized, with the same row shared across all site
columns. *Pseudotsuga menziesii*,
for example, has 143 NIWO, 138 WREF and 128 YELL plants and qualifies at all three.
Site differences are descriptive comparisons of sampled spectra, not evidence
that region alone caused those differences; acquisition, corrections, canopy
composition and field sampling can also differ.

The regional diagnostic outputs are:

- `source_table_regions.csv`: complete source-table paths, flight IDs, resolved
  sites, pixel rows, labeled pixels and independent labeled plants per source.
  Per-source plant counts must not be summed as independent regional totals,
  because one GlobalID can occur in several flights.
- `matched_plant_regions.parquet`: one matched GlobalID row per plant and its
  validated site, species, pixel count and repeated-observation count.
- `species_region_sample_sizes.csv`, `species_region_counts_wide.csv`: independent
  species/site counts and eligibility, including excluded labels and small samples.
- `region_summary.csv`: the source and independent plant counts above.
- `regional_corrected_medians.parquet`: exact per-wavelength site/species medians
  and contributing plant counts used in the direct comparison.
- Per-site `plotted_species_medians.parquet`: medians/counts for all four products.
- `regional_audit.json`, `regional_manifest.json`: decisions, input/output
  checksums, counts and shared bounds.

Each figure is a vector PDF/SVG with a 350 dpi PNG. This step does not decode any
source spectral pixel columns, reopen rasters, or create another pixel cache.
It verifies source bytes and compact product hashes, including an end-of-run
check that inputs did not change. Completed regional figures are reused only
when inputs, rendering code, options and all output hashes match. Results are
staged and the completion manifest is written last. Outputs remain under the
ignored atlas directory.

## Boosted 1–99% quantile signatures

The requested integer percentiles 1 through 99 produce **99 fitted lines**.
These are conditional quantile estimates, not 99 new plants or 99 observed
whole-spectrum trajectories. Species fits describe variation across independent
GlobalID plant medians. Individual fits use the repeated-flight polygon medians
of a single GlobalID. Their spread can reflect flight/date/geometry differences,
model approximation and repeat-observation variation; it is not between-plant
replication. One-flight polygons cannot estimate repeat-flight variability and
are explicitly flagged.

Install the optional backend, then reuse the completed comparison and regional
plant tables:

```bash
python -m pip install -e '.[quantile-models]'
OMP_NUM_THREADS=1 python examples/plant_spectral_quantiles.py \
  --comparisons artifacts/plant_spectral_atlas/comparisons \
  --output artifacts/plant_spectral_atlas/quantile_models \
  --workers 8
```

```python
from spectralbridge.plant_spectral_quantiles import (
    QuantileModelConfig, run_boosted_quantile_atlas, rank_unknown_spectrum,
)

config = QuantileModelConfig(workers=8)
result = run_boosted_quantile_atlas(
    "artifacts/plant_spectral_atlas/comparisons",
    "artifacts/plant_spectral_atlas/quantile_models",
    config=config,
)
```

Defaults are 80 boosting rounds, learning rate 0.1, maximum tree depth 5,
256 histogram bins, seed 0, and quantiles 0.01, 0.02, …, 0.99. Every worker uses
one XGBoost thread. Wavelength is the predictor and the supplied stored spectral
value is the response. All requested quantiles use the `reg:quantileerror`
objective with separate output trees in a single training call. This uses the
[XGBoost quantile implementation](https://xgboost.readthedocs.io/en/release_2.1.0/python/examples/quantile_regression.html);
no custom replacement boosting algorithm is introduced.

A spectrum contributes equal total training weight within each supported
segment. Species spectra are already medians of independent plants; individual
spectra are equal-weight flight/polygon observations. Pixel counts are never
used as fitting weights. NEON fits train separately on contiguous supported
wavelength segments, and predictions are saved only at existing common-grid
samples. Atmospheric and other unsupported bands stay NaN. OLI/MicaSense fits
retain their seven/ten supplied export coordinates; connections in the figure remain
visual guides, not additional measured samples. No scaling, clipping or
normalization is applied.

The supplied main cohort contains 1,886 independent plants in 22 pooled species.
There are 52 species/scope groups: 22 pooled, 12 NIWO, 10 WREF, and 8 YELL.
For four spectral stages, the complete run fits 208 full species signatures,
208 separate training-only species signatures, and 7,544 individual signatures:
7,960 signature fits total, each with 99 conditional quantile predictions.
This is a substantial modeling run; `--stages raw corr` restricts stages,
`--rounds` adjusts boosting rounds, and `--skip-individual-pdf` omits the large
individual PDF reports. All changes are recorded in configuration/provenance.

Boosting can produce crossing quantiles. Each checkpoint retains both the raw
fitted curves and an explicitly **pointwise rearranged** version, sorting values
across quantile levels at each wavelength. Figures and matching use the ordered
version. Crossing fractions and maximum rearrangement are reported; raw fitted
values remain available for audit. Rearrangement does not create observations,
and an ordered pointwise quantile curve does not necessarily describe one
physically observed plant trajectory.

### Outputs and fit diagnostics

- `model_index.parquet`: species or individual identity, site/scope, stage,
  full/training partition, independent plant and flight-spectrum counts,
  supported bands, crossing metrics, training median RMSE, empirical-quantile
  RMSE, low-replication flags, timing and checkpoint names.
- `checkpoints/*.npz` and `.json`: native/common wavelengths, all quantile levels,
  raw curves, ordered curves, empirical median, exact training-array and fitting
  implementation hashes, backend version and prediction-file checksums.
- `{ALL,NIWO,WREF,YELL}_species_quantiles.{pdf,png,svg}`: alphabetical species
  rows with fitted quantile fans, strong 50th-percentile fit and dotted observed
  median; separate raw NEON, corrected NEON, Landsat OLI and MicaSense columns.
- `{NIWO,WREF,YELL}_individual_examples.{pdf,png,svg}`: one deterministic,
  source-traceable GlobalID example per modeled species occurring at that site,
  including species/site combinations below the species-level sample threshold.
- `{NIWO,WREF,YELL}_all_individual_quantiles.pdf`: every modeled GlobalID,
  alphabetized by species and then GlobalID, with five plant rows per page.
  Short display identifiers are backed by complete GlobalIDs in the model index.
- `training_holdout_plants.parquet`, `held_out_species_matches.csv`,
  `matching_validation.csv`, `held_out_individual_reference_matches.csv`:
  explicit independent-plant split and matching evidence.
- `quantile_audit.json`, `quantile_manifest.json`: configuration, counts,
  interpretation limits, validation measurements and output checksums.

The models are derivative wavelength-grid signatures; large serialized tree
ensembles are not retained. Exact training inputs, parameters, code and backend
version support refitting, while saved predictions support matching on the
recorded grids. Fits checkpoint independently. Presentation/validation changes
and worker-count changes reuse scientifically identical training matrices and
parameters; fitting changes or altered inputs invalidate the corresponding fits.
A completed run is reused only after checksum validation. Final completion
requires source-product stability and all fits, diagnostics and requested reports;
an interrupted run resumes from valid individual checkpoints. No raster or source
pixel spectral columns are reopened. Generated models and reports remain ignored
by Git.

### Unknown-spectrum matching and validation

```python
# Supply an increasing wavelength vector and spectral values in the SAME stored
# units as the selected reference stage; NaN denotes missing observations.
ranking = rank_unknown_spectrum(
    "artifacts/plant_spectral_atlas/quantile_models",
    wavelengths_nm,
    spectral_values,
    stage="corr",
    region="NIWO",       # None uses pooled species references
    level="species",     # "individual" ranks polygon references
)
print(ranking.head())
```

The ranking score is twice the mean pinball loss across the 99 quantiles and
shared supported wavelengths: a discrete, truncated integrated-score
approximation. Lower is closer in the supplied units, **not an identification
probability**. Query gaps are preserved and no extrapolation is performed.
Hyperspectral interpolation uses only adjacent supported samples at most 8 nm
apart; sensor queries require exact shared band centers. By default at least
half the reference's supported bands must be shared. Stages are scored
separately; no automatic unit conversion or cross-sensor calibration is inferred.
Individual reference searches can exclude known GlobalIDs with
`exclude_plant_ids`, and all reference/checkpoint checksums are checked before
matching.

Validation assigns approximately 20% of each species/site's plants to a
reproducible holdout, leaving singleton site/species groups in training. All
flights and pixels of a GlobalID stay on the same side. Separate species models
are fit using training plants only; held-out plants are also excluded from the
individual-reference candidates. Full-data reference fits are used for the final
figures/API, not to evaluate held-out species matches. Reported measurements
include top-1/top-3 accuracy, macro species accuracy, comparison with an
empirical-median RMSE baseline, and held-out 5–95% pointwise band coverage where
those quantiles are configured.

These tests measure within-library identification, not transfer to new flights,
sites, field populations or genuinely independent sensors. Pointwise scoring
also omits spectral covariance. The 99 plotted curves do not increase the
number of independent plants; very low/high quantiles are weakly supported for
small species samples and few repeat-flight observations. Training shape fit,
quantile coverage and identification accuracy are separate diagnostics, and
matching improvement must be judged from the saved held-out results.

### Coordinate audit and observed validation limits (2026-10-13)

The supplied MicaSense columns are labeled 475, 560, 668, 717, 840, 841, 842,
843, 844, 845 nm. This matches the legacy five-band fallback followed by
one-nanometer padding, rather than the packaged ten-band grid. Physical band
identity therefore remains **unverified**. Values and ordering are retained;
no replacement wavelengths are guessed. Figures flag this condition and model
indices/audits record `coordinate_status`. `rank_unknown_spectrum()` rejects
physical-wavelength MicaSense matching by default. The explicit
`allow_unverified_export_coordinates=True` option permits comparisons against
the identical archive labels only; it does not verify those wavelengths.
NEON and OLI coordinates are unaffected. Source headers are needed to resolve
this issue before physical MicaSense interpretation or external matching.

The completed run includes 7,960 signatures for 1,886 independent plants.
There are 363 independent held-out plants. Pooled corrected-species top-1
accuracy is 15.70%, equal to the empirical-median RMSE baseline; the majority
class baseline is 22.04%. Corrected species accuracy by site is 18.62% NIWO,
17.31% WREF and 37.88% YELL. Individual-reference corrected matches achieve
34.04%, 32.08% and 52.17% respectively, without consistently improving on
empirical individual-template baselines. These results do not establish a
reliable species identifier. Reproduce the additional baselines with
`python examples/evaluate_quantile_matches.py`.

Outer quantiles can substantially underfit and appear nearly flat. For example,
the NIWO *Abies lasiocarpa* corrected fit at 425 nm has fitted 99th percentile
3529.3 versus empirical 286.6, in the supplied stored units. This is a fitting
limitation, not an observed extreme spectrum. Hyperparameter tuning and
independent validation remain necessary before uncertainty or identification
claims. Sixty-two modeled plants have only one flight observation; their
individual quantile fans cannot establish repeat-observation variation.
See the recorded local validation report under
`provenance/quantile-models/2026-10-13/VALIDATION.md`.

### Compare one quantile across every individual plant

```bash
python examples/plant_quantile_overlays.py
```

This reads verified completed checkpoints without refitting. Corrected and raw
NEON each receive a separate 10×10 PDF/PNG under
`artifacts/plant_spectral_atlas/quantile_overlays`. Read left to right, top to
bottom: 100%, 99%, …, 1%. The 100% slot explicitly states **not fitted** because
the confirmed models cover 1–99%; it is not replaced by a maximum or another
quantile. Every populated subplot contains one ordered fitted curve from each
of the 1,886 individual GlobalIDs, colored by species. Shared full-range axes,
NaN wavelength gaps, negative values and source units are preserved. Trace
layers are rasterized in PDFs for manageable size; labels remain vector text.
Low-alpha overlap is qualitative and is not a normalized density. Existing
extreme-quantile underfitting remains visible. `overlay_audit.json` records source
manifest/code/output hashes and the complete included GlobalIDs.

### Separate derived-sensor quantile views

```bash
python examples/plant_quantile_overlays.py --stages olioli micasense
```

Landsat OLI and MicaSense each receive their own descending 10×10 PDF/PNG,
with one same-quantile curve per individual plant. Each uses its own supplied
seven- or ten-band coordinate range; there is no cross-sensor overlay, added
spectral sample or NEON atmospheric shading. MicaSense uses dashed traces and
explicitly unverified export coordinates. Species-row and individual-row
quantile reports now have four columns: raw NEON, corrected NEON, derived
Landsat OLI, derived MicaSense. Stored fits, counts, gaps, holdouts and scoring
are unchanged; only presentation changes. Both sensors remain products derived
from NEON, rather than independent satellite/drone observations.

### Boosted species quantiles by acquisition year and site

```bash
python examples/plant_spectral_years.py --workers 8
```

This produces four new PDF/SVG/PNG panels under
`artifacts/plant_spectral_atlas/year_site_quantiles`, one each for raw NEON,
corrected NEON, derived Landsat OLI and derived MicaSense. Species run
alphabetically down the rows; columns run chronologically by acquisition year,
then site. All year/site combinations are shown, including explicitly unavailable
acquisitions. Cells with fewer than ten independent plants are annotated rather
than fitted. Each eligible cell shows 99 boosted quantile curves (1–99%), a
strong fitted median and dotted empirical median, using the existing model
configuration and fitting/checkpoint helpers.

Year and site come from the **source-table basename**, cross-checked against
`flight_id` and populated `aop_site`. Both dated directional-reflectance and older
timestamped-reflectance NEON names are supported. Field survey year, polygon
editing dates and ancestor folder names are not acquisition dates. The supplied
library has NIWO 2020 and 2023, WREF 2023 and YELL 2023; WREF/YELL 2020 are
unavailable.

The workflow reads verified compact plant-flight spectra. Pixel medians already
exist within each flight/polygon observation. A separate equal-observation median
is computed for each GlobalID **within its acquisition year/site**, before fitting
species quantiles with equal independent-plant weights. All-year plant medians
and all-year models are not relabeled as year-specific models. No raster/source
pixel spectral decoding, normalization, clipping or missing-band filling occurs.
Raw/corrected atmospheric gaps and discrete sensor coordinates remain unchanged;
MicaSense export labels retain their unverified-coordinate warning. Plot bounds
use the full fitted/source ranges and never alter analytical values.

`plant_year_site_cohorts.parquet`, `species_year_site_counts.csv`,
`year_site_counts.csv` and `source_year_site_provenance.csv` document the cohorts,
within-year observation counts and supporting flight/table identities.
`model_index.parquet`, `checkpoints/`, `year_site_audit.json` and
`year_site_manifest.json` record models, input/output/code hashes, configuration
and counts of plants observed in multiple years. Compatible fit checkpoints are
reused after interruption or rerun.

These are descriptive species distributions. Yearly cohorts can differ; the
same GlobalID in two years is a repeated plant, not two independent plants for a
between-year inference. The panels do not establish paired temporal change,
year effects, calibrated uncertainty or improved identification. Existing
outer-quantile fit limitations remain applicable; no new classifier validation
is claimed for the year-specific fits.

### Detailed methods and robustness review

The report authoring sources are under `provenance/plot-report/2026-10-13/`.
`analyze_report.py` verifies saved outputs and calculates compact report evidence
without refitting models; `build_report.py` renders the illustrated PDF using
ReportLab, Pillow and pypdf; `verify_report.py` checks evidence/attachments,
accuracy intervals, source hashes and page geometry. Use the repository Python
environment for analysis and a runtime with the PDF dependencies for authoring.

The generated report is
`output/pdf/plant_spectral_review/spectral_plots_methods_robustness_report.pdf`.
It synthesizes all figure families, includes the full original-PDF inventory,
embeds compact evidence and gives scientific limitations separately from software
contract checks. It does not bind every source plot page into one document.
New Wilson intervals condition on the fixed holdout and assume independent
Bernoulli outcomes; they are not flight/site-clustered uncertainty or model
selection evidence. All report artifacts remain Git-ignored; authoring and
verification sources remain reviewable.
