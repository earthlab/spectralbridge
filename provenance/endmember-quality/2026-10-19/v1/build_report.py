"""Build explanatory figures and a human-readable report from compact results."""

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import markdown
import base64
from run_analysis import CLASSES, CONFIG

# Same category palette as examples/publication_figures/figure_data.py.
COLORS = dict(zip(CLASSES, ["#D55E00", "#0072B2", "#009E73", "#777777", "#CC79A7"]))

OUT = Path(__file__).resolve().parent
TABLES = OUT / "tables"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
S = json.loads((OUT / "summary.json").read_text())
BLUE = "#6495ED"
BROWN = "#B67F63"
DARK = "#25303D"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.facecolor": "white",
        "svg.fonttype": "none",
        "svg.hashsalt": "endmember-quality-20261019",
    }
)
manifest = {}


def load(name):
    return pd.read_csv(TABLES / (name + ".csv"))


def save(fig, name, caption, sources):
    fig.savefig(FIG / (name + ".png"), dpi=190, bbox_inches="tight")
    fig.savefig(FIG / (name + ".svg"), bbox_inches="tight", metadata={"Date": None})
    manifest[name] = {
        "caption": caption,
        "sources": sources,
        "sha256": {
            ext: hashlib.sha256((FIG / (name + "." + ext)).read_bytes()).hexdigest()
            for ext in ["png", "svg"]
        },
    }
    plt.close(fig)


members = load("selected_members")
bands = [c for c in members if c.startswith("olioli_undarkened_b")]
x = members[bands].to_numpy()
cy = members.category.to_numpy()
wave = [443, 482, 561, 655, 865, 1609, 2201]
fig, axes = plt.subplots(1, 5, figsize=(18, 4.5), sharey=True, layout="constrained")
for ax, c in zip(axes, CLASSES):
    use = cy == c
    ax.plot(np.arange(7), x[use].T, color=COLORS[c], alpha=0.10, lw=0.7)
    ax.plot(np.arange(7), np.median(x[use], axis=0), color=DARK, lw=2)
    ax.set(
        title=f"{c}\n{use.sum()} spectra / {members[use].GlobalID.nunique()} polygons",
        xticks=np.arange(7),
        xticklabels=wave,
        ylim=(0, 1),
    )
    ax.tick_params(axis="x", rotation=60)
axes[0].set_ylabel("Value in supplied array")
fig.supxlabel("OLI channel center label (nm; equally spaced channels)")
save(
    fig,
    "01_selected_spectra",
    "Selected curves span substantial within-category variation; dark lines are medians. Connecting segments do not represent continuous hyperspectral measurements.",
    ["selected_members.csv"],
)

selected = load("coverage_selected").set_index("category").reindex(CLASSES)
random = load("coverage_random")
fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), layout="constrained")
for ax, field, title in zip(
    axes,
    ["mean_same_class_RMSE", "recall"],
    [
        "Within-category coverage (smaller is closer)",
        "Nearest-reference label agreement (larger is higher)",
    ],
):
    mean = random.groupby("category")[field].mean().reindex(CLASSES)
    lo = random.groupby("category")[field].quantile(0.025).reindex(CLASSES)
    hi = random.groupby("category")[field].quantile(0.975).reindex(CLASSES)
    y = np.arange(5)
    ax.errorbar(
        mean,
        y + 0.12,
        xerr=np.vstack([mean - lo, hi - mean]),
        fmt="o",
        color=BROWN,
        capsize=4,
        label="Matched random pixels",
    )
    ax.scatter(
        selected[field], y - 0.12, color=BLUE, s=65, label="Selected pixels", zorder=4
    )
    ax.set(yticks=y, yticklabels=CLASSES, title=title)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.15)
axes[0].set_xlabel("Nearest same-category spectral RMSE (array units)")
axes[1].set_xlabel("Identity-weighted category recall")
axes[1].set_xlim(0, 1)
axes[0].legend(loc="lower right", fontsize=10)
fig.suptitle(
    "A trade-off: better category discrimination, poorer within-category coverage",
    fontsize=16,
)
save(
    fig,
    "02_coverage_controls",
    "Random controls preserve all 367 selected polygon identities and the selected pixel count per polygon. Bars show central 95% of 30 random draws, not population confidence intervals.",
    ["coverage_selected.csv", "coverage_random.csv"],
)

conf = (
    load("confusion")
    .pivot(index="truth", columns="prediction", values="proportion")
    .reindex(index=CLASSES, columns=CLASSES)
)
dom = load("coverage_domains")
dom["domain"] = dom.site + " " + dom.year.astype(str)
matrix = dom.pivot(index="category", columns="domain", values="recall").reindex(CLASSES)
fig, axes = plt.subplots(1, 2, figsize=(14, 6.3), layout="constrained")
for ax, data, title in zip(
    axes,
    [conf, matrix],
    [
        "Nearest-reference confusion\nRows: true category; columns: assigned category",
        "Category agreement by acquisition domain\nInternal diagnostics, not held-site prediction",
    ],
):
    im = ax.imshow(data, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    ax.set(
        title=title,
        xticks=range(data.shape[1]),
        xticklabels=data.columns,
        yticks=range(5),
        yticklabels=data.index,
    )
    ax.tick_params(axis="x", rotation=55)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(
                j,
                i,
                f"{100 * data.iloc[i, j]:.0f}%",
                ha="center",
                va="center",
                color="white" if data.iloc[i, j] > 0.55 else DARK,
            )
fig.colorbar(im, ax=list(axes), label="Recall / assignment share", shrink=0.7)
save(
    fig,
    "03_category_agreement",
    "Evergreen matches labels through this nearest-reference rule more reliably than Woody shrub and Herbaceous. Each source domain is visible, but the endmember selection saw all domains.",
    ["confusion.csv", "coverage_domains.csv"],
)

hull = load("cross_class_hull")
weights = load("cross_class_hull_weights")
rate = hull.groupby("category").feasible.agg(["sum", "count"]).reindex(CLASSES)
example = int(
    hull[hull.feasible].sort_values(["RMSE", "array_index"]).iloc[0].array_index
)
row = members.set_index("array_index").loc[example]
w = weights[weights.target_array_index == example]
reference = (
    members.set_index("array_index").loc[w.alternative_array_index, bands].to_numpy()
)
alternative = w.weight.to_numpy() @ reference
target = row[bands].to_numpy(dtype=float)
alt_class = np.array(
    [w.loc[w.alternative_category == c, "weight"].sum() for c in CLASSES]
)
example_table = pd.DataFrame(
    {
        "category": CLASSES,
        "labelled_target_fraction": (CLASSES == row.category).astype(float),
        "alternative_fraction": alt_class,
    }
)
example_table.to_csv(TABLES / "illustrative_ambiguity.csv", index=False)
fig, axes = plt.subplots(1, 3, figsize=(17, 5.1), layout="constrained")
axes[0].barh(
    np.arange(5), 100 * rate["sum"] / rate["count"], color=[COLORS[c] for c in CLASSES]
)
axes[0].set(
    yticks=np.arange(5),
    yticklabels=CLASSES,
    xlim=(0, 100),
    xlabel="Selected spectra with a cross-category fit (%)",
    title="223 / 603 numerical ambiguity certificates",
)
axes[0].invert_yaxis()
for j, (_, rr) in enumerate(rate.iterrows()):
    axes[0].text(
        100 * rr["sum"] / rr["count"] + 1,
        j,
        f"{int(rr['sum'])}/{int(rr['count'])}",
        va="center",
        fontsize=10,
    )
axes[1].plot(range(7), target, color=BLUE, lw=3, label="Labelled target")
axes[1].plot(
    range(7), alternative, color=BROWN, lw=2, ls="--", label="Other-category mixture"
)
axes[1].set(
    xticks=range(7),
    xticklabels=wave,
    title=f"Array column {example}: {row.category}",
    xlabel="OLI channel center label (nm)",
    ylabel="Value in supplied array",
)
axes[1].tick_params(axis="x", rotation=60)
axes[1].legend(fontsize=10)
axes[1].set_xlabel(
    f"OLI channel center label (nm)\nVerified RMSE {np.sqrt(np.mean((target - alternative) ** 2)):.1e}"
)
left = np.zeros(2)
for j, c in enumerate(CLASSES):
    vals = [float(row.category == c), alt_class[j]]
    axes[2].barh([0, 1], vals, left=left, color=COLORS[c], label=c)
    left += vals
axes[2].set(
    yticks=[0, 1],
    yticklabels=[
        "Recorded category\n(one-hot interpretation)",
        "Alternative\ncategory mixture",
    ],
    xlim=(0, 1),
    xlabel="Category weight",
    title="Same spectrum, different category weights",
)
axes[2].legend(loc="lower left", bbox_to_anchor=(0, -0.55), fontsize=9, ncol=1)
save(
    fig,
    "04_cross_category_ambiguity",
    "Full-library linear programs exclude every reference with the target label. Verified alternatives use nonnegative sum-one weights; multiple references per category and up to eight active references are allowed. These are not restricted three-material MESMA solutions.",
    [
        "cross_class_hull.csv",
        "cross_class_hull_weights.csv",
        "selected_members.csv",
        "illustrative_ambiguity.csv",
    ],
)

primary = "Selected screened MESMA"
rand = "Matched random screened MESMA"
prior = "Uniform design prior"
sparse = "Sparse design prior"
oracle = "Known-parent FCLS oracle"
methods = [primary, rand, prior, sparse, oracle]
ci = load("fraction_bootstrap_intervals").query('metric=="RMSE"').set_index("method")
fig, axes = plt.subplots(1, 2, figsize=(14, 6), layout="constrained")
values = np.array([S["synthetic_RMSE"][m] for m in methods])
low = np.array([ci.loc[m, "lower"] for m in methods])
high = np.array([ci.loc[m, "upper"] for m in methods])
axes[0].barh(range(5), values, color=[BLUE, BROWN, "#84909D", "#B7C1CC", "#527D69"])
axes[0].errorbar(
    values,
    range(5),
    xerr=np.vstack([np.maximum(values - low, 0), np.maximum(high - values, 0)]),
    fmt="none",
    color=DARK,
    capsize=4,
)
axes[0].set(
    yticks=range(5),
    yticklabels=[
        "Selected MESMA\n(3 screened/class)",
        "Matched random\n(3 screened/class)",
        "Dense prior\n(5 nonzero)",
        "Sparse prior\n(3 nonzero)",
        "Known-parent\nFCLS oracle",
    ],
    xlabel="Fraction RMSE (all targets and categories)",
    title="Synthetic fraction recovery: 360 targets / 8 bundles",
    xlim=(0, 0.4),
)
axes[0].invert_yaxis()
for i, value in enumerate(values):
    axes[0].text(
        max(value, high[i]) + 0.012,
        i,
        f"{value:.3f}" if value > 1e-10 else "≈ 0",
        ha="left",
        va="center",
    )
pred = load("selected_synthetic_predictions")
for j, c in enumerate(CLASSES, 1):
    t = pred[f"truth_{j}"]
    p = pred[f"prediction_{j}"]
    grid = np.unique(t)
    means = [p[np.isclose(t, g, rtol=0, atol=1e-12)].mean() for g in grid]
    axes[1].plot(grid, means, "o-", color=COLORS[c], label=c, lw=1.8)
axes[1].plot([0, 1], [0, 1], color=DARK, ls=":", lw=1.2)
axes[1].set(
    xlim=(0, 1),
    ylim=(0, 1),
    xlabel="Known algebraic fraction",
    ylabel="Mean predicted fraction",
    title="Selected library: false presence and shrinkage",
)
axes[1].legend(loc="upper left", fontsize=10)
save(
    fig,
    "05_synthetic_recovery",
    "Primary MESMA screens three references per category from the full library, then tests 375 admitted models with at most three categories. Error bars are conditional whole-bundle bootstrap intervals; eight bundles do not provide broad ecological validation.",
    [
        "selected_synthetic_predictions.csv",
        "fraction_bootstrap_intervals.csv",
        "summary.json",
    ],
)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
ks = [1, 2, 3, 5]
names = ["Screen1 sensitivity", "Screen2 sensitivity", primary, "Screen5 sensitivity"]
axes[0].plot(ks, [S["synthetic_RMSE"][m] for m in names], "o-", color=BLUE, lw=2)
axes[0].axhline(
    S["synthetic_RMSE"][prior], color=DARK, ls="--", label="Dense prior (5 nonzero)"
)
axes[0].axhline(
    S["synthetic_RMSE"][sparse],
    color="#84909D",
    ls=":",
    label="Sparse prior (3 nonzero)",
)
axes[0].set(
    xticks=ks,
    xlabel="Nearest candidates screened per category",
    ylabel="Synthetic fraction RMSE",
    title="Exploratory screening sensitivity",
)
axes[0].legend(loc="upper right", fontsize=10)
detail = load("screened_mesma_details")
group = detail[detail.method == primary]
axes[1].plot(
    [0.001, 0.005, 0.01],
    [
        group.near_class_sets_001.mean(),
        group.near_class_sets_005.mean(),
        group.near_class_sets.mean(),
    ],
    "o-",
    color=BROWN,
    lw=2,
)
axes[1].set(
    xticks=[0.001, 0.005, 0.01],
    xticklabels=["0.001", "0.005", "0.010"],
    xlabel="Additive spectral RMSE tolerance (array units)",
    ylabel="Mean near-fitting category sets (out of 25)",
    title="Ambiguity depends on the chosen tolerance",
    ylim=(0, 25),
)
save(
    fig,
    "06_sensitivity",
    "Screening 1, 2, 3 or 5 candidates per class does not beat the dense prior, but beats the three-category sparse prior in this synthetic design. These follow-up checks do not exhaust the full 16.9-million-model search. Near-fit tolerances are illustrative, not independently measured sensor noise.",
    ["screened_mesma_details.csv", "summary.json"],
)

(OUT / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

# Practical paired whole-bundle comparison of global RMSE, not a row bootstrap.
be = load("fraction_bundle_errors").pivot(
    index="bundle", columns="method", values="RMSE"
)
rng = np.random.default_rng(CONFIG["seed"])
draw = rng.integers(0, len(be), size=(1999, len(be)))
paired = {}
for other in [rand, prior, sparse]:
    difference = np.sqrt((be[primary].to_numpy()[draw] ** 2).mean(1)) - np.sqrt(
        (be[other].to_numpy()[draw] ** 2).mean(1)
    )
    paired[other] = {
        "difference": S["synthetic_RMSE"][primary] - S["synthetic_RMSE"][other],
        "conditional_95_percentile_interval": np.quantile(
            difference, [0.025, 0.975]
        ).tolist(),
    }
(OUT / "paired_fraction_comparisons.json").write_text(
    json.dumps(paired, indent=2) + "\n"
)

selected_counts = (
    members.groupby("category")
    .agg(spectra=("array_index", "size"), polygon_IDs=("GlobalID", "nunique"))
    .reindex(CLASSES)
)
class_table = "\n".join(
    f"| {i + 1} | {c} | {selected_counts.loc[c, 'spectra']} | {selected_counts.loc[c, 'polygon_IDs']} | {100 * selected.loc[c, 'recall']:.1f}% | {int(rate.loc[c, 'sum'])}/{int(rate.loc[c, 'count'])} |"
    for i, c in enumerate(CLASSES)
)
error_table = "\n".join(f"| {m} | {S['synthetic_RMSE'][m]:.3f} |" for m in methods)
diagnostics = load("fraction_diagnostics")
diagnostics = (
    diagnostics[diagnostics.method == primary].set_index("class_label").reindex(CLASSES)
)
rate_table = "\n".join(
    f"| {c} | {diagnostics.loc[c, 'RMSE']:.3f} | {100 * diagnostics.loc[c, 'absent_false_positive_rate']:.1f}% | {100 * diagnostics.loc[c, 'low_fraction_miss_rate']:.1f}% |"
    for c in CLASSES
)
coverage_penalty = 100 * (
    S["selected_macro_same_class_RMSE"] / S["matched_random_macro_same_class_RMSE_mean"]
    - 1
)
text = f"""# How good are the 603 selected OLI endmembers?

19 October 2026 · **Internal fixed-library diagnostic; not independent validation**

## Assessment

**Useful category signal, but not an abundance-validated endmember library.**
The selected pixels improve nearest-reference category agreement compared with
random pixels from the same polygon footprints. However, they cover within-category variation
less closely, many selected spectra admit other-category reconstructions, and the
screened synthetic unmixing experiment beats a three-category prior but does not
beat a dense five-category prior.
This does not establish that an exhaustive MESMA search or every possible use of
the library would fail. It does identify substantial concerns before abundance use.

## What was supplied and verified

The array has **85,706 observations × seven undarkened OLI channels**. All values
are finite, none are negative and all five recorded categories are represented.
The CSV contains **603 unique zero-based column indices**, confirmed by the user.
Those references come from **367 polygon identities**; one polygon contributes
as many as {members.groupby("GlobalID").size().max()} selected pixels. No selected spectra are exactly duplicated.

The label file stores category names. The user's numeric mapping is
preserved as the separate `class_code` field, never confused with array indexing:

| Code | Recorded category | Selected spectra | Selected polygon IDs | Nearest-reference recall | Cross-category hull matches |
|---|---|---:|---:|---:|---:|
{class_table}

The supplied spectra align, in original row order, with the repository polygon
Parquet's undarkened OLI columns divided by 10,000 (maximum absolute difference
7.46e-8, compatible with numerical precision). Every category label matches.
This establishes usable numerical lineage; it does not independently validate
physical units, pure materials or native Landsat observations.

The `imagery_year` field differs from source acquisition dates on **18,399 rows**.
This report derives acquisition years from `flight_id`; it does not rewrite the
original field or assume that the field necessarily means acquisition year.

![Selected seven-band traces and category medians.](figures/01_selected_spectra.png)

**What you see:** every selected trace, grouped by recorded category, with a dark median.
**What to notice:** there is considerable within-category variation and unequal
category/parent coverage. Segments connect discrete bands.
**What it means:** selecting 603 rows is not equivalent to sampling 603 independent plants.
**What it does not mean:** labelled polygons are verified pure materials or these
seven-band synthetic representations are independent Landsat measurements.

## 1. Coverage and category discrimination show a trade-off

For each polygon/site/acquisition-year, take within-flight medians, then the
median of those flight summaries. Exclude every one of the 367 candidate polygon
IDs globally. This leaves **{S["target_polygon_IDs"]:,} polygon IDs / {S["target_curves"]:,} summary curves**.
Repeated identity histories share total weight one in aggregate results.
These targets are disjoint from the chosen references, but **selection already
examined the entire library**, so they are not selection-blind holdouts.

The control draws **30 alternative libraries**. Each preserves exactly the
selected pixel count from **each same polygon ID**. Category counts, parent
identities and per-parent capacity are therefore matched; only the chosen pixels
change. Controls may by chance include supplied selected pixels. This comparison
isolates pixel selection within these polygon footprints, not selection of different polygon footprints.

- Mean nearest **same-category** spectral RMSE: selected **{S["selected_macro_same_class_RMSE"]:.5f}**;
  matched random mean **{S["matched_random_macro_same_class_RMSE_mean"]:.5f}**. Selected distances are
  **{coverage_penalty:.1f}% larger** (worse coverage by this metric).
- Nearest **single-reference category agreement**, balanced across categories:
  selected **{100 * S["selected_single_reference_BA"]:.1f}%** versus random mean
  **{100 * S["matched_random_single_reference_BA_mean"]:.1f}%**. Random-draw central 95% spread is
  **{100 * S["matched_random_single_reference_BA_range"][0]:.1f}–{100 * S["matched_random_single_reference_BA_range"][1]:.1f}%**.
- Evergreen recall is **87.3%**, whereas Woody shrub is **40.3%** and Herbaceous
  **45.3%** under this particular raw-band nearest-reference rule.

A stricter follow-up also preserves the selected pixel count from **each same
polygon and flightline**, preventing changes in acquisition composition. Its 30
random controls average **{S["flight_matched_random_macro_same_class_RMSE_mean"]:.5f}**
for same-category RMSE and **{100 * S["flight_matched_random_single_reference_BA_mean"]:.1f}%**
for nearest-reference balanced agreement. The broad coverage/discrimination
trade-off remains; both sets of controls are saved. This does not make either
comparison selection-blind.

Spectral RMSE is in supplied-array units. This is a descriptive proximity rule,
not the earlier nested classifier, not MESMA abundance and not deployment accuracy.
The result is compatible with selecting more discriminating references at the
cost of representing typical within-category variation. The selector's exact
objective/script was not supplied, so its intended optimization cannot be judged.

![Coverage and label agreement against exact-parent matched random controls.](figures/02_coverage_controls.png)

**What you see:** selected pixels versus 30 matched random libraries, by category.
**What to notice:** selection improves some category recalls while coverage worsens.
**What it means:** quality depends on whether the goal is discrimination or reconstruction.
**What it does not mean:** the random-draw ranges are population confidence intervals
or this internal comparison is independent confirmation.

![Nearest-reference confusion and source-domain category agreement.](figures/03_category_agreement.png)

**What you see:** confusion between recorded labels and performance by acquisition domain.
**What to notice:** category difficulties differ; the overall average hides failures.
**What it means:** all categories and domains should remain visible during evaluation.
**What it does not mean:** these are held-site models: the original selection saw all sites.

## 2. The selected library contains concrete category ambiguity

For each selected spectrum, exclude **every reference with its own category**.
Solve a full-library linear feasibility problem: can a nonnegative, sum-one
combination of the other categories reconstruct the same seven-band vector?
Numerical certificates are accepted only after separately checking spectral RMSE
≤1e-8, nonnegativity and sum-one constraints.

**{S["cross_class_convex_hull_matches"]} of 603 ({100 * S["cross_class_convex_hull_matches"] / 603:.1f}%)** have verified alternatives.
Herbaceous has **54/90 (60.0%)**, Evergreen **80/166 (48.2%)**, and background/dead
**11/141 (7.8%)**. Thus even a perfect reconstruction can disagree with the recorded
one-hot category interpretation of a reference.

This feasibility diagnostic permits multiple references per category and as many
as eight active references in seven-dimensional affine space. It is **broader
than three-component, one-reference-per-category MESMA**. Failure to find such a
certificate does not prove uniqueness, especially for mixed targets or noisy data.
All 223 certificates and their actual reference indices/weights are saved.

![Verified cross-category alternatives and an overlapping reconstructed trace.](figures/04_cross_category_ambiguity.png)

**What you see:** certificate counts and one concrete target/alternative reconstruction.
**What to notice:** the spectra overlap, while the category weight vectors differ.
**What it means:** this dictionary does not guarantee unique category composition.
**What it does not mean:** the LP alternative is known biological truth or is admitted
by the more restrictive screened MESMA experiment.

The selected library's affine spectral rank is seven. With 603 references, unique
individual-reference fractions cannot generally be recovered from seven bands
and one sum constraint. That dimension argument alone does not prove category
ambiguity; the explicit certificates supply the category-level evidence here.

## 3. Synthetic recovery improves on a matched sparse prior

Use **eight disjoint parent bundles**, two in each observed site/acquisition-year
cell, with one distinct parent per category. No generating parent occurs in the
selected library or another bundle. Generate 45 mixtures per bundle: ten category
pairs at fractions 0.1/0.5/0.9, ten equal-third triples, and five pure-parent targets.
This gives **360 known algebraic mixtures**, not 360 independent plants or field plots.

For each target, screen the three closest references **per category** from all
603 selected spectra using spectral RMSE only, never the known fractions. The
existing numerical solver then searches **375 admitted models**, at most three
categories, with nonnegative sum-one fractions. A full unfiltered search would
have **{S["full_distinct_class_up_to_three_model_count"]:,}** such candidate models per target and was not run.
Consequently this tests a **screened inference configuration**, not exhaustive
full-library MESMA. Solver rank/interior/update tolerances remain those of the
existing `spectralbridge.mixtures.fit_models` implementation.

| Model / control | Fraction RMSE |
|---|---:|
{error_table}

The oracle is approximately **3.6e-14**: correct generating parents recover the
synthetic truth. The selected configuration's **0.322** does not beat the uniform
**0.304** prior. The prior is fixed at 0.2 per class from the symmetric design,
not fitted using test fractions. One matched random library gives **0.313**;
that is one draw, not a population-level claim about random selection superiority.

RMSE above is `sqrt(mean squared error over targets and categories)`. For clarity,
mean per-target RMSE gives selected **0.293**, random **0.283**, prior **0.292**:
aggregation matters, but it does not reveal a selected-library advantage over the
dense prior in this experiment. These values are not directly interchangeable with
previous mean-fold synthetic-study headline RMSEs.

Whole-bundle bootstrap intervals are conditional on eight sampled bundles and
this synthetic recipe. Resampling uses the observed domain mixture and does not
model spatial correlation between nearby polygons. Treat these intervals as
internal sensitivity summaries, not independently validated population coverage. The selected-minus-prior RMSE difference is
**{paired[prior]["difference"]:.3f}**, with conditional 95% percentile interval
**{paired[prior]["conditional_95_percentile_interval"][0]:.3f} to {paired[prior]["conditional_95_percentile_interval"][1]:.3f}**.
The selected-minus-one-random-draw difference is
**{paired[rand]["difference"]:.3f}**, interval
**{paired[rand]["conditional_95_percentile_interval"][0]:.3f} to {paired[rand]["conditional_95_percentile_interval"][1]:.3f}**.
These are internal sensitivity summaries, not geographic/field validation.

![Synthetic fraction errors and class calibration against known generating weights.](figures/05_synthetic_recovery.png)

**What you see:** selected and control errors plus calibration by true fraction.
**What to notice:** the oracle succeeds, whereas the selected configuration does
outperforms the sparse prior but not the dense prior; absent classes receive positive predictions.
**What it means:** accurate spectral reconstruction is insufficient for fraction recovery.
**What it does not mean:** every MESMA configuration must fail or any result validates field cover.

### A constraint-matched prior changes what we can conclude

MESMA outputs at most three nonzero category fractions. The dense prior uses all
five. A follow-up fairness control therefore assigns **1/3 each to the first
three predefined categories** and zero to the others, without inspecting any target
spectrum or selecting categories from outcomes. Under this balanced synthetic
recipe any fixed triple has the same aggregate error. Its fraction RMSE is
**{S["synthetic_RMSE"][sparse]:.3f}**. MESMA's **0.322** improves on that sparse baseline,
so the spectra add some quantification information under the same sparsity limit.

The stronger dense prior predicts the design expectation, while MESMA searches
for a spectrally fitting sparse composition. These are different objectives and
output constraints. Failing to beat the dense prior alone is **not** evidence of a
broken solver or proof that the selected library contains no useful information.
Neither comparison establishes accurate, unique biological abundance. The sparse
control was added after reviewing this potential confound, not presented as a
preregistered experiment.

### Detection and quantification are different failures

At the explicit comparison threshold **predicted fraction ≥0.10**, absent-class
false detections are common. A low positive fraction is defined as `0 < truth ≤0.20`.
Thresholds are comparison rules, not independently measured physical detection limits.

| Category | Fraction RMSE | False positive when truly absent | Miss at low positive fraction |
|---|---:|---:|---:|
{rate_table}

### Screening and near-fit sensitivity

After the primary run, repeat with 1, 2 and 5 screened candidates per class.
Fraction RMSE is **0.336 / 0.328 / 0.316**, respectively, versus the primary
three-candidate **0.322**. More candidates improve fit and some fraction error,
but none beats the dense design prior here; all improve on the sparse prior. These exploratory checks do not establish
what the full 16.9-million-model search would do.

At additive near-fit tolerance 0.01 array RMSE, the primary search has mean
**17.8 near-fitting category sets** (out of 25), with median maximum category
fraction range **1.0**. Reducing tolerance to 0.001 gives mean **4.5** near sets.
These tolerances are illustrative, not calibrated sensor noise. The existing
solver saves one best solution per category set: ranges are **restricted candidate
ambiguity**, not exhaustive feasible or biological uncertainty.

![Screening and near-fit tolerance sensitivity.](figures/06_sensitivity.png)

**What you see:** fraction error as screening expands, and near-set count as tolerance expands.
**What to notice:** conclusions depend on the evaluated search and tolerance.
**What it means:** both inference design and library ambiguity must be reported.
**What it does not mean:** a selected operating point is universally optimal or
near-set ranges are confidence intervals.

## Recommended next step

Keep this as a candidate reference dictionary, but **do not describe it as validated
for category abundance**. Obtain the selector script/objective and repeat selection
inside training-only polygon/site folds. Evaluate unmixing on parent-disjoint target
curves, compare matched parent/library capacities, and retain failed controls.
For the frozen whole-library selection, independent new observations are needed
for selection-blind performance. Field abundance additionally requires independent,
contemporaneous fractions at matched spatial support and verified reference meaning.

## Reproducibility and limits

`preflight.py` records the initial ambiguity before the user clarified indexing;
`summary.json` is the current confirmed analysis. `run_analysis.py` reads the three
original files and the existing Parquet in place. No source file is changed or copied.
`selected_members.csv` and `target_coverage.csv` preserve reference/target IDs.
Figures are regenerated from compact results by `build_report.py`. Input/code
hashes, the 30 controls, every LP certificate, synthetic parent memberships,
predictions, per-class errors and bootstrap summaries are retained in this packet.
No earlier scientific outputs, production algorithms or coefficients were changed.

From repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python provenance/endmember-quality/2026-10-19/v1/run_analysis.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python provenance/endmember-quality/2026-10-19/v1/build_report.py
.venv/bin/python -m pytest -ra tests/test_selected_endmember_quality.py tests/test_mixtures.py
```
"""
(OUT / "ENDMEMBER_QUALITY_REPORT.md").write_text(text)
html = markdown.markdown(text, extensions=["tables", "fenced_code"])
# A single portable HTML report; original figure exports remain separately available.
for image_path in sorted(FIG.glob("*.png")):
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    html = html.replace(
        'src="figures/' + image_path.name + '"',
        'src="data:image/png;base64,' + encoded + '"',
    )

style = """body{font:17px/1.65 system-ui,sans-serif;color:#25303d;max-width:1080px;margin:45px auto;padding:0 24px;background:white}h1{font-size:38px;line-height:1.2}h2{margin-top:2em;border-bottom:2px solid #6495ed;padding-bottom:8px}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:15px;display:block;overflow-x:auto}td,th{padding:9px 12px;border-bottom:1px solid #dce4ed;text-align:left}th{background:#edf2fa}code,pre{font-size:13px;background:#f2f5f8}pre{padding:15px;overflow-x:auto}a{color:#235ba8}"""
(OUT / "ENDMEMBER_QUALITY_REPORT.html").write_text(
    f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Selected endmember quality</title><style>{style}</style></head><body>{html}</body></html>'
)
print("Built six figures and Markdown/HTML report")
