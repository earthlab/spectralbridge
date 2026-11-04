"""Figure-heavy scientific comparison; display limits never modify analytical values."""

import json
from pathlib import Path
import sys
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text
from readability import readable
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import WAVES, WORK, ROOT, LEGACY, load_module  # noqa:E402
from spectralbridge import corrections as c  # noqa:E402

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 160,
        "savefig.dpi": 180,
        "svg.fonttype": "none",
        "axes.titleweight": "bold",
    }
)
COLORS = ["#5a7080", "#22877c", "#b44b3c", "#d98744", "#687cb0"]
NAMES = [
    "raw_historical",
    "raw_clean",
    "A_historical_BRDF",
    "B_clean_historical_BRDF",
    "topographic_only",
]
LABELS = [
    "Historical raw",
    "Clean raw",
    "A historical BRDF",
    "B clean + historical BRDF",
    "Topo-only diagnostic",
]
manifest = []


def read(n):
    return json.loads((HERE / n).read_text())


def save(
    fig,
    name,
    title,
    caption,
    subtitle="Conditional Goldhill DN/32768 hypothesis - calibration unverified",
):
    fig.suptitle(title + "\n" + subtitle, fontsize=14, weight="bold")
    for text in fig.findobj(Text):
        text.set_text(readable(text.get_text()))
    title, caption = readable(title), readable(caption)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(HERE / (name + ".png"), bbox_inches="tight")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(
            id=name, png=name + ".png", svg=name + ".svg", title=title, caption=caption
        )
    )


def main():
    d = np.load(HERE / "display_arrays.npz")
    m = read("artifact_metrics.json")
    metric = {x["branch"]: x for x in m}
    sel = read("fixed_regions.json")["selection"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, n in zip(axes[:2], NAMES[:2]):
        im = ax.imshow(d[n + "_red"], vmin=0, vmax=0.3, cmap="viridis")
        fig.colorbar(im, ax=ax, shrink=0.65)
        ax.set_title(n)
        ax.axis("off")
    axes[2].bar(
        ["Historical raw", "Clean raw"],
        [metric[n]["red_cross_boundary_difference"]["quantiles"][4] for n in NAMES[:2]],
        color=COLORS[:2],
    )
    axes[2].set(
        ylabel="Median absolute650nm jump",
        title="At the fixed historical BRDF boundary",
    )
    save(
        fig,
        "figure01_sources",
        "The source repair fixes preprocessing, not the BRDF model",
        "Identical0-0.3display limits; native background remains visible in historical support. Median raw boundary jumps are about0.003candidate units in both sources. No corrected output was used to choose the boundary.",
    )
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.4))
    keys = [
        "historical_native",
        "source_valid",
        "legacy_estimated_no_background_mix",
        "D_revised_prefit",
    ]
    titles = [
        "Historical finite support",
        "Clean source footprint",
        "No estimated legacy mixing",
        "Clean prefit numerical geometry",
    ]
    for ax, key, title in zip(axes, keys, titles):
        ax.imshow(d["mask_" + key], cmap="Blues", vmin=0, vmax=1)
        ax.set_title(title)
        ax.axis("off")
    save(
        fig,
        "figure02_masks",
        "Filtering is a sequence of explicit eligibility decisions",
        "Every sixth cell, same grid/north-up. Legacy mixing is estimated by bilinear source-alpha weights, not a brightness cutoff. Numerical geometry eligibility does not establish genuine views: actual Goldhill directional support remains absent.",
    )
    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.axis("off")
    statuses = read("factorial_status.json")
    rows = []
    for r in statuses:
        rows.append(
            [
                r["branch"],
                r["status"],
                f"{r.get('prefit_pixels', 0):,}" if r["branch"] != "F" else "Unknown",
                "Diagnostic only" if r["image_created"] else "No image",
            ]
        )
    table = ax.table(
        cellText=rows,
        colLabels=["Branch", "Scientific status", "Prefit pixels", "BRDF raster"],
        cellLoc="left",
        loc="center",
        colWidths=[0.08, 0.55, 0.15, 0.20],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    for (i, j), cell in table.get_celld().items():
        cell.set_facecolor(
            "#1e6976" if i == 0 else "#fff0e9" if i in [1, 2] else "#edf1f4"
        )
        cell.set_text_props(color="white" if i == 0 else "#243746")
    save(
        fig,
        "figure03_factorial",
        "Rejection is not an artifact-free corrected image",
        "A/Bare pinned historical replays. C/Duse revised prefit populations and historical equations; stable rank1prevents application. Euses current shared mathematics and gates. Fhas no applicable independent directional information; no coefficients or image are invented.",
    )
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.5))
    names = [
        "raw_historical",
        "raw_clean",
        "topographic_only",
        "A_historical_BRDF",
        "B_clean_historical_BRDF",
        None,
        None,
        None,
    ]
    titles = [
        "Historical source",
        "Clean source",
        "Topo-only diagnostic",
        "A historical BRDF",
        "B clean + historical BRDF",
        "C revised/historical",
        "D revised/clean",
        "E current shared",
    ]
    for ax, n, title in zip(axes.flat, names, titles):
        if n:
            im = ax.imshow(
                d[n + "_zoom_red"],
                vmin=0,
                vmax=0.3,
                cmap="viridis",
                interpolation="none",
            )
        else:
            ax.set_facecolor("#e8edf0")
            ax.text(
                0.5,
                0.5,
                "UNSUPPORTED\nNo corrected image",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color="#5b6d77",
            )
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.subplots_adjust(top=0.83, right=0.9, hspace=0.2)
    cax = fig.add_axes([0.93, 0.18, 0.012, 0.54])
    fig.colorbar(im, cax=cax, label="Candidate650nm-equivalent units; display0-0.3")
    fig.suptitle(
        "The stripe returns after the same historical BRDF operation\nConditional Goldhill DN/32768 hypothesis - calibration unverified",
        fontsize=14,
        weight="bold",
    )
    fig.savefig(HERE / "figure04_fixed_roi.png", bbox_inches="tight")
    fig.savefig(HERE / "figure04_fixed_roi.svg", bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(
            id="figure04_fixed_roi",
            png="figure04_fixed_roi.png",
            svg="figure04_fixed_roi.svg",
            title="Fixed native red-boundary ROI",
            caption="P165ROI rows573:974,columns812:1313,0.1m,north-up. Identical display bounds saturate enormous diagnostic values; native ranges are reported separately. Gray panels indicate absent/unsupported products, not zero reflectance or successful artifact removal.",
        )
    )
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    x = np.arange(840, 1120)
    for n, label, color in zip(NAMES, LABELS, COLORS):
        ax = axes[1] if n.startswith(("A_", "B_")) else axes[0]
        ax.plot(x, d[n + "_transect"], label=label, color=color)
    for ax in axes:
        ax.axvline(980.5, color="black", ls="--", lw=0.8)
        ax.legend(fontsize=8)
        ax.set_ylabel("650nm-equivalent candidate units")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Native column at fixed row921")
    axes[0].set_title("Uncorrected/topographic signals")
    axes[1].set_title("Historical BRDF signals; logarithmic axis")
    save(
        fig,
        "figure05_transect",
        "A0.1m boundary acquires an enormous algorithmic jump",
        "At columns980/981the clean raw jump is0.001117; the clean-source historical BRDF jump is674,321candidate-equivalent units. The same fixed transect and reference pixels are used for every branch; no smoothing or factor clipping.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, w in zip(axes[:2], [650, 717]):
        a = d[f"prediction_{w}_zoom"]
        im = ax.imshow(a, cmap="coolwarm", vmin=-0.04, vmax=0.04)
        fig.colorbar(im, ax=ax, shrink=0.7)
        ax.set_title(f"Historical{w}nm predicted denominator")
        ax.axis("off")
    for n, color in [
        ("A_historical_BRDF", COLORS[2]),
        ("B_clean_historical_BRDF", COLORS[3]),
    ]:
        a = d[n + "_factor"]
        a = a[np.isfinite(a) & (a > 0)]
        axes[2].hist(
            a, bins=np.geomspace(0.1, 2e7, 100), histtype="step", label=n, color=color
        )
    axes[2].set(
        xscale="log",
        yscale="log",
        xlabel="Reconstructed red factor",
        ylabel="Display-sampled pixels",
    )
    axes[2].legend(fontsize=7)
    save(
        fig,
        "figure06_predictions",
        "The historical prediction crosses zero; the old guard switches regimes",
        "The predicted red denominator is0outside and0.0078125inside at the fixed adjacent pair; reference prediction91,740.234375produces factor11,742,750. Plotted denominator limits and sampled factor histograms do not alter the full-scene analytical summaries.",
    )
    old = load_module("p172_fig_historical", LEGACY)
    phi = np.deg2rad(np.linspace(0, 360, 721))[None, :]
    solar = np.full_like(phi, np.deg2rad(27.76494))
    zero = np.zeros_like(phi)
    oldk = old.calc_geom_kernel(
        phi, solar, zero, zero, kernel_type="LiDenseR", b_r=10, h_b=2
    )
    newk = c.calc_geom_kernel(
        phi, solar, zero, zero, kernel_type="LiDenseR", b_r=10, h_b=2
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    axes[0].plot(
        np.rad2deg(phi).ravel(), oldk.ravel(), label="Historical", color=COLORS[2]
    )
    axes[0].plot(
        np.rad2deg(phi).ravel(), newk.ravel(), label="Correct current", color=COLORS[1]
    )
    axes[0].set(
        xlabel="Absolute solar azimuth at nadir view(degrees)", ylabel="LiDenseR kernel"
    )
    axes[0].legend()
    axes[1].plot(
        np.rad2deg(phi).ravel(),
        (oldk - oldk.mean()).ravel(),
        color=COLORS[2],
        label="Historical",
    )
    axes[1].plot(
        np.rad2deg(phi).ravel(),
        (newk - newk.mean()).ravel(),
        color=COLORS[1],
        label="Current",
    )
    axes[1].set(
        xlabel="Absolute solar azimuth(degrees)",
        ylabel="Kernel minus its azimuthal mean",
        title="Nadir azimuth must not create angular information",
    )
    refs = json.loads(
        (
            ROOT
            / "provenance/brdf-mathematical-validation/2026-11-03/independent_reference_results.json"
        ).read_text()
    )
    axes[2].bar(
        ["RossThick", "LiDenseR", "LiSparseR"],
        [
            refs["errors"][k]["max_absolute_error_through_80_degrees"]
            for k in ["RossThick", "LiDenseR", "LiSparseReciprocal"]
        ],
        color=COLORS[:3],
    )
    axes[2].set(
        yscale="log",
        ylabel="Maximum absolute independent-reference error",
        title="Existing1220-case published-equation audit",
    )
    save(
        fig,
        "figure07_kernels",
        "Current kernels already satisfy the mathematical reference tests",
        "Current RossThick/LiDenseR equations are unchanged in this task. The earlier repair removed spurious nadir azimuth response; it cannot recover real observation directions. The fresh targeted suite reruns the independent reference fixtures, reciprocity and wrapping tests.",
    )
    audits = read("fitting_population_and_rank.json")
    E = read("E_after_brdf_model.json")
    N = read("neon_after_brdf_model.json")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    axes[0].bar(
        ["Historical red", "Revised clean red"],
        [
            audits["historical_old_stored"][4]["n"],
            audits["D_revised_historical_math"][4]["n"],
        ],
        color=[COLORS[2], COLORS[1]],
    )
    axes[0].set(
        yscale="log",
        ylabel="Fitting observations; log axis",
        title="Correct units repair eligibility, not rank",
    )
    for label, singular, color in [
        ("Goldhill current", E["validation"]["fits"][4]["singular_values"], COLORS[2]),
        ("NEON current", N["validation"]["fits"][4]["singular_values"], COLORS[1]),
    ]:
        axes[1].plot(
            [1, 2, 3],
            np.maximum(np.array(singular) / singular[0], 1e-18),
            "o-",
            label=label,
            color=color,
        )
    axes[1].axhline(np.sqrt(np.finfo(np.float32).eps), color="gray", ls="--")
    axes[1].set(
        yscale="log",
        xticks=[1, 2, 3],
        xlabel="Singular-value order",
        ylabel="Singular value / largest",
    )
    axes[1].legend(fontsize=8)
    axes[2].bar(["Goldhill", "NEON"], [1, 3], color=[COLORS[2], COLORS[1]])
    axes[2].set(
        ylim=(0, 3.5),
        ylabel="Stable angular dimensions",
        title="Three coefficients require three dimensions",
    )
    save(
        fig,
        "figure08_support",
        "Millions of pixels cannot replace missing angular dimensions",
        "Stable rank is tied to the existing precision condition limit1/sqrt(float32epsilon). Algebraic rank and singular values are also retained. Pixel counts are not an estimated independent sample size; spatial/effective sampling uncertainty remains explicit.",
    )
    geom = read("geometry_feasibility.json")
    rays = pd.read_csv(HERE / "conditional_camera_envelope.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    poses = pd.read_csv(
        ROOT
        / "provenance/goldhill-end-to-end/2026-11-03/camera_poses_with_photo_times.csv"
    ).drop_duplicates(["X", "Y", "Z"])
    axes[0].scatter(
        poses.X, poses.Y, s=8, color="#748c9d", label="565reported positions"
    )
    for record in geom["records"]:
        axes[0].scatter(
            record["x"], record["y"], marker="x", s=35, label=record["label"]
        )
    axes[0].set(
        xlabel="ReportedX",
        ylabel="ReportedY",
        title="CRS label unresolved; position numbers shown",
    )
    axes[0].legend(fontsize=7)
    for name, g in rays.groupby("point"):
        axes[1].hist(
            g.candidate_zenith_degrees,
            bins=np.arange(0, 31, 2),
            histtype="step",
            label=name,
        )
    axes[1].set(
        xlabel="Conditional line-of-sight zenith(degrees)",
        ylabel="Candidate cameras, not actual contributions",
    )
    axes[1].legend(fontsize=7)
    save(
        fig,
        "figure09_camera_uncertainty",
        "Camera records leave hundreds of possible contributors per point",
        "Positions are real records; the right-hand envelope assumes their numbers are26913and altitude shares the delivered surface datum, with an illustrative nadir diagonal-FOV cone. It is not recovered viewing geometry, true image coverage, a probability distribution or a per-pixel assignment.",
    )
    examples = geom["identifiability_examples"]["examples"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    labels = ["Shape assumption1", "Shape assumption2", "Shape assumption3"]
    for ax, key, title in zip(
        axes,
        ["observed_prediction", "reference_prediction", "factor"],
        [
            "Same observed prediction",
            "Different reference prediction",
            "Different normalization factor",
        ],
    ):
        ax.bar(labels, [x[key] for x in examples], color=COLORS[:3])
        ax.tick_params(axis="x", rotation=25)
        ax.set_title(title)
    save(
        fig,
        "figure10_nonidentifiability",
        "A reduced model needs external directional assumptions",
        "Synthetic algebra only, evaluated at the actual Goldhill nadir design. Each coefficient family predicts0.3at observed geometry but allows reference0.15,0.3or0.6. No example is a Goldhill fit or applied model; isotropic-only assumptions give identity, not an estimated BRDF correction.",
    )
    poly = pd.read_csv(HERE / "polygon_summaries.csv")
    identity = sel["exemplar_GlobalID"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    p = poly[poly.GlobalID == identity]
    for n, label, color in zip(NAMES, LABELS, COLORS):
        row = p[p.branch == n].iloc[0]
        s = row[[f"b{i + 1}" for i in range(10)]].to_numpy(float)
        axes[0].plot(WAVES, s, "o-", label=label, color=color)
        axes[1].plot(WAVES, s / np.linalg.norm(s), "o-", color=color, label=label)
    axes[0].set(
        yscale="log",
        xlabel="Wavelength(nm)",
        ylabel="Polygon mean, candidate-equivalent units",
    )
    axes[0].legend(fontsize=7)
    axes[1].set(xlabel="Wavelength(nm)", ylabel="Unit-length spectral shape")
    save(
        fig,
        "figure11_spectra",
        "A known boundary-crossing polygon acquires a distorted spectrum",
        "The pre-existing Deciduous exemplar is selected by P165identity, not by new branch quality. Histories are reexpressed through the documented per-band inverse encoding; calibration remains hypothetical. Unsupported revised BRDF spectra are absent, not replaced with raw values.",
    )
    score = {
        r["branch"]: r["balanced_accuracy"] for r in read("classification_summary.json")
    }
    gain = {r["branch"]: r for r in read("paired_gain.json")}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    axes[0].bar(LABELS, [score[n] * 100 for n in NAMES], color=COLORS)
    axes[0].set(ylim=(0, 100), ylabel="Balanced accuracy(%)")
    axes[0].tick_params(axis="x", rotation=40)
    for i, n in enumerate(NAMES):
        x = gain[n]
        axes[1].errorbar(
            x["difference"] * 100,
            i,
            xerr=np.array([[x["difference"] - x["low"]], [x["high"] - x["difference"]]])
            * 100,
            fmt="o",
            color=COLORS[i],
        )
    axes[1].set_yticks(range(5), LABELS)
    axes[1].axvline(0, color="gray", ls="--")
    axes[1].set_xlabel("Paired accuracy gain over clean raw(points)")
    med = poly.groupby("branch").median_band_cv.median().reindex(NAMES)
    axes[2].bar(LABELS, med, color=COLORS)
    axes[2].tick_params(axis="x", rotation=40)
    axes[2].set_ylabel("Median within-polygon band CV")
    save(
        fig,
        "figure12_pft",
        "Historical BRDF does not improve this matched identification test",
        "157polygon identities, four recorded classes, identical3fold splits, training-only scaling,C=1;499permutations for separate spectral-separability tables. Intervals bootstrap fixed OOF predictions by class/identity. C/D/E/Fhave no supported image and no quality score; topographic score is unapproved diagnostic evidence.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    before = read("neon_before_brdf_model.json")
    after = read("neon_after_brdf_model.json")
    waves = after["wavelengths_nm"]
    diff = []
    for branch in ["brdf", "combined"]:
        a = np.load(WORK / f"neon_before_{branch}.npy", mmap_mode="r")
        b = np.load(WORK / f"neon_after_{branch}.npy", mmap_mode="r")
        diff.append(float(np.nanmax(abs(a - b))))
    axes[0].bar(["BRDF-only", "Combined"], diff, color=COLORS[:2])
    axes[0].set(
        ylim=(0, 1e-7),
        ylabel="Maximum before/after difference",
        title="Exactly zero on actual control values",
    )
    axes[1].plot(
        waves,
        [r["condition_number"] for r in after["validation"]["fits"]],
        "o-",
        color=COLORS[1],
    )
    axes[1].set(
        xlabel="Selected native NEON wavelength(nm)", ylabel="Design condition number"
    )
    for label, model, color in [
        ("Before", before, COLORS[2]),
        ("After", after, COLORS[1]),
    ]:
        axes[2].plot(
            waves,
            [r["factor_quantiles"][2] for r in model["validation"]["fits"]],
            "o-",
            label=label,
            color=color,
        )
    axes[2].set(
        xlabel="Native NEON wavelength(nm)",
        ylabel="Median supported normalization factor",
    )
    axes[2].legend()
    save(
        fig,
        "figure13_neon",
        "Supported NEON correction is preserved by the reliability changes",
        "Actual2021R10Cdirectional data, fixed120x3000native window, ten nearest native channels; both BRDF-only and combined models support10/10bands. Values and masks are identical before/after. This bounded regression control is not a MicaSense calibration transfer or full-flightline accuracy claim.",
        subtitle="Actual NEON H5 calibration and observation geometry - bounded shared-function control",
    )
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    boxes = [
        (
            0.02,
            0.70,
            0.3,
            0.20,
            "DRONE INPUTS\nCalibration hypothesis, no contributor geometry\nGoldhill remains unsupported",
            "#fff0e9",
        ),
        (
            0.68,
            0.70,
            0.3,
            0.20,
            "NEON INPUTS\nDocumented H5 decoding, real view angles\nThis control has rank3",
            "#e5f2ee",
        ),
        (
            0.22,
            0.37,
            0.56,
            0.21,
            "SHARED SCIENTIFIC CORE\nAffine decoding -> SCS+C -> Ross-Li fit\nFootprint/quality/rank/prediction guards -> reference/observed ratio",
            "#eaf0f5",
        ),
        (
            0.02,
            0.04,
            0.40,
            0.18,
            "GOLDHILL OUTPUT STATUS\nRaw ENVI/index executed\nPhysical correction/translation/library blocked",
            "#fff0e9",
        ),
        (
            0.58,
            0.04,
            0.40,
            0.18,
            "SUPPORTED CONTROL STATUS\nBRDF-only + combined executed\nNo change to corrected NEON values",
            "#e5f2ee",
        ),
    ]
    for x, y, w, h, text, color in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=.015",
                facecolor=color,
                edgecolor="#5b7c8c",
            )
        )
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=11)
    for start, end in [
        ((0.17, 0.69), (0.4, 0.60)),
        ((0.83, 0.69), (0.6, 0.60)),
        ((0.4, 0.36), (0.22, 0.23)),
        ((0.6, 0.36), (0.78, 0.23)),
    ]:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(arrowstyle="->", color="#315f71", lw=1.5),
        )
    save(
        fig,
        "figure14_shared_path",
        "One mathematical core, different evidence prerequisites",
        "Both pipelines retain BRDF requests and the same kernels, reference, physical decoder and ratio direction. Source acquisition/calibration/geometry remain platform-specific. A missing prerequisite is an explicit scientific block, not a successful uncorrected substitute.",
    )
    (HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(len(manifest), "figure pairs generated")


if __name__ == "__main__":
    main()
