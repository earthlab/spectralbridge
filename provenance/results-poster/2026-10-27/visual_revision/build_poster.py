"""White package overview poster; existing real images are illustrative only."""

from pathlib import Path
import hashlib
import io
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader, PdfWriter, Transformation

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
IMAGES = BASE.parent / "flightline_revision"
OUT = ROOT / "output/pdf/results_poster/SpectralBridge_Visual_Poster.pdf"
W, H = 2592, 3456
INK = "#183440"
MUTED = "#526873"
TEAL = "#176E65"
RULE = "#D9E5E4"
PALE = "#F4F8F7"
buffer = io.BytesIO()
c = canvas.Canvas(buffer, pagesize=(W, H))
c.setTitle("SpectralBridge | From flightlines to analysis-ready data")
c.setAuthor("SpectralBridge | Earth Lab")
c.setSubject(
    "Core package functions: processing, correction, sensor-like products, exports, quality checks, bulk and library analysis"
)
c.setFillColor(HexColor("#FFFFFF"))
c.rect(0, 0, W, H, fill=1, stroke=0)
boxes = []


def text(x, y, s, size=30, color=INK, bold=False, font=None):
    font = font or ("Helvetica-Bold" if bold else "Helvetica")
    tw = stringWidth(s, font, size)
    assert 0 <= x and x + tw < W - 70, (s, x + tw)
    assert 0 < y < H - size
    c.setFillColor(HexColor(color))
    c.setFont(font, size)
    c.drawString(x, y, s)
    boxes.append([x, y, tw, size, s])


def line(x1, y1, x2, y2, color=RULE, width=2):
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)


def marker(x, y):
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(HexColor(TEAL))
    c.setLineWidth(4)
    c.circle(x, y, 25, fill=1, stroke=1)
    c.setFillColor(HexColor(TEAL))
    c.setFont("Helvetica-Bold", 27)
    c.drawCentredString(x, y - 10, "A")


text(
    108, 3344, "E A R T H  L A B   /   S C I E N T I F I C  P Y T H O N", 25, TEAL, True
)
text(108, 3200, "SpectralBridge", 124, bold=True)
text(112, 3110, "From flightlines to analysis-ready data", 62, bold=True)
text(
    112,
    3045,
    "Prepare and compare reflected light across airborne, drone and sensor-like products.",
    34,
    MUTED,
)

# Large real-data examples remain supporting illustrations, not a before/after claim.
text(108, 2954, "REAL FLIGHTLINE  /  VISIBLE LIGHT", 26, TEAL, True)
text(1450, 2954, "A flightline is the strip recorded along one flight path.", 26, MUTED)
ix, iw = 108, 2376
ih = iw * 1115 / 5351
for name, iy in [("visible", 2420), ("near_infrared", 1790)]:
    c.drawImage(str(IMAGES / (name + ".png")), ix, iy, width=iw, height=ih, mask="auto")
    marker(ix + iw * 0.698, iy + ih * 0.73)
text(108, 2323, "SAME GROUND  /  INFRARED SHOWN IN RED", 26, TEAL, True)
text(1450, 2323, "A marks the same patch in both images.", 26, MUTED)
text(
    108,
    1726,
    "The same ground, shown with different light channels. A marks the same patch.",
    31,
    MUTED,
)
text(
    108,
    1677,
    "Red is a display color, not heat or fire. These views do not show correction improvement.",
    27,
    MUTED,
)

text(108, 1582, "Read the spectral patterns", 46, bold=True)
text(1344, 1582, "Turn spectra into sensor bands", 46, bold=True)
text(108, 1524, "Groups reflect different patterns across wavelengths.", 29, MUTED)
text(
    1344, 1524, "The package weights wavelength ranges for a target sensor.", 29, MUTED
)
# The chart PDFs are merged below as original vector content.
text(108, 570, "Bold curves: category medians. Bands: middle 50%.", 28, TEAL, True)
text(108, 526, "Gray gaps omit unsupported spectral regions.", 26, MUTED)
text(1344, 570, "A detailed spectrum becomes fewer sensor channels.", 28, TEAL, True)
text(1344, 526, "Gaussian weights shown; not measured response curves.", 26, MUTED)

line(108, 482, 2484, 482)
text(108, 421, "One package, from imagery to reusable science", 38, bold=True)
steps = [
    (108, "01  Prepare", "NEON or supported drone inputs"),
    (726, "02  Correct", "Terrain + viewing geometry"),
    (1344, "03  Translate", "Configured sensor-like bands"),
    (1962, "04  Explore", "Tables, QA, bulk + libraries"),
]
for x, title, detail in steps:
    c.setFillColor(HexColor(PALE))
    c.roundRect(x, 258, 522, 113, 14, fill=1, stroke=0)
    text(x + 20, 326, title, 30, TEAL, True)
    text(x + 20, 285, detail, 23, MUTED)
text(
    108,
    207,
    "Restart-safe files. Chunked processing. Traceable outputs.",
    28,
    TEAL,
    True,
)
text(108, 159, "earthlab.github.io/spectralbridge", 27)
c.linkURL(
    "https://earthlab.github.io/spectralbridge/", (108, 153, 1000, 190), relative=0
)
text(1390, 159, "github.com/earthlab/spectralbridge", 27)
c.linkURL(
    "https://github.com/earthlab/spectralbridge", (1390, 153, 2460, 190), relative=0
)
text(
    108,
    116,
    "Spectral graphs: saved polygon/year library summaries; separate from the illustrated R10C flightline. Physical-unit scaling unresolved.",
    22,
    MUTED,
)
text(
    108,
    78,
    "Flightline: NEON R10C, 15 September 2021, native 1 m pixels. Display: 2-98% stretch, gamma 0.8; blank exterior has no data.",
    22,
    MUTED,
)
text(
    108,
    40,
    "Configured sensor-like bands do not establish independent sensor agreement or field cover accuracy. | Earth Lab | 27 October 2026",
    22,
    MUTED,
)
c.showPage()
c.save()
page = PdfReader(buffer).pages[0]
for name, x in [("category_spectra", 108), ("sensor_weights", 1344)]:
    plot = PdfReader(BASE / (name + ".pdf")).pages[0]
    scale = 1140 / float(plot.mediabox.width)
    assert 620 + float(plot.mediabox.height) * scale < 1490
    page.merge_transformed_page(plot, Transformation().scale(scale).translate(x, 620))
writer = PdfWriter()
writer.add_page(page)
writer.add_metadata(
    {
        "/Title": "SpectralBridge | Flightlines, spectra and sensor bands",
        "/Author": "SpectralBridge | Earth Lab",
    }
)
with OUT.open("wb") as f:
    writer.write(f)
r = PdfReader(OUT)
assert len(r.pages) == 1
assert list(map(float, r.pages[0].mediabox)) == [0.0, 0.0, float(W), float(H)]
t = r.pages[0].extract_text()
for s in [
    "Read the spectral patterns",
    "Turn spectra into sensor bands",
    "Gaussian weights",
    "01  Prepare",
    "02  Correct",
    "03  Translate",
    "04  Explore",
    "separate from the illustrated",
]:
    assert s in t, s
sources = [
    BASE / "category_spectra.pdf",
    BASE / "sensor_weights.pdf",
    ROOT / "provenance/manuscript-synthesis/2026-10-16/v1/data/A_category_spectra.csv",
    ROOT / "src/spectralbridge/data/landsat_band_parameters.json",
    ROOT / "provenance/manuscript-synthesis/2026-10-16/v1/figure_data_manifest.json",
    ROOT / "README.md",
    ROOT / "src/spectralbridge/__init__.py",
    ROOT / "docs/pipeline.md",
    ROOT / "docs/vignettes/bulk-analysis.md",
    ROOT / "docs/vignettes/spectral-library.md",
    IMAGES / "visible.png",
    IMAGES / "near_infrared.png",
    IMAGES / "imagery_manifest.json",
]
(BASE / "manifest.json").write_text(
    json.dumps(
        {
            "output": str(OUT.relative_to(ROOT)),
            "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
            "size_inches": [36, 48],
            "background": "white",
            "image_dpi": 5351 / (iw / 72),
            "source_flights": 1,
            "views": 2,
            "source_hashes": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sources
            },
            "checks": [
                "one page",
                "36 x 48 inches",
                "required functions and caveats present",
                "text within page/card widths",
            ],
            "scientific_analysis_rerun": False,
            "graphs": "Saved median/IQR curves plus configured Gaussian weighting diagram; no model fitting",
        },
        indent=2,
    )
    + "\n"
)
(BASE / "layout_boxes.json").write_text(json.dumps(boxes, indent=2) + "\n")
print(OUT)
