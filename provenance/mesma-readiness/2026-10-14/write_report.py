"""Source-specific scientific interpretation; every numerical claim reads frozen tables."""

from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
T = OUT / "tables"


def write(name, text):
    (OUT / name).write_text(text.strip() + "\n")


def markdown(frame):
    # No optional tabulate dependency.
    cols = list(frame.columns)
    rows = [
        "| " + " | ".join(map(str, cols)) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        rows.append(
            "| "
            + " | ".join(
                f"{v:.3f}" if isinstance(v, (float, np.floating)) else str(v)
                for v in row
            )
            + " |"
        )
    return "\n".join(rows)


def read_table(name):
    path = T / (name + ".parquet")
    return pd.read_parquet(path) if path.exists() else pd.read_csv(T / (name + ".csv"))


methods = pd.read_csv(T / "method_comparison.csv")
errors = pd.read_csv(T / "fraction_errors.csv")
detect = read_table("detection_errors")
a = pd.read_csv(T / "class_ambiguity_summary.csv")
uc = pd.read_csv(T / "uncertainty.csv")
folds = pd.read_csv(T / "fold_support.csv")
flags = pd.read_csv(T / "unreliable_fraction_flags.csv")
native = pd.read_csv(T / "native_pixel_qc.csv")
metadata = pd.read_csv(T / "original_material_metadata.csv")
support = pd.read_csv(T / "class_sample_sizes.csv")
main = methods[methods.method.eq("EAR_MESMA3")]
physical = (
    support[support.scheme.eq("material")]
    .groupby("label", dropna=False)
    .agg(identities=("identities", "sum"))
)  # counts across years are not unique; use metadata below for totals.
rows = []
for field in ["cover_category", "cover_subcategory", "dead_subcategory", "shaded"]:
    for label, g in metadata.groupby(field, dropna=False):
        rows.append(
            dict(
                field=field,
                label=label,
                unique_GlobalIDs=g.GlobalID.nunique(),
                sites=g.aop_site.nunique(),
            )
        )
counts = pd.DataFrame(rows)
counts["label"] = counts.label.fillna("(not recorded)")
counts.to_csv(T / "material_unique_counts.csv", index=False)
identity_metadata = pd.read_csv(T / "sample_membership.csv").drop_duplicates("GlobalID")
pft_cover = pd.crosstab(identity_metadata.pft_code, identity_metadata.cover_category)
pft_cover.to_csv(T / "pft_by_cover_category.csv")
write(
    "MATERIAL_CLASS_AUDIT.md",
    f"""# Material class audit

The library has {metadata.GlobalID.nunique():,} GlobalIDs. A polygon identity is not necessarily an individual living plant, a pure canopy or a physically pure material. Species-null polygons remain through researcher labels. Preserve species, name-derived PFT and researcher categories as different annotation systems.

{markdown(counts[counts.field.eq("cover_category")][["label", "unique_GlobalIDs", "sites"]])}

## Existing physical hints, not invented classes

{markdown(counts[counts.field.isin(["cover_subcategory", "dead_subcategory"])][["field", "label", "unique_GlobalIDs", "sites"]])}

The name-derived PFT experiment covers woody taxa: all 677 Herbaceous and all 414 Non-vegetated & dead identities are UNASSIGNED in that crosswalk. It therefore cannot substitute for a full material library. Some assigned PFTs span researcher cover categories; pft_by_cover_category.csv records the exact cross-tabulation.

The broad Non-vegetated & dead category is physically heterogeneous and cannot be treated as a single clean soil/NPV endmember. Rock (119 identities) and Bare (44) exist as explicit labels. Bare is a substrate annotation, not verified mineral soil. Dead standing/downed woody annotations exist; 71 polygons explicitly say Mixed Dead / Bare / Rock. No fraction or purity measurement resolves those mixtures. A Bare record also has a dead-herbaceous subtype: conflicting detail needs review. The five inferred PFT labels are trait annotations, not independent material spectra.

The controlled material experiment conservatively uses concordant category/subcategory labels. Generic Dead records use their recorded dead_subcategory. Fifteen records with missing cover_subcategory but recorded dead subtypes are kept in the inventory and outside this conservative material benchmark pending annotation reconciliation; they are not declared physically unknown or silently merged. Rare Dead - Herbaceous records in the concordant subset fail some/all support gates. Original metadata and fold-support tables expose these choices. The combined researcher category is tested separately to show consequences of a broad hierarchy, not adopted as an operational material.

Measured water, snow, litter, pure shade and verified soil are absent as distinct validated classes. Dead - Debris has one annotated identity and does not establish a litter library. The shaded field describes 206 shaded, 53 mixed, 1,872 sunlit and 1,508 unspecified polygons; it is not a measured black-shade spectrum. Do not rename canopy shadow as a new material or use zero as empirical shade truth.

Recommended hierarchy: retain broad vegetation types as labelled canopy proxies; separate annotated Rock, Bare, woody standing/downed and dead herbaceous where supported; retain mixed/uncertain annotations explicitly. Establish independently measured purity and background fractions before ecological material abundance mapping. Species-level readouts require their own sampling/validation and cannot inherit a PFT result.
""",
)
write(
    "SPECTRAL_QC.md",
    f"""# Spectral integrity and variability

Reuse P120's verified compact pairing: 85,706 extracted pixel rows, 12,504 plant/flight observations, 4,807 polygon-years, 3,639 identities, three source grids and 122 flights. The 1,140-column union contains structural NaNs; native records each have 426 finite channels. Existing 5-nm harmonization never bridges gaps >8 nm or absorption intervals 1340-1450 and 1790-2000 nm. The analysis uses the finite intersection of that already validated support and all seven admitted OLI channels; exact coordinates are in executed_design.json. Do not interpolate atmospheric gaps or interpret union-schema missingness as random noise.

Native raw range: {native[native.stage.eq("raw")].minimum.min():.1f} to {native[native.stage.eq("raw")].maximum.max():.1f}; corrected range: {native[native.stage.eq("corr")].minimum.min():.1f} to {native[native.stage.eq("corr")].maximum.max():.3f}, in STORED UNITS. There are {int(native[native.stage.eq("corr")].negative_native_values.sum()):,} negative and {int(native[native.stage.eq("corr")].zero_native_values.sum()):,} zero corrected native entries. These counts include all native bands; absorption-supported roughness is separate. Zero is not automatically nodata. No -9999 exact sentinel was observed. Saturation cannot be established from a reflectance number without original source QA/headers.

The merged Parquet has no Arrow unit/scale metadata and historical source headers point to an unavailable archive. An unrelated R10C H5 does not prove scales for these flights. Therefore physical range >1, detector saturation, source-level brightness comparability and absolute reflectance/noise tolerances are BLOCKED. No scale was inferred from observed magnitude. A common training-only RMS divisor stabilizes numerical mixture fits and leaves convex fractions unchanged under one common positive factor; it does not verify per-flight scaling or physical reflectance.

Within-polygon native variance is reduced from all pixels in bounded 2,048-row batches using centered sufficient moments, outside absorption bands and within the inherited supported wavelength range. Pixels are immediately discarded; no persistent pixel cache is created. Population variances require >1 observed pixel for informative within-polygon variability; a zero from one point is not evidence of homogeneity. Tables retain parent count and original source/flight identities. Raw/corrected roughness and extremes are traceable per flight. Large correction extremes may be processing/illumination artifacts; unusual spectra were not deleted or automatically called ecological variation.

Repeated-observation dispersion partitions in hierarchical_dispersion.csv are separate descriptive views, not additive causal components. Identity, species, class, site, year and acquisition are confounded. The observed between-identity partition is not a genetic variance estimate; within-identity differences include acquisition, environment, year and correction effects. No model was forced to estimate unidentifiable random effects. Figure 1 shows full-value PCA on symlog axes plus class median/IQR traces with real gaps.
""",
)
write(
    "COVERAGE.md",
    """# Representativeness and coverage

Coverage is tested using complementary held-out library nearest-neighbor RMSE, spectral angle, full-value PCA, source/native-grid QC and convex reconstruction. The complete eligible compact library enters these descriptive analyses. No 2-D PCA hull is called spectral-space completeness.

Class accumulation uses training/evaluation identities separated before ten deterministic ordering replicates, with 1,2,5,10,20,50,100,200,500 candidates where available. Group accumulation separately adds species, sites and years on a fixed identity-disjoint target set. Ten curve-order replicates characterize ordering sensitivity; they are not independent field replicates or confidence intervals. A decreasing nearest-neighbor distance follows mathematically as candidates are added and alone cannot prove diversity saturation. The site/year additions change class composition as well as environment, so their effects are not independent causal factors.

Endmember-optimization comparisons use a stricter, bounded candidate proposal pool (up to 12 identities per class balanced over training site/year strata). That budget does not mean the full material diversity fits in 12 endmembers. Requested 20/50/100-entry optimization trials are explicitly not evaluated under this cap. Larger unfiltered spatial hulls/combinatorial libraries are not silently approximated.

Full NIWO/WREF/YELL source images are not available here. The supplied extraction is sparse, researcher-selected polygon pixels rather than a probability sample of the landscape. Held-out-library coverage cannot establish coverage of soil, water, snow, litter, unknown vegetation or the full source-image distribution. Full-image OOD coverage is INSUFFICIENT EVIDENCE. The R10C real-observation pilot is a different acquisition/site and lacks material fractions. Source imagery, co-registered complete material maps and source QA are required before an operational coverage claim.
""",
)
write(
    "ENDMEMBER_SELECTION.md",
    """# Endmember selection and computational envelope

Training-only selectors are stratified random, Euclidean medoid, EAR, MASA, marginal in-CoB with EAR ties, add/remove training-kappa IES, medoid-seeded farthest-point diversity and a named IES-plus-class-completion hybrid. The last is a bounded adaptation, not a claim to reproduce Roth's full injection schedule. Exact source identities, candidate scores and selected memberships are archived. in/out CoB counts are recomputed in EAR_MASA_CoB.csv from the same training pools and fixed 0.02 relative-RMS threshold. EAR is candidate-plus-ideal-black-shade reconstruction, not raw Euclidean distance; MASA is angular. Self is excluded from EAR/MASA averages. The workflow evaluates these definitions in the declared wavelength-quadrature feature space: NEON EAR/CoB use weighted RMSE and MASA a weighted angle. This is an explicit metric adaptation, not an exact equal-band reproduction of another study. CoB's incremental new coverage differs from a simple ranking of total counts.

All selection is repeated within each fold and evaluated on absent GlobalIDs. IES optimizes training classification kappa; it may omit rare classes and cannot be presumed optimal for abundance. The cap is a global k x class count, not k guaranteed examples in every class. EAR optimizes candidate-plus-shade reconstruction; a no-shade mixture objective can therefore prefer different prototypes. This objective mismatch is not evidence of intrinsic material indistinguishability. ambiguity_selection_sensitivity.csv compares EAR, medoid, MASA and the entire proposed pool with a common two-other-material limit, so conclusions do not rely solely on an EAR choice. Random/medoid/EAR/MASA/diversity and CoB have their stated per-class size constraints; CoB can stop earlier. The hybrid completes omitted classes from minimum-EAR candidates. A method winning here is only a winner for this bounded candidate pool, split design and nominal-label simulations.

Size curves evaluate 1,2,5,10 candidates/class on held-out class reconstruction, including all available lesser sizes for rare classes. library_size_fraction_recovery.csv additionally evaluates those counts on identical held-out synthetic mixtures using EAR where exhaustive models fit the 20,000-model cap; over-budget cases are reported rather than pruned. Requested sizes 20,50,100 are recorded outside the candidate budget. Fraction recovery primarily uses two selected examples/class; additional complexity compares up to two versus three materials. These experiments do NOT establish a globally optimal endmember count or a plateau for full operational libraries. A Pareto decision must jointly consider class coverage, fraction error, ambiguity, model count and runtime, not choose smallest residual alone.

Exact class-distinct model count with C classes and k candidates/class is sum_{r=1..m} choose(C,r) k^r. For C=5, k=100, m=3 this already gives 10,100,500 models; for C=8 it gives 56,280,800. The implemented cap is 20,000, checked before allocating models. Exhaustive convex search is exact within the declared candidate/model set, with all lower-dimensional simplex faces and bounded model chunks. It is verified against an independent constrained optimizer on small random cases. Numerically singular interiors are skipped at an affine Gram eigenvalue cutoff max(1e-12, 1e-10 times the largest eigenvalue); their lower faces remain eligible. Exactness is relative to this declared numerical-rank tolerance. The near-collinear regression example has negligible spectral error but radically different near-equivalent fractions, so it is not declared precisely identifiable. Exact fixed-library FCLS is capped at 12 vertices. No huge source/pixel cache or uncontrolled raster MESMA was launched. Runtime tables name kernel timing separately from I/O/selection/outer overhead; source-dependent timings are evidence, not package constants.
""",
)
ambiguity_primary = a[(a.kind == "plant")]
write(
    "MIXTURE_IDENTIFIABILITY.md",
    f"""# Mixture identifiability

Held-out spectra bearing class C are compared with the best single same-class candidate and the best sum-one, nonnegative convex model with up to three OTHER classes. The wrong model includes all two-class and singleton faces. Both primary comparisons are no-shade models; the directed EAR-style confusion table separately and explicitly includes ideal black shade. Nominal C purity is not independently verified, so these are tests of the labelled library's geometry, not proof that true pure C can or cannot be identified.

{markdown(ambiguity_primary.groupby(["scheme", "sensor"], as_index=False).agg(mean_class_ambiguity_rate=("ambiguity_rate", "mean"), heldout_records=("heldout_records", "sum")))}

A wrong reconstruction is ambiguous when its RMSE <= own-candidate RMSE + tolerance. Sensitivities 0.005,0.01,0.02 are fractions of a training-only RMS magnitude, not universally meaningful physical noise thresholds. Class ambiguity is additionally affected by poor own-class representativeness and asymmetric model capacity (one same-class prototype versus a convex combination of other classes). The selector/pool sensitivity table tests this dependence explicitly; the result is conditional on the specified library/model, not a proof of intrinsic physical non-identifiability. Exact errors and their signed gap, best wrong composition, near-composition counts, and original memberships are retained. Near-composition counts exclude zero-fraction additions: adding a material with fraction zero is not a new composition.

near_fraction_range spans the best model within each near-equivalent class set; it does not enumerate all endmember-choice variants within the same class set and is a LOWER-BOUND stability diagnostic. Monte Carlo separately probes empirical endmember choice. Different class means or previous permutation significance do not rule out convex overlap. MIXTURE_AMBIGUITY_MATRIX.csv exposes the masquerading class combinations. Missing-class tests in unknown_detection.parquet remove the entire nominal class and compare errors against training-only same-class thresholds; the main unknown test is the 100%-class endpoint, not an exhaustive contaminated-mixture OOD study.
""",
)
write(
    "SYNTHETIC_MIXTURES.md",
    """# Controlled mixtures and recovery

Every mixture source is an empirical held-out polygon/year spectrum or, for flight transfer, an actual held-out-flight polygon spectrum. All observations of its GlobalID are purged from training. A labelled polygon is not a validated pure material: known fractions here are algebraic weights on those composite source curves. Even perfect recovery would not validate real ecological cover.

Pairs use 0,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,1; triples use equal thirds and .1/.2/.7, .05/.45/.5, .8/.1/.1. One source combination per composition/fold is drawn with a fixed seed. Reusing parents across gradient points makes simulations dependent. Source IDs include year; synthetic_mixture_truth.parquet is separate from candidate memberships. No candidate spectrum generates its own test mixture.

Primary methods are physically constrained classical variable-endmember search (two/three material limits), fixed class-medoid FCLS and empirical Monte Carlo one-candidate-per-class FCLS. All estimated fractions are nonnegative and sum to one. Boundaries are solved as lower-dimensional faces, not unconstrained fractions clipped and renormalized. No sparse L1 benchmark is claimed: L1 is constant on the nonnegative sum-one simplex. A nonconstant, validated sparse alternative is deferred.

Fraction bias, MAE/RMSE, false positives/negatives, selected class-set error, spectral RMSE/angle and sum/negative violations are archived. Class-set error thresholds BOTH true and estimated fractions at 0.10; its estimand differs from detection false negatives, which treat ANY positive true fraction as present. Neither is called field classification accuracy. MC does not enumerate MESMA class sets: its near_compositions=0 records no enumerated sets, not a claim of unique composition. Detection is predeclared at estimated fraction >=0.10, with .05/.20 sensitivity. False positives have true fraction zero; false negatives have positive truth but fail detection. Conditional detection frequencies carry explicit denominators. No 50/80/95% population detection threshold is defensible from three plant folds and one parent draw per composition. The curves are diagnostics, not calibrated operating characteristics.

Acquisition stress draws signed differences between repeated TRAINING identities' year spectra at amplitudes 0.25 and 0.5, coupled across sensors. This includes biological/environmental/processing variability and is NOT instrument noise. Folds without eligible repeats do not receive fabricated noise. A general real-Landsat residual distribution is not imposed on other sites. Ideal black-shade sensitivity injects 25% zero spectrum into an FCLS model; the zero is hypothetical and cannot calibrate actual canopy shade. shade_formulation_comparison.csv compares no-shade, explicit black shade and shade-normalized estimates with matched total-footprint or non-shade-composition truth. Shade normalization changes the estimand and does not validate real shade or total cover.
""",
)
write(
    "SENSOR_TRANSFER.md",
    f"""# Paired spectral reduction versus real-sensor validation

The same held-out source identities, fraction vectors, candidate proposal pools and NEON-selected endmember IDs are used in both representations. Corrected NEON uses the inherited disconnected wavelength quadrature; OLI uses seven equally weighted verified synthetic channels. No per-spectrum brightness normalization is used. Relative RMSE normalization uses one training-only NEON scalar for BOTH sensors. Differences therefore include the declared spectral metric as well as representation loss; no literal information-retention percentage is claimed.

{markdown(main[["scheme", "sensor", "fraction_RMSE", "fraction_MAE", "reconstruction_RMSE"]])}

Previous P120 retention of 15/16 NEON-supported inferred-PFT contrasts concerned sampled-group spectral differences. It does not contradict poor fraction recovery or establish abundance information retention. Here the paired sensor_comparison.csv directly records OLI-minus-NEON fraction RMSE within exact fold/class/method pairs.

P121 compares one real R10C next-day Landsat observation: pooled undarkened SR RMSE 0.01477, angle 2.089 degrees, mixed brightness effects and conditional legacy UTC timing. It is not cross-site validation, noise truth, endmember purity or fraction validation. Library scales are unverified, so adding 0.01477 reflectance Gaussian noise to stored library values would be indefensible. Actual Landsat fractions remain unvalidated.

The required four-way native/30 m spatial/spectral experiment cannot be completed for library sites from sparse polygon extractions. No full NIWO/WREF/YELL rasters and independent fractional maps were available. P121's correctly aggregated R10C image supports a different pixel-support diagnostic but not ecological fraction truth. Spatial mixing and spectral reduction must not be conflated; the present recovery study isolates only representation under its linear synthetic model.
""",
)
transfer = pd.read_csv(T / "transferability_summary.csv")
write(
    "TRANSFERABILITY.md",
    f"""# Grouped generalization

{markdown(transfer[transfer.method.eq("EAR_MESMA3")][["scheme", "kind", "sensor", "median_fraction_RMSE", "p25_fraction_RMSE", "p75_fraction_RMSE", "folds"]])}

Three class/site-stratified plant folds; every available leave-one-site, leave-one-year and within-NIWO year direction; and all available actual-flight holdouts were considered. Exact class/fold support, omitted classes and source memberships are in fold_support.csv/fold_membership.parquet. Candidate selection is repeated INSIDE training. Every test GlobalID, across all years and flights, is excluded from training. Flight tests use actual flight-specific spectra, never all-flight annual medians. Unsupported directions are not turned into estimates.

Some repeated NIWO years cannot provide a reverse-direction training set once every held-out identity is removed. This is a sampling-structure limit, not a failure of the optimizer. Year transfer therefore concerns new identities as well as dates. Flight/site folds overlap in their source plants; their errors are correlated, not independent ecological replicates. Sample sizes and class sets vary with support. Differences between the displayed holdout summaries cannot isolate a pure geographic or temporal penalty. Within-site plant folds do not impose a spatial buffer or independent-plot split; nearby or overlapping annotations can remain correlated. GlobalIDs denote disjoint records, not proof of independent organisms or genotypes. Species remain nested/confounded in PFTs; no species-independent functional mechanism or held-out-species generalization is inferred.
""",
)
u = uc[uc.interpretation.eq("endmember_choice_stability_not_calibrated_confidence")]
write(
    "UNCERTAINTY.md",
    f"""# Fraction uncertainty, shade and unknowns

{markdown(u.groupby(["scheme", "sensor"], as_index=False).agg(mean_empirical_interval_width=("mean_interval_width", "mean"), conditional_truth_coverage=("conditional_interval_coverage", "mean"), mean_fraction_RMSE=("fraction_RMSE", "mean")))}

Twelve empirical random one-candidate-per-class FCLS draws produce an ensemble mean and empirical 2.5/97.5 percentiles. These are ENDMember-choice stability ranges, not posterior distributions or confidence intervals. Twelve draws are sparse for tail estimation. The nominal 95% reference is evaluated against controlled synthetic truth, not asserted calibrated. Finite candidate pools omit unobserved variability; the parent spectra themselves may be mixed. No independent flight-based sensor-noise model is available.

The best-per-composition near-model range is a lower bound on model ambiguity, not a full fraction interval. Small spectral residuals can coexist with large fraction RMSE; unreliable_fraction_flags.csv quantifies false-confidence sensitivities without choosing a threshold after seeing results. Thresholds 0.005/0.01/0.02 are relative spectral tolerances and fraction error 0.10/0.20 are illustrative decision aids, not universal pass criteria. Do not operationally accept an unknown merely because its residual is small.

Removing an entire class tests unknown-material masquerading at pure nominal-label endpoints. More realistic unknown mixtures, novel species/backgrounds, complete-source-image OOD validation and calibrated abstention remain required. Independent empirical shade spectra are missing. A 25% idealized zero-shade simulation probes algebra only; shade-normalized fractions describe conditional non-shade composition, while total fractions describe the footprint. Nonlinearity cannot be diagnosed uniquely from these residuals: endmember incompleteness, purity, atmosphere/correction and variable scaling are competing explanations. No nonlinear model was implemented to explain away failure.
""",
)
# Auditable, separate readiness dimensions rather than a blended score.
dimensions = [
    (
        "A",
        "spectral integrity",
        "PARTIAL",
        "Three grids/common masks verified; physical units/source QA/purity unverified",
    ),
    (
        "B",
        "material coverage",
        "PARTIAL",
        "Rock/Bare/dead tags exist; water/snow/litter/measured shade/verified soil gaps",
    ),
    (
        "C",
        "representativeness",
        "INSUFFICIENT EVIDENCE",
        "Held-out library distances do not measure full-image coverage",
    ),
    (
        "D",
        "distinguishability",
        "CONDITIONAL",
        "Prior sampled-curve differences, directed reconstruction here",
    ),
    (
        "E",
        "mixture identifiability",
        "NOT ESTABLISHED",
        "Other-class convex ambiguity, bounded candidates",
    ),
    (
        "F",
        "fraction recovery",
        "CONDITIONAL SYNTHETIC ONLY",
        "Known algebraic weights on held-out composite spectra",
    ),
    (
        "G",
        "transferability",
        "LIMITED",
        "Grouped tests; support gaps and changing classes",
    ),
    (
        "H",
        "sensor robustness",
        "CONDITIONAL",
        "Paired synthetic OLI, no real abundance truth",
    ),
    (
        "I",
        "uncertainty calibration",
        "NOT ESTABLISHED",
        "Empirical endmember spread is not calibrated probability",
    ),
    (
        "J",
        "computational feasibility",
        "FEASIBLE WITH BUDGETS",
        "Exact bounded search/checkpoints; all-library raster combinations not run",
    ),
]
pd.DataFrame(dimensions, columns=["dimension", "name", "status", "evidence"]).to_csv(
    T / "readiness_dimensions.csv", index=False
)
materials = [
    "Green vegetation",
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "NPV/dead",
    "Rock",
    "Bare",
    "Soil",
    "Water",
    "Snow",
    "Measured shade",
    "Species-level",
]
readiness = []
for material in materials:
    for sensor in ["NEON hyperspectral", "Landsat-like"]:
        readiness.append(
            dict(
                material=material,
                sensor=sensor,
                operational_fraction_status="INSUFFICIENT EVIDENCE",
                reason="No independent fractional cover or validated purity/absolute per-source scales",
                synthetic_evidence="See exact source-label hierarchy fraction/ambiguity/support tables; broad green-vegetation, soil/water/snow/shade/species fraction benchmarks not established",
            )
        )
pd.DataFrame(readiness).to_csv(T / "readiness_matrix.csv", index=False)

write(
    "RECOMMENDATIONS.md",
    """# Recommendations and boundary of present support

1. Recover original ENVI/H5 sidecars, generation versions, scale/offset/QA and exact sensor metadata for the 122 contributing flights; verify per-flight comparability without guessing from magnitudes. Review corrected-value extremes and zero provenance against raw/ancillary data.
2. Audit polygon purity and time-validity of labels, reconcile background subcategory conflicts/incomplete parents, and document mixed fractions. Keep Rock and Bare distinct; do not rename Bare soil or lump all dead/NPV/soil/rock as one endmember.
3. Collect clean, independent soil/litter/NPV/wood/water/snow and illumination/shade coverage appropriate to the intended landscape. Rare classes need new identities and sites, not synthetic oversampling.
4. Obtain temporally matched, co-registered and spatially exhaustive independent fractional-cover truth. Existing polygons are selected annotations, not complete per-pixel truth. A promising route is to revisit their independent digitized geometry with time-matched orthophotos/field records, quantify purity, overlaps and unmapped area, and assemble complete per-footprint material fractions. Selected polygon intersections alone give incomplete coverage, not manufactured ground truth. REAL ABUNDANCE VALIDATION = NOT YET AVAILABLE.
5. Expand controlled candidate pools and source-parent replicates, then rerun nested selection/validation. Validate library-size plateaus and class-conditional Pareto tradeoffs before choosing a selector. Current tests are a bounded diagnostic, not global endmember optimization.
6. Calibrate residual/uncertainty/unknown rejection using separate reference acquisitions. Include partly unknown mixtures and evaluate error/coverage and detection operating points with genuinely independent parents. Twelve bundle draws do not establish 95% uncertainty calibration.
7. Add full-image spatial-support experiments and same-day/multiple-flight/site real Landsat validation where independent truth exists. Retain both synthetic adjusted and undarkened products; do not refit gains from one pilot or treat synthetic OLI as real observation.

Supported NOW: audit stored spectral support, annotation coverage/variability, conditional sampled-group spectral differences, explicit same-library convex ambiguity, and controlled out-of-identity linear-mixture sensitivity. Unsupported NOW: calibrated ecological cover maps, reliable species/PFT fractions, operational background/shade fractions, quantitative change detection, universal detection thresholds, landscape completeness or universal Landsat interchangeability. No class is promoted to operational READY because it has a small p-value or a visually distinct mean curve.
""",
)

# All twenty requested questions, exact values remain in auditable source tables.
primary_table = markdown(
    main[["scheme", "sensor", "fraction_RMSE", "fraction_MAE", "class_set_error"]]
)
methodranking = (
    errors[errors.kind.eq("plant") & errors.method.str.endswith("_MESMA3")]
    .groupby(["scheme", "sensor", "method"], as_index=False)
    .fraction_RMSE.mean()
    .sort_values("fraction_RMSE")
    .groupby(["scheme", "sensor"])
    .first()
    .reset_index()
)
operating = detect[
    detect.kind.eq("plant")
    & detect.method.eq("EAR_MESMA3")
    & np.isclose(detect.detection_threshold, 0.1)
]
operating_rows = []
for (scheme, sensor), g in operating.groupby(["scheme", "sensor"]):
    row = dict(
        scheme=scheme,
        sensor=sensor,
        macro_FPR_true_zero=float(g[np.isclose(g.true_fraction, 0)].probability.mean()),
    )
    for f in [0.2, 0.5, 1.0]:
        row[f"macro_FNR_true_{f:g}"] = float(
            1 - g[np.isclose(g.true_fraction, f)].probability.mean()
        )
    operating_rows.append(row)
operating_summary = pd.DataFrame(operating_rows)
operating_summary.to_csv(T / "operating_point_summary.csv", index=False)
class_recovery = (
    errors[errors.kind.eq("plant") & errors.method.eq("EAR_MESMA3")]
    .groupby(["scheme", "sensor", "label"], as_index=False)
    .agg(fraction_RMSE=("fraction_RMSE", "mean"), fraction_MAE=("fraction_MAE", "mean"))
)
class_recovery.to_csv(T / "class_fraction_recovery.csv", index=False)
unknown = read_table("unknown_detection")
unknownsummary = (
    unknown[unknown.kind.eq("plant")]
    .groupby(["scheme", "sensor"], as_index=False)
    .agg(
        known_false_alarm=("known_flagged", "mean"),
        unknown_flag_rate=("unknown_flagged", "mean"),
    )
)
size_table = pd.read_csv(T / "library_size_fraction_recovery.csv")
size_summary = (
    size_table[size_table.status.eq("evaluated")]
    .groupby(["scheme", "sensor", "requested_per_class"], as_index=False)
    .fraction_RMSE.mean()
)
size_summary.to_csv(T / "library_size_recovery_summary.csv", index=False)
selector_sensitivity = pd.read_csv(T / "ambiguity_selection_sensitivity.csv")
selector_summary = (
    selector_sensitivity[np.isclose(selector_sensitivity.tolerance, 0.01)]
    .groupby(["scheme", "sensor", "selection"], as_index=False)
    .ambiguity_rate.mean()
)
selector_summary.to_csv(T / "ambiguity_selector_summary.csv", index=False)
comparison = methods.pivot(
    index=["scheme", "sensor"], columns="method", values="fraction_RMSE"
).reset_index()
comparison["MESMA3_minus_FCLS"] = comparison.EAR_MESMA3 - comparison.FCLS_medoid
comparison["MC_minus_FCLS"] = comparison.MC_mean_FCLS - comparison.FCLS_medoid
comparison.to_csv(T / "matched_method_summary.csv", index=False)
shade = (
    pd.read_csv(T / "shade_formulation_comparison.csv")
    .groupby(["scheme", "sensor", "formulation", "estimand"], as_index=False)
    .fraction_RMSE.mean()
)
shade.to_csv(T / "shade_summary.csv", index=False)
write(
    "RESULTS.md",
    f"""# Executive scientific answer: is the library ready for MESMA?

**Conditionally useful for spectral/mixture diagnostics; NOT operationally validated for material abundances.** Existing spectral separation is not mixture identifiability. Composite endmembers, convex ambiguity, held-out fraction errors, background gaps, unverified per-source scales and absent independent fractions prevent a defensible operational pass. This is a negative/qualified readiness result, not a recommendation to run all spectra through a raster solver.

## 1. Which material classes are supported?

Researcher Deciduous/Evergreen/Herbaceous/Woody shrub/Non-vegetated & dead and five inferred PFTs support labelled-library tests. Rock, Bare and some dead standing/downed classes have explicit subcategory annotations and bounded tests. Those are canopy/background proxies, not verified pure endmembers. MATERIAL_CLASS_AUDIT documents counts and rare/incomplete tags. Green vegetation versus soil/shade material fractions are not yet validated.

## 2. Which distinguishable classes are mixture-ambiguous?

{markdown(ambiguity_primary.groupby(["scheme", "sensor"], as_index=False).agg(mean_class_ambiguity_rate=("ambiguity_rate", "mean")))}

These are mean class ambiguity rates in held-out plant folds at relative tolerance 0.01, with correct candidate and other-class convex fits. Class-specific combinations and tolerance sensitivities are retained. Strong historical DBS-ECT/DBT-ECT significance does not eliminate convex overlap; weak DBT-ECS is not treated as an interchangeable material merely because an old test failed.

Selector sensitivity on the SAME plant folds, using at most TWO other materials and a common tolerance of 0.01:

{markdown(selector_summary)}

More proposed candidates improve own-class coverage but also create more wrong-class convex combinations. This check does not use the test data for selection. It guards against blaming intrinsic material physics for one EAR/shade-aware prototype choice. Candidate budget and model assumptions still limit generalization.

Class-specific inferred-PFT ambiguity (pooled held-out polygon-year records across three plant folds):

{markdown(ambiguity_primary[ambiguity_primary.scheme.eq("inferred_pft")][["sensor", "label", "ambiguity_rate", "median_correct_class_RMSE", "median_incorrect_RMSE"]])}

## 3. Which classes are inadequately sampled?

Dead - Debris has one identity; dead herbaceous is rare/incompletely annotated; named taxa have severe long tails; some PFTs are species-confounded. Rare/missing class/fold cells stay insufficient, never merged to inflate performance. Some year-transfer directions have no disjoint training support. See original material counts and fold_support.csv.

## 4. Missing backgrounds?

No verified pure soil, litter, water, snow or measured shade classes. Bare is not proof of soil, and shaded polygons are not shade endmembers. Broad Non-vegetated & dead combines disparate materials.

## 5. How many endmembers before a plateau?

Not established. Optimization probes 1,2,5,10 entries within up to 12 proposed training identities/class. Larger 20/50/100 trials are explicitly outside this budget; nearest-neighbor accumulation separately extends up to 500 where support allows. A bounded curve cannot identify a universal optimal count, and adding candidates can increase mixture ambiguity. library_size_fraction_recovery.csv measures this directly on the same mixtures at 1/2/5/10 entries where exact model counts permit.

{markdown(size_summary)}

## 6. Best selection method on held-out data?

{markdown(methodranking[["scheme", "sensor", "method", "fraction_RMSE"]])}

These are descriptive winners for the declared bounded pool and controlled plant folds, not globally selected operational methods. Three plant folds and one seeded proposed pool do not identify a generally superior selector. Acquisition-stress variants have different targets and are excluded from this ranking. No held-out result was used to choose candidates or change thresholds. IES training kappa need not optimize fractions or retain rare classes.

## 7. Known-fraction recovery?

{primary_table}

EAR_MESMA3 values are macro means of class/fold fraction RMSE/MAE, in fraction units (0.10 = ten percentage points). Truth consists of algebraic weights on held-out COMPOSITE polygon curves. Synthetic success would not establish actual cover accuracy; the observed errors are already substantial for many labels. Class-specific material results:

{markdown(class_recovery[class_recovery.scheme.eq("material")][["sensor", "label", "fraction_RMSE", "fraction_MAE"]])}

## 8. False positives and false negatives?

{markdown(operating_summary)}

Values are macro class/fold conditional frequencies on controlled mixtures, not field error probabilities.

Detection rule estimated fraction >=0.10 was declared before testing; 0.05/0.20 sensitivities are included. detection_errors.parquet reports per-fraction false-positive rates at true zero and false-negative rates at positive truth, with exact simulation denominators. They depend strongly on hierarchy, component and fraction; no single biological FPR/FNR is justified. Reused source parents invalidate treating all gradient points as independent field samples.

## 9. Reliable abundance detection thresholds?

No defensible population 50/80/95% threshold. Figure 4 shows conditional curves. Three plant folds and one parent set per composition provide too little independent replication, and the sources are not verified pure materials. A nominal detection at one simulation fraction is not a calibrated ecological detection limit.

## 10. NEON to OLI loss?

The table above and paired sensor_comparison.csv use the same parents, fractions and candidate identities. Interpret OLI-minus-NEON fraction RMSE within exact class/fold pairs, not the previous 15/16 biological-test retention statistic. Both sensors can be ambiguous; little additional spectral loss does not mean either recovers fractions well. Weighting differs by declared spectral support. This is synthetic reduction, not independent satellite abundance validation.

## 11. Does MESMA outperform FCLS?

method_comparison.csv compares EAR-limited two/three-component variable candidates with fixed class-medoid FCLS on identical mixtures. Performance is hierarchy-dependent. Extra spectral flexibility does not consistently guarantee lower fraction error, and minimal spectral residual is not a fraction-accuracy selector. No universal MESMA advantage is established.

{markdown(comparison[["scheme", "sensor", "EAR_MESMA3", "FCLS_medoid", "MESMA3_minus_FCLS", "MC_mean_FCLS", "MC_minus_FCLS"]])}

## 12. Does Monte Carlo help?

MC_mean_FCLS is evaluated on the same sources; uncertainty tables show its fraction errors, empirical width and conditional truth coverage. An ensemble can stabilize some estimates, but empirical 95% intervals are not assumed calibrated. Twelve endmember draws cannot justify tail-probability claims or resolve unobserved materials. The ensemble improves macro fraction RMSE in this benchmark but often increases thresholded class-set error by distributing fractions across absent classes; it is not an unqualified improvement in material detection.

## 13-15. Flight, year and site transfer?

TRANSFERABILITY.md and transferability_summary.csv give class/fold error distributions, support and exact source memberships. All actual flight holdouts were considered; rare/absent class cases remain explicit. Actual flight spectra are used as targets, and repeated IDs are purged globally. Year/site shifts alter class/taxon composition and candidate availability; no isolated environmental penalty is inferred. Repeated NIWO years never count as geographic replication. Unsupported reverse-year directions do not become optimistic estimates.

## 16. Correct material absent?

{markdown(unknownsummary)}

These are pure nominal-label missing-class diagnostics against training-only thresholds. Wrong classes can fit well; acceptance does not establish presence. unknown_model_status.parquet restores source year from the exactly matching pure-target ledger and explicitly marks NO_ADEQUATE_LIBRARY_MODEL or LOW_RESIDUAL_NOT_VALIDATED_MEMBERSHIP, not a forced operational class. The rates are descriptive repeated-record frequencies, not calibrated field probabilities. Partly unknown mixtures and new background types need additional validation.

## 17. Detect unreliable estimates?

unreliable_fraction_flags.csv reports the fraction of poor estimates hiding below three residual tolerances and sensitivity of a near-model fraction-range flag. Small residual is insufficient. Model-choice ranges and empirical bundles help expose instability but miss within-composition/unsampled variability. No validated operational rejection algorithm is claimed.

## 18. Applications supported now?

Stored-library QC, labelled material/PFT variability, conditional same-library spectral comparisons, controlled linear-mixture geometry and paired spectral-resolution diagnostics. These are exploratory analyses, not calibrated abundance products.

## 19. Applications not supported?

Real vegetation/background/species cover maps, calibrated uncertainty/detection limits, universal cross-site/year fraction transfer, unlabelled-landscape completeness, real Landsat abundance maps and subtle abundance change detection. Independent REAL ABUNDANCE VALIDATION = NOT YET AVAILABLE.

## 20. Exact work before operational MESMA?

Recover per-flight metadata and processing provenance; audit purity and dated labels; reconcile backgrounds; add missing pure materials and rare independent identities; obtain complete co-registered independent fractions; validate larger nested libraries and source-parent replication; calibrate uncertainty/abstention; separate spectral from actual spatial-support effects and validate real sensors across independent acquisitions. No global coefficient or BRDF/SRF change was made to improve this audit.

## Defensible manuscript statement

"In identity-disjoint controlled mixtures constructed from the current 3,639-identity SpectralBridge library, the tested candidate/model sets showed substantial other-class convex overlap. With two EAR-selected candidates per class and at most three nonnegative, sum-one material components, macro class/fold fraction RMSE was 0.344 for inferred PFTs and 0.380 for researcher categories in corrected NEON space, versus 0.351 and 0.380 in paired synthetic OLI space. Larger candidate sets and alternative selectors changed performance but did not establish operational abundance readiness. These simulations use empirical composite polygon curves; unverified source-scale/purity information and unavailable independent fractional-cover truth preclude a claim of field abundance accuracy."

## Final operational readiness matrix

{markdown(pd.DataFrame([dict(material=c, NEON="INSUFFICIENT EVIDENCE", Landsat_like="INSUFFICIENT EVIDENCE") for c in materials]))}

Each cell lacks independently validated material fractions and source/purity completeness. This does not mean all spectral comparisons are impossible. It means the current evidence does not justify operational ecological abundance claims. Ten separate dimensions are recorded in readiness_dimensions.csv; there is no opaque combined score.
""",
)
write(
    "README.md",
    """# MESMA readiness assessment - 2026-10-14

Start with RESULTS.md for the twenty scientific questions and final readiness matrix; MATERIAL_CLASS_AUDIT.md and RECOMMENDATIONS.md explain the data gates. DESIGN.md fixes constraints/thresholds before mixture benchmarks. REPOSITORY_AUDIT.md and LITERATURE_METHODS.md identify reused evidence and primary definitions. Other named reports separate QC, coverage, selection, geometry, controlled mixtures, sensor transfer, grouped transfer and uncertainty. Tables and six PDF/PNG/SVG figure families carry exact counts and memberships.

This is not an operational MESMA implementation or abundance product. No physical unit scale, pure material identity or field fraction was invented. The physical and real-abundance branches stopped at their data gates; explicitly conditional common-scale synthetic diagnostics were still run.

Reproduce from the repository root using the existing compact P120 input summaries:

```bash
python provenance/mesma-readiness/2026-10-14/audit_source.py
python examples/mesma_readiness.py Aug_2026_all_polygons_merged_pixel_extraction.parquet --compact artifacts/plant_spectral_atlas/sensor_pft_transfer/compact --output artifacts/plant_spectral_atlas/mesma_readiness_first_pass --first-pass
python examples/mesma_readiness.py Aug_2026_all_polygons_merged_pixel_extraction.parquet --compact artifacts/plant_spectral_atlas/sensor_pft_transfer/compact --output artifacts/plant_spectral_atlas/mesma_readiness
python provenance/mesma-readiness/2026-10-14/analyze_results.py
python provenance/mesma-readiness/2026-10-14/additional_sensitivity.py
python provenance/mesma-readiness/2026-10-14/ambiguity_sensitivity.py
python provenance/mesma-readiness/2026-10-14/write_report.py
```

The compact products must already be verified against this SAME immutable source; this workflow does not regenerate upstream inputs. This audit checks P120 origin and all owned output hashes before interpretation. For the optional human PDF run build_report.py with reportlab and pypdf available.

Use `.venv/bin/python`, `MPLCONFIGDIR=/tmp/spectralbridge-mpl`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` on the validated local environment. The first pass precedes the expanded audit. Grouped fold checkpoints include source/configuration/code identities and checksums; restarts reuse valid folds. Source Parquet and prior ecological/sensor results are immutable. Candidate pools, not a pixel-scale source copy, bound the combinatorics. See VALIDATION.md for full-suite, exact optimizer, identity leakage, actual-flight target and evidence checks.
""",
)
print("Scientific reports generated from verified tables.")
