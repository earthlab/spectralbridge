"""Generate quantitative science narrative from completed compact experiment results."""

import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TITLE = "Goldhill Topographic Correction: A Conditional Reflectance Experiment"


def read(n):
    return json.loads((HERE / n).read_text())


def main():
    cfg = read("branches.json")
    scores = {x["branch"]: x for x in read("classification_summary.json")}
    gains = {x["branch"]: x for x in read("paired_gain.json")}
    summary = read("analysis_summary.json")
    terrain = read("terrain_audit.json")
    C = read("coefficients.json")
    figs = read("figure_manifest.json")
    poly = pd.read_csv(HERE / "polygon_summaries.csv")
    med = (
        poly[poly.support == "common"]
        .groupby("branch")[["median_band_cv", "mean_variance", "within_angle_median"]]
        .median()
    )
    dependence = pd.read_csv(HERE / "class_spatial_control.csv")
    pages = []

    def page(
        title,
        intro,
        figure=None,
        findings=(),
        rows=(),
        columns=("Finding", "Evidence"),
        notes=(),
        section="Conditional scientific experiment",
    ):
        pages.append(
            dict(
                title=title,
                intro=intro,
                figure=figure,
                findings=list(findings),
                rows=list(rows),
                columns=list(columns),
                notes=list(notes),
                section=section,
            )
        )

    def fig(i):
        f = figs[i - 1]
        return dict(png=f["png"], caption=f["caption"])

    stable_gain = gains["stabilized"]
    rawacc = scores["raw"]["balanced_accuracy"]
    stableacc = scores["stabilized"]["balanced_accuracy"]
    page(
        TITLE,
        "November 3, 2026. A controlled, isolated test of SCS+C under the supported-but-unverified DN/32768 hypothesis. Raw candidate reflectance remains the primary scientific representation.",
        rows=[
            ("Calibration", "HYPOTHETICAL_UNVERIFIED; not VALID or VERIFIED"),
            (
                "Numerical finding",
                "Common positive scaling leaves all ten fitted C values and factors unchanged.",
            ),
            (
                "Instability",
                "Historical and current red factors reach309.9168; eligibility/Huber alone do not eliminate poles.",
            ),
            (
                "Stabilization",
                "Uncertainty/domain exclusions reduce maximum red factor to6.9901 without clipping;98.96% of raw footprint retained.",
            ),
            (
                "Identification",
                f"Common-support balanced accuracy: raw{rawacc:.1%}, stabilized{stableacc:.1%}. No established improvement.",
            ),
            (
                "Decision",
                "Use correction branches for diagnostic experiments only; no production deployment or official spectral library.",
            ),
        ],
        findings=[
            "No BRDF correction, source overwrite, production registry change, VALID calibration record or datastore write."
        ],
    )
    page(
        "The hypothesis changes units, not the evidence",
        "S=DN x10000/65535 is the fixed numerical derivative. Under the candidate convention, R=S x0.0001999969482421875, offset0. Values are candidate fractional reflectance.",
        fig(1),
        findings=[
            "The derivative is2238x3165, ten optical bands,10 cm,EPSG26913. Wavelengths444/475/531/560/650/668/705/717/740/862nm; source internal alpha-derived mask preserved exactly.",
            "The production Radiometry gate still rejects this hypothesis. The isolated subclass calls the existing Radiometry._affine kernel; functions retain their actual scientific bytecode in a separate namespace. Conversion occurs once into calculations and inverse once into storage.",
            "Exhaustive prior UInt16 arithmetic and this all-ten-band source comparison support numerical consistency, not absolute calibration. Original SHA-256:00df553e63285dde6dad4b02f2ad399bf813b8591dc93e912a007c3cddf9e954.",
        ],
    )
    page(
        "Geometry is aligned; its source history is not fully certified",
        "The recovered original photo tags support August15,2023;5650 camera IDs join uniquely. Matched times span19:42:38-20:03:47, midpoint19:53:12.5. The inherited time19:53:07 differs by5.5 seconds.",
        fig(2),
        findings=[
            f"Of{cfg['raw_pixels']:,} raw pixels,{cfg['geometry_valid_pixels']:,} have finite usable inherited geometry;{cfg['missing_geometry_pixels']:,} are unavailable and{cfg['self_shadow_pixels']:,} have local cos(i)<=0.",
            "MicaSense documentation specifies camera tags as UTC, supporting the UTC interpretation. The exported three-column CSV does not independently prove clock accuracy/time zone. No pixel contributor-time map is available.",
            "Slope/aspect are converted from degrees once. No evidence here establishes a radians/degrees bug in SCS+C. Terrain surface, execution provenance, true/grid North, interpolation and cast/canopy shadows remain separate uncertainties.",
        ],
    )
    t = read("solar_sensitivity.json")
    page(
        "Time sensitivity is a scenario test, not a choice by appearance",
        "The existing package solar function was used at scene center for six explicit timing cases; the main branches retain the inherited spatial solar grids. UTC start/end bracket available camera times.",
        fig(3),
        findings=[
            f"UTC flight span changes zenith from{t[1]['zenith_deg']:.2f}to{t[2]['zenith_deg']:.2f}degrees; refitted maximum red factors remain about{t[1]['red_factor']['quantiles'][-1]:.0f}-{t[2]['red_factor']['quantiles'][-1]:.0f}.",
            f"Treating19:53as local MDT implies01:53UTC next day and zenith{t[4]['zenith_deg']:.2f}degrees. Its factor1 fallback reflects unsupported numerator/denominator signs, not a physically demonstrated correction.",
            "The midday UTC interpretation is favored by timestamp evidence and manufacturer convention, not by prettier corrected maps. Approximate solar calculations do not establish authoritative per-photo illumination.",
        ],
    )
    native = terrain["original_terrain"]
    page(
        "Terrain resolution and North conventions need explicit provenance",
        "Delivered terrain rasters allow a bounded cross-check, not identification of the actual historical generating surface.",
        rows=[
            (
                "Available DTM",
                f"{native[0]['resolution_m'][0]:.3f}m cells; diagnostic median slope difference vs inherited{native[0]['legacy_slope_difference_degrees']['quantiles'][4]:+.2f}degrees",
            ),
            (
                "Available DEM",
                f"{native[1]['resolution_m'][0]:.3f}m cells; diagnostic median slope difference{native[1]['legacy_slope_difference_degrees']['quantiles'][4]:+.2f}degrees",
            ),
            (
                "Aligned elevation",
                f"0.1m cells; diagnostic median slope difference{native[2]['legacy_slope_difference_degrees']['quantiles'][4]:+.2f}degrees",
            ),
            (
                "Grid convergence",
                f"{terrain['meridian_convergence_degrees']:.3f}degrees at scene center; both aspect-sign sensitivities retained in terrain_audit.json",
            ),
            (
                "Intended legacy process",
                "Available R source: ground-classified0.25 m TIN, slope/aspect in degrees, then scalar bilinear resampling. Exact execution/source link unresolved.",
            ),
        ],
        findings=[
            "Diagnostic gradients assume delivered elevation values are metres; they do not silently replace the correction terrain.10 cm resampling does not establish10 cm independent terrain detail.",
            "Aspect is circular: scalar bilinear interpolation across0/360 can be problematic. This is a provenance risk, not a demonstrated cause of this red pole. Local back-facing incidence is not a complete shadow mask.",
        ],
    )
    page(
        "Why historical SCS+C became unstable",
        "SCS+C multiplies each band by [cos(solar zenith)cos(slope)+C]/[cos(i)+C], with C=intercept/slope of the reflectance-illumination regression.",
        fig(4),
        findings=[
            "At native row 1178,column 1533: slope41.891degrees, illumination0.3482566, red C=-0.3472517, denominator0.001004964 and gain309.91684. Historical red has11,305 pixels above10x on its native support.",
            "This is an interior pole induced by a negative fitted intercept relative to slope. It is not limited to terrain shadows or invalid source alpha, and the candidate multiplier cannot remove it.",
            "The existing .001 denominator guard returns raw values for invalid ratios, leaving a sharp transition just above the threshold. Current and historical functions agree; no new implementation error is required to explain the behavior.",
        ],
    )
    page(
        "What was stabilized, and what was only diagnosed",
        "The predeclared experimental rule treats uncertain or extrapolated observations as unsupported; it does not force factors into a desired numerical range.",
        fig(5),
        findings=[
            "Eligible fitting: finite source/geometry, cos(i)>0, slope>5degrees, all evaluated polygon pixels plus2 m buffer excluded. No reflectance threshold was invented; missing quality flags prevent certifying cloud/canopy-shadow exclusions.",
            "OLS C uncertainty:399 spatial 20 m-block bootstrap draws from a deterministic1-in17eligible sample. Application requires observed fit-domain illumination and positive numerator/denominator throughout the95% C interval, denominator>.001. This is an experimental uncertainty rule, not a universal physical threshold.",
            "Huber epsilon1.35,alpha0 on the same eligible sample is a robust-fit comparison. It still produces about296x maximum red gain. Unconstrained OLS/Huber negative C remains empirical, not a measured diffuse-irradiance component.",
            "The already-implemented cosine alternative has a maximum red factor38,965x on native support; it is retained as an established diagnostic and rejected for full-footprint use.",
        ],
    )
    page(
        "Visual appearance cannot certify reflectance",
        "Raw, historical, current, robust, stabilized and cosine branches all use the same source/grid/bands, and no branch includes BRDF.",
        fig(6),
        findings=[
            "Maps use shared display bounds only; full numerical tails, negative values and R>1 frequencies remain in scene_statistics.json. Historical native red reaches16.45; stabilized native red still reaches1.72. Neither is independently validated physical truth.",
            "The main comparison uses6,614,170 common pixels. Historical red has2020native pixels above1; stabilized has13, raw has0. No negative values occur in these red branches. The stabilized mask removes69,774raw pixels including5,540missing-geometry cells.",
        ],
    )
    page(
        "Signed changes and the locations of extreme gains",
        "Correction differences are evaluated on the same grid, without fabricating missing observations.",
        fig(14),
        findings=[
            "The difference maps show band-specific changes; shared spatial support is required for comparisons. The historical red maximum is marked at its actual native row/column.",
            "Display bounds are independent of analysis. Large ratios are counted and mapped; no clipping or value replacement is used in the stabilized branch.",
        ],
    )
    page(
        "Unsupported pixels are a scientific result",
        "Pole-adjacent observations cannot be rescued merely by making the output finite.",
        fig(7),
        findings=[
            "The stabilized support retains98.96% of the raw footprint; all157 previously analyzed identities remain, but common memberships fall from144,406 to 142,656.",
            "The reused package index contains158candidate identities; one additional Woody shrub polygon has no valid raw observations. The evaluated class totals remain98 Evergreen,29 Woody shrub,25 Herbaceous,5 Deciduous. No label was changed.",
            "Native support and common support answer different questions. Do not substitute rejected pixels with raw data and describe that hybrid as a completed physical correction.",
        ],
    )
    page(
        "How the spectra change",
        "All branches are evaluated using exactly matched polygon pixels and the same ten native MicaSense bands.",
        fig(8),
        findings=[
            "Common scaling preserves spectral shape, NDVI, spectral angles and CV; absolute values, residuals, variance, Euclidean distances and thresholds atR=1 depend on scale.",
            "Actual shared SCS+C C values were identical at candidate scale and S/10000. Applying through stored-space and decoded-space calls agrees to Float32 precision; the standardized classifier produces identical predictions under equivalent common scaling.",
            "Band-specific SCS+C factors can change spectral shape and red-edge/NIR-red relationships. Detailed native/common distributions, negative and above-one counts, spectral angles and red-edge reversals are retained for all branches.",
        ],
    )
    cv0 = med.loc["raw", "median_band_cv"]
    cv1 = med.loc["stabilized", "median_band_cv"]
    a0 = med.loc["raw", "within_angle_median"]
    a1 = med.loc["stabilized", "within_angle_median"]
    page(
        "Within-polygon consistency is mixed",
        "Absolute variance, relative variability and spectral angle must be interpreted together.",
        fig(9),
        findings=[
            f"Median polygon band CV rises from{cv0:.4f}raw to{cv1:.4f}stabilized; median within-polygon angle rises from{a0:.3f}to{a1:.3f}degrees.",
            f"Median mean-band variance falls from{med.loc['raw', 'mean_variance']:.7f}to{med.loc['stabilized', 'mean_variance']:.7f}, but lower absolute variance alone does not establish cleaner spectra.",
            "The result does not support a blanket statement that stabilized SCS+C improves within-polygon spectral consistency. PFT-specific variability and changes in spectral relationships are available in compact tables.",
        ],
    )

    def partial(n, w):
        return float(
            dependence[
                (dependence.branch == n) & (dependence.wavelength_nm == w)
            ].partial_illumination_pearson.iloc[0]
        )

    page(
        "Illumination dependence is reduced, with ecological ambiguity",
        "Across157 polygon means, partial associations control recorded class and a linear spatial plane. This is a descriptive control, not causal separation of topography from vegetation.",
        fig(10),
        findings=[
            f"Red partial illumination correlation changes from{partial('raw', 650):+.3f}raw to{partial('stabilized', 650):+.3f}stabilized; NIR changes from{partial('raw', 862):+.3f}to{partial('stabilized', 862):+.3f}.",
            "Residual slope/aspect/illumination associations, whole-scene and class/spatial-controlled results are retained. A linear spatial plane cannot remove all spatial autocorrelation or genuine vegetation-habitat relationships.",
            "A weak or sign-reversed relationship after correction can indicate overcorrection. No invariant target or independent radiometer is available to establish improved physical accuracy.",
        ],
    )
    page(
        "PFT identification does not establish a correction benefit",
        "Package evaluate_identifiability: fixed3 polygon-disjoint folds, training-only feature scaling, fixed C=1, no PFT-based correction tuning and no pixel-level leakage.",
        fig(11),
        findings=[
            f"Raw common-support balanced accuracy={rawacc:.2%}; stabilized={stableacc:.2%}. Paired change={stable_gain['difference'] * 100:+.2f}points,95%interval[{stable_gain['low'] * 100:+.2f},{stable_gain['high'] * 100:+.2f}]points;26 predictions change.",
            "Uncertainty uses1,999 class-stratified whole-polygon draws of fixed out-of-fold predictions. It omits training-set/model/coefficient uncertainty, nearby-polygon dependence and site/year transfer. Five deciduous identities make class recall particularly unstable.",
            "Eligible/robust/stabilized fits exclude all evaluation polygons and2 m buffer, so no test-polygon reflectance enters those coefficient fits. Historical/current scene-wide fits are explicitly transductive baselines, not evidence of held-out calibration performance.",
        ],
    )
    page(
        "Separability is not uniformly improved",
        "Package spectral_separability uses499 permutations, polygon identities and equal discrete-band integration weights. Pairwise distances, overlap, angles and Holm-adjusted evidence are retained.",
        fig(12),
        findings=[
            "Raw has5/6class pairs with Holm-adjusted NPC p<0.05; stabilized has4/6. Between-class angular separation and within-class spread change by pair. A significant class difference within a branch does not test whether correction improved it.",
            "These are exploratory multiple-branch comparisons. There is no independent ecological ground truth establishing that reduced illumination correlation or a particular classifier score preserves all genuine vegetation variation.",
        ],
    )
    page(
        "Why the earlier71.7% must not be carried forward unchanged",
        "The earlier P169 analysis used polygon means and its original support. That historical score is reproduced exactly; the raw native benchmark remains66.83%.",
        fig(13),
        findings=[
            "Primary comparisons here also use means for compatibility. Polygon medians are retained as a sensitivity analysis, not selected based on a better score. On common support, the median analysis also does not establish a stabilized correction gain.",
            "With the original support, raw66.83%versus historical71.71%can be reproduced. Restricting both to the new common support yields raw68.30%and historical64.20%. A benefit that depends on rejected pole-adjacent observations cannot justify production use.",
            "No nested tuning was needed: correction rules, Huber epsilon, classifier C, folds and seeds were fixed. These data do not choose a new production algorithm.",
        ],
    )
    decisions = [
        (
            "1. Numerically consistent candidate reflectance?",
            "Yes, conditional on DN/32768. Ten-band affine conversion/masks and precision verified; calibration not verified.",
        ),
        (
            "2. Scale-invariant SCS+C?",
            "Yes at the tested scales and masks; C and factors unchanged. An absolute near-zero-slope tolerance can break invariance in other regimes.",
        ),
        (
            "3. Cause of historical extremes?",
            "Negative fitted C cancels positive illumination near the .001 guard. Uncertain/confounded regression, not the common radiometric multiplier.",
        ),
        (
            "4. Preventable instability?",
            "Resolved-domain/uncertainty exclusions prevent these near-pole outputs without clipping; better fitting/Huber alone does not.",
        ),
        (
            "5. Less illumination dependence?",
            "Yes descriptively, with weak negative residual red correlation; not independent physical validation.",
        ),
        (
            "6. Spectral relationships preserved?",
            "Not uniformly: band-dependent factors alter shape; no absolute reference certifies improvement.",
        ),
        (
            "7. Better within-polygon consistency?",
            "Not overall: lower absolute variance, but higher CV and spectral angle.",
        ),
        (
            "8. Better PFT separability?",
            "Mixed class-pair effects; no general or independently validated gain.",
        ),
        (
            "9. Better PFT identification?",
            "No established gain on matched support; stabilized65.2%versus raw68.3%, paired interval spans zero.",
        ),
        (
            "10. Experimental use?",
            "Yes for explicitly conditional diagnostic sensitivity analysis; raw remains primary for ecological interpretation.",
        ),
        (
            "11. Production readiness?",
            "No. Verify calibration, timing/terrain/shadows and North/contributor provenance; independent targets and spatial/site-held-out evaluation are needed.",
        ),
    ]
    # Split long decision table over two readable pages.
    page(
        "Direct scientific decisions: arithmetic and stability",
        "No physical-calibration promotion follows from successful numerical tests.",
        rows=decisions[:6],
        section="Final scientific decision",
    )
    page(
        "Direct scientific decisions: information and deployment",
        "Keep raw candidate reflectance as the baseline. Retain explicit refusal/support masks in experimental outputs.",
        rows=decisions[6:],
        findings=[
            "Recommended production improvements are a separate future change: explicit per-band coefficient/support uncertainty, denominator-domain checks, non-neutral unsupported reporting and held-out scientific validation. Do not deploy this experimental mask as a universal rule."
        ],
        section="Final scientific decision",
    )
    refs = [
        (
            "Soenen,Peddle&Coburn(2005)",
            "SCS+C, IEEE TGRS43:2169-2175. https://doi.org/10.1109/TGRS.2005.852480",
        ),
        (
            "Slope-classified SCS+C study(2017)",
            "Slope-stratified SCS+C study. https://www.mdpi.com/2220-9964/6/9/287",
        ),
        (
            "Evaluation/intercomparison study(2021)",
            "Evaluation/intercomparison; excludes flat/cloud/cast-shadow regions from regression. https://www.mdpi.com/2072-4292/13/20/4120",
        ),
        (
            "Richter,Kellenberger&Kaufmann(2009)",
            "Comparison of topographic corrections. https://www.mdpi.com/2072-4292/1/3/184",
        ),
        (
            "Kaneetal.(2008)",
            "Interpretation and topographic compensation of conifer canopy self-shadowing. https://doi.org/10.1016/j.rse.2008.06.001",
        ),
        (
            "MicaSense calibrated Metashape units",
            "https://support.micasense.com/hc/en-us/articles/1500012483982-Analyzing-MicaSense-data-processed-with-Agisoft-Metashape",
        ),
    ]
    page(
        "Methodological basis and evidence boundaries",
        "The literature supports SCS+C/C formulations, attention to illumination/terrain/shadows and empirical coefficient-population sensitivity. It does not validate this exact Goldhill uncertainty rule.",
        rows=refs,
        findings=[
            "The new95%block-bootstrap positivity/domain mask is an explicitly experimental statistical eligibility rule motivated by resolved model predictions and avoidance of extrapolation. It is not a published universal physical criterion.",
            "Clock convention: MicaSense panel documentation states UTC image metadata: https://support.micasense.com/hc/en-us/articles/115000765514-Use-of-Calibrated-Reflectance-Panels-For-MicaSense-Data . A nonnegative diffuse-term constraint was considered but not imposed: forcing C>=0 would change the empirical model without evidence and would not verify calibration. Robust fitting was actually evaluated instead.",
        ],
        section="References and method boundary",
    )
    page(
        "Reproducibility and preservation",
        "Revision2444902440a48453ed14855473d3250020ba8bb3. Scientific environment: existing repository.venv; seeds20261103. Report rendering uses bundled ReportLab.",
        rows=[
            (
                "Execution",
                "experiment.py -> geometry_audit.py -> analyze.py -> median_sensitivity.py -> additional_checks.py -> figures.py -> write_report.py -> make_pdf.py -> verify.py",
            ),
            (
                "Primary data",
                "Original/fixed TIFF hashes, geometry and polygon index paths are in input_manifest.json. All historical P169 products/code were hashed before and after; no writes.",
            ),
            (
                "Adapter",
                "HypothesisRadiometry calls Radiometry._affine. FunctionType copies namespace require_radiometry binding only; production globals unchanged; scientific function bytecode identical. Production require_valid still rejects hypothesis.",
            ),
            (
                "Storage",
                "Seven10-band Float32 arrays are isolated under /private/tmp/goldhill-conditional-topographic-20261103 (~2GB). No ordinary bulk pixel-Parquet cache or official spectral library. Compact tables/masks/figures/scripts remain in dated provenance.",
            ),
            (
                "Verification",
                "Targeted synthetic unit/contract/integration checks, source hashes, decode once, orientation/band/mask checks, identical CV memberships, no clipping/no BRDF/no VALID promotion; see verification.json.",
            ),
        ],
        findings=[
            "Scripts expose stage progress and process corrections in128-row chunks. This is a bounded single-flight research experiment, not a large-VM streaming benchmark or a change to normal pipeline restart contracts."
        ],
        section="Reproducibility",
    )
    import re

    def readable(value):
        pieces = re.split(r"(https?://\S+|[0-9a-f]{20,})", value)
        for i in range(0, len(pieces), 2):
            pieces[i] = re.sub(
                r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", pieces[i]
            )
        return "".join(pieces)

    for item in pages:
        for key in ["title", "intro"]:
            item[key] = readable(item[key])
        for key in ["findings", "notes", "columns"]:
            item[key] = [readable(t) for t in item[key]]
        item["rows"] = [[readable(t) for t in row] for row in item["rows"]]
        if item["figure"]:
            item["figure"]["caption"] = readable(item["figure"]["caption"])
    (HERE / "report_pages.json").write_text(json.dumps(pages, indent=2) + "\n")
    lines = [
        "# " + TITLE,
        "",
        "November 3, 2026. **HYPOTHETICAL_UNVERIFIED** calibration; isolated P171 experiment.",
        "",
    ]
    for i, p in enumerate(pages, 1):
        lines += ["## " + str(i) + ". " + p["title"], "", p["intro"], ""]
        if p["rows"]:
            lines += [
                "| " + " | ".join(p["columns"]) + " |",
                "| " + " | ".join(["---"] * len(p["columns"])) + " |",
            ]
            lines += ["| " + " | ".join(row) + " |" for row in p["rows"]]
            lines += [""]
        if p["figure"]:
            f = p["figure"]
            lines += ["![" + f["caption"] + "](" + f["png"] + ")", "", f["caption"], ""]
        lines += ["- " + s for s in p["findings"]]
        lines += [""]
    # Additional full per-band coefficient table remains in Markdown, not tiny PDF text.
    lines += [
        "## Per-band fitted C audit",
        "",
        "| nm | Historical/current C | Eligible OLS C | Huber C |",
        "| --- | ---: | ---: | ---: |",
    ]
    from experiment import WAVES

    lines += [
        f"| {w} | {C['current'][b]:.9f} | {C['eligible'][b]:.9f} | {C['robust'][b]:.9f} |"
        for b, w in enumerate(WAVES)
    ]
    lines += [
        "",
        "All coefficients, sample counts, residuals and fit diagnostics: [regression_diagnostics.json](regression_diagnostics.json). Native/common per-band distribution counts: [scene_statistics.json](scene_statistics.json). Pairwise statistical evidence: [separability_pairs.csv](separability_pairs.csv). Machine summary: [scientific_summary.json](scientific_summary.json).",
        "",
    ]
    text = "\n".join(lines)
    (HERE / "report.md").write_text(text)
    relative = "../../provenance/goldhill-conditional-topographic/2026-11-03/"
    local = re.sub(
        r"\]\((?!https?://)([^)]+)\)",
        lambda m: "](" + relative + m.group(1) + ")",
        text,
    )
    (
        ROOT / "docs/dev/goldhill-conditional-reflectance-topographic-experiment.md"
    ).write_text(local)
    result = dict(
        status="COMPLETED_CONDITIONAL_DIAGNOSTIC_EXPERIMENT",
        calibration_status="HYPOTHETICAL_UNVERIFIED",
        hypothesis="MicaSense_Metashape_DN_32768",
        scale=0.0001999969482421875,
        offset=0,
        classification=scores,
        paired_gains=gains,
        common_support=summary,
        final_decisions=dict(decisions),
        production_ready=False,
        recommendation="Keep raw candidate reflectance primary. Stabilized branch is a resolved-support sensitivity diagnostic, without established PFT/physical accuracy gain. No production change.",
        figures=len(figs),
        PDF_pages=len(pages),
        production_changes=0,
    )
    (HERE / "scientific_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(len(pages), "report pages prepared")


if __name__ == "__main__":
    main()
