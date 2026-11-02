"""Self-contained, large-format scientific report; bundled Python + reportlab."""

import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

HERE = Path(__file__).resolve().parent
m = json.loads((HERE / "streak_comparison_metrics.json").read_text())
r = json.loads((HERE / "replay_diagnostics.json").read_text())
v = json.loads((HERE / "radiometric_recovery_validation.json").read_text())
manifest = json.loads((HERE / "experiment_manifest.json").read_text())
output = HERE / "goldhill_radiometric_recovery_report.pdf"
W, H = landscape(A3)
margin = 45
body = W - 2 * margin
c = canvas.Canvas(str(output), pagesize=(W, H))
c.setTitle("Goldhill radiometric recovery: an isolated scientific experiment")
c.setAuthor("SpectralBridge - experimental evidence, 2 November 2026")
style = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=15, leading=21, textColor=HexColor("#263447")
)
small = ParagraphStyle("small", parent=style, fontSize=12, leading=16)
page = 0


def start(title, subtitle):
    global page
    page += 1
    c.setFillColor(HexColor("#15354b"))
    c.rect(0, H - 85, W, 85, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 23)
    c.drawString(margin, H - 37, title)
    c.setFont("Helvetica", 13)
    c.drawString(margin, H - 62, subtitle)
    c.setFillColor(HexColor("#536273"))
    c.setFont("Helvetica", 10)
    c.drawString(
        margin,
        22,
        "SpectralBridge | 2026-11-02 | Isolated experiment; physical calibration remains unverified",
    )
    c.drawRightString(W - margin, 22, f"{page} / 6")


def para(text, y, width=body, x=margin, compact=False):
    p = Paragraph(text, small if compact else style)
    _, h = p.wrap(width, H)
    p.drawOn(c, x, y - h)
    return y - h - 14


def picture(name, y, maxheight):
    img = ImageReader(str(HERE / name))
    iw, ih = img.getSize()
    scale = min(body / iw, maxheight / ih)
    w, h = iw * scale, ih * scale
    c.drawImage(img, (W - w) / 2, y - h, width=w, height=h, mask="auto")
    return y - h


def table(headers, rows, y, widths):
    rowheight = 27
    c.setFillColor(HexColor("#e6eef3"))
    c.rect(margin, y - rowheight, body, rowheight, fill=1, stroke=0)
    for n, row in enumerate([headers] + rows):
        c.setFillColor(HexColor("#263447"))
        c.setFont("Helvetica-Bold" if n == 0 else "Helvetica", 12)
        x = margin + 8
        for value, width in zip(row, widths):
            c.drawString(x, y - 18, str(value))
            x += width
        y -= rowheight
        c.setStrokeColor(HexColor("#dbe3e9"))
        c.line(margin, y, W - margin, y)
    return y - 16


start(
    "Reversing normalization does not remove the Goldhill red streak",
    "Direct replay on real imagery; recovered DN and hypothetical DN/32768 tested with fixed historical coefficients",
)
y = H - 110
y = para(
    "<b>Result:</b> All three branches retain the same diagonal red boundary. Their red correction factors are unchanged; equivalent-unit differences are float32 rounding. The recovered topographic-only control has no artificial red boundary.",
    y,
)
y = para(
    f"<b>Baseline verified:</b> {r['historical_exact_replay']['values']:,} saved production values and masks match exactly. No original TIFF, working H5, ENVI product, coefficient or spectral library was modified. SHA-256 checks cover {len(manifest['source_hashes_before'])} source/product files.",
    y,
)
rows = []
for b, label in [
    ("normalized", "Normalized"),
    ("recovered", "Recovered DN"),
    ("hypothetical", "Hypothetical DN/32768"),
]:
    d = m["branches"][b]
    rows.append(
        [
            label,
            f"{d['topo']['absolute_discontinuity_dn_equivalent']:,.3f}",
            f"{d['combined']['absolute_discontinuity_dn_equivalent']:,.0f}",
            f"{d['combined']['relative_discontinuity']:.6f}",
        ]
    )
y = table(
    [
        "Branch",
        "Topo-only jump (DN-eq)",
        "Combined jump (DN-eq)",
        "Relative combined jump",
    ],
    rows,
    y,
    [240, 250, 270, body - 760],
)
y = para(
    f"Absolute jump is the median paired absolute red difference across {m['paired_locations']:,} fixed boundary pairs, sampled 0.3-1.0 m from each side. Relative jump divides by median pooled absolute red intensity. It is a descriptive contrast, not an accuracy score. Natural vegetation variation explains the nonzero topo-only jump.",
    y,
    compact=True,
)
y = para(
    f"<b>Cause:</b> The historical observed-geometry prediction crosses zero. Its guard jumps from identity to enormous red gains (maximum {r['historical_red_factor']['quantiles_0_1_50_95_99_100'][-1]:,.0f}). The old model was unidentifiable. Repaired kernels give rank {r['validated_refit']['rank']} of 3 across {r['validated_refit']['geometry_pixels']:,} pixels, so all ten band refits remain unsupported.",
    y,
)
y = para(
    "<b>Simplest defensible next step:</b> Keep the validated rejection of unsupported BRDF; explicitly skip BRDF for this mosaic. Establish physical calibration before producing approved reflectance products. Numerical recovery can restore source-DN representation but cannot create missing angular information. Topographic-only remains a diagnostic pending separate validation.",
    y,
)
c.showPage()
start(
    "Same ground, same contrast, same red streak",
    "Raw | Topographic only | BRDF only | Combined; three radiometric branches; north-up on the unchanged 0.1 m grid",
)
picture("goldhill_radiometric_recovery_comparison.png", H - 100, H - 145)
c.showPage()
start(
    "Red-band transect: the curves overlap",
    "Equivalent recovered-DN units; the model gain jumps at the identical pixel after numerical recovery",
)
picture("goldhill_red_band_transect.png", H - 100, H - 175)
para(
    "The raw red values remain near the thousands. Historical BRDF amplifies one side into billions of DN-equivalent units. The plotted symlog axis is linear within +/-1000 and logarithmic outside. These amplified numbers have no physical validity.",
    80,
    compact=True,
)
c.showPage()
start(
    "The factor discontinuity survives unchanged",
    "Historical fixed model only; coefficients are never transferred to the repaired kernel implementation",
)
y = picture("goldhill_brdf_correction_factors.png", H - 100, 340) - 20
f = r["historical_red_factor"]
q = f["quantiles_0_1_50_95_99_100"]
y = table(
    ["Red factor diagnostic", "Source-valid pixels / value"],
    [
        [
            "Minimum / median / 95th percentile",
            f"{q[0]:,.0f} / {q[2]:,.1f} / {q[3]:,.1f}",
        ],
        ["99th percentile / maximum", f"{q[4]:,.0f} / {q[5]:,.0f}"],
        [
            "Nonpositive or invalid prediction",
            f"{f['nonpositive_or_invalid_predictions']:,}",
        ],
        [
            "Gain above 10 / above 1000",
            f"{f['gains_over_10']:,} / {f['gains_over_1000']:,}",
        ],
    ],
    y,
    [500, body - 500],
)
y = para(
    "Cyan marks the historical zero-prediction contour. The factor map is independent of input red intensity under fixed coefficients. One historical NDVI upper-edge pixel is unvisited (factor one) identically in all branches; it is retained in diagnostics. The historical guard conceals invalid predictions rather than making them nodata.",
    y,
)
para(
    f"<b>Invariance control:</b> A separate full-rank synthetic scene passed through the actual validated fit/application API at scales one and two. Both fits were VALID; factor difference was {r['supported_invariance']['max_abs_factor_difference']}. Eligibility was unchanged within 0..2. Goldhill cannot support this refit; no fit was forced.",
    y - 85,
    compact=True,
)
c.showPage()
start(
    "Spectra: numerical recovery is not calibration",
    "Ten real spectral bands at identical pixels; hypothetical DN/32768 is sensitivity analysis only",
)
y = picture("goldhill_spectral_comparison.png", H - 100, 320) - 10
y = picture("goldhill_raw_spectral_offsets.png", y, 290) - 12
para(
    "Goldhill visible-band minima are zero, so the red recovery is purely multiplicative. The NIR minimum is 174 DN and requires its own offset; a scalar cannot recover the full spectrum. The offset plot isolates this smaller effect, which the pathological corrected gains otherwise overwhelm.",
    y,
    compact=True,
)
c.showPage()
start(
    "Recovery validation, methods and production decision",
    "All 30 bands checked across Gordon, Goldhill and Ruby; original exporter and absolute radiometry remain unresolved",
)
y = H - 110
y = para(
    "<b>Inverse:</b> DN = band_min + S * (band_max - band_min) / 10000. Per-band extrema are read from the verified mapping JSON. Output is floating point, unclipped, and labelled RECOVERED_SOURCE_DN - PHYSICAL_UNITS_UNVERIFIED. The hypothetical branch divides recovered DN by 32768 without asserting project calibration.",
    y,
)
rows = []
for name, d in v.items():
    b = d["bands"][:10]
    med = max(
        x["independent_original_bilinear_comparison"]["absolute_error"][
            "quantiles_0_1_50_95_99_100"
        ][2]
        for x in b
    )
    maximum = max(
        x["independent_original_bilinear_comparison"]["absolute_error"][
            "quantiles_0_1_50_95_99_100"
        ][-1]
        for x in b
    )
    rt = max(x["max_normalized_roundtrip_error"] for x in b)
    rows.append([name.title(), f"{med:.6f}", f"{maximum:,.3f}", f"{rt:.6f}"])
y = table(
    [
        "Flight",
        "Worst band median error (DN)",
        "Largest error (DN)",
        "Round trip (normalized)",
    ],
    rows,
    y,
    [180, 340, 260, body - 780],
)
y = para(
    "Comparison uses an independent bilinear warp of original native imagery onto the existing 10 cm grid. It is not an exact replay of the unavailable exporter. Border residuals are retained without trimming; Gordon has large rare edge discrepancies. Recovery restores the numerical representation of resampled pixels, not the original native integer samples. Per-band errors and counts are in the validation JSON.",
    y,
    compact=True,
)
y = para(
    f"<b>Spatial and mask controls:</b> Source CRS, affine, resolution, band order, alpha and masks are unchanged in recovered TIFFs; inverse recovery introduces no new nonfinite pixels. Historical topography requires valid ancillary illumination and reduces {m['source_valid_pixels']:,} source pixels to {m['common_valid_pixels']:,}; this identical existing loss is retained. All comparisons use the full intersection.",
    y,
)
y = para(
    "<b>Display:</b> RGB 650/560/475 nm, common raw-reference 2-98% limits after explicit conversion to recovered-DN units. Normalized stage values use S_stage * band_range / 10000 + band_min; hypothetical stage values use rho_stage * 32768. One shared stretch applies everywhere; analytical arrays are never clipped.",
    y,
    compact=True,
)
y = para(
    "<b>Decision:</b> Recovery does not fix the streak. Do not force a BRDF fit, reuse unsupported coefficients or hide instability with a gain cap. Require calibration provenance; treat affected libraries as historical/unapproved until a reviewed correction policy supports regeneration. No production changes or library regeneration occurred.",
    y,
)
y = para(
    "<b>Reproduction:</b> provenance/drone-radiometric-recovery/2026-11-02 contains recover.py, run_experiment.py, plot_experiment.py, write_report.py and make_pdf.py. Full measured JSON and source hashes accompany the figures. Historical source is preserved byte-for-byte under GPL; its SHA matches the October 30 ablation. Large experimental rasters/arrays remain in the separate work directory recorded in experiment_manifest.json.",
    y,
    compact=True,
)
para(
    "<b>Evidence:</b> October 30 drone-scale confirmation, Goldhill stage isolation and AOP/drone radiometry/BRDF audit, plus this experiment. Native calibration, exporter provenance and independent empirical validation remain unresolved. This local full-memory historical replay is not a streaming production or large-VM benchmark.",
    y,
    compact=True,
)
c.save()
print(output)
