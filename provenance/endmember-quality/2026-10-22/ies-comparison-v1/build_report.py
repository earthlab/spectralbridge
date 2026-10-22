"""Create a readable illustrated old/new endmember readiness comparison."""

from pathlib import Path
import base64
import hashlib
import json
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import markdown
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
TABLES = OUT / "tables"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
OLD = "#567389"
NEW = "#00887B"
INK = "#183440"
ORANGE = "#C46632"
DISPLAY = {
    "Herbaceous_woody_shrub": "Herbaceous +\nwoody shrub",
    "Bare_Rock": "Bare / rock",
    "Non-vegetated & dead": "Background\n& dead",
    "Woody shrub": "Woody shrub",
}
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "svg.fonttype": "none",
        "svg.hashsalt": "ies-comparison-20261022",
        "figure.facecolor": "white",
    }
)
FIGURES = []


def table(name):
    return pd.read_csv(TABLES / (name + ".csv"))


def save(fig, name, caption, sources):
    for ext in ["png", "svg"]:
        fig.savefig(
            FIG / (name + "." + ext),
            bbox_inches="tight",
            dpi=210,
            metadata={"Date": None}
            if ext == "svg"
            else {"Software": "SpectralBridge comparison"},
        )
    plt.close(fig)
    FIGURES.append(
        dict(
            id=name,
            caption=caption,
            sources=["tables/" + s + ".csv" for s in sources],
            sha256={
                ext: hashlib.sha256((FIG / (name + "." + ext)).read_bytes()).hexdigest()
                for ext in ["png", "svg"]
            },
        )
    )


def md_table(data):
    """Render a small evidence table without an extra tabulate dependency."""

    def cell(value):
        if isinstance(value, (float, np.floating)):
            return "-" if np.isnan(value) else f"{value:.4f}"
        return str(value).replace("|", " / ")

    rows = [list(data.columns), ["---"] * len(data.columns)]
    rows += [[cell(v) for v in row] for row in data.itertuples(index=False, name=None)]
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def main():
    audit = json.loads((OUT / "input_audit.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    if summary["status"] != "complete":
        raise RuntimeError(
            "All four exhaustive fits must finish before publishing the comparison."
        )
    score = table("fraction_summary")
    indexed = score.set_index(["library", "scheme", "method"])
    cov = table("coverage_summary")
    paired = table("paired_comparisons")
    capacity = table("capacity_control_summary")
    amb = table("convex_ambiguity")

    def metric(lib, scheme, method):
        return float(indexed.loc[(lib, scheme, method), "common_fraction_RMSE"])

    # 1: Raw six-way support, before merging/splitting labels.
    atoms = ["Deciduous", "Evergreen", "Herbaceous", "Woody shrub", "Bare_Rock", "Dead"]
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    y = np.arange(6)
    for k, (name, color) in enumerate([("old", OLD), ("new", NEW)]):
        values = [audit["libraries"][name]["atom_counts"][a] for a in atoms]
        ax.barh(
            y + (k - 0.5) * 0.3,
            values,
            height=0.27,
            color=color,
            label="Previous" if k == 0 else "New IES",
        )
        for j, v in enumerate(values):
            ax.text(v + 2, y[j] + (k - 0.5) * 0.3, str(v), va="center", fontsize=11)
    ax.set_yticks(y, [DISPLAY.get(a, a) for a in atoms])
    ax.invert_yaxis()
    ax.set_xlim(0, 205)
    ax.set_xlabel("Selected spectra eligible for both label schemes")
    ax.legend(frameon=False)
    ax.set_title(
        "The new selection changes reference balance, as well as category names"
    )
    save(
        fig,
        "01_reference_support",
        "Figure 1. Counts in six source groups before relabelling. The primary previous library has 592 eligible references (11 of the original 603 have mixed/unspecified backgrounds); the new library has 501. Revised labels merge herbaceous/shrub and split bare/rock from dead. Counts are references, not independent plants.",
        ["old_selected_identity", "new_selected_identity"],
    )
    # 2: Same target populations, distinct scientific quality criteria.
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for row, scheme in enumerate(["original", "revised"]):
        cats = cov[cov.scheme.eq(scheme) & cov.library.eq("old")].category.tolist()
        for col, (field, mult, label) in enumerate(
            [
                (
                    "same_category_RMSE",
                    1,
                    "Same-category spectral RMSE\n(supplied-array units; smaller is closer)",
                ),
                ("recall", 100, "Mean category recall (%)"),
            ]
        ):
            ax = axes[row, col]
            for k, (name, color) in enumerate([("old", OLD), ("new", NEW)]):
                values = (
                    cov[cov.scheme.eq(scheme) & cov.library.eq(name)]
                    .set_index("category")
                    .loc[cats, field]
                    .to_numpy()
                    * mult
                )
                ax.scatter(
                    values,
                    np.arange(5) + (k - 0.5) * 0.14,
                    color=color,
                    label="Previous" if k == 0 else "New IES",
                    s=65,
                )
            ax.set_yticks(range(5), [DISPLAY.get(c, c) for c in cats])
            ax.set_ylim(4.5, -0.5)
            ax.set_xlabel(label)
            ax.set_title(("Original categories" if row == 0 else "Revised categories"))
            ax.grid(axis="x", color="#E6ECEF")
            ax.set_axisbelow(True)
            if col == 1:
                ax.set_xlim(0, 100)
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(),
        loc="outside lower center",
        ncol=2,
        frameon=False,
    )
    save(
        fig,
        "02_coverage_and_recognition",
        "Figure 2. Both libraries predict the same 3,904 observed polygon/year targets from 3,021 IDs, excluding all 540 selected parent IDs. Annual scores are weighted so each ID contributes equally within its category. New references cover typical spectra more closely, but nearest-reference category recognition does not improve uniformly. This is an internal nearest-reference diagnostic, not the earlier trained NEON classifier.",
        ["coverage_summary", "observed_target_identity"],
    )
    # 3: One common output space for a fair comparison across taxonomies.
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True, layout="constrained")
    for ax, scheme in zip(axes, ["original", "revised"]):
        for j, (lib, color) in enumerate([("old", OLD), ("new", NEW)]):
            vals = [metric(lib, scheme, m) for m in ["ridge", "mesma"]]
            ax.bar(
                np.arange(2) + (j - 0.5) * 0.3,
                vals,
                width=0.27,
                color=color,
                label="Previous" if j == 0 else "New IES",
            )
            for k, v in enumerate(vals):
                ax.text(
                    k + (j - 0.5) * 0.3,
                    v + 0.009,
                    f"{v:.3f}",
                    ha="center",
                    weight="bold",
                    fontsize=12,
                )
        prior = metric("old", scheme, "prior")
        ax.axhline(prior, ls="--", color=INK, lw=1, label="Training-design prior")
        ax.set_xticks([0, 1], ["Ridge", "Exhaustive MESMA"])
        ax.set_title("Fit " + scheme + " categories")
        ax.set_ylim(0, max(0.42, score.common_fraction_RMSE.max() + 0.05))
    axes[0].set_ylabel("Fraction RMSE on the SAME four components\n(smaller is better)")
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        loc="outside lower center",
        ncol=3,
        frameon=False,
    )
    save(
        fig,
        "03_fraction_recovery",
        "Figure 3. The exact same 568 synthetic observations are scored after both output schemes are reduced to four common components: deciduous, evergreen, herbaceous+shrub and background. This avoids comparing errors in incompatible category spaces. MESMA searches all one-to-three-category models; ridge is tuned using polygon-disjoint training groups. The dashed prior uses training-design fractions, with no spectral information. These are known algebraic weights, not field cover.",
        ["fraction_summary", "target_membership"],
    )
    # 4: The paired experiment separates a changed selection from changed labels.
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), layout="constrained")
    for ax, kind, title in zip(
        axes,
        ["selection", "category_scheme"],
        [
            "Replace the previous references with IES",
            "Replace the original labels with revised labels",
        ],
    ):
        rows = paired[paired.comparison.eq(kind)].copy()
        labels = []
        for i, r in enumerate(rows.itertuples()):
            a = r.baseline.split("/")
            label = (
                (a[1].capitalize() + " / " + a[2].upper())
                if kind == "selection"
                else (a[0].capitalize() + " references / " + a[2].upper())
            )
            labels.append(label)
            ax.hlines(i, r.conditional_2_5, r.conditional_97_5, color=OLD, lw=2)
            ax.scatter(
                r.common_RMSE_delta,
                i,
                color=NEW if r.common_RMSE_delta < 0 else ORANGE,
                s=65,
                zorder=3,
            )
        ax.set_yticks(range(len(rows)), labels)
        ax.set_ylim(len(rows) - 0.5, -0.5)
        ax.axvline(0, color=INK, lw=1)
        ax.set_xlabel(
            "Change in common-component fraction RMSE\nNegative favors the replacement"
        )
        ax.set_title(title, fontsize=12)
    save(
        fig,
        "04_paired_effects",
        "Figure 4. Each interval resamples the same eight whole parent bundles (1,999 paired bootstrap draws). Left isolates the supplied reference selection within one label scheme. Right compares the label scheme within one fixed selection. These conditional intervals describe sensitivity to eight sampled parent bundles, not independent geographic validation or population confidence guarantees.",
        ["paired_comparisons"],
    )
    # 5: Category-specific errors, which a mean can conceal.
    bycat = table("fraction_by_category")
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), layout="constrained")
    columns = [
        ("old", "ridge"),
        ("new", "ridge"),
        ("old", "mesma"),
        ("new", "mesma"),
        ("old", "prior"),
    ]
    vmax = float(bycat[~bycat.method.eq("prior")].RMSE.max())
    for ax, scheme in zip(axes, ["original", "revised"]):
        cats = cov[cov.scheme.eq(scheme) & cov.library.eq("old")].category.tolist()
        values = np.array(
            [
                [
                    float(
                        bycat[
                            (bycat.library.eq(lib))
                            & (bycat.scheme.eq(scheme))
                            & (bycat.method.eq(method))
                            & (bycat.category.eq(c))
                        ].RMSE.iloc[0]
                    )
                    for lib, method in columns
                ]
                for c in cats
            ]
        )
        im = ax.imshow(values, vmin=0, vmax=vmax, cmap="YlOrBr", aspect="auto")
        ax.set_yticks(range(5), [DISPLAY.get(c, c) for c in cats])
        ax.set_xticks(
            range(5),
            [
                "Previous\nridge",
                "New IES\nridge",
                "Previous\nMESMA",
                "New IES\nMESMA",
                "Training\nprior",
            ],
            fontsize=10,
        )
        ax.set_title(scheme.capitalize() + " categories")
        for i in range(5):
            for j in range(5):
                ax.text(
                    j,
                    i,
                    f"{values[i, j]:.3f}",
                    ha="center",
                    va="center",
                    color="white" if values[i, j] > 0.7 * vmax else INK,
                    fontsize=11,
                )
    fig.colorbar(
        im,
        ax=axes,
        shrink=0.8,
        label="Per-category synthetic fraction RMSE (smaller is better)",
    )
    save(
        fig,
        "05_category_errors",
        "Figure 5. Per-category fraction errors expose the costs of the chosen categories. Compare old versus new references within a panel and method. Errors across the two panels represent different biological targets and are not directly interchangeable. The revised scheme cannot estimate herbaceous and shrub separately; the original scheme cannot estimate bare/rock and dead separately. The last column is the no-spectrum training-design prior.",
        ["fraction_by_category"],
    )
    # 6: Domain heterogeneity without a false held-site transfer claim.
    domain = table("fraction_by_domain")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True, layout="constrained")
    cells = [("NIWO", 2020), ("NIWO", 2023), ("WREF", 2023), ("YELL", 2023)]
    for ax, scheme in zip(axes, ["original", "revised"]):
        for lib, color in [("old", OLD), ("new", NEW)]:
            for method, style in [("ridge", "o-"), ("mesma", "s--")]:
                d = domain[
                    (domain.library.eq(lib))
                    & (domain.scheme.eq(scheme))
                    & (domain.method.eq(method))
                ].set_index(["site", "year"])
                ax.plot(
                    range(4),
                    [d.loc[cell, "common_RMSE"] for cell in cells],
                    style,
                    color=color,
                    label=("Previous" if lib == "old" else "New IES") + " " + method,
                )
        ax.axhline(
            metric("old", scheme, "prior"),
            color=INK,
            ls=":",
            lw=1,
            label="No-spectrum prior",
        )
        ax.set_xticks(range(4), [s + "\n" + str(y) for s, y in cells])
        ax.set_title(scheme.capitalize() + " labels")
        ax.grid(axis="y", color="#E6ECEF")
    axes[0].set_ylabel("Common-component synthetic fraction RMSE")
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        loc="outside lower center",
        ncol=2,
        frameon=False,
    )
    save(
        fig,
        "06_domain_patterns",
        "Figure 6. These are site/year breakdowns of common targets under global fixed libraries, not held-site experiments. The dotted line is the no-spectrum training-design prior. Each cell has two independent parent bundles; repeated mixture rows are not additional independent plants. Domain differences qualify any pooled improvement.",
        ["fraction_by_domain"],
    )
    # 7: Capacity check for ridge; draw ranges are not sampling intervals.
    controls = table("capacity_control_scores")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True, layout="constrained")
    for ax, scheme in zip(axes, ["original", "revised"]):
        d = controls[controls.scheme.eq(scheme)].pivot(
            index="replicate", columns="library", values="common_RMSE"
        )
        for _, r in d.iterrows():
            ax.plot([0, 1], [r.old, r.new], color="#C1CCD0", lw=1)
        ax.scatter(np.zeros(len(d)), d.old, color=OLD, s=55, zorder=3)
        ax.scatter(np.ones(len(d)), d.new, color=NEW, s=55, zorder=3)
        ax.plot(
            [0, 1],
            [d.old.mean(), d.new.mean()],
            color=INK,
            marker="D",
            ms=7,
            lw=2,
            label="Mean of five draws",
        )
        ax.set_xticks([0, 1], ["Previous\nmatched counts", "New IES\nmatched counts"])
        ax.set_title(scheme.capitalize() + " labels")
        ax.legend(frameon=False, fontsize=10)
    axes[0].set_ylabel("Common-component ridge fraction RMSE")
    save(
        fig,
        "07_capacity_control",
        "Figure 7. Five draw pairs match the exact reference count in each of six atomic source groups (476 references per draw). The gain in ridge becomes smaller. Parent and site distributions are not matched, and five draw outcomes are not a population uncertainty interval. Full-library results therefore describe these supplied libraries, not proof that IES is intrinsically superior.",
        ["capacity_control_scores", "capacity_controls"],
    )
    # 8: Internal ambiguity, with a deliberately limited interpretation.
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), layout="constrained")
    for ax, scheme in zip(axes, ["original", "revised"]):
        a = amb[amb.scheme.eq(scheme)].groupby(["library", "category"]).feasible.mean()
        cats = cov[cov.scheme.eq(scheme) & cov.library.eq("old")].category.tolist()
        for j, (lib, color) in enumerate([("old", OLD), ("new", NEW)]):
            ax.barh(
                np.arange(5) + (j - 0.5) * 0.3,
                [100 * a.loc[lib, c] for c in cats],
                height=0.27,
                color=color,
                label="Previous" if lib == "old" else "New IES",
            )
        ax.set_yticks(range(5), [DISPLAY.get(c, c) for c in cats])
        ax.set_ylim(4.5, -0.5)
        ax.set_xlim(0, 75)
        ax.set_xlabel("Selected references reproduced by\nother-category mixtures (%)")
        ax.set_title(scheme.capitalize() + " labels")
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        loc="outside lower center",
        ncol=2,
        frameon=False,
    )
    save(
        fig,
        "08_internal_ambiguity",
        "Figure 8 (supporting diagnostic). Verified nonnegative sum-one cross-category reconstructions at RMSE <=1e-8. Candidate counts and target reference points differ between libraries, so lower certificate frequency alone does not prove a better selector. The certificate family allows multiple references/category and is broader than three-category MESMA. Missing certificates do not prove uniqueness.",
        ["convex_ambiguity"],
    )

    # Every displayed summary number is read from recorded tables or audit JSON.
    native = score[
        [
            "library",
            "scheme",
            "method",
            "native_fraction_RMSE",
            "common_fraction_RMSE",
            "mean_spectral_RMSE",
        ]
    ].copy()
    native.columns = [
        "References",
        "Fit labels",
        "Method",
        "Native five-class fraction RMSE",
        "Common four-component fraction RMSE",
        "Mean spectral RMSE",
    ]
    means = cov.groupby(["library", "scheme"])[["recall", "same_category_RMSE"]].mean()
    citable = {}
    for (lib, scheme), r in means.iterrows():
        citable[f"{lib}/{scheme}/coverage"] = {k: float(v) for k, v in r.items()}
    pr = json.loads((OUT / "oracle.json").read_text())["atomic_fraction_RMSE"]
    # The report does not auto-promote interval signs into universal conclusions.
    text = f"""# Are the new IES endmembers and categories better?

**Internal matched-library readiness comparison | 22 October 2026**

The new selection and the new category scheme are two separate changes. This experiment tests each one, with both methods seeing exactly the same target spectra and known synthetic weights. Read the point estimates together with the category-specific errors, paired intervals and geographic limits below.

## Short answer

**The new references improve synthetic fraction recovery in this matched experiment, but they are not better on every diagnostic.** With original labels held fixed, common-component RMSE changes from **{metric("old", "original", "ridge"):.3f} to {metric("new", "original", "ridge"):.3f} for ridge** and **{metric("old", "original", "mesma"):.3f} to {metric("new", "original", "mesma"):.3f} for exhaustive MESMA**. Smaller is better; these are fraction errors, not percent accuracies.

**The revised categories help MESMA more than ridge.** With the new reference spectra held fixed, changing labels moves MESMA's common-component RMSE from **{metric("new", "original", "mesma"):.3f} to {metric("new", "revised", "mesma"):.3f}**, while ridge changes from **{metric("new", "original", "ridge"):.3f} to {metric("new", "revised", "ridge"):.3f}**. The revised scheme trades separate herbaceous/shrub estimates for separate dead/bare estimates. It is a different scientific target, not a universally better PFT classification.

**Use the new selection as a stronger candidate for the next validation stage, not as a validated field abundance product.** Ridge has lower point error than MESMA in these configurations, but their training information, priors and output constraints differ. The equal-count control shrinks the ridge selection gain. Dead-material recovery remains a specific weakness for MESMA, despite improved pooled performance.

## What changed, and what was held fixed?

The new files contain **501 spectra from 324 polygon IDs**. Their labels are Deciduous (122), Evergreen (180), Herbaceous_woody_shrub (97), Bare_Rock (75) and Dead (27). The merged herbaceous/shrub class consists of 37 originally herbaceous references and 60 originally shrub references.

The previous library has 603 spectra from 367 IDs. Eleven references have mixed/unspecified backgrounds that cannot be labelled bare/rock or dead. To isolate relabelling on the same usable references, the primary previous library is therefore **592 spectra from 359 IDs**. The archived 603-member results remain untouched.

![Selected reference counts](figures/01_reference_support.png)

{FIGURES[0]["caption"]}

The CSV and new NumPy spectra agree exactly. A one-to-one flight/GlobalID/pixel/row/column join verifies that the new CSV row numbers are **one-based**; the old selection is **zero-based**. No shifted-row assumption is used. The NumPy class list agrees exactly with the new CSV's `new_class` labels. The supplied numerical values retain the earlier array scale, not independently validated physical reflectance units.

The common observed target set contains **{audit["target_curves"]:,} polygon/year curves from {audit["target_IDs"]:,} IDs**. It excludes all **540 IDs** selected by either library, and mixed/unspecified backgrounds. The latter account for **930 archive rows from 86 IDs**; they are not guessed into a new category. This is still an **internal** evaluation: excluding selected parents does not retroactively make archive-wide selection blind.

## 1. Typical spectral coverage improves; category recognition is mixed

Under the original five labels, macro same-category distance changes from **{means.loc[("old", "original"), "same_category_RMSE"]:.5f} to {means.loc[("new", "original"), "same_category_RMSE"]:.5f}**, while mean category recall changes from **{100 * means.loc[("old", "original"), "recall"]:.1f}% to {100 * means.loc[("new", "original"), "recall"]:.1f}%**. Under the revised labels, recall is **{100 * means.loc[("old", "revised"), "recall"]:.1f}% versus {100 * means.loc[("new", "revised"), "recall"]:.1f}%**. Recall means the proportion of a labelled category recovered correctly, averaged equally across categories; it is not precision.

![Coverage versus recognition](figures/02_coverage_and_recognition.png)

{FIGURES[1]["caption"]}

The revised new library recognizes **Evergreen well**, but **Dead** and the merged **Herbaceous + woody shrub** category remain difficult. Merging herbaceous and shrub prevents confusion *between those two labels* by definition; it also removes the ability to recover their separate abundances. Splitting background adds a new question that must be supported by actual dead/bare examples, rather than by a better-looking pooled score.

Supplementary paired-ID coverage intervals are in `tables/paired_coverage_comparisons.csv`. They resample IDs within true categories after averaging annual scores. They are exploratory, conditional on sampled IDs, and assume identity-level independence; they do not account fully for geographic clustering.

## 2. Synthetic fraction recovery: direct method and category comparisons

**Primary score:** fraction RMSE on the same four components: deciduous, evergreen, herbaceous+shrub, and background. Both five-label predictions are explicitly coarsened to those components. This makes cross-taxonomy comparisons meaningful; comparing two different five-category RMSEs alone would not.

![Synthetic fraction recovery](figures/03_fraction_recovery.png)

{FIGURES[2]["caption"]}

{md_table(native)}

MESMA uses the unchanged active-face kernel to search **every permitted one-to-three-category model**, with one reference per active category. The four model counts are recorded in `models/*_mesma_metadata.json`; no target-specific shortlist is substituted. Ridge uses identical 71-recipe designs within each selection and parent-disjoint three-group tuning over five fixed penalties. The same training spectra are used for both output label schemes within each library. All target parents are absent from every training library.

Synthetic targets include six atomic source groups, allowing the same observation to contain two parents that one scheme merges into a single category. This is intentional: the geometry and output restrictions change when categories merge. The 568 mixture rows share **48 generating parents in eight disjoint six-parent bundles**; they are not 568 independent plants. Each bundle includes six pure spectra, 45 pair mixtures (10/50/90%) and 20 equal-third triple mixtures. The recipe is controlled and cannot establish performance on arbitrary physical mixtures.

## 3. Does the improvement come from references or category names?

![Paired changes](figures/04_paired_effects.png)

{FIGURES[3]["caption"]}

{md_table(paired[["comparison", "baseline", "alternative", "common_RMSE_delta", "conditional_2_5", "conditional_97_5"]])}

The ridge relabelling check is especially informative: all four primary fits choose penalty 10, and raw predictions of the four shared components agree across schemes to numerical precision. Their small displayed score differences arise when fractions are projected onto the five-category simplex (nonnegative weights summing to one) *before* coarsening. This is a constraint-geometry effect, not added spectral information. `tables/ridge_relabelling_geometry.csv` also records projection directly in the common four-component space, where both label schemes give the same prediction.

For MESMA, the revised labels change admissible combinations: a model may now contain both bare/rock and dead references, but cannot contain separate herbaceous and shrub categories. The score change therefore reflects a changed model family as well as a changed ecological question.

Negative changes favor the replacement. A range entirely below zero supports a consistent gain across these sampled parent bundles; it is not proof of field abundance accuracy. New-reference versus old-reference comparisons hold the label space fixed. Revised versus original label comparisons hold reference membership fixed, so an apparent benefit cannot be attributed simply to changing both at once.

## 4. Which categories and acquisition settings remain difficult?

![Per-category fraction errors](figures/05_category_errors.png)

{FIGURES[4]["caption"]}

![Domain breakdowns](figures/06_domain_patterns.png)

{FIGURES[5]["caption"]}

For the new revised library, dead-material fraction RMSE is **{float(bycat[(bycat.library.eq("new")) & (bycat.scheme.eq("revised")) & (bycat.method.eq("ridge")) & (bycat.category.eq("Dead"))].RMSE.iloc[0]):.3f} for ridge** and **{float(bycat[(bycat.library.eq("new")) & (bycat.scheme.eq("revised")) & (bycat.method.eq("mesma")) & (bycat.category.eq("Dead"))].RMSE.iloc[0]):.3f} for MESMA**, compared with **{float(bycat[(bycat.library.eq("new")) & (bycat.scheme.eq("revised")) & (bycat.method.eq("prior")) & (bycat.category.eq("Dead"))].RMSE.iloc[0]):.3f} for the no-spectrum prior**. This is why the new split should not be treated as already validated. Its 27 selected dead references represent only 21 polygon IDs.

The three sites and four site/year cells do not separate geography from year. These plots evaluate targets from each cell using reference libraries that include those sites. They are **not leave-one-site-out validation**. Category annotations are retrospective 2023/2024 labels reused across imagery years, and labelled polygons are not certified pure materials.

## 5. Does the ridge comparison survive matching library size?

![Capacity controls](figures/07_capacity_control.png)

{FIGURES[6]["caption"]}

{md_table(capacity[["scheme", "old_mean", "new_mean", "mean_new_minus_old", "new_better_draws", "draws"]])}

These controls reduce the attribution problem but do not eliminate it: the selected parent identities, sites and within-parent pixel distributions still differ. The result concerns these supplied libraries, not a general proof that the IES algorithm is a better selector.

## Supporting diagnostic: are selected spectra compositionally unique?

![Internal cross-category ambiguity](figures/08_internal_ambiguity.png)

{FIGURES[7]["caption"]}

The original-label certificate rates are **{100 * amb[(amb.library.eq("old")) & (amb.scheme.eq("original"))].feasible.mean():.1f}%** in the previous eligible library and **{100 * amb[(amb.library.eq("new")) & (amb.scheme.eq("original"))].feasible.mean():.1f}%** in the new library. The revised-label rates are **{100 * amb[(amb.library.eq("old")) & (amb.scheme.eq("revised"))].feasible.mean():.1f}%** and **{100 * amb[(amb.library.eq("new")) & (amb.scheme.eq("revised"))].feasible.mean():.1f}%**. These are different sets of target spectra and different candidate hulls; their sizes and sampled positions contribute to this diagnostic.

The known-parent positive control recovers the six atomic weights at RMSE **{pr:.2e}**. The solver can recover the constructed weights when the actual generating references are supplied. Failure with an operational library therefore cannot automatically be blamed on the solver. Conversely, a perfect reconstruction does not establish unique composition or physical field accuracy.

## What “ready” means here

Use three separate decisions: whether the supplied references improve synthetic fraction recovery; whether the revised ecological categories answer the intended research question; and whether independent field data validate the predictions. The first two can be assessed internally. The third is still missing.

Do not describe these tests as validated field cover, independent actual Landsat observations, or a universal sensor calibration. OLI channels are derived from NEON. Physical reflectance scaling, material purity, spatial alignment and independent contemporaneous fractional-cover measurements remain unresolved validation needs. Freezing the candidate library and evaluating independent observations is the next decisive step.

This target set differs from the October 19 360-target experiment: it has six atomic parent groups, excludes the union of both selections, and omits unresolved background categories. Historical scores must not be compared directly with these new scores as though the targets and recipes were identical.

## Reproducibility

Input hashes, source identity alignment and exclusions: `input_audit.json`. Frozen comparison design, code/kernel fingerprints and label maps: `protocol.json`. Exact reference IDs, target memberships, predictions, category/domain errors and paired summaries: `tables/`. Ridge preprocessing/coefficient values and tuning memberships: `models/`. Exhaustive class-set checkpoints: `checkpoints/`. Figure/source links: `figure_manifest.json`. Numerical and synthetic regression checks: `VALIDATION.md` and `validation.json`.

Original files were read in place. No raw spectral library or Parquet copy was made. Only compact identity/score tables, synthetic targets, model parameters and search winners were saved. No historical report, package algorithm or production default was changed. The earlier collaborator PDF remains based on the previous evidence; this experiment is a separately versioned update.
"""
    (OUT / "IES_COMPARISON_REPORT.md").write_text(text)
    html = markdown.markdown(text, extensions=["tables", "fenced_code"])
    for path in FIG.glob("*.png"):
        html = html.replace(
            'src="figures/' + path.name + '"',
            'src="data:image/png;base64,'
            + base64.b64encode(path.read_bytes()).decode()
            + '"',
        )
    style = "body{font:17px/1.65 system-ui,sans-serif;color:#183440;max-width:1120px;margin:40px auto;padding:0 24px}h1{font-size:39px;line-height:1.2}h2{margin-top:2em;border-bottom:2px solid #00887b;padding-bottom:8px}img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow-x:auto;font-size:14px}td,th{padding:8px 10px;border-bottom:1px solid #dce4e6;text-align:left}th{background:#edf4f2}code{font-size:13px}a{color:#007c76}"
    (OUT / "IES_COMPARISON_REPORT.html").write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>IES endmember and category comparison</title><link rel="icon" href="data:,"><style>{style}</style></head><body>{html}</body></html>'
    )
    save_manifest = dict(
        date="2026-10-22",
        source_git_commit=subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        figures=FIGURES,
        summary_sha256=hashlib.sha256((OUT / "summary.json").read_bytes()).hexdigest(),
        coverage_means=citable,
        report_builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (OUT / "figure_manifest.json").write_text(
        json.dumps(save_manifest, indent=2) + "\n"
    )
    print(
        "Built eight source-linked figures and a self-contained Markdown/HTML report."
    )


if __name__ == "__main__":
    main()
