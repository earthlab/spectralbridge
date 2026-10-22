# SpectralBridge PFT scientific update - 22 October 2026

An 11-page collaborator briefing, with nine large scientific figure stories,
organized around **separability -> identifiability -> abundance**. The opening
progression and final three-question synthesis are not extra scientific figures.
Only the recorded researcher `cover_category` is used. Background/dead is a
comparator, not a biological PFT.

**PDF:** [SpectralBridge_PFT_Scientific_Update.pdf](../../../../output/pdf/pft_scientific_update/SpectralBridge_PFT_Scientific_Update.pdf)

This is a presentation-only synthesis of completed results through 19 October.
No model fitting, permutation testing, mixture generation, candidate search or raw
polygon-library scan was performed. The existing 14 MB compact polygon/year table
is read in place for the first figure; no source library or spectral arrays are
copied into this packet. Earlier reports and sealed scientific packets remain
unchanged. Commit/date on the pages identify the source checkout, not a claim
that this new uncommitted report was already part of that revision.

## Main conclusions and changes in emphasis

- All ten category pairs differ within all four sampled cohorts. Within-category
  variation, unequal effects and limited geographic support constrain that claim.
- Recognition is useful but category-dependent. NEON held-site mean category
  recall is 73.8%; woody-shrub recall is only 46.3%. Synthetic OLI retains less
  recognition information. Its channels are derived from the same NEON reference,
  not independent satellite observations.
- Some known synthetic fractions are recoverable, conditional on representation,
  library capacity and prior. Endmember ambiguity and the completed exhaustive
  search show why spectral reconstruction alone is insufficient. Independent
  field abundance accuracy has not been established.

Compared with the 29-page visual story and 19-page scientific closure, this report
centers the five researcher categories rather than alternative taxonomy or woody
leaf-habit comparisons. It retains the October 16 separation of the three
questions and the equal-candidate fairness control. The October 19 exhaustive
result supersedes the original endmember report's narrower limitation that a full
search had not been run: 16,918,447 permitted models reduce mean spectral error by
78.7% without reducing pooled fraction error. This is not proof that all exhaustive
models fail; the conditional eight-bundle interval includes no change. The dense
and sparse prior comparisons and the known-parent positive control are retained
to avoid an unsupported claim that the library contains no compositional signal.

## Figure and evidence map

| Figure / page | Scientific question | Completed source packet |
| --- | --- | --- |
| 1 / 2 | How broad is within-PFT spectral variation? | Corrected compact table, October 16 category support/foundation |
| 2 / 3 | Do all category pairs differ within cohorts? | October 16 whole-spectrum separability and pair evidence |
| 3 / 4 | Where does the magnitude of contrast occur? | October 15 coordinate contrasts, October 16 pair ordering |
| 4 / 5 | What changes for unknown polygons or sites? | October 15 saved nested identification folds |
| 5 / 6 | Which categories are recovered or confused? | October 15 NEON held-site confusion/recall |
| 6 / 7 | Do selected references cover their categories? | October 19 selected/matched-random coverage |
| 7 / 8 | Can other-category mixtures explain a spectrum? | October 19 hull certificates, saved weights and illustration |
| 8 / 9 | Does synthetic recovery depend on capacity? | October 16 abundance and same-15-parent control |
| 9 / 10 | Does exhaustive fitting improve fractions? | October 19 fixed-library exhaustive MESMA and original controls |

`figure_source_map.csv` supplies exact table paths, fingerprints, related package
functions and presentation transforms. `figure_manifest.json` records the source
SHA/date, environment, colors and PNG/SVG hashes. `claims.json` records 55 named
numeric claims, source paths, selections and scientific scope. `metrics.json` is
the display-value interface. `report_content.json` maps each figure page's exact
caption/takeaway to claim IDs; opening/synthesis text lives in `build_report.py`.
`report_manifest.json` fingerprints the PDF, builders, fonts and figure manifest.
`validation.json` and `VISUAL_QA.md` record checks and page inspection.

## Reproduce the presentation

In an environment with NumPy, pandas, PyArrow, Matplotlib, ReportLab, Pillow, pypdf
and pdfplumber:

```bash
python provenance/pft-scientific-update/2026-10-22/v1/build_figures.py
python provenance/pft-scientific-update/2026-10-22/v1/build_report.py
python provenance/pft-scientific-update/2026-10-22/v1/validate_report.py
pytest -q tests/test_pft_scientific_update_report.py
```

Rebuilding Figure 1 and running the full source validator require the existing
local compact Parquet at its fingerprinted path; it is intentionally not bundled
or copied here. The PDF alone can be recomposed from the saved figures without
the original library.

Use Matplotlib's DejaVu Sans fonts (automatically discovered in a local `.venv`
or installed Matplotlib), or pass `build_report.py --font-dir PATH` with
`DejaVuSans.ttf` and `DejaVuSans-Bold.ttf`. Input sources must match their earlier
sealed manifests. A missing or changed source is a hard error. Regeneration uses
the checkout's current source commit; it must not invent or infer old provenance.

This run used the repository `.venv` for figures/tests and the Codex bundled Python
for ReportLab/PDF QA because its PDF libraries are separate from the repository's
analytics environment. Exact library versions/font hashes are in the manifests.

Render for visual review (Poppler required):

```bash
mkdir -p tmp/pdfs/pft-scientific-update
pdftoppm -scale-to 1500 -png \
  output/pdf/pft_scientific_update/SpectralBridge_PFT_Scientific_Update.pdf \
  tmp/pdfs/pft-scientific-update/page
```

Every regenerated PDF requires a new visual review; automated numeric/bounds
checks do not establish layout quality. `validate_report.py` does not itself
claim to perform visual inspection. The independent validator reaggregates all 55 recorded numeric claims from the
saved result tables. Regression tests use synthetic fixtures to accept matching
claims and reject changed, invented or duplicate claims. They do not rerun
scientific analyses.

## Interpretation safeguards

- Identity-based splitting and resampling use polygon IDs, not automatically pure
  or spatially independent plants. Repeated years and pixels are not independent
  new plants. Three sites/four site-year cells do
  not support broad geographic guarantees; year and site are confounded.
- The 2023/2024 retrospective annotations are reused across imagery years.
  Permutation inference assumes exchangeability within acquisition-history blocks.
- Absolute physical reflectance scaling is unresolved. Figure 1 divides stored
  values by 1,000 only to shorten axis numbers; the endmember figures retain
  supplied-array units. No physical conversion is inferred.
- The first figure's low-alpha curves are qualitative, not normalized densities.
  All available supported annual curves are shown. Per-coordinate tests are not
  rerun for Figure 3: it only summarizes the absolute saved matched effects over
  the four cohorts, losing their sign. It is not validated band selection.
- Balanced accuracy means mean class recall. Confusion rows describe recall, not
  precision or the chance a predicted label is correct. Fold dots are not
  confidence intervals; random-library whiskers are draw spread, not population
  intervals.
- The 603 references were selected from the whole archive, so excluding their 367
  parent IDs from evaluation does not retroactively create selection blindness.
- The hull certificate allows multiple references per category and up to eight
  active references. It establishes a broader numerical ambiguity, not necessarily
  an admissible three-category MESMA alternative or a physically observed mixture.
- Figure 8 is the earlier mean-fold NEON benchmark; Figure 9 is the separate
  fixed-library 360-target synthetic OLI benchmark using pooled fraction RMSE.
  Their RMSEs must not be compared as a common evaluation. Eight parent-sharing
  bundles, not 360 independent field observations, support the latter uncertainty.
- Dense five-category and sparse three-category prior capacities differ. Synthetic
  known-parent FCLS is a positive algebraic control, not ecological validation.
- No independent contemporaneous, spatially aligned field fractions establish real
  abundance accuracy. Measured cover, matched sensor footprints, verified units,
  endmember purity and independent regional/year coverage are the next priorities.

## Deliberate omissions

Alternative PFT taxonomies, repeated PCA variants, all quantile-trace panels,
full site/year grids, exhaustive configuration/sensitivity tables, software/API
and publication audits, and unrelated empirical sensor-pilot material remain in
existing supporting packets. They would dilute the three scientific questions.
The October 19 abundance-information audit stopped at an unresolved-scale gate;
it supplies no new empirical experiment and is not presented as one. No prior
methodological demonstration is described as field abundance validation.
