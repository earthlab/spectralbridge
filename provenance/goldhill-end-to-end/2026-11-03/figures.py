"""Figure-led matched-support report; display limits never alter measurements."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, SymLogNorm
import numpy as np
import pandas as pd
import rasterio
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
a = np.load(HERE / "display_arrays.npz")
summary = json.loads((HERE / "analysis_summary.json").read_text())
poly = pd.read_csv(HERE / "polygon_spectral_summaries.csv")
coverage = pd.read_csv(HERE / "stage_coverage.csv")
classification = pd.DataFrame(
    json.loads((HERE / "classification_summary.json").read_text())
)
waves = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
labels = {
    "old_raw": "Old raw",
    "old_reencoded_fixed": "Old, encoding recovered",
    "new_raw": "New raw",
    "old_topo": "Old SCS+C",
    "old_brdf": "Old BRDF",
    "old_combined": "Old combined",
    "new_historical_topo": "New + historical SCS+C",
    "new_historical_brdf": "New + historical BRDF",
    "new_historical_combined": "New + historical combined",
}
order = [
    "old_raw",
    "old_reencoded_fixed",
    "new_raw",
    "old_topo",
    "new_historical_topo",
    "old_brdf",
    "new_historical_brdf",
    "old_combined",
    "new_historical_combined",
]
plt.rcParams.update(
    {
        "font.size": 11,
        "figure.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
manifest = []


def save(fig, name, caption):
    fig.savefig(HERE / (name + ".png"), dpi=190, bbox_inches="tight")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(
            name=name,
            png=name + ".png",
            svg=name + ".svg",
            caption=caption,
            analytical_status="Uncalibrated numerical observations; historical corrected branches are diagnostic only",
        )
    )


def rgb(values, mask, lo, hi):
    out = np.clip((values.astype(float) - lo) / (hi - lo), 0, 1)
    out[~mask] = 1
    return out


oldsource = np.load(
    ROOT / "provenance/goldhill-original-source/2026-11-03/display_arrays.npz"
)
valid = a["new_mask"]
newrgb = a["new_raw_rgb"]
lo = np.quantile(newrgb[valid], 0.02, axis=0)
hi = np.quantile(newrgb[valid], 0.98, axis=0)
fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
original = oldsource["original_rgb"].astype(float) * 10000 / 65535
for ax, img, mask, title in [
    (axs[0], original, oldsource["original_mask"], "Original 8.44 cm"),
    (axs[1], a["old_raw_rgb"], a["old_mask"], "Historical 10 cm"),
    (axs[2], newrgb, valid, "New 10 cm"),
]:
    ax.imshow(rgb(img, mask, lo, hi))
    ax.set_title(title)
    ax.set_axis_off()
fig.suptitle(
    "What changed? Fixed numerical encoding and transparent-background exclusion",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.94))
save(
    fig,
    "figure01_sources",
    "Actual raw sources, RGB=650/560/475 nm. A common new-raw 2-98% RGB stretch is applied to all three after the explicit original-to-fixed numerical encoding. White is missing/transparent; no corrected image or physical calibration is implied.",
)

fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
axs[0].imshow(
    a["old_mask"].astype(int) + 2 * a["new_mask"].astype(int),
    vmin=0,
    vmax=3,
    cmap="viridis",
)
axs[0].set_title("Old/new source support")
delta = a["old_reencoded_fixed_red"] - a["new_raw_red"]
im = axs[1].imshow(
    delta, cmap="RdBu_r", norm=SymLogNorm(linthresh=0.1, vmin=-7500, vmax=7500)
)
axs[1].set_title("Old minus new, same encoding")
fig.colorbar(im, ax=axs[1], label="650 nm encoded units; symmetric log", shrink=0.8)
axs[2].imshow((abs(delta) > 2) & a["new_mask"], cmap="magma", vmin=0, vmax=1)
axs[2].set_title("Common-support difference >2 units")
for ax in axs:
    ax.set_axis_off()
fig.suptitle(
    "Background contamination is spatially concentrated at the observation boundary",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.92))
save(
    fig,
    "figure02_background",
    "All maps use the same grid/extent. Left codes: 0 missing both, 1 old-only, 2 new-only, 3 both. Middle uses the recovered fixed encoding, separating minimum normalization from interpolation/masks. The >2 display flag is a diagnostic threshold, not a scientific approval rule.",
)

fig, axs = plt.subplots(1, 4, figsize=(15, 4))
for ax, field, title, unit in zip(
    axs,
    ["slope", "aspect", "solar_zn", "solar_az"],
    [
        "Terrain slope",
        "Terrain aspect",
        "Inherited solar zenith",
        "Inherited solar azimuth",
    ],
    ["degrees", "degrees", "degrees", "degrees"],
):
    with rasterio.open(
        Path("/private/tmp/goldhill-end-to-end-20261103/ancillary")
        / f"legacy_{field}.tif"
    ) as src:
        im = src.read(1)[::6, ::6]
    im = np.where(a["new_mask"] & np.isfinite(im) & (im != -9999), im, np.nan)
    plot = ax.imshow(im, cmap="viridis")
    fig.colorbar(
        plot,
        ax=ax,
        shrink=0.75,
        label=unit,
        format="%.4f"
        if field == "solar_zn"
        else "%.3f"
        if field == "solar_az"
        else "%.0f",
    )
    ax.set_title(title)
    ax.set_axis_off()
fig.suptitle(
    "Available geometry is inherited provenance, not a newly verified flight solution",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.9))
save(
    fig,
    "figure03_ancillary",
    "Terrain/solar grids align with the new TIFF. Original photo tags now support the inherited August 15 scene timestamp despite the nominal August 14 package note/name. Explicit time-zone/clock validation and per-pixel camera assignments remain unresolved.",
)

fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
with rasterio.open(
    "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
) as src:
    raw = src.read()[..., ::6, ::6].transpose(1, 2, 0)
top = np.load(
    "/private/tmp/goldhill-end-to-end-20261103/historical_diagnostic/new_historical_topo.npy",
    mmap_mode="r",
)[::6, ::6]
factors = json.loads((HERE / "correction_factor_statistics.json").read_text())
for ax, b in zip(axs, [2, 4, 7]):
    f = np.divide(
        top[..., b],
        raw[..., b],
        out=np.full(raw.shape[:2], np.nan),
        where=np.isfinite(raw[..., b]) & (raw[..., b] > 0),
    )
    f[~a["common_mask"]] = np.nan
    plot = ax.imshow(f, norm=LogNorm(vmin=0.1, vmax=10), cmap="RdBu_r")
    rec = next(
        x
        for x in factors
        if x["branch"] == "new_historical_topo" and x["wavelength_nm"] == waves[b]
    )
    ax.set_title(f"{waves[b]} nm: native max {rec['maximum']:.1f}")
    ax.set_axis_off()
fig.colorbar(
    plot, ax=axs, shrink=0.8, label="Actual replay output / raw input", extend="both"
)
fig.suptitle(
    "Historical SCS+C stress replay: finite does not imply stable or physically valid",
    weight="bold",
)
save(
    fig,
    "figure04_scs_factors",
    "Only the unchanged historical implementation is replayed here; current production SCS+C is blocked by calibration. Color under/over triangles expose values beyond 0.1-10; analytical maxima are retained. The red maximum is 309.9 near a 0.001 denominator.",
)

camera = pd.read_csv(
    "/Users/tuff/Downloads/AOP-GOLDHILL-camera_locations.csv", skiprows=2
)
camera.columns = camera.columns.str.strip().str.removeprefix("# ")
poses = camera[["X", "Y", "Z"]].drop_duplicates()
fig, axs = plt.subplots(1, 2, figsize=(13, 4.5), gridspec_kw={"width_ratios": [1.1, 1]})
axs[0].scatter(poses.X, poses.Y, s=9, color="#2166ac")
axs[0].set(
    xlabel="Camera X (reported coordinates)",
    ylabel="Camera Y (reported coordinates)",
    title="565 supplied camera positions",
)
axs[0].ticklabel_format(useOffset=False, style="plain")
axs[0].tick_params(axis="x", rotation=20)
axs[1].axis("off")
axs[1].text(0.02, 0.9, "AVAILABLE", weight="bold", color="#2166ac")
axs[1].text(
    0.02,
    0.78,
    "5,650 band-specific pose records\n565 camera positions\nOrientation matrices / Omega / Phi / Kappa",
    va="top",
)
axs[1].text(0.02, 0.47, "MISSING OR UNRESOLVED", weight="bold", color="#b2182b")
axs[1].text(
    0.02,
    0.35,
    "CSV CRS label: 5070; values align with TIFF 26913\nPer-pixel contributing images and blend weights\nConfirmed time zone / angular / vertical conventions\nMeasured orthomosaic viewing-angle rasters",
    va="top",
)
fig.suptitle(
    "Camera poses are useful evidence, but do not yet define the mosaic BRDF design",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.91))
save(
    fig,
    "figure05_camera_support",
    "Points are shown in the reported coordinate numbers without silently relabeling the CRS or assigning footprints. Current source H5 deliberately has no sensor-view datasets. Historical zero-view controls are not treated as measured observations.",
)

fig, axs = plt.subplots(2, 4, figsize=(15, 8))
zoom = a["new_raw_zoom_rgb"]
mask = np.isfinite(a["new_raw_zoom_red"])
zlo = np.quantile(zoom[mask], 0.02, axis=0)
zhi = np.quantile(zoom[mask], 0.98, axis=0)
for i, name in enumerate(
    [
        "old_raw",
        "old_topo",
        "old_brdf",
        "old_combined",
        "new_raw",
        "new_historical_topo",
        "new_historical_brdf",
        "new_historical_combined",
    ]
):
    ax = axs.flat[i]
    v = a[name + "_zoom_rgb"]
    m = np.isfinite(a[name + "_zoom_red"])
    ax.imshow(rgb(v, m, zlo, zhi))
    ax.set_title(labels[name], fontsize=11)
    ax.set_axis_off()
fig.suptitle(
    "The red stripe is introduced by historical BRDF application, not removed by source repair",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.94))
save(
    fig,
    "figure06_red_stripe",
    "Same previously selected 50.1 x 40.1 m ROI, same RGB=650/560/475 nm and display limits. Historical corrections are unsupported diagnostics. Extremely large red values saturate this display; uncapped values and jumps are reported numerically.",
)

fig, axs = plt.subplots(
    1, 3, figsize=(15, 4.5), gridspec_kw={"width_ratios": [1, 1, 1.2]}
)
x = np.arange(840, 1120)
for name in ["old_raw", "new_raw"]:
    axs[0].plot(x, a[name + "_transect"], label=labels[name])
axs[0].set(
    title="Raw red values",
    xlabel="Native column, row 921",
    ylabel="650 nm encoded units",
)
axs[0].legend(fontsize=8)
axs[0].axvline(980.5, color="black", ls=":")
for name in ["old_brdf", "new_historical_brdf"]:
    axs[1].plot(x, a[name + "_transect"], label=labels[name])
axs[1].set(
    title="Historical BRDF replay",
    xlabel="Native column, row 921",
    ylabel="650 nm encoded units",
    yscale="symlog",
)
axs[1].legend(fontsize=8)
axs[1].axvline(980.5, color="black", ls=":")
b = pd.read_csv(HERE / "red_boundary_discontinuities.csv")
use = ["old_raw", "new_raw", "old_brdf", "new_historical_brdf"]
v = b.set_index("branch").loc[use]
axs[2].bar(
    np.arange(4), v.median_abs_jump, color=["#777", "#2166ac", "#b2182b", "#ef8a62"]
)
axs[2].set(
    xticks=np.arange(4),
    xticklabels=[labels[n] for n in use],
    yscale="log",
    ylabel="Median adjacent-pixel jump",
    title="2,934 fixed historical boundary edges",
)
axs[2].tick_params(axis="x", rotation=25)
fig.tight_layout()
save(
    fig,
    "figure07_boundary",
    "The raw fixed edge jump is 5.586 encoded units; the new historical-BRDF replay jumps 3.372 billion. Boundary edges were fixed from the old factor before new-branch evaluation. This is a mechanism replay, not a valid new BRDF fit.",
)

fig, axs = plt.subplots(1, 3, figsize=(15, 4.5))
means = {name: g.set_index("GlobalID") for name, g in poly.groupby("branch")}
columns = [f"b{i}" for i in range(1, 11)]
reference = means["new_raw"][columns]
angles = []
names = ["old_raw", "old_reencoded_fixed", "new_historical_topo", "new_historical_brdf"]
for name in names:
    X = means[name].loc[reference.index, columns].to_numpy()
    Y = reference.to_numpy()
    cos = np.sum(X * Y, axis=1) / (
        np.linalg.norm(X, axis=1) * np.linalg.norm(Y, axis=1)
    )
    angles.append(np.degrees(np.arccos(np.clip(cos, -1, 1))))
axs[0].boxplot(angles, tick_labels=[labels[n] for n in names], showfliers=True)
axs[0].set(
    ylabel="Angle to new raw polygon mean (degrees)",
    title="Representation versus correction",
)
axs[0].tick_params(axis="x", rotation=25)
x = means["old_reencoded_fixed"].loc[reference.index, "mean_band_variance"]
y = means["new_raw"].mean_band_variance
axs[1].scatter(x, y, s=12, alpha=0.6)
lim = [min(x.min(), y.min()), max(x.max(), y.max())]
axs[1].plot(lim, lim, color="black", ls=":")
axs[1].set(
    xscale="log",
    yscale="log",
    xlabel="Old, encoding recovered",
    ylabel="New raw",
    title="Within-polygon mean band variance",
)
names2 = ["old_reencoded_fixed", "new_raw", "new_historical_topo"]
axs[2].boxplot(
    [means[n].median_band_cv for n in names2], tick_labels=[labels[n] for n in names2]
)
axs[2].set(
    title="Within-polygon relative variability",
    ylabel="Median band coefficient of variation",
)
axs[2].tick_params(axis="x", rotation=25)
fig.tight_layout()
save(
    fig,
    "figure08_consistency",
    "All 157 polygons use identical valid pixels. Recovering the old encoding accounts for most raw spectral-angle change; the remaining median pixel angle is about 0.00077 degrees. Variance and CV are descriptive numerical metrics, not physical validation.",
)

fig, axs = plt.subplots(2, 2, figsize=(13, 7), sharex=True)
classes = sorted(poly.cover_category.unique())
for ax, label in zip(axs.flat, classes):
    for name, color in [
        ("old_raw", "#b2182b"),
        ("old_reencoded_fixed", "#777777"),
        ("new_raw", "#2166ac"),
    ]:
        values = poly[(poly.branch == name) & (poly.cover_category == label)][
            columns
        ].to_numpy()
        median = np.median(values, axis=0)
        ax.plot(waves, median, label=labels[name], color=color, marker="o", ms=3)
        if name == "new_raw":
            q = np.quantile(values, [0.25, 0.75], axis=0)
            ax.fill_between(waves, q[0], q[1], alpha=0.15, color=color)
    ax.set(
        title=f"{label} (n={len(values)} polygons)",
        xlabel="Wavelength (nm)",
        ylabel="Uncalibrated encoded units",
    )
axs[0, 0].legend(fontsize=8)
fig.suptitle(
    "Researcher-assigned cover labels preserved; no material-purity claim",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.94))
save(
    fig,
    "figure09_pft_spectra",
    "Class medians and new-raw polygon IQR on matched support. The gray inverse-encoding control nearly overlays the new source; NIR differences versus old raw mainly reflect the removed band-specific offset. Non-vegetated & dead is absent, not reassigned.",
)

between = pd.read_csv(HERE / "between_class_metrics.csv").query("branch == 'new_raw'")
cm = np.zeros((4, 4))
overlap = np.eye(4)
for _, row in between.iterrows():
    i = classes.index(row["first"])
    j = classes.index(row["second"])
    cm[i, j] = cm[j, i] = row.centroid_angle
    overlap[i, j] = overlap[j, i] = row.mean_band_IQR_overlap
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
short = ["Deciduous", "Evergreen", "Herbaceous", "Woody shrub"]
for ax, mat, title, cmap in [
    (axs[0], cm, "Class-centroid spectral angle (degrees)", "viridis"),
    (axs[1], overlap, "Mean band IQR overlap (descriptive)", "magma"),
]:
    plot = ax.imshow(mat, cmap=cmap)
    fig.colorbar(plot, ax=ax, shrink=0.8)
    ax.set(
        xticks=range(4),
        xticklabels=short,
        yticks=range(4),
        yticklabels=short,
        title=title,
    )
    ax.tick_params(axis="x", rotation=25)
    for i in range(4):
        for j in range(4):
            ax.text(
                j,
                i,
                f"{mat[i, j]:.2f}",
                ha="center",
                va="center",
                color="white" if mat[i, j] < mat.max() * 0.6 else "black",
            )
fig.tight_layout()
save(
    fig,
    "figure10_separability",
    "New-source polygon diagnostics: Evergreen/Herbaceous centroid shapes are only 1.07 degrees apart; Evergreen/Woody shrub has substantial IQR overlap. Distinct centroids or significant permutation tests do not establish reliable individual identification.",
)

fig, axs = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={"width_ratios": [1.6, 1]})
values = classification.set_index("branch").loc[order].balanced_accuracy.to_numpy()
colors = [
    "#888",
    "#aaa",
    "#2166ac",
    "#d8a659",
    "#ef8a62",
    "#b2182b",
    "#b2182b",
    "#884c80",
    "#884c80",
]
axs[0].barh(range(len(order)), values, color=colors)
axs[0].set(
    yticks=range(len(order)),
    yticklabels=[labels[n] for n in order],
    xlim=(0, 1),
    xlabel="Identity-weighted balanced accuracy",
    title="Actual package identification, fixed identical folds",
)
axs[0].invert_yaxis()
axs[0].axvline(0.25, color="gray", ls=":")
for i, v in enumerate(values):
    axs[0].text(v + 0.015, i, f"{100 * v:.1f}%", va="center", fontsize=9)
conf = pd.read_csv(HERE / "classification_confusion_new_raw.csv", index_col=0)
mat = conf.to_numpy() / conf.to_numpy().sum(1, keepdims=True)
plot = axs[1].imshow(mat, vmin=0, vmax=1, cmap="Blues")
axs[1].set(
    xticks=range(4),
    xticklabels=short,
    yticks=range(4),
    yticklabels=short,
    xlabel="Predicted",
    ylabel="Researcher label",
    title="New raw: held-out polygon recall",
)
axs[1].tick_params(axis="x", rotation=30)
for i in range(4):
    for j in range(4):
        axs[1].text(
            j,
            i,
            f"{100 * mat[i, j]:.0f}%",
            ha="center",
            va="center",
            color="white" if mat[i, j] > 0.55 else "black",
        )
fig.tight_layout()
save(
    fig,
    "figure11_identifiability",
    "157 non-overlapping polygon identities, three identical grouped folds, training-only standardization and fixed C=1. Old and new raw produce identical predictions and 66.8% balanced accuracy. Corrected bars are unsupported historical experiments; a higher score does not approve a correction.",
)

old = means["old_reencoded_fixed"].loc[reference.index]
new = means["new_raw"].loc[reference.index]
X = np.vstack([old[columns], new[columns]])
pca = PCA(2)
score = pca.fit_transform(StandardScaler().fit_transform(X))
n = len(new)
fig, ax = plt.subplots(figsize=(10, 5.5))
palette = ["#1b9e77", "#7570b3", "#d95f02", "#e7298a"]
for label, color in zip(classes, palette):
    use = new.cover_category.to_numpy() == label
    ax.scatter(
        score[:n][use, 0], score[:n][use, 1], marker="x", s=35, color=color, alpha=0.6
    )
    ax.scatter(
        score[n:][use, 0],
        score[n:][use, 1],
        marker="o",
        s=20,
        color=color,
        label=label,
        alpha=0.65,
    )
ax.set(
    xlabel=f"Joint PC1 ({pca.explained_variance_ratio_[0]:.1%})",
    ylabel=f"Joint PC2 ({pca.explained_variance_ratio_[1]:.1%})",
    title="Old fixed-encoding control (x) and new raw (o): nearly coincident structure",
)
ax.legend(fontsize=9)
save(
    fig,
    "figure12_pca",
    "One descriptive pooled standardized PCA basis on paired polygon means; this visualization is not part of classifier training. Both representations retain nearly the same structure. No independent physical accuracy, species purity or abundance claim follows.",
)
times = pd.read_csv(HERE / "camera_poses_with_photo_times.csv")
times["time"] = pd.to_datetime(times.timestamp_unzoned)
times["band"] = times.PhotoID.str.rsplit("_", n=1).str[-1].astype(int)
fig, ax = plt.subplots(figsize=(14, 4.5))
ax.scatter(times["time"], times.band, c=times.band, cmap="tab10", s=5, alpha=0.6)
ax.axvline(
    pd.Timestamp("2023-08-15 19:53:07"),
    color="#b2182b",
    label="Inherited scene solar timestamp",
)
ax.set(
    yticks=range(1, 11),
    ylabel="Band suffix in camera PhotoID",
    xlabel="Photo timestamp (time zone not stated in source CSV)",
    title="All 5,650 supplied camera records match unique August 15 photo timestamps",
)

ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
ax.legend(loc="lower right")
save(
    fig,
    "figure13_photo_times",
    "Matched camera records span 19:42:38-20:03:47 on August 15. The midpoint is 19:53:12.5, only 5.5 seconds from the inherited solar timestamp. Numerical agreement supports that timestamp; explicit clock/time-zone accuracy and mosaic pixel contributors are not established.",
)
(HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Thirteen figure pairs created")
