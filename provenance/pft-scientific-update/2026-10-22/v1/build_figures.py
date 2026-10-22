"""Presentation-only redraws from completed, hash-verified researcher-category results.

No fitting, statistical testing, raw-library scan or source-data materialization.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import platform
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
OLD = ROOT / "provenance/researcher-pft-information/2026-10-15/v1"
NEW = ROOT / "provenance/researcher-evidence/2026-10-16/v1"
END = ROOT / "provenance/endmember-quality/2026-10-19/v1"
EXH = END.parent / "exhaustive-v1"
COMPACT = (
    ROOT
    / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact/corr_polygon_year.parquet"
)
CATS = ["Deciduous", "Evergreen", "Herbaceous", "Non-vegetated & dead", "Woody shrub"]
SHORT = ["Deciduous", "Evergreen", "Herbaceous", "Non-vegetated\n& dead", "Woody shrub"]
COLORS = dict(zip(CATS, ["#D07A2F", "#007C76", "#709636", "#7C6C64", "#8A5D9B"]))
INK = "#183440"
BLUE = "#205F8A"
ORANGE = "#C46632"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11.5,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#BAC6CB",
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "svg.fonttype": "none",
        "svg.hashsalt": "pft-scientific-update-20261022",
        "figure.facecolor": "white",
    }
)
SOURCES = {}
CLAIMS = []
FIGURES = []
EXPECTED = {}
for packet, key, relative in [
    (OLD, "sha256", False),
    (NEW, "sha256", False),
    (END, "sha256", False),
    (EXH, "files", True),
]:
    manifest = packet / (
        "final_manifest.json" if packet in (OLD, NEW) else "packet_manifest.json"
    )
    for name, digest in json.loads(manifest.read_text())[key].items():
        EXPECTED[(packet / name if relative else ROOT / name).resolve()] = digest
ledger = json.loads((COMPACT.parent.parent / "statistics_manifest.json").read_text())
EXPECTED[COMPACT.resolve()] = ledger["outputs"]["compact/corr_polygon_year.parquet"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def register(path):
    path = Path(path).resolve()
    digest = sha(path)
    if path in EXPECTED and EXPECTED[path] != digest:
        raise ValueError("Existing evidence hash mismatch: " + str(path))
    if path not in EXPECTED:
        raise ValueError("No authoritative result fingerprint for " + str(path))
    SOURCES[str(path.relative_to(ROOT))] = dict(
        sha256=digest, checked_against_existing_manifest=True
    )
    return path


def csv(packet, name):
    return pd.read_csv(register(packet / "tables" / name))


def js(packet, name):
    return json.loads(register(packet / name).read_text())


def claim(key, value, source, selection, scope):
    CLAIMS.append(
        dict(
            id=key,
            value=value,
            source=str(Path(source).relative_to(ROOT)),
            selection=selection,
            scope=scope,
        )
    )
    return value


def finish(fig, num, stem, title, sources, method, transform, lesson):
    path = BASE / "figures" / f"F{num:02}_{stem}"
    path.parent.mkdir(exist_ok=True)
    for ext in ["png", "svg"]:
        fig.savefig(
            path.with_suffix("." + ext),
            dpi=240,
            bbox_inches="tight",
            metadata={"Date": None}
            if ext == "svg"
            else {"Software": "SpectralBridge presentation redraw"},
        )
    plt.close(fig)
    FIGURES.append(
        dict(
            number=num,
            filename=str(path.with_suffix(".png").relative_to(ROOT)),
            title=title,
            sources=[str(Path(p).relative_to(ROOT)) for p in sources],
            related_package_function=method,
            presentation_transform=transform,
            lesson=lesson,
            sha256={ext: sha(path.with_suffix("." + ext)) for ext in ["png", "svg"]},
        )
    )


def gaps(ax):
    for lo, hi in [(1340, 1450), (1790, 2000)]:
        ax.axvspan(lo, hi, color="#E6E9EB", zorder=0)
    ax.set_xlim(385, 2510)
    ax.set_xticks([400, 700, 1000, 1300, 1600, 1900, 2200, 2500])


def main():
    foundation = js(NEW, "foundation.json")
    support = csv(NEW, "category_support.csv")
    cells = csv(NEW, "site_year_category_support.csv")
    metrics = {}
    for key in [
        "polygon_GlobalIDs",
        "polygon_year_spectra",
        "repeated_IDs",
        "NEON_coordinates",
        "OLI_channels",
        "source_pixel_rows",
    ]:
        metrics[key] = claim(
            key,
            foundation[key],
            NEW / "foundation.json",
            key,
            "Recorded category-labelled polygon library; distinct IDs need not be spatially independent",
        )
    metrics["sites"] = claim(
        "sites",
        int(cells.site.nunique()),
        NEW / "tables/site_year_category_support.csv",
        "distinct site",
        "Observed sites only",
    )
    metrics["cells"] = claim(
        "site_year_cells",
        len(cells[["site", "year"]].drop_duplicates()),
        NEW / "tables/site_year_category_support.csv",
        "distinct site,year",
        "Observed acquisition cells, incompletely crossed",
    )
    # F1: Every existing polygon-year curve; no thinning, clipping or refitting.
    frame = (
        pd.read_parquet(register(COMPACT))
        .sort_values(["site", "year", "GlobalID"])
        .reset_index(drop=True)
    )
    assert not frame.duplicated(["site", "year", "GlobalID"]).any()
    assert set(frame.cover_category) == set(CATS)
    assert (
        len(frame) == foundation["polygon_year_spectra"]
        and frame.GlobalID.nunique() == foundation["polygon_GlobalIDs"]
    )
    cols = [c for c in frame if c.startswith("corr_wl")]
    w = np.array([float(c.split("_wl")[1][:-2]) for c in cols])
    values = frame[cols].to_numpy(float)
    good = np.isfinite(values).all(0) & ~(
        ((w >= 1340) & (w <= 1450)) | ((w >= 1790) & (w <= 2000))
    )
    w, values = w[good], values[:, good]
    assert len(w) == foundation["NEON_coordinates"]
    segments = np.split(np.arange(len(w)), np.where(np.diff(w) > 8)[0] + 1)
    fig, axes = plt.subplots(
        5, 1, figsize=(8.6, 6.5), sharex=True, sharey=True, layout="constrained"
    )
    cap = np.ceil(values.max() / 1000)
    for ax, cat in zip(axes, CATS):
        mask = frame.cover_category.eq(cat).to_numpy()
        a = values[mask] / 1000
        row = support.set_index("researcher_category").loc[cat]
        assert int(row.GlobalIDs) == frame.loc[mask, "GlobalID"].nunique()
        assert int(row.annual_rows) == int(mask.sum())
        for seg in segments:
            ax.plot(
                w[seg],
                a[:, seg].T,
                color=COLORS[cat],
                alpha=0.035,
                lw=0.35,
                rasterized=True,
            )
            ax.plot(w[seg], np.median(a[:, seg], axis=0), color=COLORS[cat], lw=2.2)
        gaps(ax)
        ax.set_ylim(0, cap)
        ax.set_yticks([0, 4, 8])
        ax.tick_params(labelsize=10)
        ax.text(
            0.012,
            0.88,
            f"{cat}   |   {int(row.GlobalIDs):,} polygons; {int(row.annual_rows):,} annual curves",
            transform=ax.transAxes,
            fontsize=10.5,
            weight="bold",
            va="top",
            bbox=dict(facecolor="white", alpha=0.9, edgecolor="none", pad=1),
        )
    axes[-1].set_xlabel("Wavelength (nm)")
    fig.supylabel("Stored spectral signal (thousands of source units)", fontsize=11)
    finish(
        fig,
        1,
        "observed_spectra",
        "Variation is visible within every assigned PFT",
        [COMPACT, NEW / "tables/category_support.csv", NEW / "foundation.json"],
        "spectralbridge.mesma_readiness.load_compact_inputs",
        "All 4,807 compact polygon-year curves; same supported 360-coordinate grid as existing analysis; divide ordinate by 1,000 for display only; median of displayed annual curves, no inferred physical conversion",
        "PFT structure coexists with broad within-group variation; curves and repeated years are not independent new plants.",
    )
    # F2: Exact saved effect for each of four cohorts; ranges are not confidence intervals.
    whole = csv(NEW, "whole_spectrum_separability.csv")
    pairs = csv(NEW, "pair_support_and_evidence.csv")
    assert len(whole) == 40 and whole.NEON_supported.all() and whole.OLI_supported.all()
    metrics["supported_contrasts"] = claim(
        "supported_contrasts",
        int(whole.NEON_supported.sum()),
        NEW / "tables/whole_spectrum_separability.csv",
        "NEON_supported.sum()",
        "Ten pairwise contrasts in each of four acquisition-matched cohorts; not 40 independent studies",
    )
    metrics["pairs"] = claim(
        "pairs",
        int(whole.contrast.nunique()),
        NEW / "tables/whole_spectrum_separability.csv",
        "contrast.nunique()",
        "All researcher-category pairs",
    )
    metrics["largest_adjusted_p"] = claim(
        "largest_adjusted_p",
        float(whole.NEON_p_holm.max()),
        NEW / "tables/whole_spectrum_separability.csv",
        "NEON_p_holm.max()",
        "Existing blocked whole-spectrum combined test and Holm family correction; exchangeability assumed",
    )
    order = pairs.sort_values("min_NEON_effect").contrast.tolist()
    fig, ax = plt.subplots(figsize=(8.6, 5.6), layout="constrained")
    shapes = ["o", "s", "^", "D"]
    domains = list(
        whole[["site", "year"]].drop_duplicates().itertuples(index=False, name=None)
    )
    for y, pair in enumerate(order):
        d = whole[whole.contrast.eq(pair)]
        ax.plot(
            [d.NEON_effect.min(), d.NEON_effect.max()],
            [y, y],
            color="#AEBCC3",
            lw=3,
            zorder=1,
        )
        for i, (site, year) in enumerate(domains):
            r = d[d.site.eq(site) & d.year.eq(year)].iloc[0]
            ax.scatter(
                r.NEON_effect,
                y,
                marker=shapes[i],
                s=52,
                color=[BLUE, "#579DA4", ORANGE, "#6C5B86"][i],
                label=f"{site} {year}" if y == 0 else None,
                zorder=3,
            )
    ax.set_yticks(
        range(len(order)),
        [
            p.replace("Non-vegetated & dead", "Non-veg. & dead").replace(" / ", " /\n")
            for p in order
        ],
        fontsize=10.5,
    )
    ax.set_xlabel(
        "Saved whole-spectrum standardized effect (larger = stronger difference)"
    )
    ax.set_xlim(0, 2)
    ax.invert_yaxis()
    ax.grid(axis="x", color="#E8EDEF")
    fig.legend(
        *ax.get_legend_handles_labels(),
        ncol=4,
        loc="outside lower center",
        fontsize=9.5,
        frameon=False,
    )
    finish(
        fig,
        2,
        "pairwise_differences",
        "All pairs differ, but their separation is unequal",
        [
            NEW / "tables/whole_spectrum_separability.csv",
            NEW / "tables/pair_support_and_evidence.csv",
        ],
        "spectralbridge.pft_method_audit.method_statistics",
        "Plot saved NEON_effect per cohort, connected minimum/maximum; no new hypothesis test; observed cohort range is not a confidence interval",
        "Background contrasts tend to be large; deciduous/shrub is among the smaller contrasts. Statistical evidence does not assign an unknown polygon correctly.",
    )
    # F3: Magnitude map only, preserving masked gaps and existing inferential scope.
    coord = csv(OLD, "cohort_wavelength_inference.csv")
    order = pairs.contrast.tolist()
    full = np.arange(385.0, 2515.0, 5.0)
    mat = (
        coord.assign(magnitude=coord.matched_effect.abs())
        .groupby(["pair", "wavelength_nm"])
        .magnitude.median()
        .unstack()
        .reindex(index=order, columns=full)
    )
    fig, ax = plt.subplots(figsize=(8.6, 5.2), layout="constrained")
    cmap = LinearSegmentedColormap.from_list(
        "contrast", ["#F6F9FA", "#99BEC9", "#356C8A", "#173B56"]
    )
    cmap.set_bad("#E5E8E9")
    im = ax.imshow(
        mat.to_numpy(),
        aspect="auto",
        extent=(382.5, 2512.5, 9.5, -0.5),
        vmin=0,
        vmax=float(np.nanmax(mat)),
        cmap=cmap,
        interpolation="nearest",
    )
    ax.set_yticks(
        range(10),
        [
            p.replace("Non-vegetated & dead", "Non-veg. & dead").replace(" / ", " /\n")
            for p in order
        ],
        fontsize=10.5,
    )
    ax.set_xticks([400, 700, 1000, 1300, 1600, 1900, 2200, 2500])
    ax.tick_params(axis="x", labelsize=10)
    ax.set_xlabel("Wavelength (nm)")
    for lo, hi, label in [
        (385, 700, "Visible"),
        (750, 1335, "Near infrared"),
        (1455, 1785, "SWIR 1"),
        (2005, 2510, "SWIR 2"),
    ]:
        ax.text((lo + hi) / 2, -0.8, label, ha="center", fontsize=9, clip_on=False)
    fig.colorbar(
        im,
        ax=ax,
        pad=0.025,
        shrink=0.8,
        label="Median absolute standardized effect\nacross the four sampled cohorts",
    )
    finish(
        fig,
        3,
        "wavelength_structure",
        "Different PFT pairs emphasize different wavelengths",
        [
            OLD / "tables/cohort_wavelength_inference.csv",
            NEW / "tables/pair_support_and_evidence.csv",
        ],
        "spectralbridge.pft_method_audit.method_statistics",
        "Median of absolute saved matched effects across four cohorts, for display only; original coordinate-level tests unchanged; no band selected and no new test or PCA",
        "Broad wavelength regions contribute different contrasts; the map describes group differences, not validated feature selection.",
    )
    # F4: Primary nested recognition, same rows/labels in both representations.
    feat = csv(OLD, "complementary_feature_performance.csv")
    fig, ax = plt.subplots(figsize=(8.6, 4.6), layout="constrained")
    for j, (sensor, budget, color) in enumerate(
        [("NEON", "360", BLUE), ("Synthetic OLI", "OLI", ORANGE)]
    ):
        means = []
        for i, kind in enumerate(["plant", "site"]):
            d = feat[feat.kind.eq(kind) & feat.budget.astype(str).eq(budget)]
            v = d.balanced_accuracy.to_numpy()
            value = float(v.mean())
            means.append(value)
            metrics[f"{sensor}_{kind}"] = claim(
                f"{sensor}_{kind}",
                value,
                OLD / "tables/complementary_feature_performance.csv",
                f"kind={kind}, budget={budget}; mean balanced_accuracy",
                "Equal-weight mean over three observed outer folds; unknown identities excluded from training, not a deployment probability",
            )
            x = i + (j - 0.5) * 0.28
            ax.bar(
                x,
                value,
                width=0.25,
                color=color,
                label=f"{sensor}: " + ("360 coordinates" if j == 0 else "7 channels")
                if i == 0
                else None,
            )
            ax.scatter(np.full(len(v), x), v, s=34, c="white", edgecolors=INK, zorder=4)
            ax.text(
                x,
                max(value, float(v.max())) + 0.035,
                f"{100 * value:.1f}%",
                ha="center",
                weight="bold",
                fontsize=15,
            )
    ax.axhline(0.2, color="#8D999E", ls="--", lw=1.3)
    ax.text(1.47, 0.21, "20% equal-class chance", ha="right", fontsize=9)
    ax.set_xticks(
        [0, 1],
        [
            "Unseen polygons\nwithin sampled population",
            "Held-out sites\nthree observed site targets",
        ],
    )
    ax.set_ylim(0, 1.02)
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylabel("Balanced accuracy = mean recall across the five classes")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
        ncol=2,
        frameon=False,
        fontsize=11,
    )
    finish(
        fig,
        4,
        "recognition",
        "Useful recognition becomes harder at a new site",
        [OLD / "tables/complementary_feature_performance.csv"],
        "spectralbridge.library_analysis.evaluate_identifiability",
        "Existing mean outer-fold balanced_accuracy, with individual fold scores as white dots; no refit and no confidence intervals",
        "Full NEON recognizes the assigned categories better than synthetic OLI; held-site transfer is weaker than new-polygon recognition.",
    )
    # F5: Confusion, average each fold's within-true-class proportions.
    confusion = csv(OLD, "confusion_plot_values.csv")
    m = (
        confusion[confusion.representation.eq("NEON") & confusion.kind.eq("site")]
        .pivot(index="truth", columns="predicted", values="mean_fold_row_fraction")
        .reindex(index=CATS, columns=CATS)
    )
    assert np.allclose(m.sum(axis=1), 1)
    rates = csv(OLD, "class_specific_transfer.csv")
    r = (
        rates[rates.kind.eq("site") & rates.budget.astype(str).eq("360")]
        .groupby("researcher_category")
        .recall.mean()
        .reindex(CATS)
    )
    assert np.allclose(np.diag(m), r)
    for cat in CATS:
        metrics["recall_" + cat] = claim(
            "recall_" + cat,
            float(r[cat]),
            OLD / "tables/class_specific_transfer.csv",
            f"kind=site,budget=360,researcher_category={cat}; mean recall",
            "Mean observed held-site recall, not precision and not a universal PFT accuracy",
        )
    metrics["shrub_to_deciduous"] = claim(
        "shrub_to_deciduous",
        float(m.loc["Woody shrub", "Deciduous"]),
        OLD / "tables/confusion_plot_values.csv",
        "NEON,site,truth=Woody shrub,predicted=Deciduous",
        "Mean fold row-normalized confusion",
    )
    fig, ax = plt.subplots(figsize=(8.6, 5.8), layout="constrained")
    im = ax.imshow(
        m.to_numpy(),
        vmin=0,
        vmax=1,
        cmap=LinearSegmentedColormap.from_list(
            "confusion", ["#F3F6F7", "#9EC6D0", "#176172"]
        ),
    )
    for y in range(5):
        for x in range(5):
            ax.text(
                x,
                y,
                f"{100 * m.iloc[y, x]:.0f}%",
                ha="center",
                va="center",
                fontsize=14,
                weight="bold" if x == y else "normal",
                color="white" if m.iloc[y, x] > 0.5 else INK,
            )
    ax.set_xticks(
        range(5),
        ["Deciduous", "Evergreen", "Herbaceous", "Non-veg.\n& dead", "Woody\nshrub"],
        fontsize=10,
    )
    ax.set_yticks(range(5), SHORT, fontsize=11)
    ax.set_xlabel("Assigned by the classifier", labelpad=14)
    ax.set_ylabel("Researcher-assigned category", labelpad=10)
    for tick, cat in zip(ax.get_xticklabels(), CATS):
        tick.set_color(COLORS[cat])
    for tick, cat in zip(ax.get_yticklabels(), CATS):
        tick.set_color(COLORS[cat])
    fig.colorbar(
        im,
        ax=ax,
        shrink=0.76,
        label="Share of each true category (mean across held-site folds)",
    )
    finish(
        fig,
        5,
        "confusion",
        "The average hides a major woody-shrub limitation",
        [
            OLD / "tables/confusion_plot_values.csv",
            OLD / "tables/class_specific_transfer.csv",
        ],
        "spectralbridge.spectral_learning.classification_metrics",
        "Plot the saved NEON/site mean_fold_row_fraction; rows sum to one; diagonal independently agrees with class_specific_transfer mean recall",
        "Evergreen and background/dead transfer best; woody shrub is often missed, especially as deciduous. These are class recalls, not precision.",
    )
    # F6: Same-parent controls; retain the two different quality criteria.
    selected = csv(END, "coverage_selected.csv")
    random = csv(END, "coverage_random.csv")
    summary = js(END, "summary.json")
    metrics["endmembers"] = summary["selected_members"]
    metrics["selected_parents"] = summary["selected_polygon_IDs"]
    for k in [
        "selected_members",
        "selected_polygon_IDs",
        "selected_macro_same_class_RMSE",
        "selected_single_reference_BA",
        "matched_random_macro_same_class_RMSE_mean",
        "matched_random_single_reference_BA_mean",
        "target_polygon_IDs",
        "target_curves",
    ]:
        claim(
            k,
            summary[k],
            END / "summary.json",
            k,
            "Internal whole-library selection; 30 random libraries match each selected polygon and its pixel capacity; not selection-blind",
        )
        metrics[k] = summary[k]
    fig, axes = plt.subplots(
        1, 2, figsize=(8.6, 5.4), layout="constrained", sharey=True
    )
    for ax, field, mult, title in zip(
        axes,
        ["mean_same_class_RMSE", "recall"],
        [1, 100],
        [
            "Same-category spectral distance\nSmaller = closer coverage",
            "Nearest-reference category recall\nLarger = better label agreement",
        ],
    ):
        for y, cat in enumerate(CATS):
            value = float(selected.set_index("category").loc[cat, field]) * mult
            draws = random[random.category.eq(cat)][field].to_numpy() * mult
            lo, hi = np.quantile(draws, [0.025, 0.975])
            mean = draws.mean()
            ax.hlines(y, lo, hi, color="#9AA9B0", lw=2)
            ax.scatter(
                mean,
                y,
                marker="o",
                s=70,
                facecolors="white",
                edgecolors=INK,
                label="Matched random mean / 95% draw spread" if y == 0 else None,
                zorder=3,
            )
            ax.scatter(
                value,
                y,
                marker="D",
                s=65,
                color=COLORS[cat],
                label="Selected pixels" if y == 0 else None,
                zorder=4,
            )
        ax.set_title(title, fontsize=11.5, pad=15)
        ax.set_yticks(range(5), SHORT)
        ax.set_ylim(4.5, -0.5)
        ax.grid(axis="x", color="#EDF0F1")
        ax.set_axisbelow(True)
    axes[0].set_xlabel("Spectral RMSE (supplied-array units)")
    axes[1].set_xlabel("Correct recorded category (%)")
    axes[1].set_xlim(0, 100)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="outside lower center", ncol=1, fontsize=10, frameon=False
    )
    finish(
        fig,
        6,
        "endmember_coverage",
        "Good classification references need not cover all within-PFT variation",
        [
            END / "tables/coverage_selected.csv",
            END / "tables/coverage_random.csv",
            END / "summary.json",
        ],
        "spectralbridge.mixtures.select_endmembers",
        "Display saved selected values and per-category mean/2.5th/97.5th percentile over the 30 existing matched random controls; ranges are draw spread, not population confidence intervals",
        "The supplied selection improves average nearest-reference agreement while covering typical within-category spectra less closely. This differs from the earlier nested classifier.",
    )
    # F7: Existing numerical certificates and their recorded illustrative example.
    hull = csv(END, "cross_class_hull.csv")
    weights = csv(END, "cross_class_hull_weights.csv")
    members = csv(END, "selected_members.csv")
    example_table = csv(END, "illustrative_ambiguity.csv")
    group = hull.groupby("category").feasible.agg(["sum", "count"]).reindex(CATS)
    metrics["ambiguous"] = claim(
        "ambiguous",
        int(hull.feasible.sum()),
        END / "tables/cross_class_hull.csv",
        "feasible.sum()",
        "Nonnegative sum-one other-category reconstructions verified at supplied-unit RMSE <= 1e-8; broader model family than one-reference/category MESMA",
    )
    assert metrics["ambiguous"] == summary["cross_class_convex_hull_matches"]
    example = int(
        hull[hull.feasible].sort_values(["RMSE", "array_index"]).iloc[0].array_index
    )
    m = members.set_index("array_index")
    target = m.loc[example]
    ww = weights[weights.target_array_index.eq(example)]
    bands = [c for c in members if c.startswith("olioli_undarkened_b")]
    wv = np.array([float(c.split("_wl")[1][:-2]) for c in bands])
    y = target[bands].to_numpy(float)
    alt = ww.weight.to_numpy() @ m.loc[ww.alternative_array_index, bands].to_numpy(
        float
    )
    q = example_table.set_index("category").reindex(CATS)
    computed = np.array(
        [ww.loc[ww.alternative_category.eq(c), "weight"].sum() for c in CATS]
    )
    assert np.allclose(q.alternative_fraction, computed)
    assert np.sqrt(np.mean((y - alt) ** 2)) <= 1e-8
    fig = plt.figure(figsize=(8.6, 6.3), layout="constrained")
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.05])
    ax = fig.add_subplot(grid[0, 0])
    ax.barh(
        range(5), 100 * group["sum"] / group["count"], color=[COLORS[c] for c in CATS]
    )
    ax.set_yticks(range(5), SHORT, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Selected references with an\nother-category reconstruction (%)")
    ax.set_xlim(0, 80)
    for i, row in enumerate(group.itertuples()):
        ax.text(
            100 * row.sum / row.count + 1.5,
            i,
            f"{row.sum}/{row.count}",
            va="center",
            fontsize=9,
        )
    ax = fig.add_subplot(grid[0, 1])
    bottom = np.zeros(2)
    for cat in CATS:
        v = q.loc[cat, ["labelled_target_fraction", "alternative_fraction"]].to_numpy(
            float
        )
        ax.bar([0, 1], v, bottom=bottom, color=COLORS[cat], width=0.6, label=cat)
        bottom += v
    ax.set_xticks(
        [0, 1],
        ["Assigned label\n(not field fractions)", "One alternative\nspectral mixture"],
    )
    ax.set_ylabel("Algebraic fraction")
    ax.set_ylim(0, 1.05)
    ax.set_title("Same spectrum, different category weights", fontsize=11)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="outside lower center", ncol=3, fontsize=9, frameon=False
    )
    ax = fig.add_subplot(grid[1, :])
    ax.plot(wv, y, "o-", color=INK, lw=2, label="Selected spectrum")
    ax.plot(
        wv,
        alt,
        "s--",
        color="#BD4E54",
        lw=1.5,
        ms=5,
        mfc="white",
        label="Other-category reconstruction",
    )
    ax.set_xlabel("Synthetic OLI band center (nm)")
    ax.set_ylabel("Supplied-array units")
    ax.set_title(
        f"Recorded illustration: selected index {example} ({target.category})",
        fontsize=10.5,
    )
    ax.legend(fontsize=10, frameon=False)
    finish(
        fig,
        7,
        "category_ambiguity",
        "A near-perfect spectral match need not identify the category",
        [
            END / "tables/cross_class_hull.csv",
            END / "tables/cross_class_hull_weights.csv",
            END / "tables/selected_members.csv",
            END / "tables/illustrative_ambiguity.csv",
            END / "summary.json",
        ],
        "spectralbridge.mixtures.fcls",
        "Reconstruct the already-saved certificate with its saved reference indices/weights; no optimization. Bar one denotes the assigned one-category interpretation, not known physical truth; up to eight active references and multiple references/category allowed",
        "223 of 603 selected references have verified other-category spectral explanations. This is numerical ambiguity, not an independently observed mixed composition.",
    )
    # F8: Existing mean-fold abundance benchmarks plus equal-candidate control.
    abundance = csv(NEW, "abundance_domain_summary.csv")
    fair = csv(NEW, "same_candidate_ridge.csv")
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 5), layout="constrained", sharex=True)
    names = [
        "Ridge: 120 parents",
        "Ridge: same 15",
        "MESMA: same 15",
        "No-spectrum prior",
    ]
    colors = [BLUE, "#75A9BF", ORANGE, "#8E999E"]
    for ax, kind, title in zip(
        axes, ["plant", "site"], ["New parent identities", "Held-out sites"]
    ):
        a = abundance[
            abundance.kind.eq(kind) & abundance.representation.eq("NEON")
        ].set_index("method")
        f = fair[fair.kind.eq(kind) & fair.representation.eq("NEON")]
        v = [
            float(a.loc["Ridge", "mean"]),
            float(f.RMSE.mean()),
            float(a.loc["MESMA", "mean"]),
            float(a.loc["Training prior", "mean"]),
        ]
        assert np.isclose(v[2], f.MESMA_RMSE.mean())
        ax.barh(range(4), v, color=colors, height=0.63)
        ax.set_yticks(range(4), names, fontsize=10.5)
        ax.invert_yaxis()
        ax.set_xlim(0, 0.46)
        ax.set_xlabel("Fraction RMSE (smaller is better)")
        ax.set_title(title, pad=16)
        ax.grid(axis="x", color="#E6ECEF")
        ax.set_axisbelow(True)
        for y, value in enumerate(v):
            ax.text(
                value + 0.008,
                y,
                f"{value:.3f}",
                va="center",
                fontsize=12,
                weight="bold",
            )
        for method, value in zip(["ridge120", "ridge15", "MESMA15", "prior"], v):
            metrics[f"{kind}_{method}"] = claim(
                f"{kind}_{method}",
                value,
                NEW
                / (
                    "tables/same_candidate_ridge.csv"
                    if method == "ridge15"
                    else "tables/abundance_domain_summary.csv"
                ),
                f"kind={kind}, representation=NEON, method={method}; mean over observed folds",
                "Known synthetic fractions; identical targets within each comparison; different aggregate/units than fixed-library 360-target benchmark",
            )
    yr = abundance[
        abundance.kind.eq("year") & abundance.representation.eq("NEON")
    ].set_index("method")
    for method in ["Ridge", "Training prior"]:
        metrics["year_" + method] = claim(
            "year_" + method,
            float(yr.loc[method, "mean"]),
            NEW / "tables/abundance_domain_summary.csv",
            f"kind=year,method={method},representation=NEON",
            "Global-year holds confound site/year and reuse retrospective labels",
        )
    finish(
        fig,
        8,
        "synthetic_fairness",
        "Synthetic recovery depends on how the library is represented",
        [
            NEW / "tables/abundance_domain_summary.csv",
            NEW / "tables/same_candidate_ridge.csv",
        ],
        "spectralbridge.library_analysis.fit_ridge_fractions; spectralbridge.mixtures.fit_models",
        "Saved mean fold RMSE; same-15 ridge mean computed across saved target rows; no new fitting or error estimates",
        "The larger ridge library improves synthetic fractions in new-parent/held-site tests; the NEON advantage disappears at matched 15-parent capacity. No intrinsic algorithm winner or field-abundance validation follows.",
    )
    # F9: The newest exhaustive search, with its own benchmark/aggregation scope.
    exhaustive = js(EXH, "comparison_summary.json")
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.8), layout="constrained")
    spectral = [
        exhaustive["mean_screened_spectral_RMSE"],
        exhaustive["mean_exhaustive_spectral_RMSE"],
    ]
    fraction = [
        summary["synthetic_RMSE"]["Selected screened MESMA"],
        exhaustive["fraction_RMSE"],
    ]
    for ax, vals, title, label, fmt in zip(
        axes,
        [spectral, fraction],
        ["Spectral reconstruction", "PFT fraction recovery"],
        [
            "Mean spectral RMSE\n(supplied-array units)",
            "Pooled fraction RMSE\n(unit fraction)",
        ],
        [".5f", ".3f"],
    ):
        ax.bar([0, 1], vals, color=[BLUE, ORANGE], width=0.58)
        ax.set_xticks(
            [0, 1], ["Screened\n375 models", "Exhaustive\n16.9 million models"]
        )
        ax.set_ylabel(label)
        ax.set_title(title, pad=16)
        ax.set_ylim(0, max(vals) * 1.27)
        for i, v in enumerate(vals):
            ax.text(
                i,
                v + max(vals) * 0.045,
                format(v, fmt),
                ha="center",
                weight="bold",
                fontsize=13,
            )
    for key in [
        "targets",
        "model_count",
        "fraction_RMSE",
        "mean_screened_spectral_RMSE",
        "mean_exhaustive_spectral_RMSE",
        "lower_fraction_error_targets",
        "higher_fraction_error_targets",
        "unchanged_fraction_error_targets",
    ]:
        metrics[key] = claim(
            "exhaustive_" + key,
            exhaustive[key],
            EXH / "comparison_summary.json",
            key,
            "360 fixed synthetic targets in eight parent-sharing bundles; one to three categories; whole-library reference selection, not selection-blind",
        )
    metrics["screened_fraction_RMSE"] = claim(
        "screened_fraction_RMSE",
        fraction[0],
        END / "summary.json",
        "synthetic_RMSE.Selected screened MESMA",
        "Pooled target-by-category RMSE, not mean-fold RMSE from the earlier abundance benchmark",
    )
    metrics["spectral_reduction_pct"] = claim(
        "spectral_reduction_pct",
        100 * (1 - spectral[1] / spectral[0]),
        EXH / "comparison_summary.json",
        "100*(1-mean_exhaustive_spectral_RMSE/mean_screened_spectral_RMSE)",
        "Descriptive change in mean spectral residual, not fraction-error improvement",
    )
    comparison = next(
        r
        for r in exhaustive["paired_comparisons"]
        if r["comparator"] == "Screened selected (3/category)"
    )
    for key in [
        "conditional_bundle_bootstrap_2_5",
        "conditional_bundle_bootstrap_97_5",
    ]:
        metrics[key] = claim(
            key,
            comparison[key],
            EXH / "comparison_summary.json",
            "paired_comparisons: Screened selected (3/category); " + key,
            "Conditional bootstrap over eight parent bundles; not population coverage or proof of equivalence",
        )
    metrics["oracle"] = claim(
        "oracle",
        summary["synthetic_RMSE"]["Known-parent FCLS oracle"],
        END / "summary.json",
        "synthetic_RMSE.Known-parent FCLS oracle",
        "Synthetic known-parent positive control; not real observed fractions",
    )
    metrics["sparse_prior"] = claim(
        "sparse_prior",
        summary["synthetic_RMSE"]["Sparse design prior"],
        END / "summary.json",
        "synthetic_RMSE.Sparse design prior",
        "Fixed three-category baseline under the synthetic recipe",
    )
    metrics["dense_prior"] = claim(
        "dense_prior",
        summary["synthetic_RMSE"]["Uniform design prior"],
        END / "summary.json",
        "synthetic_RMSE.Uniform design prior",
        "Five-category mean-design baseline; output capacity differs from sparse MESMA",
    )
    finish(
        fig,
        9,
        "exhaustive_search",
        "A better spectral fit does not ensure better fractions",
        [EXH / "comparison_summary.json", END / "summary.json"],
        "spectralbridge.mixtures.fit_models (analysis-only exhaustive extension)",
        "Plot saved screened/exhaustive summary metrics for the same 360 targets; left mean spectral RMSE, right pooled target-by-category fraction RMSE; no candidate search rerun",
        "The exhaustive search reduces the spectral residual by 78.7%, but aggregate fraction RMSE does not improve. Eight-bundle uncertainty includes no aggregate difference; this is not proof of universal failure.",
    )
    # Only result hashes/compact figure metadata are saved; no input arrays are copied.
    (BASE / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    )
    (BASE / "claims.json").write_text(
        json.dumps(CLAIMS, indent=2, sort_keys=True) + "\n"
    )
    manifest = dict(
        generated_date="2026-10-22",
        evidence_through="2026-10-19",
        git_commit=subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        source_scope="Recorded cover_category only; no model refits, raw source-library reads or new inferential tests",
        pft_colors=COLORS,
        figures=FIGURES,
        sources=SOURCES,
        source_builder_sha256=sha(__file__),
        environment=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            pandas=pd.__version__,
            matplotlib=matplotlib.__version__,
        ),
    )
    (BASE / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    rows = []
    for f in FIGURES:
        for source in f["sources"]:
            rows.append(
                dict(
                    report_figure=f["number"],
                    title=f["title"],
                    source_result=source,
                    sha256=SOURCES[source]["sha256"],
                    related_package_function=f["related_package_function"],
                    transform=f["presentation_transform"],
                )
            )
    pd.DataFrame(rows).to_csv(BASE / "figure_source_map.csv", index=False)
    print(
        f"Rendered {len(FIGURES)} presentation figures from {len(SOURCES)} verified result files; {len(CLAIMS)} numeric claim records."
    )


if __name__ == "__main__":
    main()
