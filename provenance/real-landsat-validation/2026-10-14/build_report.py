"""Build human-readable narrative plus original vector figure appendix."""

from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
OUT = ROOT / "output/pdf/real_landsat_validation"
OUT.mkdir(parents=True, exist_ok=True)
TMP = ROOT / "tmp/pdfs/real_landsat_validation"
TMP.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles["Normal"].fontSize = 10
styles["Normal"].leading = 14
styles["Normal"].spaceAfter = 8
styles["Heading1"].fontSize = 18
styles["Heading1"].leading = 23
styles["Heading2"].fontSize = 12
styles["Heading2"].leading = 16
styles["Heading2"].textColor = colors.HexColor("#16596a")
styles["Normal"].alignment = TA_LEFT


def inline(text):
    text = (
        text.replace("≥", ">=")
        .replace("≤", "<=")
        .replace("Δ", "Delta ")
        .replace("±", "+/-")
        .replace("²", "2")
        .replace("×", "x")
        .replace("→", "->")
        .replace("—", "-")
        .replace("–", "-")
    )
    text = escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


story = [
    Paragraph(
        "SpectralBridge<br/>Independent real Landsat validation", styles["Title"]
    ),
    Spacer(1, 18),
    Paragraph(
        "R10C | 15 September 2021 NEON flight<br/>16 September 2021 Landsat 8 observation<br/>Pilot evidence frozen 14 October 2026",
        styles["Normal"],
    ),
    Spacer(1, 12),
    Paragraph(
        "<b>Main finding:</b> Broad spectral structure is reproduced in this flight, with persistent band-dependent contrast error. The existing brightness adjustment has mixed effects and no clear overall advantage under the paired spatial bootstrap.",
        styles["Normal"],
    ),
    Paragraph(
        "3,583 actual 30 m footprints | 56 spatial blocks | one flight | one site<br/>Undarkened pooled RMSE 0.01477 reflectance | median angle 2.089 degrees",
        styles["Normal"],
    ),
    Paragraph(
        "This report distinguishes independent real-observation evidence from synthetic internal consistency, cross-flight replication and cross-site generalization. No new calibration was fitted. The exact 22.37-hour difference is conditional on the stated interpretation of a legacy NEON timestamp.",
        styles["Normal"],
    ),
    Paragraph(
        "Guide: results answer the ten scientific questions first; methods explain the physical comparison, statistics and limitations; scene search records selection; the final appendix contains ten full-resolution vector figure pages.",
        styles["Normal"],
    ),
    PageBreak(),
]
for name in ["RESULTS.md", "METHODS.md", "LANDSAT_SEARCH.md", "VALIDATION.md"]:
    text = (SOURCE / name).read_text()
    blocks = text.split("\n\n")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("|"):
            rows = [
                line.split("|")[1:-1]
                for line in block.splitlines()
                if line.startswith("|") and not line.startswith("|---")
            ]
            rows = [
                [Paragraph(inline(cell.strip()), styles["Normal"]) for cell in row]
                for row in rows
            ]
            table = Table(
                rows, colWidths=[72, 83, 83, 45, 70, 83], repeatRows=1, hAlign="LEFT"
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5eef0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.grey),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])
        elif block.startswith("## "):
            story.append(Paragraph(inline(block[3:]), styles["Heading2"]))
        elif block.startswith("# "):
            story.append(Paragraph(inline(block[2:]), styles["Heading1"]))
        else:
            story.append(
                Paragraph(
                    inline(block).replace("\n", "<br/>")
                    if block.startswith("- ")
                    else inline(block.replace("\n", " ")),
                    styles["Normal"],
                )
            )
    story.append(Spacer(1, 20))
story.append(PageBreak())
story.append(Paragraph("Vector figure appendix", styles["Heading1"]))
for name in sorted((SOURCE / "figures").glob("*.pdf")):
    story.append(Paragraph(name.stem.replace("_", " "), styles["Normal"]))
story.append(
    Paragraph(
        "All figures use the same accepted support for both variants. Original registration remains primary; no outlier was removed from agreement tables. Figure widths vary to preserve original vector layouts. Zoom into scatterplots and failure captions as needed.",
        styles["Normal"],
    )
)


def footer(c, doc):
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#49636b"))
    c.drawString(46, 26, "SpectralBridge | real Landsat pilot | one-flight evidence")
    c.drawRightString(A4[0] - 46, 26, str(doc.page))


narrative = TMP / "narrative.pdf"
SimpleDocTemplate(
    str(narrative),
    pagesize=A4,
    rightMargin=45,
    leftMargin=45,
    topMargin=45,
    bottomMargin=45,
    title="SpectralBridge independent real Landsat pilot",
    author="SpectralBridge",
).build(story, onFirstPage=footer, onLaterPages=footer)
writer = PdfWriter()
writer.append(PdfReader(narrative))
for name in sorted((SOURCE / "figures").glob("*.pdf")):
    writer.append(PdfReader(name))
path = OUT / "spectralbridge_real_landsat_pilot_report.pdf"
with path.open("wb") as f:
    writer.write(f)
reader = PdfReader(path)
assert all(p.extract_text().strip() for p in reader.pages)
print(f"{path}: {len(reader.pages)} pages")
