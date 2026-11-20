"""Create a four-page scientific report from completed, hash-verified PFT results.

Run from repo root in a Python environment with reportlab and pypdf:
    python examples/build_drone_mask_pft_pdf_report.py
No analysis is rerun or modified. The accompanying provenance JSON identifies
all source tables, analysis policy and plot hashes used in this report.
"""

import csv
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/pft-mask-comparison"
)
OUT = ROOT / "output/pdf/drone_shade_mask_pft_comparison_report.pdf"
NAVY = colors.HexColor("#263e56")
TEAL = colors.HexColor("#237d83")
INK = colors.HexColor("#233444")
PALE = colors.HexColor("#edf3f4")
GRAY = colors.HexColor("#66747e")
LINE = colors.HexColor("#dce5e8")
WIDTH = 524
STYLES = getSampleStyleSheet()
STYLES.add(
    ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=NAVY,
        spaceAfter=10,
    )
)
STYLES.add(
    ParagraphStyle(
        name="ReportH",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=NAVY,
        spaceBefore=11,
        spaceAfter=6,
    )
)
STYLES.add(
    ParagraphStyle(
        name="ReportBody",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=INK,
        spaceAfter=7,
    )
)
STYLES.add(
    ParagraphStyle(
        name="ReportSmall",
        parent=STYLES["ReportBody"],
        fontSize=8.1,
        leading=11,
        spaceAfter=5,
    )
)
STYLES.add(
    ParagraphStyle(
        name="ReportCell",
        parent=STYLES["ReportBody"],
        fontSize=8.3,
        leading=10.5,
        spaceAfter=0,
    )
)
STYLES.add(
    ParagraphStyle(
        name="ReportHeadCell",
        parent=STYLES["ReportCell"],
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
)
STYLES.add(
    ParagraphStyle(
        name="ReportCode",
        fontName="Courier",
        fontSize=7.7,
        leading=11,
        textColor=INK,
        spaceAfter=6,
    )
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    with (SOURCE / name).open() as stream:
        return list(csv.DictReader(stream))


def P(text, style="ReportBody"):
    return Paragraph(text, STYLES[style])


def H(text):
    return P(text, "ReportH")


def table(rows, widths):
    cells = [
        [P(escape(str(x)), "ReportHeadCell" if i == 0 else "ReportCell") for x in row]
        for i, row in enumerate(rows)
    ]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, NAVY),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, LINE),
            ]
        )
    )
    return t


def footer(canvas, doc):
    canvas.setStrokeColor(LINE)
    canvas.line(44, 756, 568, 756)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(44, 765, "SPECTRALBRIDGE  |  CALIBRATION-SITE PFT COMPARISON")
    canvas.drawString(44, 25, "19 November 2026  |  Experimental research results")
    canvas.drawRightString(568, 25, f"{doc.page} / 4")


def run():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for manifest_name in ["manifest.json", "summary_manifest.json"]:
        manifest = json.loads((SOURCE / manifest_name).read_text())
        inputs[manifest_name] = sha(SOURCE / manifest_name)
        for name, digest in manifest["outputs"].items():
            if sha(SOURCE / name) != digest:
                raise ValueError("Changed verified source: " + name)
            inputs[name] = digest
    inputs["analysis_policy.json"] = sha(SOURCE / "analysis_policy.json")
    accuracy = [
        x
        for x in read("identifiability_change.csv")
        if x["target"] == "Landsat_9_OLI-2"
    ]
    effects = [
        x
        for x in read("separability_change.csv")
        if x["target"] == "Landsat_9_OLI-2" and x["population"] == "shared_pixels"
    ]
    class_rows = [
        x
        for x in read("class_summary.csv")
        if x["target"] == "Landsat_9_OLI-2" and x["population"] == "shared_pixels"
    ]
    categories = [
        "Deciduous",
        "Evergreen",
        "Herbaceous",
        "Woody shrub",
        "Non-vegetated & dead",
    ]
    assert len(accuracy) == 4 and len(effects) == 10 and len(class_rows) == 10
    story = []
    # PAGE 1 - Results first, including class-specific failures.
    story += [
        P("Does a 10% shade mask reduce PFT information?", "ReportTitle"),
        P(
            "Unmasked null versus conservative shade masking, compared after MicaSense-to-Landsat-like translation. Primary results use OLI-2-like spectra; OLI-like sensitivity results agree to the displayed precision."
        ),
        table(
            [
                ["Main finding"],
                [
                    "No consistent reduction was detected. Identifiability changes are small and mixed; separation decreases for some PFT pairs and increases for others. No paired loss test survives the planned multiple-comparison adjustment. This does not demonstrate equivalence."
                ],
            ],
            [WIDTH],
        ),
        H("1. Identifiability: balanced accuracy"),
    ]
    rows = [
        [
            "Pixels summarized per polygon",
            "Held-out unit",
            "Unmasked",
            "10% mask",
            "Change (pp)",
        ]
    ]
    for r in accuracy:
        rows.append(
            [
                "Shared exact pixels"
                if r["population"] == "shared_pixels"
                else "Each batch retained pixels",
                "Site" if r["scheme"] == "held_out_site" else "Polygon",
                f"{float(r['ba_null']):.1%}",
                f"{float(r['ba_mask10']):.1%}",
                f"{100 * float(r['delta_ba']):+.2f}",
            ]
        )
    story += [
        table(rows, [171, 83, 80, 80, 110]),
        Spacer(1, 7),
        P(
            "Balanced accuracy is the mean of the five PFT recalls from pooled out-of-fold predictions. It is not overall accuracy or an equal-site average. The primary comparison is held-site recognition on shared pixels: <b>36.4% to 38.1%</b>."
        ),
        H("2. Per-PFT recall on shared pixels"),
    ]
    rows = [["PFT", "Polygons", "Held-polygon\nNull / 10%", "Held-site\nNull / 10%"]]
    for category in categories:
        a = next(
            x
            for x in class_rows
            if x["category"] == category and x["arm"] == "unmasked"
        )
        b = next(
            x for x in class_rows if x["category"] == category and x["arm"] == "mask10"
        )
        rows.append(
            [
                category,
                a["n_polygons"],
                f"{float(a['unseen_polygon_recall']):.1%} / {float(b['unseen_polygon_recall']):.1%}",
                f"{float(a['held_out_site_recall']):.1%} / {float(b['held_out_site_recall']):.1%}",
            ]
        )
    story += [
        table(rows, [178, 62, 142, 142]),
        Spacer(1, 7),
        P(
            "<b>Recognition remains limited.</b> Woody-shrub held-site recall is 0% in both batches. A modest increase in mean accuracy does not resolve this class-specific transfer failure."
        ),
        P(
            "Scope: 300 matched polygons across Gordon, Goldhill and Ruby; five translated bands; flight identifiers dated 14 August 2023. These are experimental corrected drone products, not actual Landsat observations.",
            "ReportSmall",
        ),
        PageBreak(),
    ]
    # PAGE 2 - Plot and pairwise effect values.
    story += [
        P("Separability and the direction of change", "ReportTitle"),
        Image(
            str(SOURCE / "mask_pft_comparison.png"),
            width=WIDTH,
            height=WIDTH * 5.7 / 13,
        ),
        P(
            "Figure 1. Point estimates, with the same polygon identities in each batch. Right panel: site-adjusted standardized RMS spectral contrasts on shared pixels; larger values indicate larger standardized PFT differences. The figure does not show confidence intervals.",
            "ReportSmall",
        ),
        H("3. Shared-pixel separation effects"),
    ]
    rows = [
        [
            "PFT pair",
            "n A / B",
            "Sites",
            "Null",
            "10%",
            "Change",
            "Adjusted p\nfor loss",
        ]
    ]
    short = {"Non-vegetated & dead": "Non-veg/dead", "Woody shrub": "Shrub"}
    for r in effects:
        pair = (
            short.get(r["first"], r["first"])
            + " / "
            + short.get(r["second"], r["second"])
        )
        rows.append(
            [
                pair,
                f"{r['n_first']} / {r['n_second']}",
                r["sites"],
                f"{float(r['effect_null']):.3f}",
                f"{float(r['effect_mask10']):.3f}",
                f"{float(r['effect_delta']):+.3f}",
                f"{float(r['p_loss_holm']):.3f}",
            ]
        )
    story += [
        table(rows, [142, 58, 40, 55, 55, 60, 114]),
        Spacer(1, 6),
        P(
            "Changes are 10% minus null. Three of ten effects decrease; seven increase. Adjusted p-values use exploratory whole-polygon paired swaps with Holm correction across 40 pair comparisons. The smallest adjusted loss p-value is 0.052. Whole-site swaps are coarser and do not establish a loss.",
            "ReportSmall",
        ),
        P(
            "<b>Significance counts:</b> Within each ten-pair family, NPC supports 8/10 pairs in the null and 6/10 in the 10% batch. With joint Holm control across all 80 tested contrasts, both support 5/10. The same counts occur in the retained-pixel analysis. Counts of significant pairs are not themselves a test of a masking effect.",
            "ReportSmall",
        ),
        PageBreak(),
    ]
    # PAGE 3 - Auditable statistical design.
    story += [
        P("Methods and statistical interpretation", "ReportTitle"),
        H("4. Cohort and pixel populations"),
        P(
            "We reused the original calibration-site researcher PFT labels and polygon pixel indices. Index coordinates match the translated grids exactly, and no indexed polygon pixels overlap. Of 302 polygon footprints, two have no complete five-band valid pixels in either batch; neither is a mask-only dropout. The matched cohort contains 300 polygons: 12 Deciduous, 176 Evergreen, 46 Herbaceous, 40 Woody shrub and 26 Non-vegetated/dead."
        ),
        P(
            "<b>Shared pixels (primary):</b> Each polygon median uses the same exact pixel intersection where all five bands are finite in both batches. <b>Retained pixels (sensitivity):</b> Each batch uses its own complete five-band pixels, retaining the same polygon IDs. Labelled footprints contain 195,849 valid null pixels, 189,178 valid masked pixels and 188,336 shared pixels. These are labelled-footprint counts, not scene-wide retention."
        ),
        H("5. Separability and paired changes"),
        P(
            "Five-band polygon medians are decoded to fractional reflectance; spectra are not divided by their band sum. Category pairs are restricted to sites containing both classes. The existing site-blocked NPC kernel permutes complete polygon labels jointly across bands, using 9,999 draws and equal discrete band weights. NPC combines maximum-band and integrated standardized contrasts. We report Holm control within each ten-pair family and jointly across 80 contrasts: two sensors, two pixel populations, two batches and ten pairs."
        ),
        P(
            "To evaluate the hypothesis directly, we compare site-adjusted standardized RMS effects using paired arm swaps, with all bands moving together within a polygon. Loss is defined as masked minus null less than zero. These 40 pairwise change tests receive Holm adjustment. Exact whole-site swaps are also reported. Polygon-level arm exchangeability is an assumption, not evidence that masking was randomized."
        ),
        H("6. Identifiability and paired changes"),
        P(
            "A training-only StandardScaler precedes balanced logistic regression with fixed C=1. Five stratified folds hold out whole polygons; three leave-one-site-out folds evaluate classifier transfer. Both batches use identical identities and folds. Every held-out class occurs in training. No features or hyperparameters are selected using test data. The archive contains 4,800 out-of-fold predictions across sensors, populations, batches and evaluation schemes."
        ),
        P(
            "Balanced-accuracy changes are tested by paired correctness swaps with equal true-class weights. Holm adjustment covers eight sensor/population/evaluation comparisons. Exact whole-site swaps provide a dependence-aware sensitivity. With three sites there are only eight site-swap assignments, so the smallest possible one-sided p-value is 0.125. No adjusted loss test is significant; this limited resolution cannot establish equivalence."
        ),
        H("7. Computational verification"),
        P(
            "Input rasters and polygon indices are hash-verified. We checked paired identities, identical fold assignments, train/test identity separation, class support and source-grid alignment. Fifteen focused regression/kernel tests passed, and a completed-run restart reused hash-verified outputs. No Figure 4 or datastore raster was changed."
        ),
        PageBreak(),
    ]
    # PAGE 4 - What the comparison does not establish and how to reproduce it.
    story += [
        P("Limits, provenance and reuse", "ReportTitle"),
        H("8. Interpretation boundaries"),
        P(
            "<b>Refitting is part of the contrast.</b> The null uses baseline unmasked SCS+C and BRDF fits. The 10% batch uses fits estimated after brightness exclusion. Shared-pixel differences therefore include changed correction parameters; the retained-pixel comparison additionally includes changed pixel composition. This is not a mask-only causal experiment."
        ),
        P(
            "<b>The null remains a failed-QA experiment at Ruby.</b> Its native 650 and 668 nm BRDF reference predictions fail the uncertainty criterion. The null intentionally applies finite diagnostic coefficient estimates while preserving INVALID status and positive numerical-denominator checks. The 10% refit passes all ten native bands, but Ruby 668 nm passes narrowly. Neither status independently establishes physical accuracy."
        ),
        P(
            "<b>Calibration and domain scope remain limited.</b> Both batches inherit conditional, unverified radiometry. Nearby polygons can remain spatially dependent, and overlapping training folds can correlate predictions. Held-site evaluation tests classifier transfer after site-specific correction; it does not test an entirely frozen correction pipeline at a new site. Three calibration sites and a single nominal acquisition date cannot establish broad ecological or geographic generalization."
        ),
        H("9. Reproduce from the repository root"),
        P(
            "Analysis and readable-summary commands (project environment):",
            "ReportSmall",
        ),
        P(
            ".venv/bin/python examples/compare_drone_mask_pft_information.py<br/>.venv/bin/python examples/summarize_drone_mask_pft_information.py",
            "ReportCode",
        ),
        P("PDF generation requires ReportLab and pypdf:", "ReportSmall"),
        P("python examples/build_drone_mask_pft_pdf_report.py", "ReportCode"),
        P(
            "Completed analysis outputs are reused only when input, code and output hashes match. The policy was frozen before examining test results. In CSV files the null batch is labelled <b>unmasked</b>, avoiding the missing-value interpretation of the literal string null.",
            "ReportSmall",
        ),
        H("10. Source tables and data access"),
    ]
    rows = [
        ["File in the comparison provenance folder", "Purpose"],
        [
            "analysis_policy.json; manifest.json",
            "Frozen design, source/code hashes and software versions",
        ],
        [
            "polygon_spectra.csv; polygon_coverage.csv",
            "Polygon medians and retained-pixel counts",
        ],
        [
            "separability.csv; separability_change.csv",
            "NPC evidence and paired separation effects",
        ],
        [
            "held_out_predictions.csv; fold_memberships.csv",
            "Auditable predictions and train/test memberships",
        ],
        [
            "identifiability_change.csv; class_summary.csv",
            "Paired accuracy changes and per-PFT recalls",
        ],
    ]
    story += [
        table(rows, [286, 238]),
        Spacer(1, 7),
        P(
            "Repository folder: provenance/drone-calibration-translation/<br/>2026-11-19/pft-mask-comparison/",
            "ReportCode",
        ),
    ]
    remote = "https://de.cyverse.org/data/ds/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/"
    story += [
        P(
            f'Datastore: <link href="{remote}gordon_goldhill_ruby_micasense_landsat_translations_20261119_v1" color="#237d83">10% translated batch</link> | <link href="{remote}gordon_goldhill_ruby_micasense_landsat_unmasked_null_20261119_v1" color="#237d83">Unmasked translated null</link>. Access requires the appropriate CyVerse permissions. Both use stored fraction x1000 (100% reflectance = 1000), with header decoder 0.001.',
            "ReportSmall",
        ),
        P(
            "Report date: 19 November 2026. Numerical source: completed SpectralBridge calibration-site comparison. This PDF is accompanied by a machine-readable report provenance record containing source hashes.",
            "ReportSmall",
        ),
    ]
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        rightMargin=44,
        leftMargin=44,
        topMargin=48,
        bottomMargin=42,
        title="PFT information after shade masking: unmasked null versus 10%",
        author="SpectralBridge research workflow",
        subject="Calibration-site translated spectra: separability and identifiability",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(str(OUT))
    assert len(reader.pages) == 4, f"Unexpected pagination: {len(reader.pages)}"
    text = "\n".join(page.extract_text() for page in reader.pages)
    for token in [
        "36.4%",
        "38.1%",
        "61.5%",
        "60.5%",
        "0.052",
        "0.125",
        "188,336",
        "0%",
    ]:
        assert token in text, token
    OUT.with_suffix(".provenance.json").write_text(
        json.dumps(
            dict(
                report=str(OUT.relative_to(ROOT)),
                sha256=sha(OUT),
                pages=4,
                source_folder=str(SOURCE.relative_to(ROOT)),
                sources=inputs,
                builder_sha256=sha(Path(__file__)),
            ),
            indent=2,
        )
        + "\n"
    )
    print(OUT)


if __name__ == "__main__":
    run()
