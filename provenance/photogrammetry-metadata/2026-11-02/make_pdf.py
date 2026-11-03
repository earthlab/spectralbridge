"""One unified, figure-heavy provenance report with literature and project evidence."""

from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

HERE = Path(__file__).resolve().parent
a = json.loads((HERE / "validation.json").read_text())
lit = json.loads((HERE / "literature.json").read_text())
W, H = landscape(A3)
M = 44
BODY = W - 2 * M
path = HERE / "where_did_the_drone_geometry_go.pdf"
c = canvas.Canvas(str(path), pagesize=(W, H))
c.setTitle(
    "Where Did the Drone Geometry Go? Tracing Photogrammetry Metadata into SpectralBridge"
)
c.setAuthor("SpectralBridge | read-only provenance investigation | 2026-11-02")
style = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=14, leading=19, textColor=HexColor("#233d4c")
)
small = ParagraphStyle("small", parent=style, fontSize=11.5, leading=15)
page = 0


def start(title, subtitle):
    global page
    page += 1
    c.setFillColor(HexColor("#153e50"))
    c.rect(0, H - 85, W, 85, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 21)
    c.drawString(M, H - 35, title)
    c.setFont("Helvetica", 12)
    c.drawString(M, H - 62, subtitle)
    c.setFillColor(HexColor("#596e7b"))
    c.setFont("Helvetica", 10)
    c.drawString(
        M,
        21,
        "SpectralBridge | 2026-11-02 | Observed evidence / code fingerprint / unknown settings kept distinct | Production unchanged",
    )
    c.drawRightString(W - M, 21, f"{page} / 8")


def para(text, y, compact=False):
    p = Paragraph(text, small if compact else style)
    _, h = p.wrap(BODY, H)
    p.drawOn(c, M, y - h)
    return y - h - 13


def picture(name, y, maxheight):
    r = ImageReader(str(HERE / name))
    iw, ih = r.getSize()
    scale = min(BODY / iw, maxheight / ih)
    w, h = iw * scale, ih * scale
    c.drawImage(r, (W - w) / 2, y - h, width=w, height=h, mask="auto")
    return y - h


def table(headers, rows, y, widths):
    height = 27
    c.setFillColor(HexColor("#e5edf1"))
    c.rect(M, y - height, BODY, height, fill=1, stroke=0)
    for i, row in enumerate([headers] + rows):
        c.setFillColor(HexColor("#233d4c"))
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 11.5)
        x = M + 7
        for item, width in zip(row, widths):
            c.drawString(x, y - 18, str(item))
            x += width
        y -= height
        c.setStrokeColor(HexColor("#dce5e8"))
        c.line(M, y, W - M, y)
    return y - 15


start(
    "Where Did the Drone Geometry Go?",
    "Tracing Photogrammetry Metadata into SpectralBridge | Gordon, Goldhill and Ruby 2023 | Unified literature/provenance report",
)
y = H - 110
y = para(
    "<b>What existed?</b> All three reports identify Metashape Professional 1.8.3 build 14331 and document aligned-camera/lens geometry. Camera/location information was therefore estimated. The corresponding machine-readable projects, poses and source-contribution exports were not recovered; their existence elsewhere is not ruled out.",
    y,
)
y = para(
    "<b>What reached SpectralBridge?</b> TIFFs retained spectral pixels and spatial metadata, but no source-camera rays. Archived TIFF-to-H5 code deliberately inserts zero view matrices. The October 29 recipe copies those values into scalar fields, and the reader broadcasts them. Neither a NEON-compatible field name nor a finite-scalar check turns them into measured views.",
    y,
)
y = para(
    "<b>What was recomputed?</b> The original H5 solar grids match a two-error PyEphem fingerprint at all 75 sampled locations. Working H5s instead record manifest-computed solar and reproduce the actual NOAA calculation exactly at all 75 locations. Independent SPA differs about 0.26 degrees in zenith at those configured times. Dates remain unresolved, especially Ruby.",
    y,
)
y = para(
    "<b>What did Metashape already correct?</b> Reflectance-panel, DLS, exposure/gain, vignette, brightness/color balance, block-adjustment and angular-normalization states remain UNKNOWN. Lens precalibration and Mosaic blending are not evidence of those operations or physical reflectance. No duplicate correction is established, but unknown upstream processing prevents ruling it out.",
    y,
)
y = para(
    "<b>Why are topographic gains large?</b> Existing SCS+C outputs replay exactly. The fitting matrices have condition numbers 11-15, but cosine incidence plus fitted C approaches the 0.001 guard. This explains gains of 528x, 357x and 373x without proving a terrain-unit mismatch. Terrain provenance and shadow handling remain separate concerns.",
    y,
)
y = para(
    "<b>Can we recover without rebuilding?</b> Solar metadata and physical encoding may be recoverable once authoritative logs/settings are supplied. Camera rays for blended pixels require project/contributor information; one angle map cannot recreate repeated source observations. Original-image block or angular correction remains conditional on calibrated overlapping observations and validation.",
    y,
)
para(
    "<b>Smallest next step:</b> Obtain the matching project plus .files/task settings, calibrated-image references and authoritative timestamp evidence; inspect a small overlapping subset before new photogrammetry. Preserve the current rank-one rejection and all original libraries. This report corrects P161's incomplete solar-origin account without changing its measured rank or spectral results.",
    y,
)
c.showPage()
start(
    "1. What information was generated, and what travelled downstream?",
    "A documented file/code chain, with missing project-to-export links shown explicitly",
)
y = picture("figure1_metadata_provenance.png", H - 100, H - 185)
para(
    "Report project dimensions differ from some exported TIFFs; Ruby is explicitly clipped. These snapshots establish that geometric estimation occurred, not that every report setting describes the exact final export. Storage owners, Git snapshot authors and notebook counters are not identified as the original human executors.",
    y - 6,
    compact=True,
)
c.showPage()
start(
    "2. The zero-valued viewing angles are placeholders",
    "Actual upstream arrays and working metadata; no recovered camera map is fabricated",
)
y = picture("figure2_viewing_geometry.png", H - 100, 500) - 14
y = para(
    "The archived tiff_to_h5 function explicitly creates np.zeros(img_shape) for view zenith and azimuth. prepare_reference reads source matrices, checks constancy, stores source_recipe.json and supplies scalar options to the TIFF bridge. NeonCube.get_ancillary broadcasts supplied scalars; missing angles raise rather than default to zero.",
    y,
)
para(
    "Reports contain camera calibration and estimated-location evidence, but no usable per-pixel contributor export was found. The first recovered code snapshot is April 23, 2025; it is not a proven code-creation or per-flight execution date. The old solar numerical fingerprint strongly supports code lineage without identifying a human executor.",
    y,
    compact=True,
)
c.showPage()
start(
    "3. Solar geometry has a traceable origin, but uncertain acquisition times",
    "Old bugs reproduced; working NOAA replay separated from independent SPA and date/time hypotheses",
)
y = picture("figure3_solar_geometry.png", H - 100, H - 215) - 8
y = para(
    "Old PyEphem code supplies degree-valued numeric latitude/longitude as radians and subtracts radian sun altitude from 90 degrees. New working solar is per-pixel location at one manifest time, with no per-photo timing or DEM/refraction term. SPA uses zero pressure/altitude for geometric-angle comparison. Exact replay is not acquisition truth.",
    y,
    compact=True,
)
para(
    "Notes: August 14. Camera CSVs: August 15 without timezone. Executed manifest: August 15 for Gordon/Goldhill and August 16 for Ruby. UTC/Denver conversion alone does not reconcile them; similar sun positions on adjacent dates cannot identify the true date. See the full candidate table in solar_candidate_comparison.csv.",
    y,
    compact=True,
)
c.showPage()
start(
    "4. Terrain metadata and high gains are related questions, not one assumption",
    "Exact TIFF/H5 terrain equality; independent derivatives; exact SCS+C denominator replay",
)
y = picture("figure4_terrain_geometry.png", H - 100, 400) - 10
rows = []
for n in ["gordon", "goldhill", "ruby"]:
    b = max(a[n]["topography_bands"], key=lambda b: b["max_gain_location"]["factor"])
    g = b["max_gain_location"]
    t = a[n]["terrain"]["aligned_dem_derivative_comparison"]
    rows.append(
        [
            n.title(),
            f"{t['slope_absolute_error']['q0_1_50_99_100'][2]:.3f} deg",
            f"{g['factor']:.2f}x",
            f"{g['cosine_incidence']:+.6f}",
            f"{g['C']:+.6f}",
            f"{g['denominator']:.6f}",
        ]
    )
y = table(
    ["Flight", "Median slope residual", "Worst gain", "cos(i)", "C", "cos(i) + C"],
    rows,
    y,
    [145, 240, 160, 190, 180, BODY - 915],
)
y = para(
    "The paired aligned elevation supports an independent Horn check, not proof of exact terra execution. R scripts intend degree slope/aspect, ground classification/0.25 m TIN and scalar bilinear resampling; source surface/version and derivative order remain unresolved. True-North solar versus grid-North terrain conventions require explicit verification.",
    y,
    compact=True,
)
para(
    "All 30 existing DN topographic band outputs replay exactly. The worst denominators sit just above 0.001; formal pixel-OLS C uncertainty is comparable or greater and assumes independent residuals. Gordon/Ruby worst cases have back-facing incidence; Goldhill cancels positive incidence with negative C. No correction algorithm, metadata replacement or gain cap was implemented.",
    y,
    compact=True,
)
c.showPage()
start(
    "5. UInt16 encoding and upstream radiometric operations remain unverified",
    "Numerical recovery is established; physical reflectance and duplicate corrections are not",
)
y = picture("figure5_radiometric_provenance.png", H - 100, 360) - 10
rows = [
    [
        "Panel / DLS / exposure / vignette",
        "UNKNOWN",
        "Missing project flags and raw calibration records",
    ],
    [
        "Radiometric block adjustment / BRDF",
        "UNKNOWN",
        "No evidence of upstream execution or confirmed duplication",
    ],
    [
        "Brightness or color balancing",
        "UNKNOWN",
        "Mosaic mode is not proof of balancing",
    ],
    [
        "Mosaic blending",
        "Reported for Gordon/Ruby",
        "Goldhill ortho task and exact final export link unresolved",
    ],
    [
        "UInt16 physical reflectance encoding",
        "UNVERIFIED",
        "No guessed 1/10000 or 1/32768 calibration",
    ],
]
y = table(
    ["Operation / interpretation", "State", "Evidence limit"],
    rows,
    y,
    [420, 190, BODY - 610],
)
para(
    "Geometric lens precalibration is not radiometric calibration. The known bandwise inverse restores numerical values, including NIR offsets, but cannot undo unknown upstream image balancing or establish absolute units. Retrieve panel/DLS/exposure, Normalize band sensitivity and export/colour-operation records, potentially differing by band and flight.",
    y,
    compact=True,
)
c.showPage()
start(
    "Recovery: inspect metadata first, then decide whether images need reprocessing",
    "No production modification, orthomosaic reconstruction or spectral-library regeneration was performed",
)
y = picture("figure6_recovery_options.png", H - 100, 450) - 12
y = para(
    "<b>Priority 1:</b> Matching Metashape .psx/.psz with complete .files and task/settings records; camera/sensor/chunk transforms, source references and project-to-TIFF identity. <b>Priority 2:</b> Panel/DLS/exposure data and actual radiometric/colour/export settings. <b>Priority 3:</b> Authoritative date/timezone and exact terrain-generation records.",
    y,
    compact=True,
)
y = para(
    "<b>Minimal implementation proposal:</b> A read-only, version-aware metadata sidecar/preflight using existing TIFF/H5 readers and project inspection. Preserve observed/derived/placeholder status, calibration equations, units, correction-operation states and source hashes. Missing flags are not false. Do not create measured angles or calibrated reflectance by default.",
    y,
    compact=True,
)
para(
    "For an existing blend, contributor-specific rays and weights must remain separate. They do not by themselves recreate multiple same-target reflectance observations. If original calibrated overlapping images and trustworthy poses/terrain become available, test a bounded subset with held-out targets/angles before choosing no-extra-BRDF, radiometric block adjustment or an angular model.",
    y,
    compact=True,
)
c.showPage()
start(
    "What the UAV BRDF Literature Tells Us About Our Pipeline",
    "Methods verified in all four full papers; published possibilities are distinct from actual project evidence",
)
y = picture("figure7_literature_pipeline.png", H - 100, 300) - 10
short = [
    (
        "Honkavaara & Khoramshahi 2018",
        "Joint weighted radiometric tie-point/panel adjustment with image and anisotropy terms; camera/DSM visibility before output mosaics.",
        "10.3390/rs10020256",
    ),
    (
        "Crucil et al. 2022",
        "Calibrated images and adjusted geometry support pre-mosaic ANIF; homogeneous bare-soil assumptions do not transfer automatically to PFTs.",
        "10.3390/rs14030537",
    ),
    (
        "Ahn et al. 2025",
        "Purpose-designed tarp/irradiance/dome/vignette/validation flights support image filters; seam quality is not biological accuracy.",
        "10.3390/rs17010151",
    ),
    (
        "Cao et al. 2023",
        "Planned target-centred views, panels and camera geometry; model comparisons are domain-specific, not a mandate to use RPV.",
        "10.3390/rs15205000",
    ),
]
for name, text, doi in short:
    y = para(
        "<b>"
        + name
        + "</b> | "
        + text
        + ' <link href="https://doi.org/'
        + doi
        + '" color="#225e8d">DOI '
        + doi
        + "</link>",
        y,
        compact=True,
    )
y = para(
    "<b>For our PFT research:</b> Keep calibrated biological spectra and indices, polygon/spatial/photo identities and independent target/view/site validation. Do not optimize away true vegetation gradients to reduce variance. Upstream seam causes remain hypotheses; Goldhill's extreme red streak is a confirmed downstream SpectralBridge BRDF failure. No duplicate upstream correction has been established.",
    y,
    compact=True,
)
para(
    "Full evidence, field/operation matrices, bounded inventories, code excerpts and reproduction scripts: provenance/photogrammetry-metadata/2026-11-02. The unified Markdown report is docs/dev/photogrammetry-metadata-investigation.md. Source hashes remain unchanged. No real-camera reconstruction or physical calibration is claimed where inputs are missing.",
    y,
    compact=True,
)
c.save()
print(path)
