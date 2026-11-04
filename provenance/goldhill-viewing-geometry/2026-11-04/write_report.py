"""Narrative assembled from measured scenario outputs; no empirical promotion."""

import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TITLE = "Reconstructing Drone Viewing Geometry for Goldhill BRDF Correction"


def read(name):
    return json.loads((HERE / name).read_text())


def main():
    figures = read("figure_manifest.json")
    flight = read("flight_and_crs.json")
    geometry = read("geometry_summary.json")
    metrics = {r["branch"]: r for r in read("matched_metrics.json")}
    scores = {r["branch"]: r for r in read("classification_summary.json")}
    gains = {r["branch"]: r for r in read("paired_gain.json")}
    source = read("minimum_source_subset.json")
    pages = []

    def page(
        title,
        intro,
        fig=None,
        findings=(),
        rows=(),
        section="Goldhill viewing geometry experiment",
    ):
        pages.append(
            dict(
                title=title,
                intro=intro,
                figure=None
                if fig is None
                else dict(
                    png=figures[fig - 1]["png"], caption=figures[fig - 1]["caption"]
                ),
                findings=list(findings),
                rows=list(rows),
                columns=["Question", "Measured outcome"],
                notes=[],
                section=section,
            )
        )

    page(
        TITLE,
        "4 November 2026. Actual experimental corrected images are produced. The historical red-line pole is absent in the new BRDF-only images, but inferred camera assignments create their own uncertainty and seams. Nothing is promoted to an approved physical product.",
        rows=[
            (
                "What was implemented",
                "Reusable nadir ray, rectangular footprint, eligible assignment and kernel aggregation functions; source-only choices with unit/convention tests.",
            ),
            (
                "What was reconstructed",
                "565 timestamped positions, 27 sign-defined N/S path legs, 32 turn candidates and 5,650 band records. EPSG:26913 is explicitly supported by project/DEM report and independent spatial tests.",
            ),
            (
                "Numerical result",
                "Four main geometry scenarios, each BRDF-only and combined: all eight fits pass the existing ten-band rank, conditioning, positivity, roundoff and uncertainty rules; eight native 10 cm experimental GeoTIFFs written.",
            ),
            (
                "Scientific limitation",
                "Calibration remains HYPOTHETICAL_UNVERIFIED. Nadir attitude, image-axis heading, common height datum and actual mosaic contributor weights are assumptions. Identifiability does not prove directional calibration.",
            ),
            (
                "Red line and seams",
                "Old red jump ~630,821 candidate units becomes ~0.0026-0.0035 with BRDF alone. Hard A/B camera assignments introduce large factor jumps elsewhere; simulated blended kernels are smoother.",
            ),
            (
                "Readiness",
                "BRDF-only candidates are useful experimental outputs. Combined products still inherit separate topographic extremes. Production readiness and verified sensor interchangeability are not established.",
            ),
        ],
        findings=[
            "Source imagery, previous investigations, official libraries and NEON numerical behavior are preserved. No coefficient, kernel, rank limit, prediction guard or correction factor was manually adjusted to obtain these images."
        ],
    )
    page(
        "The actual acquisition sequence is recovered",
        "The matched photo tags span 19:42:38-20:03:47 on 15 August 2023. Acquisition order reveals a near north-south lawnmower trajectory rather than a set of unrelated cameras.",
        1,
        findings=[
            f"Median image spacing is {flight['spacing']['quantiles'][4]:.2f} m and median inter-position speed {flight['speed_m_s']['quantiles'][4]:.2f} m/s. Each of the 565 positions has ten band-camera records. Timestamp order is unique at position level.",
            "Legs are separated by sign changes of smoothed northing travel; turn candidates exceed 30 degrees from the north-south axis. These are reproducible geometric labels, not recovered autopilot flight-line IDs. Camera rotations are orthogonal with determinant near one, but their world/camera axis conventions remain unresolved.",
        ],
    )
    page(
        "Horizontal CRS is resolved; vertical datum is still conditional",
        "The original camera CSV header says EPSG:5070. The associated processing report explicitly says NAD83 / UTM zone 13N (EPSG:26913) for both the project and DEM. Its original bytes are retained.",
        2,
        findings=[
            f"Literal EPSG:26913 interpretation places the mean at {flight['camera_center_lonlat_26913'][1]:.5f} N, {abs(flight['camera_center_lonlat_26913'][0]):.5f} W, inside Goldhill and its field polygons. Literal EPSG:5070 gives 63.68 N, 88.10 W and misses the scene by at least {flight['minimum_wrong_CRS_distance_to_scene_m'] / 1000:,.0f} km.",
            "Both rasters and the candidate camera XY use metres. Z is 2,834-2,843 m and local camera-to-surface height is 126-151 m; the report quotes 123 m flying altitude. A common vertical datum is plausible but not certified. Explicit +/-30 m height cases test, rather than conceal, this unresolved assumption. All ten report calibration rows are recovered: fitted focal lengths 1,445.91-1,453.93 pixels, principal-point offsets and distortion coefficients. Their binding to each PhotoID and exact distorted footprint remains unverified, so the main rectangles are explicitly nominal approximations.",
        ],
    )
    page(
        "Nadir rays are physically computed and explicitly labeled",
        "For each ground point, H is camera Z minus local surface Z and zenith is atan2(horizontal distance,H). Cameras at or below that ground height are excluded.",
        3,
        findings=[
            "The camera-to-ground vector is reversed to obtain the package to-sensor azimuth. Bearings are clockwise from grid north and rotated by -0.318406 degrees to true north; an independent geodesic test checks the sign. Corner variation is only about +/-0.0012 degrees. At nadir azimuth is defined as zero, where the validated kernel is azimuth-invariant.",
            "A and B both use rectangular footprint eligibility. A minimizes horizontal distance; B minimizes the maximum normalized across/along image coordinate. Neither uses brightness, PFT labels, the red-line image or corrected-output appearance to choose a camera.",
        ],
    )
    page(
        "The kernel equations and solar calculation remain shared",
        "RossThick and reciprocal LiDenseR are evaluated by the existing package functions with b/r=10, h/b=2 and scene solar zenith. No separate drone BRDF implementation is introduced.",
        4,
        findings=[
            "Inherited spatial solar azimuth and scene-mean solar zenith are retained. Camera acquisition times reconstruct the path but do not replace mosaic solar fields with unverified contributor times. The reference is unchanged: solar zenith 45 degrees, nadir view and relative azimuth zero.",
            "The kernel maps and inferred camera IDs reveal artificial tessellation. A valid geometric ray to a potential camera is still not proof that its image supplied that mosaic reflectance.",
        ],
    )
    page(
        "Overlap is reduced in kernel space, never by copying observations",
        "All physically eligible ideal-rectangle cameras are enumerated per native ground pixel. Native maps retain count, min/max/median zenith, circular azimuth diagnostics, kernel means and spreads.",
        5,
        findings=[
            f"The repaired source has 6,683,944 alpha-valid cells; 39 lack finite terrain, leaving {geometry['covered_pixels']:,} covered ground observations. No terrain gap is filled with an invented height. Median candidate count is 84, with range 4-221. All established polygon memberships remain available.",
            "C uniform uses equal candidate weights; C center uses exp(-2 centrality squared). Both average individual evaluated kernels, not view angles. Each mosaic value enters fitting only once. Weights are sensitivity assumptions, not recovered Metashape blending. A common position assignment is used across the ten bands; per-band mosaic contributors are not recovered. Circular means are descriptive and paired with resultant length; they are never fitted as a single mean ray.",
        ],
    )
    page(
        "Footprint and height choices affect the correction",
        "Six prespecified geometry cases and 24 conditional sampled fits retain an every-tenth native-pixel lattice. They do not create averaged source imagery or tune against classification scores.",
        6,
        findings=[
            "A +/-20% common footprint-size multiplier changes candidate populations substantially, even when the most central camera is unchanged. Rotating the image axes by 90 degrees changes 42.7% of B assignments. A -30 m camera-height offset leaves about 0.02% of sampled points outside all footprints.",
            "All 24 sampled models pass current numerical guards, yet C uniform reference red predictions range about 0.051-0.062 across footprint cases. Numerical acceptance therefore cannot resolve the mosaic-contributor uncertainty. Native main experiments are not substituted with these sampled fits.",
        ],
    )
    page(
        "The assumed directional model is identifiable",
        "Main global designs reach stable numerical rank 3, compared with rank 1 for the zero-view placeholder design. The estimator and acceptance thresholds are unchanged.",
        7,
        findings=[
            "Global condition numbers are approximately A 105, B 98, C uniform 182 and C center 135. Algebraic rank, stable rank, singular values, kernel covariance and 128-row spatial diagnostics are retained separately. All eight main fits support ten bands under the isolated hypothesis.",
            "These are spatial regressions of heterogeneous mosaic reflectance against inferred geometry. Repeated nearby pixels are not independent angular observations of a common target. Land-cover/topographic spatial structure can be confounded with the geometric pattern; effective independent sample size remains explicitly unestimated.",
        ],
    )
    page(
        "650 nm: the historical boundary no longer explodes",
        "The exact historical P165 ROI and red boundary are retained. Raw, topographic-only, historical and experimental imagery use identical map extents and display bounds.",
        8,
        findings=[
            f"The median fixed-edge red jump is raw {metrics['clean_raw']['fixed_boundary']['650']['jump']['quantiles'][4]:.6f}, historical {metrics['historical_BRDF']['fixed_boundary']['650']['jump']['quantiles'][4]:,.2f}, A {metrics['A_brdf']['fixed_boundary']['650']['jump']['quantiles'][4]:.6f}, B {metrics['B_brdf']['fixed_boundary']['650']['jump']['quantiles'][4]:.6f}, C uniform {metrics['C_uniform_brdf']['fixed_boundary']['650']['jump']['quantiles'][4]:.6f}, C center {metrics['C_center_brdf']['fixed_boundary']['650']['jump']['quantiles'][4]:.6f}.",
            "All 2,936 fixed native edges remain evaluable in every new output. The old pole is removed in these explicit experimental products; that observation does not establish general seam-free or physically calibrated correction.",
        ],
    )
    page(
        "717 nm: another historical failure returns to the raw-scale range",
        "The severe historical red-edge amplification is absent in the reconstructed BRDF-only products. This is an actual calculation result, not a model rejection presented as a corrected image.",
        9,
        findings=[
            "Full native 717 nm maxima are raw 0.417, historical 29,381, A BRDF 0.409, B BRDF 0.420, C uniform 0.495 and C center 0.460 candidate fractional units. BRDF-only values are not clipped to a reflectance range.",
            "Only A combined is shown in the matched map panel for compactness; all four combined GeoTIFFs, per-band model diagnostics and native summaries are retained. Their remaining topographic extremes require separate treatment.",
        ],
    )
    page(
        "Resolved predictions replace the historical zero crossing",
        "Observed-geometry predictions remain positive and above the unchanged roundoff/OLS-uncertainty limits, with no identity fallback or factor cap.",
        10,
        findings=[
            "At the original row 921, columns 980/981 pair, raw red difference is 0.001117; experimental BRDF-only differences range about 0.00089-0.00126. The historical 674,321-unit jump is absent. Predicted reference/observed ratios, rather than arbitrary coefficients, generate the corrections.",
            "The full native red factor range is approximately A 0.50-3.15, B 0.53-2.78; complete band/branch quantiles are in the model records. The OLS uncertainty rule is a computational safeguard, not a field confidence interval that accounts for spatial confounding.",
        ],
    )
    page(
        "Hard camera assignment introduces new discontinuities",
        "The old red line is not simply relocated to one new line; camera assignment creates many tessellation boundaries. These must be evaluated separately from the historical pole.",
        11,
        findings=[
            "At native horizontal assignment edges, the 99th percentile red factor jump is A 0.498, B 0.589, C uniform 0.0567 and C center 0.0265. The corresponding factor-induced signal component is about 0.0199, 0.0275, 0.00293 and 0.00114. C uses candidate-count edges, not an invented single-camera seamline.",
            "C center is the smoother geometric sensitivity candidate under this declared seam diagnostic. It is not a verified Metashape contributor model. Smoothness and PFT accuracy cannot certify its weights. A remains the transparent nearest-camera baseline; neither hard assignment is recommended as artifact-free production geometry.",
        ],
    )
    page(
        "The fixed vegetation exemplar is spectrally coherent again",
        "The boundary-crossing aspen polygon is the same preselected GlobalID as in the earlier artifact investigation. Labels and sampled memberships are unchanged.",
        12,
        findings=[
            "Raw and new BRDF-only spectra retain the vegetation red-edge rise and NIR/red structure; historical BRDF greatly corrupts the red and 717 nm components. Median within-polygon spectral angle is raw 2.495 degrees, A 2.427, B 2.441, C uniform 2.426 and C center 2.402.",
            "Median within-polygon variance is raw 0.000625, A 0.000445, B 0.000460, C uniform 0.000730 and C center 0.000611. Smaller variance or angle alone does not establish physical improvement; a band-dominated historical spectrum misleadingly has an even smaller angle. Complete CV, red-edge reversal, NIR/red and class-separation records are retained.",
        ],
    )
    page(
        "Ecological information is retained, with uncertain modest gains",
        "The package identifiability and separability functions are run on exactly the established 157 identities and 144,406 polygon-pixel memberships. No memberships are changed to favor a branch.",
        13,
        findings=[
            "A balanced-accuracy gain over raw is +2.98 points, paired 95% interval [-0.26,+6.66]; B +2.63 [-0.26,+6.14]; C uniform +0.31 [-6.43,+6.99]; C center +2.82 [-4.12,+9.59]. All include zero. Intervals bootstrap fixed out-of-fold predictions by class and identity; training/site-year and nearby-polygon dependence are not covered.",
            "Class counts remain 98 Evergreen, 29 Woody shrub, 25 Herbaceous and 5 Deciduous. Within-branch permutation/Holm separation tables are descriptive evidence, not tests that a correction beats raw. Footprints, weights and models were defined before using held-out scores.",
        ],
    )
    page(
        "Combined correction remains scientifically problematic",
        "The existing topographic calculation is executed through the same shared functions before BRDF fitting and application. Passing BRDF guards does not repair the separate topographic instability.",
        14,
        findings=[
            "Maximum 717 nm candidate reflectance remains about 50-70 in the combined products, compared with less than 0.50 for the BRDF-only candidates. These outcomes are preserved as experimental failure evidence, without clipping, masking the extremes or disabling requested branches.",
            "Combined balanced accuracy is A 67.30%, B 68.30%, C uniform 61.46% and C center 61.71%. These mixed outcomes and implausible extremes rule out a claim of validated combined production correction.",
        ],
    )
    page(
        "NEON and the production scientific contracts are unchanged",
        "Only an opt-in geometry module and isolated experiment scripts are added. The existing shared kernel, radiometry, fit/application and library gate implementations are untouched in this task.",
        rows=[
            (
                "NEON control",
                "The real 120 x 3,000 window and ten selected native channels are rerun in BRDF-only and combined modes. Both support ten bands; corrected arrays and masks exactly match the saved P172 controls (maximum difference zero). Actual ENVI serialization and library-header acceptance pass.",
            ),
            (
                "Regression checks",
                "163 focused tests pass, with zero failures, errors or skips. Nine new tests cover independent ray directions, north conversion, invalid heights, rotated footprint/assignment, weighted kernels, chunk invariance and an isolated shared-fitter control that retains production calibration rejection.",
            ),
            (
                "Production boundary",
                "Goldhill model radiometry and experimental GeoTIFF tags remain HYPOTHETICAL_UNVERIFIED / EXPERIMENTAL_NOT_VALIDATED. No approved spectral library is generated. Production require_valid still rejects the conditional decoder.",
            ),
            (
                "Kernel input adapter",
                "A/B use the normal shared angular design builder. C supplies precomputed individual-kernel mixtures through an isolated design-input adapter to the exact same estimator and application functions. The full design is fingerprinted in model identity. Placeholder angles in C bookkeeping are explicitly not the kernel inputs.",
            ),
            (
                "Core scientific identity",
                "P172 corrections.py source hash is unchanged, as are all protected earlier investigation files and source inputs. Existing parameters, model math/policy versions, reference geometry and numerical gates are unchanged.",
            ),
        ],
        section="Verification",
    )
    page(
        "A concrete small source-data request can resolve the next step",
        "The checked live package metadata contain reports, camera metadata, GCP/area records and an empty SkyPhotos collection. The recorded relative RawData/M300/SD1 location is not found. No original overlapping Goldhill photograph bytes were accessible in these checked locations.",
        rows=[
            (
                "Candidate subset",
                "Four camera positions are selected from the intersection of the four fixed diagnostic-point footprints using only geometric conditioning, not reflectance or PFT scores. Their 40 band-photo identities, timestamps and relative original paths are listed in minimum_source_subset.csv.",
            ),
            (
                "Why four views",
                "The existing three-parameter fit requires at least four observations for residual uncertainty. The selected conditional four-ray designs have worst point condition about52, but are only a search seed until real pose/intrinsic/visibility conventions are verified.",
            ),
            (
                "What to retrieve",
                "Original calibrated band images or source-linked patches around the same fixed ground targets, full pose/intrinsic/distortion metadata with source-sensor binding, horizontal/vertical/time conventions, and radiometric processing/export evidence. Calibration panel/reference QA and independent validation targets are still needed.",
            ),
            (
                "What to do with them",
                "Register the same targets across the real overlapping observations, extract distinct measured reflectance values, verify actual view rays, then fit/validate the shared model while accounting for target-specific reflectance. The finished mosaic cannot supply those repeated measurements.",
            ),
            (
                "Preferred current experiment",
                "Retain A as a transparent baseline and C center as the smoother simulated-blending sensitivity result. Neither is selected by classification score or approved for production. Obtain actual contributor/blend evidence or repeated observations before scientific promotion.",
            ),
        ],
        section="Practical next step",
    )
    page(
        "Reproducibility and deliverables",
        "Native geometry, eight corrected images and large arrays are outside the repository in the dated scratch directory. Compact scripts, models, tables, figures and hashes are retained with this report.",
        rows=[
            (
                "Run order",
                "reconstruct.py -> fit_experiments.py -> sensitivity.py -> sensitivity_fits.py -> evaluate.py -> assignment_boundaries.py -> diagnostic_maps.py -> source_subset.py -> figures.py -> write_report.py -> make_pdf.py -> verify.py. The separate neon_control.py reruns the supported real input.",
            ),
            (
                "Geometry scaling",
                "3 workers, each at most1,024 ground points x565cameras; full native geometry completed in about143seconds. Input geometry arrays are bounded per chunk; no pixel-scale bulk Parquet cache is created. The existing shared fitter remains scene-in-memory.",
            ),
            (
                "Outputs",
                "Full geometry/candidate maps, A/B angle/relative/kernel/prediction/factor GeoTIFFs, four BRDF-only and four combined experimental ten-band GeoTIFFs. Every product is tagged experimental; all original/official sources remain unchanged.",
            ),
            (
                "Experimental assumptions",
                "Ideal nadir optical axis; height-axis follows local flight heading; reported pinhole intrinsics without distortion; conditional common vertical datum; approximate constant grid-to-true rotation; unknown actual blend/occlusion. Sensitivity experiments keep these choices visible.",
            ),
            (
                "Acceptance and remaining work",
                "Numerical reconstruction and correction succeeded. Verified physical calibration, genuine contributors or repeated observations, assignment-seam validation and separate topographic stabilization remain necessary before production approval.",
            ),
        ],
        findings=[
            "Source identities, exact numerical control comparisons, test logs, artifact inventories and final rendered PDF QA are in verification.json, artifact_checksums.json and pdf_visual_qa.json. No release, datastore upload, library regeneration or calibration promotion occurred."
        ],
        section="Reproducibility",
    )
    (HERE / "report_pages.json").write_text(json.dumps(pages, indent=2) + "\n")
    lines = [
        "# " + TITLE,
        "",
        "4 November 2026. **EXPERIMENTAL: calibration and mosaic contributors unverified.**",
        "",
    ]
    for i, p in enumerate(pages, 1):
        lines += ["## " + str(i) + ". " + p["title"], "", p["intro"], ""]
        if p["rows"]:
            lines += (
                ["| Question | Measured outcome |", "| --- | --- |"]
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
        "## Detailed records",
        "",
        "- [Flight/CRS and vertical evidence](flight_and_crs.json)",
        "- [Geometry and source coverage](geometry_summary.json)",
        "- [All eight main fit/application outcomes](experiment_status.json)",
        "- [Rank and spatial conditioning](design_support.json)",
        "- [Native seam diagnostics](assignment_boundary_metrics.json)",
        "- [Exact evaluation contract](evaluation_contract.json)",
        "- [Per-polygon spectra and variability](polygon_summaries.csv)",
        "- [Within-branch class separability](separability_pairs.csv)",
        "- [Paired ecological uncertainty](paired_gain.json)",
        "- [Minimal source subset](minimum_source_subset.csv)",
        "- [Verification](verification.json)",
        "",
    ]
    text = "\n".join(lines)
    (HERE / "report.md").write_text(text)
    prefix = "../../provenance/goldhill-viewing-geometry/2026-11-04/"
    (ROOT / "docs/dev/goldhill-viewing-geometry-experiment.md").write_text(
        re.sub(
            r"\]\((?!https?://)([^)]+)\)",
            lambda m: "](" + prefix + m.group(1) + ")",
            text,
        )
    )
    summary = dict(
        status="IMPLEMENTED_EXPERIMENTAL_NATIVE_CORRECTIONS_PRODUCTION_UNVERIFIED",
        calibration="HYPOTHETICAL_UNVERIFIED",
        geometry="INFERRED_NADIR_NOT_VERIFIED_CONTRIBUTORS",
        native_corrected_images=8,
        main_fits_all_numerical_guards_pass=True,
        source_pixels=6683905,
        stable_rank=3,
        production_approved=False,
        old_red_line_pole_absent_in_experimental_BRDF_only=True,
        new_hard_assignment_seams_detected=True,
        combined_topographic_instability_remains=True,
        BRDF_disabled=False,
        kernel_math_changed=False,
        PFT_tuned_parameters=False,
        classes_and_memberships_unchanged=True,
        pages=len(pages),
        figures=len(figures),
        classification=scores,
        paired_gain=gains,
        minimum_source_subset=source,
    )
    (HERE / "scientific_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(len(pages), "report pages prepared")


if __name__ == "__main__":
    main()
