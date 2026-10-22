# New IES endmembers and revised category readiness

An internal, paired comparison requested on 22 October 2026. The new library has
501 references/324 polygon IDs. The previous library has 603 references/367 IDs;
592 references/359 IDs have unambiguous labels under both category schemes and
are used for the primary factorial comparison. The 11 omitted previous references
are mixed/unspecified background, not arbitrarily assigned to dead or bare/rock.

Open **IES_COMPARISON_REPORT.html** for the self-contained illustrated report, or
read **IES_COMPARISON_REPORT.md**. Eight source-linked PNG/SVG figures, compact
scores, exact parent memberships and prediction arrays accompany it. The earlier
collaborator PDF is preserved; this is new evidence, not a silent rewrite.

## Two independent changes

1. **Selection:** previous versus new IES reference membership.
2. **Labels:** original researcher `cover_category` versus the supplied `new_class`
   design, which merges herbaceous/shrub and splits bare/rock from dead.

The proposed label scheme is an experiment; it does not replace the package's
canonical categories or earlier biological conclusions. All four selection/label
cells predict the same observations. Cross-scheme fraction errors are compared
only after exact coarsening to four shared components: deciduous, evergreen,
herbaceous+shrub and background. This does not evaluate the additional scientific
value of resolving dead versus bare: that is examined in revised-category errors.
No reverse split of a merged category is invented.

## Provenance and exclusions

- The new CSV has one-based exported row numbers. A unique join on flight,
  GlobalID, pixel ID, row and column verifies its source indices. New CSV spectra
  and NumPy spectra agree exactly, including their order; the `new_class` list
  matches the class NumPy array. The previous selector's indices remain zero-based.
- All original source/array fingerprints match the October 19 evidence. Original
  inputs are read in place, without making a raw library, full CSV or Parquet copy.
- The union of **540 selected polygon IDs** is excluded from all common targets.
  The primary observed set has **3,904 annual curves from 3,021 polygon IDs**.
- **930 source rows / 86 IDs** have mixed or unspecified backgrounds and cannot be
  mapped to the proposed five labels. They are omitted from the common eligible
  evaluation. Eight of those IDs occur in the previous selection. Full original
  603-member historical results remain unchanged; primary new scores are not
  claimed to be an exact replay of that different benchmark.
- Source values equal the earlier NPY numerical scale; stored-source `/10000`
  lineage does not establish physical reflectance units. OLI is derived from NEON,
  not independent Landsat observations. Labels are retrospective and do not
  certify polygon/endmember purity or spatial independence.

## Matched synthetic design

`protocol.json` freezes input/code/kernel fingerprints and the analysis settings.
The targets comprise eight disjoint six-parent bundles (two per observed site/year
cell), giving **48 parent IDs**. Each bundle uses six pure spectra, every pair at
10/50/90%, and every equal-third triple: **71 recipes, 568 observations** total.
Annual parent curves use flight medians followed by polygon/year medians, matching
the earlier aggregation convention. No selected parent contributes to targets.

Six atomic groups (deciduous, evergreen, herbaceous, shrub, bare/rock, dead) permit
the same physical numerical observation and exact generating weights to be mapped
to both five-category schemes. Two source parents can belong to a category merged
by one scheme. This is intentional, not two independent instances of that merged
category. It exposes changing mixture geometry without changing the observations.

MESMA searches every permitted model with one reference per active category, up
to three categories, using the existing hash-pinned active-face search. This is
not every conceivable physical mixture or all within-category multi-reference
models. The counts per target are 16,053,803 (previous/original), 8,349,581
(IES/original), 14,619,030 (previous/revised), and 8,260,481 (IES/revised).

Ridge uses 36 training bundles x 71 recipes = 2,556 training mixtures per library.
It samples parent IDs uniformly within each atomic group, then a selected pixel
within each parent. Three parent-disjoint tuning groups prevent shared-parent
mixtures from crossing tuning folds. The penalties are fixed at .01/.1/1/10/100;
scaling is fitted within each tuning fold. Both label schemes use the same
training spectra within a selection, with exact relabelling of generating weights.
The training-design prior is a no-spectrum control, learned from training recipes.
Known-parent FCLS is an algebraic positive control only.

Five supplementary reference-count control draws match exact counts in each of
six atomic groups (476 references per draw). They do not match parent counts,
sites or within-parent distributions. Draw spread is not population uncertainty.

## Uncertainty and limits

Paired fraction intervals resample eight whole parent bundles 1,999 times, with a
common draw matrix across comparisons. They are descriptive conditional intervals,
not multiplicity-adjusted population confidence guarantees. Mixture rows sharing
parents are not independent samples. `supplementary_protocol.json` explicitly
identifies the later exploratory paired-ID coverage intervals, which assume
identity-level independence and do not fully model geographic clustering.

All libraries are fixed and internal to the explored archive. Excluding target
IDs does not establish selection blindness. Site/year breakdowns are diagnostics
under global libraries, **not** leave-one-site-out tests. Site and year remain
confounded. A smaller spectral residual, fewer hull certificates, valid fractions
or a unique ridge prediction does not establish a unique physical inverse.

Readiness for field abundance still requires contemporaneous independent field
fractions, matched spectral footprints, verified units/purity and blind external
validation. These controlled recipes do not represent arbitrary real mixtures.

## Reproduce or resume

Use the repository analytics environment with NumPy, SciPy, pandas, PyArrow,
scikit-learn, Matplotlib, Markdown. From the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/ies-mpl \
  .venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/run_comparison.py --stage small
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/ies-mpl \
  .venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/run_comparison.py --stage controls
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/ies-mpl \
  .venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/run_parallel_search.py --workers 4
.venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/paired_diagnostics.py
.venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/export_label_options.py
.venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/complete_certificates.py
MPLCONFIGDIR=/tmp/ies-mpl .venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/build_report.py
.venv/bin/python provenance/endmember-quality/2026-10-22/ies-comparison-v1/validate_results.py
.venv/bin/pytest -q tests/test_ies_endmember_comparison.py tests/test_selected_endmember_quality.py tests/test_mixtures.py
```

Use `--workers 1` for sequential execution. `run_comparison.py --stage all` is also
available. Do not run multiple controllers against the same checkpoint directory.
Each parallel cell has an isolated directory; no candidate population is saved.
Atomic per-class-set checkpoints fingerprint targets, candidates, labels, code and
chunking; mismatches stop rather than reuse incompatible work. The initial single
worker was interrupted and completed class sets were reused by the four-cell
controller. A complete result requires all 25 class sets per cell; the numerical
validator verifies that contract, counts, constraints and saved reconstructions.

The small ridge NPZ outputs are not per-fit checkpoint journals; a truncated or
missing result/parameter set fails validation and should be regenerated before
sharing. Do not silently use partially written model outputs. Version changes to
inputs/design/kernels into a new packet rather than replacing this evidence.

`models/*_mesma_metadata.json` times sum completed class-set times, including
resumed work; their sum is not the parallel wall-clock time. The helper functions
in `src/spectralbridge/library_analysis.py` and `src/spectralbridge/mixtures.py`
and the earlier analysis-only exhaustive kernel are reused without modification.
The report builder only reads compact completed results. Numerical validation
also checks original input fingerprints and source row lineage in place.

## Label options for the next experiment

`new_IES_original_researcher_labels.npy` and `new_IES_revised_labels.npy` contain
safe fixed-width string arrays aligned to the 501 columns of the supplied
`library_oli_undarkened_ies_selected.npy`. Only labels are exported; spectra are
not copied. `tables/new_label_options.csv` records both names, column positions
and source row/parent lineage. No new numeric class-code convention is inferred.

`tables/ridge_relabelling_geometry.csv` distinguishes raw linear prediction from
simplex projection. All primary ridge fits select alpha 10. Their raw shared
component predictions are invariant to the relabelling (up to floating-point
roundoff). Projecting in five categories then merging is not generally the same
as merging then projecting in four categories; the small cross-scheme ridge score
change is a geometry effect, not evidence of changed spectral information.

`complete_certificates.py` retains every feasible hull witness (source row indices
and nonnegative weights) and the known-parent oracle predictions, reproducing
rather than replacing the original compact summaries. Independent validation
reconstructs these witnesses to check their constraints and residuals.
