"""Build the curated lab report from an editable, evidence-linked JSON source."""

import hashlib
import json
from html import escape
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
DEST = REPO / "output/pdf/lab_story/SpectralBridge_The_Visual_Scientific_Story.pdf"
W, H = 1008, 756
M = 48
INK = "#183c4b"
TEAL = "#24778a"
RUST = "#b4643d"
GRAY = "#526975"
rl_config.invariant = 1
fonts = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("Lab", str(fonts / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("LabBold", str(fonts / "Arial Bold.ttf")))
pdfmetrics.registerFontFamily(
    "Lab", normal="Lab", bold="LabBold", italic="Lab", boldItalic="LabBold"
)
STYLES = {
    "body": ParagraphStyle(
        "body", fontName="Lab", fontSize=12, leading=17, textColor=INK
    ),
    "small": ParagraphStyle(
        "small", fontName="Lab", fontSize=9, leading=12, textColor=GRAY
    ),
    "caption": ParagraphStyle(
        "caption", fontName="Lab", fontSize=11.1, leading=15.2, textColor=INK
    ),
    "head": ParagraphStyle(
        "head", fontName="LabBold", fontSize=17, leading=22, textColor=INK
    ),
    "title": ParagraphStyle(
        "title", fontName="LabBold", fontSize=26, leading=31, textColor=INK
    ),
}
used = set()
geometry = []


def para(c, text, x, top, width, style="body", min_y=38):
    p = Paragraph(text, STYLES[style])
    _, height = p.wrap(width, H)
    assert top - height >= min_y, (text[:80], top, height)
    p.drawOn(c, x, top - height)
    geometry.append(
        {
            "page": c.getPageNumber(),
            "top": top,
            "bottom": top - height,
            "x": x,
            "width": width,
        }
    )
    return top - height


def chrome(c, chapter, title):
    c.setFillColor(colors.HexColor(RUST))
    c.setFont("LabBold", 11)
    c.drawString(M, H - 34, chapter.upper())
    para(c, escape(title), M, H - 51, W - 2 * M, "title")
    c.setStrokeColor(colors.HexColor("#c6d3d8"))
    c.line(M, 31, W - M, 31)
    c.setFillColor(colors.HexColor(GRAY))
    c.setFont("Lab", 8.5)
    c.drawString(M, 18, "SPECTRALBRIDGE | LAB GROUP SCIENTIFIC STORY | 15 OCTOBER 2026")
    c.drawRightString(W - M, 18, str(c.getPageNumber()))


def image(c, path, x, y, width, height):
    p = REPO / path
    used.add(p)
    with Image.open(p) as im:
        iw, ih = im.size
    factor = min(width / iw, height / ih)
    dw, dh = iw * factor, ih * factor
    c.drawImage(
        str(p), x + (width - dw) / 2, y + (height - dh) / 2, dw, dh, mask="auto"
    )


def figure_page(c, item, n):
    chrome(c, item["chapter"], f"Figure {n}. {item['title']}")
    para(c, escape(item["question"]), M, 663, W - 2 * M, "body")
    with Image.open(REPO / item["image"]) as im:
        tall = im.width / im.height < 1.7
    labels = [
        ("HOW TO READ IT", "read"),
        ("WHAT TO UNDERSTAND", "learn"),
        ("WHAT IT DOES NOT ESTABLISH", "limit"),
    ]
    if tall:
        image(c, item["image"], M, 76, 625, 556)
        x, width, top = 707, 253, 625
        for i, (label, key) in enumerate(labels):
            c.setFillColor(colors.HexColor(TEAL if i < 2 else RUST))
            c.setFont("LabBold", 10)
            c.drawString(x, top, label)
            top = (
                para(c, escape(item[key]), x, top - 13, width, "caption", min_y=70) - 24
            )
    else:
        image(c, item["image"], M, 226, W - 2 * M, 412)
        gap = 22
        width = (W - 2 * M - 2 * gap) / 3
        for i, (label, key) in enumerate(labels):
            x = M + i * (width + gap)
            c.setFillColor(colors.HexColor(TEAL if i < 2 else RUST))
            c.setFont("LabBold", 10)
            c.drawString(x, 210, label)
            para(c, escape(item[key]), x, 198, width, "caption", min_y=55)
    ev = []
    for p in item["evidence"]:
        path = REPO / p
        assert path.exists(), p
        used.add(path)
        ev.append(path.name)
    para(
        c,
        "Evidence: "
        + escape("; ".join(ev))
        + ". Full source paths and hashes are retained in the report packet.",
        M,
        51,
        W - 2 * M,
        "small",
        min_y=32,
    )
    c.showPage()


def block(c, title, text, x, top, width):
    bottom = para(c, escape(title), x, top, width, "head")
    return para(c, text, x, bottom - 10, width, "body") - 25


def build():
    src = json.loads((BASE / "report_source.json").read_text())
    DEST.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(DEST), pagesize=(W, H), pageCompression=1, invariant=1)
    c.setTitle(src["title"])
    c.setAuthor("SpectralBridge research synthesis")
    c.setSubject(
        "Exploration, biological differentiation, generalization, sensor validation and mixture readiness"
    )
    c.bookmarkPage("cover")
    c.addOutlineEntry("The visual scientific story", "cover")
    chrome(
        c,
        "A curated visual research narrative",
        "From spectral exploration to scientific readiness",
    )
    para(
        c,
        "What can the current spectral library distinguish, generalize, detect and unmix?",
        M,
        648,
        820,
        "head",
    )
    image(c, "output/pdf/publication_figures/panels/Figure_1_A.png", M, 205, 475, 410)
    x = 560
    top = 600
    top = block(
        c,
        "The central finding",
        "The library contains useful biological spectral structure. Recognition transfers most reliably at broad woody leaf habit, while species, temporal transfer and mixture attribution are more fragile.",
        x,
        top,
        390,
    )
    top = block(
        c,
        "The scientific progression",
        "We moved from trace plots and quantile signatures to matched whole-spectrum tests, grouped prediction, spectral reduction, an independent satellite pilot, and explicit tests of mixture ambiguity and uncertainty.",
        x,
        top,
        390,
    )
    block(
        c,
        "What this report is",
        "A selection of 23 data-driven figure stories, with a reading guide and an explicit lesson for every figure. Existing experiments are reused; no models were refitted for this report.",
        x,
        top,
        390,
    )
    para(
        c,
        "For lab discussion | 15 October 2026<br/>The cover shows category medians and empirical interquartile spread, not confidence bands. Values remain in source stored units. This PDF embeds every selected visual and can be shared on its own.",
        M,
        168,
        W - 2 * M,
        "body",
    )
    c.showPage()

    chrome(c, "Reader guide", "The story in seven steps")
    chapters = []
    for n, f in enumerate(src["figures"], 1):
        if not chapters or chapters[-1][0] != f["chapter"]:
            chapters.append((f["chapter"], n, n + 3))
    y = 636
    for name, n, page in chapters:
        c.setFillColor(colors.HexColor(TEAL))
        c.setFont("LabBold", 12)
        c.drawString(M, y, name)
        c.setFillColor(colors.HexColor(GRAY))
        c.setFont("Lab", 11)
        c.drawRightString(490, y, f"Figure {n} starts on p. {page}")
        y -= 43
    x = 550
    y = 638
    y = block(
        c,
        "Three distinctions to keep in mind",
        "<b>Difference:</b> do sampled groups have different spectra?<br/><b>Prediction:</b> can an unseen labelled polygon be assigned correctly?<br/><b>Unmixing:</b> can the proportion of each material be recovered uniquely?<br/>Evidence for one does not automatically establish the others.",
        x,
        y,
        405,
    )
    y = block(
        c,
        "The strongest current answer",
        "Broad woody leaf habit: <b>96.7%</b> new-polygon and <b>90.1%</b> held-site NEON balanced accuracy. Species: <b>71.7%</b> and <b>47.4%</b>, respectively, conditional on supported targets.",
        x,
        y,
        405,
    )
    block(
        c,
        "Read the bottom of every figure page",
        "HOW TO READ IT explains marks and axes. WHAT TO UNDERSTAND gives the scientific message. WHAT IT DOES NOT ESTABLISH sets the scope. Original panel letters are local to the embedded visual.",
        x,
        y,
        405,
    )
    para(
        c,
        "An evidence ladder, not a leaderboard. Early matching, later classification and synthetic fractions use different cohorts, metrics and targets. They are not interchangeable estimates of one accuracy. Methods: p. 3. Lab decisions: p. 27. Glossary: p. 28. Evidence guide: p. 29.",
        M,
        175,
        W - 2 * M,
        "body",
    )
    c.showPage()

    chrome(c, "Methods in plain language", "What the principal tests ask")
    left = [
        (
            "Whole-spectrum permutation tests",
            "We compare acquisition-matched group curves, then shuffle labels within the declared exchangeability blocks. A maximum statistic detects localized differences; an integrated statistic detects distributed ones. Their nonparametric combination (NPC) asks about the whole curve. Holm correction controls the declared comparison family.",
        ),
        (
            "Balanced classification accuracy",
            "Recall is the fraction of each true class recognized. Balanced accuracy averages these recalls equally, so a common class cannot dominate the score. A two-class score has a different chance reference from a many-species score. Scores apply to eligible closed-set targets, whose coverage must also be reported.",
        ),
        (
            "Blocked holdouts and bootstrap intervals",
            "All observations of an identity stay together. Site/year/acquisition holdouts ask specific transfer questions. Resampling whole IDs or spatial blocks preserves those clusters better than treating pixels as independent. Intervals remain conditional on the sampled domains and the stated design.",
        ),
    ]
    right = [
        (
            "Spectral angle and spectral RMSE",
            "Angle compares direction of spectral vectors and is less sensitive to a uniform brightness multiplier. Spectral RMSE measures magnitude mismatch in the stated units. Correlation measures co-variation, not equality. A good result for one metric need not be good for another.",
        ),
        (
            "Linear mixtures and fraction recovery",
            "A controlled mixture combines parent spectra with known nonnegative fractions. We fit candidate spectra and compare estimated with known fractions. Multiple combinations can fit almost the same spectrum, so low spectral residual does not establish correct abundance. Here these are algebraic experiments without independent field fractions.",
        ),
        (
            "Calibration and prediction sets",
            "Temperature scaling adjusts score sharpness on separate calibration identities. Conformal methods use a calibration-score quantile to return sets of possible labels. We measure whether the true label is in the set. Ordinary exchangeability-based coverage is not guaranteed after geographic shift.",
        ),
    ]
    for x, blocks in [(M, left), (530, right)]:
        y = 635
        for title, text in blocks:
            y = block(c, title, escape(text), x, y, 425)
    para(
        c,
        "Repeated-year partitions are descriptive sums of squares, not causal random-effect components. Source data are observational: labels, species, environment, illumination, acquisition and spatial support can remain confounded. Historical method definitions are retained in the evidence guide.",
        M,
        120,
        W - 2 * M,
        "small",
    )
    c.showPage()

    previous = None
    for n, f in enumerate(src["figures"], 1):
        if previous != f["chapter"]:
            anchor = f"chapter{n}"
            c.bookmarkPage(anchor)
            c.addOutlineEntry(f["chapter"], anchor)
            previous = f["chapter"]
        figure_page(c, f, n)

    chrome(c, "Lab decisions", "What we can conclude, and how the library should grow")
    x = M
    y = 635
    y = block(
        c,
        "Use now, within the measured scope",
        "Describe sampled spectral variation; compare matched researcher categories and assigned woody PFTs; benchmark supported-label recognition. Broad woody leaf habit is the most transferable demonstrated classification target. The independent Landsat result is a constrained one-pair radiometric/spatial comparison.",
        x,
        y,
        430,
    )
    y = block(
        c,
        "Do not promote to field abundance yet",
        "Pure-spectrum discrimination does not resolve wrong-class mixtures. Unknown rejection is weak, uncertainty loses coverage under site shift, and independent fraction/purity truth is missing. No method is operationally validated by this analysis.",
        x,
        y,
        430,
    )
    block(
        c,
        "Retain repeats; control their statistical weight",
        "Keep every valid source observation, identity, site, acquisition date and annotation date. Hold complete histories together in validation. Use identity-balanced weighting when the target is an average polygon; make additional class/site weights explicit. Preserve prototypes as derived products, not replacements for the archive.",
        x,
        y,
        430,
    )
    x = 535
    y = 635
    y = block(
        c,
        "1. Recover the inexpensive metadata first",
        "Verify original reflectance units/scaling, physical wavelength headers and polygon purity. Resolve MicaSense band identities before ecological inference. A later field survey does not independently verify a polygon's historical biological state.",
        x,
        y,
        425,
    )
    y = block(
        c,
        "2. Collect the truth missing from the hard tasks",
        "Measure independent co-located fractional cover and purity at the relevant footprint, including true absences and low positive fractions. Cross site with year and independently update labels, turnover and persistent identity links. More pixels from the same few parents do not replace replication.",
        x,
        y,
        425,
    )
    block(
        c,
        "3. Replicate real sensor comparisons",
        "Acquire synchronized, physically verified NEON, Landsat and drone observations across sites and seasons, with comparable footprints and independent references. Choose sample sizes from scientific error tolerances and cluster structure. These gaps take priority over another algorithm search.",
        x,
        y,
        425,
    )
    c.showPage()

    chrome(
        c, "Keep the terms straight", "Glossary for reading and discussing the figures"
    )
    terms = [
        (
            "Polygon / GlobalID",
            "A source-labelled footprint. It can contain one crown, several plants or a mixed patch. It is the identity used for grouped validation, not proof of biological purity.",
        ),
        (
            "Polygon/year spectrum",
            "A compact annual summary of source observations for an identity. Two years from the same GlobalID are repeated observations, not two independent individuals.",
        ),
        (
            "Researcher categories",
            "Deciduous, Evergreen, Herbaceous, Non-vegetated & dead, Woody shrub. All 3,639 identities are represented. These are recorded cover categories, not a strictly nested physiological hierarchy.",
        ),
        (
            "Species-derived woody PFTs",
            "DBS: deciduous broadleaf shrub; DBT: deciduous broadleaf tree; EBS: evergreen broadleaf shrub; ECS: evergreen conifer shrub; ECT: evergreen conifer tree. Assigned subset: 1,944 identities.",
        ),
        (
            "Broad leaf habit / coarse cover",
            "Broad leaf habit means deciduous versus evergreen within the assigned woody subset. Coarse cover contrasts vegetation-labelled categories with the heterogeneous Non-vegetated & dead proxy.",
        ),
        (
            "NEON / OLI / MicaSense",
            "NEON is the hyperspectral source. OLI is the Landsat sensor representation; synthetic OLI is derived from NEON. MicaSense here denotes exported derived values with unresolved physical coordinates, not an independently observed drone validation.",
        ),
        (
            "NIR / SWIR / atmospheric gaps",
            "Near-infrared and shortwave-infrared spectral regions. Excluded atmospheric absorption intervals remain disconnected; lines do not interpolate through those gaps.",
        ),
        (
            "Stored units / surface reflectance",
            "Library values retain their stored scale, whose absolute reflectance provenance remains unresolved. The separately verified real-sensor pilot reports unitless surface reflectance. Do not mix their error scales.",
        ),
        (
            "Closed set / target coverage",
            "Closed-set prediction evaluates labels supported by training and test eligibility rules. Coverage is the proportion of the intended target cohort retained. High conditional accuracy can coexist with low coverage.",
        ),
        (
            "Endmember / prototype",
            "An endmember is a candidate component in a mixture model. A prototype is a representative reference. An observed polygon prototype is not automatically a physically pure endmember.",
        ),
    ]
    for col in range(2):
        y = 637
        for title, text in terms[col * 5 : (col + 1) * 5]:
            y = block(c, title, escape(text), M + col * 482, y, 430)
    c.showPage()

    chrome(c, "Evidence and reproducibility", "Where the numbers and figures came from")
    y = 635
    sources = [
        (
            "Exploration and quantile checks",
            "provenance/plot-report/2026-10-13/; provenance/quantile-models/2026-10-13/. Reader-sized exploratory panels are reused from output/pdf/plant_spectral_review/figures/.",
        ),
        (
            "Biological contrasts and spectral reduction",
            "provenance/researcher-pft/2026-10-14/; provenance/sensor-pft-transfer/2026-10-14/; provenance/publication-figures/2026-10-14/. Fixed matched comparisons, label systems and metadata gates are preserved.",
        ),
        (
            "Generalization, prototypes, mixtures and uncertainty",
            "provenance/spectral-library-analytics/2026-10-14/ and provenance/mesma-readiness/2026-10-14/. Existing models, memberships and canonical numerical experiments are reused.",
        ),
        (
            "Independent Landsat and final closure",
            "provenance/real-landsat-validation/2026-10-14/; provenance/scientific-closure/2026-10-15/. Final closure supersedes earlier interpretations where metadata or biological-resolution scope was clarified.",
        ),
    ]
    for title, text in sources:
        y = block(c, title, escape(text), M, y, 900)
    y = block(
        c,
        "This report packet",
        "provenance/lab-story/2026-10-15/ retains the editable report_source.json, Markdown companion, builders, figure inventory, numerical checks and SHA-256 input/output manifest. All 23 visuals are embedded in this PDF. The packet references existing source data in place; it does not copy the merged polygon table or refit models.",
        M,
        y,
        900,
    )
    para(
        c,
        "Method reading retained from the earlier audits: Roberts et al. (2017), doi:10.1111/ecog.02881 (structured validation); Cawley &amp; Talbot (2010), JMLR 11:2079-2107 (selection bias); Bioucas-Dias et al. (2012), doi:10.1109/JSTARS.2012.2194696 (unmixing); Angelopoulos &amp; Bates, arXiv:2107.07511 (conformal prediction). See the earlier LITERATURE_METHODS.md files for method adaptations and full links.",
        M,
        y,
        900,
        "small",
    )
    c.showPage()
    c.save()
    pages = len(PdfReader(DEST).pages)
    assert pages == 29, pages
    markdown = ["# " + src["title"], "\n" + src["subtitle"]]
    for n, f in enumerate(src["figures"], 1):
        markdown.extend(
            [
                "\n## Figure " + str(n) + ". " + f["title"],
                f["question"],
                "\n![Figure " + str(n) + "](" + "../../../" + f["image"] + ")",
                "\n**How to read:** " + f["read"],
                "\n**What to understand:** " + f["learn"],
                "\n**Limits:** " + f["limit"],
                "\nEvidence: " + ", ".join(f["evidence"]),
            ]
        )
    (BASE / "report_source.md").write_text("\n\n".join(markdown) + "\n")
    used.update(
        [
            BASE / "report_source.json",
            BASE / "build_report.py",
            BASE / "curate.py",
            BASE / "build_figures.py",
        ]
    )
    redraw = json.loads((BASE / "figures/redraw_sources.json").read_text())
    for key in ("processing_effects", "early_matching", "quantile_fans"):
        used.update(REPO / p for p in redraw[key])
    used.add(BASE / "figures/redraw_sources.json")
    hashes = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(used)
    }
    result = {
        "pages": pages,
        "figures": len(src["figures"]),
        "pdf": str(DEST.relative_to(REPO)),
        "pdf_sha256": hashlib.sha256(DEST.read_bytes()).hexdigest(),
        "inputs": hashes,
        "figure_inventory": [
            dict(number=i + 1, page=i + 4, **f) for i, f in enumerate(src["figures"])
        ],
    }
    (BASE / "evidence_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    (BASE / "layout_geometry.json").write_text(json.dumps(geometry, indent=2) + "\n")
    print(f"{DEST}: {pages} pages, {len(src['figures'])} figure stories")


if __name__ == "__main__":
    build()
