"""Compose the collaborator briefing from the presentation manifest; never fit models.

Run build_figures.py first. Requires ReportLab and Pillow; QA uses pypdf/pdfplumber.
Narrative, display values and page-to-source links are saved in report_content.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
OUTPUT = (
    ROOT / "output/pdf/pft_scientific_update/SpectralBridge_PFT_Scientific_Update.pdf"
)
INK = "#183440"
MUTED = "#566C76"
TEAL = "#007C76"
PAPER = "#F8FAF9"
WIDTH, HEIGHT = 612, 792
MARGIN = 42
CONTENT = WIDTH - 2 * MARGIN
BOXES = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure_fonts(font_dir=None):
    candidates = [Path(font_dir)] if font_dir else []
    candidates += list(
        ROOT.glob(".venv/lib/python*/site-packages/matplotlib/mpl-data/fonts/ttf")
    )
    candidates += [Path("/usr/share/fonts/truetype/dejavu")]
    try:
        import matplotlib

        candidates.insert(0, Path(matplotlib.get_data_path()) / "fonts/ttf")
    except ImportError:
        pass
    folder = next((p for p in candidates if (p / "DejaVuSans.ttf").exists()), None)
    if folder is None:
        raise FileNotFoundError(
            "Provide --font-dir containing DejaVuSans.ttf and DejaVuSans-Bold.ttf"
        )
    for name, file in [
        ("Brief", "DejaVuSans.ttf"),
        ("Brief-Bold", "DejaVuSans-Bold.ttf"),
    ]:
        pdfmetrics.registerFont(TTFont(name, str(folder / file)))
    pdfmetrics.registerFontFamily("Brief", normal="Brief", bold="Brief-Bold")
    return {
        file: sha(folder / file) for file in ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]
    }


def paragraph(
    c, text, x, top, width=CONTENT, size=11, leading=None, color=INK, bold=False
):
    style = ParagraphStyle(
        "brief",
        fontName="Brief-Bold" if bold else "Brief",
        fontSize=size,
        leading=leading or size * 1.38,
        textColor=colors.HexColor(color),
        splitLongWords=False,
    )
    p = Paragraph(text, style)
    _, h = p.wrap(width, 1000)
    assert x >= 18 and x + width <= WIDTH - 18 and top - h >= 38, (text, x, top, h)
    p.drawOn(c, x, top - h)
    BOXES.append(
        {
            "page": c.getPageNumber(),
            "kind": "text",
            "x": x,
            "top": top,
            "width": width,
            "height": h,
            "text": text,
        }
    )
    return top - h


def shell(c, page, section, git):
    c.setFillColor(colors.white)
    c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(TEAL))
    c.rect(MARGIN, 752, 26, 4, fill=1, stroke=0)
    paragraph(
        c,
        "SPECTRALBRIDGE  /  RESEARCHER PFT BRIEFING",
        MARGIN + 36,
        759,
        width=CONTENT - 36,
        size=8,
        bold=True,
        color=MUTED,
    )
    c.setStrokeColor(colors.HexColor("#D9E3E4"))
    c.line(MARGIN, 38, WIDTH - MARGIN, 38)
    c.setFont("Brief", 7.3)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(
        MARGIN,
        29,
        f"22 OCT 2026  |  Evidence through 19 OCT 2026  |  Source {git[:10]}",
    )
    c.drawRightString(WIDTH - MARGIN, 29, f"{page:02d} / 11")
    if section:
        paragraph(c, section.upper(), MARGIN, 724, size=9.5, bold=True, color=TEAL)


def takeaway(c, text, top=140, height=77):
    c.setFillColor(colors.HexColor("#EDF4F1"))
    c.roundRect(MARGIN, top - height, CONTENT, height, 7, fill=1, stroke=0)
    y = paragraph(
        c,
        "WHAT THIS TELLS US",
        MARGIN + 14,
        top - 11,
        width=CONTENT - 28,
        size=8.7,
        bold=True,
        color=TEAL,
    )
    bottom = paragraph(
        c, text, MARGIN + 14, y - 6, width=CONTENT - 28, size=10.5, leading=14
    )
    assert bottom >= top - height + 8, ("Takeaway overflow", text, bottom)


def narrative(m):
    def p(key):
        return f"{100 * m[key]:.1f}%"

    def r(key):
        return f"{m[key]:.3f}"

    return [
        dict(
            figure=1,
            section="1 / Separability",
            title="Each PFT contains a wide range of spectra",
            subtitle="Begin with the observations: faint lines are polygon/year spectra; bold lines are category medians.",
            caption="<b>Figure 1.</b> All 4,807 corrected annual curves are shown, with gaps at excluded or unsupported wavelengths. The same vertical scale makes group differences and within-group spread visible. Transparency is a qualitative view of overlap, not a probability density. Repeated annual curves do not add independent plants.",
            takeaway="The category medians differ, but no median represents every observation. The next test asks whether group differences persist within the sampled site/year cohorts.",
            source_label="Corrected compact polygon/year library; category support and foundation, 16 Oct.",
            claims=["polygon_year_spectra", "NEON_coordinates", "polygon_GlobalIDs"],
            figure_top=582,
            max_height=350,
        ),
        dict(
            figure=2,
            section="1 / Separability",
            title="Every pair differs, but separation is unequal",
            subtitle="Whole-spectrum tests compare categories within the same site/year setting, rather than mixing regions together.",
            caption=f"<b>Figure 2.</b> Each symbol is one of four cohorts; connecting lines span those cohort effects, not confidence intervals. All {m['pairs']} pairs were supported in all four cohorts ({m['supported_contrasts']} contrasts) in both NEON and synthetic OLI. The largest Holm-adjusted NEON p-value was {m['largest_adjusted_p']:.3f}. Blocked permutations restrict label exchanges by acquisition history.",
            takeaway="Background/dead contrasts tend to be large; deciduous versus woody shrub is among the smaller contrasts. Statistical difference alone does not establish that individual spectra can be labelled reliably.",
            source_label="Whole-spectrum separability and pair evidence tables, 16 Oct.",
            claims=["pairs", "supported_contrasts", "largest_adjusted_p"],
            figure_top=582,
            max_height=350,
        ),
        dict(
            figure=3,
            section="1 / Separability",
            title="Different PFT pairs emphasize different wavelengths",
            subtitle="The useful signal extends across broad spectral regions, and its strength depends on the categories being compared.",
            caption="<b>Figure 3.</b> Darker cells indicate a larger absolute matched effect, summarized as the median across four existing cohorts at each wavelength. Gray gaps are omitted coordinates. This display removes the direction of the contrast and is not a new hypothesis test or an optimized band selection.",
            takeaway="Background/dead contrasts span broad regions, while deciduous/shrub differences are weaker over much of the spectrum. These patterns motivate testing full spectra against broad sensor bands on unknown observations.",
            source_label="Cohort wavelength inference, 15 Oct.; cohort/pair evidence, 16 Oct.",
            claims=["NEON_coordinates", "site_year_cells"],
            figure_top=582,
            max_height=350,
        ),
        dict(
            figure=4,
            section="2 / Identifiability",
            title="Recognition weakens when a site is held out",
            subtitle="Here the target spectrum is withheld from fitting: can the model recover its researcher-assigned category?",
            caption=f"<b>Figure 4.</b> Balanced accuracy is the mean recall of the five categories: {p('NEON_plant')} for unseen polygons and {p('NEON_site')} for held-out sites with NEON, versus {p('Synthetic OLI_plant')} and {p('Synthetic OLI_site')} with synthetic OLI. White dots are outer-fold scores, not confidence intervals. Equal-category chance is 20%.",
            takeaway="Hyperspectral information improves recognition, but the held-site result is weaker and based on only three sites. OLI here is convolved from the same NEON reference; it is not an independent Landsat validation.",
            source_label="Complementary feature performance, 15 Oct.; original held-polygon/site fits.",
            claims=[
                "NEON_plant",
                "NEON_site",
                "Synthetic OLI_plant",
                "Synthetic OLI_site",
                "sites",
            ],
            figure_top=582,
            max_height=350,
        ),
        dict(
            figure=5,
            section="2 / Identifiability",
            title="Woody shrub is the main recognition weakness",
            subtitle="Read each row as the fate of a researcher-labelled category when its site is held out.",
            caption=f"<b>Figure 5.</b> Cells are row percentages averaged across the three held-site folds, rounded to whole percentages. Diagonal cells are recall: {p('recall_Evergreen')} for evergreen and {p('recall_Non-vegetated & dead')} for background/dead, but {p('recall_Woody shrub')} for woody shrub. {p('shrub_to_deciduous')} of true shrub observations are assigned deciduous.",
            takeaway="Evergreen and background/dead are recognized strongly in these tests. Deciduous and herbaceous are less secure; shrub is missed more often than recovered. Shrub/deciduous confusion agrees with their weaker group contrast.",
            source_label="Saved NEON held-site confusion and class-specific transfer tables, 15 Oct.",
            claims=[
                "recall_Evergreen",
                "recall_Non-vegetated & dead",
                "recall_Woody shrub",
                "shrub_to_deciduous",
            ],
            figure_top=582,
            max_height=350,
        ),
        dict(
            figure=6,
            section="3 / Abundance  /  A. Endmember information",
            title="Representative spectra and useful labels are different goals",
            subtitle="Endmembers are mixture reference spectra. Their distance is measured by root-mean-square error (RMSE).",
            caption=f"<b>Figure 6.</b> The {m['endmembers']} selected pixels come from {m['selected_parents']} polygon IDs. Targets exclude those IDs. Random libraries retain the same per-polygon pixel counts; whiskers show the central 95% of 30 draws, not population uncertainty. Selected references improve mean nearest-reference label agreement ({p('selected_single_reference_BA')} versus {p('matched_random_single_reference_BA_mean')}) but have larger same-category spectral distances.",
            takeaway="The selected spectra can help distinguish labels while covering typical within-category variation less closely. Selection used the whole library, so this internal diagnostic does not demonstrate selection-blind performance.",
            source_label="Selected/reference coverage, matched random controls and summary, 19 Oct.",
            claims=[
                "selected_members",
                "selected_polygon_IDs",
                "selected_single_reference_BA",
                "matched_random_single_reference_BA_mean",
            ],
            figure_top=582,
            max_height=350,
        ),
        dict(
            figure=7,
            section="3 / Abundance  /  A. Endmember information",
            title="Different category mixtures can explain the same spectrum",
            subtitle="A saved numerical example exposes why an excellent spectral match need not imply unique composition.",
            caption=f"<b>Figure 7.</b> {m['ambiguous']} of {m['endmembers']} selected spectra can be reconstructed using only other-category references with nonnegative weights summing to one (RMSE at most 10<super>-8</super> in supplied-array units). The assigned-label bar is not measured field cover. This search allows multiple references per category and up to eight active references, broader than the three-category MESMA test.",
            takeaway="The example is a verified mathematical ambiguity, not an observed alternative plant composition. References without a certificate are not proven unique. Field constraints and endmember purity matter as well as fit quality.",
            source_label="Cross-category hull certificates, saved weights and illustration, 19 Oct.",
            claims=["ambiguous", "selected_members"],
            figure_top=582,
            max_height=350,
        ),
        dict(
            figure=8,
            section="3 / Abundance  /  B. Synthetic recovery",
            title="Synthetic recovery depends on library representation",
            subtitle="Known weighted sums of parent spectra let us check estimated fractions against exact synthetic proportions.",
            caption="<b>Figure 8.</b> Smaller fraction RMSE means closer estimated weights (fractions run from 0 to 1). Ridge is a trained, regularized regression; MESMA searches reference combinations. The larger ridge library performs better, but its NEON advantage disappears with the same 15 retained parents as MESMA. Bars summarize existing fold errors; they are not field abundance accuracies.",
            takeaway=f"Library capacity changes the conclusion; there is no intrinsic algorithm winner here. In the separate year-held-out test, ridge RMSE was {r('year_Ridge')} versus {r('year_Training prior')} for the no-spectrum prior, with site and year confounded.",
            source_label="Abundance domain summary and same-candidate ridge control, 16 Oct.",
            claims=[
                "plant_ridge120",
                "plant_ridge15",
                "plant_MESMA15",
                "site_ridge120",
                "site_ridge15",
                "site_MESMA15",
                "year_Ridge",
                "year_Training prior",
            ],
            figure_top=582,
            max_height=340,
        ),
        dict(
            figure=9,
            section="3 / Abundance  /  B. Synthetic recovery",
            title="A better spectral fit does not ensure better fractions",
            subtitle=f"The newest fixed-library check searched all {m['model_count']:,} permitted models on the same {m['targets']} synthetic targets.",
            caption=f"<b>Figure 9.</b> Models use one reference per category, up to three categories. Exhaustive MESMA reduces mean spectral error by {m['spectral_reduction_pct']:.1f}%, while pooled fraction RMSE changes from {r('screened_fraction_RMSE')} to {r('fraction_RMSE')}. Fraction error improves for {m['lower_fraction_error_targets']} targets and worsens for {m['higher_fraction_error_targets']} ({m['unchanged_fraction_error_targets']} unchanged). The paired eight-bundle 95% bootstrap range for the aggregate change is {m['conditional_bundle_bootstrap_2_5']:.3f} to {m['conditional_bundle_bootstrap_97_5']:.3f}; it includes no change.",
            takeaway=f"Known-parent recovery is essentially exact, so the solver can recover the constructed weights. Dense and sparse no-spectrum baselines have RMSE {r('dense_prior')} and {r('sparse_prior')}: information depends on the comparison. None of these tests validates field cover.",
            source_label="Fixed-library exhaustive comparison and original endmember controls, 19 Oct.",
            claims=[
                "exhaustive_model_count",
                "exhaustive_targets",
                "spectral_reduction_pct",
                "screened_fraction_RMSE",
                "exhaustive_fraction_RMSE",
                "exhaustive_lower_fraction_error_targets",
                "exhaustive_higher_fraction_error_targets",
                "exhaustive_unchanged_fraction_error_targets",
                "conditional_bundle_bootstrap_2_5",
                "conditional_bundle_bootstrap_97_5",
                "oracle",
                "dense_prior",
                "sparse_prior",
            ],
            figure_top=582,
            max_height=330,
        ),
    ]


def opening(c, m, manifest):
    shell(c, 1, "Scientific update", manifest["git_commit"])
    y = paragraph(
        c,
        "What can spectra tell us<br/>about plant functional types?",
        MARGIN,
        688,
        size=29,
        leading=36,
        bold=True,
    )
    y = paragraph(
        c,
        "Different groups. Uneven recognition.<br/>Conditional abundance information.",
        MARGIN,
        y - 19,
        size=17,
        leading=23,
        color=TEAL,
    )
    y = paragraph(
        c,
        "This library links corrected NEON spectra to researcher-assigned cover categories. We ask what those labels reveal about spectral differences, recognition of an unknown observation, and the fractions in a mixed observation.",
        MARGIN,
        y - 23,
        size=12,
        leading=17,
    )
    # A deliberately simple progression, separate from the nine scientific figures.
    card_top = y - 28
    steps = [
        ("01", "SEPARABILITY", "Are they different?"),
        ("02", "IDENTIFIABILITY", "Can we tell them apart?"),
        ("03", "ABUNDANCE", "How much is there?"),
    ]
    gap = 16
    w = (CONTENT - 2 * gap) / 3
    for i, (n, label, question) in enumerate(steps):
        x = MARGIN + i * (w + gap)
        c.setFillColor(colors.HexColor("#EDF4F1"))
        c.roundRect(x, card_top - 94, w, 94, 7, fill=1, stroke=0)
        paragraph(
            c, n, x + 12, card_top - 11, width=w - 24, size=20, bold=True, color=TEAL
        )
        paragraph(c, label, x + 12, card_top - 43, width=w - 24, size=8.8, bold=True)
        paragraph(
            c, question, x + 12, card_top - 63, width=w - 24, size=9.6, leading=13
        )
        if i < 2:
            c.setStrokeColor(colors.HexColor(TEAL))
            mid = x + w + 8
            yy = card_top - 47
            c.line(mid - 5, yy, mid + 5, yy)
            c.line(mid + 5, yy, mid + 1, yy + 3)
            c.line(mid + 5, yy, mid + 1, yy - 3)
    y = card_top - 116
    paragraph(c, "THE OBSERVED LIBRARY", MARGIN, y, size=9, bold=True, color=TEAL)
    y = paragraph(
        c,
        f"<b>{m['polygon_GlobalIDs']:,}</b> polygon IDs  /  <b>{m['polygon_year_spectra']:,}</b> annual spectra<br/><b>{m['sites']}</b> sites  /  <b>{m['cells']}</b> site-year cohorts  /  <b>{m['NEON_coordinates']}</b> supported NEON coordinates",
        MARGIN,
        y - 20,
        size=13,
        leading=21,
    )
    y -= 22
    for cat, col in manifest["pft_colors"].items():
        c.setFillColor(colors.HexColor(col))
        c.circle(MARGIN + 4, y - 6, 3.5, fill=1, stroke=0)
        paragraph(
            c, escape(cat), MARGIN + 16, y, width=CONTENT - 16, size=11, leading=16
        )
        y -= 22
    paragraph(
        c,
        "These are the recorded researcher categories, assigned in 2023/2024 and reused across imagery years. Non-vegetated &amp; dead is a background comparator, not a biological PFT. Repeated observations are not extra independent plants; physical reflectance scaling remains unresolved.",
        MARGIN,
        y - 9,
        size=9.4,
        leading=13,
        color=MUTED,
    )
    c.showPage()


def figure_page(c, item, figure, git):
    page = item["figure"] + 1
    shell(c, page, item["section"], git)
    bottom = paragraph(c, item["title"], MARGIN, 695, size=24, leading=29, bold=True)
    bottom = paragraph(
        c, item["subtitle"], MARGIN, bottom - 12, size=11.3, leading=16, color=MUTED
    )
    assert bottom >= item["figure_top"] + 8, (page, "header collides", bottom)
    path = ROOT / figure["filename"]
    assert sha(path) == figure["sha256"]["png"]
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(CONTENT / iw, item["max_height"] / ih)
    w, h = iw * scale, ih * scale
    x = (WIDTH - w) / 2
    y = item["figure_top"] - h
    c.drawImage(str(path), x, y, width=w, height=h, mask="auto")
    BOXES.append(
        {
            "page": page,
            "kind": "image",
            "x": x,
            "top": item["figure_top"],
            "width": w,
            "height": h,
        }
    )
    cap_bottom = paragraph(c, item["caption"], MARGIN, y - 14, size=9.5, leading=13.1)
    box_top = min(144, cap_bottom - 16)
    takeaway(c, item["takeaway"], top=box_top, height=84)
    # Short human-readable sources; full paths/hashes/selection rules live beside the PDF.
    # Footer is a single bounded paragraph above the shared page rule.
    source_top = box_top - 84 - 8
    if source_top >= 48:
        paragraph(
            c,
            "Source: " + item["source_label"],
            MARGIN,
            source_top,
            size=7.4,
            leading=10,
            color=MUTED,
        )
    else:
        raise ValueError(f"Page {page}: insufficient source space ({source_top})")
    c.showPage()


def synthesis(c, m, git):
    shell(c, 11, "What we can conclude", git)
    y = paragraph(
        c,
        "Three questions, three levels of evidence",
        MARGIN,
        695,
        size=24,
        leading=29,
        bold=True,
    )
    y = (
        paragraph(
            c,
            "Use these conclusions for the sampled, researcher-labelled library. Stronger ecological claims require stronger independent observations.",
            MARGIN,
            y - 12,
            size=11.3,
            leading=16,
            color=MUTED,
        )
        - 22
    )
    panels = [
        (
            "01  ARE THE PFTs SPECTRALLY DIFFERENT?",
            f"<b>Evidence:</b> All {m['pairs']} pairs differ in all four matched site/year cohorts.<br/><b>Conclusion:</b> Yes, as group distributions in this library; contrasts vary by pair and wavelength.<br/><b>What remains:</b> More independent regions and crossed years to establish broader stability.",
        ),
        (
            "02  CAN WE IDENTIFY AN UNKNOWN SPECTRUM?",
            f"<b>Evidence:</b> NEON mean category recall is {100 * m['NEON_site']:.1f}% at held-out sites.<br/><b>Conclusion:</b> Useful, uneven recognition: evergreen and background/dead are strongest; woody-shrub recall is {100 * m['recall_Woody shrub']:.1f}%.<br/><b>What remains:</b> Blind external observations, with category-specific error checks.",
        ),
        (
            "03  CAN WE ESTIMATE HOW MUCH IS PRESENT?",
            "<b>Evidence:</b> Some synthetic recovery is useful, but different mixtures can reproduce the same spectrum; exhaustive search does not improve average fraction error.<br/><b>Conclusion:</b> Conditional mathematical capability; real-world abundance accuracy is not established.<br/><b>What remains:</b> Independent field fractions aligned to sensor footprints, verified units and endmember purity.",
        ),
    ]
    for heading, body in panels:
        h = 144
        c.setFillColor(colors.HexColor("#EDF4F1"))
        c.roundRect(MARGIN, y - h, CONTENT, h, 7, fill=1, stroke=0)
        yy = paragraph(
            c,
            heading,
            MARGIN + 14,
            y - 14,
            width=CONTENT - 28,
            size=10,
            bold=True,
            color=TEAL,
        )
        b = paragraph(
            c, body, MARGIN + 14, yy - 10, width=CONTENT - 28, size=11, leading=16
        )
        assert b >= y - h + 9, (heading, b, y - h)
        y -= h + 13
    paragraph(
        c, "NEXT SCIENTIFIC PRIORITY", MARGIN, y - 5, size=9, bold=True, color=TEAL
    )
    paragraph(
        c,
        "Collect contemporaneous field cover fractions with matched spectral footprints. More synthetic mixtures alone cannot supply this missing ecological truth.",
        MARGIN,
        y - 24,
        size=11,
        leading=16,
    )
    c.showPage()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--font-dir")
    args = ap.parse_args()
    font_hashes = configure_fonts(args.font_dir)
    manifest = json.loads((BASE / "figure_manifest.json").read_text())
    m = json.loads((BASE / "metrics.json").read_text())
    pages = narrative(m)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(
        str(OUTPUT), pagesize=(WIDTH, HEIGHT), invariant=1, pageCompression=1
    )
    c.setTitle(
        "SpectralBridge: What can spectra tell us about researcher-assigned PFTs?"
    )
    c.setAuthor("SpectralBridge research team")
    c.setSubject(
        "Separability, identifiability and synthetic abundance evidence; 22 October 2026"
    )
    opening(c, m, manifest)
    for item, fig in zip(pages, manifest["figures"]):
        assert item["figure"] == fig["number"]
        figure_page(c, item, fig, manifest["git_commit"])
    synthesis(c, m, manifest["git_commit"])
    c.save()
    content = {
        "date": manifest["generated_date"],
        "git_commit": manifest["git_commit"],
        "pages": pages,
        "opening_and_synthesis_source": "build_report.py: opening() and synthesis()",
        "opening_sources": [
            "provenance/researcher-evidence/2026-10-16/v1/foundation.json",
            "provenance/researcher-evidence/2026-10-16/v1/tables/category_support.csv",
        ],
        "synthesis_figures": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    }
    (BASE / "report_content.json").write_text(json.dumps(content, indent=2) + "\n")
    (BASE / "layout_boxes.json").write_text(json.dumps(BOXES, indent=2) + "\n")
    build = {
        "output": str(OUTPUT.relative_to(ROOT)),
        "sha256": sha(OUTPUT),
        "pages": 11,
        "scientific_figures": 9,
        "git_commit": manifest["git_commit"],
        "date": manifest["generated_date"],
        "report_builder_sha256": sha(__file__),
        "figure_manifest_sha256": sha(BASE / "figure_manifest.json"),
        "fonts": font_hashes,
        "python": platform.python_version(),
        "reported_units": "Original stored NEON or supplied-array units, explicitly labelled; unit fractions for mixture error",
        "scope": "Researcher cover_category only; presentation of existing results; no new fits or inferential tests",
    }
    (BASE / "report_manifest.json").write_text(
        json.dumps(build, indent=2, sort_keys=True) + "\n"
    )
    print(f"Created {OUTPUT} (11 pages; 9 scientific figures)")


if __name__ == "__main__":
    main()
