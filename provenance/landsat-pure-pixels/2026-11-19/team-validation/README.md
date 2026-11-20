# Landsat reference-pixel team validation pack

This review snapshot contains the existing 1,241 HLS L30 NBAR cells in 61
patches. It does not change the cohort, source imagery, labels, or spectral tests.
All PFT labels remain provisional; zero independent purity confirmations are
recorded in the source cohort.

## Start here

- `output/pdf/landsat_pure_pixel_team_review_guide.pdf`: 22-page explanation,
  definitions, workflow, QA examples, ten contrasting patch cases, four
  non-retained contexts and review instructions.
- `output/pdf/landsat_pure_pixel_complete_atlas.pdf`: 126 pages covering every
  retained cell. Pages 3-4 index all 61 patches. Each patch has an evidence plate
  followed by its complete cell ledger.
- `team_pixel_review.csv`: one row per cell with review ID, original candidate
  ID, projected centre, source granule/date/QA, cover/support fractions,
  supplemental shift diagnostics and blank human-review fields.

The PDF paths above are relative to the repository root; the other files are in
this directory. Full-resolution JPEG plates are under `plates/`. Source aerials
are not recoloured; interpretation and height-proxy panels are separate layers.

## Team decisions

Record `reviewer`, `team_decision` (Confirm, Revise, Exclude, Defer), `revised_pft`
if applicable, `confidence`, `issue_tags` and `review_notes`. Use the stable
`Pxx-Cyy` ID printed in the PDFs. Preserve uncertainty and disagreements; do not
edit source fractions or treat agreeing with a displayed proposal as field truth.
The pack is not a blinded validation experiment. A different reviewer can start
from the image-only panel where feasible before inspecting the proposed label.

The preparation script preserves existing review-field contents on rerun and
refuses a changed ID-to-candidate mapping. Original acceptance/verification flags
are never changed automatically by reviewer notes. A reviewed cohort should be
frozen separately after resolving disagreements.

## What the visuals show

Every plate shows all retained 30 m cells on dated aerial imagery, the frozen
cover interpretation or older no-fill height grid, a 120 m source-area outline
for example B, and three enlarged examples. A is a stronger-support retained
cell; B is the weakest nominal retained cell; R is the closest below-threshold
cover candidate in that view. R is not assigned an alternative class. For
one-cell patches A and B necessarily repeat.

The 120 m rectangle is a conservative unweighted bounding-area diagnostic, not
the true optical footprint, signed cubic weights or a purity confidence bound.
Low support can mean unreviewed area, not known contamination. The 150 m
neighbourhood used for Fmask QA is a different spatial test.

Supplemental 3 m and 5 m diagnostics move the footprint by all nine Cartesian
combinations of -d, 0, +d in each axis. They are **per-axis** shifts; diagonals
reach about 4.2 m and 7.1 m. They are not measured georegistration errors,
continuous worst-case bounds or confidence intervals, and they do not alter
membership. Counts still meeting 95% are 1,013 for the tested 3 m set and 974 for
the 5 m set; 362 pass the separate 120 m area screen.

Evergreen evidence uses historical first-return height occupancy above 5 m,
not independently verified current evergreen cover. The PDF states source
intervals and warns about current shadows, growth form and temporal stability.

## Reproduce

From the repository root, with the existing cached inputs:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/prepare_landsat_pixel_review.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/prepare_landsat_review_summary.py
python examples/publication_figures/build_landsat_pixel_review_pdfs.py
```

The first two use the project geospatial environment. The third needs ReportLab,
Pillow and pypdf; the bundled PDF runtime was used for this delivery. No network
retrieval is needed. Frozen inputs are in the original archive and provenance
locations referenced by `review_manifest.json`.

`geometry_verification.csv` records recalculation of all 1,241 nominal and
source-support fractions from saved geometries/grids. `cohort_contract_verification.json`
checks selected QA, dates, seven finite bands, uniqueness and diagnostic bounds.
`pdf_provenance.json` identifies both PDFs and their source/builder hashes.
`visual_summary.json` records diagram identities and the non-retained examples.
`candidate_date_qa_review.csv` retains alternative-date QA for current candidates.

The existing dataset remains available unchanged at
`provenance/landsat-pure-pixels/2026-11-18/expanded-search/round-2/power-directed-expansion/review-batch-2/hls-combined/hls_l30_nominal_95pct_observations.csv`.
Sampling has not resumed; this is the review checkpoint before further work.
