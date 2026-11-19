# Landsat statistical-design audit and concrete next steps

19 November 2026. Existing runs are preserved. No p-value threshold, spatial unit,
model hyperparameter or reference label was changed to obtain significance.

## Corrected interpretation and table inputs

The 95% previously shown is classification of normalized **patch medians**, not
unknown-pixel or new-region identification. The archived NEON and drone evidence
uses stored/direct reflectance; the new Landsat primary used plot normalization.
Direct Landsat reflectance instead gives 85% held-patch accuracy
(17/20) and 87% macro recall. Class recall is 80% deciduous,
100% evergreen, 80% herbaceous, 100% shrub and 75% non-vegetated/dead.
Normalized reflectance gives 95% accuracy (19/20); retain
this as sensitivity, not a more favorable interchangeable estimate.
The models still have different physical reference units across sensors; matching
input convention does not make them a controlled sensor comparison.

## A test of the prediction evidence, conditional on geography

Enumerated all 180 unique assignments of complete patch
labels **within regions**. Each assignment refits all 20 held-patch models with
training-only scaling and the fixed balanced logistic classifier. The statistic
is five-class macro recall; raw and normalized inputs were both retained and the
two tests corrected with Holm. Both yield exact p =
0.005556, adjusted p =
0.011111. Thus the prediction results contain spectral
skill beyond what these within-region label assignments support by chance.
This is a new, post-audit diagnostic; the earlier p-values are not replaced.
Pure-class regions have fixed labels in this test. The conditional signal comes
from the mixed regions; it does not prove each of five PFTs independently
identifiable, independently valid labels, or transfer to new regions.

## Pairwise separability: actual sampling constraint

Ten exact patch-level NPC contrasts still give 0/10 Holm-supported pairs under
both representations. The current 3–5 patches per class cannot attain the first
0.005 Holm gate. This is a design limitation, not a finding of equal spectra.
Do not switch to pixel permutations, remove the correction, split one patch into
nominal replicates, or increase random permutations to conceal this limit.

A concrete minimum-resolution collection target is **six independent patches per
class**: add at least one deciduous, three evergreen, one herbaceous, three shrub,
and two non-vegetated patches (ten additional groups). This is a lower bound for
balanced unblocked pair designs, **not a statistical-power recommendation**.
With region/season restrictions, larger matched collections will be needed.
A definitive power claim would require credible effects and covariance beyond
this small, selected sample; no such power was fabricated.

`reference_collection_targets.csv` gives the class targets;
`current_independent_patch_support.csv` shows the missing class/region cells;
`prioritized_existing_photo_contexts.csv` ranks unused public contexts for cover
review without inspecting their Landsat values. Prioritize classes sharing a
region/season, not just more samples from their existing single-class region.

Newly inspected Gunnison herbaceous locator contexts 001–004 show clumped low
woody-looking vegetation and/or tracks/trees. They were **not accepted** as pure
herbaceous cover. Map hypotheses cannot resolve growth form. Independent dated
reference review remains necessary, especially for the older-lidar evergreen
candidates; current labels are provisional throughout.

## Reproduce

```bash
.venv/bin/python examples/publication_figures/landsat_design_audit.py
.venv/bin/pytest -q tests/test_landsat_design_audit.py
```

The script uses the existing compact input tables in place, no raster copies.
The exact enumeration is bounded at 10,000 unique assignments and avoids
factorially duplicated permutations for pure-class regions. The source protocols
are in `src/spectralbridge/researcher_pft_statistics.py`,
`src/spectralbridge/pft_method_audit.py`, `src/spectralbridge/spectral_learning.py`,
and `examples/publication_figures/drone_library_evidence.py`. All diagnostic null
scores and input/source hashes are retained. No independent validation claim is
made from a significant diagnostic.
