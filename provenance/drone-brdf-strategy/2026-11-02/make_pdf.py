"""Large, legible seven-page scientific report, using bundled reportlab."""

import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

HERE = Path(__file__).resolve().parent
flights = json.loads((HERE / "flight_analysis.json").read_text())
manifest = json.loads((HERE / "manifest.json").read_text())
W, H = landscape(A3)
margin = 44
body = W - 2 * margin
path = HERE / "drone_radiometric_brdf_correction_strategy.pdf"
c = canvas.Canvas(str(path), pagesize=(W, H))
c.setTitle("Drone Radiometric and BRDF Correction: What the Data Actually Support")
c.setAuthor("SpectralBridge | isolated three-flight investigation | 2026-11-02")
style = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=14, leading=19, textColor=HexColor("#263746")
)
small = ParagraphStyle("small", parent=style, fontSize=11.5, leading=15)
page = 0


def start(title, subtitle):
    global page
    page += 1
    c.setFillColor(HexColor("#173f50"))
    c.rect(0, H - 85, W, 85, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(margin, H - 35, title)
    c.setFont("Helvetica", 12)
    c.drawString(margin, H - 62, subtitle)
    c.setFillColor(HexColor("#5b6a72"))
    c.setFont("Helvetica", 10)
    c.drawString(
        margin,
        21,
        "SpectralBridge | 2026-11-02 | Recovered DN, physical units unverified | No production artifacts modified",
    )
    c.drawRightString(W - margin, 21, f"{page} / 7")


def para(text, y, compact=False):
    p = Paragraph(text, small if compact else style)
    _, h = p.wrap(body, H)
    p.drawOn(c, margin, y - h)
    return y - h - 14


def picture(name, y, maxheight):
    image = ImageReader(str(HERE / name))
    iw, ih = image.getSize()
    scale = min(body / iw, maxheight / ih)
    w, h = iw * scale, ih * scale
    c.drawImage(image, (W - w) / 2, y - h, width=w, height=h, mask="auto")
    return y - h


def table(headers, rows, y, widths):
    height = 28
    c.setFillColor(HexColor("#e5eff1"))
    c.rect(margin, y - height, body, height, fill=1, stroke=0)
    for i, row in enumerate([headers] + rows):
        c.setFillColor(HexColor("#263746"))
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 12)
        x = margin + 8
        for item, width in zip(row, widths):
            c.drawString(x, y - 19, str(item))
            x += width
        y -= height
        c.setStrokeColor(HexColor("#dce5e8"))
        c.line(margin, y, W - margin, y)
    return y - 18


start(
    "Drone Radiometric and BRDF Correction: What the Data Actually Support",
    "Gordon, Goldhill and Ruby 2023 | Real mosaics, matched researcher polygons, shared validity gates",
)
y = H - 108
y = para(
    "<b>1. What information do the mosaics contain?</b> Spatially validated ten-band imagery, terrain, smooth solar grids and scalar nadir view placeholders. The files do not identify the camera observations or blend weights contributing to each ortho pixel. Physical calibration and acquisition-date/timezone provenance remain unresolved.",
    y,
)
y = para(
    "<b>2. Can any support the current Ross-Li fit?</b> No. Every flight has rank one for three model parameters. Millions of cells and distinct floating-point solar values do not create independent viewing information. Thirty of thirty band fits are unsupported; no coefficients were forced or applied.",
    y,
)
rows = []
for name in ["gordon", "goldhill", "ruby"]:
    d = flights[name]["angular"]
    rows.append(
        [
            name.title(),
            f"{d['source_valid_pixels']:,}",
            d["rank"],
            f"{d['condition_number']:.2g}",
            f"{d['stable_rank']:.1f}",
            "0 / 10",
        ]
    )
y = table(
    [
        "Flight",
        "Valid source pixels",
        "Rank / 3",
        "Condition number",
        "Effective dimensions",
        "Supported / unsupported",
    ],
    rows,
    y,
    [135, 210, 125, 205, 190, body - 865],
)
y = para(
    "<b>3. Which corrections improve consistency?</b> Topographic DN sensitivity is mixed: variance falls in 8 of 12 sufficiently sampled flight/category cells, while median band CV falls in 6 and rises in 6. Gains reach 528x and coverage falls by 1.49-5.49%. This does not establish a blanket topographic correction benefit or physical accuracy.",
    y,
)
y = para(
    "<b>4. How should drone and NEON differ?</b> Share the equations and physical-unit contracts; require actual geometry and independent eligibility for every dataset. NEON directional-flightline observation geometry is a different input contract from these drone placeholders. Product revision and previous correction state must also be checked.",
    y,
)
y = para(
    "<b>5. What should change?</b> Preserve recovered DN as the temporary numerical baseline; omit unsupported BRDF; require calibration and validated illumination/terrain before promoting physical or topographic products. Use explicit stage states and scientific QA. Useful no-BRDF libraries are possible after those prerequisites, with a documented directional domain.",
    y,
)
para(
    "This is an isolated experiment, not a production repair. Raw-photo BRDF remains a future possibility if calibrated images, poses, repeated targets and stable illumination can be recovered. The available metadata CSVs contain filenames/times/software only; their August 15 timestamps conflict with August 14 notes. No globally exhaustive archive search or new empirical NEON cohort was performed.",
    y,
    compact=True,
)
c.showPage()
start(
    "Angular information: a rank-one design in all three flights",
    "Full-scene rank diagnostics; small solar raster gradients are not recovered per-photo viewing angles",
)
y = picture("figure1_angular_information.png", H - 100, H - 185)
para(
    "Rank and singular values use every source-valid spectral/angle location. Histograms are display-sampled only. Stable rank is an effective matrix dimension, not an independent-image sample count; that count is unknown. The unchanged condition limit is about 2,896; the observed condition numbers exceed 10^24.",
    y - 5,
    compact=True,
)
c.showPage()
start(
    "Full-flight comparison: approved BRDF branches are unsupported",
    "Same grid, RGB bands and raw-reference contrast per flight; topographic panels are numerical sensitivity only",
)
y = picture("figure2_correction_comparison.png", H - 100, H - 170)
para(
    "No valid BRDF or combined corrected raster was substituted. Topographic-only approval is also held: illumination, terrain and physical units are unverified. The shown SCS+C replay isolates numerical behavior with existing embedded geometry. Native-resolution matched regions are provided separately in Figure 2b and the Markdown report.",
    y - 5,
    compact=True,
)
c.showPage()
start(
    "Goldhill: avoid the unsupported correction that creates the streak",
    "Historical invalid model shown only as a diagnostic; current temporary baseline remains uncalibrated DN",
)
y = picture("figure3_goldhill_red_streak.png", H - 100, 340) - 15
y = para(
    "The earlier exact replay matched all 70,832,700 production values. Inverse normalization changed the red boundary metric by only 0.00000501%; the same historical factors still reach 11.7 million. The current repaired kernel has rank one, so it rejects this unsupported fit. Removing the artifact does not prove physical calibration.",
    y,
)
rows = []
for name in ["gordon", "goldhill", "ruby"]:
    d = flights[name]
    n = d["angular"]["source_valid_pixels"]
    lost = n - d["common_mask"]
    gain = max(
        x["topo_factor"]["quantiles_0_1_25_50_75_99_100"][-1]
        for x in d["topographic_diagnostic_per_band"]
    )
    rows.append(
        [
            name.title(),
            f"{lost:,} ({100 * lost / n:.2f}%)",
            f"{gain:.2f}x",
            f"{sum(x['gains_over_10'] for x in d['topographic_diagnostic_per_band']):,}",
        ]
    )
y = table(
    [
        "Flight",
        "Pixels lost to topo geometry",
        "Maximum topo factor",
        "Band-pixel factors above 10",
    ],
    rows,
    y,
    [150, 330, 250, body - 730],
)
para(
    "Large SCS+C factors and invalid ancillary masks require separate fit/denominator and terrain review. No gain cap was introduced. Topographic output is not approved merely because it avoids the red BRDF boundary. No additional fitted normalization was justified: invariant targets, calibrated overlaps and matched cross-flight polygons are unavailable.",
    y,
    compact=True,
)
c.showPage()
start(
    "Spectral consequences: matched polygons, mixed outcomes",
    "One median spectrum per polygon; researcher labels preserved; lower variation alone is not accuracy",
)
y = picture("figure4_spectral_consequences.png", H - 100, H - 190)
para(
    "301 polygons and 198,309 matched polygon-pixel memberships were checked independently against geometry. Categories require at least five retained polygon units; Ruby shrubs are insufficient. Non-vegetated & dead is a cover comparator, not a biological PFT. Solid/dashed curves use the same raw/topographic-valid pixels; shaded ranges are polygon IQRs.",
    y - 5,
    compact=True,
)
c.showPage()
start(
    "Correction performance: no uniform improvement",
    "Numerical dispersion, spatial-blocked class contrasts and source-wide stability must be considered together",
)
y = picture("figure5_correction_performance.png", H - 100, H - 190)
para(
    "Ten-band class contrasts reuse the package separability API: 1,999 permutations within 100 m spatial blocks, one spectrum per identity, equal discrete band weights and Holm correction across 34 supported tests; 10 comparisons lack support. These are conditional observational associations, not prediction accuracy or tests of correction-caused improvement. No pixel-random split was used. Residual spatial dependence remains a limitation.",
    y - 5,
    compact=True,
)
c.showPage()
start(
    "Proposed production workflow: share implementations, gate eligibility",
    "Proposal only; preserve source grids and historical products, then approve calibration and correction policy before regeneration",
)
y = picture("figure6_recommended_pipeline.png", H - 100, 480) - 12
y = para(
    "<b>Acceptance:</b> verified source calibration and per-band recovery provenance; authoritative date/timezone and terrain conventions; independent topographic stability and held-out checks; genuine angular provenance, rank, conditioning and supported reference predictions for BRDF; compatible physical-unit translation coefficients and native-library provenance.",
    y,
    compact=True,
)
y = para(
    "<b>Next data request:</b> original SD1/SD2 photos, panel/DLS/exposure records, Metashape project or intrinsics/extrinsics, DSM and per-image target overlap. Test repeated targets before committing to pre-mosaic BRDF. Do not infer calibration from export range or camera-file count. Current libraries and dependent translated/bulk contributions remain historical/unapproved until a reviewed fresh run.",
    y,
    compact=True,
)
y = para(
    "Reproduction and measured evidence: provenance/drone-brdf-strategy/2026-11-02/ (analyze.py, figures.py, report.py, metadata_audit.py, make_pdf.py; per-flight JSON and polygon/class tables). The Markdown report and separate production plan document assumptions, stage states, source hashes, original-archive search limits and narrow regression requirements.",
    y,
    compact=True,
)
para(
    "Primary context: NEON radiance-to-reflectance ATBD revision B (data.neonscience.org/api/v0/documents/NEON.DOC.001288vB); NEON bidirectional reflectance tutorial (neonscience.org/resources/learning-hub/tutorials/neon-brdf-refl-h5-py); Agisoft MicaSense reflectance-calibration workflow (agisoft.freshdesk.com, solution 31000148780). Provider/vendor documentation does not validate these drone project settings.",
    y,
    compact=True,
)
c.save()
print(path)
