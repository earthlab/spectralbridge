"""Human-researcher PDF from the recorded-category-only editable source."""

from pathlib import Path
import hashlib
import json
from html import escape
from PIL import Image
from pypdf import PdfReader
from reportlab import rl_config
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
DEST = (
    REPO
    / "output/pdf/researcher_pft_information/Researcher_Categories_Spectral_Information_and_Abundance.pdf"
)
W, H = 1008, 756
M = 48
rl_config.invariant = 1
for name, file in [("Body", "Arial.ttf"), ("Bold", "Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + file))
pdfmetrics.registerFontFamily(
    "Body", normal="Body", bold="Bold", italic="Body", boldItalic="Bold"
)
STYLES = {
    "body": ParagraphStyle(
        "body", fontName="Body", fontSize=12, leading=17, textColor="#183c4b"
    ),
    "caption": ParagraphStyle(
        "caption", fontName="Body", fontSize=10.7, leading=14, textColor="#183c4b"
    ),
    "small": ParagraphStyle(
        "small", fontName="Body", fontSize=8.5, leading=11, textColor="#526975"
    ),
    "head": ParagraphStyle(
        "head", fontName="Bold", fontSize=17, leading=22, textColor="#183c4b"
    ),
    "title": ParagraphStyle(
        "title", fontName="Bold", fontSize=23, leading=28, textColor="#183c4b"
    ),
}
geometry = []


def para(c, text, x, top, width, style="body", minimum=37):
    p = Paragraph(text, STYLES[style])
    _, height = p.wrap(width, H)
    assert top - height >= minimum, (c.getPageNumber(), text[:70], top, height)
    p.drawOn(c, x, top - height)
    geometry.append(
        {
            "page": c.getPageNumber(),
            "x": x,
            "top": top,
            "bottom": top - height,
            "width": width,
        }
    )
    return top - height


def chrome(c, chapter, title):
    c.setFont("Bold", 10)
    c.setFillColor(colors.HexColor("#b4643d"))
    c.drawString(M, H - 32, chapter.upper())
    para(c, escape(title), M, H - 47, W - 2 * M, "title")
    c.setStrokeColor(colors.HexColor("#c6d3d8"))
    c.line(M, 30, W - M, 30)
    c.setFont("Body", 8.5)
    c.setFillColor(colors.HexColor("#526975"))
    c.drawString(M, 17, "SPECTRALBRIDGE | RESEARCHER CATEGORIES ONLY | 15 OCTOBER 2026")
    c.drawRightString(W - M, 17, str(c.getPageNumber()))


def picture(c, path, x, y, width, height):
    with Image.open(path) as im:
        w, h = im.size
    scale = min(width / w, height / h)
    dw, dh = w * scale, h * scale
    c.drawImage(
        str(path), x + (width - dw) / 2, y + (height - dh) / 2, dw, dh, mask="auto"
    )


def block(c, title, text, x, y, width):
    y = para(c, title, x, y, width, "head") - 10
    return para(c, text, x, y, width) - 26


def build():
    source = json.loads((BASE / "report_source.json").read_text())
    DEST.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(DEST), pagesize=(W, H), pageCompression=1, invariant=1)
    c.setTitle(source["title"])
    c.setAuthor("SpectralBridge research synthesis")
    chrome(
        c,
        "The current primary biological analysis",
        "Researcher categories: where information lives",
    )
    para(
        c,
        "Wavelength discrimination, domain transfer and controlled synthetic abundance",
        M,
        650,
        900,
        "head",
    )
    picture(c, BASE / "figures/R03_single_wavelength_prediction.png", M, 185, 530, 420)
    y = 605
    y = block(
        c,
        "One recorded label system",
        "Deciduous; Evergreen; Herbaceous; Non-vegetated &amp; dead; Woody shrub. Species-derived groupings are excluded from the current primary analysis.",
        620,
        y,
        340,
    )
    y = block(
        c, "The strongest new result", escape(source["main_finding"]), 620, y, 340
    )
    block(
        c,
        "A reusable information atlas",
        "Ten category pairs ×360 supported NEON coordinates, with effects, adjusted evidence, prediction, stability, selection frequency and configured OLI support. Inputs remain in place; prior evidence is preserved.",
        620,
        y,
        340,
    )
    para(
        c,
        "3,639 polygon identities | 4,807 polygon/year spectra | NEON360 and synthetic OLI7<br/>Fourteen main figures plus class-confusion supplement. Every figure explains its meaning and limits. A polygon is not necessarily one plant or a pure material.",
        M,
        145,
        900,
    )
    c.showPage()
    chrome(
        c,
        "Methods for interpretation",
        "Four questions require four different kinds of evidence",
    )
    y = 635
    for title, text in [
        (
            "Do the sampled groups differ?",
            "Whole-spectrum labels shuffle within acquisition-history blocks. Reuse forty full-cohort ensembles as descriptive evidence; separately, 230 training-only pair/cohort contrasts use 1,999 blocked shuffles, max-T and within-design Bonferroni correction. Neither p-map selects predictive features.",
        ),
        (
            "Can a new measurement be recognized?",
            "Single-wavelength LDA learns means, direction and threshold from training identities. Balanced accuracy averages class recalls. Multivariate logistic selection and C tuning refit inside inner GlobalID folds. Entire IDs and their repeated years stay outside the outer training set.",
        ),
        (
            "How much spectral information is complementary?",
            "An orthogonal forward selector removes already-explained directions before choosing the next coordinate. Budgets span1 to360 coordinates and OLI7. Inner-only parsimony favors smaller budgets within two percentage points of the best inner score; outer results evaluate the policy.",
        ),
        (
            "Can fractions be recovered and transferred?",
            "Every method receives the same controlled pair/triple mixtures. Proper/tuning/test parent identities are disjoint:120, 40 and up to 60 per experiment. Each five-parent bundle generates 170 dependent mixtures. Hyperparameters use tuning parents only; 499 uncertainty draws resample entire test bundles.",
        ),
    ]:
        y = block(c, title, text, M, y, 900)
    para(
        c,
        "What the units mean: a GlobalID is a polygon footprint; neighboring wavelengths and generated mixtures are not independent biological replicates. Library units remain stored values. Synthetic OLI is a shared-source spectral representation. Annotation dates2023/2024 are reused across image years; paired tests assess retrospective footprints.",
        M,
        112,
        900,
        "small",
    )
    c.showPage()
    for item in source["figures"]:
        number = item["number"]
        c.bookmarkPage("figure" + str(number))
        c.addOutlineEntry(
            "Figure " + str(number) + ": " + item["title"], "figure" + str(number)
        )
        chrome(c, "Evidence and interpretation", f"Figure {number}. " + item["title"])
        picture(c, BASE / "figures" / (item["name"] + ".png"), M, 218, W - 2 * M, 444)
        width = (W - 2 * M - 40) / 3
        for i, (heading, key) in enumerate(
            [
                ("HOW TO READ IT", "read"),
                ("WHAT WE LEARN", "finding"),
                ("WHAT REMAINS UNCERTAIN", "limit"),
            ]
        ):
            x = M + i * (width + 20)
            c.setFont("Bold", 10)
            c.setFillColor(colors.HexColor("#26758b" if i < 2 else "#b4643d"))
            c.drawString(x, 201, heading)
            para(c, escape(item[key]), x, 189, width, "caption", minimum=52)
        para(
            c,
            "Evidence: "
            + escape("; ".join(item["sources"]))
            + ". Full paths, numerical products and hashes are retained in the versioned packet.",
            M,
            48,
            912,
            "small",
            minimum=31,
        )
        c.showPage()
    chrome(
        c,
        "Scientific interpretation",
        "What improves, what fails, and what the data cannot decide",
    )
    left = [
        (
            "Recognition is class- and domain-dependent",
            "Evergreen and the broad background category transfer more consistently than Woody shrub. Whole-spectrum support does not guarantee useful single-coordinate prediction. Exact wavelengths and all domain values are in the atlas; observed peaks are not deployed sensor recommendations.",
        ),
        (
            "Complementarity is real, but not a sensor optimum",
            "A single coordinate performs poorly on the five-way task. Multiple residual-selected measurements improve recognition; the inner-only policy chooses50-100 coordinates in these folds. Correlation clusters explain redundancy, but no universal band count follows from three sites.",
        ),
        (
            "Simple supervised models earn their place",
            "Projected ridge improves known synthetic fractions under new-polygon and held-site tests and beats a no-spectrum training-prior control. Its global-year mean does not beat that prior; gains over MESMA alone are insufficient. Trees do not improve the principal average. First/second derivatives are worse in this benchmark; other transformations remain reported rather than silently selected.",
        ),
    ]
    right = [
        (
            "Better average fractions are not unique inversion",
            "ML can exploit relationships in the finite synthetic training distribution. High-ambiguity targets can still show reduced average error, without excluding another near-fitting composition. Gains vary by stratum and class; modest-ambiguity cases do not uniformly favor ML.",
        ),
        (
            "Detection and abundance have different costs",
            "Two-stage gating reduces some absent-class predictions but increases missed low fractions. Shrinkage, false positives, calibration and low-fraction error must be read together. A .10 cutoff and conditional curves do not supply a universal detection limit.",
        ),
        (
            "Failure cannot be causally assigned to one factor",
            "Near-zero known-parent oracle error shows that the solver can recover the idealized linear weights. The remaining gap implicates representation/library variability and model choice, with domain and ambiguity effects. Missing independent purity/fraction truth still blocks a field claim.",
        ),
    ]
    for x, blocks in [(M, left), (535, right)]:
        y = 635
        for title, text in blocks:
            y = block(c, title, escape(text), x, y, 425)
    c.showPage()
    chrome(
        c, "Limits and priorities", "The evidence needed before a field-abundance claim"
    )
    y = 635
    for title, text in [
        (
            "Recover physical provenance first",
            "Verify original reflectance units/scaling, physical band headers and polygon purity. OLI export coordinates are rounded labels; response annotations use the exact configured parameters. MicaSense physical coordinates remain unresolved and are excluded. Non-vegetated &amp; dead is a heterogeneous cover class.",
        ),
        (
            "Measure independent fractions, absences and low cover",
            "Collect complete co-located fractional-cover and purity truth at the intended footprint, including true zeros and low positives. Synthetic mixing weights are exact algebra, not a substitute for field fractions. Training has120 independent parents, not4,080 independent biological samples.",
        ),
        (
            "Cross sites and years with contemporary labels",
            "Retain all valid repeats, acquisition/annotation dates and source identity. Record turnover and persistent identity linkage independently. Later annotations do not verify an earlier biological state. More regions and crossed years are needed to separate observation conditions from ecological change.",
        ),
        (
            "Keep scientific and computational uncertainties explicit",
            "Identity and parent-bundle intervals condition on observed support. They are not guarantees over unseen regions or field cover. Model comparisons are exploratory outer evaluations; confidence sets and detection rules have costs. No current use is operationally validated.",
        ),
    ]:
        y = block(c, title, text, M, y, 900)
    c.showPage()
    chrome(
        c,
        "Reproducibility and reading guide",
        "Every primary result has a numerical source",
    )
    y = 635
    for title, text in [
        (
            "Primary versioned packet",
            "provenance/researcher-pft-information/2026-10-15/v1/ contains METHODS, RESULTS, LIMITATIONS, configuration/environment, the category-only label audit, editable report JSON/Markdown, figure manifests, numerical validation and canonical CSV/Parquet products.",
        ),
        (
            "Numerical products",
            "researcher_pft_information_atlas.csv/.parquet:3,600 pair-coordinate rows. abundance_model_comparison.parquet: class/model/domain errors. tables/ contains every domain curve, class error, confusion matrix, synthetic truth/parent membership, prediction index, ambiguity analysis and paired bundle interval.",
        ),
        (
            "Historical evidence is preserved",
            "Forty researcher-category permutation ensembles and prior researcher-only temporal class metrics are reused with explicit scope. Earlier dual-label reports/builders remain frozen for provenance and are no longer the primary biological interpretation. No source table was copied or historical output deleted.",
        ),
        (
            "Methods and validation",
            "The report and publication figures rebuild from saved numerical products. Models, scalers, selection, parent roles, prediction math, simplex constraints and source hashes are checked separately. METHOD references include official scikit-learn grouped CV/PLS/boosting contracts and Duchi et al.2008, doi:10.1145/1390156.1390191 for simplex projection; inherited permutation/MESMA definitions remain linked in METHODS.",
        ),
    ]:
        y = block(c, title, escape(text), M, y, 900)
    para(
        c,
        "Researcher categories are the sole primary grouping. Statistical difference, recognition, known synthetic mixing weights and independent physical abundance remain distinct claims.",
        M,
        115,
        900,
        "head",
    )
    c.showPage()
    c.save()
    pages = len(PdfReader(DEST).pages)
    assert pages == 20, pages
    markdown = ["# " + source["title"], "\n" + source["main_finding"]]
    for f in source["figures"]:
        markdown.extend(
            [
                "\n## Figure " + str(f["number"]) + ". " + f["title"],
                f["read"],
                "\n**Finding:** " + f["finding"],
                "\n**Limit:** " + f["limit"],
            ]
        )
    (BASE / "report_source.md").write_text("\n\n".join(markdown) + "\n")
    table_hashes = {
        str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((BASE / "tables").glob("*"))
        if p.is_file()
    }
    figure_hashes = {
        str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((BASE / "figures").glob("*"))
        if p.is_file()
    }
    manifest = {
        "pages": pages,
        "figure_stories": len(source["figures"]),
        "pdf": str(DEST.relative_to(REPO)),
        "pdf_sha256": hashlib.sha256(DEST.read_bytes()).hexdigest(),
        "table_hashes": table_hashes,
        "figure_hashes": figure_hashes,
        "source_sha256": hashlib.sha256(
            (BASE / "report_source.json").read_bytes()
        ).hexdigest(),
    }
    (BASE / "report_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (BASE / "report_geometry.json").write_text(json.dumps(geometry, indent=2) + "\n")
    print(DEST, pages, "pages")


if __name__ == "__main__":
    build()
