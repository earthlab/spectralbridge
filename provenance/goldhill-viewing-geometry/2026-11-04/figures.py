"""Figure-led fixed-region experiment; display limits never alter numerical tests."""

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P172 = ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"
sys.path.insert(0, str(P172))
from common import SOURCE, WAVES  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "svg.fonttype": "none",
        "savefig.dpi": 180,
    }
)
COLORS = ["#486679", "#b24e3b", "#338a7c", "#568fb4", "#a77e3e", "#936c9c"]
BRANCHES = [
    "clean_raw",
    "historical_BRDF",
    "A_brdf",
    "B_brdf",
    "C_uniform_brdf",
    "C_center_brdf",
]
LABELS = [
    "Clean raw",
    "Historical BRDF",
    "A nearest",
    "B central",
    "C uniform kernels",
    "C central kernels",
]
manifest = []


def read(n):
    return json.loads((HERE / n).read_text())


def save(fig, name, title, caption):
    fig.suptitle(
        title
        + "\nExperimental nadir geometry; calibration and mosaic contributors unverified",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90), h_pad=2.0)
    fig.savefig(HERE / (name + ".png"), bbox_inches="tight")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(png=name + ".png", svg=name + ".svg", title=title, caption=caption)
    )


def main():
    cameras = pd.read_csv(HERE / "acquisition_path.csv")
    maps = np.load(WORK / "geometry_native.npy", mmap_mode="r")
    roi = np.load(WORK / "roi_displays.npz")
    tr = np.load(WORK / "transects.npz")
    fixed = read("evaluation_contract.json")["fixed_regions"]
    y0, y1, x0, x1 = fixed["roi_native_indices"]
    start, end = fixed["main_transect_columns"]
    left = fixed["main_transition_left_column"]
    window = np.s_[y0:y1, x0:x1]
    with rasterio.open(SOURCE) as src:
        bounds = src.bounds
        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        alpha = src.dataset_mask()[::6, ::6] > 0
        raw = np.where(alpha, src.read(5)[::6, ::6] * 0.0001999969482421875, np.nan)
        transform = src.transform
    polys = gpd.read_file(
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
    ).to_crs(26913)
    roi_extent = [
        transform.c + x0 * transform.a,
        transform.c + x1 * transform.a,
        transform.f + y1 * transform.e,
        transform.f + y0 * transform.e,
    ]
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.imshow(raw, extent=extent, vmin=0, vmax=0.3, cmap="gray")
    ax.plot(cameras.X, cameras.Y, color="#25495a", lw=0.65, alpha=0.8)
    points = ax.scatter(
        cameras.X, cameras.Y, c=cameras.order, s=13, cmap="viridis", zorder=3
    )
    polys.boundary.plot(ax=ax, color="#f0bc46", lw=0.6, alpha=0.8)
    ax.add_patch(
        Rectangle(
            (roi_extent[0], roi_extent[2]),
            roi_extent[1] - roi_extent[0],
            roi_extent[3] - roi_extent[2],
            fill=False,
            edgecolor="#e14545",
            lw=2,
            label="Fixed historical ROI",
        )
    )
    turn = cameras[cameras.turn_candidate]
    ax.scatter(turn.X, turn.Y, marker="x", c="#b8463c", s=25, label="Turn candidates")
    ax.set_xlim(extent[:2])
    ax.set_ylim(extent[2:])
    ax.set_aspect("equal")
    ax.set_xlabel("Easting, NAD83 / UTM 13N (m)")
    ax.set_ylabel("Northing (m)")
    ax.legend(loc="lower left", fontsize=9)
    fig.colorbar(points, ax=ax, label="Recovered acquisition order")
    ax.annotate(
        "START",
        (cameras.X.iloc[0], cameras.Y.iloc[0]),
        xytext=(8, 5),
        textcoords="offset points",
        weight="bold",
    )
    ax.annotate(
        "END",
        (cameras.X.iloc[-1], cameras.Y.iloc[-1]),
        xytext=(8, 5),
        textcoords="offset points",
        weight="bold",
    )
    save(
        fig,
        "figure01_path",
        "565 recovered positions reconstruct a consistent lawnmower flight",
        "All 5,650 band-camera records join to 565 unique timestamped positions. Yellow outlines are existing researcher polygons; the red rectangle is the unchanged P165 ROI. The path uses acquisition timestamps, not CSV row order or an invented traversal. All camera positions fall inside the source footprint.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    flight = read("flight_and_crs.json")
    heights = cameras.Z.to_numpy()
    axes[0].plot(cameras.order, heights, label="Camera altitude")
    axes[0].fill_between(
        cameras.order,
        heights - 30,
        heights + 30,
        alpha=0.15,
        label="Explicit +/-30 m height cases",
    )
    axes[0].set_xlabel("Acquisition order")
    axes[0].set_ylabel("Reported camera Z (m; datum unverified)")
    axes[0].legend()
    axes[1].imshow(raw, extent=extent, cmap="gray", vmin=0, vmax=0.3)
    for i in np.linspace(20, 540, 8, dtype=int):
        cam = cameras.iloc[i]
        H = flight["height_above_aligned_surface"]["mean"]
        hw, hh = H * np.array([1280, 960]) * 3.75 * 0.001 / (2 * 5.5)
        hd = np.deg2rad(cam.heading_grid_deg)
        v = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])
        X = cam.X + v[:, 0] * np.cos(hd) + v[:, 1] * np.sin(hd)
        Y = cam.Y - v[:, 0] * np.sin(hd) + v[:, 1] * np.cos(hd)
        axes[1].add_patch(
            Polygon(np.c_[X, Y], fill=False, lw=0.8, edgecolor=plt.cm.viridis(i / 565))
        )
        axes[1].text(cam.X, cam.Y, str(i), fontsize=8)
    axes[1].set_xlim(extent[:2])
    axes[1].set_ylim(extent[2:])
    axes[1].set_aspect("equal")
    axes[1].set_title("Illustrative footprints at mean height")
    axes[1].set_xlabel("Easting (m)")
    axes[1].set_ylabel("Northing (m)")
    save(
        fig,
        "figure02_footprints",
        "Reported intrinsics constrain plausible footprints",
        "The project and DEM report explicitly specify EPSG:26913; interpreting the CSV numbers as EPSG:5070 misses Goldhill by 2,874 km. Ideal pinhole rectangles use 1280 x 960 pixels, 5.5 mm focal length and 3.75 micrometre pixels. Each native target uses its local DEM height; these illustration rectangles use mean height only. Report distortion coefficients are preserved separately, but their PhotoID binding and exact footprint applicability are unverified. Occlusion, actual yaw and shared vertical datum remain unresolved.",
    )
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fields = [
        (0, "A zenith (degrees)", 0, 25, "viridis"),
        (3, "B zenith (degrees)", 0, 25, "viridis"),
        (maps[..., 2] != maps[..., 5], "Different assigned cameras", 0, 1, "coolwarm"),
        (1, "A true azimuth (degrees)", 0, 360, "twilight"),
        (4, "B true azimuth (degrees)", 0, 360, "twilight"),
        (6, "C candidate count", 0, 225, "viridis"),
    ]
    for ax, (field, title, lo, hi, cm) in zip(axes.flat, fields):
        z = maps[..., field] if isinstance(field, int) else field
        z = np.where(alpha, z[::6, ::6], np.nan)
        im = ax.imshow(z, extent=extent, vmin=lo, vmax=hi, cmap=cm)
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, shrink=0.7)
    save(
        fig,
        "figure03_angles",
        "Camera selection changes inferred viewing direction",
        "A chooses the closest eligible camera. B chooses the most central normalized position within a rectangular footprint. The two assignments differ on 25.83% of covered native cells. Median zenith is about 2 degrees, but edge pixels reach 19-22 degrees. Azimuth is clockwise from true north toward the sensor, with the grid-to-true rotation explicitly applied.",
    )
    with rasterio.open(WORK / "A_view_and_kernel_maps_EXPERIMENTAL.tif") as src:
        kernel = src.read()[:, y0:y1, x0:x1]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fields = [
        (0, "Zenith (degrees)", 0, 25, "viridis"),
        (1, "True azimuth (degrees)", 0, 360, "twilight"),
        (2, "Solar minus view azimuth (degrees)", 0, 360, "twilight"),
        (3, "RossThick kernel", None, None, "viridis"),
        (4, "LiDenseR kernel", None, None, "viridis"),
        (5, "Assigned acquisition order", 0, 564, "viridis"),
    ]
    for ax, (i, label, lo, hi, cm) in zip(axes.flat, fields):
        im = ax.imshow(kernel[i], vmin=lo, vmax=hi, cmap=cm)
        ax.set_title(label)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, shrink=0.7)
    save(
        fig,
        "figure04_roi_kernels",
        "The fixed red-line region now has varying kernel inputs",
        "Native 10 cm ROI, identical row/column extent for every panel. Kernels are evaluated by the unchanged shared functions. The relative-angle map is a display diagnostic; no new solar field is fitted or substituted. The abrupt camera-label pattern is inferred assignment, not an observed Metashape seamline.",
    )
    rays = pd.read_csv(HERE / "fixed_point_candidate_rays.csv")
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for i, (b, title) in enumerate(
        [
            (6, "Potential cameras per native pixel"),
            (7, "Minimum candidate zenith"),
            (8, "Maximum candidate zenith"),
        ]
    ):
        im = axes[0, i].imshow(
            np.where(alpha, maps[::6, ::6, b], np.nan), extent=extent, cmap="viridis"
        )
        axes[0, i].set_title(title)
        axes[0, i].set_xticks([])
        axes[0, i].set_yticks([])
        fig.colorbar(im, ax=axes[0, i], shrink=0.7)
    for point, g in rays.groupby("point"):
        axes[1, 0].hist(
            g.zenith_deg, bins=np.linspace(0, 30, 20), histtype="step", label=point
        )
        axes[1, 1].hist(g.relative_deg, bins=np.linspace(0, 360, 25), histtype="step")
        axes[1, 2].scatter(g.RossThick, g.LiDenseR, s=10, alpha=0.6, label=point)
    axes[1, 0].set_xlabel("Candidate view zenith (degrees)")
    axes[1, 0].set_ylabel("Potential cameras")
    axes[1, 0].legend(fontsize=7)
    axes[1, 1].set_xlabel("Relative azimuth (degrees)")
    axes[1, 2].set_xlabel("Individual RossThick")
    axes[1, 2].set_ylabel("Individual LiDenseR")
    save(
        fig,
        "figure05_overlap",
        "Overlap provides candidate rays, not repeated reflectance data",
        "The rectangular-footprint scenario has 4-221 potential cameras per covered native pixel, median 84. Bottom panels retain every eligible ray at the four unchanged diagnostic points. C uniform/central-weighted models use one aggregate kernel row per mosaic value. They never fit the same reflectance repeatedly at every possible angle.",
    )
    sensitivity = read("footprint_sensitivity.json")
    fits = read("fit_sensitivity.json")
    cases = [x["scenario"] for x in sensitivity]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].barh(
        cases,
        [x["C_candidate_count"]["quantiles"][4] for x in sensitivity],
        color=COLORS[0],
    )
    axes[0].set_xlabel("Median candidate cameras")
    axes[1].barh(
        cases,
        [100 * x["B_assignment_change_fraction"] for x in sensitivity],
        color=COLORS[2],
    )
    axes[1].set_xlabel("B assignment changed (%)")
    for scenario, color in zip(["A", "B", "C_uniform", "C_center"], COLORS):
        records = [r for r in fits if r["scenario"] == scenario]
        axes[2].plot(
            np.arange(len(records)),
            [r["red_reference_prediction"] for r in records],
            "-o",
            label=scenario,
            color=color,
        )
    axes[2].set_xticks(
        range(6), ["base", "80%", "120%", "H-30", "H+30", "yaw90"], rotation=45
    )
    axes[2].set_ylabel("Fitted reference red prediction")
    axes[2].legend(fontsize=8)
    save(
        fig,
        "figure06_uncertainty",
        "Uncertain footprint geometry changes the inferred correction",
        "Six prespecified cases use an every-tenth native-pixel lattice, not newly averaged reflectance. All 24 sampled BRDF fits pass the existing numerical guards. Footprint yaw rotation changes 42.7% of B assignments; camera-height minus 30 m leaves a small uncovered fraction. C normalization changes with assumed footprint width and weights. These are scenario sensitivities, not statistical confidence intervals or validation of any contributor rule.",
    )
    support = read("design_support.json")
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    names = ["Legacy nadir"] + [x["scenario"] for x in support]
    axes[0].bar(
        names,
        [1] + [x["stable_rank"] for x in support],
        color=[COLORS[1]] + [COLORS[2]] * 4,
    )
    axes[0].set_ylabel("Stable numerical rank")
    axes[0].set_ylim(0, 3.5)
    for i, r in enumerate(support):
        s = np.array(r["singular_values"])
        axes[1].semilogy(range(1, 4), s / s[0], "-o", label=r["scenario"])
        axes[2].plot(
            [z["row_start"] for z in r["tiles"]],
            [z["condition"] for z in r["tiles"]],
            label=r["scenario"],
        )
    axes[1].axhline(
        np.sqrt(np.finfo(np.float32).eps),
        ls="--",
        c="gray",
        label="Existing precision threshold",
    )
    axes[1].set_xlabel("Singular-value order")
    axes[1].set_ylabel("Singular value / largest")
    axes[1].legend(fontsize=8)
    axes[2].set_yscale("log")
    axes[2].set_xlabel("128-row spatial strip start")
    axes[2].set_ylabel("Local design condition number")
    axes[2].legend(fontsize=8)
    save(
        fig,
        "figure07_rank",
        "Reconstructed scenarios reach rank 3 without weakening the rank rule",
        "Full native designs use 6,683,905 ground observations, each at most once. Global condition numbers are 98-182, below the unchanged precision limit of about 2,896. Spatial strips are less well conditioned in places; no strip was independently labeled a successful local BRDF fit. Rank identifies the assumed spatial model, not empirical same-target directional behavior.",
    )
    for wavelength in [650, 717]:
        names = [
            "clean_raw",
            "topographic_only",
            "historical_BRDF",
            "A_brdf",
            "B_brdf",
            "C_uniform_brdf",
            "C_center_brdf",
            "A_combined",
        ]
        labels = [
            "Clean raw",
            "Topo-only diagnostic",
            "Historical BRDF",
            "A nearest BRDF",
            "B central BRDF",
            "C uniform BRDF",
            "C center BRDF",
            "A combined",
        ]
        fig, axes = plt.subplots(2, 4, figsize=(15, 8))
        for ax, name, label in zip(axes.flat, names, labels):
            im = ax.imshow(
                roi[name + "_" + str(wavelength)], vmin=0, vmax=0.3, cmap="viridis"
            )
            ax.set_title(label)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.subplots_adjust(right=0.93)
        cb = fig.add_axes([0.945, 0.15, 0.012, 0.55])
        fig.colorbar(
            im, cax=cb, label="Candidate fractional reflectance (display 0-0.3)"
        )
        # Manual colorbar has its own axis; do not tight_layout across it.
        title = f"Fixed native ROI: {wavelength} nm historical line versus reconstructed scenarios"
        caption = "All panels use the original 401 x 501 pixel ROI and identical 0-0.3 display limits. Numerical extrema and factors are retained in tables; saturated display colors do not clip analytical values. Experimental BRDF-only images lack the enormous historical boundary. Combined products still inherit the separate topographic instability, especially at 717 nm."
        fig.suptitle(
            title + "\nExperimental geometry; calibration and contributors unverified",
            fontsize=14,
            weight="bold",
        )
        name = "figure08_red" if wavelength == 650 else "figure09_rededge"
        fig.savefig(HERE / (name + ".png"), bbox_inches="tight")
        fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
        plt.close(fig)
        manifest.append(
            dict(png=name + ".png", svg=name + ".svg", title=title, caption=caption)
        )
    fig, axes = plt.subplots(3, 2, figsize=(14, 9))
    columns = np.arange(start, end)
    for col, wave in enumerate([650, 717]):
        for name, label, color in zip(
            [BRANCHES[0]] + BRANCHES[2:],
            [LABELS[0]] + LABELS[2:],
            [COLORS[0]] + COLORS[2:],
        ):
            axes[0, col].plot(
                columns, tr[name + "_" + str(wave)], lw=1, label=label, color=color
            )
        for name, label, color in zip(BRANCHES[2:], LABELS[2:], COLORS[2:]):
            axes[1, col].plot(
                columns,
                tr[name + "_factor_" + str(wave)],
                lw=1,
                label=label,
                color=color,
            )
            axes[2, col].plot(
                columns, tr[name + "_prediction_" + str(wave)], lw=1, color=color
            )
            axes[2, col].plot(
                columns,
                tr[name + "_reference_" + str(wave)],
                lw=0.8,
                ls="--",
                color=color,
            )
        axes[0, col].set_title(str(wave) + " nm")
        axes[0, col].set_ylabel("Candidate reflectance")
        axes[1, col].set_ylabel("BRDF factor")
        axes[2, col].set_ylabel("Predicted observed / dashed reference")
        axes[2, col].set_xlabel("Native column at fixed row 921")
        for ax in axes[:, col]:
            ax.axvline(left + 0.5, c="gray", ls="--", lw=0.8)
    axes[0, 0].legend(fontsize=8, ncol=2)
    save(
        fig,
        "figure10_transects",
        "The fixed transect has resolved predictions instead of a zero crossing",
        "The historical 650 nm adjacent jump was 674,321 candidate units; reconstructed BRDF-only jumps are about 0.0009-0.0013. Historical values are omitted from these linear axes because their enormous scale would hide all other signals; their unchanged values remain in the ROI panels and numerical tables. Solid prediction curves and dashed reference levels come from the accepted experimental models, not visual inversion.",
    )
    seams = read("assignment_boundary_metrics.json")
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    geometry = maps[window]
    for i, name in enumerate(["A_brdf", "B_brdf", "C_center_brdf"]):
        factor = roi[name + "_factor_650"]
        im = axes[0, i].imshow(factor, cmap="viridis", vmin=0.6, vmax=1.6)
        axes[0, i].set_title(name + " factor650")
        axes[0, i].set_xticks([])
        axes[0, i].set_yticks([])
        fig.colorbar(im, ax=axes[0, i], shrink=0.7)
        field = geometry[..., 2 if i == 0 else 5 if i == 1 else 6]
        seam = field[:, :-1] != field[:, 1:]
        overlay = np.full((*field.shape, 4), 0.0)
        overlay[:, :-1, 0] = 1
        overlay[:, :-1, 3] = seam * 0.65
        axes[0, i].imshow(overlay)
    for i, metric in enumerate(
        ["factor_jump", "corrected_jump", "factor_induced_signal_component"]
    ):
        records = [
            r
            for r in seams
            if r["wavelength"] == 650 and r["edge_set"] == "assignment_change"
        ]
        axes[1, i].bar(
            [r["scenario"] for r in records],
            [r[metric]["quantiles"][6] for r in records],
            color=COLORS[2:],
        )
        axes[1, i].set_ylabel("99th percentile " + metric.replace("_", " "))
        axes[1, i].tick_params(axis="x", rotation=25)
    save(
        fig,
        "figure11_assignment_seams",
        "Removing the old stripe does not establish seam-free correction",
        "Red overlays mark inferred A/B assignment changes or C candidate-count changes. Kernel inputs can jump when assignments change. Bottom diagnostics use native horizontal edges, with raw and corrected jumps and a factor-induced signal component separately retained. These are algorithmic sensitivity diagnostics, not independently verified physical seams. Fixed factor display limits never cap numerical gains.",
    )
    spectra = read("exemplar_spectra.json")
    lookup = {r["branch"]: np.array(r["mean_spectrum"]) for r in spectra}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for name, label, color in zip(BRANCHES, LABELS, COLORS):
        values = lookup[name]
        axes[0].semilogy(WAVES, values, "-o", ms=3, label=label, color=color)
        if name != "historical_BRDF":
            axes[1].plot(WAVES, values, "-o", ms=3, color=color, label=label)
        axes[2].plot(WAVES, values / values.sum(), "-o", ms=3, color=color)
    axes[0].set_ylabel("Mean candidate reflectance, log axis")
    axes[1].set_ylabel("Mean candidate reflectance, linear axis")
    axes[2].set_ylabel("Unit-sum spectral shape")
    for ax in axes:
        ax.set_xlabel("Wavelength (nm)")
    axes[0].legend(fontsize=8)
    save(
        fig,
        "figure12_spectra",
        "The same boundary-crossing aspen polygon retains a vegetation spectrum",
        "The exemplar GlobalID and memberships are unchanged from P165/P172. The historical spectrum is dominated by corrupted red and red-edge bands. Experimental BRDF-only spectra remain on the raw-scale range; shape and class information are evaluated separately from numerical fitting success. Unit-sum shape is a display diagnostic, not a new radiometric calibration.",
    )
    scores = read("classification_summary.json")
    gains = {r["branch"]: r for r in read("paired_gain.json")}
    pol = pd.read_csv(HERE / "polygon_summaries.csv")
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    order = [
        "clean_raw",
        "historical_BRDF",
        "A_brdf",
        "B_brdf",
        "C_uniform_brdf",
        "C_center_brdf",
    ]
    labels = ["Raw", "Historical", "A", "B", "C uniform", "C center"]
    sc = {r["branch"]: r["balanced_accuracy"] for r in scores}
    axes[0].bar(labels, [100 * sc[n] for n in order], color=COLORS)
    axes[0].set_ylabel("Balanced accuracy (%)")
    axes[0].set_ylim(0, 100)
    for i, n in enumerate(order[2:]):
        r = gains[n]
        axes[1].errorbar(
            100 * r["difference"],
            i,
            xerr=[
                [100 * (r["difference"] - r["low"])],
                [100 * (r["high"] - r["difference"])],
            ],
            fmt="o",
            c=COLORS[i + 2],
            capsize=3,
        )
    axes[1].axvline(0, c="gray", ls="--")
    axes[1].set_yticks(range(4), labels[2:])
    axes[1].set_xlabel("Paired accuracy change vs raw (points), 95% interval")
    med = pol.groupby("branch").within_angle_median.median()
    axes[2].bar(labels, [med[n] for n in order], color=COLORS)
    axes[2].set_ylabel("Median within-polygon spectral angle (degrees)")
    save(
        fig,
        "figure13_ecology",
        "BRDF-only ecological gains are modest and uncertain",
        "All comparisons preserve 157 independent polygon identities, 144,406 memberships, seed 20261103, three folds, fixed classifier C=1 and training-only scaling. Raw 66.83%, historical 59.96%; A 69.81%, B 69.46%, C uniform 67.14%, C center 69.65%. Every BRDF-only paired gain interval includes zero. No held-out score was used to choose footprints, weights, thresholds or BRDF parameters.",
    )
    metrics = read("matched_metrics.json")
    stats = {r["branch"]: r for r in metrics}
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    names = [
        "clean_raw",
        "topographic_only",
        "A_brdf",
        "A_combined",
        "B_combined",
        "C_uniform_combined",
        "C_center_combined",
    ]
    labels = [
        "Raw",
        "Topo only",
        "A BRDF",
        "A combined",
        "B combined",
        "C uniform + topo",
        "C center + topo",
    ]
    axes[0].barh(
        labels,
        [stats[n]["band_stats"][1]["distribution"]["maximum"] for n in names],
        color=COLORS[0],
    )
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Maximum 717 nm candidate reflectance, log axis")
    axes[1].barh(labels, [100 * sc.get(n, np.nan) for n in names], color=COLORS[2])
    axes[1].set_xlabel("Balanced accuracy (%)")
    axes[1].set_xlim(0, 100)
    save(
        fig,
        "figure14_topographic_risk",
        "The separate topographic instability is still unresolved",
        "Combined runs pass the current BRDF numerical checks but reach 717 nm candidate reflectance maxima of about 50-70, versus 0.41-0.50 for BRDF-only. These extreme values are not clipped or approved. Combined ecological outcomes depend strongly on the assumed geometry; numerical acceptance is insufficient for scientific production readiness.",
    )
    (HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(len(manifest), "figure pairs complete")


if __name__ == "__main__":
    main()
