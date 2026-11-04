"""Rebuild paired illustrated reports from frozen evidence and native experiment arrays.

Run with the project scientific environment, then render_pdf.py with ReportLab.
All plotted clipping is display-only. No source or experimental arrays are altered.
"""

import csv
import textwrap
import json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rasterio
from matplotlib.patches import Rectangle
from matplotlib.colors import LogNorm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PART = ROOT / "provenance/brdf-artifact-anatomy-part-ii/2026-11-04"
PRIOR = ROOT / "provenance/goldhill-viewing-geometry/2026-11-04"
WORK = Path("/private/tmp/drone-integrated-reliability-20261104/final_v2")
W = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
A = np.load("/private/tmp/brdf-artifact-part-ii-20261104/report_arrays.npz")
G = np.load(
    "/private/tmp/goldhill-viewing-geometry-20261104/geometry_native.npy", mmap_mode="r"
)
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "figure.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
    }
)
COLORS = ["#163b4b", "#bc403d", "#318988", "#d09435", "#805e9d", "#3679ba"]
PAGES = {PART: [], HERE: []}
FIGURES = {PART: [], HERE: []}


def read(folder, name):
    return json.loads((folder / (name + ".json")).read_text())


def save(folder, name, fig):
    path = folder / "figures"
    path.mkdir(exist_ok=True)
    fig.savefig(path / (name + ".png"), dpi=210, bbox_inches="tight", facecolor="white")
    fig.savefig(path / (name + ".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    FIGURES[folder].append(name)
    return "figures/" + name


def page(folder, title, text, fig, caption):
    PAGES[folder].append(
        dict(
            title=title,
            paragraphs=text if isinstance(text, list) else [text],
            figure=fig,
            caption=caption,
        )
    )


def diagram(folder, name, labels, detail):
    fig, ax = plt.subplots(figsize=(12, 3.4))
    ax.axis("off")
    n = len(labels)
    for i, (label, sub) in enumerate(zip(labels, detail)):
        x = (i + 0.5) / n
        ax.text(
            x,
            0.65,
            label,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=14,
            color="white",
            bbox=dict(
                boxstyle="round,pad=.7", facecolor=COLORS[i % 6], edgecolor="none"
            ),
        )
        sub = "\n".join(textwrap.fill(line, 32) for line in sub.split("\n"))
        ax.text(
            x, 0.25, sub, ha="center", va="center", transform=ax.transAxes, fontsize=11
        )
        if i < n - 1:
            ax.annotate(
                "",
                xy=((i + 1.5) / n - 0.14, 0.48),
                xytext=((i + 0.5) / n + 0.14, 0.48),
                xycoords="axes fraction",
                arrowprops=dict(arrowstyle="->", lw=2, color="#86949a"),
            )
    return save(folder, name, fig)


def images(folder, name, items, cols=3, vmin=None, vmax=None, cmap="viridis", bar=None):
    rows = int(np.ceil(len(items) / cols))
    fig, axs = plt.subplots(
        rows, cols, figsize=(13, rows * 3.8), squeeze=False, layout="constrained"
    )
    im = None
    for ax, (label, data) in zip(axs.flat, items):
        label = (
            label.replace("conditioned combined cluster", "Combined")
            .replace("controlled cluster BRDF", "BRDF-only")
            .replace("conditioned topography", "Topographic-only")
            .replace("clean raw", "Raw")
        )
        label = textwrap.fill(label, 27)
        data = (
            np.sqrt(np.clip(np.asarray(data) / 0.25, 0, 1))
            if folder == PART and np.asarray(data).ndim == 3
            else data
        )
        im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title(label)
        ax.set_xticks([])
        ax.set_yticks([])
        if not bar and np.asarray(data).ndim == 2:
            fig.colorbar(im, ax=ax, shrink=0.65)
    for ax in list(axs.flat)[len(items) :]:
        ax.axis("off")
    if bar:
        fig.colorbar(im, ax=axs.ravel().tolist(), shrink=0.65, label=bar)
    return save(folder, name, fig)


branches = ["raw", "historical", "nearest", "central", "uniform", "weighted"]
labels = [
    "Raw candidate",
    "Historical replay",
    "A: nearest camera",
    "B: most central",
    "C: uniform kernels",
    "D: center-weighted kernels",
]
f = images(
    PART,
    "01_opening_rgb",
    [
        (labels[i], A[b + "_rgb_roi"])
        for i, b in enumerate(branches)
        if b in ["raw", "historical", "weighted"]
    ],
)
page(
    PART,
    "Anatomy of a Red Artifact, Part II",
    [
        "How We Reconstructed the Goldhill Drone BRDF Correction | November 2026",
        "The historical red line was a correction artifact. Recovering the numerical encoding and fitting population was necessary, but neither created missing angular information. Camera positions supplied an experimental directional design; it removed the historical pole without establishing physical calibration or true orthomosaic contributors.",
        "This companion follows five separate questions: what the numbers mean, which pixels entered the fit, whether the model can be estimated, what the corrected image contains, and whether vegetation evidence improves.",
    ],
    f,
    "Diagnostic RGB = 650/560/475 nm. All images use black 0, white 0.25 and gamma 0.5, with display saturation only. Candidate units assume DN/32768; calibration remains HYPOTHETICAL_UNVERIFIED. Native crop: rows 573:974, columns 812:1313, 10 cm pixels.",
)
f = diagram(
    PART,
    "02_encoding",
    ["Stored numbers", "Recovered DN", "Candidate reflectance"],
    [
        "S = 10000 (DN - min)/(65535 - min)",
        "DN = min + S(65535 - min)/10000",
        "R = DN/32768\nphysical interpretation unverified",
    ],
)
page(
    PART,
    "A numerical inverse is not a calibration",
    "The historical export removed a band minimum. Its inverse is an affine transformation, not a universal division by 10,000. The 862 nm minimum is 174 DN, so dropping the offset removes about 0.00531 candidate units. The clean source uses S = DN x 10000/65535 with zero offset. Its candidate multiplier is 0.0001999969482421875. Alpha-aware resampling is a separate repair that prevents transparent background entering interpolation.",
    f,
    "The stored-to-candidate contract is physical = scale x stored + offset. Numerical recovery is verified against paired source arrays; the final physical interpretation is conditional. Preserve per-band offsets and do not apply the decode twice.",
)
fig, axs = plt.subplots(2, 5, figsize=(14, 6), layout="constrained")
for ax, w in zip(axs.flat, W):
    x = A[f"stored_sample_{w}"]
    ax.hist(x[np.isfinite(x)], bins=np.geomspace(0.01, 10001, 85), color=COLORS[0])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(f"{w} nm")
    ax.axvspan(0.01, 2, color=COLORS[1], alpha=0.25)
    ax.set_xlabel("Historical stored value")
    ax.set_ylabel("Sampled pixels")
f = save(PART, "03_ten_band_encoding", fig)
page(
    PART,
    "Ten bands expose the unit mismatch",
    "A 0-2 eligibility rule applied to historical stored values selected only the extreme dark tail. It did not select a broad range of fractional reflectance. The ten-band distributions make the mismatch visible without treating plausible-looking values as calibration evidence.",
    f,
    "Deterministic sampled stored-value histograms; log axes. Red shading is the old stored-value 0-2 interval. Full-resolution counts are computed independently in eligibility_counts.json; histogram samples are not independent ecological observations.",
)
e = read(PART, "encoding_residuals")
fig, ax = plt.subplots(figsize=(12, 4.8))
for key, c in [
    ("10cm_inverse_forward_roundtrip", COLORS[0]),
    ("25cm_independent_file_equation", COLORS[2]),
]:
    rows = [r for r in e if r["test"] == key]
    if rows:
        ax.plot(
            [r["wavelength_nm"] for r in rows],
            [r["maximum"] for r in rows],
            "o-",
            label=key,
            color=c,
        )
ax.set(xlabel="Wavelength (nm)", ylabel="Maximum absolute stored-value residual")
ax.legend()
ax.grid(alpha=0.2)
f = save(PART, "04_encoding_residuals", fig)
page(
    PART,
    "The encoding equation survives independent checks",
    "The 10 cm inverse-forward round trip has maximum absolute residual 0.000299 stored units. A fresh comparison of the archived original and rescaled 25 cm H5 pair has maximum residual 0.000781 stored units. The H5 pair is the available archived equivalent, not a newly retrieved original TIFF. These errors are small numerical encoding residuals, not estimates of physical reflectance accuracy.",
    f,
    "Sources: encoding_residuals.json and numerical_evidence.csv. Full finite H5 support is retained for encoding tests; the clean alpha footprint is used for image science. The independent-pair test name is recorded in the JSON ledger.",
)
fig, axs = plt.subplots(1, 3, figsize=(13, 4.8), layout="constrained")
for ax, row in zip(axs, read(PART, "encoding_polygon_examples")):
    for key, label, c in [
        ("stored_fraction", "S/10000", COLORS[1]),
        ("recovered_candidate", "Recovered DN/32768", COLORS[0]),
        ("without_offset", "Offset omitted", COLORS[3]),
    ]:
        ax.plot(W, row[key], "o-", label=label, color=c)
    ax.set(
        title=row["PFT"], xlabel="Wavelength (nm)", ylabel="Numerical spectral value"
    )
    ax.legend(fontsize=8)
f = save(PART, "05_encoding_polygon_spectra", fig)
page(
    PART,
    "Scaling changes spectral evidence before correction",
    "Three fixed researcher polygons illustrate the representation change. Dividing the min-adjusted export by 10,000 produces a different numerical spectrum from recovering its original DN and applying the conditional physical interpretation. At 862 nm the missing offset is visible. Neither curve independently establishes which physical calibration was applied upstream.",
    f,
    "Median spectra from preselected polygons, with unchanged memberships. These representations are deliberately labeled separately; they are not interchangeable reflectance estimates.",
)
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
for ax, key, title in zip(
    axs,
    ["eligible_historical", "eligible_corrected"],
    ["Old filter: 14 native red pixels", "Unit-corrected controlled population"],
):
    ax.imshow(A[key], cmap="Greys", vmin=0, vmax=1, interpolation="nearest")
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    if key == "eligible_historical":
        ax.scatter(
            A["historical_eligible_cols"] / 4,
            A["historical_eligible_rows"] / 4,
            c=COLORS[1],
            s=22,
            marker="x",
        )
f = save(PART, "06_eligibility_maps", fig)
page(
    PART,
    "Correct the units before deciding who can enter the fit",
    "The controlled eligibility experiment increases the red-band sample from 14 to 6,678,404 pixels. The dots show the exact native locations because fourteen pixels can disappear in a reduced map. The core clean-source, zero-view branch separately contains 6,683,944 eligible pixels; the reconstructed terrain-valid native domain contains 6,683,905. These are distinct populations.",
    f,
    "Maps are reduced for display only. Counts use native masks. The controlled population includes its own ancillary intersection; it must not be substituted for the native reconstructed domain.",
)
counts = read(PART, "eligibility_counts")
fig, ax = plt.subplots(figsize=(12, 4.5))
x = np.arange(10)
ax.bar(
    x - 0.18,
    [r["historical"] + 0.1 for r in counts],
    0.36,
    label="Historical +0.1 for log display",
    color=COLORS[1],
)
ax.bar(
    x + 0.18,
    [r["controlled_corrected"] for r in counts],
    0.36,
    label="Correct physical-unit eligibility",
    color=COLORS[0],
)
ax.set_yscale("log")
ax.set_xticks(x, W)
ax.set_ylabel("Eligible native pixels (log scale)")
ax.set_xlabel("Wavelength (nm)")
ax.legend()
f = save(PART, "07_eligibility_counts", fig)
page(
    PART,
    "Millions of observations do not create missing angles",
    "Historical eligible counts range from zero to thirty across ten bands: 3, 1, 9, 13, 14, 30, 8, 4, 1 and 0. A larger fitting population repairs a severe sampling failure. With constant viewing geometry, however, the precision-aware stable rank remains one. Pixel count and the number of independently estimable directional terms are different quantities.",
    f,
    "Exact counts from the controlled eligibility experiment. The +0.1 display offset makes a zero count visible on the log axis; it is never used in a fit.",
)
f = diagram(
    PART,
    "08_rank_logic",
    ["Eligibility repaired", "Geometry fixed at zero", "Model unsupported"],
    [
        "Millions of valid source pixels",
        "No independent angular variation",
        "Stable rank 1 for 3 coefficients",
    ],
)
page(
    PART,
    "Separate the kernel repair from identifiability",
    "RossThick/LiDenseR mathematics had already been repaired and checked against independent equation-based fixtures. The shared kernel version is ross-li-reciprocal-f64-v1. Correct equations cannot recover missing observation geometry. An algebraic tiny singular value from numerical noise is not a second meaningful direction; the precision-aware rank test rejects that interpretation.",
    f,
    "The fixed-geometry experiment is a negative control. Revised equations and corrected filtering are necessary repairs, but this control is not a supported BRDF correction.",
)
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot([0, 4], [0, 0], color=COLORS[0], lw=3)
ax.plot([0.8, 2], [3, 0], color=COLORS[2], lw=2)
ax.plot([3.2, 2], [3, 0], color=COLORS[3], lw=2)
ax.scatter([0.8, 3.2], [3, 3], s=120, color=[COLORS[2], COLORS[3]])
ax.scatter([2], [0], s=100, color=COLORS[1])
ax.text(2, 0.2, "One orthomosaic observation", ha="center")
ax.text(0.8, 3.2, "Camera A", ha="center")
ax.text(3.2, 3.2, "Camera B", ha="center")
ax.text(2, 1.8, "Camera-to-ground rays\nposition + aligned terrain", ha="center")
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-0.2, 3.7)
ax.axis("off")
f = save(PART, "09_camera_ray_geometry", fig)
page(
    PART,
    "Positions support rays, not contributor identities",
    "Camera position and terrain define a candidate ground-to-camera direction. Nadir assumptions and nominal intrinsics determine eligibility and centering of footprints; they do not replace actual contributor maps. Orientation matrices and calibration rows exist, but their conventions, band bindings and vertical datum have not been verified. We therefore retain experimental assignments.",
    f,
    "Conceptual ray diagram, not a recovered exposure pair. Each ground pixel still supplies one measured orthomosaic spectrum. Simulating multiple kernels never creates repeated measured directional observations.",
)
f = images(
    PART,
    "10_view_geometry",
    [
        (name, np.array(G[::4, ::4, k]))
        for name, k in [
            ("A view zenith (degrees)", 0),
            ("A view azimuth (degrees)", 1),
            ("Eligible camera count", 6),
        ]
    ],
)
page(
    PART,
    "565 positions make a spatially varying angular design possible",
    "The recovered table contains 5,650 band records at 565 camera positions. All positions fall within the scene when coordinates are interpreted in the project-reported NAD83 / UTM 13N system. Treating the conflicting CSV label EPSG:5070 literally displaces the cameras by about 2,874 km. The interpretation and the unchanged source label are both preserved.",
    f,
    "Angle and count maps use separate named quantities and scales. A zenith ranges about 0-19 degrees. Camera counts range 4-221, median 84. Ground-to-sensor azimuth includes the documented grid-to-true-north adjustment of about -0.3184 degrees.",
)
f = diagram(
    PART,
    "11_assignment_strategies",
    ["A / B: one camera", "C: uniform kernels", "D: center weighted"],
    [
        "Nearest eligible / most central",
        "Average Kvol and Kgeo directly",
        "Weights proportional to exp(-2 centrality squared)",
    ],
)
page(
    PART,
    "Four assignments test assumptions rather than recover truth",
    "Nearest eligible and most central assignments differ on 25.83% of terrain-valid pixels. Uniform and center-weighted approaches average kernels over eligible cameras. Averaging angles first would describe a different model. All four strategies use the same observed spectrum once, the same shared kernels, and the same reference-geometry mathematics.",
    f,
    "Publication labels C and D correspond to code names C_uniform and C_center. Center weights are simulated geometric weights, not recovered Metashape blend weights. Smoothness and ecological accuracy are diagnostics, not selection rules.",
)
support = read(PRIOR, "design_support")
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
for row, c in zip(support, COLORS):
    axs[0].plot([1, 2, 3], row["singular_values"], "o-", label=row["scenario"], color=c)
axs[0].set_yscale("log")
axs[0].set(xlabel="Singular-value index", ylabel="Singular value")
axs[0].legend()
axs[1].bar(
    [r["scenario"] for r in support],
    [r["condition"] for r in support],
    color=COLORS[:4],
)
axs[1].set_ylabel("Native design condition number")
f = save(PART, "12_singular_values", fig)
page(
    PART,
    "The reconstructed design has rank three, conditionally",
    "All four full native designs pass the precision-aware rank-three test. Their condition numbers are roughly 98-182. This establishes a computationally estimable three-term regression under the assumed geometry. It does not establish that angular response, rather than spatially structured vegetation, explains the coefficients.",
    f,
    "Full native terrain-valid domain: 6,683,905 pixels. Singular values and conditions are read from design_support.json, not inferred from reduced plot samples. Effective independent observation count is not estimated.",
)
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
for k, label, c in [(14, "Uniform Ross", COLORS[0]), (18, "Weighted Ross", COLORS[2])]:
    d = np.asarray(G[::8, ::8, k])
    axs[0].hist(d[np.isfinite(d)], bins=70, alpha=0.5, label=label, color=c)
for k, label, c in [(15, "Uniform Li", COLORS[0]), (19, "Weighted Li", COLORS[2])]:
    d = np.asarray(G[::8, ::8, k])
    axs[1].hist(d[np.isfinite(d)], bins=70, alpha=0.5, label=label, color=c)
for ax in axs:
    ax.set(xlabel="Kernel value", ylabel="Sampled pixels")
    ax.legend()
f = save(PART, "13_kernel_distributions", fig)
page(
    PART,
    "Kernel blending changes the design itself",
    "Uniform and center-weighted kernels differ because eligible-camera geometry contributes with different weights. They are not additional radiometric observations. Angular support, reference prediction, prediction uncertainty and denominator positivity are checked before a model can be applied; no gain cap is used to create a visually acceptable result.",
    f,
    "Deterministic stride-eight native kernel samples. Counts in these histograms describe the sample, not an effective independent sample size. Full designs and model diagnostics remain in the source investigation.",
)
f = images(
    PART,
    "14_assignment_and_factor",
    [
        (labels[i], A[b + "_factor_roi_650"])
        for i, b in enumerate(branches)
        if b not in ["raw", "historical"]
    ],
    cols=2,
    vmin=0.5,
    vmax=1.5,
    bar="650 nm output/input factor; display limits 0.5-1.5",
)
page(
    PART,
    "Hard assignments can introduce their own seams",
    "Removing the historical pole does not make every reconstruction equivalent. At new assignment boundaries, the 99th-percentile red factor jump is about 0.498 for nearest and 0.589 for central assignments, compared with 0.0567 for uniform and 0.0265 for center-weighted kernels. These diagnostics favor continuity but cannot verify actual contributors.",
    f,
    "Identical native crop and factor display range. Out-of-range factors saturate only in this display. Exact distributions and seam metrics use uncapped native values; zeros in source are excluded from ratio diagnostics.",
)
f = images(
    PART,
    "15_full_scene_rgb",
    [(labels[i], A[b + "_rgb_full"]) for i, b in enumerate(branches)],
    cols=3,
)
page(
    PART,
    "The full scene preserves the same display contract",
    "The diagnostic red channel reveals the historical anomaly while reconstructed BRDF-only branches preserve broad spatial structure. The historical maximum applied red gain is 11,742,750 and the red-edge gain is about 115,554. A standard RGB using 668 nm can miss both damaged bands; wavelength selection must be explicit.",
    f,
    "Full scene, deterministic stride-four display. RGB 650/560/475 nm with shared black 0, white 0.25, gamma 0.5. Historical saturation is deliberately visible. Statistics and correction factors are never clipped.",
)
fig, axs = plt.subplots(2, 2, figsize=(13, 7), layout="constrained")
for row, w in enumerate([650, 717]):
    for b, label, c in zip(branches, labels, COLORS):
        for col in range(2):
            axs[row, col].plot(
                np.arange(840, 1120),
                A[f"{b}_transect_{w}"],
                label=label,
                color=c,
                lw=1.3,
            )
    axs[row, 0].set_yscale("symlog", linthresh=0.01)
    axs[row, 0].set_title(f"{w} nm: all numerical extremes")
    axs[row, 1].set_ylim(0, 0.5)
    axs[row, 1].set_title(f"{w} nm: detail, display 0-0.5")
    for ax in axs[row]:
        ax.axvline(980.5, color="grey", ls=":")
        ax.set_xlabel("Native column, row 921")
        ax.set_ylabel("Candidate reflectance")
axs[0, 0].legend(fontsize=8)
f = save(PART, "16_native_transects", fig)
page(
    PART,
    "The historical boundary jump collapses in the experiments",
    "At 2,936 fixed old-boundary edges, median red jump is 0.003079 in the raw image and about 630,821 in the historical replay. Reconstructed branches are approximately 0.00261-0.00348. The common location and native sampling isolate correction behavior from zoom or display choices.",
    f,
    "Left panels retain historical extremes on a symmetric log scale. Right panels deliberately show 0-0.5 detail and therefore omit the historical peaks from view; the full numerical trace remains alongside. No source values are clipped.",
)
d = read(PART, "factor_and_band_distributions")
fig, ax = plt.subplots(figsize=(13, 4.8))
heat = np.array(
    [
        [
            next(
                r["factor"]["quantiles"][4]
                for r in d
                if r["branch"] == b and r["wavelength_nm"] == w
            )
            for w in W
        ]
        for b in branches
    ]
)
im = ax.imshow(heat, norm=LogNorm(vmin=0.1, vmax=1e7), cmap="magma", aspect="auto")
ax.set_xticks(range(10), W)
ax.set_yticks(range(6), labels)
ax.set_xlabel("Wavelength (nm)")
fig.colorbar(im, ax=ax, label="Median output/input factor (log color)")
f = save(PART, "17_ten_band_factors", fig)
page(
    PART,
    "Check every band, not only the visible streak",
    "The numerical ledger contains native factor and reflectance distributions for all ten wavelengths and all six branches. The historical red and red-edge multipliers are abnormal, but other wavelengths must also be inspected for spectral shape and preservation. Float32 output/input ratios can differ by one unit in the last place from the applied historical gain.",
    f,
    "Median factors on logarithmic color. Exact minimum, maximum and quantiles are stored in factor_and_band_distributions.json. This plot summarizes the median; it does not replace extreme-value checks.",
)
e = read(PART, "exemplar_median_spectra")
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
for b, label, c in zip(branches, labels, COLORS):
    for ax in axs:
        ax.plot(W, e[b]["median"], "o-", label=label, color=c, lw=1.5)
        ax.fill_between(W, e[b]["q25"], e[b]["q75"], color=c, alpha=0.09)
axs[0].set_yscale("symlog", linthresh=0.01)
axs[0].set_title("Historical extremes retained")
axs[1].set_ylim(0, 0.45)
axs[1].set_title("Reconstructed spectrum detail")
for ax in axs:
    ax.set(xlabel="Wavelength (nm)", ylabel="Median candidate reflectance")
axs[0].legend(fontsize=8)
f = save(PART, "18_deciduous_median_IQR", fig)
page(
    PART,
    "A fixed aspen polygon keeps its identity",
    "The same Deciduous Populus tremuloides polygon crosses the established diagnostic area. Its 6,089 memberships are unchanged in this companion comparison. Median spectra and within-polygon interquartile bands show that removing the historical red/red-edge anomaly preserves the expected ordering of this observed spectrum under the candidate calibration.",
    f,
    "GlobalID {3A6D6E1D-3581-49B8-9321-397DFE5298C5}. Shading is pixel IQR within one polygon, not a confidence interval or independent replication. Classifier evaluations elsewhere use mean spectra, not these plotted medians.",
)
with (PART / "polygon_median_spectra.csv").open() as s:
    rows = list(csv.DictReader(s))
fig, axs = plt.subplots(2, 2, figsize=(13, 7), layout="constrained")
for ax, pft in zip(axs.flat, ["Deciduous", "Evergreen", "Herbaceous", "Woody_shrub"]):
    for b, c in [("raw", COLORS[0]), ("nearest", COLORS[2]), ("weighted", COLORS[5])]:
        selected = [
            r
            for r in rows
            if r["PFT"].replace(" ", "_").lower() == pft.lower() and r["branch"] == b
        ]
        if selected:
            y = np.array([[float(r[f"median_{w}"]) for w in W] for r in selected])
            ax.plot(W, np.median(y, 0), "o-", label=f"{b} (n={len(y)})", color=c)
            ax.fill_between(
                W, *np.quantile(y, [0.25, 0.75], axis=0), color=c, alpha=0.12
            )
    ax.set(
        title=pft.replace("_", " "),
        xlabel="Wavelength (nm)",
        ylabel="Median of polygon medians",
    )
    ax.legend(fontsize=8)
f = save(PART, "19_PFT_spectra", fig)
page(
    PART,
    "Vegetation categories remain descriptive evidence",
    "The researcher-assigned comparison comprises 157 identities: 98 Evergreen, 29 Woody shrub, 25 Herbaceous and only 5 Deciduous. Equal polygon summaries prevent the largest polygon from becoming the class profile. Between-polygon dispersion and the very small Deciduous sample limit generalization.",
    f,
    "Lines are class medians of polygon median spectra; bands are the between-polygon IQR. These are descriptive spectral profiles, not corrected-output-selected training strata or tests of physical calibration.",
)
pg = read(PRIOR, "paired_gain")
fig, ax = plt.subplots(figsize=(12, 4.6))
valid = [r for r in pg if r["branch"] != "clean_raw"]
for i, r in enumerate(valid):
    ax.errorbar(
        100 * r["difference"],
        i,
        xerr=[
            [100 * (r["difference"] - r["low"])],
            [100 * (r["high"] - r["difference"])],
        ],
        fmt="o",
        color=COLORS[i % 6],
    )
ax.axvline(0, color="grey", ls=":")
ax.set_yticks(range(len(valid)), [r["branch"] for r in valid])
ax.set_xlabel("Paired balanced-accuracy difference from raw (percentage points)")
f = save(PART, "20_paired_ecology", fig)
page(
    PART,
    "The ecological gains are not decisive",
    "Mean-spectrum PFT classification uses the same 157 identities, 144,406 memberships and frozen folds. Raw balanced accuracy is 66.83%; nearest and central are about 69.81% and 69.46%. Every reconstructed branch has a paired interval including zero. This is evidence of no demonstrated improvement at the present sample size, not proof of equivalence.",
    f,
    "Class-stratified paired polygon bootstrap, frozen evaluation protocol. Directional rank, visual continuity and classification accuracy answer different questions. Neither smoothness nor the largest accuracy value selects a physically valid reconstruction.",
)
f = diagram(
    PART,
    "21_remaining_dependencies",
    ["Numerical recovery", "Experimental geometry", "Physical validation"],
    [
        "Encoding and eligibility supported",
        "Rank 3; true contributors unknown",
        "Need applied calibration + repeated targets",
    ],
)
page(
    PART,
    "What is repaired, and what remains unresolved",
    [
        "The five-step causal chain is now explicit: a reversible encoding error distorted units; filtering selected almost no observations; fixed viewing geometry left the model unsupported; reconstructed rays supplied a conditional rank-three design; experimental images removed the historical pole without proving physical identifiability.",
        "The subsequent integrated-reliability experiment retains SCS+C and introduces explicit unsupported-illumination masks. It reports both native and matched-domain extremes. It does not convert the reconstructed geometry or DN/32768 into verified physical inputs.",
        "Reproduce from collect_evidence.py, build_publications.py and render_pdf.py. The 157-row numerical_evidence.csv records value, population, calculation, source path and hash. input_manifest.json binds frozen inputs. Original reports, labels and libraries remain untouched.",
    ],
    f,
    "Companion baseline: November 4 viewing-geometry investigation. Subsequent engineering results are in Toward a Reliable Drone Correction Pipeline. Request the existing 40-photo/four-position subset, sensor/pose bindings, datum, calibration/export settings and contributor information; do not request an entire archive before testing that subset.",
)

# Integrated engineering report: new native products, controlled evaluations, implementation.
raw = np.load(
    "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
    mmap_mode="r",
)
products = read(HERE, "pipeline_results")
arrays = {r["branch"]: np.load(r["array"], mmap_mode="r") for r in products}
arrays["clean_raw"] = raw
roi = np.s_[573:974, 812:1313]


def rgb(data):
    x = np.array(data[::4, ::4, :][..., [4, 3, 1]], float)
    x[(x < -100) | ~np.isfinite(x)] = np.nan
    return np.sqrt(np.clip(x / 0.25, 0, 1))


keys = [
    "clean_raw",
    "conditioned_topography",
    "controlled_cluster_BRDF",
    "conditioned_combined_cluster",
]
f = images(
    HERE,
    "01_full_scene_products",
    [(b.replace("_", " "), rgb(arrays[b])) for b in keys],
    cols=2,
)
page(
    HERE,
    "Toward a Reliable Drone Correction Pipeline",
    [
        "Radiometry, Viewing Geometry, BRDF, and Topography | Goldhill | November 2026",
        "Seven actual experimental GeoTIFF products were generated with the package correction driver. New opt-in fitting masks, spatial-cluster uncertainty and conditioned SCS+C make unsupported observations explicit. Both topographic and BRDF stages remain active in the combined products.",
        "This is partial engineering success. Physical calibration and actual orthomosaic contributors remain unverified; spatial controls show the global directional regression can capture vegetation structure. None of these products is approved for production or spectral-library extraction.",
    ],
    f,
    "RGB 650/560/475 nm; fixed black 0, white 0.25, gamma 0.5. Identical full-scene extents, stride-four display; metrics use native pixels. Display saturation never changes the analysis.",
)
f = diagram(
    HERE,
    "02_pipeline_contract",
    ["Decode once", "Fit with provenance", "Apply with status"],
    [
        "Per-band scale + offset\ncalibration gate retained",
        "Source mask + geometry + groups\ntraining separate from application",
        "Missing / unsupported / corrected\nEXPERIMENTAL output metadata",
    ],
)
page(
    HERE,
    "Small reusable repairs preserve the existing workflow",
    "The package now accepts explicit BRDF fitting subsets and optional spatial uncertainty groups, preserving the shared RossThick/LiDenseR equations and reference geometry. A new conditioned SCS+C model binds source identity, radiometry, wavelength order, policy and fit support. Default NEON behavior is unchanged. Experimental metadata survives ENVI serialization and prevents entry into approved spectral-library workflows.",
    f,
    "Implementation: topographic.py; surgical additions in corrections.py, pipelines/drone.py, envi_writer.py and radiometry.py. No separate drone kernel formulation or ordinary pixel-scale Parquet cache is introduced. Both correction stages remain ordered and file based.",
)
f = diagram(
    HERE,
    "03_radiometric_evidence",
    ["Verified numerical", "Conditional physical", "Unavailable evidence"],
    [
        "Inverse min-adjusted encoding\nzero-offset clean-source decode",
        "DN/32768 candidate\nHYPOTHETICAL_UNVERIFIED",
        "Applied panel/DLS calibration\nMetashape radiometric/export settings",
    ],
)
page(
    HERE,
    "Radiometry: preserve the uncertainty that metadata cannot resolve",
    "Existing data-store collections, local project paths and calibration metadata were searched. The retrieved calibration sample is a 2021 TIFF, not the 2023 Goldhill source. Its MicaSense radiance and lens tags demonstrate available metadata types but cannot certify Goldhill calibration. No original Goldhill project or raw-photo collection was recovered in the searched locations. Their absence elsewhere is not established.",
    f,
    "Radiometric validation: min-adjusted inverse VERIFIED numerically; clean alpha-aware resampling VERIFIED numerically; per-band affine application TESTED; DN/32768 INFERRED, not physically verified; applied Goldhill panel/DLS chain UNSUPPORTED by currently available records. See calibration_sample_metadata.json and input manifests.",
)
f = images(
    HERE,
    "04_geometry_and_kernels",
    [
        (name, np.array(G[::4, ::4, k]))
        for name, k in [
            ("Nearest viewing zenith (deg)", 0),
            ("Viewing azimuth (deg)", 1),
            ("Uniform RossThick", 14),
            ("Uniform LiDenseR", 15),
            ("Center-weighted RossThick", 18),
            ("Center-weighted LiDenseR", 19),
        ]
    ],
    cols=3,
)
page(
    HERE,
    "Viewing geometry remains an explicitly reconstructed input",
    "The four previous assignment strategies remain available, including hard assignment and direct kernel blending. Reported intrinsics and orientation matrices cannot be promoted to verified contributor geometry without sensor binding and convention checks. The integrated experiments use the previously declared center-weighted kernels as a fixed sensitivity scenario, not a recovered source-image solution.",
    f,
    "All panels use the same spatial extent. Named quantities have separate scales. Nearest/central seams and four-scenario conditioning are quantified in the companion and source investigation. No new actual-contributor strategy was fabricated.",
)
sc = read(HERE, "spatial_control_results")
fig, ax = plt.subplots(figsize=(13, 6.7))
names = []
coef = []
se = []
for r in sc:
    fit = next((v for v in r["fits"] if v["band"] == 4), None)
    if fit and "diagnostic_coefficient_estimate" in fit:
        names.append(r["case"] + (" [rejected]" if r["status"] != "VALID" else ""))
        coef.append(fit["diagnostic_coefficient_estimate"][1])
        se.append(fit.get("coefficient_standard_errors", [0, 0, 0])[1])
ax.errorbar(
    coef, np.arange(len(coef)), xerr=1.96 * np.array(se), fmt="o", color=COLORS[0]
)
ax.set_yticks(range(len(names)), names, fontsize=8)
ax.set_xlabel("650 nm Ross coefficient; conditional +/- 1.96 SE")
ax.grid(axis="x", alpha=0.2)
f = save(HERE, "05_spatial_coefficients", fig)
page(
    HERE,
    "Spatial and class subsets challenge the global fit",
    "Twenty-seven sampled controls compare spatial blocks, flight legs, terrain and incidence strata, camera footprints, vegetation classes and raw-defined homogeneous areas. Flight-leg holdout 2, Herbaceous and camera footprint 241 are rejected. Unsupported fits are retained as diagnostics rather than forced into corrected products. Class-specific coefficients are never used in the evaluated image corrections.",
    f,
    "Native stride-ten sample, no averaging. Diagnostic coefficient estimates may be shown for rejected fits, but no usable correction coefficients are exported for them. Intervals describe conditional regression uncertainty, not a physically identified BRDF or independent pixel replication.",
)
sh = read(HERE, "spatial_shift_controls")
fig, ax = plt.subplots(figsize=(12, 4.5))
ax.plot(
    [r["column_shift_native_pixels"] * 0.1 for r in sh],
    [r["R2"] for r in sh],
    "o-",
    color=COLORS[1],
)
ax.set(
    xlabel="Horizontal displacement of reflectance relative to kernels (m)",
    ylabel="650 nm regression R-squared",
)
ax.grid(alpha=0.2)
f = save(HERE, "06_spatial_displacement", fig)
page(
    HERE,
    "A displaced signal fits about as well as the original",
    "The unshifted sampled regression has R-squared 0.1049. Displacing reflectance 25 m produces 0.1144, and 50 m produces 0.1105. Similar or better fit after displacing the signal is a warning that broad spatial vegetation structure can explain apparent angular relationships. This is a sensitivity control, not a permutation p-value or proof that every angular effect is spurious.",
    f,
    "Whole-image horizontal displacement control; details in spatial_shift_controls.json and sampling_contract.json. Native shifts are 0, 250, 500, 750 and 1000 pixels at 10 cm. No corrected-output or classification tuning chooses the displacement.",
)
f = diagram(
    HERE,
    "07_homogeneous_training",
    ["Raw target criterion", "Excluded evaluation area", "Conditional fit"],
    [
        "NDVI > 0.5\n31 x 31 window complete\nred/NIR CV < 0.15",
        "Original polygons plus 20-step\nManhattan dilation (~2 m axes)",
        "20 m spatial clusters\nsame shared kernels and reference",
    ],
)
page(
    HERE,
    "Homogeneous training is a control, not a cure for missing repeats",
    "Raw-defined homogeneous pixels support a separate full-native BRDF and combined run. The criterion is fixed before ecological evaluation and uses no corrected imagery or class labels. Evaluation polygons and a 20-iteration Manhattan pixel buffer are excluded from fitting. The buffer reaches 2 m along the axes; it is not a Euclidean-radius dilation.",
    f,
    "Both homogeneous products executed. Cluster covariance changes uncertainty, not the OLS point estimate; the controlled OLS and cluster variants produce identical corrections when both pass acceptance. Homogeneity does not supply distinct measurements of the same target from multiple angles.",
)
model = read(HERE, "conditioned_scsc_model")
fig, ax = plt.subplots(figsize=(12, 4.5))
c = np.array([r["C"] for r in model["fits"]])
ci = np.array([r["C_interval"] for r in model["fits"]])
ax.errorbar(W, c, yerr=[c - ci[:, 0], ci[:, 1] - c], fmt="o-", color=COLORS[0])
ax.axhline(0, color="grey", ls=":")
ax.set(
    xlabel="Wavelength (nm)",
    ylabel="SCS+C parameter C; conditional 95% Fieller interval",
)
f = save(HERE, "08_C_uncertainty", fig)
page(
    HERE,
    "Diagnose the SCS+C denominator before applying a gain",
    "SCS+C multiplies observed reflectance by (cos(solar zenith) cos(slope) + C)/(cos(incidence) + C). Negative fitted C values can place a pole inside the illumination domain. An identity fallback below a threshold leaves a discontinuity and can retain huge gains immediately above it. We retain SCS+C and classify unresolved observations explicitly instead.",
    f,
    "The new policy fits slopes at least 5 degrees and positive incidence with candidate source values 0-2. OLS intercept/slope gives C. Twenty-metre spatial cluster covariance and Fieller ratio intervals identify whether C is bounded. Policy choices are explicit experimental decisions, not universal terrain thresholds.",
)

geo = {}
for n in ["slope", "aspect", "solar_zn", "solar_az"]:
    with rasterio.open(
        "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_" + n + ".tif"
    ) as s:
        geo[n] = s.read(1)[::4, ::4].astype(float) * np.pi / 180
ci = np.cos(geo["solar_zn"]) * np.cos(geo["slope"]) + np.sin(geo["solar_zn"]) * np.sin(
    geo["slope"]
) * np.cos(geo["solar_az"] - geo["aspect"])
ref = np.cos(geo["solar_zn"]) * np.cos(geo["slope"])
den = ci + c[7]
geomask = np.isfinite(G[::4, ::4, 0])
ci = np.where(geomask, ci, np.nan)
den = np.where(geomask, den, np.nan)
status = np.load(WORK / "topographic_status.npy", mmap_mode="r")
topo = arrays["conditioned_topography"]
combined = arrays["conditioned_combined_cluster"]
brdf = arrays["controlled_cluster_BRDF"]


def ratio(a, b):
    a = np.array(a[::4, ::4, 7], float)
    b = np.array(b[::4, ::4, 7], float)
    return np.divide(
        a,
        b,
        out=np.full_like(a, np.nan),
        where=(a > -100) & (b > 0) & np.isfinite(a) & np.isfinite(b),
    )


f = images(
    HERE,
    "09_topographic_support",
    [
        ("Cosine of local incidence", ci),
        ("717 nm denominator: cos(i)+C", den),
        ("717 nm source status", np.array(status[::4, ::4, 7])),
    ],
    cols=3,
)
page(
    HERE,
    "A resolved uncertainty interval defines the supported domain",
    "Application requires positive incidence, fitted incidence support and positive numerator and denominator across the complete conditional C interval. The existing 0.001 numerical resolution floor remains explicit. Unsupported observations become NoData with status 1; missing or invalid source observations are status 0; corrected observations are status 2. No identity substitution or gain cap is used.",
    f,
    "Denominator uses the fitted 717 nm C, not a display-derived value. Incidence uses the shared degree-to-radian convention. Status map is discrete. Flat terrain is handled analytically. These conditions bound numerical support; they do not independently verify DEM, illumination or calibration.",
)
f = images(
    HERE,
    "10_correction_factors",
    [
        ("Topographic-only / raw", ratio(topo, raw)),
        ("BRDF-only / raw", ratio(brdf, raw)),
        ("Combined / raw", ratio(combined, raw)),
    ],
    cols=3,
    vmin=0,
    vmax=3,
    bar="717 nm factor; display 0-3, uncapped analysis",
)
page(
    HERE,
    "Retain both stages and expose unresolved observations",
    "The combined image is a real topographic-then-BRDF product. All-band support is 6,613,717 pixels, about 98.95% of the 6,683,905 reconstructed native source domain. Per-band support differs, so a band-valid extreme may lie outside the all-ten-band domain. Large mathematically resolved gains remain possible and are covered by a regression test.",
    f,
    "Correction factors are output/input ratios on finite nonzero source values. Display saturates at 3 only to keep the maps readable. Native maximum and exceedance diagnostics are computed without this display transform. Full per-band status counts are in topographic_coverage.json.",
)
roi_data = np.load(WORK / "roi_displays.npz")
f = images(
    HERE,
    "11_native_650_717",
    [
        (f"{b.replace('_', ' ')} / {w} nm", roi_data[f"{b}_{w}"])
        for w in [650, 717]
        for b in [
            "clean_raw",
            "conditioned_topography",
            "controlled_cluster_BRDF",
            "conditioned_combined_cluster",
        ]
    ],
    cols=4,
    vmin=0,
    vmax=0.5,
    bar="Candidate reflectance; display 0-0.5",
)
page(
    HERE,
    "Native crops retain wavelength and location controls",
    "Raw, topographic-only, BRDF-only and combined products are compared at the established crop and 10 cm sampling. The display scale is fixed across branches and both wavelengths. Unsupported cells remain absent rather than receiving an unchanged raw value. Numerical extremes are reported separately, so display saturation cannot masquerade as a successful repair.",
    f,
    "Rows 573:974, columns 812:1313, identical to the historical diagnostics. Candidate units remain conditional on DN/32768. The 650 and 717 nm bands are selected explicitly; substituting 668 nm would miss the historical red failure.",
)
common = np.load(WORK / "common_spectral_support.npy", mmap_mode="r")
old = (
    np.load(
        "/private/tmp/goldhill-viewing-geometry-20261104/C_center_combined.npy",
        mmap_mode="r",
    )
    if Path(
        "/private/tmp/goldhill-viewing-geometry-20261104/C_center_combined.npy"
    ).exists()
    else None
)
# Recover the authoritative baseline path from the evaluation implementation.
if old is None:
    candidates = list(
        Path("/private/tmp/goldhill-viewing-geometry-20261104").glob("*combined*.npy")
    )
    center = [p for p in candidates if "center" in p.name]
    old = np.load(center[0], mmap_mode="r")
summary = []
for label, a in [("Previous combined", old), ("Conditioned combined", combined)]:
    v = np.asarray(a[..., 7])
    valid = np.isfinite(v) & (v > -100)
    summary.append(
        dict(
            branch=label,
            native_band_max=float(v[valid].max()),
            common_all_band_max=float(v[common].max()),
            native_band_pixels=int(valid.sum()),
            common_all_band_pixels=int(common.sum()),
        )
    )
(HERE / "native_vs_common_extremes.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
for ax, key, title in zip(
    axs,
    ["native_band_max", "common_all_band_max"],
    ["Native 717 nm support", "Shared all-ten-band support"],
):
    ax.bar(
        [r["branch"] for r in summary],
        [r[key] for r in summary],
        color=[COLORS[1], COLORS[0]],
    )
    ax.set_title(title)
    ax.set_ylabel("Maximum candidate 717 nm reflectance")
    for i, r in enumerate(summary):
        ax.text(i, r[key], f"{r[key]:.4g}", ha="center", va="bottom")
f = save(HERE, "12_fair_extreme_comparison", fig)
page(
    HERE,
    "A lower native maximum partly reflects changed support",
    "The previous center-weighted combined image reaches about 63.51 at 717 nm; the new conditioned combined image reaches about 1.78. On the shared all-ten-band valid domain the maxima are about 0.655 and 0.689, respectively. The native peak reduction is therefore largely an explicit support decision, not evidence of lower reflectance everywhere on unchanged observations.",
    f,
    "Both native per-band and matched all-ten-band maxima are freshly calculated in native_vs_common_extremes.json. The new native 717 nm peak can occur where another band is unsupported. No factors or reflectance values were capped to produce this comparison.",
)
with (HERE / "polygon_summaries.csv").open() as s:
    polys = list(csv.DictReader(s))
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
for b, color in zip(keys, COLORS):
    r = next(
        r
        for r in polys
        if r["branch"] == b
        and r["GlobalID"] == "{3A6D6E1D-3581-49B8-9321-397DFE5298C5}"
    )
    axs[0].plot(
        W,
        [float(r[f"median{i}"]) for i in range(1, 11)],
        "o-",
        label=b.replace("_", " "),
        color=color,
    )
    axs[0].fill_between(
        W,
        [float(r[f"q25_{i}"]) for i in range(1, 11)],
        [float(r[f"q75_{i}"]) for i in range(1, 11)],
        alpha=0.1,
        color=color,
    )
    selected = [r for r in polys if r["branch"] == b]
    axs[1].scatter(
        [float(r["within_angle_median"]) for r in selected],
        [float(r["NIR_red_ratio_median"]) for r in selected],
        s=12,
        alpha=0.4,
        label=b,
        color=color,
    )
axs[0].set(
    xlabel="Wavelength (nm)",
    ylabel="Median candidate reflectance",
    title="Fixed aspen polygon; pixel IQR",
)
axs[0].legend(fontsize=8)
axs[1].set(
    xlabel="Within-polygon median spectral angle (degrees)",
    ylabel="Median NIR / red ratio",
    title="Each point is one polygon",
)
axs[1].set_yscale("log")
f = save(HERE, "13_vegetation_spectra", fig)
page(
    HERE,
    "Compare vegetation on the intersection, not on changing samples",
    "The integrated comparison preserves 157 original polygon identities and the same frozen folds, using 142,637 common memberships. The exemplar retains 5,956 common pixels. Spectral angle, red-edge reversal, NIR/red ratios, variance, separability and per-class outcomes are exported with all branch summaries. The smaller common support differs from the companion population and changes the raw classification baseline.",
    f,
    "Left: median spectrum and within-polygon pixel IQR. Right: individual polygon diagnostics; spectral angles are descriptive, not physical calibration tests. Mean spectra remain the frozen classifier inputs. No correction parameter was tuned to maximize classification performance.",
)
pg = read(HERE, "paired_gain")
fig, ax = plt.subplots(figsize=(13, 5.5))
for i, r in enumerate(pg):
    ax.errorbar(
        100 * r["difference"],
        i,
        xerr=[
            [100 * (r["difference"] - r["low"])],
            [100 * (r["high"] - r["difference"])],
        ],
        fmt="o",
        color=COLORS[i % 6],
    )
ax.axvline(0, color="grey", ls=":")
ax.set_yticks(range(len(pg)), [r["branch"] for r in pg], fontsize=9)
ax.set_xlabel(
    "Paired balanced-accuracy difference from matched raw (percentage points)"
)
f = save(HERE, "14_paired_ecology", fig)
page(
    HERE,
    "The ecological evaluation does not justify production promotion",
    "On matched support, raw balanced accuracy is 68.30%, controlled BRDF is 69.39%, and conditioned combined is about 66.42%. All paired gain intervals include zero. Homogeneous fitting does not demonstrate an ecological gain either. Numerical acceptance and rejection of unstable illumination do not amount to improved PFT identification or independent physical validation.",
    f,
    "Paired class-stratified polygon bootstrap with fixed predictions/folds. Full class metrics, confusion matrices, separability pairs and predictions are retained. OLS and cluster point corrections agree when both models pass; changing covariance alone does not improve the image.",
)
fig, ax = plt.subplots(figsize=(12, 4.5))
cover = read(HERE, "topographic_coverage")
ax.bar(
    W,
    [r["unsupported"] / (r["unsupported"] + r["corrected"]) * 100 for r in cover],
    width=12,
    color=COLORS[3],
)
ax.set(xlabel="Wavelength (nm)", ylabel="Unsupported fraction of footprint (%)")
ax.set_title("Per-band conditional illumination rejection")
f = save(HERE, "15_support_by_band", fig)
page(
    HERE,
    "NEON controls and scientific status remain separate",
    "The real NEON fixed-window regression reran both BRDF-only and combined corrections across ten selected wavelengths. Both remain numerically valid. The default source equations, reference geometry and acceptance path are shared; only explicitly supplied drone experiment options activate the new subset/cluster/conditioned-topography behavior. Sensor-specific calibration and sampling choices remain explicit.",
    f,
    "Source: NEON D10 R10C 2021-09-15 directional reflectance, 120 x 3000 pixels, ten bands. Native/serialized array equality and model status are checked in verification.json. Software tests cover calibration gates, affine units, masks, chunking and non-capped resolved gains; they do not certify drone calibration.",
)
f = diagram(
    HERE,
    "16_status_and_retrieval",
    ["Implemented and run", "Still unresolved", "Smallest useful retrieval"],
    [
        "Explicit unsupported SCS+C\nspatial fitting / covariance\nexperimental product gate",
        "Applied physical calibration\nactual contributors / datum\nwithin-target angular evidence",
        "40 existing requested band photos\n4 positions + pose/sensor binding\ncalibration/export + seam metadata",
    ],
)
page(
    HERE,
    "Outcome and next evidence",
    [
        "Problem -> evidence -> repair -> result -> status: stored/physical confusion -> paired encoding residuals -> affine contract -> numerical inversion verified -> physical calibration unverified. Missing angular design -> fixed rank one -> inferred camera rays -> rank three -> experimental contributors. Spatial confounding -> shift and subset sensitivity -> fitting masks, clusters and holdouts -> rejected unsupported cases -> no physical identification claim.",
        "Topographic poles -> negative C and denominator crossings -> Fieller-resolved illumination support -> real combined products with explicit NoData -> numerically bounded support, not universal physical validity. Gordon and Ruby cannot be honestly extended to the full experiment without clean radiometry and comparable viewing evidence; their source and geometry limitations remain visible.",
        "Reproduce using run_experiment.py, run_homogeneous.py, spatial_controls.py, evaluate.py, neon_control.py, build_publications.py and render_pdf.py. Existing source investigations and pre-edit snapshots are preserved. Exact inputs, hashes, plans and compact results accompany this report.",
    ],
    f,
    "References: Soenen, Peddle & Coburn (2005), SCS+C, doi:10.1109/TGRS.2005.852480; Cameron & Miller (2015), cluster-robust inference, doi:10.3368/jhr.50.2.317; von Luxburg & Franz (2009), geometric Fieller intervals, arxiv.org/abs/0711.0198. Policy thresholds are conditional choices, not universal claims from these papers.",
)
# Readable problem/evidence/repair/result/status table requested for the technical report.
fig, ax = plt.subplots(figsize=(14, 5.5))
ax.axis("off")
rows = [
    [
        "Radiometry",
        "Paired encoding residuals",
        "Per-band affine contract",
        "Residual < 0.000781\nstored units",
        "Numerical only;\ncalibration unverified",
    ],
    [
        "Viewing geometry",
        "565 camera positions",
        "Four inferred kernel designs",
        "Rank 3, conditions\nabout 98-182",
        "True contributors\nunverified",
    ],
    [
        "Spatial confounding",
        "Shifted R2 >= unshifted",
        "Masks, holdouts, clusters",
        "3 rejected controls;\nno decisive PFT gain",
        "Physical directional\nresponse unidentified",
    ],
    [
        "SCS+C poles",
        "Negative C; denominator\ncrosses zero",
        "Fieller-resolved support;\nno identity or caps",
        "Joint support 6,613,717;\nshared peak 0.689",
        "Experimental support\npolicy",
    ],
    [
        "NEON compatibility",
        "Real fixed-window control",
        "Keep default equations\nand options unchanged",
        "Exact output equality;\n10/10 bands supported",
        "Regression preserved",
    ],
]
t = ax.table(
    cellText=rows,
    colLabels=[
        "Problem",
        "Evidence",
        "Repair",
        "Numerical result",
        "Scientific status",
    ],
    cellLoc="left",
    loc="center",
    colWidths=[0.15, 0.21, 0.22, 0.23, 0.19],
)
t.auto_set_font_size(False)
t.set_fontsize(10)
t.scale(1, 3.3)
for (r, col), cell in t.get_celld().items():
    cell.set_edgecolor("#d6e1e5")
    if r == 0:
        cell.set_facecolor("#163b4b")
        cell.set_text_props(color="white", weight="bold")
    elif r % 2:
        cell.set_facecolor("#f0f5f6")
f = save(HERE, "17_problem_evidence_repair_status", fig)
PAGES[HERE][-1]["figure"] = f
# Additional standalone supporting figures integrated beside the principal panels.
with (PRIOR / "acquisition_path.csv").open() as stream:
    camera = list(csv.DictReader(stream))
fig, axs = plt.subplots(1, 2, figsize=(12, 4.7), layout="constrained")
xx = np.array([float(r["X"]) for r in camera])
yy = np.array([float(r["Y"]) for r in camera])
axs[0].plot(xx, yy, color="#9eb3bb", lw=0.6)
scatter = axs[0].scatter(xx, yy, c=np.arange(len(xx)), s=7, cmap="viridis")
axs[0].set_aspect("equal")
axs[0].set(
    xlabel="UTM easting (m)",
    ylabel="UTM northing (m)",
    title="565 positions, acquisition order",
)
fig.colorbar(scatter, ax=axs[0], label="Acquisition index")
# Nominal nadir footprint is a reconstruction scenario, not a recovered seamline.
axs[1].scatter(xx[::10], yy[::10], s=8, color=COLORS[0])

for x, y in zip(xx[::40], yy[::40]):
    axs[1].add_patch(
        Rectangle((x - 62, y - 47), 124, 94, fill=False, edgecolor=COLORS[2], alpha=0.5)
    )
axs[1].set_aspect("equal")
axs[1].set(
    xlabel="UTM easting (m)",
    ylabel="UTM northing (m)",
    title="Illustrative 143 m nominal nadir footprints",
)
f = save(PART, "22_flight_path_and_nominal_footprints", fig)
PAGES[PART][9]["extra_figures"] = [f]
PAGES[PART][9]["caption"] += (
    " Supplemental panel: acquisition positions and illustrative nominal footprints (1280 x 960, 3.75 micrometre pitch, 5.5 mm focal length at 143 m); not actual image contributors."
)
fig, axs = plt.subplots(1, 2, figsize=(12, 4.7), layout="constrained")
for k, label, color in [
    (0, "Nearest view zenith", COLORS[0]),
    (3, "Central view zenith", COLORS[2]),
    (12, "Mean relative azimuth", COLORS[3]),
]:
    d = np.asarray(G[::8, ::8, k])
    axs[0 if k != 12 else 1].hist(
        d[np.isfinite(d)], bins=60, alpha=0.5, label=label, color=color
    )
for ax in axs:
    ax.set(xlabel="Degrees", ylabel="Sampled pixels")
    ax.legend()
f = save(PART, "23_angular_distributions", fig)
PAGES[PART][12]["extra_figures"] = [f]
aid = np.array(G[::4, ::4, 2])
bid = np.array(G[::4, ::4, 5])
edge = np.zeros(aid.shape, bool)
edge[:, 1:] = aid[:, 1:] != aid[:, :-1]
edge[1:, :] |= aid[1:, :] != aid[:-1, :]
f = images(
    PART,
    "24_camera_assignment_boundaries",
    [
        ("A nearest camera identity", aid),
        ("B central camera identity", bid),
        ("A assignment boundaries", edge),
    ],
    cols=3,
)
PAGES[PART][13]["extra_figures"] = [f]
with (PRIOR / "polygon_summaries.csv").open() as stream:
    integrity = list(csv.DictReader(stream))
fig, axs = plt.subplots(1, 3, figsize=(13, 4.7), layout="constrained")
for ax, metric, title in zip(
    axs,
    ["within_angle_median", "NIR_red_ratio_median", "rededge_reversal"],
    ["Within-polygon angle (degrees)", "NIR / red ratio", "Red-edge reversal fraction"],
):
    names = ["clean_raw", "A_brdf", "C_center_brdf"]
    values = [[float(r[metric]) for r in integrity if r["branch"] == b] for b in names]
    ax.boxplot(values, tick_labels=["Raw", "Nearest", "Weighted"], showfliers=False)
    ax.set_title(title)
f = save(PART, "25_spectral_integrity", fig)
PAGES[PART][19]["extra_figures"] = [f]
PAGES[PART][19]["caption"] += (
    " Supplemental integrity diagnostics are polygon distributions; outliers are omitted from box display only, retained in the CSV."
)
# Integrate encoding residuals with the numerical decoding page to keep the companion to 20 pages.
residual = PAGES[PART].pop(3)
PAGES[PART][1]["extra_figures"] = [residual["figure"]]
PAGES[PART][1]["paragraphs"] += residual["paragraphs"]
PAGES[PART][1]["caption"] += " " + residual["caption"]
for folder, pages in PAGES.items():
    (folder / "report_pages.json").write_text(json.dumps(pages, indent=2) + "\n")
    title = (
        "Anatomy of a Red Artifact, Part II"
        if folder == PART
        else "Toward a Reliable Drone Correction Pipeline"
    )
    text = "# " + title + "\n\n"
    for i, p in enumerate(pages, 1):
        text += (
            f"## {i}. {p['title']}\n\n"
            + "\n\n".join(p["paragraphs"])
            + "\n\n"
            + "\n\n".join(
                f"![{p['title']}]({figure}.png)"
                for figure in [p["figure"]] + p.get("extra_figures", [])
            )
            + "\n\n"
            + p["caption"]
            + "\n\n"
        )
    (folder / "report.md").write_text(text)
    (folder / "figure_manifest.json").write_text(
        json.dumps(FIGURES[folder], indent=2) + "\n"
    )
print("Authored", [(str(k), len(v)) for k, v in PAGES.items()])
