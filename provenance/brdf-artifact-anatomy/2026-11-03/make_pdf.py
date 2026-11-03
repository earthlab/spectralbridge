"""Create the 19-page figure-led PDF from report_pages.json (ReportLab)."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

HERE = Path(__file__).resolve().parent
FONTROOT = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("Report", str(FONTROOT / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("ReportBold", str(FONTROOT / "Arial Bold.ttf")))
pdfmetrics.registerFontFamily("Report", normal="Report", bold="ReportBold")
BODY = ParagraphStyle(
    "body",
    fontName="Report",
    fontSize=13,
    leading=18,
    textColor=colors.HexColor("#243846"),
    alignment=TA_LEFT,
)
CAPTION = ParagraphStyle(
    "caption",
    parent=BODY,
    fontSize=11.2,
    leading=15,
    textColor=colors.HexColor("#465965"),
)
TITLE = ParagraphStyle(
    "title",
    parent=BODY,
    fontName="ReportBold",
    fontSize=23,
    leading=29,
    textColor=colors.HexColor("#163b4b"),
)


def paragraph(c, text, x, y, width, style=BODY):
    p = Paragraph(escape(text), style)
    _, h = p.wrap(width, 2000)
    p.drawOn(c, x, y - h)
    return y - h


def main():
    pages = json.loads((HERE / "report_pages.json").read_text())
    c = canvas.Canvas(
        str(HERE / "anatomy_of_a_red_artifact.pdf"),
        pagesize=landscape(A3),
        pageCompression=1,
    )
    c.setTitle("Anatomy of a Red Artifact")
    c.setAuthor("SpectralBridge — read-only scientific reconstruction")
    for n, page in enumerate(pages, 1):
        w, h = A3 if page.get("portrait") else landscape(A3)
        c.setPageSize((w, h))
        margin = 36
        c.setFillColor(colors.HexColor("#1d677a"))
        c.rect(0, h - 9, w, 9, fill=1, stroke=0)
        c.setFont("Report", 10)
        c.drawString(
            margin,
            h - 28,
            "SPECTRALBRIDGE  /  ANATOMY OF A RED ARTIFACT  /  03 NOVEMBER 2026",
        )
        y = h - 48
        if n == 1:
            y = (
                paragraph(
                    c, "Anatomy of a Red Artifact", margin, y, w - 2 * margin, TITLE
                )
                - 5
            )
            y = (
                paragraph(
                    c,
                    "How Missing Viewing Geometry and an Unsupported BRDF Model Corrupted the Goldhill Drone Orthomosaic",
                    margin,
                    y,
                    w - 2 * margin,
                    BODY,
                )
                - 10
            )
        y = paragraph(c, page["title"], margin, y, w - 2 * margin, TITLE) - 12
        if "figure" in page:
            # Put the scientific statement above the image; keep caption immediately below it.
            for text in page["paragraphs"]:
                y = paragraph(c, text, margin, y, w - 2 * margin) - 8
            cap = Paragraph(escape(page["caption"]), CAPTION)
            _, cap_h = cap.wrap(w - 2 * margin, 2000)
            bottom = 48 + cap_h + 12
            path = HERE / (page["figure"] + ".png")
            iw, ih = Image.open(path).size
            scale = min((w - 2 * margin) / iw, (y - bottom) / ih)
            if scale <= 0:
                raise ValueError(f"No figure room on page {n}")
            dw, dh = iw * scale, ih * scale
            c.drawImage(
                str(path),
                (w - dw) / 2,
                bottom + (y - bottom - dh) / 2,
                width=dw,
                height=dh,
                preserveAspectRatio=True,
                mask="auto",
            )
            cap.drawOn(c, margin, 48)
        else:
            for text in page["paragraphs"]:
                y = paragraph(c, text, margin, y, w - 2 * margin) - 14
            if page.get("coefficient_table"):
                fit = json.loads(
                    (HERE / "historical_fit_reconstruction.json").read_text()
                )
                bands = {
                    b["band"]: b
                    for b in json.loads((HERE / "band_diagnostics.json").read_text())
                    if b["flight"] == "goldhill"
                }
                rows = [
                    [
                        "nm",
                        "eligible",
                        "rank",
                        "iso",
                        "vol",
                        "geo",
                        "reference",
                        "max factor",
                    ]
                ]
                for r in fit:
                    b = bands[r["band"]]
                    rows.append(
                        [
                            str(r["wavelength_nm"]),
                            str(r["eligible_pixels"]),
                            str(r["rank"] or "neutral"),
                            *[f"{v:.7g}" for v in r["actual_coefficients"]],
                            f"{b['predicted_reference']['median']:.7g}",
                            f"{b['factor_full_H5']['max']:.7g}",
                        ]
                    )
                table = Table(rows, colWidths=[55, 65, 70, 150, 150, 150, 150, 150])
                table.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -1), "Report"),
                            ("FONTSIZE", (0, 0), (-1, -1), 11),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                            ("TOPPADDING", (0, 0), (-1, -1), 7),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e1edf0")),
                            (
                                "LINEBELOW",
                                (0, 0),
                                (-1, 0),
                                1,
                                colors.HexColor("#1d677a"),
                            ),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#f5f7f8")],
                            ),
                        ]
                    )
                )
                tw, th = table.wrap(w - 2 * margin, y)
                if y - th < 45:
                    raise ValueError("Appendix table does not fit")
                table.drawOn(c, margin, y - th)
            elif y < 45:
                raise ValueError(f"Text overflows page {n}")
        c.setFillColor(colors.HexColor("#687b84"))
        c.setFont("Report", 9)
        c.drawString(
            margin,
            23,
            "Actual data • unchanged historical coefficients • no production writes • numerical encoding ≠ calibrated reflectance",
        )
        c.drawRightString(w - margin, 23, f"{n} / {len(pages)}")
        c.showPage()
    c.save()
    print(f"Created {len(pages)} pages")


if __name__ == "__main__":
    main()
