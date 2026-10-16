# Researcher-category spectral information and synthetic abundance — v1

This is the **current primary analysis**, using only the recorded
`cover_category`: Deciduous, Evergreen, Herbaceous, Non-vegetated & dead, Woody
shrub. Earlier taxonomic groupings, dual-label reports and builders are historical
and preserved. See LABEL_SYSTEM_AUDIT.md, analysis_registry.json and the complete
reference inventory. Root FINAL_* links point here.

Start with RESULTS.md and the shareable human report:

`output/pdf/researcher_pft_information/Researcher_Categories_Spectral_Information_and_Abundance.pdf`

The report contains 20 pages, fourteen main publication figures and a six-panel
class-confusion supplement. Every visual explains its meaning and scope.

## What is new

- Every one of ten researcher-category pairs at 360 usable NEON coordinates and
  seven synthetic OLI channels: trained effects, held-out BA/AUC, class rates,
  site/year information and stability.
- Separate full-cohort descriptive inference and training-only blocked inference:
  forty earlier ensembles reused; 230 new eligible outer-training pair/cohort
  cases with 1,999 permutations and within-design joint correction.
- Nested complementary-coordinate budgets 1,2,3,5,7,10,20,50,100,360 plus OLI;
  training correlation clusters, selection frequencies and an inner-only
  parsimonious-budget policy. Single-coordinate LDA is a stated rule, not a
  theoretical maximum information claim.
- A common five-category synthetic abundance benchmark: FCLS, existing EAR/MESMA,
  ridge, PLS, forest, boosting and two-stage detection/conditional regression.
  Ten training experiments and twelve target sets share exact parent/fraction
  membership across methods. All histories are identity-disjoint across roles.
- Shape, first/second derivatives, PCA, PLS, selected-coordinate and OLI
  sensitivities; parent-diversity curves, false detection/low-fraction behavior,
  calibration, common reconstruction diagnostics, ambiguity strata and a no-spectrum training-prior null control.

## Main results

Full-NEON nested logistic balanced accuracy is 85.2% for new polygons and 73.8%
for held sites; synthetic OLI gives 66.8% and 57.7%. Evergreen and the broad
background category transfer more reliably than Woody shrub. Some statistically
supported contrasts are poor individual-coordinate predictors.

NEON ridge synthetic fraction RMSE is 0.216 for new-parent targets and 0.269 for
held-site targets, compared with MESMA 0.359/0.362. These are finite-parent
conditional comparisons. The no-spectrum prior control is 0.309; ridge beats it
on new-parent/held-site targets but not on average across global-year holds. Trees do not improve the principal average; derivatives
are worse, and two-stage detection trades fewer false positives for more missed
low fractions. Better expected fractions do not establish unique physical
inversion or field-cover validity. See all classes, domains and alternatives in
saved tables rather than selecting one favorable score.

## Primary numerical products

- `researcher_pft_information_atlas.csv` and `.parquet`: 3,600 rows with pair,
  wavelength, region, effects, adjusted evidence, BA/AUC, stability, selection
  frequency and configured Landsat response annotations. Repeated per-coordinate
  inferential summaries are explicitly descriptive across overlapping folds.
- `abundance_model_comparison.parquet`: 1,920 class/model/domain rows; a CSV is
  retained in tables/. These are known synthetic source weights.
- `tables/single_wavelength_discrimination.parquet`: all domain/pair/channel
  predictions summarized, with identity-based uncertainty and training effects.
- `tables/training_wavelength_inference.parquet`: 82,800 training-only coordinate
  rows; family correction is separate within each outer-training design.
- `tables/class_specific_transfer.csv`, `class_rate_identity_intervals.csv`,
  `confusion_matrices.csv`, `reused_researcher_class_rates_all_domains.csv` and
  `reused_researcher_year_confusion.csv`: explicit per-class errors and historical
  researcher-only temporal reuse. New and reused model/weighting scopes differ.
- `tables/abundance_case_index.csv`: canonical method-specific prediction paths.
  `synthetic_truth_*.parquet`, parent memberships and bundle scores reconstruct
  every target and paired uncertainty comparison without copying source spectra.
- `tables/abundance_by_true_fraction.csv`, `abundance_by_ambiguity.csv`,
  `two_stage_presence_metrics.csv`, `raw_prediction_constraint_diagnostics.csv`,
  oracle controls and paired bundle intervals retain successes and failures.

`figures/R01`–`R14` have PNG/PDF/SVG exports. `S1` has PNG/SVG. Captions and exact
numerical sources are recorded in FIGURE_CAPTIONS.md and the figure manifests.

## Reproduce

Use the existing `.venv` analytics environment, with the source Parquet read in
place and the earlier verified compact products available. Scripts save only
metadata, compact statistics, synthetic truth/predictions and owned checkpoints;
there is no new ordinary pixel-scale cache. Original units/coefficients are not
changed. Core processing and public pipeline APIs are unaffected.

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python examples/researcher_pft_information.py --stage all \
  --report-python /path/to/python-with-reportlab-and-pypdf
```

Stages can run separately: atlas, abundance, summary, figures, report, validate.
The desktop bundled document runtime was used for the PDF; analysis used the
repository environment. The report builder itself uses saved products and
ReportLab/Pillow/pypdf; it does not refit. Font paths currently target macOS Arial.
Use build_report.py directly to preserve manual edits to report_source.json;
create_report_source.py restores the authored default source.

Restart verifies completed per-case source/code identities and owned hashes.
A changed fitting configuration/code requires a new version/cache path. Raw
FCLS/MESMA alias exports are noncanonical intermediate files; finalization builds
unique method-named exports from immutable fit archives. The CLI abundance and
summary stages perform this repair, and the independent validator checks every
canonical saved RMSE. The numerical models and scores were unchanged by the
export correction. See METHODS for execution amendments and VALIDATION for QA.

Do not rerun old dual-label builders as primary analyses. Do not infer field
abundance, pure materials or annual biological truth from these results.

For a source/cache-denied figure rebuild, run `validate_rebuild.py` in the analysis
environment. Run `validate_report_artifacts.py` in the report environment.
`seal_results.py` hashes the final packet, helper contracts and standalone report;
`final_manifest.json` records the locally verified final bytes. See VALIDATION.md.
