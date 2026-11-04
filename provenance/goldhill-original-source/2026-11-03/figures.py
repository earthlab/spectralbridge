"""Native-data displays with explicit numerical units and shared RGB limits."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "results.json").read_text())
a = np.load(HERE / "display_arrays.npz")
inv = r["candidate_inventory"]
waves = np.array(r["wavelengths_nm"])
plt.rcParams.update(
    {
        "font.size": 10,
        "figure.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
manifest = []


def save(fig, name, caption):
    fig.savefig(HERE / (name + ".png"), dpi=180, bbox_inches="tight")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(name=name, png=name + ".png", svg=name + ".svg", caption=caption)
    )


original = a["original_rgb"].astype(float)
v = a["original_mask"]
lo = np.quantile(original[v], 0.02, axis=0)
hi = np.quantile(original[v], 0.98, axis=0)
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
for ax, name, title in zip(
    axs.flat,
    ["original", "summer_float_25cm", "normalized_10cm", "new_fixed_10cm"],
    [
        "Original export · 8.44 cm UInt16",
        "Unnormalized aligned · 25 cm Float32",
        "Existing normalized · 10 cm Float32",
        "New fixed encoding · 10 cm Float32",
    ],
):
    rgb = a[name + "_rgb"].astype(float)
    if name in ["normalized_10cm", "new_fixed_10cm"]:
        rgb *= (
            65535 / 10000
        )  # RGB minima all zero: display-only inverse common multiplier.
    image = np.clip((rgb - lo) / (hi - lo), 0, 1)
    image[~a[name + "_mask"]] = 1
    ax.imshow(image)
    ax.set_title(title)
    ax.set_axis_off()
fig.suptitle(
    "Same source acquisition; common RGB 650/560/475 nm display stretch", weight="bold"
)
fig.tight_layout(rect=(0, 0, 1, 0.95))
save(
    fig,
    "figure01_rgb",
    "Uncorrected source versions; identical original-derived 2–98% display limits after inverse numerical encoding. Display clipping does not change analyses. Existing finite background is deliberately visible; the new copy honors source alpha.",
)

fig, axs = plt.subplots(2, 5, figsize=(15, 6))
for b, ax in enumerate(axs.flat, 1):
    xy = a[f"pair25_b{b}"]
    fit = r["comparisons"]["25cm_normalization"]["bands"][b - 1]
    ax.scatter(xy[0], xy[1], s=1, alpha=0.25, rasterized=True)
    xx = np.array([0, 65535])
    ax.plot(
        xx,
        xx * fit["expected_multiplier"] + fit["expected_offset"],
        color="#b2182b",
        lw=1,
    )
    ax.set(
        title=f"{waves[b - 1]} nm",
        xlabel="Unnormalized numerical DN",
        ylabel="Normalized stored value",
    )
    ax.text(
        0.04,
        0.9,
        f"a={fit['slope']:.6f}\nb={fit['offset']:.3f}",
        transform=ax.transAxes,
        fontsize=9,
    )
fig.suptitle(
    "Paired identical 25 cm grids: normalization is not original × 10,000",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.94))
save(
    fig,
    "figure02_band_relationships",
    "Scatter displays use deterministic subsets; fits and residuals use every finite pair. The 862 nm intercept is approximately −26.62 stored units.",
)

fig, axs = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
colors = {
    "original": "black",
    "normalized_10cm": "#b2182b",
    "new_fixed_10cm": "#2166ac",
}
labels = {
    "original": "Original DN / 65,535",
    "normalized_10cm": "Existing stored / 10,000",
    "new_fixed_10cm": "New stored / 10,000",
}
for i, ax in enumerate(axs):
    for name in colors:
        vals = np.array(r["representative_spectra"][name][i]["values"], float)
        vals[vals < 0] = np.nan
        vals /= 65535 if name == "original" else 10000
        ax.plot(
            waves,
            vals,
            marker="o",
            ms=3,
            label=labels[name],
            color=colors[name],
            alpha=0.8,
        )
    p = r["representative_spectra"]["original"][i]
    ax.set(
        title=f"E {p['easting']:.0f}, N {p['northing']:.0f}", xlabel="Wavelength (nm)"
    )
axs[0].set_ylabel("Numerical fraction · physical calibration unverified")
axs[1].legend(fontsize=8)
fig.suptitle(
    "Representative spectra at fixed map coordinates (nearest native pixel)",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.92))
save(
    fig,
    "figure03_spectra",
    "Point coordinates in EPSG:26913. Different native footprints/interpolation prevent exact pixel equivalence; none of the plotted fractions is certified physical reflectance.",
)

fig, axs = plt.subplots(1, 2, figsize=(12, 5))
for ax, name, title in zip(
    axs,
    ["normalized_10cm", "new_fixed_10cm"],
    [
        "Existing 10 cm: finite-data footprint",
        "New 10 cm: source-alpha-aware footprint",
    ],
):
    arr = a[name + "_rgb"][..., 0].astype(float)
    arr[~a[name + "_mask"]] = np.nan
    im = ax.imshow(arr, vmin=0, vmax=10000, cmap="viridis")
    ax.set_title(title)
    ax.set_axis_off()
fig.colorbar(im, ax=axs, label="650 nm numerical stored units (0–10,000)", shrink=0.8)
fig.suptitle(
    "Transparent original high-DN background must not become observed signal",
    weight="bold",
)
save(
    fig,
    "figure04_footprint",
    "Shared numerical limits show the difference between finite stored background and the original valid observation mask. No BRDF/topographic correction applied.",
)
(HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
