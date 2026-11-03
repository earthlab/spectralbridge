"""Eight-page visual summary; full machine-readable evidence is alongside it."""

from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "experiment_summary.json").read_text())
W, H = landscape(A3)
M = 43
B = W - 2 * M
out = HERE / "can_assumed_viewing_angles_rescue_drone_brdf.pdf"
c = canvas.Canvas(str(out), pagesize=(W, H))
c.setTitle("Can Assumed Viewing Angles Rescue Drone BRDF Correction?")
c.setAuthor("SpectralBridge | isolated scientific experiment | 2026-11-03")
body = ParagraphStyle(
    "body",
    fontName="Helvetica",
    fontSize=13.5,
    leading=18,
    textColor=HexColor("#233d4c"),
)
small = ParagraphStyle("small", parent=body, fontSize=11, leading=14)
page = 0


def start(title, sub):
    global page
    page += 1
    c.setFillColor(HexColor("#153e50"))
    c.rect(0, H - 83, W, 83, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 21)
    c.drawString(M, H - 35, title)
    c.setFont("Helvetica", 12)
    c.drawString(M, H - 61, sub)
    c.setFillColor(HexColor("#597180"))
    c.setFont("Helvetica", 9.5)
    c.drawString(
        M,
        21,
        "SpectralBridge | 2026-11-03 | Actual source DN / imposed angles / missing evidence distinguished | Production unchanged",
    )
    c.drawRightString(W - M, 21, f"{page} / 8")
    return H - 106


def para(text, y, compact=False):
    p = Paragraph(text, small if compact else body)
    _, h = p.wrap(B, H)
    p.drawOn(c, M, y - h)
    return y - h - 11


def picture(name, y, maxheight):
    r = ImageReader(str(HERE / name))
    iw, ih = r.getSize()
    scale = min(B / iw, maxheight / ih)
    w, h = iw * scale, ih * scale
    c.drawImage(r, (W - w) / 2, y - h, width=w, height=h, mask="auto")
    return y - h - 10


def table(headers, rows, y, widths):
    height = 27
    c.setFillColor(HexColor("#e5edf1"))
    c.rect(M, y - height, B, height, fill=1, stroke=0)
    for i, row in enumerate([headers] + rows):
        c.setFillColor(HexColor("#233d4c"))
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 11.5)
        x = M + 6
        for value, width in zip(row, widths):
            c.drawString(x, y - 18, str(value))
            x += width
        y -= height
        c.setStrokeColor(HexColor("#dce5e8"))
        c.line(M, y, W - M, y)
    return y - 12


y = start(
    "Can Assumed Viewing Angles Rescue Drone BRDF Correction?",
    "Actual Gordon, Goldhill and Ruby 2023 imagery | constant angles, synthetic fields and independent-coefficient audit",
)
y = para(
    "<b>No tested constant angle rescues the fit:</b> 0 of 93 requested constant-relative geometries pass current angular conditioning. This includes 10 and 15 degrees. One constant direction changes the kernels, not their independent information.",
    y,
)
y = para(
    "<b>Invented maps can appear numerically usable:</b> 12 of 15 spatial scenarios pass angular-only rank/conditioning. They remain physically unsupported because those viewing directions were not observed.",
    y,
)
y = para(
    "<b>No eligible independent coefficients:</b> 13 files inspected; six VALID records are synthetic fixtures. None establishes validated NEON-to-drone spectral, radiometric and canopy applicability. No coefficients were invented or refitted to assumed geometry.",
    y,
)
y = picture("figure1_geometry.png", y, 280)
y = para(
    "<b>What was quantified:</b> complete source-valid kernel/design responses and a raw-DN baseline of 301 researcher polygons / 198,562 memberships. <b>What was not:</b> correction factors, corrected images or PFT improvement. Those are NOT_EVALUATED because the coefficient prerequisite is absent.",
    y,
)
y = para(
    "<b>Recommendation:</b> preserve the spatial repair and source numerical data; explicitly omit unsupported BRDF. Physical calibration, timestamps and scientific library approval remain separate. No topographic correction enters this experiment.",
    y,
)
c.showPage()

y = start(
    "Constant assumed angles change the basis, not the information",
    "31 unique constant cases per flight | 0, 5, 10, 15, 20, 25, 30 deg; five non-nadir relative azimuths",
)
y = picture("figure2_kernel_response.png", y, 510)
y = para(
    "Actual package RossThick/LiDenseR, b/r=10 and h/b=2, with each working H5's scene solar zenith. Solar grids retain their documented acquisition-date uncertainty. Nadir azimuth is undefined and is counted once, not five times.",
    y,
)
y = para(
    "For constant relative azimuth, absolute sensor azimuth = (absolute solar azimuth + relative azimuth) modulo 360. A relative angle is never inserted as an absolute compass direction. In exact arithmetic the design repeats one row [1, Kvol, Kgeo]: only one coefficient combination is identifiable.",
    y,
)
y = para(
    "Kernel change is not reflectance change. Without a valid applicable coefficient vector, these plots cannot predict a correction gain or support an optimal assumed angle.",
    y,
)
c.showPage()

y = start(
    "Rank alone can be misleading",
    "Full-scene weighted SVD for constants; streaming QR/SVD for spatial scenarios; no sampled-rank result",
)
y = picture("figure3_identifiability.png", y, 385)
y = table(
    ["Design family", "Numerical result", "Physical / correction status"],
    [
        ["93 constant-relative cases", "0 pass angular gates", "Unsupported"],
        ["24 constant-absolute checks", "0 pass angular gates", "Unsupported"],
        [
            "12 smooth/footprint/edge fields",
            "Rank 3; condition 65-132",
            "Numerically feasible, physically unvalidated",
        ],
        [
            "3 alternating strip fields",
            "Rank 3; condition 0.82-6.75 million",
            "Unsupported conditioning",
        ],
    ],
    y,
    [240, 310, B - 550],
)
y = para(
    "Float32 absolute-angle subtraction can give nominal rank 3 in 27 constant cases. Within-case kernel ranges are only 1.19e-7 (RossThick) and 3.10e-6 (LiDenseR). Even the best constant condition number is 31.7 million, versus the current limit 2896. Numerical noise does not recover real angular diversity.",
    y,
)
y = para(
    "All 30 physical band fits remain unsupported. Repeating all 93 constant and 15 spatial cases on positive-source-alpha support gives the same 0/93 and 12/15 outcomes. The experiment performs no reflectance fit to imposed geometry and never relaxes rank, conditioning or calibration checks.",
    y,
)
c.showPage()

y = start(
    "Synthetic spatial variation can manufacture a full-rank design",
    "Goldhill shown; each of five scenarios evaluated over all valid pixels in all three flights",
)
y = picture("figure4_synthetic_maps.png", y, 600)
y = para(
    "All fields are imposed, not recovered Metashape rays. Nominal report parameters: 114-123 m altitude, 1280x960 pixels, 3.75 micrometer pitch, 5.5 mm focal length; pinhole half-angles about 23.57/18.12 degrees, corner 28.61 degrees. Track origin, spacing, attitude and source blending remain unknown.",
    y,
    True,
)
y = para(
    "Shared map limits and source masks; no correction or H5 write. All fields have nominal rank 3, but only 12/15 meet conditioning. Algebraic support is not physical identifiability.",
    y,
    True,
)
c.showPage()

y = start(
    "Independent coefficient transfer: prerequisite not found",
    "Computational VALID does not establish empirical validation or transferability",
)
y = picture("figure5_coefficient_boundary.png", y, 330)
y = para(
    "The bounded repository/cache inventory records 13 paths, hashes, calibration/kernel/reference fields and rejection reasons: six synthetic fixtures, four unsupported/invalid records and three historical unvalidated models. Separate historical real-NEON QA also shows 426 collapsed zero vol/geo terms, not a valid transferable model. No suitable independent empirical NEON set was found; this is not a global claim that such coefficients do not exist.",
    y,
)
y = para(
    "<b>Required before transfer:</b> independent validation, compatible sensor wavelengths/responses, current RossThick/LiDenseR conventions and reference, physical units, vegetation/canopy/illumination domain and stable applicability. The production model also binds source identity/radiometry; no external bypass was added.",
    y,
)
y = para(
    "<b>Not computed:</b> gain/loss quantiles, invalid predictions, corrected nonfinite counts/coverage, discontinuities, indices and PFT changes. These remain null/NOT_EVALUATED, not identity factors or zero failures. Even a future valid fixed-model calculation here would be DN sensitivity until physical calibration is verified.",
    y,
)
y = para(
    "No historical Goldhill coefficients are ported to the repaired kernels. No neutral or arbitrary anisotropic model is substituted to make comparison images.",
    y,
)
c.showPage()

y = start(
    "Actual imagery: uncorrected source DN only",
    "No SCS+C branch; no assumed-angle corrected images; historical Goldhill failure remains a separate proven result",
)
y = picture("figure6_goldhill.png", y, 280)
y = picture("figure7_raw_rgb.png", y, 255)
y = para(
    "Goldhill: actual 650 nm DN and native row 921, columns 840-1120. The prior historical boundary at column 980 is marked; no 10/15-degree correction curve exists. Red map graphical range 0-20,000 DN; all values remain in analytical tables. RGB uses one pooled channel scale across the three flights, not separate stretches.",
    y,
    True,
)
y = para(
    "Numerical inverse normalization preserves source-DN representation; it is not physical reflectance or original native-pixel recovery. Source grid/masks and researcher labels are retained.",
    y,
    True,
)
c.showPage()

y = start(
    "Polygon and PFT evidence: a quantified raw baseline",
    "Preserved researcher categories, including non-vegetated/dead; no random pixel split or corrected-branch inference",
)
y = picture("figure8_pft_baseline.png", y, 385)
y = table(
    ["Flight", "Polygons", "Raw polygon-pixel memberships"],
    [["Gordon", 58, "31,598"], ["Goldhill", 157, "144,458"], ["Ruby", 86, "22,506"]],
    y,
    [240, 240, B - 480],
)
y = para(
    "301 polygons / 198,562 memberships use finite raw values intersected with positive retained TIFF alpha. The finite-H5-only audit has 302 / 200,320, including 1,758 transparent-background memberships. One all-transparent Goldhill shrub polygon is excluded from spectra but preserved in the audit. No source alpha or metadata is changed; P161 used a different common topographic population.",
    y,
)
y = para(
    "Ten-band polygon medians, within-polygon angles, bandwise dispersion, numerical indices and class overlap are recorded. Existing spatial-blocked separability analysis has 17 supported and five insufficient pairs (1,999 seeded permutations, Holm across 17 tests); seven adjusted raw associations do not imply classification accuracy or calibration.",
    y,
    True,
)
y = para(
    "Corrected within-PFT consistency, between-PFT separability and overlap changes are NOT_EVALUATED. Reducing variance with invented geometry could suppress biology; no assumed angle is selected on those grounds.",
    y,
    True,
)
c.showPage()

y = start(
    "Recommendation: preserve the baseline and omit unsupported BRDF",
    "A negative constant-angle result; no claim that every future external coefficient model must fail",
)
y = picture("figure9_sensitivity.png", y, 285)
y = para(
    "Changing 10 to 15 degrees at matched relative azimuth changes RossThick by up to 0.03095 and LiDenseR by 1.4257. That shows basis sensitivity, not a measured gain. Robustness of corrected spectra cannot be evaluated without eligible coefficients.",
    y,
)
y = table(
    ["Approach", "Classification", "Decision"],
    [
        ["Constant-angle fit", "Unsupported", "0/93 pass; no production use"],
        [
            "Synthetic varying geometry",
            "Numerically feasible but unvalidated",
            "12/15 angular-only passes; no physical fit",
        ],
        [
            "Independent coefficient transfer",
            "Not evaluated",
            "Validated applicable model unavailable",
        ],
        [
            "Preserve source / explicitly omit BRDF",
            "Supported interim preservation",
            "Not physical/library approval",
        ],
    ],
    y,
    [295, 300, B - 595],
)
y = para(
    "<b>Seven answers:</b> (1) No tested constant identifies the fit. (2) Yes, invented maps can produce rank without observations. (3) Stable independent-model transfer is not evaluated. (4) Correction robustness is unknown. (5) PFT improvement is not established. (6) No assumed-angle method is supported for production libraries. (7) Explicitly omitting BRDF remains the defensible interim strategy.",
    y,
    True,
)
y = para(
    "<b>Next evidence:</b> a real empirically validated coefficient model with wavelength/response, kernel/reference, units and canopy-domain records, or actual calibrated source-photo observations plus camera geometry. Recover physical calibration and acquisition timestamps in either case. Full report, tables, source hashes, scenario definitions and reproducible scripts are alongside this PDF.",
    y,
    True,
)
c.save()
assert page == 8
print(out)
