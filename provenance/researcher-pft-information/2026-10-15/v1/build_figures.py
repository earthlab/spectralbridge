"""Fourteen researcher-only publication figures from saved numerical products."""

import json
import hashlib
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from common import BASE, REPO, save
from spectralbridge.researcher_information import RESEARCHER_CATEGORIES
from spectralbridge.pft_method_audit import wavelength_weights

T = BASE / "tables"
F = BASE / "figures"
F.mkdir(exist_ok=True)
C = list(RESEARCHER_CATEGORIES)
METHODS = [
    "Training prior",
    "FCLS",
    "MESMA",
    "Ridge",
    "PLS",
    "Random forest",
    "Gradient boosting",
    "Two-stage",
]
COLORS = dict(
    zip(
        METHODS,
        [
            "#aaaaaa",
            "#777777",
            "#b85a3b",
            "#276f91",
            "#5b8a67",
            "#8f6bab",
            "#d49731",
            "#355555",
        ],
    )
)
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "svg.hashsalt": "researcher-information-v1",
        "pdf.fonttype": 42,
    }
)
manifest = []


def read(name):
    return (
        pd.read_parquet(T / name)
        if name.endswith(".parquet")
        else pd.read_csv(T / name)
    )


def finish(fig, number, title, caption, sources):
    if not getattr(fig, "_manual_layout", False):
        fig.tight_layout()
    name = f"R{number:02d}_" + title
    for ext in ["png", "pdf", "svg"]:
        meta = (
            {"CreationDate": None, "ModDate": None}
            if ext == "pdf"
            else {"Date": None}
            if ext == "svg"
            else {"Software": "SpectralBridge"}
        )
        fig.savefig(F / (name + "." + ext), dpi=300, bbox_inches="tight", metadata=meta)
    plt.close(fig)
    manifest.append(
        dict(
            number=number,
            name=name,
            caption=caption,
            sources=sources,
            hashes={
                ext: hashlib.sha256((F / (name + "." + ext)).read_bytes()).hexdigest()
                for ext in ["png", "pdf", "svg"]
            },
        )
    )


def spectral_axis(ax):
    for a, b in [(1340, 1450), (1790, 2000)]:
        ax.axvspan(a, b, color="#d7dce0", zorder=4, alpha=0.75)
    ax.set_xlim(382.5, 2512.5)
    ax.set_xlabel("Wavelength (nm); atmospheric gaps shaded")
    ax.set_xticks([400, 700, 1000, 1300, 1600, 1900, 2200, 2500])
    for label, lo, hi, color in [
        ("Visible", 385, 700, "#708ea4"),
        ("RE", 700, 750, "#ba704c"),
        ("NIR", 750, 1340, "#6a997a"),
        ("SWIR1", 1450, 1790, "#8b789d"),
        ("SWIR2", 2000, 2510, "#bf9c5a"),
    ]:
        ax.plot(
            [lo, hi],
            [1.025, 1.025],
            transform=ax.get_xaxis_transform(),
            color=color,
            lw=3,
            clip_on=False,
        )
        ax.text(
            (lo + hi) / 2,
            1.04,
            label,
            transform=ax.get_xaxis_transform(),
            ha="center",
            fontsize=8,
            clip_on=False,
        )
    ax.title.set_y(1.13)


def heat(ax, frame, value, title, vmin, vmax, cmap="viridis", rows="pair"):
    full = np.arange(385, 2515, 5)
    order = list(dict.fromkeys(frame[rows]))
    matrix = frame.pivot_table(
        index=rows, columns="wavelength_nm", values=value, aggfunc="mean"
    ).reindex(index=order, columns=full)
    im = ax.imshow(
        matrix.to_numpy(),
        aspect="auto",
        origin="upper",
        extent=(382.5, 2512.5, len(order) - 0.5, -0.5),
        vmin=vmin,
        vmax=vmax,
        cmap=cmap,
        interpolation="nearest",
    )
    ax.set_yticks(range(len(order)), order)
    ax.tick_params(axis="y", labelsize=10)
    ax.set_title(title, loc="left", weight="bold", pad=34)
    spectral_axis(ax)
    bands = json.loads(
        (REPO / "src/spectralbridge/data/landsat_band_parameters.json").read_text()
    )["Landsat 8 OLI"]
    for w, width in zip(bands["wavelengths"], bands["fwhms"]):
        ax.plot(w, -0.58, "v", color="black", markersize=4, clip_on=False)
        ax.hlines(
            -0.58, w - width / 2, w + width / 2, color="black", lw=2, clip_on=False
        )
    return im


def macro(frame):
    keys = ["fold", "kind", "target", "method", "representation"]
    return (
        frame.assign(MSE=frame.RMSE**2)
        .groupby(keys)
        .MSE.mean()
        .pow(0.5)
        .rename("fraction_RMSE")
        .reset_index()
    )


def main():
    atlas = read("researcher_pft_information_atlas.csv")
    cohort = read("cohort_wavelength_inference.csv")
    features = read("complementary_feature_performance.csv")
    abundance = read("abundance_model_comparison.parquet")
    primary = abundance[
        abundance.method.isin(METHODS) & abundance.representation.isin(["NEON", "OLI"])
    ]
    m = macro(primary)
    # 1: readable category-only matched overview.
    effects = pd.DataFrame(
        [
            dict(
                pair=pair,
                site=site,
                year=year,
                effect=float(
                    np.sqrt(
                        np.sum(
                            wavelength_weights(g.wavelength_nm.to_numpy())
                            * g.matched_effect.to_numpy() ** 2
                        )
                    )
                ),
                supported_coordinates=int((g.adjusted_p <= 0.05).sum()),
            )
            for (pair, site, year), g in cohort.groupby(["pair", "site", "year"])
        ]
    )
    save(effects, "whole_spectrum_effect_overview.csv")
    fig, axes = plt.subplots(
        1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.1, 1]}
    )
    pivot = effects.assign(cohort=effects.site + " " + effects.year.astype(str)).pivot(
        index="pair", columns="cohort", values="effect"
    )
    im = axes[0].imshow(pivot, aspect="auto", cmap="YlGnBu")
    axes[0].set_yticks(range(len(pivot)), pivot.index, fontsize=9)
    axes[0].set_xticks(range(4), pivot.columns, rotation=30, ha="right")
    axes[0].set_title("A  Matched standardized curve magnitude")
    fig.colorbar(im, ax=axes[0], label="Wavelength-weighted RMS contrast")
    rates = read("class_specific_transfer.csv")
    r = rates[rates.budget.eq("360")]
    for k, (kind, color) in enumerate([("plant", "#277591"), ("site", "#b97147")]):
        y = r[r.kind.eq(kind)].groupby("researcher_category").recall.mean().reindex(C)
        axes[1].barh(
            np.arange(5) + (k - 0.5) * 0.28,
            y,
            0.28,
            label="New polygon" if kind == "plant" else "Held site",
            color=color,
        )
    axes[1].set_yticks(range(5), C)
    axes[1].set_xlim(0, 1)
    axes[1].set_xlabel("Mean fold class recall (NEON full)")
    axes[1].legend(loc="lower right")
    axes[1].set_title("B  Difference is not recognition")
    finish(
        fig,
        1,
        "researcher_category_overview",
        "A: full-cohort acquisition-matched descriptive effects, not Cohen d. B: nested full-spectrum logistic class recall. Five recorded classes only; within-class spread and domain dependence remain.",
        ["cohort_wavelength_inference.csv", "class_specific_transfer.csv"],
    )
    # 2: effects and joint inferential support, without gap interpolation.
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    im = heat(
        axes[0],
        atlas,
        "matched_effect_mean",
        "A  Signed matched effect: first category minus second",
        -max(1.0, float(np.ceil(atlas.matched_effect_mean.abs().max() * 2) / 2)),
        max(1.0, float(np.ceil(atlas.matched_effect_mean.abs().max() * 2) / 2)),
        "RdBu_r",
    )
    fig.colorbar(im, ax=axes[0], label="Mean standardized coefficient")
    im = heat(
        axes[1],
        atlas,
        "training_supported_outer_designs",
        "B  Outer-training designs with corrected coordinate support",
        0,
        8,
        "YlGnBu",
    )
    fig.colorbar(im, ax=axes[1], label="Outer-training designs with adjusted p <= .05")
    finish(
        fig,
        2,
        "wavelength_effect_and_support",
        "A: full-cohort descriptive effects. B: training-only max-T and within-design Bonferroni support in eight outer-training designs, which overlap and are not independent replications. No inference map selects predictive features. Triangles/short bars mark configured OLI centers/FWHM. Visible <700; red edge 700-750; NIR 750-1340; SWIR1 1450-1790; SWIR2 2000-2510 nm.",
        ["researcher_pft_information_atlas.csv"],
    )
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    im = heat(
        axes[0],
        atlas,
        "new_polygon_BA",
        "A  Single-wavelength discrimination: new polygons",
        0,
        1,
        "RdYlBu",
    )
    fig.colorbar(im, ax=axes[0], label="Mean fold BA; two-class chance = .5")
    im = heat(
        axes[1],
        atlas,
        "held_site_BA_min",
        "B  Weakest observed held-site result",
        0,
        1,
        "RdYlBu",
    )
    fig.colorbar(im, ax=axes[1], label="Minimum site BA; two-class chance = .5")
    finish(
        fig,
        3,
        "single_wavelength_prediction",
        "Balanced-prior univariate LDA; direction and threshold trained without target identities. Mean versus weakest-site performance are different views. These are estimates for one rule, not a theoretical information bound.",
        [
            "single_wavelength_discrimination.parquet",
            "researcher_pft_information_atlas.csv",
        ],
    )
    # 4: matched curves with explicitly colored predictive separability.
    pairs = [
        "Deciduous / Evergreen",
        "Deciduous / Woody shrub",
        "Evergreen / Herbaceous",
        "Herbaceous / Woody shrub",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    norm = Normalize(0.4, 0.9)
    for ax, pair in zip(axes.ravel(), pairs):
        a = atlas[atlas.pair.eq(pair)].sort_values("wavelength_nm")
        x = a.wavelength_nm.to_numpy()
        y = a.matched_effect_mean.to_numpy()
        v = a.held_site_BA_min.to_numpy()
        segments = np.stack([np.c_[x[:-1], y[:-1]], np.c_[x[1:], y[1:]]], axis=1)
        good = np.diff(x) <= 8
        lc = LineCollection(segments[good], cmap="viridis", norm=norm, linewidth=3)
        lc.set_array((v[:-1][good] + v[1:][good]) / 2)
        ax.add_collection(lc)
        ax.set_ylim(min(-0.4, y.min() - 0.1), max(0.4, y.max() + 0.1))
        ax.axhline(0, color="gray", lw=0.7)
        spectral_axis(ax)
        ax.set_title(pair, fontsize=11, pad=32)
        ax.set_ylabel("Mean signed matched effect")
    color_axis = fig.add_axes([0.90, 0.18, 0.015, 0.65])
    fig.colorbar(lc, cax=color_axis, label="Weakest-site single-wavelength BA")
    # manual room avoids tight_layout/colorbar collision
    fig.subplots_adjust(right=0.83, wspace=0.3, hspace=0.4)
    fig._manual_layout = True
    finish(
        fig,
        4,
        "spectral_curves_colored_by_discrimination",
        "Four declared illustrations; all ten pairs are in the atlas. Effect height describes matched group differences; color describes a separate held-site predictor. Segments do not cross atmospheric gaps.",
        ["researcher_pft_information_atlas.csv"],
    )
    recall = read("single_wavelength_class_recall.csv")
    recall = recall[recall.sensor.eq("NEON")]
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    for ax, kind, title in [
        (axes[0], "plant", "A  New polygon: mean recall"),
        (axes[1], "site", "B  Held site: minimum recall"),
    ]:
        g = (
            recall[recall.kind.eq(kind)]
            .groupby(["researcher_category", "wavelength_nm"])
            .recall
        )
        f = (g.mean() if kind == "plant" else g.min()).reset_index()
        im = heat(ax, f, "recall", title, 0, 1, "YlGnBu", rows="researcher_category")
        fig.colorbar(im, ax=ax, label="Five-class single-coordinate recall")
    finish(
        fig,
        5,
        "class_recall_across_wavelengths",
        "Prespecified five-class balanced-prior nearest-mean discriminant. A single coordinate can separate two classes yet confuse the five-way classification. This differs from pairwise balanced accuracy and full-spectrum logistic recall.",
        ["single_wavelength_class_recall.csv"],
    )
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    im = heat(
        axes[0],
        atlas,
        "transfer_stability_score",
        "A  Transfer score: weakest observed site and effect-sign agreement",
        0,
        1,
    )
    fig.colorbar(im, ax=axes[0], label="Descriptive score; higher is more stable")
    im = heat(
        axes[1],
        atlas,
        "paired_year_max_absolute_BA_change",
        "B  Complete-pair NIWO temporal sensitivity",
        0,
        0.4,
        "magma",
    )
    fig.colorbar(im, ax=axes[1], label="Maximum absolute year change in BA")
    finish(
        fig,
        6,
        "site_year_stability",
        "Score=max(0,2*minimum held-site BA-1) times cohort sign consistency. It is a review aid over three observed sites. Temporal changes preserve target identities; annotations are reused later field labels. No geographic-population or annual-truth guarantee.",
        ["researcher_pft_information_atlas.csv", "domain_rank_consistency.csv"],
    )
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, kind in zip(axes[:2], ["plant", "site"]):
        g = features[features.kind.eq(kind)]
        for fold, f in g.groupby("fold"):
            regular = f[~f.budget.eq("OLI")].copy()
            regular["n"] = regular.budget.astype(int)
            regular = regular.sort_values("n")
            ax.plot(
                regular.n, regular.balanced_accuracy, marker="o", alpha=0.8, label=fold
            )
        ax.set_xscale("log")
        ax.set_ylim(0.2, 1)
        ax.set_xticks([1, 3, 10, 50, 100, 360], ["1", "3", "10", "50", "100", "360"])
        ax.set_xlabel("Nested complementary coordinates")
        ax.set_ylabel("Balanced accuracy")
        ax.set_title("New polygon" if kind == "plant" else "Held site")
        ax.legend(fontsize=8)
    a = np.load(T / "training_correlation_plant_0.npz")
    corr = a["correlation"]
    w = a["wavelength_nm"]
    im = axes[2].imshow(
        abs(corr), vmin=0, vmax=1, cmap="magma", origin="lower", interpolation="nearest"
    )
    axes[2].set_title("Training-only absolute correlation")
    ticks = [np.argmin(abs(w - x)) for x in [400, 800, 1200, 1600, 2200, 2500]]
    axes[2].set_xticks(ticks, w[ticks].astype(int), rotation=45)
    axes[2].set_yticks(ticks, w[ticks].astype(int))
    axes[2].set_xlabel("Supported coordinate (nm)")
    axes[2].set_ylabel("Supported coordinate (nm)")
    fig.colorbar(im, ax=axes[2], label="|Pearson r|")
    clusters = fcluster(
        linkage(
            squareform(np.clip(1 - abs(corr), 0, 1), checks=False), method="average"
        ),
        0.1,
        criterion="distance",
    )
    save(
        pd.DataFrame(
            {"wavelength_nm": w, "training_correlation_cluster_at_abs_r_09": clusters}
        ),
        "training_correlation_clusters.csv",
    )
    finish(
        fig,
        7,
        "complementary_measurement_budgets",
        "All selection and C tuning refit inside group-aware inner folds. Correlation panel compresses unsupported gaps in its coordinate index and interpolates no missing channel. The greedy residual criterion seeks complementary information; it is not an optimized sensor.",
        [
            "complementary_feature_performance.csv",
            "complementary_selection.csv",
            "training_correlation_clusters.csv",
        ],
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    retention = pd.read_csv(
        T / "reused_researcher_sensor_effect_retention.csv"
    )
    retention = retention[retention.scheme.eq("researcher_category")]
    # infer column names from retained canonical table
    xcol = (
        next(
            c
            for c in [
                "NEON_effect",
                "neon_effect",
                "NEON_RMS",
                "NEON_delta",
                "neon_delta",
            ]
            if c in retention
        )
        if any(
            c in retention
            for c in [
                "NEON_effect",
                "neon_effect",
                "NEON_RMS",
                "NEON_delta",
                "neon_delta",
            ]
        )
        else None
    )
    if xcol:
        ycol = next(
            c
            for c in ["OLI_effect", "oli_effect", "OLI_RMS", "OLI_delta", "oli_delta"]
            if c in retention
        )
        axes[0].scatter(retention[xcol], retention[ycol])
        axes[0].plot([0, 2], [0, 2], "--", color="gray")
        axes[0].set_xlabel("Matched NEON effect")
        axes[0].set_ylabel("Synthetic OLI effect")
    else:
        # Direct tabulated ratio is sufficient and avoids changing its metric.
        ratio = next(
            c
            for c in retention
            if "ratio" in c and not any(s in c for s in ["lo", "hi", "width"])
        )
        axes[0].hist(retention[ratio], bins=12, color="#277591")
        axes[0].axvline(1, color="gray", ls="--")
        axes[0].set_xlabel("OLI / NEON standardized effect ratio")
        axes[0].set_ylabel("Dependent pair/cohort contrasts")
    axes[0].set_title("A  Researcher-category contrasts; 40/40 retained")
    for i, (kind, color) in enumerate([("plant", "#277591"), ("site", "#b97147")]):
        for j, budget in enumerate(["360", "OLI"]):
            values = features[
                features.kind.eq(kind) & features.budget.eq(budget)
            ].balanced_accuracy
            axes[1].bar(
                i * 3 + j, values.mean(), color=color, alpha=1 if j == 0 else 0.55
            )
            axes[1].scatter(
                np.full(len(values), i * 3 + j), values, color="black", s=16
            )
    axes[1].set_xticks(
        [0, 1, 3, 4],
        ["NEON\nnew polygon", "OLI\nnew polygon", "NEON\nheld site", "OLI\nheld site"],
    )
    axes[1].set_ylabel("Nested logistic balanced accuracy")
    axes[1].set_ylim(0, 1)
    axes[1].set_title("B  Retained statistical support is not retained accuracy")
    finish(
        fig,
        8,
        "NEON_to_synthetic_Landsat",
        "Identical class labels and paired source observations. OLI spectral convolution is synthetic, at native/polygon support; it does not supply independent sensor noise, a 30 m footprint or field validation.",
        [
            "complementary_feature_performance.csv",
            "reused_researcher_sensor_effect_retention.csv",
        ],
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, kind in zip(axes, ["plant", "site"]):
        for i, method in enumerate(METHODS):
            for j, rep in enumerate(["NEON", "OLI"]):
                v = m[
                    m.kind.eq(kind) & m.method.eq(method) & m.representation.eq(rep)
                ].fraction_RMSE
                ax.bar(
                    i + (j - 0.5) * 0.32,
                    v.mean(),
                    0.3,
                    color=COLORS[method],
                    alpha=1 if j == 0 else 0.4,
                )
                ax.scatter(
                    np.full(len(v), i + (j - 0.5) * 0.32), v, color="black", s=12
                )
        ax.set_xticks(range(len(METHODS)), METHODS, rotation=35, ha="right")
        ax.set_title(
            "New-polygon parent tests"
            if kind == "plant"
            else "Entire held-site parent tests"
        )
        ax.set_ylabel("Class-balanced synthetic fraction RMSE")
    finish(
        fig,
        9,
        "abundance_model_benchmark",
        "Solid bars: NEON; pale bars: OLI. Dots are outer folds, not independent fraction levels. All methods use identical parent-disjoint targets; 120 proper and40 tuning parents per fold, up to60 test parents. These are synthetic weights, not field cover.",
        ["abundance_model_comparison.parquet", "abundance_paired_uncertainty.csv"],
    )
    grid = read("abundance_by_true_fraction.csv")
    for number, metric, title, ylabel in [
        (
            10,
            "prediction_mean",
            "predicted_vs_known_fraction",
            "Mean estimated synthetic fraction",
        ),
        (
            11,
            "detection_probability",
            "detection_vs_known_fraction",
            "Detection: estimated fraction > .10",
        ),
    ]:
        fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True, sharey=True)
        shown = (
            METHODS
            if number == 10
            else ["MESMA", "Ridge", "Gradient boosting", "Two-stage"]
        )
        for ax, c in zip(axes.ravel(), C):
            for method in shown:
                g = (
                    grid[
                        grid.kind.eq("plant")
                        & grid.representation.eq("NEON")
                        & grid.method.eq(method)
                        & grid.researcher_category.eq(c)
                    ]
                    .groupby("true_fraction")[metric]
                    .mean()
                )
                ax.plot(
                    g.index,
                    g,
                    marker="o",
                    markersize=3,
                    label=method,
                    color=COLORS[method],
                )
            if number == 10:
                ax.plot([0, 1], [0, 1], ls="--", color="gray")
            ax.set_title(c, fontsize=11)
            ax.set_xlabel("Known synthetic fraction")
            ax.set_ylabel(ylabel)
            ax.set_ylim(-0.03, 1.03)
        axes.ravel()[5].axis("off")
        handles, labels = axes.ravel()[0].get_legend_handles_labels()
        axes.ravel()[5].legend(handles, labels, loc="center", frameon=False)
        finish(
            fig,
            number,
            title,
            "Curves average the three new-polygon folds; complete grids for all methods/domains are saved. At true zero, positive detection is false detection. The .10 cutoff is declared, not a universal detection limit. Mixtures sharing parents are dependent.",
            ["abundance_by_true_fraction.csv"],
        )
    ambiguity = read("abundance_by_ambiguity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, kind in zip(axes, ["plant", "site"]):
        for method in METHODS:
            g = (
                ambiguity[
                    ambiguity.kind.eq(kind)
                    & ambiguity.method.eq(method)
                    & ambiguity.representation.eq("NEON")
                ]
                .groupby("ambiguity")
                .fraction_RMSE.mean()
                .reindex(["Low", "Moderate", "High"])
            )
            ax.plot(range(3), g, marker="o", label=method, color=COLORS[method])
        ax.set_xticks(range(3), ["Low <.10", "Moderate .10-.30", "High >=.30"])
        ax.set_ylabel("Synthetic fraction RMSE")
        ax.set_xlabel("Maximum near-solution class-fraction range")
        ax.set_title("New polygon" if kind == "plant" else "Held site")
    axes[1].legend(fontsize=8)
    finish(
        fig,
        12,
        "abundance_error_and_ambiguity",
        "Strata are shared across every method, using full-NEON MESMA near solutions within .01 training-RMS-scaled tolerance. Missing strata are unsupported. This diagnoses a candidate-library inverse problem, not intrinsic physical ambiguity or calibrated intervals.",
        ["abundance_by_ambiguity.csv"],
    )
    fig, ax = plt.subplots(figsize=(14, 6))
    d = m[m.representation.eq("NEON") & ~m.kind.eq("plant")].copy()
    d["domain"] = d.fold + " / " + d.target
    matrix = d.pivot(index="method", columns="domain", values="fraction_RMSE").reindex(
        METHODS
    )
    im = ax.imshow(
        matrix,
        aspect="auto",
        vmin=0,
        vmax=max(0.4, np.nanmax(matrix.to_numpy())),
        cmap="magma_r",
    )
    ax.set_yticks(range(len(METHODS)), METHODS)
    ax.set_xticks(
        range(len(matrix.columns)),
        [
            s.replace(" / ", "\n")
            .replace("paired_train", "train ")
            .replace("target", "target ")
            .replace("site_", "site ")
            .replace("year_", "year ")
            for s in matrix.columns
        ],
        rotation=30,
        ha="right",
    )
    for i in range(len(matrix)):
        for j in range(len(matrix.columns)):
            ax.text(
                j,
                i,
                f"{matrix.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if matrix.iloc[i, j] > 0.22 else "black",
            )
    fig.colorbar(im, ax=ax, label="Synthetic fraction RMSE; lower better")
    ax.set_title("Held-site, global-year and complete-pair temporal targets")
    finish(
        fig,
        13,
        "abundance_domain_transfer",
        "Global year holds alter site composition. Paired NIWO directions reuse the same held-out target IDs/fractions in both years, with other IDs for proper/tuning pools. Annotation labels are retrospective. Each cell is conditional on sampled parent bundles.",
        ["abundance_model_comparison.parquet"],
    )
    # Final evidence data, never an averaged readiness score.
    rows = []
    for kind in ["plant", "site"]:
        full = features[
            features.kind.eq(kind) & features.budget.eq("360")
        ].balanced_accuracy.mean()
        oli = features[
            features.kind.eq(kind) & features.budget.eq("OLI")
        ].balanced_accuracy.mean()
        rows.append(
            dict(
                question="Five-category recognition: " + kind,
                value=f"NEON {full:.1%}; synthetic OLI {oli:.1%}",
                scope="Supported labelled polygon identities; nested CV",
                decision="Conditional evidence",
            )
        )
    for kind in ["plant", "site"]:
        values = (
            m[m.kind.eq(kind) & m.representation.eq("NEON")]
            .groupby("method")
            .fraction_RMSE.mean()
        )
        best = values.drop(["FCLS", "MESMA", "Training prior"]).idxmin()
        rows.append(
            dict(
                question="Synthetic fraction recovery: " + kind,
                value=f"MESMA {values['MESMA']:.3f}; lowest observed {best} {values[best]:.3f}",
                scope="Fixed parent budget; outer comparison is exploratory",
                decision="Conditional synthetic evidence",
            )
        )
    rows.append(
        dict(
            question="Independent field abundance",
            value="No independent complete fraction truth supplied",
            scope="Researcher cover labels do not certify purity",
            decision="Not established",
        )
    )
    summary = pd.DataFrame(rows)
    save(summary, "final_evidence_summary.csv")
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis("off")
    table = ax.table(
        cellText=summary[["question", "value", "decision"]].values,
        colLabels=["Question", "Measured result", "Evidence status"],
        cellLoc="left",
        loc="center",
        colWidths=[0.28, 0.52, 0.20],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 3)
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#225367")
            cell.set_text_props(color="white", weight="bold")
        elif r == 5:
            cell.set_facecolor("#edd8cf")
        else:
            cell.set_facecolor("#e5eef0")
    finish(
        fig,
        14,
        "final_researcher_evidence",
        "Evidence status is use-specific, not an aggregate score. Lowest observed outer score is descriptive, not a tuning choice or multiplicity-corrected winner. No synthetic success is promoted to field abundance validation.",
        ["final_evidence_summary.csv"],
    )
    (BASE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (BASE / "FIGURE_CAPTIONS.md").write_text(
        "# Researcher-category publication figures\n\n"
        + "\n\n".join(
            f"## {f['name']}\n\n{f['caption']}\n\nSources: " + ", ".join(f["sources"])
            for f in manifest
        )
        + "\n"
    )
    print("Built", len(manifest), "researcher-only figure families")


if __name__ == "__main__":
    main()
