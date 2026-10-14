"""Human MESMA-readiness narrative with original vector scientific appendices."""

from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / "output/pdf"
OUT.mkdir(exist_ok=True)
TMP = Path("/tmp/mesma-readiness-pdf")
TMP.mkdir(exist_ok=True)
styles = getSampleStyleSheet()
styles["Normal"].fontSize = 10
styles["Normal"].leading = 14
styles["Normal"].spaceAfter = 8
styles["Heading1"].keepWithNext = True
styles["Heading2"].keepWithNext = True
styles["Heading1"].fontSize = 17
styles["Heading1"].leading = 22
styles["Heading1"].spaceBefore = 16
styles["Heading2"].fontSize = 12
styles["Heading2"].leading = 16
styles["Heading2"].textColor = colors.HexColor("#165969")
styles["Heading2"].spaceBefore = 12
styles.add(
    ParagraphStyle(name="TableBody", fontName="Helvetica", fontSize=8, leading=10)
)
styles.add(
    ParagraphStyle(
        name="TableHead", parent=styles["TableBody"], fontName="Helvetica-Bold"
    )
)


def inline(text):
    for a, b in [
        ("≥", ">="),
        ("≤", "<="),
        ("±", "+/-"),
        ("×", "x"),
        ("→", "->"),
        ("—", "-"),
        ("–", "-"),
        ("²", "2"),
    ]:
        text = text.replace(a, b)
    text = escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


story = [
    Paragraph("SpectralBridge<br/>MESMA readiness audit", styles["Title"]),
    Spacer(1, 15),
    Paragraph(
        "Scientific and computational assessment<br/>14 October 2026", styles["Normal"]
    ),
    Spacer(1, 12),
    Paragraph(
        "<b>Executive finding:</b> useful for controlled spectral-library diagnostics, but the current evidence does not support operational ecological abundance estimates.",
        styles["Normal"],
    ),
    Paragraph(
        "Distinct spectra do not guarantee identifiable endmembers or recoverable fractions. The bounded held-out benchmarks show substantial convex ambiguity and fraction error. Physical scale/purity/background gaps and absent independent cover truth block a stronger readiness claim.",
        styles["Normal"],
    ),
    Paragraph(
        "3,639 polygon identities | 4,807 paired polygon-years | 122 source flights<br/>360 supported scheme/fold tests | 369,048 fitted controlled-mixture results<br/>These simulations and overlapping folds are not independent field replicates.",
        styles["Normal"],
    ),
    Paragraph(
        "Guide: the twenty scientific answers come first, followed by material interpretation, selection assumptions, uncertainty, verification and primary references. Six main vector figures and a coverage supplement follow the narrative. Exact memberships, constraints, source hashes and numerical tables are preserved with the report source.",
        styles["Normal"],
    ),
    Paragraph("<b>REAL ABUNDANCE VALIDATION = NOT YET AVAILABLE</b>", styles["Normal"]),
    PageBreak(),
]
for filename in [
    "RESULTS.md",
    "MATERIAL_CLASS_AUDIT.md",
    "SPECTRAL_QC.md",
    "ENDMEMBER_SELECTION.md",
    "SYNTHETIC_MIXTURES.md",
    "UNCERTAINTY.md",
    "VALIDATION.md",
    "LITERATURE_METHODS.md",
]:
    for block in (SOURCE / filename).read_text().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("|"):
            data = [
                line.split("|")[1:-1]
                for line in block.splitlines()
                if line.startswith("|") and not re.match(r"^\|\s*---", line)
            ]
            n = len(data[0])
            available = A4[0] - 90
            widths = [
                max(10, min(25, max(len(str(row[j]).strip()) for row in data)))
                for j in range(n)
            ]
            widths = [available * w / sum(widths) for w in widths]
            rows = []
            for i, row in enumerate(data):
                rows.append(
                    [
                        Paragraph(
                            inline(cell.strip().replace("_", " ")),
                            styles["TableHead" if i == 0 else "TableBody"],
                        )
                        for cell in row
                    ]
                )
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4eef0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.grey),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])
        elif block.startswith("## "):
            story.append(Paragraph(inline(block[3:]), styles["Heading2"]))
        elif block.startswith("# "):
            story.append(Paragraph(inline(block[2:]), styles["Heading1"]))
        else:
            story.append(Paragraph(inline(block.replace("\n", " ")), styles["Normal"]))
    story.append(Spacer(1, 16))
story.append(PageBreak())
story.append(Paragraph("Scientific figure appendix", styles["Heading1"]))
for path in sorted((SOURCE / "figures").glob("*.pdf")):
    story.append(Paragraph(path.stem.replace("_", " "), styles["Normal"]))
story.append(
    Paragraph(
        "Figures retain original vector dimensions for readable zooming. Six primary families plus one coverage supplement. Native units are explicitly unverified; no displayed residual tolerance is presented as a universal reflectance threshold.",
        styles["Normal"],
    )
)


def footer(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#45636b"))
    canvas.drawString(45, 26, "SpectralBridge | MESMA readiness | conditional evidence")
    canvas.drawRightString(A4[0] - 45, 26, str(doc.page))


narrative = TMP / "narrative.pdf"
SimpleDocTemplate(
    str(narrative),
    pagesize=A4,
    leftMargin=45,
    rightMargin=45,
    topMargin=45,
    bottomMargin=45,
    title="SpectralBridge MESMA readiness audit",
    author="SpectralBridge",
).build(story, onFirstPage=footer, onLaterPages=footer)
writer = PdfWriter()
writer.append(PdfReader(narrative))
for path in sorted((SOURCE / "figures").glob("*.pdf")):
    writer.append(PdfReader(path))
path = OUT / "spectralbridge_mesma_readiness_report.pdf"
with path.open("wb") as f:
    writer.write(f)
reader = PdfReader(path)
assert all(page.extract_text().strip() for page in reader.pages)
print(f"{path}: {len(reader.pages)} pages")
