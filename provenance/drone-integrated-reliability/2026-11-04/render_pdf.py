"""Render both editable report-page manifests with checked, fixed-page layout."""

import json
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FONT = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("Report", str(FONT / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("ReportBold", str(FONT / "Arial Bold.ttf")))
BODY = ParagraphStyle(
    "body",
    fontName="Report",
    fontSize=14,
    leading=19,
    textColor=colors.HexColor("#243846"),
)
TITLE = ParagraphStyle(
    "title",
    parent=BODY,
    fontName="ReportBold",
    fontSize=25,
    leading=31,
    textColor=colors.HexColor("#163b4b"),
)
CAP = ParagraphStyle("caption", parent=BODY, fontSize=11.5, leading=15)


def draw(c, text, x, y, width, style):
    p = Paragraph(escape(text), style)
    _, height = p.wrap(width, 2000)
    p.drawOn(c, x, y - height)
    return y - height


for folder, name, short in [
    (
        ROOT / "provenance/brdf-artifact-anatomy-part-ii/2026-11-04",
        "Anatomy_of_a_Red_Artifact_Part_II.pdf",
        "ANATOMY OF A RED ARTIFACT / PART II",
    ),
    (
        HERE,
        "Toward_a_Reliable_Drone_Correction_Pipeline.pdf",
        "DRONE CORRECTION / INTEGRATED RELIABILITY",
    ),
]:
    pages = json.loads((folder / "report_pages.json").read_text())
    out = folder / name
    c = canvas.Canvas(str(out), pagesize=landscape(A3), pageCompression=1)
    c.setTitle(pages[0]["title"])
    c.setAuthor("SpectralBridge scientific investigation")
    for i, page in enumerate(pages, 1):
        w, h = landscape(A3)
        m = 42
        c.setFillColor(colors.HexColor("#1d677a"))
        c.rect(0, h - 10, w, 10, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#163b4b"))
        c.setFont("Report", 10)
        c.drawString(m, h - 30, "SPECTRALBRIDGE / " + short + " / NOVEMBER 2026")
        y = draw(c, page["title"], m, h - 52, w - 2 * m, TITLE) - 13
        for p in page["paragraphs"]:
            y = draw(c, p, m, y, w - 2 * m, BODY) - 10
        cap = Paragraph(escape(page["caption"]), CAP)
        _, ch = cap.wrap(w - 2 * m, 2000)
        bottom = 54 + ch
        figures = [page["figure"]] + page.get("extra_figures", [])
        available = y - bottom - 12
        for j, figure in enumerate(figures):
            iw, ih = Image.open(folder / (figure + ".png")).size
            zone = available / len(figures)
            scale = min((w - 2 * m) / iw, (zone - 8) / ih)
            if scale <= 0:
                raise ValueError("No figure room")
            dw, dh = iw * scale, ih * scale
            c.drawImage(
                str(folder / (figure + ".png")),
                (w - dw) / 2,
                bottom + available - (j + 1) * zone + (zone - dh) / 2,
                width=dw,
                height=dh,
                mask="auto",
            )
        cap.drawOn(c, m, 45)
        c.setFont("Report", 9)
        c.drawString(
            m,
            23,
            "EXPERIMENTAL | Candidate reflectance calibration and inferred contributors remain unverified.",
        )
        c.drawRightString(w - m, 23, f"{i} / {len(pages)}")
        c.showPage()
    c.save()
    print(out, len(pages), "pages")
