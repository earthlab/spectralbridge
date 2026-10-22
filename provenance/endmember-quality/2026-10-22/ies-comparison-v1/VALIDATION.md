# Verification and limits

**Numerical status: PASS.** `validation.json` is produced by
`validate_results.py`, independently of the report builder. This is computational
and provenance validation, not field abundance validation.

- Seven input fingerprints verified, including the unchanged original source
  Parquet and original full NPY. New row lineage independently matched by flight,
  GlobalID, pixel ID, row and column; exported row numbers verified one-based.
- The same 3,904 observed curves from 3,021 IDs are reconstructed from in-place
  source metadata and seven-band NPY values using flight/polygon-year medians.
  Per-category nearest-reference predictions, identity weighting, distances and
  recall reproduce all observed coverage summaries.
- All 540 selected IDs are absent from the targets. The 568 synthetic observations
  reconstruct from their known weights and 48 disjoint generating parents, with
  exactly 71 declared recipes per bundle. Three ridge tuning groups use disjoint
  selected parent sets, all absent from the target-parent set.
- Twelve primary prediction sets checked for finite values, nonnegative sum-one
  fractions, native/common fraction RMSE, per-category errors/bias and domain
  summaries. Saved ridge scaler/coefficient/intercept values reproduce raw and
  projected predictions; alpha selection matches grouped tuning scores.
- Four exhaustive searches each have all 25 class-set checkpoints. Model counts
  are independently enumerated from reference counts. Winner weights obey the
  one-reference-per-active-category rule, reconstruct their original spectral
  observations, and reproduce saved spectral RMSE. Checkpoint winners agree with
  final output files. Global optimality is supported by the unchanged kernel and
  its synthetic exact-solver regression, not by rerunning all searches in QA.
- All eight paired fraction comparisons and 1,999-draw whole-bundle intervals
  recompute from saved predictions. Native versus common scoring is explicit.
- All 699 feasible cross-category hull certificates have saved source-row weights.
  Their nonnegativity, sum-one constraint, own-category exclusion and <=1e-8
  residual are independently checked. Missing certificates do not prove uniqueness.
- Known-parent oracle predictions retained and reconstruction/weight RMSE verified.
  Both 501-column label options verified against the CSV in their exact order.
- Ridge's common raw prediction invariance checked independently; the small
  relabelling score difference comes from projection geometry, not new information.
- Eight PNG/SVG figure pairs, report/source fingerprints and all 34 files of the
  earlier collaborator briefing packet are unchanged or match their manifests.
- **27 focused tests pass**, covering the new six synthetic contracts, existing
  endmember/mixture kernels and AI-transparency generation. Ruff, docs links,
  whitespace and all nine AI-transparency freshness outputs pass. No production
  package changes or full-suite rerun were needed.

## Visual review

All eight figures were inspected in an overview, with large-size checks of dense
coverage/domain and category-error figures. The portable HTML was inspected in a
1200 x 900 desktop viewport (opening and category results) and a 430 x 900 mobile
viewport (opening). All eight embedded figures loaded; document width matched
viewport width in both layouts. Dense scientific panels remain zoomable static
figures. Screenshots and inspected artifact hash are in `qa/` and `visual_qa.json`.

## Interpretation remains conditional

The primary factorial comparison uses 592 of the previous 603 references, so
both label schemes have the same eligible membership. Eleven unresolved-background
references are explicitly excluded. The new 501 references all qualify. Unknown
mixed backgrounds are not assigned fabricated pure dead/bare labels.

This is not a selection-blind evaluation, independent real Landsat test, held-site
transfer test, proof of material purity or validation against field fractions.
Eight sampled parent bundles and three sites/four site-year cells limit inference.
The coverage-ID bootstrap and equal-count controls are supplementary exploratory
checks; neither provides general geographic coverage or algorithm-wide superiority.
The revised category scheme changes the scientific question and MESMA model family.
Model readiness remains conditional on the supplied reference scale, label design,
synthetic recipe, constraints and independent validation still to be collected.
