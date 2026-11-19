# HLS L30 separability and identifiability

Run 19 November 2026. Primary results use the rebuilt 114-cell strict source-area
support HLS L30 v2 NBAR cohort (nine spatial patch groups), not the previous
Collection 2 surface-reflectance table. Labels remain provisional.

| PFT | Cells | Patches | Supported/testable contrasts | Held-patch recall |
| --- | ---: | ---: | --- | --- |
| Deciduous | 32 | 2 | 0/2 | 50% (1/2) |
| Evergreen | 20 | 2 | 0/2 | 100% (2/2) |
| Herbaceous | 30 | 3 | 0/2 | 100% (3/3) |
| Woody shrub | 16 | 1 | Insufficient patches | NA: absent from training |
| Non-vegetated & dead | 16 | 1 | Insufficient patches | NA: absent from training |

The D/E/H rows share three unique pooled contrasts. All adjusted p-values are
1.0: unadjusted exact NPC p is 1/3 (D/E), 0.3 (D/H), and 0.1 (E/H).
Shrub/non-vegetated comparisons lack the declared minimum of two patches per
class. All ten planned pairs remain in the Holm family with unavailable p set
to one for adjustment; unavailable p-values themselves remain blank in outputs.
No within-region contrast has at least two patches per compared class. Pooled
exchangeability across geography/season remains an unvalidated assumption.

Whole-patch leave-one-out evaluation uses a fixed StandardScaler and balanced
logistic regression (C=1) fitted only on equally weighted training patch medians.
All seven direct NBAR reflectance bands enter; plot normalization is not used.
When a class has only one patch, its sole holdout removes the class from training.
Those predictions/support flags are saved but **do not become a 0% class recall**.
Six of seven supported target patches are correct; an overall five-class primary
accuracy is unavailable. Held-region predictions and class-support flags are also
saved. No region-transfer or independently validated reference claim is made.

## Broader nominal-support sensitivity

The separate `nominal_support_sensitivity/` analysis uses 382 cells in 19 patches,
requiring nominal 95% footprint cover without the extra conservative source-area
screen. All ten pooled contrasts are testable; none passes Holm. Whole-patch
identification gives 16/19 (84.2%): D4/5, E3/3, H5/5, shrub3/3, non-vegetated1/3.
This is a different reference selection, not a substitute for the strict table.
Neither cohort's statistics should be copied into the other's caption/counts.

## Files and provenance

Each cohort folder contains exact pair p-values/statuses, patch-median spectra,
every patch/secondary pixel prediction, class-level support and recall summaries,
and the Figure 4 numeric table summary. Secondary pixel predictions are not extra
independent replicates. `cohort_comparison.csv` keeps supported and unsupported
fold counts separate; `five_class_patch_accuracy` is blank if a target class is
absent from any training fold. `manifest.json` hashes inputs, code and all CSVs.

Original HLS rebuild files, label basis and source dates are under the sibling
`hls-l30-rebuild/`. Its nominal and source-area screens are geometric/structural
proxies, not independent proof of current PFT purity. Evergreen uses older lidar
structure with provisional 2023 evergreen identities. The source-support policy
was fixed before this HLS test run; no threshold or unit was changed to obtain
significance. This analysis reuses existing NPC and classifier helpers without
modifying package statistics or old C2 results.

## Reproduce from repository root

```bash
.venv/bin/python examples/publication_figures/landsat_hls_pft_tests.py
.venv/bin/pytest -q tests/test_landsat_hls_pft_tests.py tests/test_landsat_exploratory_pft_tests.py tests/test_landsat_photo_annotation.py tests/test_landsat_hls_reference_rebuild.py
```

No network access or raster reads are needed: compact rebuilt HLS tables are read
in place. Figure reproduction remains in `publication/figure_4_plant_functional_types/`
with local numeric evidence, code, caption and standalone checks. Panel B uses
these strict HLS results; Panel A retains its different descriptive C2 cohort.
