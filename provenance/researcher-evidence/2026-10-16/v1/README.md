# Separability, identifiability and abundance

Current primary scientific validation, 16 October 2026. Only the five recorded
researcher `cover_category` classes enter the analysis. Earlier reports and all
numerical outputs remain preserved. The previous wavelength/abundance packet
is an immutable numerical companion, not overwritten by this report.

Start with the human report:
`output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf`.
It follows the three questions, with foundational validation first, section
checklists/evidence statements and a final four-level evidence ladder.

## What the audit added

- Five equal-size random wavelength paths, matched to the original nested
  selector's exact inner/outer groups and tuning grid; no winning seed selected.
- Nested PCA20/PCA50 recognition, and consistent full-NEON/OLI temporal
  recognition on purged global-year and complete-pair held-ID targets.
- Ridge using the **exact 15 MESMA candidate parents**, the same tuning parents
  and the identical outer mixtures: an adverse retained-capacity control.
- Class-level recognition, fraction error, false detection, low-fraction misses
  and mixture ambiguity links, explicitly descriptive across only five classes.
- Full source/compact missingness and exact annual-vector duplicate audit,
  66 PASS/FAIL/NOT TESTABLE requirements and 19 hostile-review failure modes.

## Main conclusions

Separability is established for the sampled blocked comparisons, not for all
regions or physical materials. Recognition is conditional: NEON balanced
accuracy is 85.2% on unseen polygons and 73.8% on held sites; Woody shrub is weak.
At 20 coordinates selected/random held-site BA is 70.1%/65.0%; the gap narrows
at 100 coordinates and small selected budgets do not win uniformly.

Synthetic ridge120 RMSE improves on MESMA15 in the original new-parent/site
benchmark (0.216/0.269 versus 0.359/0.362), but **same-candidate ridge15 NEON
RMSE is 0.365/0.387**. Retained parent diversity/capacity matters; the original
comparison does not establish intrinsic ridge superiority. Global-year ridge
0.311 also fails the no-spectrum prior 0.309. Better expected fraction estimates
do not remove candidate ambiguity or validate real field cover.

## Reusable saved products

- `tables/design_validation.csv`: every requirement, status, result, source, limit.
- `tables/adversarial_validation.csv`: claim, failure mode, test, result, status,
  remaining limitation and supporting evidence.
- `tables/evidence_ladder.csv`: four separate statuses, never one readiness score.
- `tables/claim_registry.csv`: important quantitative claims and source filters.
- `tables/whole_spectrum_separability.csv`, `wavelength_effect_stability.csv`,
  `region_separability.csv`, `wavelength_null_uncertainty.csv`: difference evidence.
- `tables/metrics.csv`, `selected_minus_random.csv`, `subset_redundancy.csv`,
  `temporal_recognition_summary.csv`: new recognition controls. All memberships,
  inner scores, feature indices and fitted parameters are in `checkpoints/`.
- `tables/abundance_domain_summary.csv`, `abundance_paired_vs_baselines.csv`,
  `same_candidate_ridge.csv`: recalculated RMSE, paired uncertainty, prior and
  capacity controls. Canonical older predictions remain in their original places.
- `tables/class_recognition_abundance_links.csv`, `class_link_correlations.csv`,
  `class_ambiguity_burden.csv`: explicitly limited five-category associations.
- `tables/reconstruction_fraction_points.parquet`: compact diagnostic values,
  not copied source spectra. The original wavelength atlas and all per-class,
  fraction/detection/transform tables remain in the P129 companion packet.
- `figures/`: ten PNG/PDF/SVG figure families. Figure manifests/captions provide
  exact numerical sources and readable interpretation/limits.
- `report_source.json`/`.md`: editable report. `build_report.py` preserves edits;
  `write_report_source.py` restores the authored source from canonical numbers.

## Reproduce

Use the existing analysis environment and supplied original Parquet in place:

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python examples/researcher_evidence_validation.py --stage all \
  --report-python /path/to/python-with-reportlab-pypdf-pandas-pillow
```

Stages: controls, candidate, summary, figures, report, validate. Completed fitting
checkpoints verify code/input/protocol identities and owned hashes on restart.
Changing fitting code/protocol requires a new version; do not silently reset them.
The desktop bundled document runtime produced the PDF. Arial font paths are
currently macOS-specific. No package production correction, coefficient, response,
unit, pipeline or core public API changed.

Run `validate_figure_rebuild.py` in the analysis environment to require exact
rebuilding with raw-data/cache reads denied; run `validate_artifacts.py` in the
report environment for geometry, source hashes and exact PDF rebuilding.
`seal_results.py` seals the final bytes after all verification. See VALIDATION.md.

The existing nominal-fraction summaries already collapse floating-point-equivalent
truth fractions. `fraction_grid_calibration.csv` preserves their actual counts
and squared-error aggregation, protected by a regression test. Raw model errors
and all earlier scientific tables remain unchanged.

`stage_A_detection_by_fraction.csv`, `conditional_admitted_quantification.csv`
and `forced_presence_admission.csv` distinguish raw tuned presence decisions,
the existing highest-score fallback when no class is admitted, and final-fraction
detection. Model presence scores are not claimed to be calibrated probabilities.
