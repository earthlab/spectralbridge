"""Build the science-team narrative from compact measured results and stage refusals."""

import json
from pathlib import Path
import re
from readability import readable

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TITLE = "Goldhill BRDF Correction: Resolving the Red-Line Artifact"


def read(n):
    return json.loads((HERE / n).read_text())


def main():
    figures = read("figure_manifest.json")
    counts = read("filter_counts.json")
    artifact = {x["branch"]: x for x in read("artifact_metrics.json")}
    scores = {x["branch"]: x for x in read("classification_summary.json")}
    gains = {x["branch"]: x for x in read("paired_gain.json")}
    geom = read("geometry_feasibility.json")
    scaling = read("ingestion_and_scaling.json")
    pages = []
    poly = pd.read_csv(HERE / "polygon_summaries.csv")
    med = poly.groupby("branch")[
        ["median_band_cv", "mean_variance", "within_angle_median"]
    ].median()
    A = artifact["A_historical_BRDF"]
    B = artifact["B_clean_historical_BRDF"]
    R = artifact["raw_clean"]
    gain = gains["B_clean_historical_BRDF"]
    change = (
        (
            A["red_cross_boundary_difference"]["quantiles"][4]
            - B["red_cross_boundary_difference"]["quantiles"][4]
        )
        / A["red_cross_boundary_difference"]["quantiles"][4]
        * 100
    )

    def fig(i):
        f = figures[i - 1]
        return dict(png=f["png"], caption=f["caption"])

    def page(
        title,
        intro,
        figure=None,
        findings=(),
        rows=(),
        columns=("Question", "Measured outcome"),
        notes=(),
        section="Clean-source BRDF investigation",
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

    page(
        TITLE,
        "November3,2026. Underlying causes are quantitatively identified and the shared pathway is hardened. Goldhill still lacks the evidence needed for a scientifically supported BRDF product.",
        rows=[
            (
                "Source repair",
                "Correct10cm,ten-band,alpha-aware numerical derivative used throughout. Calibration remains HYPOTHETICAL_UNVERIFIED.",
            ),
            (
                "Artifact attribution",
                "The raw boundary is ordinary; the historical BRDF model produces the enormous jump on both old and clean sources.",
            ),
            (
                "Filtering",
                "Red eligibility rises14 ->6,678,404under correct candidate units; stable angular rank remains1/3.",
            ),
            (
                "Implemented reliability",
                "Footprint/quality/NDVI filtering, missing-geometry records, band identity, stable-rank diagnostics, common fit/application prediction checks and versioned model/header acceptance.",
            ),
            (
                "Supported control",
                "Real NEON window:10/10bands supported in BRDF-only and combined branches; corrected values/masks identical before/after.",
            ),
            (
                "Goldhill outcome",
                "No C/D/E/Fcorrected image is fabricated. Calibration and genuine contributor/view information remain prerequisites.",
            ),
        ],
        findings=[
            "BRDF remains requested in the drone workflow. No original source, historical result, official spectral library or production calibration registry was overwritten."
        ],
    )
    page(
        "What the repaired source changes",
        "The source repair excludes transparent65535background before interpolation and removes per-band minimum subtraction. It does not supply angular information.",
        fig(1),
        findings=[
            f"Historical finite support={counts['historical_native']:,}pixels; clean support={counts['clean_source_valid']:,}. Revised historical prefit support={counts['C_revised_prefit']:,}; revised clean prefit support={counts['D_revised_prefit']:,}.",
            f"The estimated legacy bilinear mixing footprint intersects{counts['estimated_legacy_mixed_background_on_clean_footprint']:,}clean-footprint cells. This is a source-validity reconstruction, not a brightness cutoff or recovered exporter certificate.",
            "Both uncorrected sources lack this particular BRDF boundary artifact. Raw imagery is a baseline, not a secretly substituted successful correction.",
        ],
    )
    page(
        "One affine physical interface, two different source encodings",
        "Clean S=DN x10000/65535. Under the unverified MicaSense hypothesis, R=DN/32768=S x0.0001999969482421875,offset0. NEON decodes its documented source divisor10000to fractional reflectance.",
        rows=[
            (
                "Calibration status",
                "Goldhill HYPOTHETICAL_UNVERIFIED, hypothesis MicaSense_Metashape_DN_32768; never VALID or VERIFIED.",
            ),
            (
                "Historical comparison encoding",
                "The historical NIR minimum174requires inverse slope0.0001994659423828125and offset0.00531005859375. Other historical channels use the common candidate multiplier. Reexpression does not approve historical corrections.",
            ),
            (
                "Ten-band checks",
                f"All ten decoded source comparisons are exact at Float32 arithmetic. Largest stored-space round-trip error={max(x['max_roundtrip_stored_error'] for x in scaling['checks']):.9g}; masks, wavelengths, CRS and north-up orientation preserved.",
            ),
            (
                "Scaling invariance",
                "With the same design/population and common multiplier k, beta*=k beta and both predictions scale by k, so their ratio cancels. A supported synthetic RossThick/LiDenseR control verifies this property.",
            ),
            (
                "What breaks that comparison",
                "Incorrect unit-based fitting thresholds, band-specific offsets, changing masks/NDVI strata and cancellation/roundoff can change an actual historical fit or its unstable numerical behavior.",
            ),
        ],
        findings=[
            "Physical decoding occurs once on entry to each calculation, with inverse encoding on native storage output. A subsequent stage decodes that stored result once again; it is not multiplied twice without inversion.",
            "The isolated adapter delegates to Radiometry._affine and changes only the experimental calibration precondition. Its inherited production require_valid still rejects the hypothesis. Scientific kernels, fitting/rank/prediction gates remain the actual implementations.",
        ],
    )
    page(
        "What the filters actually remove",
        "Source, radiometric, terrain, numerical angular, fitting and application support are distinct. Finite zero-angle placeholders are not measured contributor geometry.",
        fig(2),
        findings=[
            "Explicit source footprint is intersected independently with the combined mask. Nonfinite values and declared NoData/saturation are separate from observed zeros and finite negative measurements.",
            "Fitting uses the existing configurable physical interval0-2by default; the isolated angular investigation uses rho_max=None. No new reflectance threshold or ROI mask was introduced to erase the line.",
            "When optional NDVI strata are enabled, percentile edges now exclude source-invalid/angular-invalid observations and invalid665/865nmmeasurements. They cannot be set by transparent background or a different red channel.",
            "Finite topographic outputs are not automatically scientifically supported: P171found separate SCS+C instability. The main artifact factorial is BRDF-only; topographic-only is an explicitly unapproved diagnostic comparator.",
        ],
    )
    page(
        "The factorial comparison has honest unsupported branches",
        "Pinned historical functions are executed for A/Band actual revised-population historical refits for C/D. Current shared functions are used for E. No geometry or independent coefficient set was manufactured for F.",
        fig(3),
        findings=[
            "A/Buse the identical preserved saved production model. This isolates changing source/encoding without attributing a new model to cleaner pixels. Both stored-array replays match their preserved prior outputs exactly.",
            "C/Dhistorical refits estimate diagnostic coefficient vectors, but stable rank1makes them non-identifiable. They are recorded as unsupported and never applied. Ehas no usable coefficients for the same underlying support reason.",
            "C/D/Ereport application support0because no model is supported. This does not mean their correction successfully removed the artifact; there is no corrected image or PFT score.",
        ],
    )
    page(
        "When does the known red boundary appear?",
        "The P165evaluation ROI, transect, inside/outside locations, unaffected reference and boundary-crossing Deciduous polygon are fixed before this experiment.",
        fig(4),
        findings=[
            f"On{read('fixed_regions.json')['artifact_common_pixels']:,}common source pixels,the A/Bextreme-boundary pattern agrees100%. The current common-mask evaluation contains{B['fixed_edges']:,}native boundary edges; these counts depend on the declared support, not a newly chosen line.",
            f"Median red cross-boundary jump: clean raw{R['red_cross_boundary_difference']['quantiles'][4]:.8f}; A{A['red_cross_boundary_difference']['quantiles'][4]:,.2f}; B{B['red_cross_boundary_difference']['quantiles'][4]:,.2f}candidate-equivalent units.",
            "Full-scene/ROIimages share display limits. Analytical ranges and extreme gains are retained; saturation in a displayed color scale is not data clipping.",
        ],
    )
    page(
        "The source repair barely changes the historical boundary jump",
        "This is the decisive source-versus-model contrast, with the model held fixed.",
        fig(5),
        findings=[
            f"Changing old to clean source reduces the median historical boundary jump by only{change:.5f}%on the fixed common edges. It does not eliminate the stripe. This measured contrast is not a universal percentage causal attribution.",
            f"At row921,columns980/981,the clean raw difference is{R['fixed_jump']:.8f}, while Bhas{B['fixed_jump']:,.2f}candidate-equivalent units. Topography alone has{artifact['topographic_only']['fixed_jump']:.8f}at that pair.",
            "Reconstructed A/Bfactors can differ by a few Float32ULPs at gains near1e7because they are recovered from output/input ratios. The saved-model prediction mechanism and affected-pattern location are unchanged.",
        ],
    )
    page(
        "Why the historical prediction fails",
        "Historical red fitting included only14observations under an erroneous stored-unit0-2filter. The old geometric kernel also had a spurious nadir-azimuth response; deficient angular support was not rejected.",
        fig(6),
        findings=[
            "At the fixed pair,the predicted denominator changes from0to0.0078125while the reference prediction is91,740.234375. The old policy switches from identity to factor11,742,750.",
            "The old guard can hide nonpositive predictions behind an unchanged signal and apply enormous positive ratios next door. This is not a physical edge or proof of a calibrated surface response.",
            "Current application shares fitting positivity, Float32roundoff and1.96OLSstandard-error checks. Unresolved predictions raise explicit errors instead of returning identity or capped factors. These uncertainty checks are computational, not spatially independent field confidence.",
        ],
    )
    page(
        "The shared Ross-Li mathematics was already repaired",
        "The existing mathematical audit distinguishes reciprocal LiDenseR from nonreciprocal dense and LiSparseR. This task keeps the validated kernel equations and math-version identifier unchanged.",
        fig(7),
        findings=[
            "The independent published-equation fixtures, nadir invariance, reciprocity, wrapping, shape parameters, units and invalid-angle tests are rerun. Crown b/rtransforms tangent zenith; it is not an output-amplitude multiplier.",
            "Both production paths explicitly use RossThick/LiDenseR,b/r10,h/b2,scene solar; direct helper defaults remain RossThick/LiSparseReciprocal,b/r1,h/b2,pixel solar.",
            "Correction is observed reflectance times predicted reference/observed reflectance. The reference remains solar45degrees,nadir view,relative azimuth0. A correct kernel cannot manufacture missing observation directions.",
        ],
    )
    page(
        "A larger population is not an identifiable directional model",
        "Under repaired units,all ten revised Goldhill bands have millions of eligible numerical values. The current scene-solar/nadir design still has one independent row combination.",
        fig(8),
        findings=[
            "Stable angular rank is1for every revised Goldhill band. Algebraic rank, singular values, condition number and precision tolerance are recorded separately; tiny singular values do not establish directional observations.",
            "The current fitter requires at least4eligible observations,rank3and condition<=about2896. No arbitrary neutral coefficient vector is labeled a successful fit. Unsupported models expose no usable current coefficients.",
            "Effective independent sample size is explicitly not estimated. Repeated nearby pixels and one constant view do not become millions of independent angular observations. Supported NEONcontrol bands have stable rank3.",
        ],
    )
    mincam = min(r["conditional_nadir_cone_candidates"] for r in geom["records"])
    maxcam = max(r["conditional_nadir_cone_candidates"] for r in geom["records"])
    page(
        "What can the recovered camera records resolve?",
        "There are5650band-camera records and565distinct positions. Rotation matrices are numerically orthogonal, but their world/camera conventions, vertical datum and stated CRSstill require confirmation.",
        fig(9),
        findings=[
            f"At the four fixed ROIpoints,an explicitly conditional nadir-FOVcone leaves{mincam}-{maxcam}possible cameras per point,with view-zenith envelopes roughly1-29degrees. These are proxy scenario envelopes,not actual contributors or statistical confidence intervals.",
            "The CSVsays CRS5070while its numbers align with the26913mosaic. The delivered elevation and pose heights were used only under a stated common-datum scenario. No ray is assigned to an orthomosaic pixel.",
            "Most practical route: obtain a small source-linked export of calibrated overlapping image patches/tie points with camera poses,intrinsics,CRS/time/surface conventions; or contributor IDs and per-band blend weights if retrievable. A whole archive is not required merely to export those records.",
        ],
    )
    page(
        "External or constrained coefficients need independent evidence",
        "Goldhill cannot estimate three free directional coefficients from this encoded geometry. Reduced parameterization does not remove the need for defensible external directional information.",
        fig(10),
        findings=[
            "The three bars are synthetic algebra on the actual nadir design: the same observed prediction can yield reference0.15,0.3or0.6. They are not fitted Goldhill models and are never applied.",
            "The new actual NEONmodels are computationally supported controls,not independently validated2023Goldhill MicaSense transfers. Spectral response,vegetation,site/year,geometry and normalization domain must be tested before transfer. Nearest native channels do not supply sensor-band calibration.",
            "For a blended mosaic,average view angles are not equivalent to weighted kernel predictions. Source-linked contributor weights could support kernel aggregation under validated assumptions; otherwise normalize calibrated observations before mosaicking. This source-bound APIis not silently converted into an external-model consumer.",
        ],
    )
    page(
        "What happens to a known polygon spectrum?",
        "All PFTcomparisons use157unchanged researcher identities and144,406common polygon-pixel memberships. Sampling uses the package pixel-center index on the repaired grid.",
        fig(11),
        findings=[
            "The Deciduous exemplar was selected by the earlier artifact study. Red650and717nmcan dominate the historical normalized spectrum; a generic RGBomitting those bands can conceal that corruption.",
            "Spectral angle,red-edge reversals,NIR/redrelationships,within-polygon CV/variance and class distances/overlap are retained. Smaller within-polygon angular spread can reflect domination by a corrupted band,not improved physical spectra.",
            "C/D/E/Fhave no corrected spectra. No raw spectrum or neutral normalization is substituted and labeled a revised BRDFproduct.",
        ],
    )
    page(
        "Does the historical correction improve PFT information?",
        "Package spectral_separability and evaluate_identifiability use independent polygon identities,identical3fold memberships,training-only scaling and fixed classifier C1. No BRDFparameter was selected using held-out PFTscores.",
        fig(12),
        findings=[
            f"Raw clean balanced accuracy={scores['raw_clean']['balanced_accuracy']:.2%}; clean-source historical BRDF={scores['B_clean_historical_BRDF']['balanced_accuracy']:.2%}. Paired difference={gain['difference'] * 100:+.2f}points,95%interval[{gain['low'] * 100:+.2f},{gain['high'] * 100:+.2f}];33predictions change.",
            f"Median within-polygon variance grows from{med.loc['raw_clean', 'mean_variance']:.7f}to{med.loc['B_clean_historical_BRDF', 'mean_variance']:,.2f}. Median angular spread falls from{med.loc['raw_clean', 'within_angle_median']:.3f}to{med.loc['B_clean_historical_BRDF', 'within_angle_median']:.3f}degrees; this is not physical improvement.",
            "The interval uses1999class-stratified whole-polygon draws of fixed OOFpredictions; it excludes training/model/site/year uncertainty and nearby-polygon dependence. Classes:98Evergreen,29Woody shrub,25Herbaceous,5Deciduous. Pairwise permutation evidence is exploratory; no new class or abundance truth is invented.",
        ],
    )
    page(
        "The actual supported NEON control is unchanged",
        "A fixed120x3000native window from the archived2021R10Cdirectional H5provides real solar/view geometry and authoritative documented physical decoding. Ten nearest native channels are a bounded shared-function test.",
        fig(13),
        findings=[
            "Both actual corrected controls serialize through EnviWriter and pass library header acceptance. Before and after hardening,BRDF-only and combined models support10/10bands; their corrected arrays and masks are identical,maximum absolute difference0. Both paths use actual measured reflectance,not a synthetic replacement signal.",
            "Observed/reference predictions pass the common roundoff/uncertainty checks. Reference predictions lie within the component kernel bounds in this control; bounds alone are not independent transfer validation.",
            "This is a representative bounded regression control,not a full native-band flightline reprocessing claim or proof of empirical BRDFaccuracy. The separate known-coefficient synthetic controls verify ratio direction and scaling analytically.",
        ],
    )
    page(
        "The two platforms share mathematics,not missing inputs",
        "NEONand drone use the same affine converter,SCS+C,Ross-Li kernels,scene fits,reference/observed ratio and current model/library validity contracts.",
        fig(14),
        findings=[
            "NEONinputs have source-defined calibration and observation geometry; MicaSense orthomosaics need source-specific calibration and contributor geometry. Do not force identical coefficients,masks or angular arrays.",
            "AOPproduction builds a scene-topographic BRDFfit then applies the same stage and convolves supported hyperspectral output. Drone uses native wavelength identities and optional translation after supported correction. NDVIstrata are optional and default off in both.",
            "Shared kernels do not establish complete equivalence to grouped/stratified/interpolated FlexBRDF. Radiometric accuracy,land-cover confounding,shadow/terrain support and empirical normalization quality remain separate scientific evaluations.",
        ],
    )
    stage_rows = [
        (
            "Source ingestion and raw ENVI",
            "EXECUTED:ten-band values,masks,CRS/orientation preserved; no sensor-view placeholders written.",
        ),
        (
            "Radiometric decoding",
            "NUMERICALLY VERIFIED UNDER HYPOTHESIS:never approved physical calibration.",
        ),
        ("Raw polygon index", "EXECUTED using actual package index; labels unchanged."),
        (
            "Production topo/BRDFpreflight",
            "UNSUPPORTED:calibration hypothesis rejected; missing sensor_zn reported by direct BRDFmodel preflight.",
        ),
        (
            "Isolated conditional BRDF/combined",
            "UNSUPPORTED:actual shared functions reach stable-rank1gate; no corrected image.",
        ),
        (
            "Target-band physical translation",
            "UNSUPPORTED:all four actual plan calls refuse the unapproved physical source.",
        ),
        (
            "Approved polygon library",
            "UNSUPPORTED:actual extraction guard rejects; no official library created.",
        ),
        (
            "Actual producer",
            "All topo/BRDF/translation requests stay enabled. UTCscenario reaches radiometry guard; absent/embedded-only timestamps are separately blocked by timing preflight.",
        ),
    ]
    page(
        "End-to-end execution is not end-to-end approval",
        "Actual run_drone_pipeline and component calls retain stage-specific outcomes. Partial numerical success is not counted as a scientifically valid corrected flight.",
        rows=stage_rows,
        findings=[
            "The explicit UTCmanifest is a conditional timing scenario supported by recovered camera tags,not independent clock verification. No timing validation flag is presented as a calibration certificate.",
            "Raw and diagnostic files remain in a fresh temporary namespace. Unsupported stages are neither silently omitted nor substituted with a successful uncorrected product.",
        ],
    )
    decisions = [
        (
            "1. Contribution of source contamination?",
            f"It is a confirmed preprocessing defect,but A/Bboundary locations agree100%; fixed-model median jump changes only{change:.5f}%. It does not explain away the downstream line.",
        ),
        (
            "2. Contribution of fitting eligibility?",
            "The wrong units select only14red observations; revised units admit6.68million. Historical accepted coefficients are unreliable,but a separate causal percentage is not identifiable from rank1data.",
        ),
        (
            "3. Contribution of missing geometry?",
            "Fundamental non-identifiability:only one coefficient combination is determined. Two directional degrees of freedom and the reference response remain unsupported.",
        ),
        (
            "4. Does corrected scaling change coefficients/factors?",
            "Unit-based filtering and band offsets can change fitting populations/NDVI. A common positive multiplier cancels in a supported fixed-population ratio; unstable historical Float32cancellation can still be numerically sensitive.",
        ),
        (
            "5. Does clean source eliminate the artifact before BRDF?",
            "The particular line is absent in both raw sources; clean preprocessing is necessary independently. Historical BRDFreintroduces it on the clean source.",
        ),
        (
            "6. Does revised filtering prevent it during BRDF?",
            "Invalid fits cannot produce a valid output under current gates. C/D/Eare rejected; no corrected Goldhill image exists to declare artifact-free success.",
        ),
        (
            "7. Are current RossThick/LiDenseR correct?",
            "Yes against the established independent equations/property tests. Current equations are preserved; historical wrong nadir response is not reused as valid mathematics.",
        ),
        (
            "8. Can available Goldhill geometry support the fit?",
            "No. Zero placeholders with scene solar give stable rank1,not three independent parameters.",
        ),
        (
            "9. Most practical route to angular information?",
            "A small calibrated repeated-target subset with verified poses/intrinsics/terrain/CRS/timing,or source-linked contributors/blend weights. External coefficient transfer needs independent spectral/ecological/domain validation.",
        ),
        (
            "10. Does revised BRDFpreserve spectral consistency?",
            "No supported Goldhill output yet; cannot claim improvement. Historical diagnostic spectra are corrupted and PFTscores do not establish a benefit.",
        ),
        (
            "11. Is library reliability improved?",
            "Yes at the software boundary:unsupported/stale BRDFproducts cannot enter approved extraction under current guards. No Goldhill physical library was regenerated or validated.",
        ),
        (
            "12. What remains for production?",
            "Keep the shared validated mathematics and hardened guards. Supply verified drone calibration and genuine directional observations,then validate normalization on independent directions/targets and spatial/site-held-out ecological data.",
        ),
    ]
    page(
        "Direct decisions:source,filter and artifact attribution",
        "Measured contrasts and unsupported states answer different questions. Do not assign a causal fraction to an unidentified model.",
        rows=decisions[:6],
        section="Final required decisions",
    )
    page(
        "Direct decisions:mathematics,data and production readiness",
        "The reliable supported-input pathway is implemented. Goldhill remains scientifically blocked until its missing evidence is supplied.",
        rows=decisions[6:],
        section="Final required decisions",
    )
    refs = read("reference_sources.json")
    page(
        "Scientific basis and reference boundaries",
        "Primary references support the kernels,directional sampling and data requirements. They do not certify this Goldhill calibration or a transferred coefficient model.",
        rows=[(x["title"], x["url"]) for x in refs],
        findings=[
            "MODISATBDprovides RossThick/reciprocal overlap and linear inversion; LiDenseR uses the separate reciprocal dense formulation checked in the existing1220case audit. These variants are not interchangeable.",
            "FlexBRDFuses actual airborne directional observations and grouped/stratified processing. UAVradiometric block adjustment uses calibrated repeated observations,geometry and reference constraints. We do not import their conclusions as a universal Goldhill correction.",
        ],
        section="References",
    )
    page(
        "Reproducibility,preservation and computational scope",
        "Revision2444902440a48453ed14855473d3250020ba8bb3with the explicitly recorded working-tree changes. Python3.12repository environment; report uses bundled ReportLab.",
        rows=[
            (
                "Inputs and code",
                "input_manifest.json records protected source/historical paths+hashes and pre-edit snapshots. Modified code is separately hashed; original datasets and earlier investigations remain unchanged.",
            ),
            (
                "Scripts",
                "experiment.py ->legacy_refits.py ->geometry_feasibility.py ->analyze.py ->neon_control.py(before/after) ->pipeline_validation.py ->figures.py ->write_report.py ->make_pdf.py ->verify.py.",
            ),
            (
                "Acceptance order",
                "Before snapshots/control precede production changes; rerun current supported NEONcontrol and targeted tests after changes. C/Dlegacy coefficients remain diagnostic-only.",
            ),
            (
                "Memory/disk",
                "Correction application uses bounded window masks. Added per-fit covariance has9numbers,not a pixel-scale state file. Fitter remains scene-in-memory with existing physical/design buffers; no new large-VM streaming claim. Scratch image arrays are dated temporary diagnostics,not an ordinary bulk pixel Parquet cache.",
            ),
            (
                "Verification",
                "178 targeted tests pass (zero failures or skips). Source preservation,exact historical replay,ten-band scaling/masks/grid,independent kernels,rank/prediction guards,header policy propagation,raw/physical library boundaries and supported NEONregression are checked. See verification.json and test logs.",
            ),
        ],
        findings=[
            "All figures have short interpretations and fixed or declared display limits. Compact tables retain native/common support,coefficients,counts,predictions,spectra,PFTrecall/confusion/paired uncertainty and exact source identity. No source upload,official library regeneration,release or calibration promotion occurs."
        ],
        section="Reproducibility",
    )

    for p in pages:
        for k in ["title", "intro"]:
            p[k] = readable(p[k])
        for k in ["findings", "notes", "columns"]:
            p[k] = [readable(x) for x in p[k]]
        p["rows"] = [[readable(x) for x in row] for row in p["rows"]]
        if p["figure"]:
            p["figure"]["caption"] = readable(p["figure"]["caption"])
    (HERE / "report_pages.json").write_text(json.dumps(pages, indent=2) + "\n")
    lines = [
        "# " + TITLE,
        "",
        "November 3, 2026. **Goldhill calibration remains HYPOTHETICAL_UNVERIFIED.**",
        "",
    ]
    for i, p in enumerate(pages, 1):
        lines += ["## " + str(i) + ". " + p["title"], "", p["intro"], ""]
        if p["rows"]:
            lines += (
                [
                    "| " + " | ".join(p["columns"]) + " |",
                    "| " + " | ".join(["---"] * len(p["columns"])) + " |",
                ]
                + ["| " + " | ".join(row) + " |" for row in p["rows"]]
                + [""]
            )
        if p["figure"]:
            lines += [
                "![" + p["figure"]["caption"] + "](" + p["figure"]["png"] + ")",
                "",
                p["figure"]["caption"],
                "",
            ]
        lines += ["- " + x for x in p["findings"]] + [""]
    lines += [
        "## Detailed measured records",
        "",
        "- [Fitting populations,coefficients and rank](fitting_population_and_rank.json)",
        "- [Current conditional model](E_after_brdf_model.json)",
        "- [Native/common distributions](native_common_statistics.json)",
        "- [Fixed-edge artifact metrics](artifact_metrics.json)",
        "- [Per-polygon spectra and variability](polygon_summaries.csv)",
        "- [Class separation and corrected within-branch evidence](separability_pairs.csv)",
        "- [Paired prediction uncertainty](paired_gain.json)",
        "- [Actual pipeline stage results](pipeline_stage_results.json)",
        "- [Scientific summary](scientific_summary.json)",
        "- [Verification](verification.json)",
        "",
    ]
    text = "\n".join(lines)
    (HERE / "report.md").write_text(text)
    relative = "../../provenance/goldhill-clean-source-brdf/2026-11-03/"
    local = re.sub(
        r"\]\((?!https?://)([^)]+)\)",
        lambda m: "](" + relative + m.group(1) + ")",
        text,
    )
    (ROOT / "docs/dev/goldhill-clean-source-brdf-investigation.md").write_text(local)
    scientific = dict(
        status="INVESTIGATION_AND_SHARED_RELIABILITY_COMPLETE_GOLDHILL_UNSUPPORTED",
        calibration="HYPOTHETICAL_UNVERIFIED",
        scale=0.0001999969482421875,
        offset=0,
        source_repair_alone_eliminates_artifact=False,
        current_Goldhill_supported_bands=0,
        angular_stable_rank=1,
        factorial_status=read("factorial_status.json"),
        filter_counts=counts,
        artifact_metrics=artifact,
        classification=scores,
        paired_gains=gains,
        Goldhill_corrected_image_created=False,
        official_library_regenerated=False,
        BRDF_disabled=False,
        production_ready_Goldhill=False,
        shared_supported_input_hardening_implemented=True,
        final_decisions=dict(decisions),
        PDF_pages=len(pages),
        figure_pairs=len(figures),
    )
    (HERE / "scientific_summary.json").write_text(
        json.dumps(scientific, indent=2) + "\n"
    )
    print(len(pages), "report pages prepared")


if __name__ == "__main__":
    main()
