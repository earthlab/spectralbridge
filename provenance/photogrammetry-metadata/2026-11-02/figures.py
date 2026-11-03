"""Unified provenance/literature figures. All maps use actual file metadata/data."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
a = json.loads((HERE / "validation.json").read_text())
names = ["gordon", "goldhill", "ruby"]
colors = ["#287fa0", "#ca7a35", "#679653"]
plt.rcParams.update(
    {"font.size": 11, "axes.spines.top": False, "axes.spines.right": False}
)


def save(fig, name):
    fig.savefig(HERE / name, dpi=180)
    plt.close(fig)


def diagram(figsize=(17, 9)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    ax.set(xlim=(0, 17), ylim=(0, 9))
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.04, top=0.91)
    return fig, ax


def box(ax, x, y, w, h, text, color="#e5eef4", size=11):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=.13", facecolor=color, edgecolor="#506578"
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size)


def arrow(ax, start, end, **kw):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle="->", lw=1.6, color="#506578", **kw),
    )


fig, ax = diagram()
labels = [
    (
        "Original photographs",
        "Referenced SD1/SD2 paths\nCSV times/software retained\nRaw calibration/poses not recovered",
    ),
    (
        "Metashape 1.8.3",
        "Camera geometry estimated\nLens tables + reports exist\nRadiometric flags UNKNOWN",
    ),
    (
        "Original UInt16 TIFF",
        "10 spectral bands + alpha\nNAD83 / UTM 13N\nNo contributor/ray metadata",
    ),
    (
        "Resampling / normalization",
        "Verified bandwise 0–10,000\nExact exporter not recovered\nTerrain grids travel separately",
    ),
    (
        "Legacy H5 conversion",
        "Explicit zero view matrices\nMixed-unit PyEphem solar\nNo real camera contributors",
    ),
]
for i, (title, detail) in enumerate(labels):
    x = 0.2 + i * 3.4
    box(
        ax,
        x,
        6.2,
        3,
        1.7,
        title + "\n\n" + detail,
        color="#f4e9ce" if i == 1 else "#e5eef4",
        size=10,
    )
    if i < 4:
        arrow(ax, (x + 3, 7.05), (x + 3.4, 7.05))
box(
    ax,
    0.7,
    2.9,
    6.4,
    1.8,
    "Metadata not exported / not recovered\nProject poses, intrinsics, calibration flags,\nimage-to-ground mapping, selection/blend weights\nReports prove some geometry existed, not a ray export",
    color="#f3dede",
)
box(
    ax,
    8.1,
    2.9,
    8.1,
    1.8,
    "October 29 executed TIFF recipe → new working H5\nprepare_reference copies upstream zero views as scalars\n_compute_solar_geometry_arrays calculates NEW manifest solar\nNeonCube broadcasts the supplied scalar views",
    color="#dfeddf",
)
arrow(ax, (15.3, 6.2), (12.2, 4.7))
arrow(ax, (5.1, 6.2), (4, 4.7))
box(
    ax,
    2.5,
    0.4,
    12,
    1.2,
    "SpectralBridge correction → translation → polygon libraries\nHistorical Goldhill BRDF failure is downstream; current scientific gates reject unsupported fits",
    color="#e5eef4",
)
arrow(ax, (11.8, 2.9), (10.5, 1.6))
fig.suptitle(
    "Figure 1. Where geometry was omitted, assumed, inherited and recomputed",
    fontsize=18,
)
save(fig, "figure1_metadata_provenance.png")
fig, axes = plt.subplots(3, 3, figsize=(15, 9), layout="constrained")
for i, name in enumerate(names):
    with (
        h5py.File(a[name]["source_h5"]) as src,
        h5py.File(a[name]["working_h5"]) as dst,
    ):
        om = next(iter(src.values()))["Reflectance/Metadata"]
        wm = next(iter(dst.values()))["Reflectance/Metadata"]
        original = om["to-sensor_Zenith_Angle"][::20, ::20]
        scalar = float(wm["to-sensor_Zenith_Angle"][()])
        working = np.full(original.shape, scalar)
    for ax, values, title in zip(
        axes[i, :2],
        [original, working],
        ["Upstream H5: zero matrix", "Working H5: copied scalar, broadcast"],
    ):
        ax.imshow(values, vmin=0, vmax=30, cmap="viridis", interpolation="none")
        ax.set_title(name.title() + ": " + title, fontsize=10)
        ax.axis("off")
    axes[i, 2].axis("off")
    axes[i, 2].text(
        0.5,
        0.62,
        "Recovered camera/view map:\nNOT AVAILABLE",
        ha="center",
        va="center",
        transform=axes[i, 2].transAxes,
        color="#a73434",
        fontsize=14,
    )
    axes[i, 2].text(
        0.5,
        0.22,
        "Reports show estimated camera geometry.\nNo usable pose/contributor export was found.\nZero is a placeholder, not a measurement.",
        ha="center",
        transform=axes[i, 2].transAxes,
        fontsize=10,
    )
fig.suptitle(
    "Figure 2. Actual stored view zenith is 0° throughout; azimuth is also 0°\nNo recovered map is fabricated. Scalar validation establishes constancy, not observation geometry.",
    fontsize=15,
)
save(fig, "figure2_viewing_geometry.png")
solar = pd.read_csv(HERE / "solar_candidate_comparison.csv")
fig, axes = plt.subplots(2, 2, figsize=(15, 9), layout="constrained")
x = np.arange(3)
width = 0.23
oldzen = [a[n]["solar_replay"]["old_grid_zenith"]["q0_1_50_99_100"][2] for n in names]
for ax, field, title in [
    (axes[0, 0], "zenith", "Zenith: old unit bug versus new calculation"),
    (axes[0, 1], "azimuth", "Azimuth: old coordinate-unit bug versus new calculation"),
]:
    actual = (
        solar[solar.candidate == "manifest UTC (executed)"]
        .set_index("flight")
        .loc[names]
    )
    if field == "zenith":
        oldvalues = oldzen
    else:
        oldvalues = []
        for n in names:
            with h5py.File(a[n]["source_h5"]) as f:
                ds = next(iter(f.values()))[
                    "Reflectance/Metadata/Logs/Solar_Azimuth_Angle"
                ]
                oldvalues.append(float(ds[ds.shape[0] // 2, ds.shape[1] // 2]))
    ax.bar(
        x - width,
        oldvalues,
        width,
        color="#b4534e",
        label="Old upstream H5: known unit bugs",
    )
    ax.bar(
        x,
        actual["stored_" + field],
        width,
        color="#4d847b",
        label="Working H5: manifest NOAA",
    )
    ax.bar(
        x + width,
        actual["spa_" + field],
        width,
        color="#376c9c",
        label="Independent SPA, same UTC",
    )
    ax.set(
        xticks=x,
        xticklabels=[n.title() for n in names],
        ylabel="Angle (degrees)",
        title=title,
    )
    ax.legend(fontsize=8)
for ax, field in [(axes[1, 0], "zenith"), (axes[1, 1], "azimuth")]:
    for k, (label, color) in enumerate(
        [
            ("manifest UTC (executed)", "#376c9c"),
            ("notes Aug14 Denver", "#c47c32"),
            ("SD1 median as UTC", "#679653"),
        ]
    ):
        subset = solar[solar.candidate == label].set_index("flight").loc[names]
        ax.plot(x, subset[field + "_difference"], "o-", label=label, color=color)
    ax.axhline(0, color="gray", lw=1)
    ax.set(
        xticks=x,
        xticklabels=[n.title() for n in names],
        ylabel="Working minus SPA (degrees)",
        title="Candidate-time " + field + " residuals",
    )
    ax.legend(fontsize=8)
fig.suptitle(
    "Figure 3. Solar origin is traceable; acquisition dates are not yet authoritative\nOld bug replay: 75/75 sampled zenith and azimuth values exact. New NOAA replay: 75/75 exact; SPA differences ≈0.26° zenith.",
    fontsize=15,
)
save(fig, "figure3_solar_geometry.png")
fig, axes = plt.subplots(3, 3, figsize=(15, 10), layout="constrained")
for i, n in enumerate(names):
    d = np.load(HERE / (n + "_aligned_terrain_display.npz"))
    v = d["valid"]
    sl = d["stored_slope"]
    derived = d["derived_slope"]
    error = np.where(v, derived - sl, np.nan)
    for j, (image, title) in enumerate(
        [
            (np.where(v, sl, np.nan), "Stored slope"),
            (np.where(v, derived, np.nan), "Independent Horn on aligned DEM"),
            (error, "Derived minus stored slope"),
        ]
    ):
        im = axes[i, j].imshow(
            image,
            vmin=-10 if j == 2 else 0,
            vmax=10 if j == 2 else 70,
            cmap="coolwarm" if j == 2 else "terrain",
            interpolation="none",
        )
        axes[i, j].set_title(n.title() + ": " + title, fontsize=10)
        axes[i, j].axis("off")
        fig.colorbar(im, ax=axes[i, j], shrink=0.75, label="Degrees")
fig.suptitle(
    "Figure 4. Terrain can be checked, but the exact generating surface/toolchain remains unresolved\nSame aligned grid; median slope difference ≈1.1–1.3°. Native-export comparisons differ more; all residuals remain in tables.",
    fontsize=14,
)
save(fig, "figure4_terrain_geometry.png")
fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout="constrained")
for ax, n, color in zip(axes, names, colors):
    b = max(a[n]["topography_bands"], key=lambda b: b["max_gain_location"]["factor"])
    p = b["max_gain_location"]
    ax.bar(
        ["Numerator", "Denominator"],
        [p["numerator"], p["denominator"]],
        color=[color, "#bf584e"],
    )
    ax.set_yscale("log")
    ax.set_ylim(8e-4, 1)
    ax.set_title(n.title() + f": {p['factor']:.1f}× at {b['wavelength_nm']:.0f} nm")
    ax.text(
        0.5,
        0.73,
        f"cos(i) = {p['cosine_incidence']:.4f}\nC = {p['C']:.4f}\nDenominator = {p['denominator']:.6f}",
        ha="center",
        transform=ax.transAxes,
    )
    ax.set_ylabel("Dimensionless SCS+C term")
fig.suptitle(
    "Figure 4b. Exact gain mechanism: cosine incidence + fitted C nearly cancel\nTwo-parameter fit condition numbers 11–15; high gains do not require a rank-deficient topographic design.",
    fontsize=15,
)
save(fig, "figure4b_scs_denominators.png")
fig, ax = diagram((17, 8))
box(
    ax,
    0.5,
    5.6,
    4.5,
    2,
    "Original orthomosaic\nUInt16 numerical values\n10 spectral bands; range up to 65535\nPhysical encoding UNVERIFIED",
    color="#e5eef4",
)
box(
    ax,
    6.0,
    5.6,
    4.7,
    2,
    "Verified numerical normalization\nS = 10000 (DN − min) / (max − min)\nPer-band offsets matter\nNot a physical calibration",
    color="#f4e9ce",
)
box(
    ax,
    11.7,
    5.6,
    4.8,
    2,
    "Verified inverse recovery\nDN = min + S (max − min)/10000\nSource numerical representation\nNo guessed reflectance divisor",
    color="#dfeddf",
)
arrow(ax, (5, 6.6), (6, 6.6))
arrow(ax, (10.7, 6.6), (11.7, 6.6))
box(
    ax,
    0.8,
    2,
    7.1,
    2,
    "Measured band minima from original source TIFFs\nGordon: all zero\nGoldhill: NIR 174\nRuby: bands 1 / 2 / NIR = 4 / 3 / 297",
    color="#e5eef4",
)
box(
    ax,
    9.0,
    2,
    7,
    2,
    "Remaining physical-calibration gate\nPanel/DLS records + sensor/exposure metadata\nMetashape sensitivity/calibration + export settings\nColour balance / upstream normalization history",
    color="#f3dede",
)
fig.suptitle(
    "Figure 5. Numerical reversibility does not establish physical reflectance",
    fontsize=18,
)
save(fig, "figure5_radiometric_provenance.png")
fig, ax = diagram((17, 8))
for x, title, text, color in [
    (
        0.5,
        "Recoverable from existing files",
        "Exact zero-view lineage and software path\nOld solar algorithm fingerprint\nNew solar recomputation and candidate checks\nNumeric inverse + source grid/masks\nTerrain inputs and denominator mechanism",
        "#dfeddf",
    ),
    (
        6.1,
        "Needs matching Metashape project",
        "Camera transforms + intrinsics\nPanel / DLS / band-sensitivity flags\nActual processing and export settings\nSource-image selection / seam / blend data\nProject-to-export identity",
        "#f4e9ce",
    ),
    (
        11.7,
        "Needs original observations",
        "Calibrated photo values / exposure\nRepeated same-target viewing rays\nIllumination / occlusion consistency\nHeld-out target and angular validation\nPre-mosaic correction feasibility",
        "#e5eef4",
    ),
]:
    box(ax, x, 3.3, 4.8, 3.5, title + "\n\n" + text, color=color, size=11)
box(
    ax,
    2,
    0.6,
    13,
    1.3,
    "Inspect settings and a small overlapping subset first. Do not rebuild mosaics yet.\nOne blended pixel plus a viewing-angle map does not recreate its separate source observations.",
    color="#f3dede",
)
fig.suptitle(
    "Figure 6. Recover metadata first; reprocess photographs only if the evidence supports it",
    fontsize=18,
)
save(fig, "figure6_recovery_options.png")
fig, ax = diagram((17, 9))
box(ax, 0.3, 6.3, 3.3, 1.5, "Current route\nAlready mosaicked DN", color="#e5eef4")
box(ax, 4.2, 6.3, 3.6, 1.5, "Numeric normalization\n→ zero-view H5", color="#f4e9ce")
box(ax, 8.5, 6.3, 3.5, 1.5, "Post-mosaic Ross–Li\nRank 1: unsupported", color="#f3dede")
box(
    ax,
    12.7,
    6.3,
    3.8,
    1.5,
    "Preserve baseline\nHold physical promotion",
    color="#e5eef4",
)
for x, y in [(3.6, 4.2), (7.8, 8.5), (12, 12.7)]:
    arrow(ax, (x, 7.05), (y, 7.05))
box(
    ax,
    0.3,
    2.5,
    3.3,
    2.3,
    "Conditional alternative\nCalibrated raw photos\nPanel / DLS / sensor history\nAvoid duplicate corrections",
    color="#dfeddf",
)
box(
    ax,
    4.2,
    2.5,
    3.6,
    2.3,
    "Geometric photogrammetry\nCamera poses + intrinsics\nGround / visibility mapping\nSame-target overlap",
    color="#e5eef4",
)
box(
    ax,
    8.5,
    2.5,
    3.5,
    2.3,
    "BEFORE final mosaic\nBlock adjustment OR\nSupported angular model\nIndependent validation",
    color="#f4e9ce",
)
box(
    ax,
    12.7,
    2.5,
    3.8,
    2.3,
    "Final calibrated mosaic\nPreserved processing states\nSpectralBridge QA + library\nBRDF only if supported",
    color="#dfeddf",
)
for x, y in [(3.6, 4.2), (7.8, 8.5), (12, 12.7)]:
    arrow(ax, (x, 3.65), (y, 3.65))
ax.text(
    8.5,
    0.9,
    "Literature supports the observational design, not a guaranteed model or our unverified project settings.\nValidate PFT spectra, indices, held-out targets/angles and cross-sensor agreement—not only seam appearance.",
    ha="center",
    fontsize=13,
)
fig.suptitle(
    "Figure 7. What the UAV BRDF literature changes: correction stage and required observations",
    fontsize=17,
)
save(fig, "figure7_literature_pipeline.png")
print("Eight unified scientific figures generated")
