"""Render the evidence-backed review; uses the bundled ReportLab/PDF runtime."""

from pathlib import Path
from pypdf import PdfReader, PdfWriter
import json
import html
import math
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    PageBreak,
    NextPageTemplate,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from PIL import Image as PILImage

ROOT = Path.cwd()
REPORT_DIR = ROOT / "output/pdf/plant_spectral_review"
D = json.loads((REPORT_DIR / "report_evidence.json").read_text())
F = REPORT_DIR / "figures"
PDF = REPORT_DIR / "spectral_plots_methods_robustness_report.pdf"
NAVY = colors.HexColor("#163746")
TEAL = colors.HexColor("#326b78")
GOLD = colors.HexColor("#ae7632")
LIGHT = colors.HexColor("#eef3f5")
INK = colors.HexColor("#23323a")
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=10.1,
        leading=14.4,
        textColor=INK,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="H1",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=NAVY,
        spaceAfter=16,
    )
)
styles.add(
    ParagraphStyle(
        name="H2r",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=TEAL,
        spaceBefore=9,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="CaptionR",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.3,
        textColor=colors.HexColor("#52636b"),
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="CellR", fontName="Helvetica", fontSize=8.3, leading=11, textColor=INK
    )
)
styles.add(
    ParagraphStyle(
        name="SmallR",
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=INK,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverR",
        fontName="Helvetica-Bold",
        fontSize=33,
        leading=38,
        textColor=NAVY,
        spaceAfter=24,
    )
)
styles.add(
    ParagraphStyle(
        name="LeadR",
        fontName="Helvetica",
        fontSize=14,
        leading=20,
        textColor=TEAL,
        spaceAfter=17,
    )
)
S = []
mode = "portrait"
width = A4[0] - 92


def p(text, style="Body"):
    S.append(Paragraph(text, styles[style]))


def subhead(text):
    p(text, "H2r")


def note(text):
    t = Table([[Paragraph(text, styles["Body"])]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d7dc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    S.append(t)
    S.append(Spacer(1, 12))


def table(headers, rows, weights=None):
    weights = weights or [1] * len(headers)
    col = [width * x / sum(weights) for x in weights]
    data = [
        [
            Paragraph("<b>" + html.escape(str(c)) + "</b>", styles["CellR"])
            for c in headers
        ]
    ] + [[Paragraph(str(c), styles["CellR"]) for c in row] for row in rows]
    t = Table(data, colWidths=col, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, TEAL),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#d7dfe3")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    S.append(t)
    S.append(Spacer(1, 10))


def pic(name, maxheight=290, caption=None):
    path = F / name
    with PILImage.open(path) as im:
        w, h = im.size
    scale = min(width / w, maxheight / h)
    S.append(Image(str(path), width=w * scale, height=h * scale, hAlign="CENTER"))
    if caption:
        p(caption, "CaptionR")


def page(title, wide=False):
    global mode, width
    mode = "landscape" if wide else "portrait"
    width = (landscape(A4) if wide else A4)[0] - 92
    if S:
        S.extend([NextPageTemplate(mode), PageBreak()])
    p(title, "H1")


def pct(x):
    return f"{100 * x:.1f}%"


def rows(stage=None, scope=None):
    return [
        r
        for r in D["matching"]
        if (stage is None or r["stage"] == stage)
        and (scope is None or r["scope"] == scope)
    ]


def baseline(level, scope, stage):
    return next(
        r
        for r in D["baselines"]
        if r["level"] == level and r["scope"] == scope and r["stage"] == stage
    )


def interval(scope, stage):
    return next(
        r
        for r in D["accuracy_intervals"]
        if r["scope"] == scope and r["stage"] == stage
    )


def evidence(text):
    p("Evidence: " + text, "CaptionR")


page("")
S.pop()
S.append(Spacer(1, 40))
p("Spectral signatures<br/>across plants,<br/>sensors, sites and years", "CoverR")
p("Methods, findings and scientific robustness", "LeadR")
p("SpectralBridge | Analysis review | 13 October 2026", "Body")
note(
    "<b>Primary assessment.</b> The library is a useful, source-traceable descriptive resource. Its plots reveal spectral variation and make stratification possible. The present boosted quantile signatures have weak identification performance and unreliable extreme tails. They should be treated as exploratory models, not validated species identifiers or calibrated uncertainty envelopes."
)
table(
    ["Evidence base", "Current scope"],
    [
        [
            "Independent labeled plants",
            "2,496 GlobalIDs; 1,886 in the pooled main-species cohort",
        ],
        ["Sites / acquisition years", "NIWO, WREF, YELL / 2020 and 2023"],
        [
            "Fitted signatures",
            "7,960 all-year signatures plus 164 year/site species signatures",
        ],
        [
            "Reviewed artifacts",
            "46 original PDF artifacts, totaling 421 pages, including aliases and individual-plant reports",
        ],
    ],
    [1.1, 2.4],
)
p(
    "This report synthesizes every plot family, embeds readable examples and supplies a complete original-figure inventory. It does not reproduce all 421 source pages. New calculations are descriptive audit summaries and conditional accuracy intervals; no models or source observations were changed.",
    "CaptionR",
)
p(
    "Prepared with OpenAI Codex from the saved local analysis. This is a computational review, not independent field validation or peer review.",
    "CaptionR",
)

page("How to use this report")
p(
    "Start with the evidence assessment below, then use the empirical plots to understand the data and the validation tables to judge predictive claims. The figure pages are deliberately wider than the text pages so labels and individual traces remain readable."
)
table(
    ["Question", "Where to look"],
    [
        [
            "What are the observations and independent samples?",
            "Data and aggregation; wavelength support",
        ],
        [
            "What do the original traces show?",
            "Empirical spectra; raw/corrected comparison; regional views",
        ],
        [
            "What do the 99 lines mean?",
            "Boosted models; species and individual examples; tail diagnostics",
        ],
        [
            "Can an unknown plant be identified?",
            "Holdout design; pooled and site matching; full performance tables",
        ],
        [
            "Are site/year differences trustworthy?",
            "Year/site design; NIWO temporal and 2023 spatial examples",
        ],
        [
            "Where are all the original plots?",
            "Complete artifact inventory and source ledger",
        ],
    ],
    [1.4, 2],
)
subhead("Evidence assessment")
table(
    ["Use", "Assessment", "Reason"],
    [
        [
            "Describe spectra in this archive",
            "Supported, with stated cohort limits",
            "Native units, equal-plant summaries, traceable source records",
        ],
        [
            "Compare observed sites/years descriptively",
            "Supported with qualification",
            "Different species, plants, flights and dates contribute",
        ],
        [
            "Interpret fitted 1%/99% curves as calibrated limits",
            "Not supported",
            "Tail underfitting; few independent observations",
        ],
        [
            "Identify unknown species reliably",
            "Not established",
            "Held-out accuracy is weak and often no better than baselines",
        ],
        [
            "Infer true satellite/drone calibration",
            "Not supported",
            "OLI/MicaSense are derived NEON products; MicaSense labels unverified",
        ],
        [
            "Claim year-driven biological change",
            "Not supported by these panels",
            "Unpaired cohorts and acquisition effects remain confounded",
        ],
    ],
    [1.15, 1, 1.8],
)
evidence(
    "Saved audits [L1-L6], matching evidence [L7-L8], source code [L9]. The ratings are this report's interpretation, not package approval thresholds."
)

page("1. Data, identities and the sampling unit")
a = D["audit"]
p(
    "The supplied merged polygon-extraction Parquet contains <b>85,706 pixel rows</b>, of which <b>45,880 are labeled</b>. Its records cover 122 flight/source pairs and three native hyperspectral grids. The original file was read in place; it was not copied for convenience or edited during analysis."
)
table(
    ["Level", "Count", "Meaning"],
    [
        [
            "Labeled pixels",
            "45,880",
            "Spatial samples inside polygon/flight observations",
        ],
        [
            "Plant-flight/polygon observations",
            "8,845",
            "Pixel-median spectra, grouped by GlobalID, flight, source image and polygon",
        ],
        [
            "Independent labeled plants",
            "2,496",
            "Unique GlobalIDs; repeated flights are not new plants",
        ],
        [
            "Pooled main cohort",
            "1,886 plants / 22 species",
            "At least 10 plants per eligible species; Other, Unidentified and genus-only labels excluded",
        ],
        [
            "Regional eligible union",
            "21 species",
            "At least 10 plants in a species/site cell",
        ],
        [
            "Year/site eligible cohorts",
            "41 species-year-site cells",
            "At least 10 plants within that year and site",
        ],
    ],
    [1.3, 1, 2.2],
)
subhead("Why pixels, observations and plants must stay separate")
p(
    "A large polygon can contribute more pixels without contributing more independent plants. The analysis first takes the pixel median within each polygon/flight/source observation. It then takes an equal-observation median for each GlobalID. Species summaries give each plant equal weight. This prevents polygon area or repeated pixel sampling from dominating the nominal sample size."
)
p(
    "This aggregation is a defensible design choice, not proof that all observational dependence disappears. Plants can share a flight, site, illumination, processing history or sampling strategy. These dependencies matter when interpreting uncertainty and transferability. The displayed sample size is a count of identities, not an estimate of an effective independent environmental sample size."
)
evidence(
    "[L1-L3]. Species labels and GlobalIDs are inherited from the supplied library; no independent field-label audit was performed."
)

page("2. Wavelength support and stored values")
p(
    "The original merged corrected table has 1,140 wavelength columns because three native 426-band grids are represented in a union schema. Every inspected pixel has 426 finite native samples. The merged finite fraction is <b>37.3684%</b> (426 / 1,140), a schema-coverage statistic. It is not a fraction of reflectance retained, a model accuracy, or evidence that 62.6% of the original bands were lost."
)
table(
    ["Contract", "Implementation / consequence"],
    [
        ["Common NEON grid", "385-2,510 nm at 5 nm intervals: 426 target positions"],
        [
            "Supported analysis positions",
            "360 positions outside excluded/unsupported spans; 100% finite within supported positions in the audited harmonized output",
        ],
        ["Excluded atmospheric spans", "1,340-1,450 and 1,790-2,000 nm"],
        [
            "Interpolation",
            "Only adjacent supported native points separated by at most 8 nm; no gap bridging or extrapolation",
        ],
        [
            "Units",
            "Native stored spectral values; no scaling, clipping, normalization or conversion to a 0-1 reflectance claim",
        ],
        [
            "Negative values",
            "Finite negative values are not automatically nodata; plotting/analysis retain them when present",
        ],
    ],
    [1, 2.4],
)
subhead("How to read an empty or broken trace")
p(
    "Gaps across excluded wavelengths are deliberate. They should not be interpreted as species absorption features or failed curve fitting. Apparent line continuity in the sparse-band products is only a plotting connection between supplied coordinates. It does not add measured samples between bands."
)
subhead("What the support audit establishes")
p(
    "The coverage and validation artifacts support consistency of the supplied grids and the harmonization procedure. They do not establish radiometric accuracy, correct physical units, instrument calibration, or physical band identity for MicaSense. Those require independent metadata or observations."
)
evidence(
    "[L1-L3], wavelength_coverage and common_coverage outputs; exact filenames appear in the inventory."
)

page("Wavelength coverage: visual evidence")
coverage = ROOT / "artifacts/plant_spectral_atlas/wavelength_coverage.png"
with PILImage.open(coverage) as image:
    image_width, image_height = image.size
S.append(Image(str(coverage), width=width, height=width * image_height / image_width))
p(
    "Coverage exhibit. Original wavelength-coverage plot from the audited atlas. The union schema, native-grid sampling and analysis mask describe different kinds of missingness; they should not be collapsed into one percentage.",
    "CaptionR",
)
subhead("A schema fraction is not an accuracy score")
p(
    "The 37.3684% merged finite fraction arises from 426 native samples occupying a union of 1,140 wavelength columns. The harmonized grid uses a different denominator: 360 supported positions out of 426 target positions, after the stated exclusions. Both figures can be correct without any loss of the original 426 finite native measurements per pixel."
)
p(
    "The figure is an input/support diagnostic. It does not evaluate spectral calibration, correct species labels, the physical validity of an individual band, or quantile-model fit quality. In particular, complete numerical MicaSense data can coexist with incorrect or unverified wavelength labels."
)
evidence(
    "[L1-L2], original wavelength_coverage.png/PDF and common_coverage.csv. No source data or plot values changed."
)

page("3. Empirical plant spectra", True)
p(
    "These selected examples reproduce the original descriptive trace semantics: faint lines are independent plant summaries; the strong trace is the species median. For NEON, the shaded band is the empirical interquartile range. For sparse sensors, IQR bars occur only at the supplied band positions. Examples illustrate reading the plots; they were not selected by a statistical separation criterion."
)
pic(
    "empirical_examples.png",
    maxheight=305,
    caption="Figure 1. All-year empirical examples from the pooled cohort. Each GlobalID contributes once. Derived OLI and MicaSense are shown separately here for clarity; some earlier overview files retain the historical combined darkened column. MicaSense physical coordinates remain unverified.",
)
p(
    "Read differences in broad level, shape and spread together. Similar medians can coexist with extensive overlap among individual plants. A visually distinct row does not establish separability from all other species, and a low-opacity dense patch is not a normalized probability density. Full species and supplementary atlases retain the remaining labels and original counts.",
    "CaptionR",
)
evidence(
    "[L1-L3]. Re-rendered from verified compact plant tables using the existing plotting helper; no analytical values changed."
)

page("4. Raw versus corrected: what changed?")
c = D["correction"]
p(
    "The raw/corrected layouts keep the same plant identities aligned. This makes correction-related shifts visible without changing species order or sample size. The comparison is descriptive: the correction algorithm was already applied upstream, and the plotting workflow did not alter its coefficients or assumptions."
)
table(
    ["Paired diagnostic, pooled main cohort", "Observed value"],
    [
        ["Plants compared", f"{c['plants']:,}"],
        ["Finite plant-by-band pairs", f"{c['finite_pairs']:,}"],
        [
            "Median absolute difference",
            f"{c['median_absolute_change']:.2f} stored units",
        ],
        ["Mean absolute difference", f"{c['mean_absolute_change']:.2f} stored units"],
        [
            "Largest absolute paired difference",
            f"{c['max_absolute_change']:.2f} stored units",
        ],
        ["Fraction of finite pairs differing", pct(c["changed_fraction"])],
    ],
    [1.7, 1],
)
pic(
    "correction_histogram.png",
    maxheight=185,
    caption="Figure 2. Distribution of each selected plant's median absolute correction over supported bands. This is an audit of change, not a measure of correction accuracy. Band pairs remain correlated and are not independent replicates.",
)
p(
    "Neither a larger nor a smaller raw/corrected shift proves a better physical result. There is no independent reference spectrum here against which correction accuracy was assessed. In the saved identification experiment, corrected NEON also did not consistently improve accuracy over raw NEON. That is a limitation of this matching exercise, not a general verdict on BRDF/topographic correction."
)
evidence(
    "[L2], paired compact raw/corrected tables; new descriptive calculation in report_evidence.json. Values refer to the 1,886-plant cohort, not every labeled plant."
)

page("5. Regional views and uneven representation")
p(
    "Site codes were read from the source extraction-table basename and cross-checked against flight IDs and populated aop_site metadata. No GlobalID spans multiple sites in the audited mapping. Ecological region names are inherited metadata, not independent ecological classifications generated by this report."
)
table(
    [
        "Site",
        "Metadata region",
        "Labeled plants",
        "Eligible species",
        "Plants in eligible cells",
    ],
    [
        [
            r["region"],
            r["ecoregion"],
            r["matched_labelled_plants"],
            r["eligible_species"],
            r["main_plants"],
        ]
        for r in D["regional"]["regions"]
    ],
    [0.55, 1.2, 0.8, 0.8, 1],
)
subhead("What the regional plots tell us")
p(
    "The separate site atlases and direct corrected-by-region panel show which species/site cohorts are present, their plant counts, and how within-archive distributions differ. They also show that regional representation is uneven. Pooling can weight a species toward the site with more plants or more characteristic acquisition conditions, even though each individual plant is weighted equally."
)
subhead("What they do not tell us")
p(
    "Regional differences do not isolate climate, geography, phenology or sensor-processing causes. Species composition, site conditions, acquisition dates and sampling may all change together. Species absent from a fitted panel can be absent from the library, represented below the threshold, or excluded by the label policy. These alternatives are distinguished in sample-size tables and unavailable-cell annotations, rather than silently treated as zero reflectance."
)
p(
    "The regional union has 21 eligible species while the pooled main panel has 22. A globally eligible species can fail every site-level threshold. This cohort change is a selection rule, not a lost identity or an error in the plant matching."
)
evidence(
    "[L3], matched_plant_regions and regional species counts. No leave-one-site-out classifier evaluation was performed for these plot-derived signatures."
)

page("6. Derived Landsat and MicaSense products")
p(
    "The Landsat OLI-like and MicaSense-like products are derived from the NEON spectra in this library. They are not independently observed satellite and drone acquisitions. A relationship among them is therefore a within-reference diagnostic, not an empirical demonstration that real sensors are interchangeable."
)
table(
    ["Product", "Supplied samples", "Interpretation"],
    [
        [
            "NEON raw / corrected",
            "426 target positions; 360 supported",
            "Dense supported spectral traces, with explicit gaps",
        ],
        [
            "Derived Landsat OLI",
            "7 supplied coordinates",
            "Sparse-band signal derived from the reference; connections are guides",
        ],
        [
            "Derived MicaSense",
            "10 supplied export coordinates",
            "Physical wavelength labeling unverified; archive-order comparisons only",
        ],
    ],
    [1, 1.1, 1.9],
)
subhead("The MicaSense coordinate issue is consequential")
p(
    "The exported labels are <b>475, 560, 668, 717, 840, 841, 842, 843, 844, 845 nm</b>. This sequence matches the legacy five-band fallback followed by one-nanometer padding. It disagrees with the packaged ten-band grid: 444, 475, 531, 560, 650, 668, 705, 717, 740, 842 nm. This is evidence of a metadata problem requiring source-header verification; it is not enough evidence to assign replacement wavelengths by order."
)
p(
    "The values, ordering and labels were left unchanged. Current sensor plots flag the uncertainty. The matching API rejects physical-wavelength MicaSense queries by default; an explicit override only permits comparison on the same archive labels. It does not verify physical wavelengths. Until headers resolve the issue, do not interpret the apparent MicaSense red-edge position or a rise near 845 nm as a physical feature."
)
note(
    "Separating the sensors into their own graphs improves visibility. It does not repair band metadata, add spectral resolution, or provide independent calibration evidence."
)
evidence(
    "[L2, L4, L9], packaged landsat_band_parameters.json and legacy SENSOR_WAVELENGTHS_NM/export padding paths. Coordinate diagnosis is an inference from the exact label pattern; original source headers have not been inspected."
)

page("7. What a boosted quantile curve represents")
p(
    "At each wavelength, the model predicts a chosen percentile of the supplied spectral values. Wavelength is the predictor; stored spectral value is the response. For a species model, the training observations are independent plant medians. For an individual model, they are that plant's repeated-flight/polygon median spectra. These are different distributions and should not be described as interchangeable uncertainty estimates."
)
table(
    ["Model choice", "Recorded setting"],
    [
        ["Quantiles", "0.01, 0.02, ..., 0.99: 99 fitted levels"],
        ["Backend / objective", "XGBoost 3.4.1; reg:quantileerror; histogram trees"],
        [
            "Tree fitting",
            "80 boosting rounds; learning rate 0.1; maximum depth 5; max_bin 256; seed 0",
        ],
        [
            "Weighting",
            "Equal total weight per supplied plant/observation within each supported segment",
        ],
        [
            "Missing support",
            "NEON fitted in supported contiguous segments; no prediction into excluded gaps",
        ],
        [
            "Curve ordering",
            "Raw predictions retained; pointwise sorting across quantiles produces ordered curves for figures/scoring",
        ],
    ],
    [1, 2.4],
)
p(
    "The quantile objective is pinball loss [W1-W2]. Tree boosting can fit nonlinear wavelength dependence, but its flexibility does not guarantee adequate shape recovery at all percentile levels. A smooth or intricate line is a fitted representation, not an additional observed plant. Pointwise percentile curves also need not form physically observed whole-spectrum trajectories: different plants can occupy the same percentile at different wavelengths."
)
p(
    "There is no fitted 100th-percentile model in this analysis. The user-selected range was 1-99%. The 10 by 10 display has 100 slots in descending order, with the 100% slot explicitly unfitted. It is not filled with a maximum, duplicated 99th percentile, or extrapolated endpoint."
)
evidence(
    "[L4, L9], XGBoost objective documentation [W1], pinball scoring documentation [W2]."
)

page("8. Species quantile fans: useful shape, limited tails", True)
pic(
    "species_quantile_examples.png",
    maxheight=348,
    caption="Figure 3. Three selected pooled species, showing the same 99 fitted levels in raw, corrected, Landsat and MicaSense columns. Strong curves are fitted medians; dotted curves are empirical medians. MicaSense physical coordinates are unverified.",
)
p(
    "The 52 full-data species/scope groups comprise 22 pooled groups plus 12 NIWO, 10 WREF and 8 YELL groups. Across four stages these yield 208 full-data signatures. Another 208 species signatures are fit separately on training-only plants for holdout evaluation. Full-data figure fits are not the fits used to score held-out species.",
    "CaptionR",
)
p(
    "A narrow fan can arise from a narrow observed cohort, model underfit, or few independent plants. A wide fan can represent real observed spread or poor tail fitting. Neither fan width nor lack of crossing alone demonstrates calibrated coverage. Pointwise rearrangement enforces ordering, not statistical validity. The all-year run records zero crossing models; that does not rule out substantial tail error.",
    "CaptionR",
)
evidence(
    "[L4, L7, L9]. Full-data models retain both raw and ordered arrays and empirical medians in per-model checkpoints."
)

page("9. Individual-plant quantile fans", True)
pic(
    "individual_examples.png",
    maxheight=345,
    caption="Figure 4. Deterministic NIWO examples selected by alphabetical species and GlobalID. Each row is one real plant; its repeated observations train its quantile family. It is not 99 independent plants.",
)
p(
    "The main cohort contains 1,886 individual GlobalIDs, each represented in four stages: 7,544 individual signatures. The full individual reports cover every modeled plant once: NIWO 964 plants / 193 pages; WREF 553 / 111; YELL 369 / 74. These counts differ from regional species-eligible counts because the individual reports use globally eligible species, including site/species combinations below the regional threshold.",
    "CaptionR",
)
p(
    "Repeat observations are sparse: minimum 1, lower quartile 2, median 3, upper quartile 5, maximum 8. Sixty-two modeled plants have one observation. A single observation cannot establish repeat-observation variation; even eight independent repeats would weakly constrain a 1st or 99th percentile. Extra wavelength samples do not replace independent repeat spectra. These individual fans combine wavelength fitting with very limited replication.",
    "CaptionR",
)
evidence(
    "[L4], full individual model_index and observed spectra counts. Repeat observations may share flights; they are not assumed environmentally independent."
)

page("10. A measured failure of extreme-tail fitting")
p(
    "The following check compares a saved full-data species fit to empirical percentiles of exactly the same independent plants. It measures agreement with the training distribution, not external generalization. It exposes why visually prominent outer lines should not yet be read as calibrated species limits."
)
pic(
    "tail_fit_diagnostic.png",
    maxheight=210,
    caption="Figure 5. NIWO Abies lasiocarpa, corrected NEON, 32 plants. Left: solid boosted curves versus dotted empirical curves. Right: fitted and empirical quantiles at 425 nm. Large upper-tail disagreement is model underfit, not an observed extreme plant.",
)
table(
    ["Quantile at 425 nm", "Fitted value", "Empirical value"],
    [
        [f"{int(r['quantile'] * 100)}%", f"{r['fitted']:.1f}", f"{r['empirical']:.1f}"]
        for r in D["tail_425nm"]
    ],
    [1, 1, 1],
)
p(
    "The fitted median is close in this example, while q95 and q99 are grossly elevated. At q99, 32 plants provide an expected 0.32 observations in the upper 1% tail. That is a useful warning about support, not an effective-sample-size calculation. The boosted q99 value is about 12.3 times the empirical q99 value here; do not reinterpret that discrepancy as biological variability."
)
evidence(
    "[L4], checkpoint and matched NIWO plant spectra. This diagnostic was recomputed for the report; production fits remain unchanged."
)

page("11. Fit diagnostics and what has not been tested")
table(
    ["Stage", "Median empirical-quantile RMSE", "Maximum across 52 full species fits"],
    [[r["stage"], f"{r['median']:.1f}", f"{r['max']:.1f}"] for r in D["fit_rmse"]],
    [0.8, 1.4, 1.5],
)
p(
    "These RMSE values compare fitted versus empirical quantile arrays at supported wavelengths in native stored units. They summarize training-distribution agreement, not field accuracy. Different band grids and distributions make them unsuitable as a direct sensor-quality ranking. Twelve of 52 full species groups have fewer than 20 plants, per stage; extreme tails are particularly weakly supported."
)
subhead("Known strengths")
p(
    "Deterministic configuration, explicit spectral gaps, equal input-spectrum weight, saved empirical medians, raw and ordered predictions, and checksum-validated checkpoints make fitting reproducible and inspectable. Species/individual models and full/training partitions are explicit. Source values were not adjusted to make fans appear better behaved."
)
subhead("Missing robustness evidence")
p(
    "No systematic hyperparameter-selection study, repeated-seed evaluation, clustered bootstrap, convergence analysis, out-of-flight validation, out-of-year validation, leave-one-site-out evaluation, independent sensor check or external field validation has established robustness for these signatures. Exploratory tuning pilots were not adopted into production settings. The recorded seed and 80-round configuration provide reproducibility, not proof of optimal fitting."
)
note(
    "A lack of quantile crossings and a visually smooth median are useful engineering observations. Neither establishes tail calibration, physical realism or identification skill."
)
evidence(
    "[L4, L9], empirical_quantile_rmse, low_replication and crossing fields. The absence of studies listed above is a limitation, not evidence they would fail."
)

page("12. Descending quantile grids")
p(
    "The corrected, raw, Landsat and MicaSense 10 by 10 grids hold the percentile fixed within each subplot. Every populated subplot overlays that percentile from all 1,886 individual plants, colored by 22 species. Reading left to right, top to bottom moves from the unfitted 100% slot through 99%, 98%, ..., 1%."
)
# Render enlarged cell excerpts rather than shrink an entire 100-panel poster.
cells = []
for stage in ["corr", "olioli", "micasense"]:
    rr = []
    for qlabel in ["q99", "q50"]:
        path = F / f"{stage}_{qlabel}_crop.png"
        with PILImage.open(path) as im:
            w, h = im.size
        rr.append(
            Image(
                str(path),
                width=min(width * 0.43, 110 * w / h),
                height=min(width * 0.43 * h / w, 110),
            )
        )
    cells.append(
        [
            Paragraph(
                {
                    "corr": "Corrected NEON",
                    "olioli": "Derived OLI",
                    "micasense": "MicaSense*",
                }[stage],
                styles["CellR"],
            ),
            *rr,
        ]
    )
t = Table(
    [
        [
            Paragraph("<b>Product</b>", styles["CellR"]),
            Paragraph("<b>99% cell</b>", styles["CellR"]),
            Paragraph("<b>50% cell</b>", styles["CellR"]),
        ]
    ]
    + cells,
    colWidths=[width * 0.14, width * 0.43, width * 0.43],
)
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
S.append(t)
p(
    "Figure 6. Enlarged crops from the original descending grids. Crop labels identify the source cell; the crops preserve line values but are not new analyses. MicaSense physical coordinates are unverified. Original grid titles/legend and all remaining percentiles are retained in the source PDFs.",
    "CaptionR",
)
p(
    "These grids help locate overlap, horizontal/flat fitted tails and broad model differences at a fixed percentile. Heavy overlap is not a normalized density, class probability or independent simulation ensemble. The plotting order, opacity and species sample imbalance affect visibility; a common species can dominate the visual impression."
)
evidence(
    "[L4-L5], descending-grid artifacts and included GlobalID lists. There are 99 populated cells, not 100 fitted quantiles."
)

page("13. How unknown-spectrum matching was evaluated")
p(
    "The saved experiment assigns approximately 20% of each species/site's GlobalIDs to a deterministic holdout, retaining singleton groups in training. All observations of an identity stay together. There are 363 held-out plants in the globally eligible cohort. Separate training-only species fits are used for species matching; held-out identities are excluded from individual-reference candidate sets."
)
table(
    ["Aspect", "Meaning"],
    [
        [
            "Species reference score",
            "Twice the average pinball loss over 99 quantiles and shared supported wavelengths; lower is closer",
        ],
        [
            "Shared support",
            "At least half of a reference's supported bands; no extrapolation or unsupported-gap filling",
        ],
        [
            "Top-1 / top-3",
            "True species ranked first / among the first three candidates",
        ],
        [
            "Macro species accuracy",
            "Unweighted mean of species-specific accuracy; sensitive to small per-species holdout counts",
        ],
        [
            "Baseline",
            "Nearest empirical median by RMSE; additional MAE/RMSE template and majority-class baselines saved separately",
        ],
        [
            "Individual-reference search",
            "Ranks against other training plants from the known site; scores species-label agreement, not recovery of the same physical plant",
        ],
    ],
    [1.1, 2.3],
)
subhead("What leakage is prevented - and what dependence remains")
p(
    "Holding GlobalIDs apart prevents the same plant from appearing on both sides. It does not prevent training and holdout plants from sharing a flight, acquisition conditions or site. The plant-level split is therefore a within-library test. It can be optimistic for a genuinely new flight, year, site or sensor. Site-restricted tasks also have fewer candidate species and know the location in advance."
)
p(
    "The score is a discrete truncated integrated-quantile loss approximation, not a normalized likelihood or identification probability. It treats wavelengths pointwise and does not model whole-spectrum covariance. Band grids, units and sensor metadata must be compatible before any score is interpreted."
)
evidence(
    "[L7-L9], pinball-loss objective [W2]. Neither the main API nor this report claims a posterior species probability."
)

page("14. Pooled identification: weak present skill")
pr = []
for stage in ["raw", "corr", "olioli", "micasense"]:
    r = rows(stage, "ALL")[0]
    ci = interval("ALL", stage)
    b = baseline("species", "ALL", stage)
    pr.append(
        [
            stage,
            pct(r["top1_accuracy"]),
            f"{ci['correct']}/{ci['n']}",
            f"{100 * ci['wilson_low']:.1f}-{100 * ci['wilson_high']:.1f}%",
            pct(b["empirical_template_RMSE_accuracy"]),
            pct(b["majority_class_accuracy"]),
        ]
    )
table(
    ["Stage", "Top-1", "Correct", "95% Wilson interval", "Median RMSE", "Majority"],
    pr,
    [0.9, 0.65, 0.65, 1.1, 0.9, 0.8],
)
pic(
    "pooled_accuracy.png",
    maxheight=195,
    caption="Figure 7. Plant-level conditional binomial intervals for one fixed holdout, not repeated-training or site-transfer uncertainty. Dashed line: the observed majority-class baseline. MicaSense results use unverified archive labels, not established physical wavelengths.",
)
p(
    "Corrected NEON identifies 57 of 363 plants correctly: <b>15.7%</b>, identical to the median-RMSE baseline and below the 22.0% majority baseline. Its top-3 accuracy is 41.9% and macro species accuracy is 17.3%. Derived OLI improves over its median-RMSE baseline in this split but reaches only 20.9% top-1, still below the majority baseline. These results do not establish reliable identification."
)
p(
    "Wilson intervals [W3] assume independent Bernoulli outcomes and condition on this selected sample and trained model. Shared flights/site effects, model fitting, label error and split selection are not represented. Interval overlap is not a paired significance test; none is claimed here. Baseline comparisons should ultimately use paired, cluster-aware repeated evaluation.",
    "CaptionR",
)
evidence(
    "[L7-L8]; interval inputs are the saved per-plant top1_correct outcomes, with counts and formula preserved in accuracy_intervals.csv and the report analysis script."
)

page("15. Site-restricted and individual-reference matching")
table(
    [
        "Site",
        "Species top-1 / n",
        "Species median-RMSE",
        "Individual top-1 / n",
        "Individual median-RMSE",
    ],
    [
        [
            site,
            f"{pct(rows('corr', site)[0]['top1_accuracy'])} / {rows('corr', site)[0]['held_out_plants']}",
            pct(baseline("species", site, "corr")["empirical_template_RMSE_accuracy"]),
            f"{pct(baseline('individual', site, 'corr')['boosted_top1_accuracy'])} / {baseline('individual', site, 'corr')['held_out_plants']}",
            pct(
                baseline("individual", site, "corr")["empirical_template_RMSE_accuracy"]
            ),
        ]
        for site in ["NIWO", "WREF", "YELL"]
    ],
    [0.65, 1.15, 1.1, 1.2, 1.2],
)
p(
    "These corrected-NEON tasks give different answers because their reference sets and eligibility rules differ. Species-reference validation requires a qualifying species/site model; individual-reference validation can use locally sparse species from the globally eligible cohort. This explains WREF counts of 104 versus 106 and YELL counts of 66 versus 69. They are not two estimates on identical case sets."
)
p(
    "Individual-reference top-1 rates are higher than the species-fan rates in the saved site searches, but the empirical individual-median RMSE baseline is higher still in all three corrected-NEON site tasks: NIWO 41.5%, WREF 33.0%, YELL 53.6%. The boosted distributional representation therefore does not demonstrate a consistent benefit over simple stored templates."
)
subhead("Why the regional percentages are not a site ranking")
p(
    "Sites differ in candidate species count, sample balance, species identity, repeat coverage and acquisition conditions. YELL's higher observed accuracy does not mean its data or habitat are intrinsically easier to identify, nor that the method transfers there from another region. Training and testing were both within the known-site setting."
)
subhead("What a useful next identification experiment would require")
p(
    "Predefine the candidate set and intended unknown population; isolate held-out flights or years; select hyperparameters on training groups only; preserve identity grouping; include class-balanced and simple-template baselines; report errors by species/site and abstain when support or scores are poor. No tuned classifier or abstention threshold was created in this report."
)
evidence("[L7-L8]. Complete four-stage measurements follow in the appendix.")

page("16. Coverage is not the same as calibration")
table(
    [
        "Scope, corrected NEON",
        "Mean held-out 5-95% band coverage",
        "Nominal central interval",
    ],
    [
        [r["scope"], pct(r["true_species_05_95_band_coverage"]), "90% pointwise"]
        for r in rows("corr")
    ],
    [1.2, 1.7, 1.2],
)
p(
    "The saved coverage statistic averages the fraction of a held-out plant's supported bands falling between its true-species q5 and q95 curves. Pooled corrected coverage is 92.4%. That looks close to 90%, but it does not establish calibrated spectral uncertainty. An overly wide envelope can give high coverage even if upper tails are badly fitted; the 425 nm example shows that this happens in at least one group."
)
p(
    "A pointwise interval is not a simultaneous whole-spectrum interval. Neighboring bands are correlated, and a plant can be inside at most wavelengths while failing at a scientifically important feature. Aggregating all bands and plants can hide species- or wavelength-specific overcoverage and undercoverage. The number does not assess correct class assignment, and high true-class coverage can coexist with many overlapping wrong-class envelopes."
)
subhead("Needed checks before uncertainty claims")
p(
    "Inspect empirical versus fitted quantiles on training and held-out observations separately, coverage by quantile/wavelength/species/site, interval widths, repeat-split variability, and out-of-group calibration. Compare pinball loss to empirical quantile estimators and consider whether individual repeat counts can support the desired tail levels at all."
)
evidence(
    "[L4, L7]. The report does not promote marginal band coverage to a calibrated probability of species identity."
)

page("17. Year/site panels: what is actually available")
table(
    [
        "Year",
        "Site",
        "Labeled plants",
        "Observations",
        "Flights",
        "Eligible species / plants",
    ],
    [
        [
            r["year"],
            r["site"],
            r["plants"],
            r["observations"],
            r["flights"],
            next(
                f"{v['species']} / {v['plants']}"
                for v in D["year_eligible"]
                if v["year"] == r["year"] and v["site"] == r["site"]
            ),
        ]
        for r in D["year"]["acquisition_groups"]
    ],
    [0.5, 0.65, 0.85, 0.85, 0.55, 1.2],
)
p(
    "NIWO has acquisitions in both 2020 and 2023. WREF and YELL have 2023 only. The new panels retain all six combinations as columns so missing WREF/YELL 2020 acquisitions are explicit. They distinguish unavailable acquisitions, no plants of a particular species, and below-threshold cohorts."
)
p(
    "Acquisition year comes from the original source-table basename, cross-checked against the flight ID. Both legacy timestamped-reflectance names and newer dated directional-reflectance names are supported. Ancestor directories, field survey years and polygon editing dates are not substituted for spectral acquisition year."
)
p(
    "For each GlobalID, the within-year/site median of its flight/polygon spectra is recomputed before fitting species quantiles. The all-year median is not relabeled as a year-specific observation. There are 41 eligible species-year-site cells, fit separately for four stages: 164 additional signatures and 21 species in the union."
)
note(
    "All 886 NIWO plants observed in 2023 also have a 2020 identity record in the compact source grouping. They remain repeated plants, not independent replicates across years. The displayed 2020 species cohorts can nevertheless include additional plants not observed in 2023."
)
evidence(
    "[L6], source_year_site_provenance.csv, year_site_counts.csv and plant_year_site_cohorts.parquet. Counts in this table describe all labeled compact observations, before species eligibility filtering."
)

page("18. NIWO 2020 versus 2023: descriptive evidence", True)
pic(
    "niwo_year_examples.png",
    maxheight=345,
    caption="Figure 8. Corrected-NEON year-specific species fits for selected NIWO species. Each fan is refit from that year's plant medians. Plants and flight counts differ across years; n denotes independent plants within the cell.",
)
p(
    "The panels make changes in fitted level, shape and spread visible, but a visible shift has multiple possible causes: different plant subsets, flight dates, illumination, processing behavior and real plant condition. Differences between fitted tails are additionally contaminated by the established tail-fitting limitations. No formal temporal effect size, uncertainty interval or significance test was computed.",
    "CaptionR",
)
p(
    "A paired analysis would restrict to the same GlobalIDs in both years, compare supported bands or predefined spectral summaries within plant, and account for the shared acquisition structure. That is feasible for 886 repeated identities but has not been performed. Even a paired difference would not by itself identify a causal biological effect of year.",
    "CaptionR",
)
evidence(
    "[L6]. These are full within-year descriptive fits, not held-out year-transfer results."
)

page("19. Spatial contrast within 2023", True)
pic(
    "site_2023_examples.png",
    maxheight=345,
    caption="Figure 9. Selected corrected-NEON species quantiles for the three sites in 2023. Absent or small species cohorts are labeled rather than fitted. The shared vertical range supports visual comparison without rescaling each cell independently.",
)
p(
    "Restricting to a common calendar year removes the simplest year mismatch, but does not align flight date, phenology, illumination, canopy structure or site ecology. A species shared by sites provides a clearer comparison than unrelated species rows, yet its samples can still differ in selection and condition. The displayed cross-site differences are descriptive associations in the supplied library.",
    "CaptionR",
)
p(
    "Site means or medians pooled across species would conflate geography and composition. The species-row layout avoids that most direct mixture, while preserving sample-size and missing-cohort evidence. It does not replace a hierarchical analysis of plant, flight, site and year.",
    "CaptionR",
)
evidence(
    "[L6]. No sites other than NIWO, WREF and YELL are represented; broader regional transfer remains untested."
)

page("20. Robustness by component")
table(
    ["Component", "What is supported", "Principal remaining limit"],
    [
        [
            "Provenance and identity",
            "Source/flight/site checks; GlobalID grouping; verified compact checkpoints",
            "Inherited field labels and source metadata lack independent validation",
        ],
        [
            "Spectral support",
            "Explicit native grids, NaN gaps, no scaling/clipping or extrapolation",
            "Physical units not independently established; MicaSense labels unresolved",
        ],
        [
            "Empirical summaries",
            "Equal-plant descriptive medians and distributions",
            "Selection bias, shared flights and median aggregation can hide within-plant variation",
        ],
        [
            "Boosted median shape",
            "Inspectable nonlinear wavelength fit and empirical comparison",
            "Training fit is not external validity; tuning/convergence not established",
        ],
        [
            "Extreme quantiles",
            "Saved, auditable q1-q99 predictions",
            "Sparse tail replication and measured underfit",
        ],
        [
            "Identification",
            "Plant-disjoint within-library evaluation and simple baselines",
            "Weak accuracy; no blocked transfer or external sensor validation",
        ],
        [
            "Year/site views",
            "Acquisition-specific regrouping and explicit missing combinations",
            "Different cohorts; no paired inference or causal interpretation",
        ],
        [
            "Visualization",
            "Alphabetical rows, distinct sensors, shared full-range axes",
            "Opacity/order affect visibility; sparse-band connections are not extra samples",
        ],
    ],
    [1, 1.5, 1.6],
)
p(
    "Software tests and scientific robustness answer different questions. Recent targeted suites passed 26 year/site-region-quantile tests and 18 overlay/quantile tests; these counts overlap and must not be added as independent evidence. They exercise contracts such as exact coordinates, gaps, plant grouping, holdout separation and checkpoint reuse. They do not establish physical calibration, ecological representativeness or statistical generalization."
)
evidence(
    "[L9], saved test results recorded in FEATURE_REQUESTS and validation notes; this report also verified manifest-covered output checksums and its own tables/figures."
)

page("21. Prioritized next analyses")
table(
    ["Priority", "Action", "Evidence needed to advance"],
    [
        [
            "1: band identity",
            "Recover original MicaSense product headers; reconcile exporter fallback/padding",
            "Verified physical band centers/response definitions with provenance; regenerate affected interpretations",
        ],
        [
            "2: fit adequacy",
            "Evaluate per-quantile and per-band errors; tune on training groups only",
            "Clear improvement over empirical quantiles, especially tails; stable validation, no guessed repairs",
        ],
        [
            "3: identification",
            "Use blocked flight/year/site tests and stronger simple baselines",
            "Repeated, paired, cluster-aware improvement; useful per-species errors and abstention behavior",
        ],
        [
            "4: temporal change",
            "Analyze the 886 repeated NIWO identities with predefined summaries",
            "Within-plant differences, uncertainty reflecting flights, sensitivity to cohort and date",
        ],
        [
            "5: sampling robustness",
            "Bootstrap identities and cluster acquisition groups; compare eligibility thresholds",
            "Stability of median/quantile patterns and conclusions under defensible perturbations",
        ],
        [
            "6: real sensor transfer",
            "Acquire independent satellite/drone/field measurements",
            "Validation on independent observations, not convolutions of the same reference",
        ],
    ],
    [0.7, 1.7, 1.7],
)
subhead("Practical use now")
p(
    "Use the empirical traces and central summaries to inspect within-library variation, detect suspicious products, identify underrepresented groups and design the next validation dataset. Use the quantile fans as model diagnostics and exploratory reference shapes. Treat their scores as candidate-ranking aids that require verification, not final labels."
)
subhead("Practical claims to defer")
p(
    "Defer reliable species identification, calibrated 99% spectral limits, universal sensor interchangeability, causal year effects, and broad regional generalization. None is established by a large number of plotted lines, the absence of missing supported bands, high pointwise coverage, or passing code tests."
)
evidence(
    "Recommendations are inferences from [L1-L9], not newly demonstrated results. Pending repository tasks P107 and P108 cover band identity and model/identification improvement."
)

page("22. Full species-reference validation table")
table(
    ["Scope", "Stage", "n", "Top-1", "Top-3", "Macro", "Median RMSE", "5-95 coverage"],
    [
        [
            r["scope"],
            r["stage"],
            r["held_out_plants"],
            pct(r["top1_accuracy"]),
            pct(r["top3_accuracy"]),
            pct(r["macro_species_accuracy"]),
            pct(r["empirical_median_baseline_accuracy"]),
            pct(r["true_species_05_95_band_coverage"]),
        ]
        for r in D["matching"]
    ],
    [0.8, 1.1, 0.5, 0.7, 0.7, 0.7, 0.95, 1],
)
p(
    "All entries are within-library results on the saved fixed holdout. Site-level eligibility differs from pooled eligibility. Mean true-species coverage is pointwise across supported bands. MicaSense rows use the supplied unverified archive coordinate labels. The majority baseline is not shown here but is retained in the next appendix and embedded evidence.",
    "CaptionR",
)
p(
    "Top-1 accuracies are not interchangeable across scopes because the candidate species, distributions and denominators differ. No table entry is an external sensor accuracy or an estimate of transfer to a new site.",
    "CaptionR",
)
evidence(
    "[L7]. Percentages are rounded only for presentation; embedded evidence retains full numeric precision."
)

page("23. Baselines and individual-reference results")
ibs = [r for r in D["baselines"] if r["level"] == "individual"]
table(
    ["Site", "Stage", "n", "Boosted", "Median MAE", "Median RMSE", "Majority"],
    [
        [
            r["scope"],
            r["stage"],
            r["held_out_plants"],
            pct(r["boosted_top1_accuracy"]),
            pct(r["empirical_template_MAE_accuracy"]),
            pct(r["empirical_template_RMSE_accuracy"]),
            pct(r["majority_class_accuracy"]),
        ]
        for r in ibs
    ],
    [0.7, 1, 0.5, 0.8, 0.9, 0.9, 0.8],
)
p(
    "The empirical-template baselines rank held-out spectra against stored medians from eligible training identities. MAE and RMSE are computed on identical shared supported positions within each comparison. Scores remain in the supplied units and no cross-sensor calibration is inferred. Individual-reference searches exclude all held-out GlobalIDs and operate within the known site.",
    "CaptionR",
)
subhead("Pooled species-template baseline detail")
table(
    ["Stage", "Boosted", "Median MAE", "Median RMSE", "Majority"],
    [
        [
            r["stage"],
            pct(r["boosted_top1_accuracy"]),
            pct(r["empirical_template_MAE_accuracy"]),
            pct(r["empirical_template_RMSE_accuracy"]),
            pct(r["majority_class_accuracy"]),
        ]
        for r in D["baselines"]
        if r["level"] == "species" and r["scope"] == "ALL"
    ],
    [1, 1, 1, 1, 1],
)
evidence(
    "[L8]. Species/site baseline rows not duplicated here remain in the embedded report_evidence.json and source matching_baselines.csv."
)

# Inventory lists every original PDF without silently treating aliases as independent evidence.
for chunk in range(0, len(D["inventory"]), 10):
    page(
        f"Artifact inventory {chunk // 10 + 1} of {math.ceil(len(D['inventory']) / 10)}"
    )
    p(
        "Paths are relative to artifacts/plant_spectral_atlas/. The original files remain available in the repository workspace. This inventory includes historical layouts and aliases; byte-identical aliases are not additional scientific results. Original page counts refer to the source PDF, not this report.",
        "CaptionR",
    )
    rr = []
    for r in D["inventory"][chunk : chunk + 10]:
        label = html.escape(r["path"]).replace("/", "/<br/>")
        rr.append([label, str(r["pages"]), f"{r['bytes'] / 1048576:.2f}"])
    table(["Original PDF path", "Pages", "MiB"], rr, [4.5, 0.5, 0.6])
    p(
        "Complete SHA-256 values and file sizes are retained in the embedded figure_inventory.json. Long overview figures are best read in their original vector PDFs; this report embeds selected excerpts at readable size.",
        "CaptionR",
    )

page("Source ledger and reproducibility")
entries = [
    (
        "L1",
        "Data and harmonization",
        "audit.json, manifest.json, common_coverage.csv, native_band_statistics.csv, plant_harmonized_spectra.parquet",
    ),
    (
        "L2",
        "Matched empirical comparisons",
        "comparisons/comparison_audit.json; comparisons/products/{raw,corr,olioli,micasense}/ manifests and compact tables",
    ),
    (
        "L3",
        "Regions",
        "comparisons/regional/regional_audit.json, matched_plant_regions.parquet and regional sample-size outputs",
    ),
    (
        "L4",
        "Boosted fits",
        "quantile_models/quantile_audit.json, model_index.parquet, quantile_manifest.json and checkpoints/",
    ),
    (
        "L5",
        "Descending grids",
        "quantile_overlays/overlay_audit.json and four sensor/stage PDF/PNG grids",
    ),
    (
        "L6",
        "Year/site fits",
        "year_site_quantiles/year_site_audit.json, model_index.parquet, cohort/count/provenance tables and manifest",
    ),
    (
        "L7",
        "Holdout species evidence",
        "quantile_models/matching_validation.csv, held_out_species_matches.csv, training_holdout_plants.parquet",
    ),
    (
        "L8",
        "Additional baselines",
        "quantile_models/held_out_individual_reference_matches.csv; quantile_validation/matching_baselines.csv",
    ),
    (
        "L9",
        "Methods and checks",
        "src/spectralbridge/plant_spectral_{atlas,comparison,regions,quantiles,years}.py; plant_quantile_overlays.py; matching tests; docs/vignettes/plant-spectral-atlas.md",
    ),
]
for key, title, text in entries:
    p(f"<b>[{key}] {title}.</b> " + html.escape(text), "SmallR")
p(
    "All L1-L8 paths are relative to artifacts/plant_spectral_atlas/. Code/docs paths in L9 are relative to repository root. Source input: Aug_2026_all_polygons_merged_pixel_extraction.parquet. No raster or pixel-scale spectral data were reopened for this report.",
    "CaptionR",
)
p(
    f"The report analysis verified {D['verified_manifest_outputs']:,} manifest-covered output entries, including checkpoint metadata/prediction files and figure aliases. This is an integrity count, not a count of independent observations. Input hashes, derived diagnostics and figure paths are preserved in report_evidence.json."
)
p(
    "Rebuild evidence with the repository environment using provenance/plot-report/2026-10-13/analyze_report.py; build the PDF with build_report.py in the bundled ReportLab runtime. Original data/models are not attached to this PDF. Compact report evidence, accuracy intervals and figure inventory are embedded as attachments; a report-only evidence ledger can be read without the production archive.",
    "CaptionR",
)

page("References and interpretation boundaries")
p(
    "<b>[W1] XGBoost authors. Quantile Regression example.</b> Official documentation, accessed 13 October 2026. Supports the recorded quantile objective and the warning that quantile crossing can occur. It does not validate these plant data.",
    "Body",
)
p(
    '<link href="https://xgboost.readthedocs.io/en/release_2.1.0/python/examples/quantile_regression.html" color="#326b78">xgboost.readthedocs.io - quantile regression example</link>',
    "SmallR",
)
p(
    "<b>[W2] Scikit-learn authors. Metrics and scoring: quantifying the quality of predictions.</b> Official documentation, accessed 13 October 2026. Pinball loss is aligned with conditional quantile prediction; an identification probability does not follow from this loss.",
    "Body",
)
p(
    '<link href="https://scikit-learn.org/stable/modules/model_evaluation.html#pinball-loss" color="#326b78">scikit-learn.org - model evaluation / pinball loss</link>',
    "SmallR",
)
p(
    "<b>[W3] NIST/SEMATECH e-Handbook of Statistical Methods. 7.2.4.1 Confidence intervals.</b> Accessed 13 October 2026. Reference for Wilson binomial intervals. The intervals in this report use z = 1.959963984540054 and do not adjust for acquisition clustering or fitted-model uncertainty.",
    "Body",
)
p(
    '<link href="https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm" color="#326b78">itl.nist.gov - confidence intervals for proportions</link>',
    "SmallR",
)
subhead("Interpretation boundaries")
p(
    "All production counts, accuracies and spectral discrepancies are calculated from this supplied archive, not package constants or general scientific guarantees. Descriptive differences have not been tested as ecological effects. Model fit diagnostics, marginal coverage, and species-label accuracy are distinct evidence. Physical interpretation of the MicaSense wavelength axis remains blocked pending source-header verification."
)
p(
    "This report is a synthesis of computational evidence and documented limitations. It does not certify source labels, field measurements, sensor calibration, ecological representativeness or transfer beyond the library. No new model fit, new classification result, paired-change test or physical band remapping was introduced in preparing it."
)


class ReviewDoc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == "H1":
            title = f.getPlainText()
            if title:
                key = "section" + str(self.page)
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(title, key, 0)


def footer(canvas, doc):
    w, h = canvas._pagesize
    canvas.setStrokeColor(colors.HexColor("#c9d5db"))
    canvas.line(46, 34, w - 46, 34)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#617079"))
    canvas.drawString(
        46, 22, "SpectralBridge | Methods and robustness review | 13 October 2026"
    )
    canvas.drawRightString(w - 46, 22, str(doc.page))
    if doc.page > 1:
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            46, h - 24, "SPECTRAL SIGNATURES: EVIDENCE, INTERPRETATION AND LIMITS"
        )


doc = ReviewDoc(
    str(PDF),
    pagesize=A4,
    leftMargin=46,
    rightMargin=46,
    topMargin=47,
    bottomMargin=48,
    title="SpectralBridge spectral plots: methods, findings and robustness",
    author="OpenAI Codex; local SpectralBridge analysis review",
)
for name, size in [("portrait", A4), ("landscape", landscape(A4))]:
    w, h = size
    doc.addPageTemplates(
        PageTemplate(
            id=name,
            frames=Frame(
                46,
                48,
                w - 92,
                h - 96,
                leftPadding=0,
                bottomPadding=0,
                rightPadding=0,
                topPadding=0,
            ),
            onPage=footer,
            pagesize=size,
        )
    )
doc.build(S)
# Embed compact, inspectable evidence without copying the source scientific dataset.

reader = PdfReader(PDF)
writer = PdfWriter()
writer.clone_document_from_reader(reader)
for name in ["report_evidence.json", "accuracy_intervals.csv", "figure_inventory.json"]:
    writer.add_attachment(name, (REPORT_DIR / name).read_bytes())
temporary = PDF.with_suffix(".pdf.tmp")
with temporary.open("wb") as f:
    writer.write(f)
temporary.replace(PDF)
print(PDF)
print("Pages", len(PdfReader(PDF).pages))
