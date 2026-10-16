"""Ten information-dense figures with numerical sources and disconnected spectra."""

from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from run_controls import BASE, REPO, PRIOR, CATS

T = BASE / "tables"
O = PRIOR / "tables"
F = BASE / "figures"
F.mkdir(exist_ok=True)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "svg.fonttype": "none",
        "svg.hashsalt": "three-question-v1",
        "pdf.fonttype": 42,
        "figure.facecolor": "white",
    }
)
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
            "#858585",
            "#b47729",
            "#c5423b",
            "#166aab",
            "#724c9f",
            "#3c9064",
            "#d17c9d",
            "#b7a21b",
        ],
    )
)
SHORT = ["Deciduous", "Evergreen", "Herbaceous", "Non-veg. & dead", "Woody shrub"]
manifest = []


def read(name, old=False):
    return pd.read_csv((O if old else T) / name)


def finish(fig, number, name, title, how, learn, uncertain, sources):
    fig.suptitle(title, fontsize=17, fontweight="bold", y=1.015)
    fig.tight_layout()
    stem = f"F{number:02}_{name}"
    for ext in ["png", "pdf", "svg"]:
        meta = (
            {"CreationDate": None, "ModDate": None}
            if ext == "pdf"
            else {"Date": None}
            if ext == "svg"
            else {"Software": "SpectralBridge"}
        )
        fig.savefig(F / (stem + "." + ext), dpi=240, bbox_inches="tight", metadata=meta)
    plt.close(fig)
    manifest.append(
        dict(
            number=number,
            name=stem,
            title=title,
            how=how,
            learn=learn,
            uncertain=uncertain,
            sources=sources,
            hashes={
                ext: hashlib.sha256((F / (stem + "." + ext)).read_bytes()).hexdigest()
                for ext in ["png", "pdf", "svg"]
            },
        )
    )


def heat(
    ax, matrix, rows, cols, title, cmap="viridis", vmin=None, vmax=None, annotate=False
):
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_yticks(range(len(rows)), rows)
    ax.set_xticks(range(len(cols)), cols, rotation=35, ha="right")
    ax.set_title(title)
    if annotate:
        for i in range(len(rows)):
            for j in range(len(cols)):
                value = np.asarray(matrix)[i, j]
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="black"
                    if np.dot(im.cmap(im.norm(value))[:3], [0.2126, 0.7152, 0.0722])
                    > 0.52
                    else "white",
                )
    return im


def spectra(ax, w, Z, cmap, vmin, vmax):
    for ix in np.split(np.arange(len(w)), np.flatnonzero(np.diff(w) > 10) + 1):
        edges = np.r_[w[ix] - 2.5, w[ix[-1]] + 2.5]
        im = ax.pcolormesh(
            edges,
            np.arange(Z.shape[0] + 1) - 0.5,
            Z[:, ix],
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            rasterized=True,
            shading="flat",
        )
    ax.set_xlim(w.min() - 3, w.max() + 3)
    ax.set_ylim(Z.shape[0] - 0.5, -0.5)
    ax.set_xticks([500, 1000, 1500, 2000, 2400])
    ax.set_facecolor("#dedede")
    return im


def main():
    fig, ax = plt.subplots(2, 2, figsize=(15, 8))
    support = read("category_support.csv").set_index("researcher_category").loc[CATS]
    ax[0, 0].barh(SHORT, support.GlobalIDs, color="#287e8a")
    ax[0, 0].invert_yaxis()
    ax[0, 0].set_xlabel("Distinct polygon GlobalIDs")
    ax[0, 0].set_title("Five labelled categories; unequal sample sizes")
    for i, v in enumerate(support.GlobalIDs):
        ax[0, 0].text(v + 10, i, str(v), va="center")
    s = read("site_year_category_support.csv")
    s["domain"] = s.site + " " + s.year.astype(str)
    p = s.pivot(index="researcher_category", columns="domain", values="GlobalIDs").loc[
        CATS
    ]
    im = heat(
        ax[0, 1],
        p,
        SHORT,
        p.columns,
        "Only NIWO has repeated acquisition years",
        vmin=0,
        vmax=float(p.max().max()),
    )
    fig.colorbar(im, ax=ax[0, 1], label="GlobalIDs per observed cell")
    a = json.loads((BASE / "foundation.json").read_text())
    text = f"{a['source_pixel_rows']:,} extracted pixel records\n\u2193 summarize within footprint/acquisition\n{a['polygon_year_spectra']:,} polygon/year spectra\n\u2193 cluster repeated acquisitions\n{a['polygon_GlobalIDs']:,} independent polygon IDs\n\n{a['repeated_IDs']:,} IDs observed in both years\nPixels, channels and mixtures are not replicates."
    ax[1, 0].text(
        0.05,
        0.95,
        text,
        transform=ax[1, 0].transAxes,
        va="top",
        fontsize=14,
        linespacing=1.5,
    )
    ax[1, 0].axis("off")
    status = (
        read("design_validation.csv")
        .groupby(["section", "status"])
        .size()
        .unstack(fill_value=0)
    )
    status.reindex(
        ["FOUNDATION", "SEPARABILITY", "IDENTIFIABILITY", "ABUNDANCE"]
    ).plot.barh(
        stacked=True,
        color={"PASS": "#33936c", "FAIL": "#c7473b", "NOT TESTABLE": "#9a9a9a"},
        ax=ax[1, 1],
    )
    ax[1, 1].set_title("Requirement audit includes negative findings")
    ax[1, 1].set_xlabel("Requirements")
    ax[1, 1].set_ylabel("")
    ax[1, 1].legend(fontsize=9)
    finish(
        fig,
        1,
        "foundation",
        "The biological sampling unit is the polygon, not the pixel",
        "Counts use distinct GlobalIDs. A repeated ID can occur in two acquisition-year cells. Audit FAIL refers to a tested claim failing, not a concealed pipeline error.",
        "The library has broad category coverage but only four site/year cells. The experimental independence and truth limits are explicit.",
        "Polygon purity, absolute reflectance units and independent annual/field fraction truth are not verified. Distinct nearby polygons can remain spatially correlated.",
        [
            "tables/category_support.csv",
            "tables/site_year_category_support.csv",
            "foundation.json",
            "tables/design_validation.csv",
        ],
    )
    whole = read("whole_spectrum_separability.csv")
    pairs = list(whole.contrast.unique())
    domains = sorted(
        whole.assign(domain=whole.site + " " + whole.year.astype(str)).domain.unique()
    )
    whole["domain"] = whole.site + " " + whole.year.astype(str)
    fig, ax = plt.subplots(2, 2, figsize=(16, 9))
    m = whole.pivot(index="contrast", columns="domain", values="NEON_effect").loc[
        pairs, domains
    ]
    im = heat(
        ax[0, 0],
        m,
        pairs,
        domains,
        "Matched whole-spectrum effect (standardized RMS)",
        vmin=0,
        vmax=float(m.max().max()),
    )
    fig.colorbar(im, ax=ax[0, 0], label="Standardized effect")
    for domain, g in whole.groupby("domain"):
        ax[0, 1].scatter(g.NEON_effect, g.OLI_effect, label=domain, s=45)
    lim = max(whole.NEON_effect.max(), whole.OLI_effect.max()) * 1.05
    ax[0, 1].plot([0, lim], [0, lim], "k--", lw=1)
    ax[0, 1].set(
        xlabel="NEON effect",
        ylabel="Synthetic OLI effect",
        title="Effect magnitude after shared-source convolution",
    )
    ax[0, 1].legend(fontsize=9)
    for i, pair in enumerate(pairs):
        g = whole[whole.contrast.eq(pair)]
        ax[1, 0].plot(
            [g.OLI_NEON_ratio.min(), g.OLI_NEON_ratio.max()],
            [i, i],
            color="#1d7182",
            lw=3,
        )
        ax[1, 0].scatter(g.OLI_NEON_ratio, np.repeat(i, len(g)), s=20, color="#1d7182")
    ax[1, 0].set_yticks(range(len(pairs)), pairs)
    ax[1, 0].invert_yaxis()
    ax[1, 0].axvline(1, color="grey", ls="--")
    ax[1, 0].set(
        xlabel="OLI / NEON effect magnitude",
        title="Every cohort retained; ratio can exceed one",
    )
    reg = (
        read("region_separability.csv")
        .groupby(["pair", "region"])
        .mean_abs_effect.mean()
        .unstack()
        .loc[pairs, ["Visible", "Red edge", "NIR", "SWIR1", "SWIR2"]]
    )
    im = heat(
        ax[1, 1],
        reg,
        pairs,
        reg.columns,
        "Region mean |effect| (mean across four cohorts)",
        vmin=0,
        vmax=float(reg.max().max()),
    )
    fig.colorbar(im, ax=ax[1, 1], label="Mean standardized |effect|")
    finish(
        fig,
        2,
        "separability",
        "Different spectra: effect size, statistical evidence and sensor retention",
        "Each heatmap row is one of ten category pairs. All four cohorts remain visible. Ratios measure standardized effect retention, not prediction accuracy or a probability.",
        "All ten whole-spectrum contrasts are supported in the four observed cohorts after declared blocked permutation correction. Effect magnitude and OLI retention vary by pair/domain.",
        "Absolute physical units remain unresolved. Convolution can smooth within-class variability, so a standardized effect ratio above one is possible. Synthetic OLI is not independent Landsat evidence.",
        [
            "tables/whole_spectrum_separability.csv",
            "tables/pair_support_and_evidence.csv",
            "tables/region_separability.csv",
        ],
    )
    wave = read("cohort_wavelength_inference.csv", True)
    w = np.sort(wave.wavelength_nm.unique())
    fig, ax = plt.subplots(2, 4, figsize=(18, 8.5), sharex=True, sharey=False)
    for j, domain in enumerate(domains):
        site, year = domain.split()
        g = wave[wave.site.eq(site) & wave.year.eq(int(year))]
        effects = (
            g.pivot(index="pair", columns="wavelength_nm", values="matched_effect")
            .loc[pairs, w]
            .to_numpy()
        )
        p = (
            g.pivot(index="pair", columns="wavelength_nm", values="adjusted_p")
            .loc[pairs, w]
            .to_numpy()
        )
        im = spectra(ax[0, j], w, effects, "RdBu_r", -2.5, 2.5)
        im2 = spectra(ax[1, j], w, -np.log10(p), "viridis", 0, 2.4)
        ax[0, j].set_title(domain)
        ax[1, j].set_xlabel("Wavelength (nm)")
        ax[0, j].set_yticks(range(10), pairs if j == 0 else [""] * 10, fontsize=9)
        ax[1, j].set_yticks(range(10), pairs if j == 0 else [""] * 10, fontsize=9)
    # Separate colorbar space prevents labels covering spectra.
    fig.subplots_adjust(right=0.90, wspace=0.08, hspace=0.12)
    cax = fig.add_axes([0.92, 0.56, 0.012, 0.30])
    fig.colorbar(im, cax=cax, label="Signed standardized effect (bounded +/-2.5)")
    cax = fig.add_axes([0.92, 0.14, 0.012, 0.30])
    fig.colorbar(im2, cax=cax, label="-log10 joint-adjusted p; .05 = 1.30")
    # Custom layout for dedicated colorbar axes.
    fig.suptitle(
        "Where differences occur, and where they change across domains",
        fontsize=17,
        fontweight="bold",
        y=0.99,
    )
    stem = "F03_wavelength_separability"
    for ext in ["png", "pdf", "svg"]:
        meta = (
            {"CreationDate": None, "ModDate": None}
            if ext == "pdf"
            else {"Date": None}
            if ext == "svg"
            else {"Software": "SpectralBridge"}
        )
        fig.savefig(F / (stem + "." + ext), dpi=240, bbox_inches="tight", metadata=meta)
    plt.close(fig)
    manifest.append(
        dict(
            number=3,
            name=stem,
            title="Wavelength-level differences retain their domain context",
            how="Top: signed matched effect, class A minus B in the displayed pair. Bottom: adjusted evidence; 1.30 corresponds to p=.05. Grey intervals are masked gaps. Color limits bound display only.",
            learn="Many broad regions are supported, but sign/magnitude/rank stability is pair- and domain-dependent. All coordinates share whole-curve permutation shuffles; adjacent channels are not independent tests.",
            uncertain="The lower map is evidence against exchangeability, not an effect confidence interval. Full-cohort maps are descriptive and never used to select predictive features. Null standard errors and every unbounded effect are saved.",
            sources=[
                "prior:tables/cohort_wavelength_inference.csv",
                "tables/wavelength_effect_stability.csv",
                "tables/wavelength_null_uncertainty.csv",
                "prior:tables/domain_rank_consistency.csv",
            ],
            hashes={
                ext: hashlib.sha256((F / (stem + "." + ext)).read_bytes()).hexdigest()
                for ext in ["png", "pdf", "svg"]
            },
        )
    )
    fig, ax = plt.subplots(1, 2, figsize=(16, 6))
    single = read("single_coordinate_five_class.csv")
    for kind, color, label in [
        ("plant", "#216f9d", "New polygon"),
        ("site", "#c65738", "Held site"),
    ]:
        g = (
            single[single.sensor.eq("NEON") & single.kind.eq(kind)]
            .groupby("wavelength_nm")
            .balanced_accuracy.agg(["mean", "min", "max"])
            .reindex(w)
        )
        for ix in np.split(np.arange(len(w)), np.flatnonzero(np.diff(w) > 10) + 1):
            ax[0].plot(
                w[ix],
                g["mean"].to_numpy()[ix],
                color=color,
                label=label if ix[0] == 0 else None,
            )
            ax[0].fill_between(
                w[ix],
                g["min"].to_numpy()[ix],
                g["max"].to_numpy()[ix],
                color=color,
                alpha=0.12,
            )
    ax[0].axhline(0.2, color="grey", ls="--", label="Five-class chance BA")
    ax[0].set(
        xlabel="Wavelength (nm)",
        ylabel="Five-class balanced accuracy",
        ylim=(0, 1),
        title="One coordinate: fixed nearest-training-mean rule",
    )
    ax[0].legend(fontsize=10)
    binary = read("pairwise_single_coordinate_summary.csv")
    z = (
        binary[binary.kind.eq("site") & binary.sensor.eq("NEON")]
        .pivot(index="pair", columns="wavelength_nm", values="min_BA")
        .loc[pairs, w]
    )
    im = spectra(ax[1], w, z.to_numpy(), "RdYlBu", 0, 1)
    ax[1].set_yticks(range(10), pairs)
    ax[1].set_title("Pairwise LDA: weakest held-site BA at each coordinate")
    ax[1].set_xlabel("Wavelength (nm)")
    fig.colorbar(im, ax=ax[1], label="Binary BA; chance = .50")
    finish(
        fig,
        4,
        "single_coordinate_recognition",
        "Statistical differences do not guarantee individual recognition",
        "Left is a five-class problem (chance BA=.20); shaded ranges are observed outer-fold ranges. Right contains ten separate binary problems (chance=.50). No coordinate is chosen using these test scores.",
        "Single-coordinate five-class recognition is limited. Herbaceous versus Woody shrub remains especially weak under the fixed pairwise rule despite supported differences.",
        "This tests specified mean-based rules, not all possible nonlinear classifiers. Observed maxima are descriptive and not validated operational bands.",
        [
            "tables/single_coordinate_five_class.csv",
            "tables/pairwise_single_coordinate_summary.csv",
        ],
    )
    fig, ax = plt.subplots(2, 2, figsize=(15, 8))
    perf = read("recognition_control_summary.csv")
    old = read("complementary_feature_performance.csv", True)
    for j, kind in enumerate(["plant", "site"]):
        for method, color in [("Random", "#8e8e8e"), ("Selected replay", "#1c7996")]:
            g = perf[perf.kind.eq(kind) & perf.method.eq(method)].sort_values("budget")
            ax[0, j].plot(
                g.budget,
                g["mean"],
                "o-",
                color=color,
                label=method.replace(" replay", ""),
            )
            ax[0, j].fill_between(g.budget, g["min"], g["max"], color=color, alpha=0.12)
        for budget, color, label in [
            ("360", "#154b39", "Full NEON"),
            ("OLI", "#b54538", "OLI7"),
        ]:
            ax[0, j].axhline(
                old[
                    old.kind.eq(kind) & old.budget.astype(str).eq(budget)
                ].balanced_accuracy.mean(),
                color=color,
                ls="--",
                label=label,
            )
        ax[0, j].set(
            xscale="log",
            xticks=[1, 3, 7, 20, 50, 100],
            xlabel="NEON wavelength budget",
            ylabel="Balanced accuracy",
            ylim=(0.2, 1),
            title={"plant": "Unseen polygons", "site": "Entire held sites"}[kind],
        )
        ax[0, j].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax[0, j].legend(fontsize=9, ncol=2)
    pca = perf[perf.method.eq("PCA")]
    labels = ["PCA20", "PCA50", "Full360", "OLI7"]
    x = np.arange(4)
    for offset, kind, color in [(-0.17, "plant", "#1c7996"), (0.17, "site", "#b55837")]:
        vals = [
            float(pca[pca.kind.eq(kind) & pca.budget.eq(n)]["mean"].iloc[0])
            for n in [20, 50]
        ] + [
            old[
                old.kind.eq(kind) & old.budget.astype(str).eq(b)
            ].balanced_accuracy.mean()
            for b in ["360", "OLI"]
        ]
        ax[1, 0].bar(x + offset, vals, 0.32, color=color, label=kind)
    ax[1, 0].set_xticks(x, labels)
    ax[1, 0].set(
        ylim=(0, 1),
        ylabel="Balanced accuracy",
        title="PCA components are not a sensor band budget",
    )
    ax[1, 0].legend()
    red = read("subset_redundancy.csv")
    red["method"] = red.variant.str.split("_").str[0]
    for method, color in [("Random", "#8e8e8e"), ("Selected replay", "#1c7996")]:
        g = red[red.method.eq(method)].groupby("budget").fraction_abs_r_above_09.mean()
        ax[1, 1].plot(g.index, g, "o-", label=method, color=color)
    ax[1, 1].set(
        xlabel="Subset coordinate count",
        ylabel="Fraction of pairs with |r| >= .90",
        ylim=(0, 1),
        title="Outer-training redundancy remains substantial",
    )
    ax[1, 1].legend()
    finish(
        fig,
        5,
        "complementarity_controls",
        "Complementary selection adds value, but random bands can catch up",
        "Selected and random subsets use identical inner folds and tuning grids. Five fixed random paths are averaged; shaded envelopes include seed/fold variation, not confidence intervals. PCA uses every input wavelength.",
        "Selected subsets improve modest-budget average recognition. The gap narrows at large budgets; two/three-band held-site controls can favor random subsets. High correlation does not make every additional band useless.",
        "No seed or budget is chosen from outer scores. Five random controls do not establish an optimal selector, universal intrinsic dimension or optimized sensor. PCA fit uses annual rows within training only.",
        [
            "tables/recognition_control_summary.csv",
            "tables/selected_minus_random.csv",
            "tables/recognition_budget_increments.csv",
            "tables/subset_redundancy.csv",
            "prior:tables/complementary_feature_performance.csv",
        ],
    )
    fig, ax = plt.subplots(2, 2, figsize=(15, 8))
    rates = read("class_specific_transfer.csv", True)
    r = (
        rates[rates.budget.astype(str).isin(["360", "OLI"])]
        .groupby(["researcher_category", "kind", "budget"])
        .recall.mean()
        .unstack(["kind", "budget"])
        .loc[CATS]
    )
    r = r.reindex(
        columns=[("plant", "360"), ("site", "360"), ("plant", "OLI"), ("site", "OLI")]
    )
    im = heat(
        ax[0, 0],
        r,
        SHORT,
        ["NEON new", "NEON site", "OLI new", "OLI site"],
        "Per-class recall: means over observed outer folds",
        vmin=0,
        vmax=1,
        annotate=True,
    )
    fig.colorbar(im, ax=ax[0, 0])
    cm = read("confusion_plot_values.csv", True)
    cm = (
        cm[cm.kind.eq("site") & cm.representation.eq("NEON")]
        .pivot(index="truth", columns="predicted", values="mean_fold_row_fraction")
        .loc[CATS, CATS]
    )
    im = heat(
        ax[0, 1],
        cm,
        SHORT,
        SHORT,
        "NEON held-site confusion: true rows / predicted columns",
        vmin=0,
        vmax=1,
        annotate=True,
    )
    temp = read("temporal_recognition_summary.csv")
    pairs_temp = temp[temp.kind.eq("paired_year")]
    positions = np.arange(4)
    for offset, rep, color in [(-0.16, "NEON", "#1c7996"), (0.16, "OLI", "#b55837")]:
        vals = []
        for ty, vy in [(2020, 2020), (2020, 2023), (2023, 2023), (2023, 2020)]:
            vals.append(
                pairs_temp[
                    pairs_temp.representation.eq(rep)
                    & pairs_temp.training_year.eq(ty)
                    & pairs_temp.target_year.eq(vy)
                ].BA.mean()
            )
        ax[1, 0].bar(positions + offset, vals, 0.30, label=rep, color=color)
    ax[1, 0].set_xticks(positions, ["2020→2020", "2020→2023", "2023→2023", "2023→2020"])
    ax[1, 0].set(
        ylim=(0, 1),
        ylabel="Balanced accuracy",
        title="Same held target IDs, different acquisition years",
    )
    ax[1, 0].legend()
    gy = temp[temp.kind.eq("year")]
    for offset, rep, color in [(-0.16, "NEON", "#1c7996"), (0.16, "OLI", "#b55837")]:
        g = (
            gy[gy.representation.eq(rep)]
            .set_index("target")
            .loc[["year_2020", "year_2023"]]
        )
        ax[1, 1].bar(np.arange(2) + offset, g.BA, 0.3, color=color, label=rep)
    ax[1, 1].set_xticks(range(2), ["Hold 2020", "Hold 2023"])
    ax[1, 1].set(
        ylim=(0, 1),
        ylabel="Balanced accuracy",
        title="Global-year holds confound year with site",
    )
    ax[1, 1].legend()
    finish(
        fig,
        6,
        "class_and_domain_failures",
        "Recognition failures are class-specific and domain-dependent",
        "Recall measures recovered true-category observations. Confusion rows sum to one. Paired-year targets keep the same held identities and trained model; global-year targets change site composition.",
        "Woody shrub transfers poorly relative to Evergreen/background. Controlled paired NEON recognition drops in both temporal directions and is asymmetric. OLI can be less temporally sensitive despite lower familiar-domain recognition.",
        "Static retrospective annotations test footprint recognition, not annual biological truth. Three sites and one repeatedly observed site cannot isolate ecological, illumination and processing causes.",
        [
            "prior:tables/class_specific_transfer.csv",
            "prior:tables/confusion_plot_values.csv",
            "tables/temporal_recognition_summary.csv",
            "tables/rates.csv",
            "tables/confusions.csv",
        ],
    )
    summary = read("abundance_domain_summary.csv")
    fig, ax = plt.subplots(2, 2, figsize=(16, 9))
    for j, rep in enumerate(["NEON", "OLI"]):
        for k, (kind, color) in enumerate(
            [("plant", "#21718c"), ("site", "#b95835"), ("year", "#776293")]
        ):
            g = (
                summary[summary.kind.eq(kind) & summary.representation.eq(rep)]
                .set_index("method")
                .loc[METHODS]
            )
            ax[0, j].bar(
                np.arange(8) + (k - 1) * 0.24, g["mean"], 0.23, color=color, label=kind
            )
        ax[0, j].set_xticks(range(8), METHODS, rotation=30, ha="right")
        ax[0, j].set(
            ylabel="Mean-fold macro fraction RMSE",
            ylim=(0, 0.5),
            title=rep + " synthetic mixtures",
        )
        ax[0, j].legend(fontsize=9)
    equal = read("same_candidate_ridge.csv")
    kinds = ["plant", "site", "year"]
    x = np.arange(3)
    vals = [
        equal[equal.kind.eq(k) & equal.representation.eq("NEON")].RMSE.mean()
        for k in kinds
    ]
    mes = [
        equal[equal.kind.eq(k) & equal.representation.eq("NEON")].MESMA_RMSE.mean()
        for k in kinds
    ]
    ridge = [
        summary[
            summary.kind.eq(k)
            & summary.method.eq("Ridge")
            & summary.representation.eq("NEON")
        ]["mean"].iloc[0]
        for k in kinds
    ]
    for off, v, color, label in [
        (-0.25, mes, COLORS["MESMA"], "MESMA15"),
        (0, vals, "#65a6c3", "Ridge15"),
        (0.25, ridge, COLORS["Ridge"], "Ridge120"),
    ]:
        ax[1, 0].bar(x + off, v, 0.24, color=color, label=label)
    ax[1, 0].set_xticks(x, ["New parents", "Held sites", "Global year"])
    ax[1, 0].set(
        ylim=(0, 0.5),
        ylabel="Fraction RMSE",
        title="Same retained NEON candidates: ridge advantage disappears",
    )
    ax[1, 0].legend(fontsize=9)
    raw = read("raw_prediction_constraint_diagnostics.csv", True)
    raw = (
        raw[raw.method.eq("Ridge") & raw.representation.eq("NEON")]
        .groupby("kind")[["raw_fraction_RMSE", "projected_fraction_RMSE"]]
        .mean()
        .loc[kinds]
    )
    ax[1, 1].bar(
        x - 0.17, raw.raw_fraction_RMSE, 0.32, color="#777777", label="Raw ridge"
    )
    ax[1, 1].bar(
        x + 0.17,
        raw.projected_fraction_RMSE,
        0.32,
        color=COLORS["Ridge"],
        label="Projected ridge",
    )
    ax[1, 1].set_xticks(x, ["New parents", "Held sites", "Global year"])
    ax[1, 1].set(
        ylim=(0, 0.5),
        ylabel="Fraction RMSE",
        title="Simplex projection contributes to accuracy",
    )
    ax[1, 1].legend(fontsize=9)
    finish(
        fig,
        7,
        "abundance_controls",
        "Synthetic abundance gains depend on domain, priors and retained library",
        "All main models see identical outer mixtures. Macro RMSE is sqrt(mean class MSE) within target then averaged across folds. The fairness control reduces ridge to the exact 15 MESMA candidates; the original ridge uses 120 parents.",
        "Ridge120 improves the primary new-parent/held-site benchmark, but fails the global-year prior on average. Ridge15 loses the NEON advantage. Projection improves error. The known-generating-parent oracle has near-zero fraction error.",
        "The candidate control changes training diversity/bundle count and model prior; it does not prove a single cause. Methods are not intrinsically ranked, and these algebraic fractions are not field cover.",
        [
            "tables/abundance_domain_summary.csv",
            "tables/same_candidate_ridge.csv",
            "tables/abundance_paired_vs_baselines.csv",
            "prior:tables/raw_prediction_constraint_diagnostics.csv",
            "prior:tables/oracle_solver_controls.csv",
        ],
    )
    fraction = read("fraction_grid_calibration.csv")
    f = fraction[fraction.kind.eq("site") & fraction.representation.eq("NEON")]
    plot = (
        f.groupby(["method", "researcher_category", "true_fraction"])[
            ["prediction_mean", "bias", "RMSE", "detection_probability"]
        ]
        .mean()
        .reset_index()
    )
    plot.to_csv(T / "calibration_plot_values.csv", index=False)
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    axs = axes.ravel()
    for i, c in enumerate(CATS):
        for method in METHODS:
            g = plot[
                plot.researcher_category.eq(c) & plot.method.eq(method)
            ].sort_values("true_fraction")
            axs[i].plot(
                g.true_fraction,
                g.prediction_mean,
                "o-",
                ms=3,
                lw=1.4,
                color=COLORS[method],
                label=method,
            )
        axs[i].plot([0, 1], [0, 1], "k--", lw=1)
        axs[i].set(
            xlim=(0, 1),
            ylim=(0, 1),
            title=c,
            xlabel="Known algebraic fraction",
            ylabel="Mean predicted fraction",
        )
        axs[i].grid(alpha=0.15)
    axs[5].axis("off")
    handles, labels = axs[0].get_legend_handles_labels()
    axs[5].legend(handles, labels, loc="upper left", bbox_to_anchor=(.04, 1.02), fontsize=11)
    axs[5].text(
        0.04,
        0.05,
        "NEON; held-site targets\nMean across three held sites\nDiagonal = unbiased mean prediction",
        transform=axs[5].transAxes,
        fontsize=11,
    )
    finish(
        fig,
        8,
        "fraction_calibration",
        "Zero, low and pure-end mixtures reveal shrinkage hidden by RMSE",
        "Each point averages predictions at a nominal truth-grid fraction, first count-weighting machine-precision-equivalent bins within fold, then averaging held sites. The diagonal represents unbiased mean recovery. Endpoints are synthetic pure-parent mixtures, not verified pure materials.",
        "Many methods overpredict absent categories and shrink high fractions. Similar overall RMSE can hide different class-specific biases and detection behavior.",
        "Mean calibration curves hide bundle variation; paired intervals and per-fold/per-class errors remain saved. No universal field detection threshold follows from this grid.",
        [
            "tables/calibration_plot_values.csv",
            "tables/fraction_grid_calibration.csv",
        ],
    )
    fig, ax = plt.subplots(2, 2, figsize=(16, 8.5))
    m = read("abundance_model_comparison.csv", True)
    m = (
        m[m.kind.eq("site") & m.representation.eq("NEON")]
        .groupby(["researcher_category", "method"])[["RMSE", "FPR", "low_FNR"]]
        .mean()
    )
    for axes, metric, title in [
        (ax[0, 0], "RMSE", "Held-site fraction RMSE"),
        (ax[0, 1], "FPR", "False detection at true zero"),
        (ax[1, 0], "low_FNR", "Missed low fractions"),
    ]:
        z = m[metric].unstack("method").loc[CATS, METHODS]
        im = heat(
            axes, z, SHORT, METHODS, title, vmin=0, vmax=1 if metric != "RMSE" else 0.6
        )
        fig.colorbar(im, ax=axes)
    fraction = read("fraction_grid_calibration.csv")
    g = fraction[fraction.kind.eq("site") & fraction.representation.eq("NEON")]
    for i, c in enumerate(CATS):
        for method, style in [("Ridge", "-"), ("Two-stage", "--")]:
            a = (
                g[g.researcher_category.eq(c) & g.method.eq(method)]
                .groupby("true_fraction")
                .detection_probability.mean()
            )
            ax[1, 1].plot(
                a.index,
                a,
                style,
                color=plt.cm.tab10(i),
                lw=1.8,
                label=c if method == "Ridge" else None,
            )
    ax[1, 1].set(
        xlabel="Known algebraic fraction",
        ylabel="Empirical detection frequency",
        title="Final fraction >= .10: ridge solid / two-stage dashed",
        ylim=(0, 1),
    )
    ax[1, 1].legend(fontsize=8, ncol=2)
    finish(
        fig,
        9,
        "detection_and_class_links",
        "Recognition, false detection and quantification are different outcomes",
        "Rows are researcher categories and columns are methods. False detection and low-fraction misses use the declared .10 final-fraction cutoff. The final panel shows empirical detection frequency versus truth, ridge solid and two-stage dashed. Class-level links are saved separately for all five categories.",
        "Harder-to-recognize categories also tend to have larger ridge fraction error here. False detection and missed low fractions trade off; a stronger prior can improve one while worsening the other.",
        "Class-level associations are descriptive, not five independent geographic replicates. Stage-A presence metrics are separately saved; .10 is a comparison rule, not an independently validated detection limit.",
        [
            "prior:tables/abundance_model_comparison.csv",
            "prior:tables/two_stage_presence_metrics.csv",
            "tables/fraction_grid_calibration.csv",
            "tables/class_recognition_abundance_links.csv",
            "tables/class_link_correlations.csv",
        ],
    )
    scatter = pd.read_parquet(T / "reconstruction_fraction_points.parquet")
    fig, ax = plt.subplots(2, 2, figsize=(16, 8))
    amb = read("abundance_by_ambiguity.csv", True)
    amb = amb[amb.kind.eq("site") & amb.representation.eq("NEON")]
    for k, method in enumerate(
        [
            "Training prior",
            "MESMA",
            "Ridge",
            "Random forest",
            "Gradient boosting",
            "Two-stage",
        ]
    ):
        g = (
            amb[amb.method.eq(method)]
            .groupby("ambiguity")
            .fraction_RMSE.mean()
            .reindex(["Low", "Moderate", "High"])
        )
        ax[0, 0].plot(range(3), g, "o-", color=COLORS[method], label=method)
    ax[0, 0].set_xticks(range(3), ["Low", "Moderate", "High"])
    ax[0, 0].set(
        ylabel="Mean-fold fraction RMSE",
        title="Same target ambiguity strata for every method",
    )
    ax[0, 0].legend(fontsize=9, ncol=2)
    ax[0, 1].scatter(
        scatter.native_spectral_RMSE,
        scatter.MESMA_fraction_RMSE,
        c=scatter.max_near_fraction_range,
        cmap="viridis",
        s=3,
        alpha=0.2,
        rasterized=True,
    )
    ax[0, 1].set(
        xlabel="MESMA native spectral RMSE (training-RMS-scaled)",
        ylabel="MESMA fraction RMSE",
        title="Low spectral residual does not ensure correct fractions",
    )
    allm = read("abundance_model_comparison.csv", True)
    rr = (
        allm[allm.method.eq("Ridge")]
        .groupby(["fold", "kind", "target", "representation"])
        .RMSE.apply(lambda x: np.sqrt(np.mean(x * x)))
        .reset_index(name="RMSE")
    )
    reps = [
        "NEON",
        "OLI",
        "shape",
        "PCA20",
        "selected7",
        "selected20",
        "derivative1",
        "derivative2",
    ]
    available = [v for v in reps if v in set(rr.representation)]
    for offset, kind, color in [(-0.17, "plant", "#1c7996"), (0.17, "site", "#b55837")]:
        g = (
            rr[rr.kind.eq(kind)]
            .groupby("representation")
            .RMSE.mean()
            .reindex(available)
        )
        ax[1, 0].bar(
            np.arange(len(available)) + offset, g, 0.32, label=kind, color=color
        )
    ax[1, 0].set_xticks(range(len(available)), available, rotation=30, ha="right")
    ax[1, 0].set(
        ylabel="Ridge fraction RMSE",
        title="Existing representation sensitivities; no new sweep",
    )
    ax[1, 0].legend(fontsize=9)
    links = read("class_recognition_abundance_links.csv")
    g = links[links.kind.eq("site")]
    for i, r in enumerate(g.itertuples()):
        ax[1, 1].scatter(
            r.recall,
            r.high_ambiguity_fraction_when_present,
            s=60,
            color=plt.cm.tab10(i),
        )
        ax[1, 1].annotate(
            r.researcher_category,
            (r.recall, r.high_ambiguity_fraction_when_present),
            xytext=(4, 5),
            textcoords="offset points",
            fontsize=10,
        )
    ax[1, 1].set(
        xlabel="Held-site recognition recall",
        ylabel="High-ambiguity fraction when category present",
        title="Mixture ambiguity burden, not class-specific range",
        xlim=(0.35, 1.08),
    )
    finish(
        fig,
        10,
        "ambiguity_and_limits",
        "Better expected fractions do not establish unique physical inversion",
        "Ambiguity is maximum candidate-class fraction range among near-fitting solutions at the declared .01 tolerance. High means range >=.30. Every scatter point is one saved synthetic mixture, not an independent plant.",
        "Ridge can reduce error in high-ambiguity targets while alternatives remain feasible. The moderate stratum can favor MESMA. Spectral reconstruction is insufficient, and derivatives do not remedy the main limitations.",
        "Candidate/tolerance ambiguity is not exhaustive physical uncertainty. The class burden is mixture-level ambiguity conditional on category presence. Observational data cannot uniquely apportion library variability, overlap, acquisition shift and prior effects.",
        [
            "prior:tables/abundance_by_ambiguity.csv",
            "tables/reconstruction_fraction_points.parquet",
            "prior:tables/abundance_model_comparison.csv",
            "tables/class_recognition_abundance_links.csv",
        ],
    )
    (BASE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (BASE / "FIGURE_CAPTIONS.md").write_text(
        "\n\n".join(
            f"## {r['name']}: {r['title']}\n\nHOW TO READ IT: {r['how']}\n\nWHAT WE LEARN: {r['learn']}\n\nWHAT REMAINS UNCERTAIN: {r['uncertain']}\n\nSources: "
            + "; ".join(r["sources"])
            for r in manifest
        )
        + "\n"
    )
    print("Built", len(manifest), "publication figure families.")


if __name__ == "__main__":
    main()
