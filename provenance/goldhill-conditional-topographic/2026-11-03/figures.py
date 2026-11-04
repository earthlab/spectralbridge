"""Scientific figures; robust display limits never modify analytical arrays."""

import json
from pathlib import Path
import sys
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import WAVES  # noqa: E402

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
ORDER = [
    "raw",
    "historical",
    "current",
    "eligible_OLS",
    "robust_Huber",
    "stabilized",
    "cosine",
]
LABELS = [
    "Raw",
    "Historical",
    "Current",
    "Eligible OLS",
    "Robust Huber",
    "Stabilized",
    "Cosine",
]
COLORS = ["#526b79", "#c14e3b", "#d38c38", "#955ca2", "#5a78b2", "#188b83", "#849238"]
manifest = []


def read(n):
    return json.loads((HERE / n).read_text())


def save(fig, n, title, caption):
    fig.suptitle(
        title + "\nConditional DN/32768 hypothesis - calibration unverified",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(HERE / (n + ".png"), bbox_inches="tight")
    fig.savefig(HERE / (n + ".svg"), bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(id=n, png=n + ".png", svg=n + ".svg", title=title, caption=caption)
    )


def main():
    d = np.load(HERE / "display_arrays.npz")
    geom = np.load(HERE / "geometry_arrays.npz")
    cfg = read("branches.json")
    g = pd.read_csv(HERE / "polygon_summaries.csv")
    g = g[g.support == "common"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    raw = [
        x
        for x in read("scene_statistics.json")
        if x["branch"] == "raw" and x["support"] == "common"
    ]
    med = np.array([x["quantiles"][4] for x in raw])
    axes[0].plot(WAVES, med, "o-", label="Candidate fractional reflectance")
    axes[0].plot(WAVES, med / (65535 / 32768), "x--", label="Numerical S/10000")
    axes[0].legend()
    axes[0].set(xlabel="Wavelength (nm)", ylabel="Scene median, same common pixels")
    scale = read("scale_invariance.json")
    axes[1].plot(WAVES, scale["C_candidate"], "o-", label="Candidate scale")
    axes[1].plot(WAVES, scale["C_fixed_fraction"], "x--", label="S/10000")
    axes[1].axhline(0, color="gray", lw=0.7)
    axes[1].legend()
    axes[1].set(
        xlabel="Wavelength (nm)",
        ylabel="Fitted C (identical)",
        title="Changing a common multiplier does not fix C",
    )
    save(
        fig,
        "figure01_scaling",
        "Scaling changes magnitude, not the SCS+C factors",
        "Exact multiplier 0.0001999969482421875; no offset. All ten fitted C values are identical at the tested scales. Spectral shape alone cannot verify calibration.",
    )
    fig, axes = plt.subplots(1, 4, figsize=(14, 4.7))
    for ax, (k, title) in zip(
        axes,
        [
            ("slope", "Slope (degrees)"),
            ("aspect", "Aspect (degrees)"),
            ("ci", "Illumination cos(i)"),
            ("shadow", "Local self-shadow"),
        ],
    ):
        a = (
            np.rad2deg(geom[k])
            if k in ["slope", "aspect"]
            else (geom["ci"] <= 0 if k == "shadow" else geom[k])
        )
        a = np.where(geom["mask"], a, np.nan)
        im = ax.imshow(a, cmap="twilight" if k == "aspect" else "viridis")
        fig.colorbar(im, ax=ax, shrink=0.65)
        ax.set_title(title)
        ax.axis("off")
    save(
        fig,
        "figure02_geometry",
        "Aligned geometry, with unresolved terrain provenance",
        "North is up on the common 10cm grid; images sampled every sixth cell. Self-shadow means cos(i)<=0, not a complete cast/canopy-shadow mask. Terrain resampling does not create new independent detail.",
    )
    times = read("solar_sensitivity.json")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    short = [
        "UTC midpoint",
        "UTC start",
        "UTC end",
        "UTC +5.5s",
        "Local MDT",
        "Package note",
    ]
    axes[0].bar(range(len(times)), [x["zenith_deg"] for x in times], color="#5a78b2")
    axes[0].set_xticks(range(len(times)), short, rotation=45, ha="right")
    axes[0].set(ylabel="Solar zenith (degrees)")
    axes[1].bar(
        range(len(times)),
        [x["red_factor"]["quantiles"][-1] for x in times],
        color="#a95342",
    )
    axes[1].set_xticks(range(len(times)), short, rotation=45, ha="right")
    axes[1].set(ylabel="Maximum red factor (refitted OLS)")
    maps = np.load(HERE / "solar_maps.npz")
    im = axes[2].imshow(
        np.where(
            geom["mask"],
            maps["local_MDT_interpretation"] - maps["UTC_inherited"],
            np.nan,
        ),
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
    )
    fig.colorbar(im, ax=axes[2])
    axes[2].set_title("Local-minus-UTC incidence")
    axes[2].axis("off")
    save(
        fig,
        "figure03_time",
        "Timestamp interpretation changes the model, not its provenance",
        "Solar geometry uses the existing approximate UTC package function at scene center for sensitivity. Local-time interpretation puts the sun near the horizon and can trigger neutral fallbacks; that is not evidence of successful correction. No case was selected for looking better.",
    )
    fits = read("coefficients.json")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    ci = geom["ci"]
    r = d["raw_red"]
    v = np.isfinite(r) & np.isfinite(ci)
    axes[0].hexbin(
        ci[v], r[v], gridsize=70, bins="log", mincnt=1, cmap="viridis", rasterized=True
    )
    axes[0].axvline(
        -fits["historical"][4], color="#ce4b36", ls="--", label="Pole: cos(i)=-C"
    )
    axes[0].legend(fontsize=8)
    axes[0].set(
        xlabel="Illumination cos(i)",
        ylabel="Raw candidate red",
        title="Surface variation confounds the scene fit",
    )
    den = ci[v] + fits["historical"][4]
    axes[1].hist(den, bins=150, color="#596e7c", log=True)
    axes[1].axvline(0.001, color="red", ls="--")
    axes[1].set(
        xlabel="Red denominator cos(i)+C",
        ylabel="Display-sampled pixels",
        title="A guard at .001 leaves a sharp boundary",
    )
    for name, color in [
        ("historical", COLORS[1]),
        ("stabilized", COLORS[5]),
        ("robust_Huber", COLORS[4]),
    ]:
        f = d[name + "_factor"]
        f = f[np.isfinite(f) & (f > 0)]
        axes[2].hist(
            f,
            bins=np.geomspace(0.1, 400, 100),
            histtype="step",
            label=name,
            color=color,
        )
    axes[2].set(
        xscale="log",
        yscale="log",
        xlabel="Red correction factor",
        ylabel="Display-sampled pixels",
    )
    axes[2].legend(fontsize=8)
    save(
        fig,
        "figure04_instability",
        "The red instability is denominator cancellation",
        "At row1178,col1533, cos(i)=0.3482566 and C=-0.3472517 leave denominator0.00100496 and factor309.9168. Positive illumination does not prevent cancellation. Huber moves the pole; it does not remove it.",
    )
    factors = read("factor_statistics.json")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for name, label, color in zip(ORDER[1:], LABELS[1:], COLORS[1:]):
        x = [a for a in factors if a["branch"] == name]
        axes[0].plot(
            WAVES, [a["quantiles"][-1] for a in x], ".-", label=label, color=color
        )
    axes[0].set(
        yscale="log",
        xlabel="Wavelength (nm)",
        ylabel="Maximum factor on native support",
    )
    axes[0].legend(fontsize=8, ncol=2)
    sizes = [cfg["raw_pixels"]] + [
        next(a["native_support"] for a in factors if a["branch"] == name)
        for name in ORDER[1:]
    ]
    axes[1].bar(LABELS, np.array(sizes) / cfg["raw_pixels"] * 100, color=COLORS)
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].set(ylim=(98, 100.1), ylabel="Raw footprint retained (%)")
    axes[1].axhline(100, color="gray", lw=0.6)
    save(
        fig,
        "figure05_support",
        "Resolved support reduces extremes; robust fitting alone does not",
        "Native supports are shown separately. Stabilized coverage is98.96% of raw, including existing geometry losses; no gain was capped. The cosine alternative is numerically extreme near local self-shadow and is not recommended.",
    )
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    vmax = np.nanquantile(d["raw_red"], 0.99)
    for ax, name in zip(
        axes.flat,
        ["raw", "historical", "current", "robust_Huber", "stabilized", "cosine"],
    ):
        a = d["raw_red"] if name == "raw" else d[name + "_red"]
        im = ax.imshow(a, cmap="viridis", vmin=0, vmax=vmax)
        ax.set_title(name)
        ax.axis("off")
    fig.subplots_adjust(top=0.85, right=0.88, hspace=0.15)
    fig.suptitle(
        "Red reflectance on native supports\nConditional DN/32768 hypothesis - calibration unverified",
        fontsize=14,
        weight="bold",
    )
    cax = fig.add_axes([0.91, 0.16, 0.015, 0.58])
    fig.colorbar(im, cax=cax, label="Candidate 650nm reflectance (display bounded)")
    fig.savefig(HERE / "figure06_red_maps.png", bbox_inches="tight")
    fig.savefig(HERE / "figure06_red_maps.svg", bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(
            id="figure06_red_maps",
            png="figure06_red_maps.png",
            svg="figure06_red_maps.svg",
            title="Red reflectance on each native support",
            caption="Identical grid, north up, every sixth cell. Common raw99th percentile controls display only; analytical extremes are retained. White is unsupported/missing. Candidate calibration remains unverified.",
        )
    )
    fig, axes = plt.subplots(1, 4, figsize=(14, 4.6))
    for ax, name in zip(axes[:3], ["historical", "robust_Huber", "stabilized"]):
        im = ax.imshow(
            d[name + "_factor"], norm=LogNorm(vmin=0.5, vmax=350), cmap="magma"
        )
        ax.set_title(name + " red factor")
        ax.axis("off")
    axes[3].imshow(
        np.where(geom["mask"], 1 - d["stable"], np.nan), cmap="Reds", vmin=0, vmax=1
    )
    axes[3].set_title("Excluded by stabilized support")
    axes[3].axis("off")
    fig.subplots_adjust(top=0.77, bottom=0.2, wspace=0.25)
    fig.suptitle(
        "Factors and excluded support\nConditional DN/32768 hypothesis - calibration unverified",
        fontsize=14,
        weight="bold",
    )
    cax = fig.add_axes([0.24, 0.12, 0.49, 0.025])
    fig.colorbar(
        im, cax=cax, orientation="horizontal", label="Red factor (logarithmic display)"
    )
    fig.savefig(HERE / "figure07_factor_maps.png", bbox_inches="tight")
    fig.savefig(HERE / "figure07_factor_maps.svg", bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(
            id="figure07_factor_maps",
            png="figure07_factor_maps.png",
            svg="figure07_factor_maps.svg",
            title="Where factors and exclusions occur",
            caption="Display factor limits0.5-350 do not clip analysis. Pole-adjacent regions become unsupported; the rule does not make new measurements. Unsupported boundaries can create selection bias and are tested using identical common pixels.",
        )
    )
    fig, axes = plt.subplots(1, 4, figsize=(14, 4.2))
    for ax, label in zip(axes, sorted(g.cover_category.unique())):
        identity = sorted(g[g.cover_category == label].GlobalID.unique())[0]
        for name, color in zip(ORDER, COLORS):
            row = g[(g.branch == name) & (g.GlobalID == identity)].iloc[0]
            ax.plot(
                WAVES,
                row[[f"b{i}" for i in range(1, 11)]].to_numpy(float),
                ".-",
                color=color,
                label=name,
            )
        ax.set_title(label)
        ax.set(xlabel="Wavelength (nm)", ylabel="Matched polygon mean candidate R")
    axes[0].legend(fontsize=7)
    save(
        fig,
        "figure08_spectra",
        "Matched spectra: first identity in each recorded class",
        "One outcome-blind lexicographic polygon per class, on identical common pixels. Curves are ten discrete optical bands, not a continuous hyperspectral measurement. Representative curves cannot establish physical accuracy.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    med = (
        g.groupby("branch")[["median_band_cv", "mean_variance", "within_angle_median"]]
        .median()
        .reindex(ORDER)
    )
    for ax, key, title in zip(
        axes,
        med.columns,
        [
            "Median polygon band CV",
            "Median within-polygon variance",
            "Median within-polygon angle (degrees)",
        ],
    ):
        ax.bar(LABELS, med[key], color=COLORS)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=45)
    save(
        fig,
        "figure09_consistency",
        "Smaller absolute variance is not uniformly better consistency",
        "All157 polygons use the same142,656 common memberships. Compare CV and spectral angles alongside absolute variance: multiplicative dimming can lower variance without improving relative spectral consistency.",
    )
    dep = pd.read_csv(HERE / "class_spatial_control.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for name, label, color in zip(ORDER, LABELS, COLORS):
        sub = dep[dep.branch == name]
        axes[0].plot(
            sub.wavelength_nm,
            sub.partial_illumination_pearson,
            ".-",
            label=label,
            color=color,
        )
    axes[0].axhline(0, color="gray", lw=0.7)
    axes[0].set(
        xlabel="Wavelength (nm)",
        ylabel="Partial illumination correlation",
        title="Class + linear spatial plane controlled",
    )
    axes[0].legend(fontsize=7, ncol=2)
    classes = pd.read_csv(HERE / "within_class.csv")
    q = classes.pivot(index="label", columns="branch", values="median_angle")
    q[["raw", "historical", "stabilized"]].plot.bar(
        ax=axes[1], color=[COLORS[0], COLORS[1], COLORS[5]]
    )
    axes[1].set(
        ylabel="Median angle to class centroid (degrees)", xlabel="Recorded class"
    )
    axes[1].tick_params(axis="x", rotation=25)
    save(
        fig,
        "figure10_dependence",
        "Illumination dependence and class variation can move differently",
        "Partial associations control recorded class and a linear spatial plane across independent polygon means. Spatial autocorrelation/nonlinear vegetation structure remain. Reducing correlation alone does not establish more accurate reflectance.",
    )
    scores = read("classification_summary.json")
    gains = {x["branch"]: x for x in read("paired_gain.json")}
    score = {x["branch"]: x["balanced_accuracy"] for x in scores}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    axes[0].bar(LABELS, [score[n] * 100 for n in ORDER], color=COLORS)
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].set(
        ylim=(0, 100),
        ylabel="Balanced accuracy (%)",
        title="Same157 identities and held-out folds",
    )
    for i, n in enumerate(ORDER):
        a = gains[n]
        axes[1].errorbar(
            a["difference"] * 100,
            i,
            xerr=np.array([[a["difference"] - a["low"]], [a["high"] - a["difference"]]])
            * 100,
            fmt="o",
            color=COLORS[i],
        )
    axes[1].set_yticks(range(7), LABELS)
    axes[1].axvline(0, color="gray", ls="--")
    axes[1].set(
        xlabel="Paired gain over raw (percentage points)",
        title="95% paired polygon interval",
    )
    cm = pd.read_csv(HERE / "confusion_stabilized.csv", index_col=0)
    im = axes[2].imshow(cm, cmap="Blues")
    axes[2].set_xticks(range(4), cm.columns, rotation=40, ha="right")
    axes[2].set_yticks(range(4), cm.index)
    axes[2].set(
        xlabel="Predicted class", ylabel="True class", title="Stabilized: counts"
    )
    for i in range(4):
        for j in range(4):
            axes[2].text(
                j,
                i,
                str(int(cm.iloc[i, j])),
                ha="center",
                va="center",
                color="white" if cm.iloc[i, j] > 50 else "black",
            )
    save(
        fig,
        "figure11_identifiability",
        "No established identification benefit from stabilized SCS+C",
        "Package classifier uses polygon-disjoint3fold validation, training-only scaling and fixed C=1. Intervals bootstrap fixed out-of-fold predictions by class/identity; they exclude model/coefficient/site uncertainty. Only5 deciduous polygons: one changed prediction shifts balanced accuracy by5 points.",
    )
    pair = pd.read_csv(HERE / "between_class.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, key, title in zip(
        axes,
        ["angle", "IQR_overlap"],
        ["Between-class centroid angle (degrees)", "Mean band IQR overlap"],
    ):
        for name, color in [
            ("raw", COLORS[0]),
            ("historical", COLORS[1]),
            ("stabilized", COLORS[5]),
        ]:
            s = pair[pair.branch == name]
            ax.plot(range(len(s)), s[key], "o-", label=name, color=color)
        ax.set_xticks(
            range(6),
            [
                x + " / " + y
                for x, y in pair[pair.branch == "raw"][["first", "second"]].to_numpy()
            ],
            rotation=45,
            ha="right",
        )
        ax.set_title(title)
        ax.legend(fontsize=8)
    save(
        fig,
        "figure12_separability",
        "Class separation is mixed, not universal",
        "Distances, overlap and permutation evidence are descriptive of one labeled flight. Package spectral_separability uses499 permutations, independent polygon units and equal discrete-band weights; significance within a branch does not test a correction gain.",
    )
    median = read("median_classification_summary.json")
    mean = read("classification_summary.json")
    fig, ax = plt.subplots(figsize=(11, 4.5))
    x = np.arange(7)
    ax.bar(
        x - 0.18,
        [
            next(v["balanced_accuracy"] for v in mean if v["branch"] == n) * 100
            for n in ORDER
        ],
        width=0.36,
        label="Polygon means (primary)",
        color="#188b83",
    )
    ax.bar(
        x + 0.18,
        [
            next(v["balanced_accuracy"] for v in median if v["branch"] == n) * 100
            for n in ORDER
        ],
        width=0.36,
        label="Polygon medians (sensitivity)",
        color="#7f91ad",
    )
    ax.set_xticks(x, LABELS)
    ax.set(ylim=(0, 100), ylabel="Common-support balanced accuracy (%)")
    ax.legend()
    save(
        fig,
        "figure13_summary_sensitivity",
        "Aggregation and support are part of the scientific comparison",
        "Means reproduce the earlier P169 aggregation; medians are a sensitivity analysis, not selected for a better score. Native-support contrasts and the old71.7% historical score use different masks and cannot be attributed solely to correction.",
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, key, title in [
        (axes[0], "stabilized_difference", "Stabilized minus raw,650 nm")
    ]:
        a = d[key]
        bound = np.nanquantile(abs(a), 0.99)
        im = ax.imshow(a, cmap="coolwarm", vmin=-bound, vmax=bound)
        fig.colorbar(im, ax=ax, shrink=0.65)
        ax.set_title(title)
        ax.axis("off")
    delta = d["stabilized_nir"] - d["raw_nir"]
    bound = np.nanquantile(abs(delta), 0.99)
    im = axes[1].imshow(delta, cmap="coolwarm", vmin=-bound, vmax=bound)
    fig.colorbar(im, ax=axes[1], shrink=0.65)
    axes[1].set_title("Stabilized minus raw,862 nm")
    axes[1].axis("off")
    a = np.where(
        np.isfinite(d["historical_factor"]), d["historical_factor"] > 10, np.nan
    )
    axes[2].imshow(a, cmap="Reds", vmin=0, vmax=1)
    peak = read("extreme_pixels.json")[0]
    axes[2].scatter(
        peak["col"] / 6,
        peak["row"] / 6,
        marker="*",
        s=120,
        color="#159dcb",
        edgecolors="black",
        linewidth=0.5,
    )
    axes[2].set_title("Historical red factor>10;star=maximum")
    axes[2].axis("off")
    save(
        fig,
        "figure14_differences",
        "Changes and extreme-factor locations",
        "Signed differences are candidate reflectance on stabilized support;99th-percentile display bounds do not alter measurements. Right: sampled positions with historical red gain>10;star marks actual native maximum at row1178,column1533. The threshold10 is descriptive only, not the eligibility rule.",
    )
    (HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(len(manifest), "figure pairs generated")


if __name__ == "__main__":
    main()
