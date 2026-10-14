"""Build the human-readable PDF from verified researcher-category outputs."""

from pathlib import Path
import hashlib
import json
import html

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "artifacts/plant_spectral_atlas/researcher_pft_statistics"
HERE = Path(__file__).resolve().parent
TMP = ROOT / "tmp/pdfs/researcher_pft"
TMP.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "output/pdf/researcher_pft_distinguishability_report.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)


def digest(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


manifest = json.loads((RUN / "manifest.json").read_text())
assert all(digest(RUN / n) == h for n, h in manifest["outputs"].items())
interpret = json.loads((RUN / "interpretation/manifest.json").read_text())
assert all(
    digest(RUN / "interpretation" / n) == h for n, h in interpret["outputs"].items()
)
assert digest(HERE / "methods_and_effects.csv") == digest(
    RUN / "interpretation/methods_and_effects.csv"
)
assert digest(HERE / "support.csv") == digest(RUN / "support.csv")
s = pd.read_csv(HERE / "methods_and_effects.csv")
p = s[s.blocking == "flight_history"].copy()
support = pd.read_csv(HERE / "support.csv")
t = pd.read_parquet(RUN / "polygon_year_spectra.parquet")
cohorts = ["NIWO 2020", "NIWO 2023", "WREF 2023", "YELL 2023"]
cats = sorted(t.cover_category.unique())
abbrev = {
    "Deciduous": "D",
    "Evergreen": "E",
    "Herbaceous": "H",
    "Non-vegetated & dead": "N",
    "Woody shrub": "W",
}
p["short"] = p.a.map(abbrev) + " / " + p.b.map(abbrev)
plt.rcParams.update(
    {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
)
# Effect magnitudes are estimators, not p-values or classification accuracies.
matrix = p.pivot(
    index="short", columns="cohort", values="weighted_rms_standardized_contrast"
).reindex(columns=cohorts)
fig, ax = plt.subplots(figsize=(7.3, 5))
im = ax.imshow(matrix.to_numpy(), cmap="YlGnBu", vmin=0, vmax=1.8, aspect="auto")
ax.set(
    xticks=np.arange(4),
    xticklabels=cohorts,
    yticks=np.arange(10),
    yticklabels=matrix.index,
)
for i in range(10):
    for j in range(4):
        val = matrix.iloc[i, j]
        ax.text(
            j,
            i,
            f"{val:.2f}",
            ha="center",
            va="center",
            color="white" if val > 1.1 else "#142b36",
            fontsize=11,
        )
fig.colorbar(
    im, ax=ax, label="RMS standardized spectral contrast", fraction=0.045, pad=0.03
)
fig.tight_layout()
fig.savefig(TMP / "effects.png", dpi=220)
plt.close(fig)
# Full cohort descriptions: median and empirical spread, distinct from matched mean contrasts.
cols = [c for c in t if c.startswith("corr_wl")]
w = np.array([float(c.split("_wl")[1][:-2]) for c in cols])
for name, cohort_names in [("niwo", cohorts[:2]), ("other", cohorts[2:])]:
    fig, axes = plt.subplots(5, 2, figsize=(7.2, 8), sharex=True, squeeze=False)
    for i, category in enumerate(cats):
        for j, cohort in enumerate(cohort_names):
            site, year = cohort.split()
            sub = t[
                (t.site == site)
                & (t.year == int(year))
                & (t.cover_category == category)
            ]
            values = sub[cols].to_numpy(float)
            valid = np.isfinite(values).any(axis=0)
            ix = np.flatnonzero(valid)
            med = np.nanmedian(values[:, valid], axis=0)
            lo, hi = np.nanquantile(values[:, valid], [0.1, 0.9], axis=0)
            ax = axes[i, j]
            for seg in np.split(
                np.arange(len(ix)), np.flatnonzero(np.diff(w[ix]) > 8) + 1
            ):
                ax.fill_between(w[ix[seg]], lo[seg], hi[seg], color="#bbd6e2")
                ax.plot(w[ix[seg]], med[seg], color="#185c79", lw=1)
            ax.set_title(f"{cohort} | {abbrev[category]} | n={len(sub)}", fontsize=9)
            ax.tick_params(labelsize=8)
            if j == 0:
                ax.set_ylabel(
                    category.replace("Non-vegetated & dead", "Nonvegetated\n& dead"),
                    fontsize=8,
                )
            if i == 4:
                ax.set_xlabel("Wavelength (nm)", fontsize=9)
    fig.tight_layout(h_pad=0.55, w_pad=1.2)
    fig.savefig(TMP / (name + ".png"), dpi=220)
    plt.close(fig)
# Four transparently selected examples: broad contrast, two energy exceptions,
# and a small-magnitude contrast. Not chosen to hide non-significant tests.
selected = [
    ("NIWO 2023", "Evergreen", "Non-vegetated & dead"),
    ("WREF 2023", "Deciduous", "Woody shrub"),
    ("YELL 2023", "Deciduous", "Herbaceous"),
    ("YELL 2023", "Herbaceous", "Woody shrub"),
]
e = pd.read_csv(RUN / "envelopes.csv")
fig, axes = plt.subplots(2, 2, figsize=(7.3, 5.5), squeeze=False)
for ax, (cohort, a, b) in zip(axes.flat, selected):
    row = p[(p.cohort == cohort) & (p.a == a) & (p.b == b)].iloc[0]
    frame = e[(e.test_id == row.test_id) & (e.scope == "family")].sort_values(
        "wavelength_nm"
    )
    with np.load(RUN / "checkpoints" / (row.test_id + ".npz")) as result:
        se = result["se"]
    ww = frame.wavelength_nm.to_numpy()
    observed = frame.beta.to_numpy() / se
    low = frame.lower.to_numpy() / se
    high = frame.upper.to_numpy() / se
    for ix in np.split(np.arange(len(ww)), np.flatnonzero(np.diff(ww) > 8) + 1):
        ax.fill_between(ww[ix], low[ix], high[ix], color="#d1dce5")
        ax.plot(ww[ix], observed[ix], color="#145b77", lw=1)
    sig = frame.excursion.to_numpy(bool)
    ax.scatter(ww[sig], observed[sig], color="#b73c36", s=3, zorder=3)
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_title(
        f"{cohort}: {abbrev[a]} minus {abbrev[b]}\nEnergy adjusted p={row.p_energy_holm:.4g}",
        fontsize=9,
    )
    ax.set_xlabel("Wavelength (nm)", fontsize=9)
    ax.set_ylabel("Standardized test contrast", fontsize=8)
    ax.tick_params(labelsize=8)
fig.tight_layout()
fig.savefig(TMP / "envelope_examples.png", dpi=220)
plt.close(fig)

C = colors.HexColor
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleX",
        fontName="Helvetica-Bold",
        fontSize=30,
        leading=34,
        textColor=C("#163d52"),
        spaceAfter=17,
    )
)
styles.add(
    ParagraphStyle(
        name="H1X",
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=C("#163d52"),
        spaceAfter=15,
    )
)
styles.add(
    ParagraphStyle(
        name="H2X",
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=C("#185c79"),
        spaceBefore=10,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyX", fontName="Helvetica", fontSize=10.4, leading=15, spaceAfter=9
    )
)
styles.add(
    ParagraphStyle(
        name="SmallX",
        fontName="Helvetica",
        fontSize=8.3,
        leading=11.5,
        spaceAfter=6,
        textColor=C("#41525d"),
    )
)
styles.add(ParagraphStyle(name="CellX", fontName="Helvetica", fontSize=8.3, leading=11))
styles.add(
    ParagraphStyle(
        name="CallX",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=18,
        textColor=C("#163d52"),
        spaceAfter=8,
    )
)
story = []


def para(text, style="BodyX"):
    story.append(Paragraph(text, styles[style]))


def h(text):
    para(text, "H2X")


def page(title, kicker=None):
    if story:
        story.append(PageBreak())
    if kicker:
        para(kicker.upper(), "SmallX")
    para(title, "H1X")


def img(path, width=504, maxheight=480):
    iw, ih = ImageReader(str(path)).getSize()
    height = width * ih / iw
    if height > maxheight:
        width *= maxheight / height
        height = maxheight
    story.append(Image(str(path), width=width, height=height))
    story.append(Spacer(1, 7))


def table(rows, widths=None, small=False):
    cells = [
        [Paragraph(html.escape(str(v)), styles["CellX"]) for v in row] for row in rows
    ]
    obj = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    obj.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), C("#e5eef3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), C("#163d52")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, C("#9cb5c3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C("#f5f7f9")]),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, C("#c9d4da")),
            ]
        )
    )
    story.append(obj)
    story.append(Spacer(1, 10))


def call(text):
    obj = Table([[Paragraph(text, styles["CallX"])]], colWidths=[504])
    obj.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), C("#eaf3f4")),
                ("BOX", (0, 0), (-1, -1), 0.6, C("#b7d1d8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(obj)
    story.append(Spacer(1, 12))


para("SPECTRALBRIDGE | SCIENTIFIC RESULTS", "SmallX")
para("Can we tell the<br/>PFTs apart?", "TitleX")
para(
    "A plain-language guide to the researcher-defined spectral groups<br/>Corrected NEON spectra | 14 October 2026",
    "BodyX",
)
call(
    "Yes, the sampled groups have statistically distinguishable spectra.<br/>We have not yet measured how accurately an unknown polygon can be classified."
)
para(
    "Using the five classes chosen by researchers in <b>cover_category</b>, every class pair shows a spectral difference in each available site/year cohort. This conclusion applies to the sampled polygon mixtures, conditional on the acquisition blocks and the test assumptions. It does not imply that every trace is unique or that the groups never overlap."
)
table(
    [
        ["Evidence", "Result"],
        ["Primary combined test", "40 of 40 matched comparisons supported"],
        ["Maximum / integrated / FPCA tests", "40 of 40 supported by each method"],
        ["Energy-distance sensitivity", "38 of 40 supported"],
        ["Scope", "3,639 polygon identities; 4,807 polygon/year spectra"],
    ],
    [188, 316],
)
h("The useful distinction")
para(
    "<b>Different groups:</b> Do class labels track systematic differences in the measured curves? The present tests support yes.<br/><b>Recognizing a new sample:</b> Can a model assign one unknown curve correctly? That requires held-out prediction tests, which were not performed here."
)
para(
    "This report explains the data, the executed tests, the results and their practical limits. It uses the researcher labels, not the earlier species-name-derived PFT tags. Non-vegetated &amp; dead is retained as a cover comparator, not described as a living plant functional type.",
    "SmallX",
)

page("What was compared?", "01 | Data and sampling units")
para(
    "The five researcher classes are <b>Deciduous, Evergreen, Herbaceous, Woody shrub, and Non-vegetated &amp; dead</b>. They are the source table labels, preserved exactly. They mix vegetation habit, growth form and nonliving cover; the label definitions should be checked before giving a physiological explanation."
)
rows = [["Class", "Unique polygon IDs"]]
for c in cats:
    rows.append([c, f"{t[t.cover_category == c].GlobalID.nunique():,}"])
table(rows, [330, 174])
para(
    "All 3,639 polygon identities have a nonmissing, consistent class across their source records. A species name is missing for 1,143 identities; they remain included because the researcher class is available. A polygon can represent a crown, a shrub patch, herbaceous cover, or nonvegetated material. Therefore the analysis unit is called a <b>polygon</b>, not always an individual plant."
)
h("How many polygon/year spectra are available?")
rows = [["Cohort", "D", "E", "H", "N", "W", "Total"]]
for co in cohorts:
    site, year = co.split()
    sub = support[(support.site == site) & (support.year == int(year))].set_index(
        "cover_category"
    )
    counts = [int(sub.loc[c, "polygons"]) for c in cats]
    rows.append([co, *counts, sum(counts)])
table(rows, [114, 65, 65, 65, 65, 65, 65])
para(
    "<b>Key:</b> D = Deciduous; E = Evergreen; H = Herbaceous; N = Non-vegetated &amp; dead; W = Woody shrub. These abbreviations are used in the figures and numerical tables.",
    "SmallX",
)
para(
    "NIWO is represented in 2020 and 2023; WREF and YELL in 2023. Repeated years can contain the same polygon IDs. They are tested separately, so 4,807 polygon/year spectra must not be described as 4,807 different plants or independent cross-year replications."
)

page("How a pixel table becomes a fair comparison", "02 | Design before tests")
h("1. Reduce repeated measurements before testing")
para(
    "Pixels within the same polygon and acquisition are summarized by a median spectrum. Repeated acquisition/polygon observations are then summarized by an equally weighted median within each polygon and year. A polygon with many pixels or flights does not receive one independent vote per pixel or flight. The fitted quantile lines are not used as independent observations."
)
h("2. Compare within site and year")
para(
    "Ten class pairs are compared in each of four cohorts: 40 comparisons. Each uses corrected NEON spectra. Sensor-simulated Landsat and MicaSense products are not independent observations and are not part of this report's inference."
)
h("3. Match acquisition histories for the primary analysis")
para(
    "Within a site/year, polygons are grouped by the exact set of flight IDs and source images that contributed their spectra. Labels are shuffled only among polygons sharing that history. Blocks containing only one of the two classes do not contribute to that pair. At least 10 polygons per class across the contributing mixed blocks are required; all 40 pairs meet this threshold. Matched sample sizes differ by pair."
)
h("4. Keep a broader sensitivity analysis")
para(
    "The site/year sensitivity removes the exact-history restriction and shuffles within the whole site/year. It uses more polygons, but provides less control for acquisition exposure. Its 40 comparisons form a separate correction family. Agreement is reassuring; it does not remove all observational confounding."
)
h("5. Retain actual spectral support")
para(
    "Source-aware aggregation harmonizes the wavelength grids without filling unsupported gaps. The atlas excludes 1340-1450 and 1790-2000 nm; interpolation is limited to gaps of at most 8 nm. The tests use only finite, variable wavelengths shared by the contributing polygons. All matched comparisons retain 360 wavelengths. Finite negative corrected values are retained."
)
call(
    "The statistical question is conditional: among sampled polygons with comparable acquisition histories, do the class labels track spectral differences?"
)

page(
    "The common engine: shuffle labels, keep curves",
    "03 | What a permutation test means",
)
para(
    "Imagine two classes whose labels carry no spectral information once the acquisition block is fixed. Under that null model, swapping class labels among comparable polygons should produce differences like the observed one. A permutation test constructs that reference directly from the measured curves."
)
table(
    [
        ["Step", "What happens"],
        [
            "Observed result",
            "Calculate a measure of the difference between the two classes.",
        ],
        [
            "Null reference",
            "Shuffle whole-polygon labels within each block 9,999 times, keeping each spectrum intact and class counts fixed within each block.",
        ],
        [
            "Comparison",
            "Ask how often a shuffled statistic is at least as extreme as the observed statistic.",
        ],
        [
            "Probability",
            "Use (1 + extreme shuffled results) / 10,000, including the observed arrangement.",
        ],
    ],
    [112, 392],
)
para(
    "Whole curves move together. Nearby wavelengths are not incorrectly treated as independent experiments. The same shuffled labels are used for the methods, which makes their comparison consistent."
)
h("What must be true for this to work?")
para(
    "Within each block, class labels must be exchangeable under the null: after conditioning on the block, a label swap must be a defensible representation of no class-related distributional difference. These observational classes were not randomly assigned. Unmodeled spatial clustering, species composition or canopy conditions can violate that assumption. The mean-oriented statistics do not become assumption-free tests of equal means with arbitrary unequal distributions."
)
h("What does a small p-value say?")
para(
    "The observed statistic is unusual under this no-label-information model. A p-value is <b>not</b> the probability that the classes are the same, the fraction of polygons correctly recognized, or the size of the difference. Small p-values can coexist with extensive overlap when samples are large."
)
para(
    "Randomly drawn permutation p-values include the observed arrangement and must not be reported as zero [1]. The minimum attainable raw value here is 0.0001.",
    "SmallX",
)

page(
    "Tests 1 and 2: a sharp feature or a broad shift?", "04 | Mean-contrast components"
)
h("Test 1. Maximum spectral difference")
para(
    "<b>Question:</b> Is there any supported wavelength where the block-adjusted class contrast is unusually large?<br/><b>How it works:</b> Estimate the class A minus class B mean contrast after subtracting acquisition-block means. At each wavelength, divide by a fixed, label-independent scale based on within-block spectral variation. Take the largest absolute standardized contrast. Compare it with the largest contrast from each shuffled data set."
)
para(
    "<b>Intuition:</b> A detector for a strong departure somewhere along the curve. It can detect a localized feature even if most of the spectrum is similar. Taking the maximum inside every shuffle accounts for searching all tested wavelengths."
)
para(
    "<b>Result:</b> All 40 matched comparisons are supported; every Holm-adjusted p-value is 0.004. The simultaneous-envelope examples visualize this same maximum statistic, rather than providing a new independent confirmation."
)
h("Test 2. Integrated spectral difference")
para(
    "<b>Question:</b> Is the total standardized difference across the supported spectrum unusually large?<br/><b>How it works:</b> Square the standardized contrast at each wavelength, weight by wavelength coverage and add the pieces. Squaring keeps positive and negative differences from canceling. Weights follow trapezoidal integration and do not bridge excluded gaps. Compare this total with the same total from each shuffle."
)
para(
    "<b>Intuition:</b> A detector for a moderate difference spread over many wavelengths. It complements the maximum, which emphasizes the single strongest departure. It does not itself identify which wavelengths are significant."
)
para(
    "<b>Result:</b> All 40 matched comparisons are supported. Adjusted p-values are 0.004 except WREF Deciduous versus Woody shrub and WREF Herbaceous versus Woody shrub, which are 0.006."
)
call(
    "These two statistics ask complementary questions about the same block-adjusted mean curve. They share the same data and shuffles, so they are correlated evidence."
)

page(
    "Tests 3 and 4: combine signals and compare shape",
    "05 | Primary omnibus and functional sensitivity",
)
h("Test 3. Combined maximum + integrated test (NPC)")
para(
    "<b>Question:</b> Is there evidence of a class difference, whether it appears as a sharp feature or a broad change?<br/><b>How it works:</b> Use the synchronized shuffles to obtain probability ranks for the maximum and integrated statistics. Take the smaller component probability (a Tippett combination), then calibrate that combination against the same shuffled ensemble. This calibration accounts for looking at two component tests and their dependence."
)
para(
    "<b>Intuition:</b> Give the analysis two ways to detect a difference, while charging the statistical cost of having those two ways. NPC means nonparametric combination. It is the <b>primary test</b> for the conclusions in this report, not an uncorrected rule to accept whichever test is positive."
)
para(
    "<b>Result:</b> All 40 matched comparisons have adjusted p = 0.004. All 40 broader site/year sensitivity comparisons also have adjusted p = 0.004 in their own family. A combined-test rejection alone does not locate a significant wavelength."
)
h("Test 4. Functional principal component comparison (FPCA)")
para(
    "<b>Question:</b> Do the classes differ in a small set of dominant patterns of spectral variation?<br/><b>How it works:</b> Remove block means, standardize wavelengths and apply wavelength weights. A label-blind singular value decomposition finds common curve patterns, such as coordinated changes in brightness or shape. Retain enough components to explain at least 95% of the total weighted variation, capped at 10 and by available rank/degrees of freedom. Whiten those component scores, calculate a block-adjusted score contrast, and use the same label shuffles for its reference distribution."
)
para(
    "<b>Intuition:</b> Replace hundreds of correlated bands with a few main ways that the curves vary, then ask whether the class centers differ in that reduced space. Because labels do not choose the components, the projection is fixed during permutation. A difference in a discarded low-variance direction can still be missed."
)
para(
    "<b>Result:</b> All 40 matched comparisons are supported, with adjusted p = 0.004. Two or three components were retained, explaining 95.3-98.8% of variation. This is a functional-response sensitivity, not a fitted classifier or a fully adjusted species/spatial mixed model."
)

page(
    "Test 5 and the safeguards around every result",
    "06 | Distributions, localization and multiplicity",
)
h("Test 5. Energy distance")
para(
    "<b>Question:</b> Do the classes differ in their spectral distributions, rather than only in a mean-curve projection?<br/><b>How it works:</b> Compute distances between whole standardized, wavelength-weighted curves inside each mixed block. Compare distances between classes with distances within each class. Combine block contributions using weights proportional to nA x nB / (nA + nB), and compare with the same label shuffles. This is an explicit blocked adaptation of energy statistics [2]."
)
para(
    "<b>Intuition:</b> Compare the two clouds of curves. A location change, spread change or other distributional difference can contribute. It is not a test of classification accuracy, and it has different power from the maximum or FPCA statistics."
)
para(
    "<b>Result:</b> 38 of 40 matched comparisons are supported. WREF Deciduous versus Woody shrub has adjusted p = 0.2235; YELL Deciduous versus Herbaceous has p = 0.1182. These are weaker multi-method conclusions, not proof of identical distributions."
)
h("Simultaneous envelopes: where is the departure?")
para(
    "Each shuffle contributes its largest scaled contrast. A critical value from those maxima creates a band around the no-difference curve that controls excursions over all supported wavelengths. For the displayed matched panels, a further Bonferroni factor of 40 controls the contrast family. An excursion shows a wavelength contributing to the maximum-test rejection. This is a <b>null envelope</b>, not a confidence interval for the true class difference and not an ERL rank-envelope implementation [3]."
)
h("Holm correction: account for asking 40 questions")
para(
    "For each method, sort the 40 p-values, compare them with increasingly less stringent thresholds, and enforce monotonic adjusted p-values. This limits the chance of one or more false rejections within that method's family, assuming valid individual p-values. The primary NPC family and sensitivity methods are reported separately; we do not declare success by taking the union of whichever methods reject."
)
para(
    "The repeated primary adjusted value 0.004 is the resolution floor (40 x 0.0001 here), not evidence that all effects are equal. Holm decisions and the more conservative fixed Bonferroni envelope can differ in general.",
    "SmallX",
)

page(
    "How large are the observed differences?", "07 | Magnitudes, not just significance"
)
para(
    "Every primary comparison rejects, so p-values alone do little to rank practical separation. The figure summarizes the block-adjusted mean contrast relative to the pooled within-block spectral variation. Each cell is the wavelength-weighted root-mean-square (RMS) standardized contrast."
)
img(TMP / "effects.png", maxheight=355)
para(
    "<b>Key:</b> D = Deciduous; E = Evergreen; H = Herbaceous; N = Non-vegetated &amp; dead; W = Woody shrub. Larger values indicate a larger average standardized curve contrast for that cohort and matched sample. These are descriptive magnitudes, with no effect-size confidence intervals supplied.",
    "SmallX",
)
para(
    "<b>The smaller differences deserve attention:</b> WREF D/W = 0.336 and YELL H/W = 0.352 are the smallest. WREF H/W = 0.409 is also relatively small. Strong evidence of a nonzero group difference does not make those pairs easy to classify."
)
para(
    "<b>The nonvegetated/dead comparator is strongly differentiated:</b> contrasts involving N range from 0.801 to 1.795 across the four cohorts. This supports a broad cover distinction; it does not establish a particular biochemical mechanism or isolate bare ground from dead vegetation."
)
para(
    "Values do not use an arbitrary small/medium/large cutoff and cannot be converted directly to accuracy. Acquisition matching and class composition differ by pair, so these are not a universal ranking of class difficulty."
)

page("What the spectra look like: NIWO", "08 | Typical curves and their spread")
img(TMP / "niwo.png", maxheight=546)
para(
    "Each row is one researcher class; columns are 2020 and 2023. Dark line: median polygon/year spectrum. Shading: empirical 10th-90th percentile range across polygons, not a confidence interval. Values are in stored spectral units. Local vertical scales differ. Gaps are retained.",
    "SmallX",
)
para(
    "These are full-cohort descriptive plots, not the acquisition-matched mean-contrast estimator. The broad spreads explain why significant group differences can coexist with ambiguous individual traces.",
    "SmallX",
)

page("What the spectra look like: WREF and YELL", "09 | Regional context")
img(TMP / "other.png", maxheight=546)
para(
    "The same definitions apply: median and empirical 10th-90th percentile range, full site/year cohorts, stored spectral units and local vertical scales. See page 2 for the class key.",
    "SmallX",
)
para(
    "Class differences are detected within each site/year. This is not a test that the same spectral rule transfers across regions. Regional shifts, mixed composition and class-specific spread can change recognition difficulty.",
    "SmallX",
)

page("Where do the curves differ?", "10 | Reading simultaneous null envelopes")
img(TMP / "envelope_examples.png", maxheight=360)
para(
    "The dark curve is the signed, block-adjusted class contrast divided by its fixed null scale for the test. Positive means the first class is higher; negative means the second class is higher. Grey-blue shading is the family-controlled maximum null envelope. Red points mark departures outside that band. Missing spectral intervals remain blank. Vertical scales differ.",
    "SmallX",
)
para(
    "Examples were selected to show a larger contrast (NIWO E/N), both energy-distance exceptions (WREF D/W and YELL D/H), and another small-magnitude contrast (YELL H/W). All four have primary NPC and maximum adjusted p = 0.004."
)
para(
    "The WREF D/W contrast shows departures despite its small RMS magnitude and non-significant energy test. YELL D/H also has maximum evidence but weaker energy evidence. The tests summarize different aspects of the curves; disagreement does not permit choosing one retrospectively as the sole answer."
)
call(
    "An envelope excursion identifies evidence against the no-label-information model at those wavelengths. It does not prove that an unknown trace at those wavelengths will be uniquely identifiable."
)

for names, title in [
    (cohorts[:2], "Full matched results: NIWO"),
    (cohorts[2:], "Full matched results: WREF and YELL"),
]:
    page(title, "11 | Numerical results")
    para(
        "All entries below use acquisition-matched polygons. Every row has NPC, maximum and FPCA adjusted p = 0.004. All integrated tests reject; WREF D/W and H/W have adjusted p = 0.006, the remainder 0.004. Energy values are listed because agreement varies. All p-values are Holm-adjusted across 40 contrasts within each method.",
        "SmallX",
    )
    for cohort in names:
        h(cohort)
        rows = [["Pair", "n A / n B", "NPC p", "Energy p", "RMS effect"]]
        for row in p[p.cohort == cohort].itertuples():
            rows.append(
                [
                    row.short,
                    f"{row.n_a} / {row.n_b}",
                    f"{row.p_npc_holm:.4g}",
                    f"{row.p_energy_holm:.4g}",
                    f"{row.weighted_rms_standardized_contrast:.3f}",
                ]
            )
        table(rows, [90, 115, 90, 104, 105])
    para(
        "D = Deciduous; E = Evergreen; H = Herbaceous; N = Non-vegetated &amp; dead; W = Woody shrub. The RMS effect is a descriptive standardized curve magnitude, not a prediction metric. Matched n changes by pair because only acquisition-history blocks containing both classes contribute.",
        "SmallX",
    )

page("What can we conclude, and what comes next?", "12 | Scientific judgment")
call(
    "The sampled researcher-defined groups are distinguishable at the group level across all four available site/year cohorts. Individual-trace recognition remains an open prediction question."
)
h("What makes that conclusion reasonably well supported?")
para(
    "The analysis uses actual empirical polygon spectra, not fitted quantiles as replicates. It reduces repeated pixel/acquisition observations, compares within site/year, uses acquisition matching, preserves spectral gaps, adjusts for multiple questions and compares complementary test statistics. Primary results agree with the broader site/year sensitivity and most energy-distance results. The strongest conclusion is about sampled class mixtures under the stated exchangeability assumption."
)
h("What still limits robustness?")
para(
    "<b>Composition and ecology:</b> Species, canopy structure, substrate and illumination may explain some class differences. Some species occur in multiple researcher classes; the earlier species-derived tag analysis's exact species/PFT aliasing result cannot simply be reused. This report does not estimate an independent causal PFT effect.<br/><b>Dependence:</b> Exact acquisition histories do not account for all spatial correlation. Repeated NIWO years are not independent sets of polygons.<br/><b>Scope:</b> Three sites and two represented years do not establish universal regional transfer. The nonvegetated/dead class combines potentially different materials.<br/><b>Exploration:</b> These are post-exploration observational results. Multiple-test adjustment does not erase choices made during earlier plot exploration."
)
h("What earlier simulations do and do not establish")
para(
    "The method audit used 15,000 simulated studies across null and alternative scenarios. In 5,000 exchangeable-null studies, the primary combined test rejected 4.86% at a nominal 5% level (95% Monte Carlo interval 4.30-5.49%). This supports implementation/calibration under those simulated assumptions. It does not show that the real polygons are exchangeable, spatially independent, or accurately classifiable. Those simulations were not rerun as a new empirical validation for these labels."
)
h('The next test for "Can I name this unknown trace?"')
para(
    "Fit and evaluate a classifier with all records of a polygon held together. For the sampled-population question, use blocked held-out polygons and report the confusion matrix, per-class recall/precision and balanced accuracy, with uncertainty. Spatial or acquisition grouping should prevent leakage. Then test held-out sites or species only if transfer is the scientific target. Prioritize D/W and H/W ambiguities. No classification results are claimed in this report."
)

page("Technical details, sources and reproducibility", "13 | Audit trail")
h("Exact statistical target and estimator")
para(
    "For a pair of classes, center the binary class indicator and spectra within the contributing blocks. At each wavelength, beta = sum(centered indicator x centered spectrum) / sum(centered indicator squared). This is a common block-adjusted mean coefficient, with block weights proportional to nA x nB / n. The fixed pooled scale is the square root of the within-block sum of squared spectral deviations divided by n minus the number of blocks. The maximum/integrated test curve scales beta by that pooled scale divided by the square root of the centered indicator sum of squares. This fixed scale includes class-related variation; it is not a Welch standard error."
)
para(
    "The reported RMS magnitude instead divides beta by the pooled spectral scale itself, squares the ratios, averages with normalized wavelength weights and takes the square root. Therefore it removes the sample-size factor used by the test statistic. It remains descriptive and does not quantify individual-class overlap.",
    "SmallX",
)
h("Reproduce and inspect")
para(
    'Analysis: <font name="Courier">examples/researcher_pft_statistics.py</font><br/>Report: <font name="Courier">provenance/researcher-pft/2026-10-14/build_report.py</font><br/>Evidence: <font name="Courier">provenance/researcher-pft/2026-10-14/</font><br/>Full generated tables, memberships, checkpoints and envelopes:<br/><font name="Courier">artifacts/plant_spectral_atlas/researcher_pft_statistics/</font>',
    "SmallX",
)
para(
    'The analysis used 9,999 permutations per contrast, seed 20261014 with deterministic per-test seeds. Checks verified 181 primary output files, unchanged source bytes, all 173 previous inferred-label outputs, exact membership counts, envelope/scalar decisions and restart reuse. Thirty-four targeted tests passed. Source Parquet SHA-256:<br/><font name="Courier" size="7">'
    + manifest["identity"]["source"]
    + "</font>",
    "SmallX",
)
h("Selected methodological sources")
para(
    '[1] Phipson &amp; Smyth (2010). Permutation p-values should never be zero. <link href="https://gksmyth.github.io/pubs/PermPValuesPreprint.pdf" color="#185c79">Author paper</link>. Explains the observed-arrangement correction for randomly drawn permutations.',
    "SmallX",
)
para(
    '[2] Szekely &amp; Rizzo (2013). Energy statistics: a class of statistics based on distances. <link href="https://doi.org/10.1016/j.jspi.2013.03.018" color="#185c79">doi:10.1016/j.jspi.2013.03.018</link>. The current blocked weighting is an explicit implementation adaptation.',
    "SmallX",
)
para(
    '[3] Myllymaki &amp; Mrkvicka (2024). GET: Global Envelopes in R. <link href="https://www.jstatsoft.org/article/view/v111i03" color="#185c79">Journal of Statistical Software 111(3)</link>. Global envelope concepts; this analysis uses a scaled maximum envelope, not the R GET implementation or ERL.',
    "SmallX",
)
para(
    '[4] Pesarin &amp; Salmaso (2010). Permutation Tests for Complex Data. <link href="https://doi.org/10.1002/9780470689516" color="#185c79">doi:10.1002/9780470689516</link>. Synchronized partial tests and calibrated nonparametric combination.',
    "SmallX",
)
para(
    "Methods reviewed but not executed for the new researcher classes include ERL rank envelopes, full species/spatial functional mixed models, classifier validation, equivalence tests and a separate rank sensitivity. This report makes no claim that those analyses have been completed.",
    "SmallX",
)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(C("#bed0d9"))
    canvas.setLineWidth(0.5)
    canvas.line(54, 42, 558, 42)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C("#506674"))
    canvas.drawString(
        54, 28, "SpectralBridge | Researcher PFT spectral evidence | 14 October 2026"
    )
    canvas.drawRightString(558, 28, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUT),
    pagesize=(612, 792),
    leftMargin=54,
    rightMargin=54,
    topMargin=46,
    bottomMargin=56,
    title="Can we tell the PFTs apart? Researcher-category spectral evidence",
    author="SpectralBridge analysis; prepared with OpenAI Codex",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
verification = {
    "pdf": str(OUT.relative_to(ROOT)),
    "pdf_sha256": digest(OUT),
    "analysis_manifest_sha256": digest(RUN / "manifest.json"),
    "interpretation_manifest_sha256": digest(RUN / "interpretation/manifest.json"),
    "report_source_sha256": digest(__file__),
    "source_parquet_sha256": manifest["identity"]["source"],
}
(HERE / "REPORT_VERIFICATION.json").write_text(
    json.dumps(verification, indent=2) + "\n"
)
print(OUT)
