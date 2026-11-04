"""Assemble a coherent scientific report from executed stage/evidence records."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
s = json.loads((HERE / "analysis_summary.json").read_text())
manifest = json.loads((HERE / "input_manifest.json").read_text())
figs = json.loads((HERE / "figure_manifest.json").read_text())
stage = json.loads((HERE / "production_stage_results.json").read_text())
classify = pd.DataFrame(
    json.loads((HERE / "classification_summary.json").read_text())
).set_index("branch")
boundary = pd.read_csv(HERE / "red_boundary_discontinuities.csv").set_index("branch")
tests = ET.parse("/private/tmp/p169_tests.xml")
n_tests = len(tests.findall(".//testcase"))
pages = []


def page(
    section,
    title,
    intro,
    *,
    figure=None,
    findings=None,
    rows=None,
    columns=None,
    notes=None,
):
    pages.append(
        dict(
            section=section,
            title=title,
            intro=intro,
            figure=figs[figure - 1] if figure else None,
            findings=findings or [],
            rows=rows,
            columns=columns,
            notes=notes or [],
        )
    )


page(
    "Executive decision",
    "Goldhill Reprocessing: End-to-End Validation of Corrected Drone Imagery",
    "The new source is a more faithful numerical preprocessing input. It does not yet support an approved physical correction or official spectral library.",
    rows=[
        [
            "Source preprocessing",
            "READY as documented uncalibrated 10 cm / fixed-10K numerical input",
        ],
        [
            "Raw numerical export and membership",
            "EXECUTED: exact finite values, masks, CRS and orientation preserved",
        ],
        [
            "Physical topographic / BRDF / combined",
            "UNSUPPORTED: calibration missing; sensor views not assigned; time-zone/per-pixel timing still unverified",
        ],
        [
            "Landsat physical translation / official library",
            "UNSUPPORTED: physical-input safeguard correctly blocks execution",
        ],
        [
            "Native MicaSense subsets",
            "EXECUTED as wavelength-selected numerical diagnostics only",
        ],
        [
            "Research-category recognition",
            "157 polygons, four recorded classes, 66.8% raw balanced accuracy before and after",
        ],
        [
            "Abundance / physical accuracy",
            "NOT VALIDATED: no independent abundance or physical-reflectance reference",
        ],
    ],
    columns=["Decision area", "Outcome"],
    findings=[
        "The report separates actual production calls, unsupported stages and unchanged historical replays. No scientific safeguard was disabled.",
        "The red stripe persists in the historical BRDF replay. A visually improved source does not repair an unsupported correction model.",
    ],
    notes=[
        "November 3, 2026 | P169 | SpectralBridge science-team experiment",
        "No production imagery, official library or CyVerse object was overwritten or uploaded.",
    ],
)
page(
    "1. What changed?",
    "A better numerical source, with the physical question still open",
    "The original approximately 8.44 cm UInt16 orthomosaic was converted directly to 10 cm using S = DN x 10000 / 65535. There is no band-minimum subtraction, clipping or integer quantization.",
    figure=1,
    findings=[
        "The declared original alpha mask excludes transparent samples before bilinear interpolation. The new file has ten spectral bands and an internal GDAL validity mask.",
        "Nominal encoding 0-10,000 does not force each observed band to fill that interval. Physical reflectance calibration remains UNVERIFIED.",
    ],
)
page(
    "2. Did the source correction work?",
    "Background is no longer treated as observed signal",
    "All 537,552 occurrences of 65,535 in each original band lie in transparent background. None is a measured saturated pixel. The historical interpolation allowed this background to mix into boundary pixels.",
    figure=2,
    findings=[
        "New source support: 6,683,944 pixels. Historical finite-H5 support: 7,068,376 pixels. These counts are not equivalent observation masks.",
        "Within the new footprint, 3,244 old red-band values exceed the original observed maximum under the same fixed encoding. The new source excludes transparent samples during interpolation; no value clipping is used.",
    ],
)
page(
    "3. What happens during correction?",
    "Aligned inputs do not establish correct solar provenance",
    "Actual TIFF-to-H5 and H5-to-ENVI package functions preserved all finite values and missingness, EPSG:26913, the affine grid, band order and source footprint. Sensor viewing datasets were deliberately not created.",
    figure=3,
    findings=[
        "Wavelengths: 444, 475, 531, 560, 650, 668, 705, 717, 740, 862 nm. FWHM: 28, 32, 14, 27, 16, 14, 10, 12, 18, 57 nm, inherited from the established source H5.",
        "Inherited solar metadata says 2023-08-15T19:53:07; original package notes identify 2023-08-14 at 13:41 local. The original photo metadata supports August 15: all 5,650 linked cameras match unique August 15 tags; the inherited solar time is 5.5 seconds from their midpoint. Explicit time-zone/clock and per-pixel time assignments remain unverified.",
    ],
)
page(
    "3. What happens during correction?",
    "Camera orientations arrived; the per-pixel observation model did not",
    "The supplied CSV contains camera locations and band-specific rotations, which improves the available provenance. It does not identify the camera observations or blend weights contributing to each mosaic pixel.",
    figure=5,
    findings=[
        "The CSV states CRS 5070, while its coordinate values fall with the TIFF in UTM 13N / EPSG:26913. The CRS and angular/vertical conventions need confirmation.",
        "Actual production BRDF receives no per-pixel sensor angles. The direct fit reports missing sensor_zn; the correction driver reports UNSUPPORTED. The known legacy zero-view control has rank 1 of 3, but is not treated as measured viewing geometry.",
    ],
)
page(
    "3. What happens during correction?",
    "Photo metadata supports August 15 and the inherited scene midpoint",
    "The nominal August 14 package name/note conflicts with the original photo tags. All 6,095 raw metadata rows are dated August 15; all 5,650 supplied camera records join uniquely, without missing or ambiguous IDs.",
    figure=13,
    findings=[
        "Matched timestamps span 19:42:38-20:03:47. Their midpoint is 19:53:12.5; the inherited solar computation used 19:53:07. This is positive source evidence for that scene timestamp, not a reason to discard it based only on the package name.",
        "The CSV does not state the time zone or independently verify camera clock accuracy. Per-photo times are now recoverable by ID, but each orthomosaic pixel still needs its contributing images/weights before those times and views can be assigned scientifically.",
    ],
)
page(
    "3. What happens during correction?",
    "Production functions executed; refused stages stay refused",
    "Each result below comes from an actual package call. A raw export or native-band subset is an uncalibrated numerical product, not a physical correction.",
    rows=[
        [
            "convert_drone_tiff_to_h5 / export_h5_to_envi",
            "EXECUTED",
            "Exact grid, finite values, NoData and mask checks pass",
        ],
        [
            "apply_drone_corrections: no correction",
            "EXECUTED",
            "Raw numerical baseline; calibration remains UNSUPPORTED",
        ],
        [
            "apply_drone_corrections: topographic",
            "UNSUPPORTED",
            "Authoritative physical scale, offset, units and provenance absent",
        ],
        [
            "fit_scs_c_coefficients: direct current API",
            "UNSUPPORTED",
            "Same physical-radiometry safeguard",
        ],
        [
            "apply_drone_corrections: BRDF / combined",
            "UNSUPPORTED",
            "Physical calibration missing; no valid combined result produced",
        ],
        [
            "fit_and_save_brdf_model: direct current API",
            "UNSUPPORTED",
            "Per-pixel sensor_zn unavailable",
        ],
        [
            "apply_drone_translation: Landsat 5/7/8/9",
            "UNSUPPORTED",
            "Physical-input requirement; no coefficients or units fabricated",
        ],
        [
            "ensure_matched_source_product: two MicaSense sets",
            "EXECUTED",
            "Native wavelength selection only, unverified-unit metadata retained",
        ],
        [
            "build_polygon_pixel_index",
            "EXECUTED",
            "144,749 memberships, 158 intersecting identities",
        ],
        [
            "extract_polygon_parquet_from_envi",
            "UNSUPPORTED",
            "Approved physical-library requirement",
        ],
    ],
    columns=["Actual function / stage", "Final status", "Meaning"],
    findings=[
        "The caller initially omitted output directories for the raw-copy and matched-subset helpers. Those setup errors were corrected and the actual calls rerun successfully; initial outcomes and both logs are retained.",
        "No alternate correction algorithm, neutral current coefficient set or fabricated calibration was substituted. The normal drone route uses native MicaSense band selection and versioned bulk-affine Landsat plans; no hyperspectral SRF convolution was fabricated from ten sparse bands.",
    ],
)
page(
    "3. What happens during correction?",
    "Historical SCS+C is a stress test, not approval",
    "The unchanged historical fit/application functions were replayed with the new encoded source and inherited terrain/solar arrays. Their model guards are retained and all output magnitudes remain uncapped.",
    figure=4,
    findings=[
        "Red factor maximum: 309.9 at row 1178, column 1533. Slope is 41.89 degrees, illumination cosine 0.34826, fitted C=-0.34725, denominator 0.001005. This is near cancellation of model terms, not proof of a valid 310-fold physical illumination adjustment.",
        "On common support, 11,305 red pixels receive factors above 10. Current production SCS+C was blocked. Missing calibration, unverified time-zone/per-pixel timing and this numerical instability prevent a defensible production recommendation.",
    ],
)
page(
    "4. What happened to the red stripe?",
    "Source repair does not repair the historical BRDF denominator",
    "The unchanged saved model and historical code were applied only inside the explicitly marked replay namespace. The source change leaves the old geometry/model mechanism in place.",
    figure=6,
    findings=[
        "The new raw image has no comparable algorithmic red discontinuity. The historical replay still turns ordinary red-band values into billions of encoded units.",
        "Saved neutral coefficients in historically under-supported bands remain historical evidence, not successful new fits. Current package safeguards do not silently replace the missing fit with neutral coefficients.",
    ],
)
page(
    "4. What happened to the red stripe?",
    "Measure the discontinuity on a fixed boundary",
    "A previously defined row/ROI and 2,934 boundary edges fixed from the historical red factor were reused. All branches share the same valid comparison support.",
    figure=7,
    findings=[
        f"At row 921, columns 980-981: new raw jump {boundary.loc['new_raw', 'fixed_jump']:.3f}; new historical-BRDF replay jump {boundary.loc['new_historical_brdf', 'fixed_jump']:.3g} encoded units.",
        f"Median absolute edge jump: new raw {boundary.loc['new_raw', 'median_abs_jump']:.3f}; historical replay {boundary.loc['new_historical_brdf', 'median_abs_jump']:.3g}. The source cleanup does not remove a pathological model/reference prediction.",
    ],
)
page(
    "5. Are the spectra better?",
    "The main raw spectral-angle change is an encoding effect",
    "Old native encoding, old data recovered to the fixed encoding, and the new source were kept separate. Comparisons use the same pixel memberships, so coverage changes cannot create an apparent quality improvement.",
    figure=8,
    findings=[
        "On 144,406 matched polygon pixels, median angle from old raw to new raw is 0.4743 degrees. After recovering the old encoding, it is only 0.000773 degrees. This residual does not establish physical accuracy.",
        "Median within-polygon band CV is 0.232002 for new raw versus 0.231988 for the old fixed-encoding control: essentially unchanged, with a tiny increase. Median mean-band variance is 15,618 versus 15,617 encoded-unit squared. Do not call that improved homogeneity.",
    ],
)
page(
    "6. Does this improve the science?",
    "Keep the researcher labels and the sampling unit",
    "The canonical package index supplies membership. Experimental numeric spectra retain GlobalID, cover_category, species, flight identity, source hash, branch and pixel count. Approved physical extraction remains blocked.",
    figure=9,
    findings=[
        "Matched sample: 157 non-overlapping polygon representatives and 144,406 memberships. Recorded classes are Evergreen 98, Woody shrub 29, Herbaceous 25 and Deciduous 5. Non-vegetated & dead is absent and is not invented or reassigned.",
        "All-band scene comparison uses 6,678,404 common pixels. Raw-only comparison uses 6,683,944. Native mask changes affect 277 canonical polygon memberships before matching; common sampling removes this coverage confound.",
    ],
)
page(
    "6. Does this improve the science?",
    "Separation and identification answer different questions",
    "The package spectral_separability function ran 499 synchronized permutations with explicit equal weights on the ten discrete bands. It provides conditional pairwise tests, not physical purity or abundance. Polygon exchangeability is assumed; fine spatial confounding is untested, Holm adjustment is within branch, and across-branch comparisons are exploratory.",
    figure=10,
    findings=[
        "Evergreen versus Herbaceous centroid angle is 1.07 degrees; Evergreen versus Woody shrub has mean band-IQR overlap 0.432. These are descriptions of the retained single-flight researcher categories.",
        "Woody shrub remains difficult to identify. The new-raw held-polygon recalls are Deciduous 4/5, Evergreen 73/98, Herbaceous 17/25 and Woody shrub 13/29. Five deciduous identities are too few for a precise generalization claim.",
    ],
)
page(
    "6. Does this improve the science?",
    "No detected identification gain from the new raw source",
    "The actual evaluate_identifiability API used identical three-fold polygon-disjoint splits, training-only scaling, fixed C=1, and no pixel-level replication as training samples. All branches use the same 157 identities.",
    figure=11,
    findings=[
        "Old raw, old recovered encoding and new raw all score 66.829% balanced accuracy, with identical out-of-fold predictions. A conditional bootstrap of those fixed predictions has zero paired difference, but omits training/model uncertainty and does not establish population equivalence.",
        "Historical topographic replay scores 71.7%, while historical BRDF replay scores 60.0%. These remain unsupported corrections. A higher classification score cannot establish correct physical reflectance or justify near-singular correction factors.",
    ],
)
page(
    "6. Does this improve the science?",
    "Spectral structure is largely retained; abundance stays unvalidated",
    "PCA summarizes the paired spectral distributions after bringing old data to the same numerical encoding. It is a descriptive figure, separate from the classifier training and test splits.",
    figure=12,
    findings=[
        "The nearly coincident paired structure is consistent with little change in interior polygon spectra after the encoding control. It does not establish transfer to another flight, site or year.",
        "Abundance estimation is NOT_EVALUATED: no independently verified physical endmember library, fractional-cover ground truth or abundance-validation design was supplied. Category recognition is not an abundance-accuracy test.",
    ],
)
page(
    "7. What should we do next?",
    "Direct answers for production decisions",
    "The source repair succeeds as numerical preprocessing. It does not make the complete physical correction pipeline ready.",
    rows=[
        [
            "1. More reliable numerical/spatial source?",
            "YES: common fixed encoding, original alpha honored, exact ingestion grid/value/mask checks. Physical accuracy remains unverified.",
        ],
        [
            "2. Background contamination eliminated?",
            "YES for transparent-source contribution in the new derivative: alpha=0 is excluded before interpolation. Edge/field validity still needs normal source QA.",
        ],
        [
            "3. Topographic correction stable and defensible?",
            "NOT ESTABLISHED. Current API is blocked; historical stress factors reach 310x in red near a vanishing denominator, before physical and illumination validation.",
        ],
        [
            "4. BRDF supported by available geometry?",
            "NO. Camera poses are not mapped to mosaic pixel contributors; actual sensor angles are unavailable and calibration is missing.",
        ],
        [
            "5. Does the historical red stripe persist?",
            "YES in the historical replay on the new source. It is introduced by old BRDF application; no approved new BRDF result exists.",
        ],
        [
            "6. Are PFT spectra more consistent?",
            "NO material improvement detected on matched interior polygon support after controlling the old encoding; variability changes are tiny or mixed.",
        ],
        [
            "7. Improved separability/identifiability?",
            "NO identification gain in this experiment: identical raw predictions / 66.8% balanced accuracy. Some classes remain overlapping or poorly identified.",
        ],
        [
            "8. Safe for future production?",
            "READY for documented numerical preprocessing/raw QA; NOT READY for approved physical correction, translated physical products or an official spectral library.",
        ],
        [
            "9. Before official library regeneration?",
            "Recover physical calibration, confirm acquisition time and camera/CRS conventions, recover per-pixel view/contributor information or a justified independent model, validate correction stability, then regenerate in fresh versioned outputs.",
        ],
    ],
    columns=["Question", "Answer"],
    notes=[
        "Do not upload or replace the official library with any diagnostic replay or numeric-only experimental Parquet.",
        "A separate empirical reference/independent domain test is still needed before claiming physical or abundance accuracy.",
    ],
)
page(
    "Reproducibility and QA",
    "What ran, what is retained, and what passed",
    "All artifacts belong to a new dated experiment. Reproduction preserves source bytes and logs every scientific refusal rather than converting a failed stage into apparent success.",
    rows=[
        ["Evidence folder", "provenance/goldhill-end-to-end/2026-11-03/"],
        [
            "Large experimental rasters and numeric tables",
            "/private/tmp/goldhill-end-to-end-20261103/",
        ],
        [
            "Source identity",
            "input_manifest.json: new/original/historical sources, poses, polygons, saved model and code hashes",
        ],
        ["Software revision", manifest["repository_revision"]],
        [
            "Production API outcomes",
            "production_stage_results.json; per-stage audit JSON; ingestion.json; both execution logs",
        ],
        [
            "Scientific measurements",
            "Stage masks/counts; native/common scene distributions; boundary jumps; factors; polygon/PFT tables; fixed grouped-fold memberships",
        ],
        [
            "Diagnostic isolation",
            "Historical code/model hashes unchanged; no current safeguard bypass and no invented physical coefficients or viewing angles",
        ],
        [
            "Tests",
            f"{n_tests} targeted unit/integration tests pass, including new uncalibrated-mask/zero/grid/guard contracts",
        ],
        [
            "Figure/PDF QA",
            "13 actual-data figure pairs; PDF pages rendered and visually reviewed; source/production-code preservation verified",
        ],
        [
            "Production writes",
            "None: no CyVerse upload, source edit, official corrected raster replacement or library replacement",
        ],
    ],
    columns=["Reproducibility item", "Record"],
    findings=[
        "Use run_pipeline.py, audit_photo_times.py, analyze.py and figures.py, then write_report.py, make_pdf.py and verify.py. Paths and source identities are explicit; restore the documented local inputs before running elsewhere.",
        "This report deliberately contains no approved physical corrected Goldhill branch. That is the scientific eligibility result of the end-to-end exercise.",
    ],
)
(HERE / "report_pages.json").write_text(json.dumps(pages, indent=2) + "\n")
lines = [
    "# Goldhill Reprocessing: End-to-End Validation of Corrected Drone Imagery",
    "\nNovember 3, 2026. P169 experimental validation; no production overwrite/upload.\n",
]
for n, p in enumerate(pages, 1):
    lines += [f"## {n}. {p['title']}", p["intro"]]
    if p["rows"]:
        lines += [
            "| " + " | ".join(p["columns"]) + " |",
            "| " + " | ".join(["---"] * len(p["columns"])) + " |",
        ]
        lines += ["| " + " | ".join(row) + " |" for row in p["rows"]]
    if p["figure"]:
        lines += [
            f"![{p['figure']['caption']}]({p['figure']['png']})",
            p["figure"]["caption"],
        ]
    lines += ["\n- " + v for v in p["findings"]]
    lines += p["notes"]
    lines += [""]
(HERE / "report.md").write_text("\n\n".join(lines) + "\n")
(ROOT / "docs/reports/GOLDHILL_END_TO_END_VALIDATION.md").write_text(
    """# Goldhill end-to-end validation\n\nNovember 3, 2026. The fixed-10K source improves numerical preprocessing and excludes transparent-background contributions, but physical calibration, explicit clock/time-zone conventions and pixel-level viewing geometry remain unresolved. Original photo tags now support the inherited August 15 scene timestamp. Current production corrections, physical translation and the approved library stage are explicitly unsupported.\n\nThe matched 157-polygon raw classification remains 66.8% balanced accuracy, with identical predictions before and after. Historical BRDF replay retains the red stripe; historical SCS+C stress factors remain unstable. No production imagery/library was overwritten or uploaded.\n\n- [Full scientific report with all figures](../../provenance/goldhill-end-to-end/2026-11-03/report.md)\n- [Visual PDF](../../provenance/goldhill-end-to-end/2026-11-03/goldhill_end_to_end_validation.pdf)\n- [Input manifest](../../provenance/goldhill-end-to-end/2026-11-03/input_manifest.json)\n- [Actual production stage outcomes](../../provenance/goldhill-end-to-end/2026-11-03/production_stage_results.json)\n- [Machine-readable scientific summary](../../provenance/goldhill-end-to-end/2026-11-03/scientific_summary.json)\n- [Verification](../../provenance/goldhill-end-to-end/2026-11-03/verification.json)\n"""
)
print(f"{len(pages)} report pages assembled")
