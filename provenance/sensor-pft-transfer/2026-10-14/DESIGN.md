# Paired sensor/spectral-resolution transfer design

Written before sensor inferential comparisons on 2026-10-14. This is an exploratory
extension of already inspected biological contrasts, not a preregistration.

## Target and gates

Ask whether conditional sampled-group spectral structure is retained under a
synthetic lower-resolution representation of the same acquisitions. This is not
independent sensor validation or classification. Audit stored OLI against code,
source metadata and numerical consistency; prefer `olioli_undarkened` to separate
spectral averaging from the brightness transform. Preserve `olioli` as a sensitivity.
Do not run MicaSense biological inference unless physical band identities can be
validated; a guessed permutation of ten exported values is not validation.

## Labels and support

1. Primary label system: the original species-derived PFT lookup, including all
   eligible pairs, not only DBS/ECT and DBT/ECT. Preserve DBT/ECS weak examples.
2. Secondary, separate analysis: researcher `cover_category`, including species-null
   polygons and Non-vegetated & dead as a comparator.

Use the same source observations, exact GlobalID/flight/source/polygon keys and
one median spectrum per polygon/year for each representation. Intersect valid
observation support before reducing, then require valid polygon/year support in
all admitted representations. Check identical histories, labels and identities.
Restrict both representations to the same mixed acquisition-history blocks per
pair. Minimum support is 10 per group across those mixed blocks, as previously.
Do not replace acquisition-history conditioning with unmatched data silently.
Report all exclusions and pre/post support by cohort and label.

## Families and tests

Retain the original exact-history primary comparisons: all eligible pairs across
four cohorts, separately for inferred labels and researcher labels. Each sensor's
NPC p-values receive Holm over the same pair/cohort family within each label
system. Secondary bandwidth-weighted OLI NPC uses its own explicitly labeled
sensitivity family. No union-of-methods or union-of-labels claim. Use 9,999 label
permutations, synchronized across representations and components, deterministic
legacy-compatible test IDs/seeds. NEON uses the existing max/integrated NPC.
OLI primary integrates equally weighted squared standardized band contrasts.
FWHM-weighted OLI is a metric sensitivity, not extra wavelength samples. Compare
corrected NEON on exactly the same units and histories with its legacy baseline.

## Retention estimands

Record raw and adjusted NPC, max and integrated statistics, calibrated NPC
combination score, per-band signed beta and standardized beta, RMS standardized
contrasts and support. Compare detection, point-estimate direction in seven
corresponding OLI band supports, effect ratios and rankings. NEON-to-OLI direction
uses a declared Gaussian projection on observed harmonized NEON support, not fake
interpolation between OLI bands. Report projection support and noncommutativity
of convolution versus pixel/observation medians; it is not a second independent
sensor. Effect ratios compare distinct spectral metrics and are not literal
fractions of total ecological information; they can exceed one. Suppress ratio
interpretation when the NEON RMS denominator is <=0.1 (explicit descriptive guard).

Compare effect-vector Pearson/Spearman correlations across common contrasts,
overall and by cohort. Report standardized effect compression and rank changes.
Cross-site checks use only the shared 2023 sites and comparable pair definitions;
show signed support-space direction agreement/cosines, without extrapolating to
a random population of sites. Optional band ablation is descriptive: compare
OLI equal-band RMS with and without its two SWIR bands on the identical sample.

## Paired uncertainty

If feasible, use 499 paired cluster-bootstrap replicates. Resample GlobalIDs
within site, label and their complete joint-year acquisition-history pattern,
using the same multiplicity for all sensor representations and repeated years.
This preserves each class/history sample count while coupling correlated
contrasts and repeated identities. Report singleton strata and conditional
bootstrap limitations. Bootstrap pointwise band intervals and effect/ratio/
correlation intervals are descriptive percentile intervals, not simultaneous
inferential bands. Detection percentages summarize dependent contrasts; do not
attach binomial confidence intervals. No significance test of sensor superiority.

## Deliverables and validation

Add reusable code, regression tests, checkpoints and explicit progress; retain
compact outputs, not a source-library copy. Produce requested CSVs, reports and
PDF/PNG/SVG figures. Validate source identities, response definitions, native
support, default NEON numerics, pairing, simultaneous permutations and reproducible
restart; run targeted and full pytest suite. Record all failures and distinguish
existing failures from new regressions. Preserve prior scientific outputs.
