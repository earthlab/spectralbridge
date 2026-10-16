"""Five table-backed synthesis figures, replacing further exploratory panels."""

from pathlib import Path
import json
import re
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from spectralbridge.spectral_closure import closure_labels

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
PRIOR = REPO / "provenance/spectral-library-analytics/2026-10-14/tables"
LEVELS = [
    "species_level",
    "researcher_level",
    "narrow_pft",
    "broad_pft",
    "coarse_cover",
]
NAMES = [
    "Species",
    "Researcher class",
    "Narrow woody PFT",
    "Broad leaf habit",
    "Coarse cover proxy",
]
COLORS = ["#26708b", "#c47746", "#4f8060", "#8d628c", "#8998a0"]
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "svg.hashsalt": "spectralbridge-closure-20261015",
        "pdf.fonttype": 42,
    }
)
manifest = []


def read(name):
    return pd.read_csv(BASE / "tables" / name)


def save(fig, name, caption, tables, *, bottom=0):
    fig.tight_layout(rect=(0, bottom, 1, 1))
    for ext in ["png", "pdf", "svg"]:
        metadata = (
            {"Date": None}
            if ext == "svg"
            else {"CreationDate": None, "ModDate": None}
            if ext == "pdf"
            else {"Software": "SpectralBridge"}
        )
        fig.savefig(
            BASE / "figures" / f"{name}.{ext}",
            dpi=350,
            bbox_inches="tight",
            metadata=metadata,
        )
    plt.close(fig)
    manifest.append(
        dict(
            name=name,
            caption=caption,
            source_tables=tables,
            files=[
                str((BASE / "figures" / f"{name}.{ext}").relative_to(REPO))
                for ext in ["png", "pdf", "svg"]
            ],
        )
    )


def run():
    index = closure_labels(
        pd.read_parquet(
            REPO
            / "artifacts/plant_spectral_atlas/closure_20261015/canonical_analysis_index.parquet"
        )
    )
    index[
        [
            "observation_id",
            "GlobalID",
            "site",
            "year",
            "species_level",
            "researcher_level",
            "narrow_pft",
            "broad_pft",
            "coarse_cover",
            "flight_history",
            "native_grid_ids",
        ]
    ].to_csv(BASE / "tables/label_hierarchy.csv", index=False)
    exposures = []
    for row in index.itertuples(index=False):
        products = set(json.loads(item)[0] for item in json.loads(row.flight_history))
        for product in sorted(products):
            match = re.search(r"_(20[0-9]{6})(?:_|\.)", product)
            exposures.append(
                dict(
                    GlobalID=row.GlobalID,
                    site=row.site,
                    year=row.year,
                    product=product,
                    source_date=match.group(1) if match else "unresolved",
                )
            )
    exposure = pd.DataFrame(exposures).drop_duplicates()
    acquisition = (
        exposure.groupby(["site", "year", "source_date"])
        .agg(
            unique_polygon_ids=("GlobalID", "nunique"),
            source_products=("product", "nunique"),
        )
        .reset_index()
    )
    acquisition["interpretation"] = (
        "source-date grouping; independent flight-event identity is not established"
    )
    acquisition.to_csv(BASE / "tables/acquisition_date_support.csv", index=False)
    support = read("observational_support.csv")
    fig, axes = plt.subplots(
        1, 3, figsize=(13, 4.3), gridspec_kw={"width_ratios": [1.2, 1, 1]}
    )
    g = support[support.level.eq("researcher_level")].copy()
    g["cohort"] = g.site + " " + g.year.astype(str)
    heat = g.pivot(index="label", columns="cohort", values="identities").fillna(0)
    axes[0].imshow(heat, aspect="auto", cmap="Blues")
    axes[0].set(
        xticks=range(len(heat.columns)),
        xticklabels=heat.columns,
        yticks=range(len(heat)),
        yticklabels=heat.index,
        title="A  Researcher-label support",
    )
    axes[0].tick_params(axis="x", rotation=30, labelsize=9)
    axes[0].tick_params(axis="y", labelsize=9)
    for i in range(len(heat)):
        for j in range(len(heat.columns)):
            axes[0].text(
                j,
                i,
                str(int(heat.iloc[i, j])),
                ha="center",
                va="center",
                fontsize=9,
                color="white"
                if heat.iloc[i, j] > heat.to_numpy().max() * 0.5
                else "black",
            )
    sampling = read("sampling_weight_effect.csv")
    x = np.arange(len(sampling))
    axes[1].bar(
        x - 0.17,
        sampling.annual_row_share * 100,
        0.34,
        label="Annual-row share",
        color=COLORS[0],
    )
    axes[1].bar(
        x + 0.17,
        sampling.identity_share * 100,
        0.34,
        label="Identity share",
        color=COLORS[1],
    )
    axes[1].set(
        xticks=x,
        xticklabels=sampling.site,
        ylabel="Share of library (%)",
        title="B  Repeat sampling changes weights",
    )
    axes[1].legend(fontsize=8)
    unit = read("identity_sampling.csv").groupby("years").GlobalID.count()
    axes[2].bar(
        ["One year", "Both years"], unit.reindex([1, 2]), color=[COLORS[4], COLORS[2]]
    )
    for i, v in enumerate(unit.reindex([1, 2])):
        axes[2].text(i, v + 30, str(v), ha="center")
    axes[2].set(
        ylabel="Unique polygon identities",
        ylim=(0, unit.max() * 1.15),
        title="C  Repeats are polygons, not new plants",
    )
    save(
        fig,
        "F1_library_structure",
        "A: identity counts within cohorts; across-year repeats are not additive biological replication. B: equal annual-row weighting differs from equal identity weighting. C: all repeated-year identities are at NIWO. GlobalID denotes a polygon, not verified biological-individual purity.",
        [
            "observational_support.csv",
            "sampling_weight_effect.csv",
            "identity_sampling.csv",
        ],
    )
    partition = read("paired_temporal_partition.csv")
    paired = read("paired_temporal_recognition.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    components = [
        "class_fraction",
        "polygon_within_class_fraction",
        "year_fraction",
        "class_by_year_fraction",
        "residual_change_fraction",
    ]
    labels = [
        "Class",
        "Polygon within class",
        "Common year",
        "Class x year",
        "Residual change",
    ]
    sub = (
        partition[partition.sensor.eq("NEON") & partition["mode"].eq("stored")]
        .set_index("level")
        .reindex(LEVELS)
    )
    bottom = np.zeros(5)
    for column, label, color in zip(components, labels, COLORS):
        axes[0, 0].barh(range(5), sub[column], left=bottom, label=label, color=color)
        bottom += sub[column].to_numpy()
    axes[0, 0].set(
        yticks=range(5),
        yticklabels=NAMES,
        xlabel="Fraction of paired-panel total SS",
        title="A  Descriptive temporal partition",
    )
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.005),
        ncol=3,
        fontsize=8,
    )
    for j, mode in enumerate(["stored", "shape"]):
        s = (
            partition[partition.sensor.eq("NEON") & partition["mode"].eq(mode)]
            .set_index("level")
            .reindex(LEVELS)
        )
        x = np.arange(5) + (j - 0.5) * 0.18
        axes[0, 1].errorbar(
            x,
            s.change_to_class_ratio,
            yerr=[
                s.change_to_class_ratio - s.change_to_class_ratio_low,
                s.change_to_class_ratio_high - s.change_to_class_ratio,
            ],
            fmt="o",
            capsize=2,
            color=COLORS[j],
            label=mode,
        )
    axes[0, 1].axhline(1, color=".4", ls="--", lw=1)
    axes[0, 1].set(
        xticks=range(5),
        xticklabels=NAMES,
        ylabel="Paired change / class-centroid separation",
        title="B  Change can approach class separation",
    )
    axes[0, 1].tick_params(axis="x", rotation=25, labelsize=8)
    axes[0, 1].legend(fontsize=8)
    for ax, training in zip(axes[1], [2020, 2023]):
        for level, name, color in zip(LEVELS, NAMES, COLORS):
            g = (
                paired[
                    paired.scheme.eq(level)
                    & paired.training_year.eq(training)
                    & paired.representation.eq("NEON_full")
                ]
                .groupby("test_year")
                .balanced_accuracy.mean()
            )
            ax.plot(g.index, g, marker="o", label=name, color=color)
        ax.set(
            xticks=[2020, 2023],
            ylim=(0, 1.02),
            ylabel="Mean fold balanced accuracy",
            title=f"{'C' if training == 2020 else 'D'}  Train other identities in {training}",
            xlabel="Year of the same unseen target polygons",
        )
    axes[1, 1].legend(fontsize=7, loc="lower right")
    save(
        fig,
        "F2_temporal_resolution",
        "A: exact balanced two-year SS, not causal random-effect variances. B: equal-class-centroid distance and temporal change differ from weighted SS; intervals resample paired identities. Populations/classes differ across levels. C-D: same unseen identities in both years; lines average three folds. Neither year is trained using test identities. Reference labels are reused 2023/2024 annotations, not independent annual field verification.",
        [
            "paired_temporal_partition.csv",
            "paired_temporal_recognition.csv",
            "paired_temporal_accuracy_change.csv",
        ],
        bottom=0.10,
    )
    summary = read("biological_generalization.csv")
    raw = summary[
        summary.probability.eq("raw")
        & summary.experiment.eq("hierarchy")
        & summary["mode"].eq("stored")
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, rep, title in [
        (axes[0, 0], "NEON_full", "A  Common NEON"),
        (axes[0, 1], "OLI", "B  Synthetic OLI"),
    ]:
        heat = (
            raw[raw.representation.eq(rep)]
            .pivot_table(
                index="scheme",
                columns="kind",
                values="balanced_accuracy",
                aggfunc="mean",
            )
            .reindex(index=LEVELS, columns=["plant", "year", "site"])
        )
        ax.imshow(heat, vmin=0, vmax=1, cmap="YlGnBu", aspect="auto")
        ax.set(
            xticks=range(3),
            xticklabels=["New polygon", "Held year", "Held site"],
            yticks=range(5),
            yticklabels=NAMES,
            title=title,
        )
        for i in range(5):
            for j in range(3):
                ax.text(
                    j,
                    i,
                    f"{heat.iloc[i, j]:.2f}",
                    ha="center",
                    va="center",
                    color="white" if heat.iloc[i, j] > 0.65 else "black",
                )
    sens = summary[
        summary.probability.eq("raw")
        & summary.kind.eq("site")
        & summary.representation.eq("NEON_full")
    ]
    for j, (mode, color) in enumerate(zip(["stored", "shape", "amplitude"], COLORS)):
        if mode == "stored":
            g = sens[sens.experiment.eq("hierarchy") & sens["mode"].eq(mode)]
        else:
            g = sens[sens.experiment.eq("sensitivity") & sens["mode"].eq(mode)]
        v = (
            g.groupby("scheme")
            .balanced_accuracy.mean()
            .reindex(["researcher_level", "narrow_pft", "broad_pft"])
        )
        axes[1, 0].bar(np.arange(3) + (j - 1) * 0.23, v, 0.23, label=mode, color=color)
    axes[1, 0].set(
        xticks=range(3),
        xticklabels=["Researcher class", "Narrow PFT", "Broad leaf habit"],
        ylim=(0, 1.02),
        ylabel="Mean held-site balanced accuracy",
        title="C  Shape survives amplitude removal",
    )
    axes[1, 0].legend(fontsize=8)
    selection = pd.read_csv(PRIOR / "wavelength_selection.csv")
    for kind, color in zip(["plant", "year", "site"], COLORS):
        s = selection[
            selection.scheme.eq("inferred_pft")
            & selection.kind.eq(kind)
            & selection.representation.eq("NEON_k20")
        ]
        axes[1, 1].scatter(
            s.wavelength_nm, s.selection_frequency, s=7, color=color, label=kind
        )
    axes[1, 1].axvspan(1340, 1450, color=".92")
    axes[1, 1].axvspan(1790, 2000, color=".92")
    axes[1, 1].set(
        xlabel="Wavelength (nm)",
        ylabel="Training-selection frequency",
        title="D  Recurrent SWIR, not a universal optimum",
    )
    axes[1, 1].legend(fontsize=8)
    save(
        fig,
        "F3_generalization_shape_sensor",
        "A-B: descriptive mean fold scores on supported closed-set targets, with different class counts/populations and chance references. Global year holdouts confound site composition; paired NIWO inference is Figure 2. C: same held-site targets and training memberships; shape normalization is analytical only. D: reused twenty-coordinate training-only selection.",
        [
            "biological_generalization.csv",
            "closed_set_coverage.csv",
            "brightness_sampling_sensitivity.csv",
            "P126/wavelength_selection.csv",
        ],
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    amb = pd.read_csv(PRIOR / "mixture_identifiability.csv")
    g = amb[amb.scheme.eq("inferred_pft") & amb.kind.eq("plant")].pivot(
        index="label", columns="sensor", values="ambiguity_rate"
    )
    g.plot.bar(ax=axes[0, 0], color=COLORS[:2], rot=0)
    axes[0, 0].set(
        ylim=(0, 1.03),
        ylabel="Conditional ambiguous record fraction",
        xlabel="",
        title="A  Pure observations admit wrong mixtures",
    )
    recovery = pd.read_csv(PRIOR / "sensor_resolution_mixture_results.csv")
    sensors = [
        "NEON",
        "NEON_k100",
        "NEON_k50",
        "NEON_k20",
        "NEON_k10",
        "NEON_k7",
        "OLI",
    ]
    for scheme, color in zip(["inferred_pft", "researcher"], COLORS):
        g = (
            recovery[recovery.scheme.eq(scheme) & recovery.kind.eq("plant")]
            .groupby("sensor")
            .fraction_RMSE.mean()
            .reindex(sensors)
        )
        axes[0, 1].plot(
            range(7), g, marker="o", label=scheme.replace("_", " "), color=color
        )
    axes[0, 1].set(
        xticks=range(7),
        xticklabels=["360", "100", "50", "20", "10", "7", "OLI 7"],
        ylabel="Mean class/fold fraction RMSE",
        xlabel="Representation",
        title="B  More fit flexibility does not validate fractions",
    )
    axes[0, 1].legend(fontsize=8)
    det = pd.read_csv(PRIOR / "detection_limits.csv")
    for label, color in zip(
        sorted(g for g in det[det.scheme.eq("inferred_pft")].label.unique()), COLORS
    ):
        d = det[
            det.scheme.eq("inferred_pft") & det.sensor.eq("NEON") & det.label.eq(label)
        ].sort_values("true_fraction")
        axes[1, 0].plot(
            d.true_fraction,
            d.conditional_detection_frequency,
            marker=".",
            label=label,
            color=color,
        )
    axes[1, 0].set(
        ylim=(0, 1.03),
        xlabel="Known synthetic fraction",
        ylabel="Frequency estimate reaches 0.10",
        title="C  Conditional detection, not field detection limit",
    )
    axes[1, 0].legend(fontsize=8, ncol=2)
    unknown = pd.read_csv(PRIOR / "unknown_material_detection.csv")
    unknown = unknown[
        unknown.status.eq("evaluated") & unknown.representation.eq("NEON_full")
    ]
    detectors = [
        "nearest_angle_deg",
        "nearest_RMSE",
        "PCA_radius",
        "PCA_residual",
        "one_minus_confidence",
        "empty_conformal_set",
    ]
    for j, (scheme, color) in enumerate(zip(["inferred_pft", "researcher"], COLORS)):
        d = (
            unknown[unknown.scheme.eq(scheme)]
            .groupby("detector")[["known_false_rejection", "unknown_recall"]]
            .mean()
            .reindex(detectors)
        )
        y = np.arange(6) + (j - 0.5) * 0.2
        axes[1, 1].scatter(
            d.unknown_recall, y, color=color, label=scheme.replace("_", " ")
        )
        axes[1, 1].scatter(d.known_false_rejection, y, color=color, marker="x")
    axes[1, 1].set(
        yticks=range(6),
        yticklabels=[
            "Angle",
            "Distance",
            "PCA radius",
            "PCA residual",
            "Confidence",
            "Empty set",
        ],
        xlim=(-0.02, 1.02),
        xlabel="Rate: circles unknown recall; crosses known rejection",
        title="D  Unknown classes often remain accepted",
    )
    axes[1, 1].legend(fontsize=8, loc="lower right")
    save(
        fig,
        "F4_mixture_limits",
        "All numerical experiments reused from the verified prior audit. A: ambiguity at the declared 0.01 training-normalized analytical metric tolerance, not an absolute reflectance threshold. B: exact saved parent/fraction/endmember comparisons. C: repeated trajectories are dependent, and positive detection at zero is false detection. D: unknown labels are ecological proxies; thresholds use known calibration only. No independent field abundance truth is present.",
        [
            "P126/mixture_identifiability.csv",
            "P126/sensor_resolution_mixture_results.csv",
            "P126/detection_limits.csv",
            "P126/unknown_material_detection.csv",
        ],
    )
    matrix = pd.read_csv(BASE / "tables/FINAL_READINESS_MATRIX.csv")
    levels = [
        "not ready",
        "exploratory",
        "scientifically promising",
        "validated for constrained use",
        "operationally validated",
    ]
    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    values = np.array([levels.index(s) for s in matrix.readiness])[:, None]
    cmap = ListedColormap(["#b85e52", "#d8aa5e", "#7aab91", "#4d839d", "#294f6a"])
    ax.imshow(values, aspect="auto", cmap=cmap, vmin=-0.5, vmax=4.5)
    ax.set(
        yticks=range(len(matrix)),
        yticklabels=matrix.use,
        xticks=[],
        title="Use-specific readiness - no composite score",
    )
    for i, row in enumerate(matrix.itertuples(index=False)):
        ax.text(
            0,
            i,
            row.readiness,
            ha="center",
            va="center",
            fontsize=10,
            color="white"
            if row.readiness in ["not ready", "validated for constrained use"]
            else "black",
        )
    ax.legend(
        handles=[
            Patch(facecolor=cmap(i), label=label) for i, label in enumerate(levels)
        ],
        bbox_to_anchor=(1.03, 1),
        loc="upper left",
        fontsize=9,
    )
    save(
        fig,
        "F5_final_decisions",
        "Readiness categories follow the explicit DESIGN review scenarios and actual validation scope, not an averaged score. Classification is conditional on supported source-label populations. The real-Landsat constrained category applies only to one radiometric/spatial scene comparison. No use is operationally validated.",
        ["FINAL_READINESS_MATRIX.csv", "DESIGN.md"],
    )
    (BASE / "FIGURE_CAPTIONS.md").write_text(
        "# Five final synthesis figures\n\n"
        + "\n\n".join(
            "## "
            + f["name"]
            + "\n\n"
            + f["caption"]
            + "\n\nSource tables: "
            + ", ".join(f["source_tables"])
            for f in manifest
        )
        + "\n"
    )
    (BASE / "manifests/figures.json").write_text(
        json.dumps(dict(figures=manifest), indent=2) + "\n"
    )


if __name__ == "__main__":
    run()
