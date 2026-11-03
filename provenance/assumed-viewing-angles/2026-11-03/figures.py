"""Scientific figures: real source DN, imposed geometry, and uncomputed branches."""

from pathlib import Path
import json
from collections import Counter
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
NAMES = ["gordon", "goldhill", "ruby"]
COLORS = ["#276f91", "#b77535", "#4b8a6d"]
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def save(fig, name):
    fig.savefig(HERE / name, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    const = pd.read_csv(HERE / "constant_geometries.csv")
    spatial = pd.read_csv(HERE / "spatial_geometries.csv")
    summary = json.loads((HERE / "experiment_summary.json").read_text())
    inventory = json.loads((HERE / "coefficient_inventory.json").read_text())
    polys = pd.read_csv(HERE / "baseline_polygon_spectra.csv")
    within = pd.read_csv(HERE / "within_class_metrics.csv")
    sep = pd.read_csv(HERE / "separability.csv")
    display = {n: np.load(HERE / f"{n}_display.npz") for n in NAMES}
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.6))
    for ax, title in zip(
        axs,
        [
            "Encoded baseline",
            "Constant assumed view",
            "Spatially varying invented views",
        ],
    ):
        ax.set(xlim=(-1.3, 1.3), ylim=(-0.15, 1.9))
        ax.axis("off")
        ax.plot([-1.2, 1.2], [0, 0], color="#758d61", lw=5)
        ax.scatter([0], [0], marker="s", color="#b77535", s=55)
        ax.set_title(title, fontweight="bold")
    axs[0].plot([0, 0], [0, 1.5], ls="--", color="#ac4a49", lw=3)
    axs[0].scatter([0], [1.5], color="#276f91", s=150)
    axs[0].text(0, 1.73, "H5 stores 0 degrees", ha="center")
    axs[0].text(
        0,
        0.8,
        "Placeholder,\nnot a measured ray",
        ha="center",
        bbox={"facecolor": "white", "edgecolor": "none"},
    )
    axs[1].plot([0, 0.5], [0, 1.5], color="#b77535", lw=3)
    axs[1].plot([0, 0], [0, 1.5], ls=":", color="grey")
    axs[1].scatter([0.5], [1.5], color="#b77535", s=150)
    axs[1].text(
        0,
        0.8,
        "Same assumed direction\nat every ground pixel",
        ha="center",
        bbox={"facecolor": "white", "edgecolor": "none"},
    )
    axs[1].text(
        0, 1.73, "Changes kernel row; no new information", ha="center", fontsize=10
    )
    for x in [-0.8, 0, 0.8]:
        axs[2].plot([0, x], [0, 1.5], color="#4b8a6d", lw=2)
        axs[2].scatter([x], [1.5], s=100, color="#4b8a6d")
    axs[2].text(
        0,
        0.72,
        "Numerical diversity\nassigned by the experiment",
        ha="center",
        bbox={"facecolor": "white", "edgecolor": "none"},
    )
    axs[2].text(
        0, 1.73, "These are not recovered photographs", ha="center", fontsize=10
    )
    fig.suptitle(
        "Figure 1. Assumed viewing geometry cannot recreate separate source observations",
        fontsize=15,
        y=1.03,
    )
    fig.text(
        0.5,
        -0.04,
        "Schematic only. Actual calibrated overlapping photos and camera-to-ground rays remain unavailable.",
        ha="center",
    )
    save(fig, "figure1_geometry.png")
    fig, axs = plt.subplots(2, 3, figsize=(14, 7.4), sharex=True)
    for j, name in enumerate(NAMES):
        d = const[const.flight.eq(name)]
        for rel in [0, 45, 90, 135, 180]:
            g = d[d.relative_azimuth_degrees.eq(rel)]
            # At nadir include one unique observation in each response curve for continuity only.
            if rel != 0:
                g = pd.concat([d[d.view_zenith_degrees.eq(0)], g]).sort_values(
                    "view_zenith_degrees"
                )
            for i, col in enumerate(["RossThick", "LiDenseR"]):
                axs[i, j].plot(
                    g.view_zenith_degrees, g[col], marker="o", label=f"{rel} deg"
                )
        axs[0, j].set_title(
            name.title()
            + f" | scene solar {summary['flights'][name]['solar_scene_zenith_degrees']:.2f} deg"
        )
        axs[1, j].set_xlabel("Assumed view zenith (degrees)")
    axs[0, 0].set_ylabel("RossThick kernel")
    axs[1, 0].set_ylabel("LiDenseR kernel")
    axs[0, 2].legend(title="Relative azimuth", fontsize=9)
    fig.suptitle(
        "Figure 2. Kernels change with imposed angle; no reflectance coefficients are fitted",
        fontsize=15,
        y=1.02,
    )
    fig.tight_layout()
    save(fig, "figure2_kernel_response.png")
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    for name, color in zip(NAMES, COLORS):
        g = const[const.flight.eq(name)]
        axs[0].scatter(
            g.view_zenith_degrees,
            np.log10(g.condition_number),
            s=35,
            alpha=0.7,
            label=name.title(),
            color=color,
        )
    axs[0].axhline(
        np.log10(2896.31), ls="--", color="black", label="Current precision limit"
    )
    axs[0].set(
        xlabel="Assumed view zenith (degrees)",
        ylabel="log10(condition number)",
        title="0 of 93 constant cases pass",
    )
    axs[0].legend(fontsize=9)
    labels = ["Footprints", "Alternating", "Edges", "Smooth", "Reflected"]
    x = np.arange(5)
    for j, (name, color) in enumerate(zip(NAMES, COLORS)):
        g = spatial[spatial.flight.eq(name)]
        axs[1].bar(
            x + (j - 1) * 0.24,
            np.log10(g.condition_number),
            width=0.23,
            color=color,
            label=name.title(),
        )
    axs[1].axhline(np.log10(2896.31), ls="--", color="black")
    axs[1].set(
        xticks=x,
        xticklabels=labels,
        ylabel="log10(condition number)",
        title="12 of 15 synthetic cases pass angular-only gates",
    )
    axs[1].tick_params(axis="x", rotation=18)
    fig.suptitle(
        "Figure 3. Mathematical rank is not physical evidence", fontsize=15, y=1.04
    )
    fig.text(
        0.5,
        -0.05,
        "Constant relative geometry has one independent row. Roundoff can give nominal rank 3; conditioning rejects it.\nEvery spatial case has nominal rank 3; all remain physically unsupported.",
        ha="center",
    )
    fig.tight_layout()
    save(fig, "figure3_identifiability.png")
    scenarios = [
        "symmetric_footprints",
        "alternating_strips",
        "mosaic_edges",
        "smooth_map",
        "smooth_map_reflected",
    ]
    titles = [
        "Repeated pinhole footprints",
        "Alternating hypothetical strips",
        "Edge-weighted view",
        "Smooth hypothetical field",
        "Reflected smooth field",
    ]
    fig, axs = plt.subplots(5, 3, figsize=(13, 13.5), layout="constrained")
    d = display["goldhill"]
    mask = d["valid"]
    for i, (scenario, title) in enumerate(zip(scenarios, titles)):
        for j, (suf, lim) in enumerate(
            [("zenith", (0, 30)), ("kv", (-0.15, 0.16)), ("kg", (-2, 9))]
        ):
            im = axs[i, j].imshow(
                np.where(mask, d[scenario + "_" + suf], np.nan),
                vmin=lim[0],
                vmax=lim[1],
                cmap="viridis" if j == 0 else "coolwarm",
                interpolation="nearest",
            )
            axs[i, j].axis("off")
            if j == 0:
                axs[i, j].set_title(title, loc="left", fontsize=11)
            if i == 0:
                axs[i, j].text(
                    0.5,
                    1.18,
                    ["Assumed zenith (degrees)", "RossThick kernel", "LiDenseR kernel"][
                        j
                    ],
                    transform=axs[i, j].transAxes,
                    ha="center",
                    fontsize=12,
                )
            if i == 4:
                fig.colorbar(
                    im, ax=axs[:, j], orientation="horizontal", fraction=0.02, pad=0.02
                )
    fig.suptitle(
        "Figure 4. Synthetic geometry laid onto the actual Goldhill footprint\nNo measured camera rays or corrected pixels are shown",
        fontsize=15,
    )
    save(fig, "figure4_synthetic_maps.png")
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    counter = Counter(r["classification"] for r in inventory["candidates"])
    keys = [
        "SYNTHETIC_CONTRACT_FIXTURE",
        "UNSUPPORTED_OR_INVALID",
        "HISTORICAL_UNVALIDATED_MODEL",
    ]
    axs[0].barh(
        range(len(keys)),
        [counter[k] for k in keys],
        color=["#b77535", "#ac4a49", "#6f8998"],
    )
    axs[0].set(
        yticks=range(len(keys)),
        yticklabels=[
            "Synthetic fixtures",
            "Unsupported / invalid",
            "Historical, unvalidated",
        ],
        xlabel="Candidate coefficient files",
        xlim=(0, 7),
        title="13 candidate files; 0 eligible independent sets",
    )
    axs[1].axis("off")
    axs[1].text(
        0.03,
        0.85,
        "Correction-factor distributions:\nNOT EVALUATED",
        fontsize=19,
        color="#ac4a49",
        fontweight="bold",
    )
    axs[1].text(
        0.03,
        0.43,
        "No validated transferable coefficient set.\nNo invented coefficients or assumed-angle refits.\n\nInvalid prediction counts, gains and corrected\ncoverage are unknown, not zero or factor one.",
        fontsize=12,
    )
    fig.suptitle(
        "Figure 5. A computational VALID fixture is not an empirical NEON calibration",
        fontsize=15,
        y=1.05,
    )
    fig.tight_layout()
    save(fig, "figure5_coefficient_boundary.png")
    d = display["goldhill"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    im = axs[0].imshow(
        np.where(d["valid"], d["raw"][..., 4], np.nan),
        cmap="magma",
        vmin=0,
        vmax=20000,
        interpolation="nearest",
    )
    axs[0].set_title("Uncorrected 650 nm | source DN")
    axs[0].set_xlabel("Display column (8 native pixels)")
    axs[0].set_ylabel("Display row (8 native pixels)")
    fig.colorbar(im, ax=axs[0], label="Source-DN representation")
    native = np.load(
        "/private/tmp/drone-brdf-strategy-20261102/goldhill_raw.npy", mmap_mode="r"
    )
    axs[1].plot(
        np.arange(840, 1121),
        native[921, 840:1121, 4],
        color="#b77535",
        label="Actual uncorrected source DN",
    )
    axs[1].axvline(
        980, color="grey", ls="--", label="Prior historical artifact crossing"
    )
    axs[1].set(
        xlabel="Native column; row 921",
        ylabel="650 nm source DN",
        title="Historical boundary location; no assumed-angle output",
    )
    axs[1].legend(fontsize=9)
    axs[1].text(
        0.03,
        0.08,
        "10/15-degree correction curves do not exist:\nno eligible coefficient model.",
        transform=axs[1].transAxes,
        color="#ac4a49",
    )
    fig.suptitle(
        "Figure 6. Goldhill baseline: real uncorrected values, with no topographic processing",
        fontsize=15,
        y=1.04,
    )
    fig.tight_layout()
    save(fig, "figure6_goldhill.png")
    samples = np.vstack([d["raw"][d["valid"]][:, [4, 3, 1]] for d in display.values()])
    lo, hi = np.percentile(samples, [2, 98], axis=0)
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, name in zip(axs, NAMES):
        d = display[name]
        rgb = np.clip((d["raw"][..., [4, 3, 1]] - lo) / (hi - lo), 0, 1)
        rgb = np.where(d["valid"][..., None], rgb, 1)
        ax.imshow(rgb, interpolation="nearest")
        ax.axis("off")
        ax.set_title(name.title())
    fig.suptitle(
        "Figure 7. Actual uncorrected RGB: one pooled DN display scale across all flights",
        fontsize=15,
        y=0.98,
    )
    fig.text(
        0.5,
        0.04,
        "RGB 650/560/475 nm. Pooled 2nd-98th percentile channel limits affect display only; no corrections or per-panel stretches.",
        ha="center",
        fontsize=11,
    )
    save(fig, "figure7_raw_rgb.png")
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.5))
    labels = [f"{r.flight.title()} | {r.cover_category}" for r in within.itertuples()]
    axs[0].barh(
        np.arange(len(within)),
        within.median_band_cv,
        color=[COLORS[NAMES.index(x)] for x in within.flight],
    )
    axs[0].set(
        yticks=np.arange(len(within)),
        yticklabels=labels,
        xlabel="Median across-band CV of polygon median spectra",
        title="Within-class raw-DN dispersion (not calibration error)",
    )
    axs[0].invert_yaxis()
    axs[0].tick_params(axis="y", labelsize=8)
    eligible = sep[sep.status.eq("DESCRIPTIVE_CONDITIONAL_TEST")]
    offset = 0
    for name, color in zip(NAMES, COLORS):
        g = eligible[eligible.flight.eq(name)]
        axs[1].scatter(
            np.arange(len(g)) + offset,
            g.mean_absolute_standardized_effect,
            label=name.title(),
            color=color,
            s=45,
        )
        offset += len(g)
    axs[1].set(
        xlabel="Supported class pair (polygon/spatial support)",
        ylabel="Mean absolute standardized spectral contrast",
        title=f"Between-class baseline | {len(eligible)} supported, 5 insufficient",
    )
    axs[1].legend()
    axs[1].text(
        0.02,
        0.02,
        "No corrected branch or improvement test exists.",
        transform=axs[1].transAxes,
        color="#ac4a49",
        fontsize=10,
    )
    fig.suptitle(
        "Figure 8. Researcher-PFT baseline: polygons, not random pixels, are the analysis units",
        fontsize=15,
        y=1.02,
    )
    fig.tight_layout()
    save(fig, "figure8_pft_baseline.png")
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for name, color in zip(NAMES, COLORS):
        d = const[const.flight.eq(name)]
        for ax, col in zip(axs, ["RossThick", "LiDenseR"]):
            g = (
                d[d.view_zenith_degrees > 0]
                .groupby("view_zenith_degrees")[col]
                .agg(["min", "max"])
            )
            ax.fill_between(g.index, g["min"], g["max"], color=color, alpha=0.2)
            ax.plot(
                g.index,
                g["max"] - g["min"],
                marker="o",
                color=color,
                label=name.title(),
            )
            ax.set(
                xlabel="Assumed zenith (degrees)",
                ylabel="Kernel value / azimuth span",
                title=col + ": plausible azimuth assumptions change the basis",
            )
    axs[0].legend()
    fig.suptitle(
        "Figure 9. Sensitivity of the actual package kernels, not a correction-factor result",
        fontsize=15,
        y=1.05,
    )
    fig.text(
        0.5,
        -0.04,
        "Shading: kernel range across relative azimuth. Lines: max-min span. Reflectance change cannot be computed without eligible coefficients.",
        ha="center",
        fontsize=10,
    )
    fig.tight_layout()
    save(fig, "figure9_sensitivity.png")
    # Report independent polygon associations under two equally invented maps, without fitting reflectance.
    syn = pd.read_csv(HERE / "synthetic_polygon_kernels.csv").merge(
        polys, on=["flight", "GlobalID", "cover_category"]
    )
    rows = []
    for (flight, scenario), g in syn[syn.independent_component_representative].groupby(
        ["flight", "scenario"]
    ):
        for k in ["RossThick", "LiDenseR"]:
            rows.append(
                dict(
                    flight=flight,
                    scenario=scenario,
                    kernel=k,
                    polygons=len(g),
                    spearman_raw_red_vs_imposed_kernel=float(
                        spearmanr(g.b5, g[k + "_mean"]).statistic
                    ),
                    meaning="Descriptive spatial association; not a BRDF fit or correction",
                )
            )
    pd.DataFrame(rows).to_csv(HERE / "imposed_geometry_associations.csv", index=False)
    (HERE / "display_limits.json").write_text(
        json.dumps(
            dict(
                RGB_wavelengths_nm=[650, 560, 475],
                pooled_lower_2_percent_DN=lo.tolist(),
                pooled_upper_98_percent_DN=hi.tolist(),
                Goldhill_650_map_limits_DN=[0, 20000],
                display_sampling="Every eighth source pixel; no interpolation; source masks retained",
                no_analytical_clipping=True,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Nine labelled figures and display provenance saved.")


if __name__ == "__main__":
    main()
