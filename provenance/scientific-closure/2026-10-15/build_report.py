"""Human scientific closure: table-derived narrative, five synthesis figures."""

from pathlib import Path
import json
import argparse
import hashlib
from html import escape
import numpy as np
import pandas as pd
from reportlab import rl_config
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    PageBreak,
    NextPageTemplate,
    Image,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from pypdf import PdfReader

rl_config.invariant = 1
BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
PRIOR = REPO / "provenance/spectral-library-analytics/2026-10-14/tables"
DEST = (
    REPO
    / "output/pdf/scientific_closure/What_Can_We_Reliably_Learn_from_the_SpectralBridge_Spectral_Library.pdf"
)
LEVELS = [
    "species_level",
    "researcher_level",
    "narrow_pft",
    "broad_pft",
    "coarse_cover",
]
NAMES = [
    "Recorded species",
    "Researcher categories",
    "Narrow woody PFTs",
    "Broad woody leaf habit",
    "Coarse cover proxy",
]


def read(name):
    return pd.read_csv(BASE / "tables" / name)


def pct(v):
    return f"{float(v) * 100:.1f}%"


def fmt(v):
    return f"{float(v):.3f}"


def markdown_table(rows):
    return (
        "| "
        + " | ".join(rows[0])
        + " |\n| "
        + " | ".join(["---"] * len(rows[0]))
        + " |\n"
        + "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows[1:])
    )


def make_source():
    s = read("biological_generalization.csv")
    s = s[s.probability.eq("raw")]

    def part(level, kind="plant", rep="NEON_full", mode="stored"):
        experiment = "hierarchy" if mode == "stored" else "sensitivity"
        return s[
            s.scheme.eq(level)
            & s.kind.eq(kind)
            & s.representation.eq(rep)
            & s["mode"].eq(mode)
            & s.experiment.eq(experiment)
        ]

    def ba(level, kind="plant", rep="NEON_full", mode="stored"):
        return part(level, kind, rep, mode).balanced_accuracy.mean()

    pair = read("paired_temporal_recognition.csv")

    def paired(level, training, test, rep="NEON_full"):
        return pair[
            pair.scheme.eq(level)
            & pair.training_year.eq(training)
            & pair.test_year.eq(test)
            & pair.representation.eq(rep)
        ].balanced_accuracy.mean()

    temporal = read("paired_temporal_partition.csv")
    annotation = read("annotation_year_audit.csv")
    dates = read("acquisition_date_support.csv")
    metadata = json.loads((BASE / "manifests/metadata_audit.json").read_text())
    spatial = read("native_spatial_support.csv")
    native = spatial[spatial.fit_rank.eq(2)]

    def tp(level, mode="stored"):
        return temporal[
            temporal.level.eq(level)
            & temporal.sensor.eq("NEON")
            & temporal["mode"].eq(mode)
        ].iloc[0]

    sampling = read("sampling_weight_effect.csv")
    niwo = sampling[sampling.site.eq("NIWO")].iloc[0]
    coverage = read("closed_set_coverage.csv")
    effects = read("biological_effect_sizes.csv")
    counts = pd.read_csv(PRIOR / "library_summary.csv").set_index("quantity").value
    unknown = pd.read_csv(PRIOR / "unknown_material_detection.csv")
    unknown = unknown[
        unknown.status.eq("evaluated") & unknown.representation.eq("NEON_full")
    ]
    u = unknown[
        unknown.scheme.eq("inferred_pft") & unknown.detector.eq("nearest_angle_deg")
    ]
    pilot = pd.read_csv(PRIOR / "real_landsat_flight_metrics.csv")
    pilot = pilot[pilot.variant.eq("undarkened")].iloc[0]
    realbase = REPO / "provenance/real-landsat-validation/2026-10-14"
    decomposition = pd.read_csv(realbase / "error_decomposition.csv")
    heterogeneity = decomposition[
        decomposition.variant.eq("undarkened")
        & decomposition.feature.eq("heterogeneity")
    ].Spearman_rho.iloc[0]
    brightness = pd.read_csv(realbase / "brightness_comparison.csv")
    change = brightness[
        brightness.band.eq("seven_band")
        & brightness.metric.eq("pooled_seven_band_RMSE")
    ].iloc[0]
    oldeffects = pd.read_csv(PRIOR / "biological_contrasts.csv")
    oe = oldeffects[oldeffects.scheme.eq("inferred_pft")]
    pages = []

    def page(
        title,
        paragraphs,
        *,
        table=None,
        figure=None,
        evidence="",
        layout="body",
        kicker="SCIENTIFIC CLOSURE",
    ):
        pages.append(
            dict(
                title=title,
                paragraphs=paragraphs,
                table=table,
                figure=figure,
                evidence=evidence,
                layout=layout,
                kicker=kicker,
            )
        )

    sentence = "Broad woody leaf-habit associations in these labelled polygon footprints transfer better across the observed sites and NIWO image years than finer taxonomic distinctions, including after amplitude removal."
    paragraph = f"Within the assigned woody subset, mean full-NEON balanced accuracy was {pct(ba('broad_pft'))} for new polygons and {pct(ba('broad_pft', 'site'))} across held-out sites; shape-only site performance was {pct(ba('broad_pft', 'site', mode='shape'))}. On the same unseen NIWO polygons, a model trained on other 2020 polygons scored {pct(paired('broad_pft', 2020, 2020))} in 2020 and {pct(paired('broad_pft', 2020, 2023))} in 2023. The corresponding species scores fell from {pct(paired('species_level', 2020, 2020))} to {pct(paired('species_level', 2020, 2023))}. Labels recorded in 2023/2024 are reused on both image years; this is retrospective footprint recognition, not independent annual field confirmation. This supports conditional broad functional discrimination, not universal species recognition, causal trait attribution or unique field-mixture recovery."
    page(
        "What can we reliably learn from this library?",
        [
            "Final scientific synthesis | 15 October 2026",
            sentence,
            paragraph,
            "Decision: the library is scientifically promising for supported closed-set ecological discrimination and controlled sensor/mixture diagnostics. Preserve repeated observations and their year/site/acquisition identity. Operational abundance mapping and reliable physical unknown-material recognition remain unvalidated.",
            "This report closes the analysis. It reuses completed functional, sensor, real-Landsat, classifier and mixture evidence. New calculations address paired temporal change, biological resolution, shape/amplitude and repeat representation; no production correction, sensor coefficients or raw-library normalization changed.",
        ],
        evidence="biological_generalization.csv; paired_temporal_recognition.csv; FINAL_READINESS_MATRIX.csv",
        kicker="EXECUTIVE DECISION",
    )
    support = read("observational_support.csv")
    cohorts = (
        support[support.level.eq("researcher_level")]
        .groupby(["site", "year"])
        .identities.sum()
        .reset_index()
    )
    rows = [["Site", "Year", "Polygon IDs"]] + [
        [r.site, str(r.year), f"{r.identities:,}"]
        for r in cohorts.itertuples(index=False)
    ]
    page(
        "1. What data do we actually have?",
        [
            f"The source has {int(counts['pixel_rows']):,} pixel records, {int(counts['identities']):,} unique GlobalIDs and {int(counts['polygon_years']):,} annual polygon summaries, with {int(counts['flights'])} acquisition/flightline product identities. Pixels and repeats are not additional independent plants. A GlobalID is a polygon identifier; biological-individual or population purity is not established.",
            f"NIWO contains {int(tp('researcher_level').identities):,} polygons observed in both 2020 and 2023. Every 2023 NIWO polygon in this library has a 2020 observation. WREF and YELL contribute 2023 observations only. Site, year, species and acquisition history are therefore incompletely crossed.",
            "Researcher categories, species names and inferred traits are separate labels. The broad PFT used here is deciduous versus evergreen within crosswalk-assigned woody taxa. The coarse cover grouping contrasts vegetation-labelled records with the heterogeneous nonvegetated/dead source category; it is not pure vegetation versus mineral soil.",
            f"The source histories identify {len(dates)} site-date groups, not necessarily independent flight events. Polygon field-year metadata span {int(annotation.field_year.min())}-{int(annotation.field_year.max())}; NIWO's polygon imagery_year stays 2020 even for 2023 extractions. Acquisition year here comes from actual source histories. Reused labels are not independent annual field observations.",
            f"The extracted raster-coordinate vectors have median native lengths {native.pixel_col_vector_length.median():.2f} by {native.pixel_row_vector_length.median():.2f} in verified metre grids. Median extracted support is {metadata['median_extracted_pixels_per_polygon_acquisition']:.0f} pixels per polygon/acquisition. This is native polygon support, not an independently measured pure plant endmember.",
            "The common corrected NEON spectrum retains supported coordinates without bridging atmospheric gaps. OLI is derived from that reference; MicaSense physical coordinates remain unverified. Finite negative corrected values remain valid. Library stored units are unresolved and are not silently treated as unitless reflectance.",
        ],
        table=rows,
        evidence="observational_support.csv; flight_support.csv; product_support.csv; identity_sampling.csv; DATA_AUDIT inherited from P126",
    )
    page(
        "Figure 1. Observations, labels and repeat sampling",
        [],
        figure="F1_library_structure",
        layout="figure",
        evidence="observational_support.csv; sampling_weight_effect.csv; identity_sampling.csv",
    )
    r = tp("narrow_pft")
    rows = [
        [
            "Label resolution",
            "Paired IDs",
            "Class SS share",
            "Common year share",
            "Change / class distance",
        ]
    ]
    for level, name in zip(LEVELS, NAMES):
        a = tp(level)
        rows.append(
            [
                name,
                str(int(a.identities)),
                pct(a.class_fraction),
                pct(a.year_fraction),
                fmt(a.change_to_class_ratio),
            ]
        )
    page(
        "2. How large is change in the same polygon?",
        [
            "We compare the complete 2020/2023 NIWO pairs, retaining only stable labels with descriptive support. A balanced two-year decomposition separates class differences, persistent polygon differences within a class, a common year shift, class-specific year shifts and residual polygon-specific change. The components sum exactly to the observed total.",
            f"For narrow PFTs, the common year component is {pct(r.year_fraction)} of paired-panel variation; persistent differences among polygons within class account for {pct(r.polygon_within_class_fraction)}, and residual polygon-specific change for {pct(r.residual_change_fraction)}. The RMS change in a polygon is {fmt(r.change_to_class_ratio)} times the equally weighted class-centroid separation.",
            "Thus substantial temporal change does not require a large uniform year offset. Individual polygons can move differently, including changes large enough to disrupt fine discrimination. Shape normalization reduces several temporal differences but does not make every broad centroid separation stronger.",
            "These are descriptive sums of squares, not causal population variance components. There is no within-NIWO site variance to estimate, only two years, and no balanced global site-year experiment. Changes may combine ecology, phenology, illumination, acquisition composition and processing; this dataset cannot apportion those causes. Stable labels across pairs reflect annotation reuse, not independent proof of biological stability.",
        ],
        table=rows,
        evidence="paired_temporal_partition.csv; paired_polygon_changes.csv; paired_label_audit.csv",
    )
    page(
        "Figure 2. Paired temporal change and recognition",
        [],
        figure="F2_temporal_resolution",
        layout="figure",
        evidence="paired_temporal_partition.csv; paired_temporal_recognition.csv; paired_temporal_accuracy_change.csv",
    )
    rows = [
        [
            "Resolution",
            "IDs / labels*",
            "New polygon",
            "Held site",
            "Global held year",
            "OLI new polygon",
        ]
    ]
    for level, name in zip(LEVELS, NAMES):
        rows.append(
            [
                name,
                f"{int(effects[(effects.level == level) & (effects.sensor == 'NEON') & (effects['mode'] == 'stored')].identities.iloc[0]):,} / {int(effects[(effects.level == level) & (effects.sensor == 'NEON') & (effects['mode'] == 'stored')].classes.iloc[0])}",
                pct(ba(level)),
                pct(ba(level, "site")),
                pct(ba(level, "year")),
                pct(ba(level, rep="OLI")),
            ]
        )
    species = coverage[coverage.level.eq("species_level") & coverage.kind.eq("site")]
    wref = species[species.fold.eq("site_WREF")].iloc[0]
    page(
        "3. What is the finest useful biological resolution?",
        [
            "Species is the finest tested target, but its support is conditional. We retain exact recorded two-token binomial names rather than promote genus-only or unidentified records to species. Training requires at least ten distinct IDs per class and test reporting at least three; missing/rare/absent-training classes remain explicit.",
            f"Species mean new-polygon balanced accuracy is {pct(ba('species_level'))}, versus {pct(ba('species_level', 'site'))} at held sites and {pct(ba('species_level', 'year'))} in global year holdouts. At WREF only {pct(wref.closed_set_fraction)} of named-species target IDs meet closed-set support; the score is not a claim to recognize all species there.",
            f"Broad woody leaf habit is more transferable: mean new-polygon/site scores are {pct(ba('broad_pft'))}/{pct(ba('broad_pft', 'site'))}. But it covers assigned woody taxa, not herbaceous or background records. Researcher categories retain their separate, useful five-class interpretation.",
            "Support counts marked * use the global descriptive subset with at least ten IDs per label; actual fold eligibility differs. The table compares different class counts, chance references and eligible populations. It is not proof that coarsening the same set of records monotonically improves information. The practical conclusion is conditional species recognition within familiar distributions, with broader functional labels better supported for transfer across these observed domains.",
        ],
        table=rows,
        evidence="biological_generalization.csv; biological_effect_sizes.csv; closed_set_coverage.csv; fold_support.csv; all_class_detection_rates.csv",
    )
    page(
        "Figure 3. Biological resolution, shape and sensor retention",
        [],
        figure="F3_generalization_shape_sensor",
        layout="figure",
        evidence="biological_generalization.csv; brightness_sampling_sensitivity.csv; closed_set_coverage.csv; prior wavelength_selection.csv",
    )
    rows = [
        [
            "Label scheme",
            "Stored site BA",
            "Shape-only site BA",
            "Amplitude-only site BA",
        ]
    ]
    for level, name in zip(
        ["researcher_level", "narrow_pft", "broad_pft"],
        ["Researcher categories", "Narrow PFT", "Broad woody habit"],
    ):
        rows.append(
            [
                name,
                pct(ba(level, "site")),
                pct(ba(level, "site", mode="shape")),
                pct(ba(level, "site", mode="amplitude")),
            ]
        )
    page(
        "4. Is the result merely brightness? What survives Landsat?",
        [
            "The analytical shape sensitivity divides each observation by its own weighted spectral norm. No population parameter or test label is used, and the production library is unchanged. An amplitude-only model uses that single norm. All learned scaling and tuning remain confined to proper training.",
            f"Broad woody shape-only held-site performance is {pct(ba('broad_pft', 'site', mode='shape'))}, versus {pct(ba('broad_pft', 'site', mode='amplitude'))} from amplitude alone. Researcher/narrow PFT recognition also remains useful after amplitude removal. These results reject an amplitude-only explanation within these tested labels/domains, without identifying a causal physiological mechanism.",
            f"The existing functional sensor audit retains {int((oe.NEON_supported & oe.OLI_supported).sum())} of {int(oe.NEON_supported.sum())} NEON-supported inferred-PFT contrasts in synthetic OLI. Broad woody OLI new-polygon/site scores are {pct(ba('broad_pft', rep='OLI'))}/{pct(ba('broad_pft', 'site', rep='OLI'))}. Sensor aggregation loses some information but does not erase this broad distinction. Synthetic OLI changes spectral response at native/polygon support; it does not simulate 30 m spatial mixing, point-spread function or actual Landsat noise.",
            "Training-selected narrow coordinates are correlated and not an optimized sensor. Repeated inferred-PFT selection concentrates in the established SWIR region, with additional NIR/SWIR functional localization. Placement, bandwidth, averaging, band count and selection method change together; their independent causal contributions are not identified.",
            f"The real R10C/Landsat pilot supplies independent 30 m footprint radiometric/spatial context: {int(pilot.N):,} matched footprints, {int(pilot.spatial_blocks)} blocks, pooled SR RMSE {pilot.pooled_seven_band_RMSE:.5f}. It remains one next-day pair with a timestamp caveat, not a regional ecological validation. Heterogeneity-error Spearman association is {heterogeneity:.3f} (descriptive spatially correlated footprints); the brightness-adjustment RMSE difference is {change.adjusted_minus_undarkened:.5f} with interval [{change.lo:.5f}, {change.hi:.5f}], spanning zero. Offset diagnostics support retaining original alignment. Atmosphere, timing, illumination and BRDF cannot be separately estimated here.",
        ],
        table=rows,
        evidence="brightness_sampling_sensitivity.csv; prior biological_contrasts.csv; prior real_landsat_flight_metrics.csv; prior registration/heterogeneity diagnostics",
    )
    ambiguity = pd.read_csv(PRIOR / "mixture_identifiability.csv")
    ambiguity = ambiguity[
        ambiguity.scheme.eq("inferred_pft")
        & ambiguity.sensor.eq("NEON")
        & ambiguity.kind.eq("plant")
    ]
    recovery = pd.read_csv(PRIOR / "mixture_recovery.csv")
    recovery = recovery[
        recovery.scheme.eq("inferred_pft")
        & recovery.sensor.eq("NEON")
        & recovery.kind.eq("plant")
        & recovery.method.eq("EAR_MESMA3")
    ]
    detection = pd.read_csv(PRIOR / "detection_limits.csv")
    detection = detection[
        detection.scheme.eq("inferred_pft") & detection.sensor.eq("NEON")
    ]
    rows = [
        [
            "PFT",
            "Ambiguous records",
            "Fraction RMSE",
            "False detection at 0",
            "Miss at true 0.20",
        ]
    ]
    for label in sorted(ambiguity.label.unique()):
        amb = ambiguity[ambiguity.label.eq(label)].ambiguity_rate.iloc[0]
        err = recovery[recovery.label.eq(label)].fraction_RMSE.mean()
        d = detection[detection.label.eq(label)]
        fp = d[np.isclose(d.true_fraction, 0)].conditional_detection_frequency.iloc[0]
        fn = (
            1
            - d[np.isclose(d.true_fraction, 0.2)].conditional_detection_frequency.iloc[
                0
            ]
        )
        rows.append([label, pct(amb), fmt(err), pct(fp), pct(fn)])
    page(
        "5. Is the library ready to test mixtures?",
        [
            "Yes, as an exploratory laboratory for constrained synthetic recoverability. No, as a validated field-abundance mapping system. Endmember coverage, redundancy, selector sensitivity, ambiguity and fraction recovery are already tested; repeating them would not create independent truth.",
            "FCLS enforces nonnegative fractions that sum to one. MESMA compares small models with variable candidate spectra. Saved test parents, fractions and candidate identities are held fixed in sensor comparisons. This establishes mathematical performance under the declared linear mixture model, not canopy, biomass or surface-cover accuracy.",
            "Wrong-class combinations often explain an observed spectrum as well as its own class. More endmembers can reduce residual error while adding alternative compositions. Therefore a low residual and good classification accuracy do not establish a unique or correct mixture.",
            "The table uses the existing 0.10 detection cutoff and positive-fraction presence rule. Rates condition on repeated synthetic parent trajectories, not independent field populations. Class-specific D50/D80/D95 remain unestimated. EBS has lower conditional ambiguity but sparse support; no PFT is certified uniquely identifiable.",
            "DBS/DBT are deciduous broadleaf shrubs/trees; EBS is evergreen broadleaf shrub; ECS/ECT are evergreen conifer shrubs/trees. These inferred woody types are not pure physical-material measurements.",
        ],
        table=rows,
        evidence="prior mixture_identifiability.csv; prior mixture_recovery.csv; prior detection_limits.csv; prior library-size/selector/uncertainty tables",
    )
    page(
        "Figure 4. Mixture ambiguity, recovery and false detection",
        [],
        figure="F4_mixture_limits",
        layout="figure",
        evidence="verified P123/P126 mixture, detection and withheld-class master tables",
    )
    oldsummary = pd.read_csv(PRIOR / "ml_generalization.csv")
    c = oldsummary[
        oldsummary.scheme.eq("inferred_pft")
        & oldsummary.model.eq("logistic")
        & oldsummary.representation.eq("NEON_full")
        & oldsummary.probability.eq("raw")
    ]
    plant = c[c.kind.eq("plant")]
    site = c[c.kind.eq("site")]
    page(
        "6. How should false positives and uncertainty be read?",
        [
            "For each class, sensitivity/recall measures detection among true members; false-negative rate is its complement. Specificity measures rejection among all other known classes; false-positive rate is its complement. Precision asks how often an assigned label is correct. Multiclass negative pools and class prevalence matter, so these are not one universal Type I/II error pair.",
            "The class table retains TP/FP/TN/FN, support, recall, specificity, precision and whole-identity conditional bootstrap intervals by fold and paired year. Rare/absent classes are not turned into reassuring zero-error rates. Confusion matrices show which classes are confused.",
            f"For omitted PFTs, nearest-angle unknown recall averages {pct(u.unknown_recall.mean())} at known rejection {pct(u.known_false_rejection.mean())}. Most proxy unknowns therefore remain accepted. The declared 80%-recall/5%-known-FPR review scenario is not satisfied by this average result; physical unknown materials are less comprehensively tested still.",
            f"Existing full-NEON PFT group-conformal joint-identity coverage spans {pct(plant.identity_joint_coverage.min())}-{pct(plant.identity_joint_coverage.max())} for plant folds, and {pct(site.identity_joint_coverage.min())}-{pct(site.identity_joint_coverage.max())} for sites, against a 90% nominal target. Independent calibration is valuable but does not grant geographic exchangeability.",
            "Brier score, log loss, reliability bins and ECE assess probability quality. Temperature scaling is fitted on separate known training identities; it does not fix domain shift automatically. Endmember Monte Carlo intervals quantify choice stability and can under-cover; they are not validated field fraction confidence intervals.",
        ],
        evidence="all_class_detection_rates.csv; new_confusion.csv; prior unknown_material_detection.csv; uncertainty_calibration.csv; mixture_uncertainty.csv",
    )
    page(
        "7. Keep repeats, but do not let them dominate",
        [
            f"NIWO supplies {pct(niwo.annual_row_share)} of annual rows but {pct(niwo.identity_share)} of unique polygon IDs. A repeated polygon can receive twice the row weight of a single-year polygon before flights or pixels are considered. This is a sampling distinction, not extra biological independence.",
            f"Choosing only the earliest proper-training observation per identity reduces narrow-PFT new-polygon BA from {pct(ba('narrow_pft'))} to {pct(ba('narrow_pft', mode='one_identity'))}; researcher-category BA changes from {pct(ba('researcher_level'))} to {pct(ba('researcher_level', mode='one_identity'))}. This sensitivity jointly removes temporal representation and changes weights. It does not isolate a pure weighting effect.",
            "Recommendation: preserve every scientifically valid source observation with polygon, site, year, flight/source, product, label and QA metadata. Derive annual summaries, prototypes and endmembers separately and version them. Never erase the year/site identity by replacing the archive with a grand average.",
            "For an equal-polygon inferential target, distribute a polygon’s total training weight across its repeated observations (for example, 1/n within that identity), and assess class/site weighting against the intended target population. Keep entire identity histories together in validation. Pixel count must not determine biological training weight.",
            "For a new observation: preserve the original source; verify units and native coordinates; resolve GlobalID linkage and source labels; retain uncertain/unknown labels; apply documented QA; update derived summaries with provenance; and test new domains against frozen identity/site/year holdouts before retraining. Add independent truth as a separate evidence layer, never as another synthetic derivative.",
        ],
        evidence="sampling_weight_effect.csv; identity_sampling.csv; brightness_sampling_sensitivity.csv; paired_polygon_changes.csv; label_hierarchy.csv",
    )
    page(
        "Figure 5. What the library is ready for",
        [],
        figure="F5_final_decisions",
        layout="figure",
        evidence="FINAL_READINESS_MATRIX.csv; DESIGN.md",
    )
    page(
        "8. The final use decision and its criteria",
        [
            "Use now: reproducible descriptive characterization; conditional group contrasts; supported closed-set recognition in explicitly tested populations; sensor-response diagnostics; and exploratory endmember/mixture stress tests. Use the source-label interpretation appropriate to the question.",
            "Classification is scientifically promising when supported folds beat the equal-class reference with conditional lower intervals. The review scenario for constrained predictive use additionally asks for at least 0.70 class recall and a 0.70 balanced-accuracy lower bound throughout its specified domain, plus an agreed ecological error tolerance and independent validation. These are necessary review aids, not automatic approvals or universal biological thresholds. Species use is downgraded to exploratory because target coverage and paired temporal transfer are poor, despite useful known-class polygon scores.",
            "Composition is flagged nonunique when wrong-class alternatives are common at the established 0.01 residual tolerance. A hypothetical ten-percentage-point fraction application also requires RMSE no greater than 0.10, appropriate uncertainty and independent measured truth. The current evidence does not meet an operational abundance gate.",
            "Unknown rejection review uses at least 0.80 recall at no more than 0.05 known false rejection. Current proxy-class challenges are inadequate for reliable open-world membership certification. No final-test threshold optimization is used to manufacture a pass.",
            "The decision matrix distinguishes not ready, exploratory, scientifically promising, validated for constrained use and operationally validated. Only the single real-Landsat radiometric/spatial comparison has the narrowly constrained empirical interpretation stated there. No ecological abundance application is operationally validated.",
        ],
        evidence="FINAL_READINESS_MATRIX.csv; DESIGN.md; biological_evidence_ladder.csv; class-specific support/rates",
    )
    page(
        "9. The smallest new evidence that would change the answer",
        [
            "First, recover original units/scaling and physical wavelength headers, especially the unresolved MicaSense export, and document polygon/material purity. This is inexpensive provenance recovery before purchasing more imagery. It can remove validity gates but cannot by itself validate abundance.",
            "Highest scientific priority: independent co-located fraction and purity measurements at the relevant footprint, including true absences, low positive fractions and mixed materials. Use independently sampled parents/plots rather than many fraction levels from the same few spectra. This directly tests abundance, false detection and interval coverage.",
            "Next: balanced repeated identities across additional site-year combinations, prioritizing underrepresented PFTs/species and deliberately crossing year with site. Retain a held-out acquisition/domain and independently record contemporary labels, mortality/turnover, persistent individual linkage and physiology/environment/illumination where practical. Recover dated historical field/photo evidence for retrospective image years; a later survey alone does not verify the earlier biological state. This distinguishes temporal ecology from observation conditions better than simply increasing pixel count.",
            "Then: synchronized independent NEON, Landsat and physically verified drone observations across more sites/seasons, with common footprints and independent field references. This tests real sensor transfer rather than shared-reference convolution.",
            "Determine sample size from the scientific error tolerance and clustered design; these data do not justify a universal number of pixels, plots or flights. Additional algorithm searches are lower priority than resolving missing truth and crossed sampling.",
        ],
        evidence="NEXT_DATA_NEEDED.md; FINAL_READINESS_MATRIX.csv",
    )
    effect_rows = [
        ["Resolution", "Stored eta squared [95%]", "Shape eta squared [95%]"]
    ]
    for level, name in zip(LEVELS, NAMES):
        e = effects[effects.level.eq(level) & effects.sensor.eq("NEON")].set_index(
            "mode"
        )
        effect_rows.append(
            [
                name,
                f"{e.loc['stored', 'eta_squared']:.3f} [{e.loc['stored', 'eta_low']:.3f}, {e.loc['stored', 'eta_high']:.3f}]",
                f"{e.loc['shape', 'eta_squared']:.3f} [{e.loc['shape', 'eta_low']:.3f}, {e.loc['shape', 'eta_high']:.3f}]",
            ]
        )
    page(
        "Descriptive class effects and their limits",
        [
            "The class-effect fraction is the proportion of weighted spectral variation explained by class centers. Each polygon identity contributes total weight one across its annual observations. The descriptive subset requires at least ten global identities per class; the identity/label support column in the recognition table refers to this subset, while actual fold eligibility can differ.",
            "Intervals resample whole identities within classes. These are descriptive associations, not causal effects or new family-adjusted significance tests. Class count, eligible population and site/species composition differ across levels, so larger eta squared is not proof of a scientifically superior classification hierarchy.",
            "A modest fraction of total spectral variance can coexist with accurate multivariate recognition: large within-class variation may occupy different directions from a discriminating boundary. Use the independently held-out recognition and class-error evidence for prediction decisions. The earlier blocked functional contrasts remain the confirmatory sampled-group evidence.",
        ],
        table=effect_rows,
        evidence="biological_effect_sizes.csv; observational_support.csv; fold_support.csv; prior blocked functional results",
        kicker="TECHNICAL NOTES",
    )
    methods = [
        ["Question", "Method and why", "What it does not prove"],
        [
            "What changes within a polygon?",
            "Complete two-year pairing; orthogonal descriptive SS and paired-ID bootstrap",
            "Causal temporal or geographic random-effect variance",
        ],
        [
            "Can labels transfer?",
            "Grouped outer holdouts; training-only scaling/tuning; same unseen targets across years",
            "Novel species/regions outside supported targets",
        ],
        [
            "Brightness or shape?",
            "Per-observation weighted unit norm; amplitude-only sensitivity",
            "Production normalization or a physiological cause",
        ],
        [
            "Are classes separated?",
            "Reused blocked functional tests plus descriptive identity-balanced eta squared",
            "Predictive accuracy or fair class-count-adjusted hierarchy ranking",
        ],
        [
            "Are errors controlled?",
            "Class-wise confusion/rates; clustered intervals; independent calibration and empirical coverage",
            "A geographic or field-abundance guarantee",
        ],
        [
            "Can fractions be recovered?",
            "Reused constrained exact synthetic mixtures and ambiguity checks",
            "Independent real-world abundance validation",
        ],
    ]
    page(
        "Methods in plain language",
        [
            f"A metadata-only source audit found {metadata['source_pixel_keys_shared_by_distinct_IDs']} exact source-image/flight/row/column pixels shared by distinct GlobalIDs among {metadata['original_rows']:,} records. This rules out that specific duplicate-pixel mechanism, not spatial autocorrelation, polygon purity or every possible geometry issue.",
            "The main reusable statistics are tested against exact synthetic identities. Numerical validation independently reproduces saved predictions, metrics, calibration thresholds, identity roles and the balanced-panel partition. Descriptive class effects use equal identity weight and remain conditional associations, partly confounded with site/year/species.",
            "Bootstrap intervals resample whole identities, stratified by class, retaining paired years. Different holdouts support different classes. No site-superpopulation interval, new p-value family, causal variance estimate or post-hoc best-model claim is introduced.",
        ],
        table=methods,
        evidence="FINAL_ANALYSIS_AUDIT.md; DESIGN.md; manifests/numerical_validation.json; tests/test_spectral_closure.py",
        kicker="TECHNICAL NOTES",
    )
    manuscript = (
        f"The source comprised {int(counts['identities']):,} polygon identities and {int(counts['polygon_years']):,} polygon-year summaries across three sites, with repeated observations restricted to NIWO. In the paired NIWO panel, narrow-PFT temporal change was {fmt(tp('narrow_pft').change_to_class_ratio)} times the RMS class-centroid separation, while the common year component accounted for {pct(tp('narrow_pft').year_fraction)} of total paired variation. Most variation was persistent within-class polygon structure and polygon-specific change rather than a shared year offset. Source field annotations date from 2023/2024 and were reused across image years, so the paired task evaluates retrospective labelled footprints rather than independently verified annual biological status. "
        f"For full-NEON broad woody leaf habit, mean identity-held-out balanced accuracy was {pct(ba('broad_pft'))}; held-site accuracy averaged {pct(ba('broad_pft', 'site'))}, and shape-only held-site accuracy averaged {pct(ba('broad_pft', 'site', mode='shape'))}. On identical unseen NIWO targets, 2020-trained broad-label recognition changed from {pct(paired('broad_pft', 2020, 2020))} to {pct(paired('broad_pft', 2020, 2023))}, compared with {pct(paired('species_level', 2020, 2020))} to {pct(paired('species_level', 2020, 2023))} for supported species. "
        f"Synthetic OLI retained useful broad discrimination ({pct(ba('broad_pft', rep='OLI'))} mean new-polygon accuracy), whereas mixture ambiguity, synthetic fraction error and weak omitted-class rejection prevented operational abundance conclusions. These results support conditional broad functional discrimination and retention of temporal observations, with explicit limits on finer taxonomic and mixture inference."
    )
    page(
        "Manuscript-ready Results narrative",
        [
            manuscript,
            "Interpretation boundaries: these comparisons use partial label hierarchies, differing class counts and eligible populations; they are not a causal decomposition of information loss. Broad leaf habit is inferred from woody taxa rather than measured on every polygon. Shape-only discrimination does not identify the responsible physiological mechanism. Two years at one repeated site do not define long-term temporal variance.",
            "The report preserves negative findings: limited named-species coverage at some sites, narrow-class temporal failure, poor unknown recall, shifted uncertainty coverage and nonunique mixtures. Further fitting cannot replace missing independent mixture truth or a balanced observation design.",
        ],
        evidence="all numerical master tables; original conditional inference/sensor/mixture evidence",
        kicker="MANUSCRIPT TEXT",
    )
    page(
        "Validation, literature and provenance",
        [
            "The complete feasible offline suite, focused analytic tests, strict docs, links, formatting and numerical/lineage checks are recorded in VALIDATION.md and the checks/manifests folders. Skipped optional/network/full integrations are not represented as executed field validation. Earlier analyses remain immutable and their evidence hashes are checked.",
            "Roberts et al. (2017), Ecography: structured ecological cross-validation. https://doi.org/10.1111/ecog.02881",
            "Cawley and Talbot (2010), JMLR: model-selection overfitting and nested evaluation. https://www.jmlr.org/beta/papers/v11/cawley10a.html",
            "Bioucas-Dias et al. (2012): spectral unmixing, variability and inverse-problem limits. https://doi.org/10.1109/JSTARS.2012.2194696",
            "Angelopoulos and Bates (2021): split conformal calibration and exchangeability assumptions. https://arxiv.org/abs/2107.07511",
            "Published methods versus adaptations, source sensor definitions, endmember-selection references and real-Landsat QA are documented in the reused P123/P126 literature/provenance records. The new balanced-panel partition is an algebraic descriptive identity, verified by exact tests; it is not presented as a fitted causal mixed-effects model.",
            "Editable report source, five full-resolution figure sets, final readiness/evidence tables, source hashes, fitted model/membership references and the audit matrix make every numerical claim traceable. No independent fraction observations were invented. Production NEON/drone correction behavior is unchanged.",
        ],
        evidence="VALIDATION.md; manifests/closure_run.json; manifests/broad_sensitivity.json; manifests/report_manifest.json; reused literature audits",
        kicker="VERIFICATION AND SOURCES",
    )
    # Deliver requested text at three levels, generated from exact result tables.
    text = (
        "# Final scientific synthesis\n\n## One sentence\n\n"
        + sentence
        + "\n\n## One paragraph\n\n"
        + paragraph
        + "\n\n## Manuscript-ready Results\n\n"
        + manuscript
        + "\n\n"
    )
    text += (
        "\n\n".join(
            "## "
            + p["title"]
            + "\n\n"
            + "\n\n".join(p["paragraphs"])
            + "\n\n"
            + ("Evidence: " + p["evidence"])
            for p in pages
            if p["layout"] == "body"
        )
        + "\n"
    )
    (BASE / "FINAL_SCIENTIFIC_SYNTHESIS.md").write_text(text)
    next_page = [p for p in pages if p["title"].startswith("9.")][0]
    (BASE / "NEXT_DATA_NEEDED.md").write_text(
        "# Next data needed, ranked by scientific value\n\n"
        + "\n\n".join(next_page["paragraphs"])
        + "\n"
    )
    return dict(
        title="What Can We Reliably Learn from the SpectralBridge Spectral Library?",
        date="2026-10-15",
        pages=pages,
    )


def render(source):
    fonts = "/System/Library/Fonts/Supplemental/"
    pdfmetrics.registerFont(TTFont("Closure", fonts + "Arial.ttf"))
    pdfmetrics.registerFont(TTFont("ClosureBold", fonts + "Arial Bold.ttf"))
    styles = dict(
        title=ParagraphStyle(
            "title",
            fontName="ClosureBold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#173f50"),
            spaceAfter=14,
        ),
        body=ParagraphStyle(
            "body", fontName="Closure", fontSize=10.5, leading=15, spaceAfter=10
        ),
        small=ParagraphStyle(
            "small",
            fontName="Closure",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#53656b"),
            spaceAfter=6,
        ),
        kicker=ParagraphStyle(
            "kicker",
            fontName="ClosureBold",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#a55f3d"),
            spaceAfter=8,
        ),
        table=ParagraphStyle("table", fontName="Closure", fontSize=8, leading=10.5),
    )
    figures = {
        f["name"]: f
        for f in json.loads((BASE / "manifests/figures.json").read_text())["figures"]
    }

    def footer(canvas, doc):
        width, height = canvas._pagesize
        canvas.setStrokeColor(colors.HexColor("#ced8da"))
        canvas.line(54, 36, width - 54, 36)
        canvas.setFont("Closure", 7.5)
        canvas.setFillColor(colors.HexColor("#53656b"))
        canvas.drawString(54, 24, "SPECTRALBRIDGE | SCIENTIFIC CLOSURE | 15 OCT 2026")
        canvas.drawRightString(width - 54, 24, str(doc.page))

    DEST.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(DEST),
        pagesize=(612, 792),
        title=source["title"],
        author="SpectralBridge scientific synthesis",
        leftMargin=54,
        rightMargin=54,
        topMargin=45,
        bottomMargin=45,
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="body",
                frames=[
                    Frame(
                        54,
                        48,
                        504,
                        699,
                        leftPadding=0,
                        rightPadding=0,
                        topPadding=0,
                        bottomPadding=0,
                    )
                ],
                onPage=footer,
                pagesize=(612, 792),
            ),
            PageTemplate(
                id="figure",
                frames=[
                    Frame(
                        45,
                        48,
                        702,
                        520,
                        leftPadding=0,
                        rightPadding=0,
                        topPadding=0,
                        bottomPadding=0,
                    )
                ],
                onPage=footer,
                pagesize=(792, 612),
            ),
        ]
    )
    story = []
    for i, page in enumerate(source["pages"]):
        if i:
            story.extend([NextPageTemplate(page["layout"]), PageBreak()])
        story.extend(
            [
                Paragraph(escape(page["kicker"]), styles["kicker"]),
                Paragraph(escape(page["title"]), styles["title"]),
            ]
        )
        for paragraph in page["paragraphs"]:
            story.append(Paragraph(escape(paragraph), styles["body"]))
        if page.get("table"):
            rows = [
                [Paragraph(escape(str(v)), styles["table"]) for v in row]
                for row in page["table"]
            ]
            n = len(rows[0])
            widths = [504 / n] * n
            if n == 3:
                widths = [125, 190, 189]
            if n >= 5:
                widths = [135] + [(504 - 135) / (n - 1)] * (n - 1)
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4edef")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f3f6f5")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.extend([Spacer(1, 4), table])
        if page.get("figure"):
            from PIL import Image as PILImage

            path = BASE / "figures" / f"{page['figure']}.png"
            with PILImage.open(path) as im:
                w, h = im.size
            scale = min(690 / w, 365 / h)
            story.append(Image(str(path), w * scale, h * scale))
            story.append(
                Paragraph(escape(figures[page["figure"]]["caption"]), styles["small"])
            )
        story.extend(
            [
                Spacer(1, 8),
                Paragraph("Evidence: " + escape(page["evidence"]), styles["small"]),
            ]
        )
    doc.build(story)
    return DEST


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-json", type=Path)
    args = parser.parse_args()
    source = (
        json.loads(args.source_json.read_text()) if args.source_json else make_source()
    )
    (BASE / "report_source.json").write_text(json.dumps(source, indent=2) + "\n")
    result = render(source)
    reader = PdfReader(result)
    report = dict(
        pdf=str(result.relative_to(REPO)),
        pdf_sha256=hashlib.sha256(result.read_bytes()).hexdigest(),
        pages=len(reader.pages),
        source=str((BASE / "report_source.json").relative_to(REPO)),
        sections=[
            dict(title=p["title"], figure=p.get("figure"), evidence=p["evidence"])
            for p in source["pages"]
        ],
        table_hashes={
            str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((BASE / "tables").glob("*.csv"))
        },
        source_library_sha256="cd3a8afd2697f09d1f4749f92df8a5e2cc71ee12490d38de12f21f90b2a75978",
    )
    report["figure_hashes"] = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((BASE / "figures").glob("*"))
        if p.is_file()
    }
    (BASE / "manifests/report_manifest.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(result, len(reader.pages), "pages")


if __name__ == "__main__":
    main()
