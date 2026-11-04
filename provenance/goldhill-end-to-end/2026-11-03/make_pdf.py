"""Render the figure-led science narrative and assert layout bounds."""

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
from reportlab.platypus import Paragraph, Table, TableStyle

HERE = Path(__file__).resolve().parent
FONTS = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("Science", str(FONTS / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("ScienceBold", str(FONTS / "Arial Bold.ttf")))
pdfmetrics.registerFontFamily("Science", normal="Science", bold="ScienceBold")
BODY = ParagraphStyle(
    "body",
    fontName="Science",
    fontSize=14,
    leading=20,
    textColor=colors.HexColor("#243746"),
    spaceAfter=5,
)
TITLE = ParagraphStyle(
    "title",
    parent=BODY,
    fontName="ScienceBold",
    fontSize=25,
    leading=31,
    textColor=colors.HexColor("#16475a"),
)
CAPTION = ParagraphStyle(
    "caption",
    parent=BODY,
    fontSize=12,
    leading=16,
    textColor=colors.HexColor("#4e6571"),
)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=12.5, leading=17)
HEAD = ParagraphStyle(
    "head", parent=CELL, fontName="ScienceBold", textColor=colors.white
)


def clean(text):
    return (
        str(text)
        .replace("\u2014", " - ")
        .replace("\u2013", "-")
        .replace("\u2011", "-")
        .replace("\u00d7", "x")
    )


def para(text, width, style=BODY):
    p = Paragraph(escape(clean(text)), style)
    _, height = p.wrap(width, 3000)
    return p, height


def draw(c, text, x, y, width, style=BODY):
    p, h = para(text, width, style)
    p.drawOn(c, x, y - h)
    return y - h


def main():
    pages = json.loads((HERE / "report_pages.json").read_text())
    path = HERE / "goldhill_end_to_end_validation.pdf"
    c = canvas.Canvas(str(path), pagesize=landscape(A3), pageCompression=1)
    c.setTitle(
        "Goldhill Reprocessing: End-to-End Validation of Corrected Drone Imagery"
    )
    c.setAuthor("SpectralBridge experimental scientific validation")
    layout = []
    for number, page in enumerate(pages, 1):
        w, h = landscape(A3)
        margin = 40
        width = w - 2 * margin
        c.setFillColor(colors.HexColor("#1b6a7e"))
        c.rect(0, h - 8, w, 8, fill=1, stroke=0)
        c.setFont("ScienceBold", 10)
        c.drawString(
            margin,
            h - 28,
            "SPECTRALBRIDGE  /  GOLDHILL END-TO-END VALIDATION  /  03 NOV 2026",
        )
        c.setFont("Science", 10)
        c.drawRightString(w - margin, h - 28, clean(page["section"]))
        c.bookmarkPage(str(number))
        c.addOutlineEntry(clean(page["title"]), str(number), level=0)
        y = h - 48
        y = draw(c, page["title"], margin, y, width, TITLE) - 12
        y = draw(c, page["intro"], margin, y, width) - 16
        if page.get("rows"):
            columns = page["columns"]
            cw = (
                [width * 0.31, width * 0.69]
                if len(columns) == 2
                else [width * 0.43, width * 0.13, width * 0.44]
            )
            rows = [[Paragraph(escape(clean(t)), HEAD) for t in columns]] + [
                [Paragraph(escape(clean(t)), CELL) for t in row] for row in page["rows"]
            ]
            table = Table(rows, colWidths=cw, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#245b6b")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.HexColor("#eff5f7"), colors.white],
                        ),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#245b6b")),
                        (
                            "LINEBELOW",
                            (0, 1),
                            (-1, -1),
                            0.3,
                            colors.HexColor("#d0dfe4"),
                        ),
                    ]
                )
            )
            _, th = table.wrap(width, 10000)
            table.drawOn(c, margin, y - th)
            y -= th + 15
        if page.get("figure"):
            figure = page["figure"]
            caption = figure["caption"]
            _, caption_h = para(caption, width, CAPTION)
            reserved = caption_h + 15
            for text in page["findings"]:
                reserved += para("- " + text, width)[1] + 9
            image = Image.open(HERE / figure["png"])
            available = y - 70 - reserved
            scale = min(width / image.width, available / image.height)
            assert scale > 0
            iw, ih = image.width * scale, image.height * scale
            c.drawImage(
                str(HERE / figure["png"]),
                margin + (width - iw) / 2,
                y - ih,
                width=iw,
                height=ih,
                preserveAspectRatio=True,
                mask="auto",
            )
            y -= ih + 9
            y = draw(c, caption, margin, y, width, CAPTION) - 12
        for text in page["findings"]:
            y = draw(c, "- " + text, margin, y, width) - 9
        for text in page["notes"]:
            y = draw(c, text, margin, y, width, CAPTION) - 7
        assert y > 44, f"Page {number} text overflow: bottom {y:.1f}"
        c.setStrokeColor(colors.HexColor("#b5cbd3"))
        c.line(margin, 35, w - margin, 35)
        c.setFont("Science", 10)
        c.setFillColor(colors.HexColor("#506875"))
        c.drawString(
            margin,
            20,
            "EXPERIMENTAL / UNCALIBRATED NUMERICAL UNITS / HISTORICAL REPLAYS ARE NOT APPROVED CORRECTIONS",
        )
        c.drawRightString(w - margin, 20, f"{number} / {len(pages)}")
        layout.append(
            dict(
                page=number,
                title=page["title"],
                lowest_content_y=y,
                page_height=h,
                page_width=w,
            )
        )
        c.showPage()
    c.save()
    (HERE / "pdf_layout.json").write_text(json.dumps(layout, indent=2) + "\n")
    print(f"{len(pages)} PDF pages written; all text bounds pass")


if __name__ == "__main__":
    main()
