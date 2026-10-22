"""Curate sealed P145 outputs into a researcher briefing; no model fitting."""

import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
SOURCE = ROOT / "provenance/endmember-quality/2026-10-22/ies-comparison-v1"
OUT = ROOT / "output/pdf/ies_endmember_update/SpectralBridge_New_Endmember_Analysis.pdf"
FONT = next(ROOT.glob(".venv/lib/python*/site-packages/matplotlib/mpl-data/fonts/ttf"))
for name, file in [("Body", "DejaVuSans.ttf"), ("Body-Bold", "DejaVuSans-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(FONT / file)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold")
STYLE = ParagraphStyle(
    "body", fontName="Body", fontSize=10.3, leading=15, textColor="#183440"
)
CAP = ParagraphStyle(
    "caption", parent=STYLE, fontSize=8.6, leading=12, textColor="#526771"
)
PAGES = [
    (
        "New endmembers: stronger candidates",
        "Decision briefing | 22 October 2026",
        None,
        [
            (
                "The result",
                "The new 501-reference library improves recovery of known synthetic mixture fractions for both ridge and exhaustive MESMA. Ridge has lower fraction error in the tested configurations. Neither method has yet been validated against independent measured field cover.",
            ),
            (
                "What to take forward",
                "Use the new library for a controlled validation pilot, with ridge as the leading candidate and MESMA as a comparison. Keep both category options until the research question is settled: the revised scheme merges herbaceous vegetation with woody shrubs and separates bare/rock from dead material.",
            ),
            (
                "Headline numbers",
                "With original categories held fixed, common-component fraction RMSE falls from 0.283 to 0.258 for ridge and from 0.351 to 0.313 for MESMA. With the new references and revised categories, ridge scores 0.260 and MESMA 0.295. Lower is better; these are errors, not percentages of correct predictions.",
            ),
            (
                "How to read this report",
                "Pages 2-3 describe the library and observed spectral coverage. Pages 4-6 explain fraction recovery, uncertainty and category weaknesses. Pages 7-8 examine controls and the validation decision. All results come from the completed internal comparison; no models were refitted for this report.",
            ),
        ],
    ),
    (
        "What changed in the library?",
        "Separate reference selection from category definition",
        "01_reference_support",
        [
            (
                "Understand the figure",
                "Bars count selected spectra in six source groups before the groups are merged into either five-category scheme. Multiple spectra can come from the same polygon; bars do not count independent plants.",
            ),
            (
                "A fair comparison",
                "The new library has 501 references from 324 polygon IDs. The previous library had 603; 11 mixed/unspecified-background references cannot be assigned revised bare/dead labels. The factorial comparison therefore uses 592 previous references from 359 IDs, with identical membership under each label scheme.",
            ),
            (
                "Two different ecological questions",
                "Original: deciduous, evergreen, herbaceous, non-vegetated & dead, woody shrub. Revised: deciduous, evergreen, herbaceous + woody shrub, bare/rock, dead. Revised labels cannot recover herbaceous and shrub abundance separately. Only 27 new dead references represent 21 polygon IDs.",
            ),
        ],
    ),
    (
        "Closer spectral coverage is not better recognition",
        "Observed polygon spectra | internal diagnostic",
        "02_coverage_and_recognition",
        [
            (
                "Understand the figure",
                "Lower same-category spectral distance means references lie closer to observed targets. Higher recall means the nearest reference more often belongs to the target category. Those are different questions.",
            ),
            (
                "What we learned",
                "Under original labels, macro same-category distance improves from 0.01509 to 0.01218, but mean category recall falls from 59.3% to 56.0%. Improved spectral coverage does not establish improved classification or abundance accuracy.",
            ),
            (
                "What was tested",
                "Both libraries see the same 3,904 polygon/year curves from 3,021 IDs, excluding all 540 IDs selected by either library. ID weighting prevents repeated years from dominating within a category. Selection used the whole archive, so this is not selection-blind validation. Recall here is nearest-reference recognition, not fraction accuracy.",
            ),
        ],
    ),
    (
        "Ridge recovers fractions better in this benchmark",
        "Identical synthetic targets | four common components",
        "03_fraction_recovery",
        [
            (
                "Understand the figure",
                "Both five-category outputs are reduced to the same four components: deciduous, evergreen, herbaceous + shrub, and background. This makes cross-category-scheme scores comparable. The dashed prior predicts training-design fractions without using spectra.",
            ),
            (
                "What 0.260 means",
                "Fraction RMSE is the square root of the mean squared prediction error over all target-component pairs. An RMSE of 0.260 is about 26 percentage points of fraction error under this scoring rule. It is not 74% accuracy, not a 26% failure rate, not mean absolute error, and not a confidence interval. For example, true cover of 40% and estimated cover of 65% gives one error of 25 percentage points; this example is illustrative, not an observed case.",
            ),
            (
                "Controlled mixtures, not measured cover",
                "The 568 targets share 48 generating polygon IDs in eight disjoint six-parent bundles. Each bundle has 6 pure, 45 pair and 20 equal-third triple recipes. Those known algebraic fractions do not establish field canopy or ground-cover fractions.",
            ),
        ],
    ),
    (
        "What caused the improvement?",
        "Paired comparisons isolate selection and label effects",
        "04_paired_effects",
        [
            (
                "Understand the figure",
                "Negative change means lower error after replacement. Intervals resample the same eight parent bundles in 1,999 paired draws. All four selection comparisons favor the new references in these conditional ranges.",
            ),
            (
                "References versus labels",
                "New references improve both methods with labels held fixed. With the new references fixed, revised labels improve MESMA common-component RMSE from 0.313 to 0.295. MESMA now permits bare and dead together, but no longer permits separate herbaceous and shrub categories: its admissible model family changes.",
            ),
            (
                "A subtle ridge result",
                "All four primary ridge models select penalty 10. Before nonnegative sum-one projection, shared-component predictions are identical across label schemes to numerical precision. The small 0.258 versus 0.260 difference comes from applying constraints in different five-category spaces. Relabelling did not add shared linear spectral information.",
            ),
            (
                "Limits of the intervals",
                "These ranges describe sensitivity to eight sampled bundles, conditional on fixed selections and models. They are not population guarantees or independent geographic validation.",
            ),
        ],
    ),
    (
        "The pooled score hides category weaknesses",
        "Native five-category fraction errors",
        "05_category_errors",
        [
            (
                "Understand the figure",
                "Compare reference selections and methods within each label panel. The panels contain different ecological targets, so their five-category errors are not directly interchangeable. The prior is a no-spectrum baseline.",
            ),
            (
                "Dead material needs attention",
                "For the new revised library, dead fraction RMSE is 0.259 for ridge and 0.292 for MESMA; the no-spectrum prior is 0.278. MESMA is worse than that baseline for this component in this benchmark. Lower pooled error does not validate the new dead/bare split.",
            ),
            (
                "How the methods work",
                "Ridge learns seven-band-to-fraction coefficients with a penalty and parent-disjoint tuning; outputs are projected to nonnegative fractions summing to one. Exhaustive MESMA reconstructs each target using every permitted one-to-three-category model, with one reference per active category and all simplex faces. The new revised search evaluates 8,260,481 models per target. Better spectral reconstruction alone does not ensure correct composition.",
            ),
        ],
    ),
    (
        "How much depends on selection size?",
        "Controls and identifiability qualify the headline gain",
        "07_capacity_control",
        [
            (
                "Understand the figure",
                "Five draw pairs match reference counts within all six source groups: 476 references per library per draw. These are ridge controls, not five independent field experiments.",
            ),
            (
                "What remains after matching",
                "With original labels, mean ridge error is 0.270 for previous references and 0.264 for new references, with new references better in 5/5 draws. With revised labels the means are 0.273 and 0.266, better in 3/5 draws. The smaller gain shows that library composition and capacity matter. Parent identities and site distributions remain unmatched; this does not prove intrinsic IES algorithm superiority.",
            ),
            (
                "Why composition can remain ambiguous",
                "Verified alternative cross-category reconstructions exist for 25.9% of new revised reference spectra (130/501). This is not a failure probability for targets. The certificate family is broader than three-category MESMA, and absent certificates do not prove uniqueness. Different compositions can fit very similar spectra.",
            ),
        ],
    ),
    (
        "Ready for a validation pilot",
        "Freeze the candidate, then measure real-world fraction error",
        "06_domain_patterns",
        [
            (
                "Understand the figure",
                "Site/year scores use global fixed reference libraries that include those sites. There are only two parent bundles per cell. These are not held-site tests; three sites and four cells confound geography with year.",
            ),
            (
                "Decision for coworkers",
                "Proceed with ridge as the stronger tested fraction-estimation candidate and MESMA as a comparator. Choose labels to match the ecological question. Report outputs as experimental spectral mixture fractions until their relationship to the intended field abundance measure is established.",
            ),
            (
                "Next decisive validation",
                "Freeze library, category maps and model settings. Obtain independent contemporaneous measured fractional cover with matched spatial footprints; verify reflectance units and material purity. Score category-specific RMSE, bias and absolute error, compare against a no-spectrum baseline, and examine site/year transfer with appropriate spatial grouping.",
            ),
            (
                "Evidence and boundaries",
                "OLI bands are derived from NEON, not independent Landsat observations. Polygon labels do not certify purity, and retrospective annotations may not match imagery year. The source packet is provenance/endmember-quality/2026-10-22/ies-comparison-v1/: protocol.json, input_audit.json, tables/, models/, validation.json and IES_COMPARISON_REPORT.html. These targets differ from the October 19 experiment; do not directly compare their scores. Original data and sealed analysis outputs were preserved.",
            ),
        ],
    ),
]

OUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUT), pagesize=(612, 792))
c.setTitle("SpectralBridge | New endmember analysis")
c.setAuthor("SpectralBridge research team; prepared with OpenAI Codex")
boxes = []
for n, (title, sub, fig, sections) in enumerate(PAGES, 1):
    c.setFillColorRGB(0.03, 0.42, 0.41)
    c.rect(0, 782, 612, 10, fill=1, stroke=0)
    c.setFillColorRGB(0.09, 0.20, 0.25)
    c.setFont("Body-Bold", 19)
    c.drawString(38, 744, title)
    c.setFont("Body", 10)
    c.drawString(38, 721, sub)
    y = 697
    if fig:
        img = SOURCE / "figures" / f"{fig}.png"
        w, h = Image.open(img).size
        scale = min(536 / w, 270 / h)
        iw, ih = w * scale, h * scale
        c.drawImage(str(img), 38 + (536 - iw) / 2, y - ih, width=iw, height=ih)
        y -= ih + 15
    for heading, body in sections:
        style = STYLE
        p = Paragraph("<b>" + escape(heading) + "</b><br/>" + escape(body), style)
        _, h = p.wrap(536, 700)
        assert y - h >= 48, (n, heading, y, h)
        p.drawOn(c, 38, y - h)
        boxes.append({"page": n, "heading": heading, "bottom": y - h, "height": h})
        y -= h + 12
    c.setStrokeColorRGB(0.8, 0.85, 0.85)
    c.line(38, 37, 574, 37)
    c.setFont("Body", 8)
    c.setFillColorRGB(0.35, 0.43, 0.46)
    c.drawString(
        38,
        23,
        "SpectralBridge | Internal synthetic readiness assessment | 22 October 2026",
    )
    c.drawRightString(574, 23, f"{n} / {len(PAGES)}")
    c.showPage()
c.save()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


sources = [
    SOURCE / "IES_COMPARISON_REPORT.md",
    SOURCE / "summary.json",
    SOURCE / "protocol.json",
    SOURCE / "figure_manifest.json",
]
sources += [SOURCE / "figures" / f"{p[2]}.png" for p in PAGES if p[2]]
(BASE / "report_manifest.json").write_text(
    json.dumps(
        {
            "pdf": str(OUT.relative_to(ROOT)),
            "pdf_sha256": sha(OUT),
            "pages": len(PAGES),
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources},
            "layout_boxes": boxes,
        },
        indent=2,
    )
    + "\n"
)
print(OUT)
