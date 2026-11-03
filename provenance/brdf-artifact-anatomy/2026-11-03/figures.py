"""Aligned scientific figures, with explicit encoding, display and masking contracts."""

from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import (
    LogNorm,
    TwoSlopeNorm,
    SymLogNorm,
    ListedColormap,
    BoundaryNorm,
)
from matplotlib.patches import Rectangle
from shapely import wkt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
plt.rcParams.update(
    {
        "font.size": 12,
        "axes.formatter.useoffset": False,
        "axes.titlesize": 13,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "svg.fonttype": "none",
    }
)
COLORS = dict(raw="#244e69", topo="#b67732", brdf="#b83e4a", combined="#754f90")
STAGES = ["raw", "topo", "brdf", "combined"]
WAVE = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
F = json.loads((HERE / "flight_comparison.json").read_text())
S = json.loads((HERE / "selection.json").read_text())
B = pd.read_csv(HERE / "band_diagnostics.csv")
P = pd.read_csv(HERE / "polygon_stage_spectra.csv")
G = pd.read_csv(HERE / "polygon_geometry.csv")
Q = pd.read_csv(HERE / "pixel_trajectories.csv")
MAP = json.loads(
    (
        ROOT
        / "provenance/drone-scale-confirmation/2026-10-30/verified_numeric_mapping.json"
    ).read_text()
)
Z = np.load(HERE / "goldhill_zoom.npz")
FULL = {
    n: np.load(HERE / f"{n}_full_display.npz") for n in ["goldhill", "gordon", "ruby"]
}
TOPO = np.load(HERE / "goldhill_topo_zoom.npz")
R = np.array([[r["original_min"], r["original_max"]] for r in MAP["goldhill"]["bands"]])
E = S["roi_extent_NAD83_UTM13N"]
FIGURES = []
ONLY = set(sys.argv[1:])


def save(fig, name, caption, dpi=210):
    if ONLY and name not in ONLY:
        plt.close(fig)
        return
    fig.savefig(HERE / (name + ".png"), dpi=dpi, bbox_inches="tight")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
    plt.close(fig)
    FIGURES.append(dict(name=name, caption=caption))


def dn(values, name="goldhill"):
    bands = MAP[name]["bands"]
    lo = np.array([b["original_min"] for b in bands])
    span = np.array([b["original_max"] - b["original_min"] for b in bands])
    return np.asarray(values, dtype=float) * span / 10000 + lo


def limits(data, valid, bands=[4, 3, 1], name="goldhill"):
    x = dn(data, name)[..., bands][valid]
    return np.percentile(x, [2, 98], axis=0)


def rgb(data, mask, display_limits=None, bands=[4, 3, 1], name="goldhill"):
    v = dn(data, name)[..., bands]
    ok = mask & np.isfinite(v).all(-1)
    if display_limits is None:
        display_limits = np.percentile(v[ok], [2, 98], axis=0)
    lo, hi = display_limits
    a = np.clip((v - lo) / np.maximum(hi - lo, 1e-12), 0, 1)
    a[~np.isfinite(a)] = 0
    a[mask & ~ok] = 0.72
    a[~mask] = 1
    return a


def full_extent(name):
    f = F[name]
    tr = f["transform"]
    st = f["display_stride"]
    a = FULL[name]["raw"]
    left = tr[2] + tr[0] * 0.5 - st * tr[0] / 2
    top = tr[5] + tr[4] * 0.5 - st * tr[4] / 2
    return [left, left + a.shape[1] * st * tr[0], top + a.shape[0] * st * tr[4], top]


def adorn(ax, extent, bar=10, ticks=True):
    ax.set_xlim(extent[:2])
    ax.set_ylim(extent[2:])
    ax.set_aspect("equal")
    x0, x1, y0, y1 = extent
    if ticks:
        ax.set_xticks(np.linspace(x0, x1, 3))
        ax.set_yticks(np.linspace(y0, y1, 3))
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(labelsize=8)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    ax.annotate(
        "N",
        xy=(0.93, 0.92),
        xytext=(0.93, 0.76),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        color="black",
        fontsize=10,
        arrowprops={"arrowstyle": "-|>", "color": "black"},
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 1},
    )
    if bar is None:
        return
    x = x0 + 0.05 * (x1 - x0)
    y = y0 + 0.07 * (y1 - y0)
    ax.plot([x, x + bar], [y, y], color="white", lw=4)
    ax.plot([x, x + bar], [y, y], color="black", lw=1.5)
    ax.text(
        x + bar / 2,
        y + 0.025 * (y1 - y0),
        f"{bar:g} m",
        ha="center",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 1},
    )


def polygons(ax, ids=None, labels=False, color="#00b9c4"):
    ids = ids if ids is not None else S["selected_polygons"]
    for i, key in enumerate(ids):
        g = G[G.GlobalID.eq(key)]
        if not len(g):
            continue
        geom = wkt.loads(g.iloc[0].geometry_wkt)
        for part in [geom] if geom.geom_type == "Polygon" else geom.geoms:
            ax.plot(*part.exterior.xy, color=color, lw=1.4)
        if labels:
            ax.text(
                geom.centroid.x,
                geom.centroid.y,
                str(i + 1),
                ha="center",
                fontsize=9,
                color="black",
                bbox={"facecolor": "white", "edgecolor": color, "pad": 1},
            )


def map_image(
    ax,
    a,
    title,
    extent=E,
    mask=None,
    cmap="viridis",
    vmin=None,
    vmax=None,
    norm=None,
    contour=False,
    constant=False,
    bar=10,
):
    if a.ndim == 3:
        im = ax.imshow(a, extent=extent, origin="upper", interpolation="nearest")
    else:
        data = (
            np.ma.masked_where(~mask, a)
            if mask is not None
            else np.ma.masked_invalid(a)
        )
        cm = (plt.get_cmap(cmap) if isinstance(cmap, str) else cmap).copy()
        cm.set_bad((0, 0, 0, 0))
        if mask is not None:
            background = np.ones((*a.shape, 3), dtype=float)
            background[mask & ~np.isfinite(a)] = 0.72
            ax.imshow(
                background, extent=extent, origin="upper", interpolation="nearest"
            )
        if constant:
            im = ax.imshow(
                np.ma.masked_where(~mask, np.zeros_like(a)),
                extent=extent,
                origin="upper",
                cmap=ListedColormap(["#48758d"]),
                vmin=0,
                vmax=1,
                interpolation="nearest",
            )
            ax.text(
                0.02,
                0.03,
                f"Stored value: {float(np.nanmedian(a[mask])):.6g}",
                transform=ax.transAxes,
                fontsize=9,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9},
            )
        else:
            im = ax.imshow(
                data,
                extent=extent,
                origin="upper",
                cmap=cm,
                vmin=vmin if norm is None else None,
                vmax=vmax if norm is None else None,
                norm=norm,
                interpolation="nearest",
            )
    ax.set_title(title)
    adorn(ax, extent, bar=bar)
    if contour:
        y = np.linspace(E[3] - 0.05, E[2] + 0.05, Z["red_den"].shape[0])
        x = np.linspace(E[0] + 0.05, E[1] - 0.05, Z["red_den"].shape[1])
        ax.contour(x, y, Z["red_den"], levels=[0], colors="black", linewidths=0.8)
    return im


def spectrum(row, prefix="b"):
    return np.array([row[f"{prefix}{i}"] for i in range(1, 11)], float)


def eq_median(row, prefix="b"):
    return dn(spectrum(row, prefix))


def main():
    lim = limits(Z["raw"], Z["common"])
    # 1: full-source observation, with both fixed and individually stretched diagnostics.
    fig, axs = plt.subplots(2, 3, figsize=(15, 10), layout="constrained")
    for j, stage in enumerate(["raw", "brdf", "combined"]):
        for i in range(2):
            a = FULL["goldhill"]
            extent = full_extent("goldhill")
            image = rgb(a[stage], a["observed"], lim if i == 0 else None)
            map_image(
                axs[i, j],
                image,
                stage.upper()
                + (
                    " | FIXED source scale"
                    if i == 0
                    else " | INDIVIDUAL channel stretch"
                ),
                extent,
                bar=50,
            )
            axs[i, j].add_patch(
                Rectangle(
                    (E[0], E[2]),
                    E[1] - E[0],
                    E[3] - E[2],
                    fill=False,
                    ec="#00b9c4",
                    lw=1.4,
                )
            )
    fig.suptitle(
        "1. The red artifact is absent from the source and appears after historical BRDF\nDiagnostic RGB 650/560/475 nm | NAD83 / UTM 13N, metres",
        fontsize=18,
    )
    save(
        fig,
        "figure01_observation",
        "Full scene on the repaired grid. Top: one source-DN-equivalent display scale. Bottom: independent per-stage 2-98% channel stretches reveal structure but cannot compare radiometric magnitude. Cyan box is the common native zoom. Gray is missing stage data; white is outside positive source alpha.",
    )
    # 2: central requested six-row processing narrative.
    exemplar = P[P.GlobalID.eq(S["exemplar_GlobalID"])].set_index("stage")
    rawrow = exemplar.loc["raw"]
    black = eq_median(rawrow)
    fig, axs = plt.subplots(
        6,
        2,
        figsize=(14, 20),
        layout="constrained",
        gridspec_kw={"width_ratios": [1.05, 1.1]},
    )
    rows = [
        ("Source DN representation", "raw"),
        ("Spatially repaired | same values", "raw"),
        ("Stored normalization | inverse displayed", "raw"),
        ("Topographic correction only", "topo"),
        ("Historical BRDF only", "brdf"),
        ("Historical combined", "combined"),
    ]
    maxy = max(np.max(eq_median(exemplar.loc[st], "q75_b")) for st in STAGES) * 1.3
    for i, (label, stage) in enumerate(rows):
        map_image(axs[i, 0], rgb(Z[stage], Z["observed"], lim), label)
        polygons(axs[i, 0], [S["exemplar_GlobalID"]])
        r = exemplar.loc[stage]
        v = eq_median(r)
        q1 = eq_median(r, "q25_b")
        q3 = eq_median(r, "q75_b")
        ax = axs[i, 1]
        ax.plot(WAVE, black, color="black", lw=2, label="Source median")
        ax.plot(WAVE, v, color=COLORS[stage], marker="o", label=label)
        ax.fill_between(WAVE, q1, q3, color=COLORS[stage], alpha=0.15)
        ax.set(
            yscale="symlog",
            ylim=(0, maxy),
            ylabel="DN-equivalent numerical value",
            xlabel="Wavelength (nm)",
        )
        ax.set_yscale("symlog", linthresh=10000)
        ax.axvline(650, color="#b83e4a", ls=":", lw=1)
        ax.axvline(717, color="#754f90", ls=":", lw=1)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(alpha=0.15)
    fig.suptitle(
        "2. Watch the same mapped vegetation spectrum become corrupted\n"
        + S["exemplar_cover_category"]
        + " polygon "
        + S["exemplar_GlobalID"]
        + "\nMaps: one fixed RGB scale; spectra: identical pixel memberships, source median plus pixel IQR",
        fontsize=15,
    )
    save(
        fig,
        "figure02_stage_story",
        "Six requested views on one native 0.1 m grid and one extent. First three rows are encoding/spatial views of the same source, not new observations: spatial repair changes coordinates, not spectra. The actual historical order normalized before H5 spatial repair. Common display uses DN-equivalent = min + S*(65535-min)/10000 after each stage; this is not physical reflectance or native-camera recovery. Source-DN reference is black. Shading is within-polygon pixel IQR, not independent-replicate uncertainty. The 650 and 717 nm spikes are real historical numerical output.",
        dpi=250,
    )
    # 3: display audit, including actual default QA RGB.
    fig, axs = plt.subplots(3, 3, figsize=(15, 12), layout="constrained")
    sets = [
        ([4, 3, 1], "650/560/475 | diagnostic native-red view"),
        ([5, 3, 1], "668/560/475 | default production QA RGB"),
        ([4, 3, 0], "650/560/444 | semantic named bands"),
    ]
    for i, (bands, label) in enumerate(sets):
        ll = limits(Z["raw"], Z["common"], bands)
        for j, stage in enumerate(["raw", "brdf", "combined"]):
            map_image(
                axs[i, j],
                rgb(Z[stage], Z["observed"], ll, bands),
                stage.upper() + "\n" + label,
            )
    fig.suptitle(
        "3. A clean RGB can hide a corrupted spectrum\nEach row has one fixed source display scale; mappings are explicit, never inferred from color",
        fontsize=18,
    )
    save(
        fig,
        "figure03_rgb_mapping",
        "The default QA targets 660/560/490 nm and resolves to 668/560/475 nm. The named band_map red=650, green=560, blue=444 belongs to band-fidelity metrics, not the RGB selector. The default RGB omits both catastrophically altered Goldhill wavelengths (650 and 717 nm). Diagnostic native-red RGB exposes the artifact; a normal-looking default RGB does not validate the cube.",
    )
    # 4: tracked actual pixels.
    labels = list(Q.label.unique())
    fig, axs = plt.subplots(len(labels), 3, figsize=(15, 16), layout="constrained")
    for i, label in enumerate(labels):
        q = Q[Q.label.eq(label)].sort_values("wavelength_nm")
        r = int(q.row.iloc[0])
        c = int(q.column.iloc[0])
        for stage in STAGES:
            axs[i, 0].plot(
                WAVE,
                dn(q[stage].to_numpy()),
                label=stage,
                color=COLORS[stage],
                marker="o",
            )
        axs[i, 0].set_yscale("symlog", linthresh=10000)
        axs[i, 0].set_title(f"{label}: row {r}, col {c}")
        axs[i, 0].set_ylabel("DN-equivalent")
        axs[i, 1].plot(WAVE, q.pred_observed, marker="o", label="Observed prediction")
        axs[i, 1].plot(WAVE, q.pred_reference, ls="--", label="Reference prediction")
        axs[i, 1].axhline(0, color="black", lw=0.7)
        axs[i, 1].set_yscale("symlog", linthresh=0.01)
        axs[i, 1].set_title("Signed historical predictions")
        axs[i, 2].plot(WAVE, q.factor, marker="o", color="#b83e4a")
        axs[i, 2].set_yscale("log")
        axs[i, 2].set_ylim(1e-3, 2e8)
        axs[i, 2].axhline(1, color="black", ls=":")
        fb = q.fallback.astype(bool)
        axs[i, 2].scatter(
            WAVE[fb],
            q.factor[fb],
            s=70,
            facecolors="none",
            edgecolors="#276f91",
            label="Positivity fallback",
        )
        axs[i, 2].set_title("Factor; open circles mark fallback")
        for ax in axs[i]:
            ax.set_xlabel("Wavelength (nm)")
            ax.grid(alpha=0.15)
    axs[0, 0].legend(fontsize=9)
    axs[0, 1].legend(fontsize=9)
    fig.suptitle(
        "4. Four real pixels, unchanged source vegetation, radically different numerical trajectories",
        fontsize=17,
    )
    save(
        fig,
        "figure04_pixel_trajectories",
        "Actual native row/column and projected coordinates are in pixel_trajectories.csv. Positive factors use a logarithmic axis; signed predictions and spectra use symlog, preserving zeros and negative values. No gains are capped in the calculations. The zero-denominator outside pixel and first positive-denominator neighbor are adjacent 0.1 m cells.",
        dpi=240,
    )
    # 5: viewing and solar atlas.
    fields = [
        ("sensor_zn", "View zenith | PLACEHOLDER"),
        ("sensor_az", "View azimuth | PLACEHOLDER"),
        ("solar_zn", "Solar zenith | DERIVED, time unverified"),
        ("solar_az", "Solar azimuth | DERIVED, time unverified"),
        (
            "relative_azimuth",
            "Relative azimuth | numerical only\nUndefined direction at nadir",
        ),
        ("kg_old", "Historical LiDenseR\nSpurious nadir azimuth response"),
    ]
    fig, axs = plt.subplots(2, 3, figsize=(16, 10), layout="constrained")
    d = FULL["goldhill"]
    extent = full_extent("goldhill")
    stats = pd.read_csv(HERE / "geometry_statistics.csv")
    for ax, (key, title) in zip(axs.flat, fields):
        arr = d[key]
        mask = d["observed"]
        constant = key.startswith("sensor")
        im = map_image(ax, arr, title, extent, mask=mask, constant=constant, bar=50)
        if not constant:
            fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        ax.set_xticks([])
        ax.set_yticks([])
        row = stats[stats.flight.eq("goldhill") & stats.field.eq(key)]
        if len(row):
            row = row.iloc[0]
            text = f"min {row['min']:.6f}; median {row['median']:.6f}\nmax {row['max']:.6f}; range {row['range']:.6g} deg"
        else:
            text = f"Display-sample range {np.nanmin(arr[mask]):.6g} to {np.nanmax(arr[mask]):.6g}"
        ax.text(0.01, -0.17, text, transform=ax.transAxes, fontsize=9)
    fig.suptitle(
        "5. Actual encoded viewing and derived solar geometry | full Goldhill scene\nPLACEHOLDER is not measured view; azimuth zero at nadir is not independent direction",
        fontsize=18,
    )
    save(
        fig,
        "figure05_geometry_atlas",
        "Uniform zero view maps are shown with a single-value legend, not a misleading continuous scale. Numeric relative azimuth is stored solar azimuth minus placeholder zero. Solar fields are per-pixel NOAA calculations at one manifest timestamp, not camera observations; time remains unverified. Full-population ranges and projected gradient bearings are in geometry_statistics.csv. Images are native point samples, stride 6; all exact metrics use native arrays.",
    )
    # 6: terrain atlas and concept diagram.
    fig, axs = plt.subplots(2, 3, figsize=(16, 10), layout="constrained")
    for ax, key, title, cm, limt in zip(
        axs.flat[:4],
        ["slope", "aspect", "cos_i", "incidence_angle"],
        [
            "Stored terrain slope (degrees)",
            "Stored aspect (clockwise degrees)",
            "Solar incidence cosine",
            "Incidence angle (degrees; back-facing >90)",
        ],
        ["viridis", "twilight", "RdBu_r", "viridis"],
        [(0, 90), (0, 360), (-1, 1), (0, 180)],
    ):
        im = map_image(
            ax,
            d[key],
            title,
            extent,
            mask=d["observed"],
            cmap=cm,
            vmin=limt[0],
            vmax=limt[1],
            bar=50,
        )
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    ax = axs[1, 1]
    ax.axis("off")
    ax.plot([0.1, 0.9], [0.2, 0.55], color="#678154", lw=5)
    ax.plot([0.5, 0.5], [0.35, 0.95], ls=":", color="gray")
    ax.annotate(
        "surface normal",
        xy=(0.33, 0.82),
        xytext=(0.7, 0.85),
        arrowprops={"arrowstyle": "->"},
    )
    ax.annotate(
        "solar ray",
        xy=(0.5, 0.38),
        xytext=(0.08, 0.95),
        arrowprops={"arrowstyle": "->", "color": "#b67732"},
    )
    ax.text(
        0.05,
        0.05,
        "Conceptual only: slope, solar incidence\nand viewing angle are different quantities.",
        transform=ax.transAxes,
    )
    ax.set_title("Geometry relative to terrain (not measured rays)")
    ax = axs[1, 2]
    ax.axis("off")
    ax.text(
        0.03,
        0.95,
        "Terrain provenance remains qualified\n\nDegree arrays are read unchanged.\nAspect is cyclic; no north seam is hidden.\n\ncos(i) is computed from actual stored\nslope/aspect and working solar grids.\n\nNo terrain is substituted or interpolated.\nBack-facing illumination is retained.\n\nSPA comparison at configured Goldhill time:\nNOAA 27.7649 deg, SPA 28.0396 deg.\nThis does not verify the acquisition date.",
        va="top",
        fontsize=12,
    )
    fig.suptitle(
        "6. Terrain illumination is separate from viewing geometry", fontsize=19
    )
    save(
        fig,
        "figure06_terrain_atlas",
        "Source slope/aspect grids and their degree interpretation are preserved. Physical source-surface/derivative and timestamp provenance remain unresolved. Incidence angle is arccos(cos(i)) only where finite and within [-1,1]; negative cosine is explicitly back-facing. The explanatory terrain diagram is conceptual, not recovered camera geometry.",
    )
    # 7: identical native zoom for angular fields.
    fig, axs = plt.subplots(2, 3, figsize=(16, 10), layout="constrained")
    for ax, key, title, cm in zip(
        axs.flat,
        ["solar_zn", "solar_az", "slope", "aspect", "cos_i", "kg_old"],
        [
            "Solar zenith (deg)",
            "Solar azimuth (deg)",
            "Slope (deg)",
            "Cyclic aspect (deg)",
            "cos(i)",
            "Historical LiDenseR",
        ],
        ["viridis", "viridis", "viridis", "twilight", "RdBu_r", "coolwarm"],
    ):
        im = map_image(ax, Z[key], title, mask=Z["observed"], cmap=cm, contour=True)
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        polygons(ax, [S["exemplar_GlobalID"]])
    fig.suptitle(
        "7. One native 0.1 m zoom: geometry, historical zero contour and the same polygon\nBlack: historical red predicted response = 0; cyan: selected researcher polygon",
        fontsize=18,
    )
    save(
        fig,
        "figure07_geometry_zoom",
        "All six panels use identical NAD83/UTM13N extent and native pixel centers. Black contours are based on the actual quantized historical 650 nm prediction, not a smoothed image edge. Sensor angles remain the same zero placeholders in this zoom. The incidence field is not substituted for sensor zenith.",
    )
    # 8: rank/kernel evidence.
    fig, axs = plt.subplots(2, 3, figsize=(16, 9), layout="constrained")
    for j, name in enumerate(["goldhill", "gordon", "ruby"]):
        f = F[name]
        ax = axs[0, j]
        for key, color in [
            ("historical_defective_design", "#b67732"),
            ("modern_angular_design", "#276f91"),
        ]:
            sv = np.array(f[key]["singular_values"])
            ax.plot(
                [1, 2, 3],
                sv / sv[0],
                marker="o",
                color=color,
                label=key.replace("_", " "),
            )
            ax.set_yscale("log")
            ax.set_xticks([1, 2, 3])
            ax.set_title(
                name.title()
                + f" | old rank {f['historical_defective_design']['rank']}, current rank {f['modern_angular_design']['rank']}"
            )
            ax.set_xlabel("Singular value index")
            ax.set_ylabel("Singular value / largest")
        ax.legend(fontsize=8)
    ax = axs[1, 0]
    kg = d["kg_old"][d["observed"]]
    kv = d["kv_old"][d["observed"]]
    ax.scatter(kv[::17], kg[::17], s=5, alpha=0.1, rasterized=True)
    ax.set(
        xlabel="Historical RossThick (constant)",
        ylabel="Historical LiDenseR",
        title="A constant column has undefined correlation",
    )
    ax = axs[1, 1]
    ax.hist(kg, bins=50, color="#b67732")
    ax.set(
        xlabel="Historical LiDenseR",
        ylabel="Display-sample pixels",
        title="Tiny spurious variation is not camera diversity",
    )
    axs[1, 0].yaxis.set_major_locator(plt.MaxNLocator(4))
    axs[1, 1].xaxis.set_major_locator(plt.MaxNLocator(4))
    axs[1, 1].tick_params(axis="x", rotation=20, labelsize=9)
    ax = axs[1, 2]
    ax.axis("off")
    ax.text(
        0.02,
        0.95,
        "Millions of pixels repeat the same view\n\nCurrent correct nadir kernels give rank 1/3.\nAll 30 band fits are unsupported.\n\nThe old geometric kernel spuriously used\nazimuth at nadir, creating nominal rank 2.\nIt still could not identify three coefficients.\n\nOld least squares discarded returned rank.\nNo synthetic angle map is used here.",
        va="top",
        fontsize=13,
    )
    fig.suptitle(
        "8. Pixel count cannot replace independent angular information", fontsize=19
    )
    save(
        fig,
        "figure08_design_rank",
        "Full native design SVD, not a sampled rank estimate. The old kernel manufactured a second numerical direction through erroneous nadir azimuth dependence; the repaired kernel is rank one. RossThick is constant, so its correlation with LiDenseR is undefined rather than zero. Tiny positive trailing singular values are numerical roundoff, not independent observations.",
    )
    # 9: saved coefficients, tiny training population and cancellation.
    fig, axs = plt.subplots(2, 3, figsize=(16, 9), layout="constrained")
    gold = B[B.flight.eq("goldhill")]
    fit = json.loads((HERE / "historical_fit_reconstruction.json").read_text())
    for ax, key in zip(axs[0], ["iso", "vol", "geo"]):
        ax.plot(gold.wavelength_nm, gold[key], marker="o", color="#754f90")
        ax.set_yscale("symlog", linthresh=0.01)
        ax.axhline(0, color="black", lw=0.6)
        ax.set(
            xlabel="Wavelength (nm)",
            ylabel="Historical response coefficient",
            title=key,
        )
    axs[1, 0].bar(
        [r["wavelength_nm"] for r in fit],
        [r["eligible_pixels"] for r in fit],
        width=10,
        color="#b67732",
    )
    axs[1, 0].set(
        xlabel="Wavelength (nm)",
        ylabel="Eligible source pixels",
        title="Stored values 0..2 only; no verified physical units",
    )
    q = Q[(Q.label.eq("near_zero_inside")) & Q.wavelength_nm.eq(650)].iloc[0]
    terms = [q.iso_term, q.vol_term, q.geo_term]
    axs[1, 1].bar(
        ["isotropic", "volume term", "geometric term"],
        terms,
        color=["#276f91", "#b67732", "#754f90"],
    )
    axs[1, 1].axhline(0, color="black")
    axs[1, 1].set_title(f"Cancellation leaves {q.pred_observed:.7f}")
    axs[1, 1].tick_params(axis="x", rotation=15)
    axs[1, 2].axis("off")
    axs[1, 2].text(
        0.02,
        0.95,
        f"Red training pixels: {next(r for r in fit if r['band'] == 5)['eligible_pixels']}\nGreen training pixels: {next(r for r in fit if r['band'] == 4)['eligible_pixels']}\nBoth historical fits have rank 2/3.\nSaved coefficients reproduce bit-for-bit.\n\nObserved red prediction: {q.pred_observed:.7f}\nReference prediction: {q.pred_reference:,.6f}\n\nThe reference is 45-degree solar / nadir,\nfar outside the supported design.\nIt is not an observed calibration target.",
        va="top",
        fontsize=13,
    )
    fig.suptitle(
        "9. An underdetermined fit produces large cancelling coefficients and an unsupported reference",
        fontsize=18,
    )
    save(
        fig,
        "figure09_coefficients",
        "Actual unchanged coefficient vectors. Historical fitting treated stored range-normalized numbers as scale-one unitless values and selected 0..2, leaving only 14 red and 13 green pixels. This is a numerical population mismatch, not verified physical reflectance calibration. Red/green least-squares reconstruction uses those exact source coordinates and matches saved float32 coefficients. The 650 nm reference prediction is 91,740.234375, not a measured signal.",
    )
    # 10: predictions/factors/actual output on one extent.
    fig, axs = plt.subplots(2, 4, figsize=(18, 10), layout="constrained")
    red = Z["red_den"]
    num = Z["red_num"]
    factor = Z["red_factor"]
    obs = Z["observed"]
    state = np.where(~Z["visited"], 2, np.where((red <= 0) | (num <= 0), 0, 1))
    fields = [
        (
            red,
            "Observed prediction = denominator",
            "RdBu_r",
            TwoSlopeNorm(vcenter=0, vmin=-1.5, vmax=1.5),
        ),
        (num, "Reference prediction = numerator", "viridis", None),
        (
            red,
            "Near-zero denominator detail",
            "RdBu_r",
            TwoSlopeNorm(vcenter=0, vmin=-0.05, vmax=0.05),
        ),
        (num, "Correction numerator (same reference field)", "viridis", None),
        (
            factor,
            "Applied positive factor (log scale)",
            "magma",
            LogNorm(vmin=1, vmax=2e7),
        ),
        (
            state,
            "Fallback state: 0 guard, 1 ratio, 2 unvisited",
            ListedColormap(["#4c78a8", "#f58518", "#b279a2"]),
            BoundaryNorm([-0.5, 0.5, 1.5, 2.5], 3),
        ),
        (
            dn(Z["combined"])[..., 4],
            "Final combined red | DN-equivalent",
            "magma",
            SymLogNorm(linthresh=10000, vmin=0, vmax=5e10),
        ),
    ]
    for ax, (array, title, cm, norm) in zip(axs.flat, fields):
        im = map_image(ax, array, title, mask=obs, cmap=cm, norm=norm, contour=True)
        cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        if title.startswith("Fallback"):
            cb.set_ticks([0, 1, 2], labels=["Guard", "Ratio", "Unvisited"])
    axs[1, 3].axis("off")
    edge = json.loads((HERE / "boundary_correspondence.json").read_text())
    axs[1, 3].text(
        0.01,
        0.97,
        f"Observed output and full branch rule:\n{edge['actual_edges']:,} matching native edges\nDice = {edge['dice']:.1f}\nMaximum edge displacement = 0 m\n\nMain denominator transition: 2,933 edges.\nFour other edges surround one NDVI\nupper-bin exception pixel, not the streak.\n\nBlack lines: quantized response zero.\nWhite: outside observation; gray: missing.\nNo nonpositive response is clipped positive.",
        va="top",
        fontsize=12,
    )
    fig.suptitle(
        "10. The observed prediction crosses zero; the historical branch switches from identity to enormous gain",
        fontsize=18,
    )
    save(
        fig,
        "figure10_predictions",
        "Seven spatial fields on exactly the same native zoom. Observed response and denominator are the same quantity; reference response and numerator are the same quantity, shown explicitly rather than implying independent measurements. Signed fields use a zero-centered diverging scale. Positive factors use log color; nonpositive predictions remain visible and the fallback state is separate. Quantitative boundary comparison uses native neighbor edges, not raster color or interpolated contours.",
    )
    # 11: contiguous transects plus exact factor/denominator scatter.
    t = pd.read_csv(HERE / "red_transects.csv")
    t = t[t.row.eq(S["main_transect_row"])]
    fig, axs = plt.subplots(5, 1, figsize=(14, 16), layout="constrained", sharex=False)
    for ax, col, label in zip(
        axs[:4],
        ["den", "num", "factor", "raw"],
        [
            "Signed observed prediction",
            "Reference prediction",
            "Applied historical factor",
            "Original red-band S",
        ],
    ):
        ax.plot(
            t.column, t[col], color="#b83e4a" if col in ["den", "factor"] else "#276f91"
        )
        ax.set_ylabel(label)
        ax.axvline(S["main_transition_left_column"] + 0.5, color="black", ls="--")
        ax.grid(alpha=0.15)
    axs[0].axhline(0, color="black")
    axs[2].set_yscale("log")
    axs[3].plot(t.column, t.brdf, label="BRDF-only red", color="#b83e4a")
    axs[3].set_yscale("symlog", linthresh=1000)
    axs[3].legend()
    axs[3].set_xlabel("Contiguous native columns at row " + str(S["main_transect_row"]))
    den = np.load(
        "/private/tmp/goldhill-radiometric-recovery-20261102/red_denominator.npy",
        mmap_mode="r",
    )
    cf = np.load(
        "/private/tmp/goldhill-radiometric-recovery-20261102/red_factor.npy",
        mmap_mode="r",
    )
    aa = den[::13, ::13].ravel()
    bb = cf[::13, ::13].ravel()
    good = np.isfinite(aa) & np.isfinite(bb)
    axs[4].scatter(aa[good], bb[good], s=4, alpha=0.15)
    axs[4].set_yscale("log")
    axs[4].axvline(0, color="black", ls="--")
    axs[4].set(
        xlabel="Actual signed denominator (display point sample)",
        ylabel="Applied factor",
        title="Nonpositive denominator: identity. First positive quantized levels: largest gains.",
    )
    fig.suptitle(
        "11. A contiguous 0.1 m transect shows the guard discontinuity forming",
        fontsize=19,
    )
    save(
        fig,
        "figure11_denominator_transect",
        "Rows 881, 921 and 961 are available in the CSV; the main plot is actual contiguous row 921. The two neighboring cells 980/981 go from denominator 0 to 0.0078125 and factor 1 to 11,742,750. The reference prediction stays 91,740.234375. Signed predictions use linear or symlog axes, positive factors use log. The scatter is a deterministic display sample only; all metrics are full native arrays.",
        dpi=240,
    )
    # 12: band specificity and actual RGB choices.
    tb = np.load(HERE / "goldhill_transect_bands.npz")
    fig, axs = plt.subplots(2, 2, figsize=(16, 10), layout="constrained")
    pos = tb["columns"]
    im = axs[0, 0].imshow(
        np.log10(tb["factors"].T),
        aspect="auto",
        extent=[pos[0] - 0.5, pos[-1] + 0.5, 9.5, -0.5],
        cmap="magma",
        vmin=-2,
        vmax=8,
        interpolation="nearest",
    )
    axs[0, 0].set_yticks(range(10), WAVE)
    axs[0, 0].set(
        xlabel="Native column at row 921",
        ylabel="Wavelength (nm)",
        title="log10 factor | no gain cap",
    )
    fig.colorbar(im, ax=axs[0, 0])
    ratio = np.divide(
        tb["brdf"], tb["raw"], out=np.full_like(tb["raw"], np.nan), where=tb["raw"] != 0
    )
    im = axs[0, 1].imshow(
        np.ma.masked_invalid(np.log10(ratio.T)),
        aspect="auto",
        extent=[pos[0] - 0.5, pos[-1] + 0.5, 9.5, -0.5],
        cmap="magma",
        vmin=-2,
        vmax=8,
        interpolation="nearest",
    )
    axs[0, 1].set_yticks(range(10), WAVE)
    axs[0, 1].set(
        title="Measured output/input ratio, same pixels",
        xlabel="Native column",
        ylabel="Wavelength (nm)",
    )
    fig.colorbar(im, ax=axs[0, 1])
    axs[1, 0].plot(gold.wavelength_nm, gold.factor_max, marker="o", color="#b83e4a")
    axs[1, 0].set_yscale("log")
    axs[1, 0].set(
        xlabel="Wavelength (nm)",
        ylabel="Maximum historical factor",
        title="650 nm dominates; 717 nm also severely corrupted",
    )
    axs[1, 1].bar(
        gold.wavelength_nm,
        gold.historical_positivity_fallback_fraction,
        width=10,
        color="#276f91",
    )
    axs[1, 1].set(
        xlabel="Wavelength (nm)",
        ylabel="Positivity-guard fraction",
        title="A factor of one may mean model rejection, not success",
    )
    fig.suptitle(
        "12. The artifact is wavelength-specific, not an RGB-only illusion", fontsize=19
    )
    save(
        fig,
        "figure12_spectral_heatmap",
        "All ten actual bands. 650 nm reaches 11.74 million gain; 717 nm reaches about 115,554. Green 560 and red 668 have negative reference predictions and fall back everywhere. 475 is initialized neutral. The default 668/560/475 RGB therefore hides the 650/717 corruption. Named blue 444 follows a separate loss response. Full per-band ranges, quantiles, masks, coefficients and fractions are in band_diagnostics.json.",
    )
    # 13: separate topographic denominator.
    fig, axs = plt.subplots(2, 3, figsize=(16, 10), layout="constrained")
    C = float(TOPO["topo_C"])
    fields = [
        (Z["cos_i"], "Solar incidence cosine", "RdBu_r", TwoSlopeNorm(0, -1, 1)),
        (
            np.full(Z["cos_i"].shape, C),
            f"Fitted C at 531 nm = {C:.8f}",
            "viridis",
            None,
        ),
        (
            TOPO["topo_den"],
            "SCS+C denominator = cos(i) + C",
            "RdBu_r",
            TwoSlopeNorm(0, -1, 1),
        ),
        (
            TOPO["topo_factor"],
            "SCS+C factor at 531 nm",
            "magma",
            LogNorm(vmin=0.1, vmax=400),
        ),
        (
            (TOPO["topo_factor"] > 10).astype(float),
            "Diagnostic extreme factor >10 (not a cap)",
            "magma",
            None,
        ),
        (
            Z["red_den"],
            "BRDF denominator: a DIFFERENT quantity",
            "RdBu_r",
            TwoSlopeNorm(0, -1.5, 1.5),
        ),
    ]
    for ax, (arr, title, cm, norm) in zip(axs.flat, fields):
        im = map_image(ax, arr, title, mask=Z["observed"], cmap=cm, norm=norm)
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    fig.suptitle(
        "13. Topography has its own instability; it does not generate the red BRDF branch boundary",
        fontsize=18,
    )
    save(
        fig,
        "figure13_topographic_mechanism",
        "Actual historical normalized-source 531 nm C=-0.21112473. Full-scene ratio reproduces cached topographic values bit-for-bit and reaches 356.55. The SCS+C near-zero denominator is cos(i)+C with guard 0.001; the BRDF denominator is the fitted directional response. They are different mechanisms. Threshold >10 is descriptive, never clipping or a scientific acceptance criterion. Topographic outputs remain unapproved.",
    )
    # 14: immediate scientific consequence in the representative researcher polygon.
    geom = wkt.loads(G[G.GlobalID.eq(S["exemplar_GlobalID"])].iloc[0].geometry_wkt)
    pad = 2.0
    emin, nnmin, emax, nnmax = geom.bounds
    local = [emin - pad, emax + pad, nnmin - pad, nnmax + pad]
    fig, axs = plt.subplots(1, 3, figsize=(17, 6), layout="constrained")
    for ax, stage in zip(axs[:2], ["raw", "brdf"]):
        map_image(
            ax,
            rgb(Z[stage], Z["observed"], lim),
            stage.upper() + " | identical fixed scale",
            bar=None,
        )
        polygons(ax, [S["exemplar_GlobalID"]], color="#00b9c4")
        ax.set_xlim(local[:2])
        ax.set_ylim(local[2:])
        bx = local[0] + 0.08 * (local[1] - local[0])
        by = local[2] + 0.08 * (local[3] - local[2])
        ax.plot([bx, bx + 2], [by, by], color="white", lw=4)
        ax.plot([bx, bx + 2], [by, by], color="black", lw=1.4)
        ax.text(
            bx + 1,
            by + 0.15,
            "2 m",
            ha="center",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
        )
    for stage in ["raw", "brdf"]:
        r = exemplar.loc[stage]
        v = eq_median(r)
        axs[2].plot(WAVE, v, marker="o", color=COLORS[stage], label=stage)
        axs[2].fill_between(
            WAVE,
            eq_median(r, "q25_b"),
            eq_median(r, "q75_b"),
            color=COLORS[stage],
            alpha=0.2,
        )
    axs[2].set_yscale("symlog", linthresh=10000)
    axs[2].set(
        xlabel="Wavelength (nm)",
        ylabel="DN-equivalent median and pixel IQR",
        title=S["exemplar_cover_category"] + " | same vegetation, same pixels",
    )
    axs[2].axvline(650, color="#b83e4a", ls=":")
    axs[2].axvline(717, color="#754f90", ls=":")
    axs[2].legend()
    fig.suptitle(
        "14. A researcher-assigned vegetation signature is changed by the algorithm alone",
        fontsize=19,
    )
    save(
        fig,
        "figure14_polygon_consequence",
        "Source and BRDF-only show the same Deciduous polygon, source grid and acquisition. No biological change occurred between panels. The curve uses common retained source-alpha-positive pixels; shading is their within-polygon IQR, not a confidence interval from independent plants. The 650 and 717 nm bands acquire artificial dominance. PFT label and GlobalID are preserved exactly.",
    )
    # 15: all Goldhill PFT distortion.
    fig, axs = plt.subplots(2, 2, figsize=(16, 10), layout="constrained")
    classes = sorted(P.cover_category.unique())
    for ax, label in zip(axs.flat, classes):
        for stage in STAGES:
            g = P[P.cover_category.eq(label) & P.stage.eq(stage)]
            med = g[[f"b{i}" for i in range(1, 11)]].median().to_numpy()
            ax.plot(
                WAVE,
                dn(med),
                marker="o",
                color=COLORS[stage],
                label=f"{stage} ({len(g)} polygons)",
            )
        ax.set_yscale("symlog", linthresh=10000)
        ax.set(
            xlabel="Wavelength (nm)",
            ylabel="DN-equivalent median of polygon medians",
            title=label,
        )
        ax.legend(fontsize=9)
        ax.grid(alpha=0.15)
    fig.suptitle(
        "15. Spectral distortion across the four recorded Goldhill cover categories",
        fontsize=19,
    )
    save(
        fig,
        "figure15_pft_distortion",
        "One polygon median per identity, with exactly the same pixels compared across all stages. All 157 Goldhill polygons and 144,411 common memberships are retained. Goldhill has no non-vegetated/dead polygons on this footprint; that category remains present in the source and Gordon/Ruby comparisons, not invented for Goldhill. Descriptive within-polygon variability, spectral angles, index changes and between-PFT overlap are separate tables, not classification accuracy or correction efficacy.",
    )
    # 16: common comparative views, same columns and scales across flights.
    fig, axs = plt.subplots(3, 6, figsize=(21, 11), layout="constrained")
    for i, name in enumerate(["gordon", "goldhill", "ruby"]):
        d = FULL[name]
        ex = full_extent(name)
        ll = limits(d["raw"], d["common"], name=name)
        images = [
            (rgb(d["raw"], d["observed"], ll, name=name), "Source RGB"),
            (d["sensor_zn"], "Stored view zenith = 0"),
            (d["solar_zn"], "Derived solar zenith"),
            (d["red_factor"], "650 nm factor"),
            ((d["red_den"] <= 0).astype(float), "650 nm nonpositive observed"),
            (
                rgb(d["combined"], d["observed"], ll, name=name),
                "Historical combined RGB",
            ),
        ]
        for j, (arr, title) in enumerate(images):
            kw = {}
            cm = "viridis"
            if j == 1:
                kw["constant"] = True
            if j == 2:
                kw.update(vmin=20, vmax=40)
            if j == 3:
                kw["norm"] = LogNorm(vmin=1, vmax=2e7)
                cm = "magma"
            im = map_image(
                axs[i, j],
                arr,
                name.title() + "\n" + title,
                ex,
                mask=d["observed"],
                cmap=cm,
                norm=LogNorm(vmin=1, vmax=2e7) if j == 3 else None,
                bar=50,
            )
            axs[i, j].set_xticks([])
            axs[i, j].set_yticks([])
            if j in [2, 3]:
                fig.colorbar(im, ax=axs[i, j], fraction=0.04, pad=0.01)
    fig.suptitle(
        "16. No red streak does not mean a valid correction | all three current designs are rank 1/3",
        fontsize=21,
    )
    save(
        fig,
        "figure16_three_flights",
        "Columns are matched across flights; RGB uses a fixed source scale within each flight, explicitly not a claim of calibrated cross-flight equivalence. 650 nm factors share a log scale from 1 to 20 million. In the observed-nonpositive mask, purple is false and yellow is true. Gordon has large gains in other bands (notably 444/475), while Ruby mainly loses signal or takes neutral guards. Negative reference predictions can force identity even when observed predictions are positive, so the full guard fractions must be read alongside the observed-negative mask. Every fit remains unsupported under the current corrected kernels.",
    )
    # Compact presentation bookkeeping and explicit RGB result.
    production_bands = [5, 3, 1]
    raw = Z["raw"][..., production_bands]
    # Additional actual kernel maps and honest display-sample angular histograms.
    fig, axs = plt.subplots(2, 3, figsize=(16, 10), layout="constrained")
    for ax, key, title in zip(
        axs[0],
        ["kv_old", "kg_old", "kv_current"],
        [
            "Historical RossThick | constant",
            "Historical LiDenseR | defective variation",
            "Corrected RossThick | constant",
        ],
    ):
        arr = FULL["goldhill"][key]
        mask = FULL["goldhill"]["observed"]
        im = map_image(
            ax,
            arr,
            title,
            full_extent("goldhill"),
            mask=mask,
            constant=(key != "kg_old"),
            bar=50,
        )
        if key == "kg_old":
            fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    for ax, key, title in zip(
        axs[1],
        ["solar_zn", "solar_az", "kg_old"],
        [
            "Derived solar zenith | time unverified",
            "Derived solar azimuth | time unverified",
            "Historical LiDenseR distribution",
        ],
    ):
        arr = FULL["goldhill"][key]
        sample = arr[FULL["goldhill"]["observed"] & np.isfinite(arr)]
        ax.hist(sample, bins=45, color="#276f91", alpha=0.8)
        ax.set(
            title=title,
            xlabel="Degrees" if key.startswith("solar") else "Kernel value",
            ylabel="Display-sample count (stride 6)",
        )
        ax.ticklabel_format(useOffset=False, style="plain", axis="x")
        ax.tick_params(axis="x", rotation=20, labelsize=9)
    fig.suptitle(
        "7b. Actual angular distributions and kernel fields, including the uniform RossThick map",
        fontsize=18,
    )
    save(
        fig,
        "figure07b_kernel_distributions",
        "Full-scene kernel fields use the same repaired grid as the overview. Histograms show the explicitly stride-6 positive-alpha display sample, not independent camera observations; exact full-population solar statistics and SVDs are tabulated separately. RossThick is uniform at scene zenith and zero view, so a single-value map legend replaces a continuous color bar. LiDenseR variation belongs to the defective historical implementation.",
    )
    out = Z["brdf"][..., production_bands]
    v = Z["observed"] & np.isfinite(raw).all(-1) & np.isfinite(out).all(-1)
    rec = dict(
        fixed_zoom_RGB_DN_equivalent_limits=lim.tolist(),
        generic_QA_RGB_nm=[668, 560, 475],
        generic_QA_RGB_BRDF_only_changed_values=int(np.count_nonzero(raw[v] != out[v])),
        named_band_map_RGB_nm=[650, 560, 444],
        diagnostic_RGB_nm=[650, 560, 475],
        fixed_vs_individual="Fixed scaling shares source limits across stages. Individual diagnostics estimate 2-98% per stage/channel and cannot compare numerical magnitude.",
        map_native_zoom_extent=E,
        zoom_resolution_m=0.1,
        full_overview_point_sampling="Stride6 Goldhill, stride8 Gordon/Ruby; coarse image cell centers are aligned to actual native centers; exact metrics remain native",
        polygons_primary="Positive source alpha and finite four-stage intersection; no source masks rewritten",
        spectral_display="DN equivalent = per-band min + stored S*(max-min)/10000; not calibrated reflectance",
        spectral_symlog_linear_threshold=10000,
    )
    (HERE / "display_contract.json").write_text(json.dumps(rec, indent=2) + "\n")
    if ONLY:
        existing = {
            r["name"]: r
            for r in json.loads((HERE / "figure_manifest.json").read_text())
        }
        existing.update({r["name"]: r for r in FIGURES})
        FIGURES[:] = [existing[k] for k in sorted(existing)]
    (HERE / "figure_manifest.json").write_text(json.dumps(FIGURES, indent=2) + "\n")
    print("High-resolution PNG/SVG figures complete.", flush=True)


if __name__ == "__main__":
    main()
