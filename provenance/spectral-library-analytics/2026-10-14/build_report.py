"""Build the human science report from machine-readable audit tables.

Run with the bundled document Python (ReportLab/pandas/pypdf). The generated
report_source.json is editable: --source-json renders an edited narrative without
recomputing experiments. Default generation reads and formats actual result tables.
"""

from pathlib import Path
import argparse
import hashlib
import json
from html import escape
import numpy as np
import pandas as pd
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    Table,
    TableStyle,
)
from reportlab import rl_config

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

rl_config.invariant = 1

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
DEST = (
    REPO
    / "output/pdf/spectral_library_analytics/SpectralBridge_Spectral_Library_Analytics_Report.pdf"
)


def read(name):
    return pd.read_csv(BASE / "tables" / name)


def pct(v):
    return f"{100 * float(v):.1f}%"


def num(v):
    return f"{float(v):.3f}"


def data_table(frame, columns, labels=None, limit=None):
    frame = frame[columns]
    if limit is not None:
        frame = frame.head(limit)
    rows = [labels or columns]
    for row in frame.itertuples(index=False, name=None):
        rows.append(
            [num(v) if isinstance(v, (float, np.floating)) else str(v) for v in row]
        )
    return rows


def make_source():
    s = read("ml_generalization.csv")
    raw = s[s.probability.eq("raw")]
    primary = raw[raw.model.eq("logistic")]

    def part(scheme="inferred_pft", kind="plant", rep="NEON_full"):
        return primary[
            primary.scheme.eq(scheme)
            & primary.kind.eq(kind)
            & primary.representation.eq(rep)
        ]

    def ba(scheme="inferred_pft", kind="plant", rep="NEON_full"):
        return part(scheme, kind, rep).balanced_accuracy.mean()

    pft = part()
    site = part(kind="site")
    effects = read("biological_contrasts.csv")
    e = effects[effects.scheme.eq("inferred_pft")]
    ec = effects[effects.scheme.eq("researcher_category")]
    # Current legacy scheme string is read rather than presumed.
    if not len(ec):
        ec = effects[~effects.scheme.eq("inferred_pft")]
    summary = read("library_summary.csv").set_index("quantity").value

    def count(k):
        return f"{int(float(summary[k])):,}"

    unknown = read("unknown_material_detection.csv")
    unknown = unknown[
        unknown.status.eq("evaluated") & unknown.representation.eq("NEON_full")
    ]
    ug = (
        unknown.groupby(["scheme", "detector"])[
            ["unknown_recall", "known_false_rejection", "unknown_average_precision"]
        ]
        .mean()
        .reset_index()
    )
    mix = read("sensor_resolution_mixture_results.csv")
    mix = mix[mix.kind.eq("plant")]
    mg = mix.groupby(["scheme", "sensor"]).fraction_RMSE.mean().reset_index()
    amb = read("mixture_identifiability.csv")
    amb = amb[amb.scheme.eq("inferred_pft") & amb.kind.eq("plant")]
    det = read("detection_limits.csv")
    dom = read("domain_performance.csv")
    conf = part()
    siteconf = part(kind="site")
    cfg = json.loads((BASE / "manifests/learning_run.json").read_text())["identity"][
        "config"
    ]
    pages = []

    def page(
        title,
        paragraphs,
        *,
        figure=None,
        table=None,
        evidence="",
        kicker="SCIENTIFIC AUDIT",
    ):
        pages.append(
            dict(
                title=title,
                paragraphs=paragraphs,
                figure=figure,
                table=table,
                evidence=evidence,
                kicker=kicker,
            )
        )

    page(
        "Ecological signal is real. Transfer and inversion are conditional.",
        [
            "SpectralBridge spectral-library analytics report | 14 October 2026",
            "The central question is how much ecological information survives new plants, acquisitions, years, sites, spectral reduction and mixtures. The library supports conditional ecological discrimination. It does not yet establish reliable operational abundance mapping.",
            f"Across held-out plant identities, full-spectrum logistic regression achieved mean balanced accuracy of {pct(ba())} for inferred PFTs and {pct(ba('researcher'))} for researcher categories. Equal class recall, rather than majority-dominated overall accuracy, is the principal metric.",
            f"Transfer to a held-out site was much less uniform: inferred-PFT balanced accuracy ranged from {pct(site.balanced_accuracy.min())} to {pct(site.balanced_accuracy.max())}. These are the observed sites, not a confidence interval for new regions.",
            f"Biological differences mostly survive synthetic OLI: {int((e.NEON_supported & e.OLI_supported).sum())} of {int(e.NEON_supported.sum())} NEON-supported PFT contrasts remain supported. That preservation does not imply accurate fractions. Full-NEON primary synthetic PFT fraction RMSE was {num(mg[(mg.scheme == 'inferred_pft') & (mg.sensor == 'NEON')].fraction_RMSE.iloc[0])}.",
            "The decisive restrictions are domain dependence, wrong-class mixture reconstructions, weak unknown rejection, physical-material/purity gaps and absent independent abundance truth. A small residual is evidence of fit, not proof that the identified materials or fractions are correct.",
        ],
        evidence="ml_generalization.csv; biological_contrasts.csv; sensor_resolution_mixture_results.csv",
        kicker="EXECUTIVE SUMMARY · 1 OF 2",
    )
    page(
        "Five findings and the decision",
        [
            f"1. New-plant recognition is credible within the sampled population: PFT plant-fold scores span {pct(pft.balanced_accuracy.min())}–{pct(pft.balanced_accuracy.max())}. This is stronger predictive evidence than significant group contrasts alone.",
            "2. Geographic and temporal transfer depend on direction and available classes. Site and year are themselves highly predictable. Environmental, species, phenological and acquisition structure remain entangled; the experiment cannot assign a causal share to each.",
            f"3. Broad OLI responses can preserve useful information: PFT plant-held-out balanced accuracy is {pct(ba(rep='OLI'))}, versus {pct(ba(rep='NEON_k7'))} for seven training-selected narrow coordinates. The experiment changes response width and placement as well as selection; it does not isolate a pure band-number effect.",
            "4. Better classification and larger endmember libraries do not solve the inverse mixture problem. Wrong-class combinations frequently fit pure observations well, and conditional fraction errors remain substantial. Detection frequencies are not population detection limits.",
            "5. Unknowns and uncertainty are weak links. Withheld-class detectors generally accept most unknown spectra at thresholds chosen to keep known rejection low. Conformal sets can look reasonable for held-out plants and lose coverage under site shift.",
            "Decision: use the library for reproducible characterization, sampled-group comparisons and explicitly validated closed-set recognition. Treat MESMA as an experimental diagnostic. Collect independent fractional-cover/purity truth, replicated site/year acquisitions and matched real sensor observations before operational ecological abundance claims.",
            "No operational class is declared READY on the basis of a composite score. The evidence-linked matrix reports each readiness dimension separately. Deep learning is not warranted by the present sampling and validation gaps.",
        ],
        evidence="readiness_matrix.csv; unknown_material_detection.csv; uncertainty_calibration.csv",
        kicker="EXECUTIVE SUMMARY · 2 OF 2",
    )
    page(
        "1 · Why this audit follows an information ladder",
        [
            "A plot can show different curves without establishing that an unseen plant can be recognized. A classifier can recognize pure classes without determining the fractions in a mixed pixel. Each step asks a harder scientific question with its own observational unit and failure modes.",
            "Observed spectra → new individual → new acquisition → new year → new site → reduced spectral response → mixed composition → unknown material and uncertainty → defensible ecological inference.",
            "This ladder is an organizing logic, not a sequence of nested numerical percentages. Different holdouts contain different plants, years and supported classes. Their scores cannot be subtracted to estimate a causal “fraction of ecological information lost.”",
            "The original library is read in place. Earlier functional inference, sensor-transfer, real-Landsat and MESMA results are reused with their original scope. New experiments add grouped classical prediction, coordinate selection, prototypes, domain diagnostics and withheld-class challenges.",
        ],
        figure="00_validation_diagram",
        evidence="DESIGN.md; REPOSITORY_AUDIT.md; OBSERVATIONAL_STRUCTURE.md",
    )
    page(
        "2 · What is in the library?",
        [
            f"The source contains {count('pixel_rows')} pixel records and {count('identities')} globally identified polygons/plants. Compact observations produce {count('polygon_years')} polygon/year summaries. They are repeated observations, not independent new plants.",
            "The sites are NIWO, WREF and YELL. NIWO has 2020 and 2023 observations; WREF and YELL are represented in 2023. Consequently “year” and “region” are incompletely crossed. Species, source categories and inferred functional types remain distinct label systems.",
            f"The common NEON representation has {count('common_NEON_coordinates')} supported coordinates and the synthetic OLI representation has {count('OLI_channels')} channels. Atmospheric gaps are excluded rather than interpolated. Original native-grid identities and complete acquisition histories remain traceable.",
            "Finite negative corrected values are retained. The library’s absolute stored-unit interpretation remains unresolved; no division by an assumed scaling constant is introduced. The independently checked Landsat pilot has its own verified reflectance units and does not repair the library’s missing scale provenance.",
            "Missing species and unassigned PFT records are reported, not guessed or merged to improve prediction. Researcher categories are source labels, not certificates of pure vegetation, soil, dead material or shade.",
        ],
        figure="atlas",
        evidence="library_summary.csv; canonical metadata/reference index; material_unique_counts.csv",
    )
    page(
        "3 · Do ecological groups actually look different?",
        [
            "The primary functional analysis compares whole curves within matched observational-history blocks. A maximum statistic asks whether the largest standardized difference is unusual; an integrated statistic asks whether differences accumulate over supported wavelengths. Synchronized nonparametric combination joins their evidence without pretending they are independent tests.",
            f"The audited PFT family contains {len(e)} eligible contrasts: {int(e.NEON_supported.sum())} are supported with full NEON and {int((e.NEON_supported & e.OLI_supported).sum())} retain support with OLI. The researcher-category family contains {len(ec)} contrasts. Family adjustment and exact memberships are retained from the earlier audit.",
            "Repeated strong contrasts include deciduous broadleaf shrubs versus evergreen conifer trees and deciduous broadleaf trees versus evergreen conifer trees. A weak or unsupported contrast is not evidence of equivalence: limited independent support and heterogeneous groups can also reduce power.",
            "Localization is conditional on the supported contrast and matching design. Established repeated intervals include portions of NIR and SWIR. An interval showing a group effect is not automatically an optimal prediction band or an identifiable mixture endmember.",
            "Holm adjustment applies to the declared contrast families. Family excursion envelopes control wavelength searches for differences; they are not uncertainty intervals for the magnitude of every ecological effect.",
        ],
        figure="02_biological",
        evidence="biological_contrasts.csv; original pft-audit and sensor-pft-transfer manifests",
    )
    page(
        "4 · Can we recognize a new plant?",
        [
            f"All {cfg['plant_folds']} outer plant folds hold out entire GlobalIDs across years and flights. Proper training fits scaling, coordinate selection and tuning. A separate {pct(cfg['calibration_fraction'])} training-identity reserve is used for calibration where support permits; the final test plants are never used to choose parameters.",
            "Logistic regression is a regularized linear rule that learns how spectral coordinates jointly distinguish classes. PLS-DA compresses correlated predictors while fitting one-hot class responses. RBF SVM and random forest can learn nonlinear boundaries. Majority, stratified random and nearest-centroid rules provide simpler reference points.",
            f"Full-NEON mean plant-fold balanced accuracy is {pct(ba())} for PFTs and {pct(ba('researcher'))} for researcher categories. Per-class recall, precision, confusion matrices and whole-identity bootstrap intervals are available; overall accuracy alone would hide rare-class failures.",
            "The complex models did not improve the principal plant-fold comparison over logistic regression. PLS-DA was particularly weak for inferred PFTs under the fixed component grid. This result supports retaining a simple baseline, not a universal ranking of algorithms.",
            "These tests recognize new identities among the sampled class/site/species distribution. They do not withhold entire species and cannot establish recognition of novel species or continents.",
        ],
        figure="06_classical_models",
        evidence="ml_generalization.csv; class_predictive_performance.csv; paired_model_differences.csv",
    )
    page(
        "5 · What changes across acquisition, year and site?",
        [
            "A held-flight target uses its actual compact flight spectrum, not an annual median that mixes it with other acquisitions. Every identity exposed to that flight is removed from training. Site and year holdouts likewise purge each GlobalID’s entire history.",
            "Class support is a scientific gate. A class absent from training is an open-set case, not an ordinary closed-set error. Multiclass scores require multiple evaluable test classes; unsupported or single-class folds remain explicit in the support table.",
            f"For inferred PFTs, full-NEON mean balanced accuracy is {pct(ba(kind='flight'))} by acquisition, {pct(ba(kind='year'))} by year and {pct(ba(kind='site'))} by site. These are descriptive equal-fold averages, not equally representative geographic populations.",
            "Direction matters: training on 2020 and testing in 2023 can differ sharply from the reverse direction. The within-NIWO year experiment helps separate this question from the addition of other 2023 sites, but only one eligible direction supports its summary.",
            "Bootstrap intervals resample whole plants conditional on the observed site and class support. With only the observed sites, a reliable superpopulation confidence interval over regions is not available.",
        ],
        figure="03_information_ladder",
        evidence="ml_generalization.csv; fold_support.csv; paired_sensor_differences.csv",
    )
    dg = dom.groupby(["domain", "sensor"]).balanced_accuracy.mean().reset_index()
    page(
        "6 · The spectra also encode observational domains",
        [
            "We reverse the prediction question and ask whether spectra identify site, year or acquisition on unseen plant identities. Strong domain prediction indicates structured spectral differences that a biological classifier might exploit or encounter as shift.",
            "These diagnostic models use a fixed logistic setting and grouped folds. Acquisition targets use actual plant/flight observations. A repeated identity may have multiple domain labels across acquisitions; the GlobalID remains grouped through validation and uncertainty.",
            "High site/year accuracy is not proof of instrument bias. Real ecological differences, species composition, water status, phenology, illumination and processing may all contribute. Three sites and incomplete year crossing cannot disentangle them causally.",
            "The practical implication is to qualify ecological predictions by domain and to prioritize balanced repeated sampling. A very high random-plant score does not remove this concern.",
        ],
        table=data_table(
            dg,
            ["domain", "sensor", "balanced_accuracy"],
            ["Target domain", "Representation", "Mean balanced accuracy"],
        ),
        evidence="domain_performance.csv; domain memberships/predictions",
    )
    sel = read("wavelength_selection.csv")
    stable = sel[
        (sel.scheme == "inferred_pft")
        & (sel.kind == "site")
        & (sel.representation == "NEON_k20")
        & sel.selection_frequency.eq(1)
    ]
    stable_sentence = f"Coordinates selected in every observed site-training fold span {stable.wavelength_nm.min():.0f}–{stable.wavelength_nm.max():.0f} nm for the inferred-PFT twenty-coordinate ranking. This concentrated SWIR choice is correlated and does not deliver the best broad-spectrum recognition."
    page(
        "7 · Where is transferable wavelength information?",
        [
            "The primary predictive ranking is a training-only between-class/within-class F ratio. It is recomputed within every inner tuning fit and again on proper training after tuning. Its numerical F values are exploratory ranks, not confirmatory wavelength p-values.",
            "Selection frequency across outer folds, standardized logistic coefficients and PLS loading norms provide complementary views. Existing functional localization supplies a separate biological check. Correlated adjacent coordinates can exchange ranks without representing different ecological processes.",
            "The figure shows which coordinates recur when twenty are selected. Repetition across the observed site holdouts is stronger evidence of stability than one pooled importance curve; it still does not establish a universal sensor design.",
            stable_sentence,
            "The coordinate table records exact wavelengths and frequencies. Interpret repeated regions rather than attaching causal pigment/water mechanisms to a selected coordinate without an independent physiological measurement.",
        ],
        figure="05_wavelength_stability",
        evidence="wavelength_selection.csv; wavelength_coefficients.csv; original functional localization",
    )
    page(
        "8 · How much spectral resolution is enough?",
        [
            "The controlled prediction curve compares full common NEON, training-selected coordinate subsets, and the packaged synthetic OLI response. All representations use exactly the same eligible final test keys within each fold.",
            f"PFT plant-held-out mean balanced accuracy is {pct(ba())} for full NEON, {pct(ba(rep='NEON_k100'))} for one hundred selected coordinates, {pct(ba(rep='NEON_k7'))} for seven selected coordinates and {pct(ba(rep='OLI'))} for OLI.",
            "The selected-coordinate curve is not monotonic in every domain. For example, a reduced representation can regularize a site-transfer problem better than all available coordinates. This is evidence about this training rule and population, not proof that the omitted wavelengths contain no ecological information.",
            "OLI versus seven narrow coordinates changes placement, width, averaging and the supervised selection rule together. Both count and response design can matter, but this experiment cannot assign an isolated causal contribution to either. A globally optimized seven-band sensor has not been demonstrated.",
            "MicaSense remains blocked for physical sensor inference because the stored fallback/padded coordinates do not have verified source wavelength provenance. No MicaSense accuracy or sensor-transfer conclusion is manufactured.",
        ],
        figure="04_resolution_curve",
        evidence="spectral_resolution_performance.csv; paired_sensor_differences.csv; SENSOR_AUDIT predecessor",
    )
    page(
        "9 · Does one example describe a class?",
        [
            "A mean or median summarizes a class but can be a spectrum no observed plant actually had. A medoid is an observed central plant. Cluster medoids spread representatives across training clusters; diversity selection deliberately chooses distant examples.",
            "Candidates use one earliest proper-training observation per independent identity. Distances are evaluated in coordinate space standardized using proper training only. A cluster medoid here is the observed point nearest a KMeans center, not a global PAM optimum.",
            "Multiple cluster representatives often improve coverage over a single center, especially for heterogeneous researcher categories. Maximal diversity does not reliably improve classification: extreme examples can move nearest-prototype boundaries in harmful ways.",
            "Size requests beyond the available independent candidates are marked insufficient support. The rarer inferred PFTs limit the all-class size curve. There is no defensible single “number of endmembers needed” for every class/domain.",
            "The earlier class-specific accumulation and reconstruction tables distinguish which classes remain variable. More candidates can reduce reconstruction error while also providing more wrong-class mixture alternatives. Coverage and uniqueness must be evaluated together.",
        ],
        figure="07_prototype_coverage",
        evidence="prototype_performance.csv; prototype memberships; library_size.csv predecessor; library_size_recovery_summary.csv",
    )
    page(
        "10 · Can a pure class be mistaken for a mixture?",
        [
            "Mixture identifiability asks a different question from classification. Can an observation from class C be reconstructed by a nonnegative sum-to-one combination of candidates from other classes? If so, a low spectral residual cannot uniquely identify its composition.",
            "The audit compares the best own-class fit with wrong-class convex combinations under the same declared metric and tolerance. A near-alternative composition is not a second independent material truth; it is evidence that the inverse problem admits competing explanations.",
            "No PFT is certified uniquely mixture-identifiable. Some classes have lower conditional ambiguity than others, but limited rare-class support and unverified pure-material labels prevent a general uniqueness claim.",
            "Adding more representatives can improve spectral coverage and simultaneously increase ambiguity. A library can be valuable for classification yet unsuitable for unique fraction inversion. That tension is an important scientific result, not a software failure.",
        ],
        figure="10_mixture_ambiguity",
        evidence="mixture_identifiability.csv; original ambiguity and selector-sensitivity tables",
    )
    page(
        "11 · Can known fractions be recovered?",
        [
            "Synthetic mixtures combine held-out empirical parent spectra at known algebraic fractions. The training library never contains those parent identities. FCLS uses nonnegative fractions that sum to one; MESMA compares small models with varying endmembers. An exact constrained face search avoids pretending that clipped unconstrained coefficients solve the problem.",
            "These are controlled linear-mixture experiments. The fractions are known because we created them; they are not independently measured canopy, biomass, surface-cover or leaf-area fractions. Nonlinear radiative transfer, three-dimensional structure and real spatial mixing are not reproduced.",
            f"The primary EAR-MESMA full-NEON mean class/fold fraction RMSE is {num(mg[(mg.scheme == 'inferred_pft') & (mg.sensor == 'NEON')].fraction_RMSE.iloc[0])} for PFTs and {num(mg[(mg.scheme == 'researcher') & (mg.sensor == 'NEON')].fraction_RMSE.iloc[0])} for researcher categories. These substantial errors do not establish reliable operational abundance recovery.",
            "Selected-coordinate counterparts preserve the exact saved parents, fractions, folds and EAR candidate identities. Full-spectrum reconstruction is checked against the earlier saved fit before interpreting the new comparisons. Reduced-band errors are not contaminated by a fresh random parent draw.",
            "Residual error, fraction error, class-set error, runner-up composition and near-fraction ranges are separate diagnostics. A good residual alone cannot certify correct fractions.",
        ],
        figure="08_mixtures_detection",
        evidence="mixture_recovery.csv; sensor_resolution_mixture_results.csv; legacy reproduction manifests",
    )
    page(
        "12 · How much must be present to detect it?",
        [
            "Detection means the estimated class fraction exceeds a declared operating cutoff. True presence means any positive algebraic fraction. These definitions differ from the class-set metric, which uses its own fraction threshold for the true composition.",
            "The detection curves show conditional frequencies along saved parent trajectories. At zero true fraction, a positive detection is a false positive. At a small positive fraction, failure to cross the cutoff is a false negative. Both matter; showing only recall at high abundance is misleading.",
            "Population D50, D80 and D95 thresholds are marked INSUFFICIENT EVIDENCE. The repeated fraction levels share a few parent draws and cannot be treated as independent plants to fit a precise universal detection curve. No extrapolated population limit is reported.",
            "The machine table gives class-specific conditional frequencies and support for full NEON, selected coordinates and OLI. Those can guide a future independent-parent experiment, but cannot promise a particular field detection limit.",
        ],
        table=data_table(
            det[
                (det.scheme == "inferred_pft")
                & (det.sensor == "NEON")
                & det.true_fraction.isin([0, 0.2])
            ],
            ["label", "true_fraction", "conditional_detection_frequency", "N"],
            [
                "PFT",
                "True fraction",
                "Detection frequency",
                "Dependent trajectory rows",
            ],
        ),
        evidence="detection_limits.csv; original cutoff sensitivity tables",
    )
    page(
        "13 · Does the library know when it lacks the answer?",
        [
            "For each class challenge, that entire ecological class is removed from proper training and known calibration. Final test plants from the omitted class become proxy unknowns. A model trained on the remaining classes is asked to reject them, rather than simply force their assignment.",
            "We compare nearest spectral angle, nearest distance, scaled PCA radius and reconstruction residual, classifier confidence and empty raw-score conformal sets. Distance thresholds are chosen from known calibration identities alone. Unknown labels never tune them.",
            "Unknown recall is low at the resulting low known-class rejection rates. This is a strong reason not to interpret a confident closed-set class label as proof of membership. Precision and average precision also depend on the challenge prevalence; the tables retain that baseline.",
            "The omitted labels are ecological proxies. They do not exhaust water, soil, snow, mixed vegetation, shadow or new mineral materials. Earlier absent-class MESMA residual and ambiguity checks reinforce the same warning: unknown materials can lie inside the known library’s convex spectral space.",
            "A zero vector in selected coordinates has no spectral angle; the angle result is explicitly undefined while valid distance/PCA diagnostics remain available. No artificial angle is assigned.",
        ],
        figure="09_unknowns_uncertainty",
        evidence="unknown_material_detection.csv; withheld memberships/predictions; earlier unknown residual audit",
    )
    utable = ug[
        ug.detector.isin(
            [
                "nearest_angle_deg",
                "nearest_RMSE",
                "one_minus_confidence",
                "empty_conformal_set",
            ]
        )
    ]
    page(
        "14 · Are confidence and uncertainty trustworthy?",
        [
            "Temperature scaling fits a single score-scale parameter on independent training calibration identities. It can soften or sharpen probabilities but does not change the winning class. Its held-out Brier score, log loss, expected calibration error and reliability bins are evaluated rather than presumed improved.",
            "Raw PLS/SVM/centroid softmax mappings are scores, not automatically calibrated ecological probabilities. Brier score penalizes the whole probability vector; top-label ECE summarizes binwise confidence error but can conceal class-specific problems.",
            f"For PFT full-NEON logistic regression, empirical joint-identity conformal coverage ranges from {pct(conf.identity_joint_coverage.min())} to {pct(conf.identity_joint_coverage.max())} across plant folds, but from {pct(siteconf.identity_joint_coverage.min())} to {pct(siteconf.identity_joint_coverage.max())} across site folds. The nominal target is {pct(1 - cfg['conformal_alpha'])}.",
            "The conformal score is fitted without calibration labels. One maximum nonconformity per calibration identity protects the within-identity cluster definition, conditional on the required exchangeability. Ordinary split conformal does not promise coverage after geographic or temporal shift.",
            "Mixture Monte Carlo intervals describe endmember-choice stability. They are broad and under-cover their nominal target in several settings; they are not validated field abundance confidence intervals. More uncertainty replicates cannot create missing ground truth.",
        ],
        table=data_table(
            utable,
            ["scheme", "detector", "unknown_recall", "known_false_rejection"],
            ["Label scheme", "Unknown detector", "Unknown recall", "Known rejection"],
        ),
        evidence="uncertainty_calibration.csv; class_conformal_coverage.csv; mixture_uncertainty.csv; reliability.csv",
    )
    pilot = read("real_landsat_flight_metrics.csv")
    real = pilot[pilot.variant.eq("undarkened")].iloc[0]
    pilot_sentence = f"The undarkened comparison includes {int(real.N):,} matched footprints and {int(real.spatial_blocks)} spatial blocks. Pooled seven-band RMSE is {real.pooled_seven_band_RMSE:.5f} in verified reflectance units; median spectral angle is {real.median_spectral_angle_deg:.2f}°. The nominal lag is {real.delta_time_hours:.2f} hours, conditional on the legacy NEON timestamp interpretation."
    page(
        "15 · What does real Landsat add?",
        [
            "Synthetic OLI is convolution of the same NEON reference and establishes a controlled spectral-response relationship. The independent R10C pilot adds real spatial footprint aggregation, timing, atmospheric product, QA and alignment effects. These are distinct evidence layers.",
            "The pilot uses one paired NEON flightline and Landsat 8 Level-2 scene. It applies documented Landsat scaling and QA, uses true footprint overlap and spatial-block uncertainty, compares the original alignment with a limited offset diagnostic and surfaces heterogeneity dependence.",
            pilot_sentence,
            "The actual pilot numeric results and plotted data are reused from its own verified provenance. They do not measure PFT classification, fractional-cover accuracy or multi-site sensor interchangeability. Its verified reflectance units cannot be transplanted into the spectral library by assumption.",
            "Empirical real-Landsat residual perturbation of the library mixtures is therefore blocked: the library’s absolute stored-unit provenance is unresolved and transfer of one scene’s residual distribution would require additional assumptions. The earlier acquisition-variability sensitivity remains a sensitivity, not measured universal sensor noise.",
            "Good agreement in one real pair strengthens confidence that the pipeline can make a meaningful sensor comparison. It does not overcome the ecological inversion or validation gaps.",
        ],
        figure="landsat",
        evidence="REAL_LANDSAT_CONTEXT.md; provenance/real-landsat-validation/2026-10-14",
    )
    page(
        "16 · Is the library ready for MESMA?",
        [
            "Readiness is evaluated by dimension: spectral integrity, ecological distinction, plant recognition, domain transfer, endmember uniqueness, fraction recovery, unknown rejection, uncertainty calibration and operational validation. No arbitrary composite readiness score is calculated.",
            "Conditional uses include sampled-library characterization, matched group contrasts, controlled synthetic sensor-response comparisons and held-out closed-set recognition in explicitly evaluated domains.",
            "Operational fractions are NOT READY or have INSUFFICIENT EVIDENCE. The reasons are traceable: unknown library scale/purity, ecological labels that are not pure physical materials, ambiguity under convex mixtures, substantial synthetic fraction error, weak unknown rejection and absent independent abundance truth.",
            "“Green vegetation,” “Non-vegetated & dead,” woody shrubs and dead-material proxies must not be silently treated as pure endmembers for water, soil, snow, shade or species abundance. A missing physical material remains missing, even if an ecological classifier performs well.",
            "Every class × dimension decision links to the exact supporting master table and limitation. Human review should apply the intended ecological error tolerance and deployment domain before approving any narrower application.",
        ],
        evidence="readiness_matrix.csv; MATERIAL_CLASS_AUDIT.md; RECOMMENDATIONS.md",
    )
    page(
        "17 · The three most valuable new datasets",
        [
            "First: co-located, independently measured fractional cover and endmember purity. Measure actual green, senescent/dead, soil/mineral, water and shade fractions at the relevant footprint, with repeat observers or uncertainty estimates. Include small positive fractions and true absences. This directly tests inversion, false detection and interval coverage.",
            "Second: a balanced repeated site × year × species/PFT panel with persistent plant identities, native wavelength metadata, units, acquisition geometry and physiological/environmental measurements. Prioritize currently rare or geographically restricted classes. This separates ecological variability from domain structure and supports stronger transfer claims.",
            "Third: matched independent NEON, Landsat and verified drone acquisitions across sites/seasons, with tight timing, documented QA, spatial footprints and scale. This tests real sensor/domain shift rather than only convolution of one reference.",
            "Analysis priorities after collection: freeze deployment questions and error tolerances; repeat the same grouped evaluation; assess class-specific physical unknown rejection and fraction uncertainty against independent truth; only then consider more complex representations if they solve a documented failure.",
            "The current negative results change the description of SpectralBridge: it is a reproducible translation and scientific diagnostic system with demonstrated conditional ecological signal, not a universally calibrated sensor or validated ecological abundance engine.",
        ],
        evidence="RECOMMENDATIONS.md; LIMITATIONS.md; readiness_matrix.csv",
    )
    methods = [
        [
            "Scientific question",
            "Chosen method and why",
            "Alternative / reason not primary",
        ],
        [
            "Do curves differ?",
            "Blocked whole-spectrum max/integrated/NPC; retains wavelength structure and matching",
            "Energy/FPCA sensitivities retained; many separate band tests would multiply searches",
        ],
        [
            "Recognize a new plant?",
            "Regularized logistic; interpretable multivariate baseline with grouped nesting",
            "PLS-DA, RBF SVM, forest compared; deep learning does not address missing sites/truth",
        ],
        [
            "Where is information?",
            "Training-only F selection, coefficient/loading stability and functional localization",
            "No RF-importance-only or globally preselected band claims",
        ],
        [
            "Represent variable classes?",
            "Mean/median, actual medoid, cluster and diversity prototypes",
            "No single selected size optimized on outer test",
        ],
        [
            "Recover composition?",
            "Constrained FCLS / variable small-model MESMA with exact saved truth",
            "Clip-and-renormalize least squares is not equivalent; sum-one L1 penalty is constant",
        ],
        [
            "Recognize unknowns?",
            "Withheld-class challenges and known-only novelty thresholds",
            "Extra detectors cannot substitute for a physically diverse unknown set",
        ],
        [
            "Trust confidence?",
            "Separate calibration; Brier/ECE/reliability and raw-score grouped conformal sets",
            "No exchangeability guarantee across unobserved geographic shifts",
        ],
    ]
    page(
        "Methods choices · why these tests?",
        [
            "Published methods are distinguished from source-specific adaptations in LITERATURE_METHODS.md. A method’s reputation does not substitute for validation on the intended observational unit."
        ],
        table=methods,
        evidence="DESIGN.md; LITERATURE_METHODS.md; reusable experimental modules",
        kicker="TECHNICAL APPENDIX",
    )
    protocol = json.loads((BASE / "manifests/model_protocol.json").read_text())
    grids = [["Model", "Predeclared inner grid", "Fixed choices / score mapping"]]
    descriptions = {
        "logistic": "Balanced class weighting; regularized multinomial fit",
        "PLSDA": "One-hot response PLS; raw softmax scores",
        "SVM": "RBF; scale gamma; balanced; no internal probability CV",
        "forest": "100 trees; leaf minimum 5; balanced subsampling",
        "centroid": "Standardized class mean; raw distance softmax",
        "majority": "Training majority class",
        "stratified": "Seeded training-frequency random baseline",
    }
    for name, record in protocol.items():
        grids.append([name, json.dumps(record["inner_grid"]), descriptions[name]])
    page(
        "Model protocol and candidate budgets",
        [
            f"Grouped inner tuning uses up to {cfg['inner_folds']} folds; insufficient support is marked fixed/untuned. Every selector and scaler is refitted within each inner training fold. The final proper-training model is refitted after the declared choice.",
            "PLS components are capped by available feature/sample dimensions. SVM internal random-row probability fitting is disabled. Temperature calibration and conformal thresholds use separate grouped calibration, as described in DESIGN.",
            "Prototype size requests and selected-coordinate counts are fixed before final tests. The largest supported sizes differ by class; unsupported requests are not filled using repeated observations. No final-test optimization chooses a preferred size or wavelength set.",
        ],
        table=grids,
        evidence="manifests/model_protocol.json; per-fit parameter/warning/membership records; DESIGN.md",
        kicker="TECHNICAL APPENDIX",
    )
    glossary = [
        ["Term", "Plain-language meaning"],
        [
            "PFT",
            "Plant functional type inferred from recorded taxonomic names/crosswalk; separate from researcher cover category.",
        ],
        ["DBS / DBT", "Deciduous broadleaf shrubs / deciduous broadleaf trees."],
        [
            "EBS / ECS / ECT",
            "Evergreen broadleaf shrubs / evergreen conifer shrubs / evergreen conifer trees.",
        ],
        [
            "GlobalID",
            "Persistent identity used to keep the same plant out of both training and test.",
        ],
        [
            "Balanced accuracy",
            "Mean class recall, so a dominant class cannot hide rare-class failure.",
        ],
        [
            "Nested grouped validation",
            "Tune only on training folds, keeping entire plant identities together.",
        ],
        [
            "Medoid / endmember",
            "An observed representative / a component spectrum in a mixture model; neither guarantees pure material.",
        ],
        [
            "FCLS / MESMA",
            "Fractions constrained nonnegative and sum-one / comparison of small models with variable candidate spectra.",
        ],
        [
            "Identifiability",
            "Whether different compositions can explain the same observed spectrum.",
        ],
        ["Open set", "The true class is absent from the fitted library."],
        [
            "Brier / ECE",
            "Whole-vector probability error / binned top-confidence discrepancy.",
        ],
        [
            "Conformal prediction set",
            "A set of candidate labels formed using independent calibration scores; coverage needs assumptions.",
        ],
        [
            "Conditional synthetic detection",
            "Performance for saved algebraic mixtures, not a population field detection guarantee.",
        ],
    ]
    page(
        "Methods glossary",
        [
            "Labels, targets and uncertainty units should be read together. A plant-held-out accuracy, a blocked group-effect p-value and a synthetic fraction RMSE answer different questions."
        ],
        table=glossary,
        evidence="Methods implementation and master-table schemas",
        kicker="TECHNICAL APPENDIX",
    )
    page(
        "Reproducibility and statistical scope",
        [
            f"Fixed seed {cfg['seed']}; whole-identity bootstrap draws {cfg['bootstraps']}; minimum training/test identities per class {cfg['minimum_train']}/{cfg['minimum_test']}; independent calibration reserve {pct(cfg['calibration_fraction'])}. Unsupported branches are explicit rather than forced.",
            "Proper-training preprocessing and grouped inner tuning precede final evaluation. Models, selected wavelengths, memberships, calibration status, exact source hash, configuration, versions and output hashes are retained. Completed fold checkpoints are verified and reused; changed evidence is rejected.",
            "Paired sensor/model differences resample the same identity clusters with the same draws. They condition on observed folds/classes. They are descriptive conditional intervals, not a new family of multiple-testing-adjusted superiority claims. Existing biological Holm-adjusted families are reused unchanged.",
            "Synthetic mixture parents and fraction trajectories are dependent. Repeated rows at many fractions do not supply independent abundance-validation samples. Site averages are descriptive because the observed sites do not support a geographic superpopulation claim.",
            "Report figures read tidy master tables. Editable JSON/Markdown narrative, the builder, source/result checksums and a section-level report manifest allow every major claim to be traced. Trusted local joblib files are loaded only after checksum verification.",
        ],
        evidence="manifests/learning_run.json; full_learning_validation.json; report_manifest.json; VALIDATION.md",
        kicker="TECHNICAL APPENDIX",
    )
    site_table = part(kind="site")[
        [
            "fold",
            "test_identities",
            "balanced_accuracy",
            "BA_lo",
            "BA_hi",
            "identity_joint_coverage",
        ]
    ]
    page(
        "Detailed geographic evidence · inferred PFTs",
        [
            "Each row is one complete held-site target, using only eligible supported classes. Balanced-accuracy intervals are whole-identity conditional bootstrap intervals. Coverage is empirical joint-identity raw-score conformal coverage, not a guarantee.",
            "A high score in one direction cannot cancel a weak score in another. Examine class support and class-specific recall before applying the library to a particular region or functional group.",
        ],
        table=data_table(
            site_table,
            list(site_table),
            [
                "Held site",
                "Test identities",
                "BA",
                "BA lower",
                "BA upper",
                "Joint coverage",
            ],
        ),
        evidence="ml_generalization.csv; class_predictive_performance.csv; fold_support.csv",
        kicker="TECHNICAL APPENDIX",
    )
    page(
        "Unknown challenge · full-spectrum diagnostic detail",
        [
            "Rows average omitted-class × plant-fold challenges equally. Thresholds use known calibration only. Average precision is compared with each challenge’s retained unknown prevalence in the machine table; an average AP alone is not a prevalence-free deployment guarantee.",
            "Low known rejection and low unknown recall mean that the method is conservative about rejecting familiar observations but accepts many missing classes. This is not reliable open-world membership validation.",
        ],
        table=data_table(
            ug,
            [
                "scheme",
                "detector",
                "unknown_recall",
                "known_false_rejection",
                "unknown_average_precision",
            ],
            [
                "Scheme",
                "Detector",
                "Unknown recall",
                "Known rejection",
                "Average precision",
            ],
        ),
        evidence="unknown_material_detection.csv",
        kicker="TECHNICAL APPENDIX",
    )
    page(
        "Limitations that bound every conclusion",
        [
            "Independence: source pixels, repeat flights, repeat years and mixture fraction trajectories are not independent plants. GlobalID grouping addresses known identities but cannot remove all spatial, species or exposure dependence.",
            "Observational design: few sites, incomplete year crossing, uneven class support and species/domain aliasing limit ecological attribution and external validity. No causal plant-trait mechanism or novel-species recognition is established.",
            "Spectral/physical validity: absolute library units, source purity and physical-material coverage remain incomplete; MicaSense coordinates are unverified. Atmospheric gaps are never bridged. Finite negative corrected values are not automatically nodata.",
            "Predictive scope: thresholds and grids are predeclared and training-confined, but the experiment is still a source-specific benchmark. Conditional confidence intervals do not represent unobserved geographic populations.",
            "Inverse problems: empirical endmembers vary; linear synthetic mixtures omit real radiative transfer, spatial adjacency and canopy structure. Spectral fit cannot establish correct abundance, and no independent fraction truth validates operational MESMA.",
            "Sensor evidence: synthetic OLI is derived from NEON. One real pair adds important radiometric/spatial context but does not validate regional PFT classification or abundance. Poor unknown rejection and shifted uncertainty coverage remain visible, not averaged away.",
        ],
        evidence="LIMITATIONS.md; all stage and readiness evidence",
        kicker="TECHNICAL APPENDIX",
    )
    refs = [
        "Roberts et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography. https://doi.org/10.1111/ecog.02881",
        "Cawley & Talbot (2010). On over-fitting in model selection and subsequent selection bias. JMLR. https://www.jmlr.org/beta/papers/v11/cawley10a.html",
        "Bioucas-Dias et al. (2012). Hyperspectral unmixing overview. https://doi.org/10.1109/JSTARS.2012.2194696",
        "Roth, Dennison & Roberts (2012). Comparing endmember selection and vegetation classification. https://doi.org/10.1016/j.rse.2012.08.030",
        "Guo et al. (2017). On Calibration of Modern Neural Networks. Temperature scaling adapted and evaluated here for classical scores. https://proceedings.mlr.press/v70/guo17a.html",
        "Angelopoulos & Bates (2021). A Gentle Introduction to Conformal Prediction. https://arxiv.org/abs/2107.07511",
        "Scheirer et al. (2013). Toward Open Set Recognition. https://doi.org/10.1109/TPAMI.2012.256",
        "Implementation contracts and prior MESMA definitions: LITERATURE_METHODS.md and provenance/mesma-readiness/2026-10-14/LITERATURE_METHODS.md. Official scikit-learn contracts are linked there.",
    ]
    page(
        "Primary literature and implementation provenance",
        refs,
        evidence="LITERATURE_METHODS.md; original audited references",
        kicker="REFERENCES",
    )
    return dict(
        title="SpectralBridge spectral-library analytics",
        date="2026-10-14",
        pages=pages,
    )


def render(source):
    font = "/System/Library/Fonts/Supplemental/"
    pdfmetrics.registerFont(TTFont("ArialAudit", font + "Arial.ttf"))
    pdfmetrics.registerFont(TTFont("ArialAuditBold", font + "Arial Bold.ttf"))
    pdfmetrics.registerFontFamily(
        "ArialAudit",
        normal="ArialAudit",
        bold="ArialAuditBold",
        italic="ArialAudit",
        boldItalic="ArialAuditBold",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="AuditTitle",
            fontName="ArialAuditBold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#173e52"),
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AuditBody",
            fontName="ArialAudit",
            fontSize=10.2,
            leading=15,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AuditSmall",
            fontName="ArialAudit",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#4b5c66"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AuditTable", fontName="ArialAudit", fontSize=8, leading=10.5
        )
    )
    styles.add(
        ParagraphStyle(
            name="AuditKicker",
            fontName="ArialAuditBold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#a45c3d"),
            spaceAfter=8,
        )
    )
    story = []
    figure_manifest = json.loads((BASE / "manifests/figures.json").read_text())[
        "figures"
    ]
    flookup = {x["name"]: x for x in figure_manifest}
    assets = {
        "atlas": BASE / "figures/01_readable_atlas.png",
        "02_biological": REPO
        / "provenance/sensor-pft-transfer/2026-10-14/figures/C_strong_exemplar_contrasts.png",
        "landsat": REPO / "docs/images/spectral-library/real-landsat-pilot.png",
    }
    for pi, page in enumerate(source["pages"]):
        if pi:
            story.append(PageBreak())
        story.extend(
            [
                Paragraph(escape(page["kicker"]), styles["AuditKicker"]),
                Paragraph(escape(page["title"]), styles["AuditTitle"]),
            ]
        )
        for para in page["paragraphs"]:
            story.append(Paragraph(escape(para), styles["AuditBody"]))
        if page.get("figure"):
            name = page["figure"]
            path = assets.get(name, BASE / "figures" / f"{name}.png")
            if not path.exists():
                raise FileNotFoundError(path)
            from PIL import Image as PILImage

            with PILImage.open(path) as im:
                w, h = im.size
            width = 480
            height = width * h / w
            if height > 230:
                width *= 230 / height
                height = 230
            story.append(Spacer(1, 5))
            story.append(Image(str(path), width, height))
            cap = (
                flookup[name]["caption"]
                if name in flookup
                else "Reused canonical figure; see the source evidence and original figure manifest for exact data and scope."
            )
            story.append(Paragraph(escape(cap), styles["AuditSmall"]))
        if page.get("table"):
            rows = [
                [
                    Paragraph(escape(str(v)).replace("_", " "), styles["AuditTable"])
                    for v in row
                ]
                for row in page["table"]
            ]
            widths = [480 / len(rows[0])] * len(rows[0])
            if len(rows[0]) == 2:
                widths = [125, 355]
            if len(rows[0]) == 3:
                widths = [110, 185, 185]
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4eef1")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#f4f6f5")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#77949f")),
                    ]
                )
            )
            story.append(table)
        story.append(Spacer(1, 10))
        story.append(
            Paragraph("Evidence: " + escape(page["evidence"]), styles["AuditSmall"])
        )
    DEST.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(DEST),
        pagesize=(612, 792),
        leftMargin=66,
        rightMargin=66,
        topMargin=49,
        bottomMargin=47,
        title=source["title"],
        author="SpectralBridge scientific analytics audit",
    )

    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#cbd6d9"))
        canvas.line(66, 37, 546, 37)
        canvas.setFont("ArialAudit", 7.5)
        canvas.setFillColor(colors.HexColor("#50636d"))
        canvas.drawString(
            66,
            25,
            "SPECTRALBRIDGE  |  CONDITIONAL EVIDENCE, EXPLICIT LIMITS  |  14 OCT 2026",
        )
        canvas.drawRightString(546, 25, str(doc.page))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return DEST


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", type=Path)
    args = parser.parse_args()
    source = (
        json.loads(args.source_json.read_text()) if args.source_json else make_source()
    )
    (BASE / "report_source.json").write_text(
        json.dumps(source, indent=2, ensure_ascii=False) + "\n"
    )
    md = []
    for page in source["pages"]:
        md.extend(
            [
                "# " + page["title"],
                "",
                *sum(([p, ""] for p in page["paragraphs"]), []),
                "Evidence: " + page["evidence"],
                "",
            ]
        )
    (BASE / "report_source.md").write_text("\n".join(md))
    path = render(source)
    pages = PdfReader(path).pages
    text = "\n".join(p.extract_text() for p in pages)
    (BASE / "manifests/pdf_validation.json").write_text(
        json.dumps(
            dict(
                pages=len(pages),
                text_characters=len(text),
                pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                all_pages_have_text=all(len(p.extract_text()) > 150 for p in pages),
            ),
            indent=2,
        )
        + "\n"
    )
    manifest = dict(
        pdf=str(path.relative_to(REPO)),
        pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        builder=str(Path(__file__).relative_to(REPO)),
        sections=[
            dict(title=p["title"], figure=p.get("figure"), evidence=p["evidence"])
            for p in source["pages"]
        ],
        table_hashes={
            str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((BASE / "tables").glob("*.csv"))
        },
    )
    manifest["figure_definitions"] = json.loads(
        (BASE / "manifests/figures.json").read_text()
    )["figures"]
    manifest["editable_source"] = str(BASE.relative_to(REPO) / "report_source.json")
    manifest["original_source"] = dict(
        path="Aug_2026_all_polygons_merged_pixel_extraction.parquet",
        sha256="cd3a8afd2697f09d1f4749f92df8a5e2cc71ee12490d38de12f21f90b2a75978",
    )
    manifest["analysis_model_index"] = str(
        BASE.relative_to(REPO) / "models/model_index.csv"
    )
    for section in manifest["sections"]:
        section["result_files"] = [
            str(p.relative_to(REPO))
            for p in sorted((BASE / "tables").glob("*.csv"))
            if p.name in section["evidence"]
        ]
        name = section.get("figure")
        if name == "02_biological":
            section["figure_files"] = [
                "provenance/sensor-pft-transfer/2026-10-14/figures/C_strong_exemplar_contrasts.png"
            ]
        elif name == "landsat":
            section["figure_files"] = [
                "docs/images/spectral-library/real-landsat-pilot.png"
            ]
        elif name:
            actual = "01_readable_atlas" if name == "atlas" else name
            section["figure_files"] = [
                str(BASE.relative_to(REPO) / "figures" / f"{actual}.{ext}")
                for ext in ["png", "pdf", "svg"]
            ]
        section["analysis_scripts"] = [
            "examples/spectral_library_analytics.py",
            "examples/spectral_library_analytics_results.py",
            str(Path(__file__).relative_to(REPO)),
        ]
    (BASE / "manifests/report_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(path, len(pages), "pages")


if __name__ == "__main__":
    main()
