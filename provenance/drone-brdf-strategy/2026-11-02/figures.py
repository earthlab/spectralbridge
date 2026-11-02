"""Figure-heavy P161 report assets; shared DN contrast and explicit rejected branches."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MaxNLocator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
manifest = json.loads((HERE / "manifest.json").read_text())
WORK = Path(manifest["work"])
flights = json.loads((HERE / "flight_analysis.json").read_text())
NAMES = ["gordon", "goldhill", "ruby"]
COLORS = ["#287ca1", "#d97a30", "#6a9950"]
WAVE = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
RGB = [int(np.argmin(abs(WAVE - w))) for w in [650, 560, 475]]
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def finish(fig, name):
    fig.savefig(HERE / name, dpi=190)
    plt.close(fig)


def render(ax, data, valid, extent, limits):
    rgb = np.clip(
        (np.asarray(data[:, :, RGB], float) - limits[0]) / (limits[1] - limits[0]), 0, 1
    )
    rgb[~valid] = [0.93, 0.93, 0.93]
    ax.imshow(rgb, extent=extent, interpolation="none", origin="upper")
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.tick_params(labelsize=7)


fig, axes = plt.subplots(3, 4, figsize=(17, 10), layout="constrained")
for i, (name, color) in enumerate(zip(NAMES, COLORS)):
    d = flights[name]["angular"]
    s = np.load(HERE / (name + "_display_samples.npz"))
    sz = s["solar_zenith"][s["valid"]]
    az = s["solar_azimuth"][s["valid"]]
    axes[i, 0].hist((sz - np.median(sz)) * 60, bins=30, color=color)
    axes[i, 0].set(
        xlabel="Solar zenith deviation from median (arcmin)",
        ylabel=name.title() + "\nDisplay-sampled cells",
    )
    axes[i, 0].set_title(f"Median {np.median(sz):.4f}°; tiny spatial gradient")
    axes[i, 1].plot([0], [1], "o", color=color, ms=12)
    axes[i, 1].set(
        xlim=(-1, 1), ylim=(0, 1.5), yticks=[], xlabel="Assigned view zenith (degrees)"
    )
    axes[i, 1].text(
        0,
        0.55,
        "All pixels: zenith = 0°, azimuth = 0°\nScalar fields, not contributing camera rays",
        ha="center",
        fontsize=9,
    )
    axes[i, 1].set_title("No measured viewing-angle diversity")
    kv = d["kernels"]["RossThick"]["quantiles_0_1_25_50_75_99_100"][3]
    kg = d["kernels"]["LiDenseR"]["quantiles_0_1_25_50_75_99_100"][3]
    axes[i, 2].scatter([kv], [kg], color=color, s=90)
    axes[i, 2].set(
        xlabel="RossThick kernel",
        ylabel="LiDenseR kernel",
        xlim=(kv - 0.01, kv + 0.01),
        ylim=(kg - 0.01, kg + 0.01),
    )
    axes[i, 2].set_title("One design row repeated across the mosaic")
    singular = np.array(d["singular_values"])
    axes[i, 3].plot([1, 2, 3], singular / singular[0], "o-", color=color)
    axes[i, 3].axhline(
        1 / d["condition_limit"], color="gray", ls="--", label="conditioning threshold"
    )
    axes[i, 3].set(
        yscale="log",
        ylim=(1e-27, 2),
        xticks=[1, 2, 3],
        xlabel="Singular direction",
        ylabel="Singular value / largest",
    )
    axes[i, 3].set_title(
        f"Rank {d['rank']}/3; effective dimension {d['stable_rank']:.1f}"
    )
fig.suptitle(
    "Figure 1. Millions of cells, one usable angular design direction per flight",
    fontsize=17,
)
finish(fig, "figure1_angular_information.png")
fig, axes = plt.subplots(3, 3, figsize=(14, 11), layout="constrained")
for i, name in enumerate(NAMES):
    s = np.load(HERE / (name + "_display_samples.npz"))
    grid = flights[name]["grid"]
    a = grid["transform"]
    extent = [a[2], a[2] + grid["width"] * a[0], a[5] + grid["height"] * a[4], a[5]]
    limits = np.percentile(s["raw"][:, :, RGB][s["valid"]], [2, 98], axis=0)
    for j, key in enumerate(["raw", "topo"]):
        render(axes[i, j], s[key], s["valid"], extent, limits)
        axes[i, j].set_title(
            name.title()
            + ": "
            + ("raw recovered DN" if key == "raw" else "topographic DN sensitivity")
        )
        axes[i, j].set_xlabel("Easting (m)")
        axes[i, j].set_ylabel("Northing (m)")
    ax = axes[i, 2]
    ax.set_facecolor("#eef1f4")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(
        0.5,
        0.6,
        "BRDF: UNSUPPORTED",
        transform=ax.transAxes,
        ha="center",
        fontsize=15,
        color="#a13232",
        weight="bold",
    )
    ax.text(
        0.5,
        0.36,
        "Rank 1 of 3\nPhysical calibration unverified\nCombined topo + BRDF also unsupported",
        transform=ax.transAxes,
        ha="center",
        fontsize=11,
    )
fig.suptitle(
    "Figure 2. Raw and topographic sensitivity; no valid BRDF output for any flight\nIdentical raw-reference RGB stretch within each flight; all values are source DN, not verified reflectance",
    fontsize=15,
)
finish(fig, "figure2_correction_comparison.png")
fig, axes = plt.subplots(3, 2, figsize=(12, 12), layout="constrained")
for i, name in enumerate(NAMES):
    raw = np.load(WORK / (name + "_raw.npy"), mmap_mode="r")
    topo = np.load(WORK / (name + "_topo_diagnostic.npy"), mmap_mode="r")
    valid = np.load(WORK / (name + "_common_mask.npy"))
    h, w = valid.shape
    cy, cx = h // 2, w // 2
    if name == "goldhill":
        cy, cx = 921, 980
    roi = (slice(cy - 100, cy + 101), slice(cx - 100, cx + 101))
    v = valid[roi]
    limits = np.percentile(raw[roi][:, :, RGB][v], [2, 98], axis=0)
    a = flights[name]["grid"]["transform"]
    extent = [
        a[2] + (cx - 100) * a[0],
        a[2] + (cx + 101) * a[0],
        a[5] + (cy + 101) * a[4],
        a[5] + (cy - 100) * a[4],
    ]
    for j, data in enumerate([raw, topo]):
        render(axes[i, j], data[roi], v, extent, limits)
        axes[i, j].set_title(
            name.title() + (" raw DN" if j == 0 else " topo diagnostic (not accepted)")
        )
        axes[i, j].set_xlabel("Easting (m)")
        axes[i, j].set_ylabel("Northing (m)")
        axes[i, j].plot(
            [extent[0] + 1, extent[0] + 6],
            [extent[2] + 1, extent[2] + 1],
            color="white",
            lw=3,
        )
        axes[i, j].text(
            extent[0] + 3.5, extent[2] + 1.5, "5 m", ha="center", color="white"
        )
fig.suptitle(
    "Figure 2b. Native 0.1 m cells; fixed geometric extents and raw-reference contrast\nTerrain-related brightness differences are visible; source-photo seams and footprints are unavailable",
    fontsize=14,
)
finish(fig, "figure2b_native_regions.png")
# Real historical artifact, alongside the two isolated numerical candidates.
gold = flights["goldhill"]
roi = (slice(821, 1022), slice(840, 1121))
v = np.load(WORK / "goldhill_common_mask.npy")[roi]
raw = np.load(WORK / "goldhill_raw.npy", mmap_mode="r")[roi]
topo = np.load(WORK / "goldhill_topo_diagnostic.npy", mmap_mode="r")[roi]
historical = np.load(
    "/private/tmp/goldhill-radiometric-recovery-20261102/normalized_combined.npy",
    mmap_mode="r",
)[roi] * np.float32(6.5535)
limits = np.percentile(raw[:, :, RGB][v], [2, 98], axis=0)
a = gold["grid"]["transform"]
extent = [a[2] + 840 * 0.1, a[2] + 1121 * 0.1, a[5] - 1022 * 0.1, a[5] - 821 * 0.1]
fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout="constrained")
for ax, data, title in zip(
    axes,
    [historical, raw, topo],
    [
        "Historical invalid BRDF: artifact",
        "Recommended temporary baseline: raw DN",
        "Topographic sensitivity: unverified",
    ],
):
    render(ax, data, v, extent, limits)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
fig.suptitle(
    "Figure 3. Avoiding an unsupported correction avoids the artificial red boundary\nRaw and topo diagnostic remain uncalibrated; neither is presented as validated physical reflectance",
    fontsize=14,
)
finish(fig, "figure3_goldhill_red_streak.png")
# Polygon-level PFT/category spectra: no pixel pseudo-replication.
poly = pd.read_csv(HERE / "polygon_spectra.csv")
poly = poly[poly.independent_component_representative]
summary = pd.read_csv(HERE / "within_class_metrics.csv")
labels = ["Evergreen", "Woody shrub", "Herbaceous", "Deciduous", "Non-vegetated & dead"]
colors = dict(zip(labels, ["#167051", "#bc8235", "#7a9d35", "#ad4a66", "#6a6a70"]))
fig, axes = plt.subplots(2, 3, figsize=(16, 10), layout="constrained")
for j, name in enumerate(NAMES):
    for branch, ls in [("raw", "-"), ("topo_diagnostic", "--")]:
        for label in labels:
            p = poly[
                (poly.flight == name)
                & (poly.branch == branch)
                & (poly.cover_category == label)
            ]
            if len(p) < 5:
                continue
            X = p[[f"b{i}" for i in range(1, 11)]].to_numpy()
            q = np.percentile(X, [25, 50, 75], axis=0)
            axes[0, j].plot(
                [444, 475, 531, 560, 650, 668, 705, 717, 740, 862],
                q[1],
                ls=ls,
                color=colors[label],
                label=f"{label}, n={len(p)}" if branch == "raw" else None,
            )
            axes[0, j].fill_between(
                [444, 475, 531, 560, 650, 668, 705, 717, 740, 862],
                q[0],
                q[2],
                color=colors[label],
                alpha=0.06,
            )
    axes[0, j].set(
        title=name.title() + ": polygon medians and IQR",
        xlabel="Wavelength (nm)",
        ylabel="Recovered source DN",
    )
    axes[0, j].legend(fontsize=7)
    g = summary[summary.flight == name]
    ordered = [s for s in labels if s in set(g.cover_category)]
    x = np.arange(len(ordered))
    for branch, shift, color in [
        ("raw", -0.16, "#326f9c"),
        ("topo_diagnostic", 0.16, "#d48a44"),
    ]:
        d = g[g.branch == branch].set_index("cover_category").loc[ordered]
        axes[1, j].bar(
            x + shift,
            d.median_polygon_angle_degrees,
            0.30,
            label="Raw DN" if branch == "raw" else "Topo diagnostic",
            color=color,
        )
    axes[1, j].set(
        xticks=x,
        xticklabels=[
            x.replace("Non-vegetated & dead", "Non-veg / dead").replace(
                "Woody shrub", "Shrub"
            )
            for x in ordered
        ],
        ylabel="Median angle to class median spectrum (degrees)",
        title="Within-class shape consistency\nLower is not proof of accuracy",
    )
    axes[1, j].tick_params(axis="x", rotation=25, labelsize=8)
    axes[1, j].legend(fontsize=8)
fig.suptitle(
    "Figure 4. Topographic correction has mixed spectral effects\nSolid = raw DN; dashed = topo sensitivity. One median per non-overlapping polygon component; minimum five polygons per category.",
    fontsize=15,
)
finish(fig, "figure4_spectral_consequences.png")
# Paired class diagnostics, separability and numerical stability.
raw = summary[summary.branch == "raw"].set_index(["flight", "cover_category"])
topo = summary[summary.branch == "topo_diagnostic"].set_index(
    ["flight", "cover_category"]
)
keys = raw.index.intersection(topo.index)
variance = 100 * (
    topo.loc[keys].mean_band_variance_dn2 / raw.loc[keys].mean_band_variance_dn2 - 1
)
cv = 100 * (topo.loc[keys].median_band_cv / raw.loc[keys].median_band_cv - 1)
fig, axes = plt.subplots(2, 2, figsize=(15, 10), layout="constrained")
y = np.arange(len(keys))
texts = [
    n.title() + " · " + label.replace("Non-vegetated & dead", "Non-veg / dead")
    for n, label in keys
]
axes[0, 0].barh(y, variance, color=np.where(variance < 0, "#3a8b78", "#c46450"))
axes[0, 0].set(
    yticks=y,
    yticklabels=texts,
    xlabel="Topo versus raw: variance change (%)",
    title="Variance falls in some groups, rises in others",
)
axes[0, 0].axvline(0, color="gray")
axes[0, 0].tick_params(axis="y", labelsize=8)
axes[0, 1].barh(y, cv, color=np.where(cv < 0, "#3a8b78", "#c46450"))
axes[0, 1].set(
    yticks=y,
    yticklabels=texts,
    xlabel="Topo versus raw: median band-CV change (%)",
    title="Relative variation also shows mixed changes",
)
axes[0, 1].axvline(0, color="gray")
axes[0, 1].tick_params(axis="y", labelsize=8)
sep = pd.read_csv(HERE / "separability.csv")
sep = sep[sep.status == "DESCRIPTIVE_CONDITIONAL_TEST"]
a = sep[sep.branch == "raw"].set_index(["flight", "first", "second"])
b = sep[sep.branch == "topo_diagnostic"].set_index(["flight", "first", "second"])
idx = a.index.intersection(b.index)
for name, color in zip(NAMES, COLORS):
    k = [i for i in idx if i[0] == name]
    axes[1, 0].scatter(
        a.loc[k].mean_absolute_standardized_effect,
        b.loc[k].mean_absolute_standardized_effect,
        label=name.title(),
        color=color,
        s=40,
    )
lim = (
    max(
        a.mean_absolute_standardized_effect.max(),
        b.mean_absolute_standardized_effect.max(),
    )
    * 1.1
)
axes[1, 0].plot([0, lim], [0, lim], "--", color="gray")
axes[1, 0].set(
    xlabel="Raw pairwise standardized spectral effect",
    ylabel="Topo pairwise standardized spectral effect",
    title="Between-class contrast does not uniformly improve",
)
axes[1, 0].legend()
loss = [
    100
    * (flights[n]["source_geometry_masks"] - flights[n]["common_mask"])
    / flights[n]["source_geometry_masks"]
    for n in NAMES
]
axes[1, 1].bar(NAMES, loss, color=COLORS)
axes[1, 1].set(
    ylabel="Source-valid pixels lost to topo geometry (%)",
    title="Coverage loss and large topographic gains need review",
)
for i, n in enumerate(NAMES):
    gain = max(
        d["topo_factor"]["quantiles_0_1_25_50_75_99_100"][-1]
        for d in flights[n]["topographic_diagnostic_per_band"]
    )
    axes[1, 1].text(i, loss[i] + 0.13, f"Max gain {gain:.0f}×", ha="center", fontsize=9)
fig.suptitle(
    "Figure 5. No blanket winner: numerical consistency is not physical validation\nMatched polygons, identical pixels, spatial-blocked conditional comparisons; no pixel-random classification score.",
    fontsize=15,
)
finish(fig, "figure5_correction_performance.png")
# Compact proposed policy schematic, shared implementation and explicit gates.
fig, ax = plt.subplots(figsize=(15, 8))
ax.set(xlim=(0, 15), ylim=(0, 8))
ax.axis("off")


def box(x, y, w, h, text, color="#e6eef5", size=11):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=.12", facecolor=color, edgecolor="#526778"
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size)


def arrow(a, b):
    ax.annotate(
        "", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", lw=1.8, color="#526778")
    )


box(
    0.4,
    6.3,
    4.2,
    1,
    "Drone orthomosaic\nVerified grid + band-specific numeric recovery",
)
box(
    5.4,
    6.3,
    4.2,
    1,
    "NEON directional source\nVerify product level + documented calibration",
)
box(
    10.5,
    6.3,
    4.0,
    1,
    "Original drone photographs (future)\nCalibrate; recover rays + target overlap",
)
box(
    2.0,
    4.6,
    10.7,
    1,
    "Shared radiometric contract: verified physical affine mapping + provenance\nIf missing: retain labelled DN diagnostics; block physical libraries",
    color="#f6e9cb",
)
for x in [2.5, 7.5, 12.5]:
    arrow((x, 6.3), (x, 5.6))
box(
    0.5,
    2.5,
    4.2,
    1.3,
    "Topographic gate\nVerified illumination + terrain\nStable model, held-out checks",
    color="#dfeddf",
)
box(
    5.5,
    2.5,
    4.2,
    1.3,
    "Shared Ross–Li gate\nReal angles, rank 3, conditioning\nStable predictions + reference support",
    color="#dfeddf",
)
box(
    10.6,
    2.5,
    3.9,
    1.3,
    "Current drone result\nBRDF skipped: rank 1\nTopo held pending validation\nPhysical library held",
    color="#f2dede",
)
arrow((4, 4.6), (2.6, 3.8))
arrow((8, 4.6), (7.6, 3.8))
arrow((9.7, 3.15), (10.6, 3.15))
box(
    1,
    0.4,
    13,
    1.1,
    "Only outputs passing radiometry and selected-stage gates → QA → native physical library\nOptional translation only with compatible, independently validated coefficients; preserve immutable provenance",
    color="#e6eef5",
)
arrow((2.6, 2.5), (4, 0.4 + 1.1))
arrow((7.6, 2.5), (7.6, 1.5))
fig.suptitle(
    "Figure 6. Proposed policy: share the equations, require evidence at every stage",
    fontsize=17,
    y=0.97,
)
fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.91)
finish(fig, "figure6_recommended_pipeline.png")
print("Seven scientific figures generated")
