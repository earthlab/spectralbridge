"""Common-unit, fixed-contrast figures and fixed-pixel boundary measurements."""

import json
from pathlib import Path
import numpy as np
import rasterio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
manifest = json.loads((HERE / "experiment_manifest.json").read_text())
WORK = Path(manifest["work"])
mapping = json.loads(
    (
        ROOT
        / "provenance/drone-scale-confirmation/2026-10-30/verified_numeric_mapping.json"
    ).read_text()
)["goldhill"]["bands"]
minima = np.array([b["original_min"] for b in mapping])
mult = np.array([(b["original_max"] - b["original_min"]) / 10000 for b in mapping])
valid = np.load(WORK / "valid.npy")
factor = np.load(WORK / "red_factor.npy")
den = np.load(WORK / "red_denominator.npy")
raw = np.load(WORK / "normalized_raw.npy", mmap_mode="r")
source_valid_count = int(valid.sum())
for branch in ["normalized", "recovered", "hypothetical"]:
    for stage in ["raw", "topo", "brdf", "combined"]:
        values = np.load(WORK / (branch + "_" + stage + ".npy"), mmap_mode="r")
        valid &= np.isfinite(values).all(2)
        valid &= (values != -9999).all(2)
common_valid_count = int(valid.sum())
# Select the historical zero-contour crossing with vegetation on both sides,
# nearest the scene center. No outcome-dependent re-selection across branches.
boundary = (factor[:, :-1] > 1) != (factor[:, 1:] > 1)
ndvi = (raw[:, :, 9] - raw[:, :, 4]) / (raw[:, :, 9] + raw[:, :, 4] + 1e-12)
choose = (
    boundary & valid[:, :-1] & valid[:, 1:] & (ndvi[:, :-1] > 0.3) & (ndvi[:, 1:] > 0.3)
)
y, x = np.nonzero(choose)
assert len(y) > 0
idx = np.argmin((y - valid.shape[0] / 2) ** 2 + (x - valid.shape[1] / 2) ** 2)
cy, cx = int(y[idx]), int(x[idx])
y0, y1 = max(0, cy - 100), min(valid.shape[0], cy + 101)
x0, x1 = max(0, cx - 140), min(valid.shape[1], cx + 141)
roi = (slice(y0, y1), slice(x0, x1))
common = valid[roi]
with rasterio.open(
    Path(manifest["historical_flight"]) / "AOP_GOLDHILL_20230814__envi.img"
) as src:
    transform = src.transform
    west, north = transform * (x0, y0)
    east, south = transform * (x1, y1)
extent = [west, east, south, north]
branches = ["normalized", "recovered", "hypothetical"]
stages = ["raw", "topo", "brdf", "combined"]
labels = ["Existing normalized", "Recovered source DN", "Hypothetical DN / 32768"]
stage_labels = ["Raw", "Topographic only", "BRDF only", "Topographic + BRDF"]
rgb = [4, 3, 1]


def array(branch, stage):
    return np.load(WORK / (branch + "_" + stage + ".npy"), mmap_mode="r")


def equivalent(values, branch):
    values = np.asarray(values, dtype=float)
    if branch == "normalized":
        return values * mult + minima
    if branch == "hypothetical":
        return values * 32768
    return values


reference = equivalent(raw[roi], "normalized")
limits = np.percentile(reference[:, :, rgb][common], [2, 98], axis=0)


def draw(ax, values, branch, coords=True):
    dn = equivalent(values, branch)[:, :, rgb]
    image = np.clip((dn - limits[0]) / (limits[1] - limits[0]), 0, 1)
    image[~common] = [0.96, 0.96, 0.96]
    ax.imshow(image, extent=extent, origin="upper", interpolation="none")
    line_x = (transform * (cx + 0.5, cy + 0.5))[0]
    line_y = (transform * (cx + 0.5, cy + 0.5))[1]
    ax.plot(line_x, line_y, marker="+", color="white", ms=8, mew=1.2)
    ax.plot(line_x, line_y, marker="+", color="black", ms=6, mew=0.5)
    if coords:
        ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        ax.ticklabel_format(style="plain")
        ax.tick_params(labelsize=7)
    else:
        ax.set_axis_off()


fig, axes = plt.subplots(3, 4, figsize=(17, 10), layout="constrained")
for i, b in enumerate(branches):
    for j, s in enumerate(stages):
        ax = axes[i, j]
        draw(ax, array(b, s)[roi], b)
        if i == 0:
            ax.set_title(stage_labels[j], fontsize=12)
        if j == 0:
            ax.set_ylabel(labels[i] + "\nNorthing (m)", fontsize=10)
        if i == 2:
            ax.set_xlabel("Easting (m), NAD83 / UTM 13N", fontsize=8)
        if i == 0 and j == 0:
            ax.plot([west + 1, west + 6], [south + 1, south + 1], color="white", lw=4)
            ax.text(
                west + 3.5, south + 1.5, "5 m", ha="center", color="white", fontsize=9
            )
        if j == 3:
            # Native 0.1 m cells, nearest-neighbor display; identical inset everywhere.
            ins = ax.inset_axes([0.67, 0.04, 0.30, 0.30])
            values = array(b, s)[cy - 12 : cy + 13, cx - 12 : cx + 13]
            image = np.clip(
                (equivalent(values, b)[:, :, rgb] - limits[0])
                / (limits[1] - limits[0]),
                0,
                1,
            )
            ins.imshow(image, interpolation="none")
            ins.set_xticks([])
            ins.set_yticks([])
            ins.set_title(
                "Native 0.1 m pixels",
                fontsize=6,
                color="black",
                backgroundcolor="white",
            )
fig.suptitle(
    "Goldhill: reversing range normalization does not remove the red streak\nFixed historical coefficients and kernels; shared DN-equivalent display; + marks the same boundary pixel",
    fontsize=15,
)
fig.get_layout_engine().set(rect=(0, 0.045, 1, 0.94))
fig.text(
    0.5,
    0.012,
    "All rows: identical RGB 650 / 560 / 475 nm; common valid mask and raw-reference 2–98% RGB limits.\nHistorical BRDF model is invalid; hypothetical row does not establish physical calibration. No per-panel stretch.",
    ha="center",
    fontsize=9,
)
fig.savefig(HERE / "goldhill_radiometric_recovery_comparison.png", dpi=200)
fig.savefig(HERE / "goldhill_radiometric_recovery_comparison.pdf")
plt.close(fig)
# Second figure documents exact display equivalence after explicit conversion.
fig, axes = plt.subplots(1, 3, figsize=(14, 5), layout="constrained")
for ax, b, label in zip(axes, branches, labels):
    draw(ax, array(b, "combined")[roi], b)
    ax.set_title(label + "\nConverted to recovered-DN display units", fontsize=10)
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
fig.suptitle(
    "Equivalent-unit comparison: one fixed display normalization for all branches",
    fontsize=14,
)
fig.savefig(HERE / "goldhill_common_display_normalization.png", dpi=200)
plt.close(fig)
# A single fixed transect, perpendicular (horizontal) to this local boundary.
col = np.arange(x0, x1)
distance = (col - cx) * 0.1
fig, axes = plt.subplots(2, 1, figsize=(12, 8))
fig.subplots_adjust(left=0.10, right=0.98, bottom=0.16, top=0.86, hspace=0.28)
colors = dict(normalized="#222222", recovered="#e67e22", hypothetical="#1677bd")
for b, label in zip(branches, labels):
    for s, ls in [("raw", ":"), ("brdf", "--"), ("combined", "-")]:
        red = equivalent(array(b, s)[cy, x0:x1], b)[:, 4]
        red = np.where(valid[cy, x0:x1], red, np.nan)
        axes[0].plot(
            distance, red, color=colors[b], ls=ls, lw=1.3, label=label + " · " + s
        )
axes[0].set_yscale("symlog", linthresh=1000)
axes[0].set_ylabel("Red band, DN-equivalent\nsymlog above ±1000")
fig.legend(
    *axes[0].get_legend_handles_labels(),
    ncol=3,
    fontsize=7,
    loc="lower center",
    bbox_to_anchor=(0.5, 0.005),
)
axes[0].set_title("Same 0.1 m pixels; branch curves overlap after unit conversion")
axes[1].plot(distance, factor[cy, x0:x1], color="#a5212f")
axes[1].set_yscale("log")
axes[1].set_ylabel("Historical red BRDF factor")
axes[1].set_xlabel("Distance east of marked boundary pixel (m)")
for ax in axes:
    ax.axvline(0, color="gray", lw=1)
    ax.grid(alpha=0.2)
fig.suptitle(
    "Goldhill red-band transect: the unstable gain survives numerical recovery",
    fontsize=15,
)
fig.savefig(HERE / "goldhill_red_band_transect.png", dpi=200)
plt.close(fig)
fig, axes = plt.subplots(1, 3, figsize=(14, 5), layout="constrained")
vmax = float(np.ceil(np.log10(np.max(factor[valid]))))
for ax, label in zip(axes, labels):
    image = np.where(common, np.log10(factor[roi]), np.nan)
    im = ax.imshow(
        image, extent=extent, cmap="magma", vmin=0, vmax=vmax, interpolation="none"
    )
    ax.contour(
        np.arange(x0, x1) * 0.1 + transform.c + 0.05,
        transform.f - (np.arange(y0, y1) + 0.5) * 0.1,
        den[roi],
        levels=[0],
        colors="cyan",
        linewidths=0.7,
    )
    ax.set_title(label + "\nSame fixed model: identical factors", fontsize=10)
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.tick_params(labelsize=7)
fig.colorbar(im, ax=axes, label="log10 red-band gain (0 = ×1; 6 = ×1,000,000)")
fig.suptitle(
    "The historical model switches at a zero prediction (cyan contour)", fontsize=14
)
fig.savefig(HERE / "goldhill_brdf_correction_factors.png", dpi=200)
plt.close(fig)
# Matched strips on both sides over the same ROI rows; no vegetation reselection.
left = []
right = []
centers = []
for row in range(y0, y1):
    transitions = np.flatnonzero(boundary[row, x0 : x1 - 1]) + x0
    if len(transitions) == 0:
        continue
    c = int(transitions[np.argmin(abs(transitions - cx))])
    if abs(c - cx) > 75:
        continue
    for offset in range(3, 11):
        left_values, r = c - offset, c + 1 + offset
        if valid[row, left_values] and valid[row, r]:
            left.append((row, left_values))
            right.append((row, r))
            centers.append(c)
left = np.array(left)
right = np.array(right)
assert len(left) > 0
metrics = dict(
    roi=dict(
        row_start=y0,
        row_stop=y1,
        column_start=x0,
        column_stop=x1,
        extent_utm_m=extent,
        boundary_pixel=[cy, cx],
        selection="Nearest scene-center historical factor identity-to-gain crossing with NDVI > .3 on both adjacent pixels; fixed before comparing branches",
        transect_row=cy,
        rgb_wavelengths_nm=[650, 560, 475],
    ),
    boundary_metric="Across each ROI row, nearest historical gain-switch boundary within 75 columns of marked crossing; paired pixels 3..10 cells from either side. Absolute = median |R_right-R_left|; relative = absolute / median pooled |R|. Same locations all branches; no trimming.",
    paired_locations=int(len(left)),
    branches={},
    common_valid_pixels=common_valid_count,
    source_valid_pixels=source_valid_count,
    display=dict(
        units="recovered DN-equivalent",
        formula_normalized="S_corrected * (band_max-band_min)/10000 + band_min",
        formula_hypothetical="rho_corrected * 32768",
        limits_2_98_per_rgb=limits.tolist(),
        clipping="Display only, shared across all panels; analytical arrays unclipped",
    ),
    historical_fixed_model_factor_difference=0.0,
    no_brdf_control="recovered / topo",
)
for b in branches:
    metrics["branches"][b] = {}
    for s in stages:
        a = array(b, s)
        left_values = equivalent(a[left[:, 0], left[:, 1]], b)[:, 4]
        r = equivalent(a[right[:, 0], right[:, 1]], b)[:, 4]
        absolute = float(np.median(abs(r - left_values)))
        base = float(np.median(abs(np.r_[left_values, r])))
        metrics["branches"][b][s] = dict(
            absolute_discontinuity_dn_equivalent=absolute,
            relative_discontinuity=absolute / base,
            median_left_dn_equivalent=float(np.median(left_values)),
            median_right_dn_equivalent=float(np.median(r)),
            valid_paired_pixels=int(len(left_values)),
        )
# Full-scene equivalent red-output difference as a direct scale invariance check.
metrics["full_scene_red_invariance"] = {}
base = array("normalized", "combined")[:, :, 4].astype(float) * mult[4]
for b in ["recovered", "hypothetical"]:
    a = array(b, "combined")[:, :, 4].astype(float) * (
        32768 if b == "hypothetical" else 1
    )
    diff = abs(a[valid] - base[valid])
    rel = diff / np.maximum(abs(base[valid]), 1)
    metrics["full_scene_red_invariance"][b] = dict(
        max_abs_dn_equivalent=float(diff.max()),
        relative_error_quantiles_50_99_100=np.percentile(rel, [50, 99, 100]).tolist(),
    )
(HERE / "streak_comparison_metrics.json").write_text(
    json.dumps(metrics, indent=2, allow_nan=False) + "\n"
)
# Pick one pair near marked transect; all ten bands at identical positions.
idx = int(np.argmin(abs(left[:, 0] - cy) + abs(left[:, 1] - cx)))
pixels = [left[idx].tolist(), right[idx].tolist()]
fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
wave = [444, 475, 531, 560, 650, 668, 705, 717, 740, 862]
for ax, pixel, side in zip(axes, pixels, ["West side", "East side"]):
    row, col = pixel
    for b, label in zip(branches, labels):
        for s, ls in [("raw", "--"), ("combined", "-")]:
            y = equivalent(array(b, s)[row, col], b)
            ax.plot(
                wave,
                y,
                color=colors[b],
                ls=ls,
                marker="o",
                ms=3,
                label=label + " · " + s,
            )
    ax.set_yscale("symlog", linthresh=1000)
    ax.set_ylim(bottom=1)
    ax.set_title(f"{side}: row {row}, column {col}")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("DN-equivalent; symlog above ±1000")
    ax.grid(alpha=0.2)
axes[1].legend(fontsize=7)
fig.suptitle(
    "Same ground pixels: red amplification dominates the corrected spectra", fontsize=14
)
fig.savefig(HERE / "goldhill_spectral_comparison.png", dpi=200)
plt.close(fig)
# Offset effects are masked by pathological gains above; expose raw spectral relationships.
fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
for pixel, side in zip(pixels, ["West", "East"]):
    s = np.asarray(raw[pixel[0], pixel[1]], float)
    ax.plot(
        wave,
        s * mult[4],
        ls="--",
        label=side + ": uniform red-band multiplier (offset omitted)",
    )
    ax.plot(
        wave,
        s * mult + minima,
        marker="o",
        label=side + ": verified band-specific inverse",
    )
ax.set(
    xlabel="Wavelength (nm)",
    ylabel="Recovered source DN (physical units unverified)",
    title="Band-specific recovery restores the NIR offset; visible bands have zero offsets",
)
ax.legend(fontsize=8)
ax.grid(alpha=0.2)
fig.savefig(HERE / "goldhill_raw_spectral_offsets.png", dpi=200)
plt.close(fig)
print(json.dumps(metrics["branches"], indent=2))
