# Figure 4 data dictionary

All CSVs are UTF-8, comma-delimited with a header row. Empty numeric cells mean
unavailable, **not zero**. No imputation is performed. Category order:
Deciduous; Evergreen; Herbaceous; Woody shrub; Non-vegetated & dead.

Exact current sensor values: `HLS L30 NBAR`, `NEON AOP → OLI/OLI-2-like`,
`Drone → OLI/OLI-2-like`. Unicode arrows/dashes are intentional UTF-8 text.
Bands `B1`–`B7` denote coastal, blue, green, red, NIR, SWIR1 and SWIR2.
Drone observations only support B1–B5.

## data/spectral_observations_by_footprint.csv

One row per sensor and footprint identity. A footprint is an observational unit,
not a pixel-sized replicate of a polygon. NEON repeat years are averaged per
polygon and drone pixels are reduced by polygon medians **before** this file.

| Column | Meaning |
| --- | --- |
| sensor | Exact display name above |
| category | Recorded researcher PFT, verbatim |
| footprint_id | NEON/drone GlobalID, or HLS physical cell ID (EPSG plus projected centre) |
| site | Source site, retained for provenance; no reweighting during plotting |
| calculation_dtype | Arithmetic precision for normalization: float32 for the original drone summaries, float64 for Landsat/NEON; keep one value per sensor |
| B1 … B7 | Pre-normalization band values; drone B6/B7 blank |

Real Landsat values are HLS L30 v2 NBAR reflectance (DN ×0.0001); drone values
are verified physical reflectance. NEON source table units are retained without
inventing an absolute scale conversion. Plot normalization is dimensionless and
removes each spectrum's common scale. These units are not a license to treat all
three sources as interchangeable absolute reflectance measurements. The sources
have different dates, locations and footprint sizes.

## data/spectral_medians_and_interquartile_ranges.csv

One row for every sensor/PFT/band, including unavailable bands: 3 × 5 × 7 = 105.

| Column | Meaning |
| --- | --- |
| sensor, category, band | Unique key |
| n | Positive integer number of retained footprints, same across bands per sensor/PFT |
| median | Median normalized band value; blank for drone B6/B7 |
| q25, q75 | Linear 25th/75th percentiles across normalized footprints |

For each complete footprint, divide **all available bands**, including SWIR,
by that footprint's B1+B2+B3+B4+B5 sum. Require that sum >0 and all available
values finite. Then compute quantiles, giving each footprint one vote.
`q25 ≤ median ≤ q75`; no confidence-interval calculation is performed.
All normalized values are dimensionless. Heatmap values equal absolute
sensor-pair median difference ×100, and are descriptive differences on the
normalized scale, not probabilities, effect-significance flags, or necessarily
percentage differences in physical reflectance.

## data/pft_separability_and_identifiability.csv

Exactly 15 rows: one per sensor/PFT. Tests are not recalculated by the renderer.

| Column | Meaning |
| --- | --- |
| sensor, category | Unique key |
| separability_status | `supported_test_counts`, `provisional_matched_test`, `insufficient_patch_support`, or `no_matched_reference` |
| supported_tests | Count meeting the archived adjusted-p criterion (integer) |
| total_tests | Number of testable comparisons/cohorts (integer; varies by source) |
| matched_n | Matched footprint count for this class in the provisional Landsat contrast |
| adjusted_p | Holm-adjusted NPC p, [0,1]; blank when not tested |
| identifiability_status | `available`, `provisional_patch_recall`, `insufficient_training_patches`, or `untested` |
| unseen_polygon_recall | Recall fraction [0,1] on held-out polygons; display first |
| held_out_patch_correct, held_out_patch_total | Integer held-patch prediction counts; must agree with recall |
| held_out_patch_recall | Landsat-only recall on held-out patch medians; single daggered percentage |
| held_out_site_recall | Recall fraction [0,1] on held-out sites; display second; blank if unavailable |

Counts are formatted as supported/total, recall fractions as whole percentages,
and p-values to two decimals. Full numeric precision remains in CSVs. Current
daggered HLS rows summarize four pooled NPC contrasts and class recall on held-
out patch medians. They share ten unique contrasts, three meeting Holm p<=.05.
Historical matched_n/adjusted_p fields remain supported for archived tables, but
are blank in the current Landsat rows. Drone double-dagger rows denote the separate exploratory
calibration-library protocol. See the caption for permutations, blocking, Holm
families, models, date, site and reference-label limitations. Statistical status
is distinct from the descriptive spectral counts in panel A.

## evidence/ reference tables

These are copied supporting results, not additional renderer inputs. Original
column names are retained to avoid silently changing analytical provenance.

- `neon_pairwise_separability.csv`: PFT pairs `a`/`b`, site/year cohorts and archived
  `OLI_supported` decisions; other original columns are retained.
- `neon_held_out_recall.csv`: filter `representation=OLI`, `experiment=hierarchy`;
  mean `recall` by `label` and `kind` (`plant`/`site`) supplies panel B.
- `landsat_photo_screened_separability.csv`: primary rows use `threshold=0.95`,
  `shift_m=0`. `n_a/n_b`, `p_npc_holm` and status define the matched contrast;
  sensitivity analyses remain available in other rows.
- `landsat_matched_test_memberships.csv`: candidate IDs, source scene/acquisition
  and selected per-footprint bands; repeated threshold/shift memberships must
  not be treated as independent footprints.
- `drone_pairwise_separability.csv`: `a/b`, group sample sizes and mixed-site
  counts, raw NPC probability and `p_npc_holm`. Missing p means untestable.
- `drone_held_out_predictions.csv`: one held-out prediction per GlobalID per
  evaluation `scheme`; `truth_in_training` distinguishes a missing training
  class from a measured transfer failure. `fold` is meaningful within scheme.

Source paths and hashes are in `provenance.json`; changes to analytical methods
require an updated caption and new source provenance, not only edited displays.

- `landsat_exploratory_patch_separability.csv`: exact NPC results for pooled patch
  permutations and within-region mixed support; use the pooled scope for B.
- `landsat_exploratory_held_out_predictions.csv`: patch and secondary pixel
  predictions, explicit patch/region holdouts and training-class support flags.
- `landsat_exploratory_patch_median_spectra.csv`: direct-reflectance seven-band input
  medians for 24 spatial groups in the expanded nominal HLS cohort.
- `landsat_exploratory_identifiability_summary.csv`: class recall by scheme/unit.
- `landsat_exploratory_sensitivity_overview.csv`: primary and sensitivity results.

- `landsat_normalized_sensitivity_*.csv`: previous normalized table evidence,
  retained explicitly as historical Collection 2 sensitivity; not the current B inputs.
- `landsat_geography_conditioned_prediction_test.csv`: historical Collection 2 diagnostic
  of full held-patch macro recall under all 180 within-region assignments.

## Current HLS table fields

`evidence_product` identifies the expanded nominal-95%-footprint HLS L30 cohort.
`sensor` is `HLS L30 NBAR` in both A and B; no legacy C2 sensor key is plotted.
`planned_pairs` and `total_tests` are four per class. `supported_test_patches`
counts held patches whose true class exists in training; all current primary
held-patch targets have support. Correct/total counts must agree with recall.
The renderer still supports explicit insufficient-test/training statuses for
future or sensitivity inputs and never converts unavailable recall into 0%.

`landsat_hls_figure_table_summary.csv` is the current main-table numeric source.
`landsat_hls_pairwise_balanced_accuracy.csv` and its predictions retain a separate
binary predictive-discrimination diagnostic; they do not replace NPC counts.
`landsat_hls_expanded_source_support_sensitivity_*` is the new 161-cell sensitivity.
Older nominal/strict-only/C2 files are retained history; their cohort names/counts
must not be confused with the current main table.

## HLS-specific spectral provenance columns

HLS rows additionally carry `source_product` (HLS L30 v2 NBAR), `source_item_id`
(actual selected HLS granule), `patch_group_id`, `reference_basis` and
`brdf_normalized`. These are blank where not supplied for other sensors.
`site` is the reference region for HLS cells. Current HLS category counts in A
are 77/110/99/165/45 (plot order); all 496 cells match the exact source behind B.
A normalizes each cell before median/quantiles; B uses direct-reflectance patch
medians. The historical C2 files under evidence are not renderer inputs.

Display label: `Landsat HLS L30 NBAR`; internal sensor key: `HLS L30 NBAR`.
This is a display-only clarification, with no data or statistical changes.
