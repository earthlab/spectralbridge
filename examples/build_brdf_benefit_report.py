"""Build the team BRDF benefit report from verified compact numerical evidence.

Run with a Python environment containing ReportLab/Pillow/pypdf. This builder does
not analyze pixels, change labels or rerun correction fits. Source tables and code
are hashed beside the PDF. Main5band effects and declared sensitivities all appear.
"""

import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape
import csv
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provenance/brdf-benefit-audit/2026-11-19"
PDF = ROOT / "output/pdf/brdf_benefit_across_aop_drone_landsat_report.pdf"
WIDTH = 7.35 * 72
NAVY = colors.HexColor("#183849")
TEAL = colors.HexColor("#168b7b")
GREY = colors.HexColor("#eaf0f3")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(name):
    with (BASE / name).open() as stream:
        return list(csv.DictReader(stream))


def number(r, key, multiply=1, digits=2):
    v = r.get(key, "")
    return f"{float(v) * multiply:.{digits}f}" if v else "NA"


def run():
    PDF.parent.mkdir(parents=True, exist_ok=True)
    evidence = json.loads((BASE / "summary/summary.json").read_text())
    for p, h in evidence["all_source_hashes"].items():
        if sha(BASE / p) != h:
            raise ValueError("Evidence changed: " + p)
    fonts = Path("/System/Library/Fonts/Supplemental")
    pdfmetrics.registerFont(TTFont("Team", str(fonts / "Arial.ttf")))
    pdfmetrics.registerFont(TTFont("TeamBold", str(fonts / "Arial Bold.ttf")))
    pdfmetrics.registerFontFamily(
        "Team", normal="Team", bold="TeamBold", italic="Team", boldItalic="TeamBold"
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TeamBody",
            fontName="Team",
            fontSize=9.3,
            leading=13,
            spaceAfter=8,
            textColor=NAVY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TeamTitle",
            fontName="TeamBold",
            fontSize=24,
            leading=28,
            spaceAfter=13,
            textColor=NAVY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TeamH",
            fontName="TeamBold",
            fontSize=16,
            leading=20,
            spaceAfter=10,
            textColor=NAVY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TeamSmall",
            fontName="Team",
            fontSize=8,
            leading=10.5,
            spaceAfter=6,
            textColor=NAVY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TeamCell", fontName="Team", fontSize=8.2, leading=10.4, textColor=NAVY
        )
    )
    story = []

    def p(text, kind="TeamBody"):
        return Paragraph(text, styles[kind])

    def add(text, kind="TeamBody"):
        story.append(p(text, kind))

    def image(name, width=WIDTH):
        path = BASE / "summary" / name
        w, h = ImageReader(str(path)).getSize()
        story.append(Image(str(path), width=width, height=width * h / w))
        story.append(Spacer(1, 6))

    def table(rows, widths):
        t = Table(
            [[p(escape(str(c)), "TeamCell") for c in row] for row in rows],
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREY),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.7, NAVY),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#d6e0e6")),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 10))

    def page(title):
        story.append(PageBreak())
        add(title, "TeamH")

    rates = read("statistics/identifiability.csv")

    def row(sensor, scheme, bands=5):
        return next(
            r
            for r in rates
            if r["sensor"] == sensor
            and r["scheme"] == scheme
            and r["bands"] == str(bands)
        )

    add("Does BRDF earn its complexity?", "TeamTitle")
    add(
        "A matched benefit-and-cost audit across our Landsat, AOP and drone data<br/><b>Team report • 20 November 2026</b>"
    )
    add(
        "<b>Current evidence does not show a consistent PFT recognition benefit.</b> HLS changes recognition little; the archived AOP correction package gives small, mixed effects; incremental drone BRDF lowers held-site recognition in this cohort. These results do not establish that BRDF is unnecessary for time series, reflectance accuracy or every sensor geometry."
    )
    rows = [
        ["Five-band comparison", "Control → corrected balanced accuracy", "Change (pp)"]
    ]
    for sensor, scheme, label in [
        ("hls", "unseen_identity", "HLS, unseen patch"),
        ("aop_archive", "held_site", "AOP package, held site"),
        ("drone_10pct", "held_site", "Drone 10% mask, held site"),
    ]:
        r = row(sensor, scheme)
        rows.append(
            [
                label,
                f"{number(r, 'ba_no_brdf', 100)}% → {number(r, 'ba_brdf', 100)}%",
                number(r, "delta_ba", 100),
            ]
        )
    table(rows, [165, 270, WIDTH - 435])
    image("recognition_effects.png")
    add(
        "Intervals: pointwise 95% paired identity-bootstrap intervals, conditional on fitted folds. The shaded ±2-point zone is an illustrative decision aid, not an equivalence test or a universal definition of a small benefit. Unmasked Ruby failed BRDF QA and is a diagnostic sensitivity only.",
        "TeamSmall",
    )
    add(
        "<b>Decision for this project:</b> there is no evidence here of a large, reliable PFT information gain that would justify further intensive drone BRDF tuning by itself. Preserve the controlled alternatives and require an independent validation benefit before making BRDF a prerequisite. Keep HLS NBAR as the standard product; this small, geographically confounded snapshot does not justify undoing operational HLS processing."
    )

    page("1 / What exactly was compared?")
    table(
        [
            [
                "Data and independent unit",
                "Matched support",
                "What the contrast isolates",
            ],
            [
                "Landsat HLS L30 v2; spatial patch",
                "1,241 cells in 61 patches; 9 granules; 5 PFTs",
                "NBAR versus reconstructed pre-NBAR on the SAME HLS grid, atmosphere and cells. Original directional quantization cannot be recovered.",
            ],
            [
                "NEON AOP archive; labelled GlobalID",
                "85,706 source pixel rows; 122 flights; 3,639 identities / 4,807 identity-years; NIWO, WREF, YELL",
                "Raw versus archived BRDF + topography, projected before polygon medians. This is a bundled pipeline comparison, not a BRDF-only effect.",
            ],
            [
                "Drone; field polygon",
                "300 paired polygons / 3 sites; 189,178 shared labelled pixels in 10% arm",
                "Frozen topographic-only versus the SAME topographic model plus BRDF, with identical mask, pixel support and fixed five-band OLI2-like affine.",
            ],
            [
                "Real-angle AOP control; 20 m block",
                "One R10C window, 120 × 3,000 pixels; 720 training and 180 held blocks; 72,000 held pixels",
                "Current BRDF-only algorithm; no topography; held spatial groups excluded from fitting. Angular diagnostic only; no PFT labels or truth reflectance.",
            ],
        ],
        [151, 164, WIDTH - 315],
    )
    add(
        "<b>BRDF</b> is the dependence of reflected light on illumination and viewing directions. A correction predicts a shared reference geometry; it cannot itself supply independent ground truth. <b>Topographic correction</b> addresses terrain illumination and is a distinct stage. <b>NBAR</b> means nadir BRDF-adjusted reflectance. HLS uses globally fixed RossThick/LiSparseR coefficients; our current fitted AOP/drone implementation uses its recorded kernel configuration, so this is not a comparison of identical algorithms."
    )
    add(
        "<b>Identifiability:</b> can a fixed classifier recognize PFT on an unseen identity or site? Balanced accuracy is the mean of the five PFT recalls, so abundant evergreen polygons do not dominate the score. <b>Separability:</b> do two labelled PFT distributions differ within sites? A significant difference does not imply reliable recognition, and its p-value is not a measure of physical reflectance accuracy."
    )
    add(
        "Main analyses use five common OLI-like bands in physical fractional units, without spectrum-sum normalization; seven-band AOP/HLS results are declared sensitivities. All source stages, correction settings, masks and classification choices were fixed before these new effect results were calculated. The design is retrospective: prior project outcomes were known, and this is not a preregistered randomized trial."
    )

    page("2 / Recognition: effects, uncertainty and transfer")
    rows = [
        [
            "Cohort / bands / evaluation",
            "Control %",
            "Corrected %",
            "Δ pp [95% conditional interval]",
            "Holm p / site p",
        ]
    ]
    names = {
        "hls": "HLS",
        "aop_archive": "AOP package",
        "drone_10pct": "Drone 10%",
        "drone_unmasked": "Drone null†",
    }
    for r in rates:
        label = (
            names[r["sensor"]]
            + " / "
            + r["bands"]
            + " / "
            + ("identity" if r["scheme"] == "unseen_identity" else "site")
        )
        if r["status"] == "SUPPORTED":
            rows.append(
                [
                    label,
                    number(r, "ba_no_brdf", 100),
                    number(r, "ba_brdf", 100),
                    f"{number(r, 'delta_ba', 100)} [{number(r, 'ci_low', 100)}, {number(r, 'ci_high', 100)}]",
                    number(r, "p_identity_holm_family", 1, 3)
                    + " / "
                    + number(r, "p_site_exact_holm_family", 1, 3),
                ]
            )
        else:
            rows.append([label, "NA", "NA", "Unsupported training classes", "NA"])
    table(rows, [154, 59, 65, 156, WIDTH - 434])
    add(
        "“Identity” is five grouped folds; “site” leaves each domain out. AOP repeats never cross folds, and metrics give each identity equal total weight. Fixed training-only standardization plus balanced logistic regression (C = 1) is unchanged between arms. These are classifier-specific tests; a different downstream task could respond differently.",
        "TeamSmall",
    )
    add(
        "<b>How to read the p-values.</b> The first is the paired whole-identity correctness-swap test, Holm-adjusted across all 10 supported recognition contrasts. The second is the exact whole-site/domain swap sensitivity, with its own Holm adjustment. Every adjusted whole-domain p-value is 1.000. With only three AOP/drone sites, even large polygon counts cannot establish a broadly transferable site-level effect. The bootstrap intervals above are unadjusted and conditional; they can exclude zero when an adjusted test does not."
    )
    add(
        "<b>HLS limits:</b> some PFTs occur in only one region, so a complete five-class held-region experiment is unsupported. This is reported as NA, never a zero score. Seven-band HLS predictions were identical between arms: the zero-width fixed-prediction bootstrap interval does not establish equivalence or account for training variability. Purity labels remain provisional pending the separate team review."
    )
    add(
        "† Unmasked sensitivity intentionally retains the known invalid Ruby BRDF bands for comparison. Its larger apparent loss is evidence about this diagnostic run, not a production-approved estimate."
    )

    page("3 / Drone: a QA pass did not establish a PFT benefit")
    image("drone_class_recalls.png")
    add(
        "The 7.42-point held-site balanced-accuracy decrease is concentrated in <b>non-vegetated &amp; dead</b>: recall falls from 92.3% to 57.7%. Woody shrub falls from 2.5% to 0%; deciduous, evergreen and herbaceous recalls are unchanged at these fixed held-site predictions. The baseline already performs poorly for shrub, so this is not evidence that BRDF erased otherwise strong shrub recognition."
    )
    qa = read("summary/drone_qa_support.csv")
    rows = [
        [
            "Site",
            "Unmasked combined valid bands",
            "10% combined valid bands",
            "10% BRDF-only valid bands",
        ]
    ]
    for site in ["gordon", "goldhill", "ruby"]:

        def q(v, stage):
            return (
                next(
                    r["valid_bands"]
                    for r in qa
                    if r["site"] == site and r["variant"] == v and r["stage"] == stage
                )
                + "/10"
            )

        rows.append(
            [
                site.title(),
                q("baseline", "combined"),
                q("conservative", "combined"),
                q("conservative", "brdf_only"),
            ]
        )
    table(rows, [90, 145, 145, WIDTH - 380])
    add(
        "<b>What QA establishes:</b> angular design support, stable coefficients, bounded spatial-cluster uncertainty and positive predictions above uncertainty at observed/reference geometries. Those checks constrain numerical model use. They do not establish correct ground reflectance, improved PFT recognition or successful cross-site transfer. Ruby’s masked BRDF-only model remains 9/10; the primary combined model is 10/10. The combined 668 nm reference prediction is 0.019286 with SE 0.009823; its lower uncertainty margin is only 0.0000322, so the pass is narrow."
    )
    add(
        "<b>Coverage cost:</b> of 200,363 original labelled pixel memberships in 302 polygons, 189,178 enter the matched masked comparison (94.42%); 300 polygons remain. The unmasked comparison has 195,849 shared memberships and the same 300 polygons. Main effects compare topographic-only and combined values on the identical retained pixels, so the within-variant BRDF result is not caused by changing the analysed pixels."
    )
    add(
        "Both arms retain conditional historical drone radiometry: native stored values decode by 0.0001999969482421875, then the same AOP-derived fractional affine maps selected native bands to OLI2-like channels. The registry is a synthetic same-AOP diagnostic relationship, not independent empirical sensor calibration. No failed-QA product was silently approved."
    )

    page("4 / Repeated views and the BRDF-only AOP control")
    image("repeat_view_consistency.png")
    repeat = read("summary/repeat_view_summary.csv")
    r = next(r for r in repeat if r["site"] == "ALL" and r["bands"] == "5")
    add(
        f"For 3,207 AOP identities observed at repeated nominal ground centres on the same day (4,090 polygon-days), the five-band median relative change in repeat-view RMS is {float(r['median_percent_change']):.2f}%; {100 * float(r['fraction_improved']):.1f}% of identities improve. Across identities, median RMS is {float(r['median_rms_no_brdf']):.5f} before and {float(r['median_rms_brdf']):.5f} after. This bundled archive comparison does not show a broad repeat-view gain. Exact nominal centres do not guarantee perfect physical coregistration.",
        "TeamSmall",
    )
    image("aop_brdf_only_control.png")
    add(
        "The independent spatial-fit control passes 10/10 current band checks. Within held 20 m blocks, measured angular R² is already weak before correction (0.31–0.65%); after correction it is 0.36–0.84%, increasing in all ten selected native bands. This window supplies no positive angular-flattening evidence. It is one bounded R10C scene, not the full AOP archive, and low initial angular association limits the possible gain.",
        "TeamSmall",
    )
    add(
        "Archive identity checks found 181/12,504 plant-flight pairs unchanged to 10^-12 in all seven projected channels; some other flights have near-identity adjustments. They are retained, not selected out. The audit evaluates the delivered archive; it cannot certify that every historical flight correction was active or physically adequate. Reduced repeat-view dispersion or angular R², if found, would still be consistency evidence rather than absolute accuracy.",
        "TeamSmall",
    )

    page("5 / Separation: a p-value count is not a gain estimate")
    image("separation_effects.png")
    sep = read("statistics/separability.csv")
    rows = [
        [
            "Five-band cohort",
            "Testable pairs",
            "Control supported",
            "Corrected supported",
        ]
    ]
    for sensor in names:
        x = [
            r
            for r in sep
            if r["sensor"] == sensor
            and r["bands"] == "5"
            and r["status"] == "SUPPORTED"
        ]
        counts = []
        for arm in ["no_brdf", "brdf"]:
            aa = [r for r in x if r["arm"] == arm]
            counts.append(
                f"{sum(float(r['p_npc_holm_family']) <= 0.05 for r in aa)}/{len(aa)}"
            )
        rows.append([names[sensor], str(len(x) // 2) + "/10", *counts])
    table(rows, [166, 95, 130, WIDTH - 391])
    add(
        "Each cell is the change in a site-adjusted, standardized RMS PFT contrast; positive means greater separation under correction. Only sites containing both PFTs contribute. Gray NA cells have no within-site exchangeable comparison. HLS has only four testable PFT pairs because class and region are entangled. Counts use Holm over all 96 supported arm-specific NPC tests, including seven-band sensitivities.",
        "TeamSmall",
    )
    add(
        "AOP is already at 10/10 supported pairs without the correction package; it cannot improve that count, even though effect sizes can move. Drone has 5/10 supported pairs in both masked stages while held-site recognition falls. The unmasked diagnostic gains one supported pair while losing recognition. These are compatible outcomes: distributional differences, generalization and physical accuracy measure different things."
    )
    add(
        "Paired separation-change tests and exact site swaps are archived for all 48 supported feature/cohort/PFT contrasts, with a separate Holm family. No whole-site separation-change result survives that family adjustment. Do not tune correction or inference methods simply to increase the number of significant pairs."
    )

    page("6 / Benefit versus effort: what the numbers justify")
    add(
        "<b>Landsat HLS:</b> median absolute multiplicative adjustments are 1.33–1.60% across bands, with bandwise 95th percentiles 2.56–3.09%. Five-band recognition changes by +0.10 points, with a conditional interval spanning about −4.0 to +4.3 points. That is no demonstrated large gain for this snapshot; it is not a test of multi-date normalization, high-angle extremes or absolute reflectance accuracy."
    )
    add(
        "<b>AOP:</b> archived combined processing changes unseen-identity balanced accuracy by −0.81 points (five bands) and held-site accuracy by −0.08 points. The repeat-view median benefit is approximately zero. The BRDF-only holdout control adds no positive consistency evidence in its weak-angular-signal window. Together, these results do not support a claim of a large PFT benefit from the delivered pipeline, and cannot isolate historical BRDF from topography."
    )
    add(
        "<b>Drone:</b> masked incremental BRDF changes unseen-identity recognition by −0.65 points and held-site recognition by −7.42 points. Conditional uncertainty and site counts prevent a universal harm claim, but the estimated transfer loss is large enough to require explanation before adopting this stage for PFT analysis. Passing 10/10 fit checks is insufficient justification."
    )
    record = json.loads((BASE / "aop-control/completed.json").read_text())
    add(
        f"<b>Measured computation:</b> the bounded AOP control took {record['fit_seconds']:.2f} s to fit and {record['application_seconds']:.2f} s for application plus diagnostic reduction, within {record['elapsed_seconds']:.1f} s total after source hashing. These local timings are not whole-scene benchmarks. Compact archive extraction, reconstruction and statistical elapsed times are retained in each completed.json. Existing runs do not consistently record comparable correction-stage runtimes, peak RAM or scientist-hours. A defensible numerical labour-cost/benefit ratio is therefore unavailable."
    )
    add(
        "<b>Recommended gate for further effort:</b> retain raw and topographic-only comparison products; validate geometry and radiometry independently; then require a held-site or repeat-target benefit that matters for the planned scientific endpoint. Agree on a practical gain threshold before another optimisation run. Illustrative thresholds of two or five accuracy points are decision aids only, and additional independent sites are required to establish transfer."
    )
    add(
        "For HLS, continue using its established NBAR product rather than reverting the dataset on the strength of this audit. For drone PFT work, preserve both stages and avoid treating BRDF as mandatory pending independent validation. This report changes no production products, figure numbers, source data, QA guards or scientific defaults."
    )
    add(
        "The evidence supports questioning automatic adoption, not a conclusion about scientific fashion. Directional reflectance is a physical phenomenon, and the literature documents BRDF effects and time-series consistency benefits in settings beyond this sample. The practical question is whether the particular implementation improves the particular endpoint enough to justify its cost."
    )

    page("7 / Methods, limitations and reproducibility")
    add(
        "<b>Pairing and aggregation.</b> All comparisons use finite common source support without outcome-based trimming; negative corrected reflectance is retained. AOP raw/corrected native spectra are projected through the existing Gaussian OLI-like diagnostic response before plant-flight medians, then equally averaged over flights per plant-year. They are not measured sensor response convolutions. For separation, plant histories are averaged to one curve per identity. Repeated-view variance uses same-day, same-identity, nominal same-ground centres across unique flights, with stable grouped variance, then medians by polygon-day and identity."
    )
    add(
        "<b>Recognition inference.</b> Both arms share grouped folds, training-only scaling and fixed C = 1 balanced logistic classifiers. Histories stay with their identity, and held domains purge identities globally. Correctness is averaged per identity, then weighted equally across true PFTs. The change uses 9,999 paired identity sign swaps and exact whole-domain swaps; 1,999 paired true-class-stratified identity bootstrap replicates supply conditional 95% intervals. Classifier refitting is not part of this bootstrap, so it omits model-training variability. Training is row-based; histories have equal total identity weight in reported metrics. No equivalence claim follows from a nonsignificant p-value."
    )
    add(
        "<b>Separation inference.</b> Complete-curve labels are permuted within mixed sites using 9,999 draws plus the identity configuration. Max-band and equal-discrete-band integrated statistics are jointly calibrated using the existing NPC rule, regression-tested against the canonical implementation. The compact implementation omits unused quadratic energy matrices; it changes neither NPC draws nor results. Paired arm swaps quantify standardized separation change. Separate Holm families cover 10 supported recognition contrasts, 96 supported arm-specific NPC tests and 48 supported separation changes. Both identity and whole-domain p-value families are retained."
    )
    add(
        "<b>HLS reconstruction.</b> For band λ, cλ = model(reference geometry) / model(observed geometry), and reconstructed pre-NBAR = archived NBAR / cλ. We compiled pinned, unmodified official NASA RTLS kernels and coefficients at commit 8620ed613b7250149c29dbffb19e9f947e235871. Per-pixel solar/view angles and the granule NBAR_SOLAR_ZENITH metadata set the geometries. Sampled B01 values match the existing cohort. The reconstructed directional quantization bound is at most half a 10^-4 stored step divided by cλ for unclipped samples. This is not original Landsat Collection 2 and cannot reverse upstream atmosphere, resampling or clipping."
    )
    add(
        "<b>Inference limits.</b> These are observational, task-specific results with only three AOP/drone sites, regional class confounding, provisional Landsat PFT labels and no independent absolute-reflectance ground truth. Nearby polygons may remain correlated; site-swap sensitivity is deliberately reported separately. Historical AOP corrections are bundled and incompletely certified; drone historical radiometry is conditional. Neither surface anisotropy nor a correction algorithm is guaranteed to align with PFT classification objectives."
    )
    add(
        "Study folder: <b>provenance/brdf-benefit-audit/2026-11-19/</b>. See README.md for the exact run order, source locations, units, checkpoint behaviour and dependencies. All primary predictions, fold memberships, class recalls, p-values, effects, source hashes and declared unsupported cases are preserved. This is a reproducible local evidence bundle, not a claim that restricted/local source data have been publicly archived or independently validated.",
        "TeamSmall",
    )

    page("8 / Source references and evidence map")
    add("<b>Primary external sources</b>")
    refs = [
        (
            "Roy et al. (2016), A general method to normalize Landsat reflectance data to nadir BRDF adjusted reflectance, Remote Sensing of Environment 176:255–271. DOI 10.1016/j.rse.2016.01.023.",
            "https://doi.org/10.1016/j.rse.2016.01.023",
        ),
        (
            "Ju et al. (2025), The Harmonized Landsat and Sentinel-2 version 2.0 surface reflectance dataset. DOI 10.1016/j.rse.2025.114723. Includes c-factor inversion as a supported property.",
            "https://doi.org/10.1016/j.rse.2025.114723",
        ),
        (
            "NASA HLS BRDF Normalization: operational c-factor, fixed coefficients and v2 solar-angle convention. Accessed20 November2026.",
            "https://hls.gsfc.nasa.gov/brdf-adjustment/",
        ),
        (
            "Official NASA-IMPACT hls-landsat-tile implementation, pinned source commit used for the reconstruction.",
            "https://github.com/NASA-IMPACT/hls-landsat-tile/tree/8620ed613b7250149c29dbffb19e9f947e235871",
        ),
    ]
    for text, url in refs:
        add(
            escape(text)
            + '<br/><link href="'
            + url
            + '" color="#246b8e">'
            + escape(url)
            + "</link>",
            "TeamSmall",
        )
    add(
        "HLS uses conservative global coefficients rather than refitting a poorly constrained local model for each image. Its engineering burden and failure modes therefore differ from the experimental drone fits. Published directional/time-series benefits cannot be assumed to imply an improvement in this project’s PFT classification scores."
    )
    table(
        [
            ["Evidence location inside study folder", "Contents"],
            [
                "analysis_design.json",
                "Frozen new-run retrospective endpoints and contrasts; not preregistered.",
            ],
            [
                "hls/",
                "Same-cell angle metadata, c-factors, inverse reconstruction, quantization bounds, compact patch spectra.",
            ],
            [
                "aop/",
                "Paired plant-flight and identity-year curves; source support and nominal same-ground repeat-view summaries.",
            ],
            [
                "aop-control/",
                "Spatial holdout identity, fit model, full normal QA, held-block angular and dispersion diagnostics.",
            ],
            [
                "drone/",
                "Both frozen variants, matched translated polygon spectra, coverage and magnitudes; source/model/registry hashes.",
            ],
            [
                "statistics/",
                "All predictions, fold memberships, recalls, recognition changes, NPC and separation-change results, including unsupported cases.",
            ],
            [
                "summary/",
                "Human-readable tables, SVG/PNG figures, QA support audit and source-hash manifest.",
            ],
        ],
        [233, WIDTH - 233],
    )
    add(
        "Prepared with OpenAI Codex. This analysis estimates outcomes for the supplied local datasets and the specified classifier/protocol. It does not estimate the prevalence of BRDF errors in the wider community or scientist labour expenditure. The separate Landsat team-validation PDFs provide the pixel-by-pixel label review needed before stronger purity claims.",
        "TeamSmall",
    )

    def footer(canvas, doc):
        canvas.setStrokeColor(TEAL)
        canvas.line(40, 34, 572, 34)
        canvas.setFont("Team", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(
            40, 22, "SpectralBridge • BRDF benefit audit • 20 November 2026"
        )
        canvas.drawRightString(572, 22, str(doc.page))

    doc = SimpleDocTemplate(
        str(PDF),
        pagesize=(612, 792),
        leftMargin=41.4,
        rightMargin=41.4,
        topMargin=38,
        bottomMargin=45,
        title="BRDF benefit across AOP, drone and Landsat",
        author="SpectralBridge team / OpenAI Codex",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    from pypdf import PdfReader

    reader = PdfReader(PDF)
    provenance = dict(
        pdf_sha256=sha(PDF),
        pages=len(reader.pages),
        builder_sha256=sha(Path(__file__)),
        source_hashes={
            str(p.relative_to(ROOT)): sha(p)
            for p in BASE.rglob("*")
            if p.is_file()
            and p.name != "pdf_quality_checks.json"
            and p.suffix in [".csv", ".json", ".png", ".svg"]
        },
        summary="Retrospective paired effects; no production data/model modifications",
        created="2026-11-20",
    )
    PDF.with_suffix(".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    print(PDF, len(reader.pages), "pages")


if __name__ == "__main__":
    run()
