"""Export audit master tables and figures from completed immutable experiments."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from spectralbridge.spectral_learning import cluster_bootstrap_accuracy
from spectralbridge.spectral_library_analytics import stable_seed
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.bulk.provenance import write_json_atomic

ROOT = Path("artifacts/plant_spectral_atlas/analytics")
OUT = Path("provenance/spectral-library-analytics/2026-10-14")
OLD = Path("provenance/mesma-readiness/2026-10-14/tables")
REP = ["NEON_full", "NEON_k100", "NEON_k50", "NEON_k20", "NEON_k10", "NEON_k7", "OLI"]
COLORS = ["#186383", "#bb6540", "#5a7751", "#805885", "#b6953b", "#767676", "#223a54"]


def csv(data, name):
    data.to_csv(OUT / "tables" / name, index=False)
    return data


def paired_comparison(
    predictions, first, second, *, column="representation", model="logistic"
):
    """Paired whole-identity BA differences on identical targets only."""
    rows = []
    for (scheme, fold, kind), g in predictions.groupby(["scheme", "fold", "kind"]):
        if kind not in {"plant", "year", "site"}:
            continue
        if column == "representation":
            g = g[g.model.eq(model)]
        else:
            g = g[g.representation.eq("NEON_full")]
        a = g[g[column].eq(first)].sort_values("observation_id")
        b = g[g[column].eq(second)].sort_values("observation_id")
        if not len(a) or not len(b):
            continue
        if (
            a.observation_id.tolist() != b.observation_id.tolist()
            or a.label.tolist() != b.label.tolist()
        ):
            raise ValueError("Unpaired comparison")
        classes = np.asarray(json.loads(a.classes.iloc[0]))
        seed = stable_seed(fold)
        draws = [
            cluster_bootstrap_accuracy(a.label, v, a.GlobalID, classes, seed=seed)
            for v in [a.suggested_label, b.suggested_label]
        ]
        delta = draws[1] - draws[0]

        # Point estimate, not the mean of resampled estimates.
        def ba(frame):
            return (
                frame.assign(correct=frame.label.eq(frame.suggested_label))
                .groupby("label")
                .correct.mean()
                .mean()
            )

        rows.append(
            dict(
                scheme=scheme,
                fold=fold,
                kind=kind,
                reference=first,
                comparison=second,
                axis=column,
                BA_difference=float(ba(b) - ba(a)),
                difference_low=np.quantile(delta, 0.025),
                difference_high=np.quantile(delta, 0.975),
                test_identities=a.GlobalID.nunique(),
                interpretation="paired_conditional_identity_bootstrap_not_multiple_testing_adjusted",
            )
        )
    return pd.DataFrame(rows)


def export_tables():
    manifest = json.loads((ROOT / "learning_manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Full learning experiment is not complete")
    for p, h in manifest["outputs"].items():
        if _file_hash(ROOT / p) != h:
            raise ValueError("Altered learning output: " + p)
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    csv(pd.read_csv(ROOT / "library_summary.csv"), "library_summary.csv")
    effects = csv(
        pd.read_csv("provenance/sensor-pft-transfer/2026-10-14/effect_retention.csv"),
        "biological_contrasts.csv",
    )
    summary = csv(pd.read_csv(ROOT / "summary.csv"), "ml_generalization.csv")
    csv(pd.read_csv(ROOT / "class_metrics.csv"), "class_predictive_performance.csv")
    csv(pd.read_csv(ROOT / "fold_support.csv"), "fold_support.csv")
    csv(pd.read_csv(ROOT / "domains/domain_performance.csv"), "domain_performance.csv")
    csv(pd.read_csv(ROOT / "prototypes.csv"), "prototype_performance.csv")
    csv(pd.read_csv(ROOT / "unknown.csv"), "unknown_material_detection.csv")
    csv(summary[summary.model.eq("logistic")], "spectral_resolution_performance.csv")
    selection = pd.read_csv(ROOT / "selection.csv")
    selection = selection[
        selection.model.eq("logistic")
        & selection.representation.str.startswith("NEON_k")
    ]
    stability = (
        selection.groupby(["scheme", "kind", "representation", "wavelength_nm"])
        .agg(
            selection_frequency=("selected", "mean"),
            outer_folds=("fold", "nunique"),
            mean_F_rank_score=("F_score", "mean"),
        )
        .reset_index()
    )
    csv(stability, "wavelength_selection.csv")
    csv(pd.read_csv(ROOT / "coefficients.csv"), "wavelength_coefficients.csv")
    csv(pd.read_csv(OLD / "class_ambiguity_summary.csv"), "mixture_identifiability.csv")
    recovery = csv(pd.read_csv(OLD / "fraction_errors.csv"), "mixture_recovery.csv")
    selected = csv(
        pd.read_csv(ROOT / "selected_mixture_recovery.csv"),
        "selected_mixture_recovery.csv",
    )
    primary = recovery[
        recovery.method.eq("EAR_MESMA3")
        & recovery.scheme.isin(["inferred_pft", "researcher"])
    ]
    csv(
        pd.concat([primary, selected], ignore_index=True),
        "sensor_resolution_mixture_results.csv",
    )
    detection = pd.read_parquet(OLD / "detection_errors.parquet")
    detection = detection[
        detection.method.eq("EAR_MESMA3")
        & detection.kind.eq("plant")
        & np.isclose(detection.detection_threshold, 0.1)
    ]
    new = pd.read_csv(ROOT / "selected_mixture_detection.csv")
    new = new[new.kind.eq("plant") & np.isclose(new.detection_threshold, 0.1)]
    det = pd.concat([detection, new], ignore_index=True)
    det["detections"] = det.probability * det.N
    det = (
        det.groupby(["scheme", "sensor", "label", "true_fraction"])
        .agg(
            N=("N", "sum"), detections=("detections", "sum"), folds=("fold", "nunique")
        )
        .reset_index()
    )
    det["conditional_detection_frequency"] = det.detections / det.N
    det["D50"] = np.nan
    det["D80"] = np.nan
    det["D95"] = np.nan
    det["population_detection_limit_status"] = (
        "INSUFFICIENT EVIDENCE: repeated trajectories and few independent parent draws"
    )
    csv(det, "detection_limits.csv")
    csv(summary, "uncertainty_calibration.csv")
    csv(pd.read_csv(OLD / "uncertainty.csv"), "mixture_uncertainty.csv")
    preds = pd.read_parquet(ROOT / "predictions.parquet")
    covered = preds[preds.conformal_available]
    groups = ["scheme", "fold", "kind", "representation", "model", "label"]
    coverage = (
        covered.groupby(groups)
        .agg(
            N=("GlobalID", "size"),
            identities=("GlobalID", "nunique"),
            row_coverage=("prediction_set_covered", "mean"),
            mean_set_size=("prediction_set_size", "mean"),
        )
        .reset_index()
    )
    csv(coverage, "class_conformal_coverage.csv")
    paired = pd.concat(
        [
            paired_comparison(preds, "NEON_full", "OLI"),
            paired_comparison(preds, "NEON_full", "NEON_k7"),
            paired_comparison(preds, "NEON_k7", "OLI"),
        ],
        ignore_index=True,
    )
    csv(paired, "paired_sensor_differences.csv")
    modelpairs = pd.concat(
        [
            paired_comparison(preds, "logistic", name, column="model")
            for name in ["PLSDA", "SVM", "forest", "centroid", "majority", "stratified"]
        ],
        ignore_index=True,
    )
    csv(modelpairs, "paired_model_differences.csv")
    for name in [
        "hierarchical_dispersion",
        "material_unique_counts",
        "cover_category_inventory",
        "cross_site_library_coverage",
        "library_size_recovery_summary",
        "endmember_accumulation",
    ]:
        csv(pd.read_csv(OLD / (name + ".csv")), name + ".csv")
    # Explicit dimension judgements, always accompanied by evidence paths.
    performance = pd.read_csv(ROOT / "class_metrics.csv")
    records = []
    for scheme in ["inferred_pft", "researcher"]:
        labels = sorted(
            performance.loc[performance.scheme.eq(scheme), "label"].unique()
        )
        for label in labels:
            sub = performance[
                performance.scheme.eq(scheme)
                & performance.label.eq(label)
                & performance.model.eq("logistic")
                & performance.probability.eq("raw")
                & performance.representation.eq("NEON_full")
            ]
            for dimension in [
                "spectral integrity",
                "biological distinction",
                "plant classification",
                "site transfer",
                "endmember identifiability",
                "fraction recovery",
                "unknown rejection",
                "uncertainty calibration",
                "operational MESMA",
            ]:
                status = "INSUFFICIENT EVIDENCE"
                reason = "No independent ecological abundance/purity truth"
                evidence = "mixture_recovery.csv; MATERIAL_CLASS_AUDIT.md"
                if dimension == "spectral integrity":
                    status = "CONDITIONALLY READY"
                    reason = "Common finite coordinate support validated; absolute library units and source purity unresolved"
                    evidence = "library_summary.csv; DATA_AUDIT.md"
                elif dimension == "biological distinction":
                    status = "CONDITIONALLY READY"
                    reason = "Conditional observational contrasts available; support differs by pair/site/year"
                    evidence = "biological_contrasts.csv"
                elif dimension in {"plant classification", "site transfer"}:
                    part = sub[
                        sub.kind.eq(
                            "plant" if dimension == "plant classification" else "site"
                        )
                    ]
                    status = (
                        "CONDITIONALLY READY" if len(part) else "INSUFFICIENT EVIDENCE"
                    )
                    reason = "Held-out class recall recorded; no universal acceptance threshold or species extrapolation"
                    evidence = "class_predictive_performance.csv; fold_support.csv"
                elif dimension == "endmember identifiability":
                    status = "NOT READY"
                    reason = "Other-class convex reconstructions create ambiguity; no demonstrated unique inversion"
                    evidence = "mixture_identifiability.csv"
                elif dimension == "fraction recovery":
                    status = "NOT READY"
                    reason = "Substantial conditional synthetic fraction error; no independent field validation"
                    evidence = (
                        "mixture_recovery.csv; sensor_resolution_mixture_results.csv"
                    )
                elif dimension == "unknown rejection":
                    reason = "Withheld ecological classes are proxies, not exhaustive physical unknown materials"
                    evidence = "unknown_material_detection.csv"
                elif dimension == "uncertainty calibration":
                    reason = "Held-out calibration assessed; no geographic guarantee or validated abundance intervals"
                    evidence = "uncertainty_calibration.csv; mixture_uncertainty.csv"
                records.append(
                    dict(
                        scheme=scheme,
                        label=label,
                        dimension=dimension,
                        status=status,
                        reason=reason,
                        evidence=evidence,
                    )
                )
    csv(pd.DataFrame(records), "readiness_matrix.csv")
    modelrows = []
    contextual = []
    for relative in manifest["active_checkpoints"]:
        directory = ROOT / relative
        details = json.loads((directory / "fit_details.json").read_text())
        modelrows.append(
            dict(
                **details["context"],
                model=details["model"],
                representation=details["representation"],
                path=str(directory / "model.joblib"),
                sha256=_file_hash(directory / "model.joblib"),
                memberships=str(directory / "memberships.parquet"),
                memberships_sha256=_file_hash(directory / "memberships.parquet"),
                fit_details=str(directory / "fit_details.json"),
            )
        )
        if (
            details["model"] == "logistic"
            and details["representation"] == "NEON_full"
            and details["context"]["kind"] in {"plant", "site", "year"}
        ):
            frame = pd.read_parquet(directory / "memberships.parquet")
            for key, value in details["context"].items():
                frame[key] = value
            contextual.append(frame)
    pd.DataFrame(modelrows).to_csv(OUT / "models/model_index.csv", index=False)
    csv(pd.concat(contextual, ignore_index=True), "primary_learning_memberships.csv")
    write_json_atomic(OUT / "manifests/learning_run.json", manifest)
    return effects, summary


def figure(name, fig, caption):
    fig.tight_layout()
    for ext in ["png", "pdf", "svg"]:
        fig.savefig(
            OUT / "figures" / f"{name}.{ext}",
            dpi=350,
            bbox_inches="tight",
            metadata=(
                {"Date": None}
                if ext == "svg"
                else {"CreationDate": None, "ModDate": None}
                if ext == "pdf"
                else {"Software": "SpectralBridge"}
            ),
        )
    plt.close(fig)
    return dict(
        name=name,
        caption=caption,
        source="tables",
        files=[f"figures/{name}.{e}" for e in ["png", "pdf", "svg"]],
    )


def draw_figures():
    (OUT / "figures").mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "spectralbridge-analytics-20261014",
            "pdf.fonttype": 42,
        }
    )
    figures = []
    summary = pd.read_csv(OUT / "tables/ml_generalization.csv")
    raw = summary[summary.probability.eq("raw")]
    primary = raw[raw.model.eq("logistic")]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for ax, scheme in zip(axes, ["inferred_pft", "researcher"]):
        for rep, color in zip(
            ["NEON_full", "NEON_k7", "OLI"], [COLORS[0], COLORS[1], COLORS[-1]]
        ):
            sub = primary[primary.scheme.eq(scheme) & primary.representation.eq(rep)]
            for x, kind in enumerate(["plant", "flight", "year", "site"]):
                v = sub[sub.kind.eq(kind)].balanced_accuracy
                if len(v):
                    ax.scatter(
                        np.full(len(v), x)
                        + (["NEON_full", "NEON_k7", "OLI"].index(rep) - 1) * 0.14,
                        v,
                        s=16,
                        alpha=0.45,
                        color=color,
                    )
                    ax.plot(
                        x + (["NEON_full", "NEON_k7", "OLI"].index(rep) - 1) * 0.14,
                        v.median(),
                        "_",
                        ms=16,
                        color=color,
                    )
            ax.plot([], [], marker="o", color=color, label=rep.replace("_", " "), ls="")
        ax.set(
            xticks=range(4),
            xticklabels=["Plant", "Flight", "Year", "Site"],
            ylim=(0, 1.02),
            title=scheme.replace("_", " ").title(),
            ylabel="Balanced accuracy (equal class recall)",
        )
        ax.legend(fontsize=8)
    figures.append(
        figure(
            "03_information_ladder",
            fig,
            "Logistic classification by holdout and representation. Dots are eligible folds; bars are medians, not confidence intervals. Support and populations differ across holdout types; this is not a causal loss decomposition.",
        )
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for ax, scheme in zip(axes, ["inferred_pft", "researcher"]):
        sub = primary[primary.scheme.eq(scheme)]
        for kind, color in zip(["plant", "year", "site"], COLORS):
            v = (
                sub[sub.kind.eq(kind)]
                .groupby("representation")
                .balanced_accuracy.median()
            )
            ax.plot(range(7), v.reindex(REP), marker="o", label=kind, color=color)
        ax.set(
            xticks=range(7),
            xticklabels=["360", "100", "50", "20", "10", "7", "OLI 7"],
            ylim=(0, 1.02),
            title=scheme.replace("_", " ").title(),
            xlabel="Training-selected NEON coordinates / OLI channels",
            ylabel="Median fold balanced accuracy",
        )
        ax.legend()
    figures.append(
        figure(
            "04_resolution_curve",
            fig,
            "Training-confined coordinate selection; full NEON and OLI are distinct response representations. Points summarize different eligible folds; inspect paired differences for conditional intervals.",
        )
    )
    stability = pd.read_csv(OUT / "tables/wavelength_selection.csv")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 5.6), sharex=True)
    for ax, scheme in zip(axes, ["inferred_pft", "researcher"]):
        for kind, color in zip(["plant", "year", "site"], COLORS):
            g = stability[
                stability.scheme.eq(scheme)
                & stability.kind.eq(kind)
                & stability.representation.eq("NEON_k20")
            ]
            ax.scatter(
                g.wavelength_nm,
                g.selection_frequency,
                s=8,
                label=kind,
                color=color,
                alpha=0.7,
            )
        ax.set(
            ylabel="Selection frequency",
            ylim=(-0.03, 1.05),
            title=scheme.replace("_", " ").title(),
        )
        ax.axvspan(1340, 1450, color=".9")
        ax.axvspan(1790, 2000, color=".9")
        ax.legend(loc="upper right", fontsize=8)
    axes[-1].set_xlabel("Wavelength (nm); atmospheric gaps remain empty")
    figures.append(
        figure(
            "05_wavelength_stability",
            fig,
            "Frequency of selection among twenty proper-training F-ranked coordinates. Ranking is exploratory; correlated adjacent coordinates can substitute. Site stability uses only the observed holdout sites.",
        )
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), sharey=True)
    for ax, scheme in zip(axes, ["inferred_pft", "researcher"]):
        sub = raw[
            raw.scheme.eq(scheme)
            & raw.kind.eq("plant")
            & raw.representation.eq("NEON_full")
        ]
        means = (
            sub.groupby("model")
            .balanced_accuracy.mean()
            .reindex(
                [
                    "majority",
                    "stratified",
                    "centroid",
                    "logistic",
                    "PLSDA",
                    "SVM",
                    "forest",
                ]
            )
        )
        ax.bar(range(len(means)), means, color=COLORS)
        for i, name in enumerate(means.index):
            values = sub[sub.model.eq(name)].balanced_accuracy
            ax.scatter(np.full(len(values), i), values, color="black", s=15)
        ax.set(
            xticks=range(len(means)),
            xticklabels=means.index,
            ylim=(0, 1.02),
            title=scheme.replace("_", " ").title(),
            ylabel="Plant-held-out balanced accuracy",
        )
        ax.tick_params(axis="x", rotation=35)
    figures.append(
        figure(
            "06_classical_models",
            fig,
            "All predeclared models; bars are means of plant folds, dots individual folds. No model was selected using these test scores.",
        )
    )
    prototypes = pd.read_csv(OUT / "tables/prototype_performance.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for ax, scheme in zip(axes, ["inferred_pft", "researcher"]):
        for method, color in zip(["cluster_medoid", "diversity"], COLORS):
            sub = prototypes[
                prototypes.scheme.eq(scheme)
                & prototypes.kind.eq("plant")
                & prototypes.representation.eq("NEON_full")
                & prototypes.method.eq(method)
                & prototypes.status.eq("evaluated")
            ]
            g = sub.groupby("prototypes_per_class").balanced_accuracy.mean()
            ax.plot(
                g.index,
                g.values,
                marker="o",
                label=method.replace("_", " "),
                color=color,
            )
        for method, color in zip(["mean", "median", "medoid"], COLORS[2:]):
            v = prototypes[
                prototypes.scheme.eq(scheme)
                & prototypes.kind.eq("plant")
                & prototypes.representation.eq("NEON_full")
                & prototypes.method.eq(method)
            ].balanced_accuracy.mean()
            ax.axhline(v, color=color, ls="--", label=method + " (one)")
        ax.set(
            xscale="log",
            xlabel="Prototypes per class",
            ylabel="Mean plant-fold balanced accuracy",
            ylim=(0, 1.02),
            title=scheme.replace("_", " ").title(),
        )
        ax.legend(fontsize=7)
    figures.append(
        figure(
            "07_prototype_coverage",
            fig,
            "Proper-training representatives in training-standardized coordinate space. Unsupported sizes are omitted. Mean/median are synthetic centers; medoids/diversity are observed plants. More representatives are not a purity or mixture-identifiability certificate.",
        )
    )
    mixtures = pd.read_csv(OUT / "tables/sensor_resolution_mixture_results.csv")
    detection = pd.read_csv(OUT / "tables/detection_limits.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    for scheme, color in zip(["inferred_pft", "researcher"], COLORS):
        g = (
            mixtures[mixtures.scheme.eq(scheme) & mixtures.kind.eq("plant")]
            .groupby("sensor")
            .fraction_RMSE.mean()
        )
        axes[0].plot(
            range(7),
            g.reindex(
                [
                    "NEON",
                    "NEON_k100",
                    "NEON_k50",
                    "NEON_k20",
                    "NEON_k10",
                    "NEON_k7",
                    "OLI",
                ]
            ),
            marker="o",
            label=scheme.replace("_", " "),
            color=color,
        )
    axes[0].set(
        xticks=range(7),
        xticklabels=["360", "100", "50", "20", "10", "7", "OLI 7"],
        ylabel="Mean class/fold fraction RMSE",
        xlabel="Representation",
    )
    axes[0].legend(fontsize=8)
    for label, color in zip(
        sorted(detection[detection.scheme.eq("inferred_pft")].label.unique()), COLORS
    ):
        g = detection[
            detection.scheme.eq("inferred_pft")
            & detection.sensor.eq("NEON")
            & detection.label.eq(label)
        ].sort_values("true_fraction")
        axes[1].plot(
            g.true_fraction,
            g.conditional_detection_frequency,
            marker=".",
            label=label,
            color=color,
        )
    axes[1].set(
        xlabel="Known synthetic true fraction",
        ylabel="Frequency estimated fraction ≥ 0.10",
        ylim=(0, 1.02),
    )
    axes[1].legend(fontsize=8, ncol=2)
    figures.append(
        figure(
            "08_mixtures_detection",
            fig,
            "Identical saved parents, fractions and EAR candidate identities. Left averages class/fold errors equally. Right frequencies condition on a few repeated parent trajectories; they are not population detection limits. Positive detection at zero fraction is false detection.",
        )
    )
    unknown = pd.read_csv(OUT / "tables/unknown_material_detection.csv")
    unknown = unknown[
        unknown.status.eq("evaluated") & unknown.representation.eq("NEON_full")
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.7))
    detectors = [
        "nearest_angle_deg",
        "nearest_RMSE",
        "PCA_radius",
        "PCA_residual",
        "one_minus_confidence",
        "empty_conformal_set",
    ]
    for j, (scheme, color) in enumerate(zip(["inferred_pft", "researcher"], COLORS)):
        g = (
            unknown[unknown.scheme.eq(scheme)]
            .groupby("detector")[["known_false_rejection", "unknown_recall"]]
            .mean()
            .reindex(detectors)
        )
        positions = np.arange(len(detectors)) + (j - 0.5) * 0.22
        axes[0].scatter(
            g.unknown_recall,
            positions,
            color=color,
            marker="o",
            label=scheme.replace("_", " "),
        )
        axes[0].scatter(g.known_false_rejection, positions, color=color, marker="x")
    axes[0].set(
        xlabel="Rate",
        yticks=range(len(detectors)),
        yticklabels=[
            "Angle",
            "Nearest distance",
            "PCA radius",
            "PCA residual",
            "Confidence",
            "Empty set",
        ],
        xlim=(-0.02, 1.02),
        title="● Unknown recall     × Known rejection",
    )
    axes[0].tick_params(axis="y", labelsize=8)
    axes[0].legend(fontsize=8, loc="lower right")
    for kind, color in zip(["plant", "site", "year", "flight"], COLORS):
        g = primary[
            primary.scheme.eq("inferred_pft")
            & primary.representation.eq("NEON_full")
            & primary.kind.eq(kind)
            & primary.probability.eq("raw")
        ]
        axes[1].scatter(
            g.mean_set_size,
            g.identity_joint_coverage,
            label=kind,
            color=color,
            s=20,
            alpha=0.6,
        )
    axes[1].axhline(0.9, color=".3", ls="--", lw=1)
    axes[1].set(
        xlabel="Mean conformal set size",
        ylabel="Identity joint empirical coverage",
        ylim=(0, 1.03),
    )
    axes[1].legend(fontsize=8)
    figures.append(
        figure(
            "09_unknowns_uncertainty",
            fig,
            "Left: mean withheld-class diagnostics at independent known-calibration thresholds; class prevalence changes precision and AP. Right: raw-score group-conformal empirical coverage versus set size, not a domain-shift guarantee.",
        )
    )
    # Actual class-specific ambiguity, not a generic conceptual illustration.
    ambiguity = pd.read_csv(OUT / "tables/mixture_identifiability.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.1))
    for ax, scheme in zip(axes, ["inferred_pft", "researcher"]):
        g = ambiguity[ambiguity.scheme.eq(scheme) & ambiguity.kind.eq("plant")].pivot(
            index="label", columns="sensor", values="ambiguity_rate"
        )
        g.plot.bar(ax=ax, color=[COLORS[0], COLORS[-1]], rot=25)
        ax.set(
            title=scheme.replace("_", " ").title(),
            ylabel="Ambiguous held-out record fraction",
            ylim=(0, 1.03),
            xlabel="",
        )
        ax.legend(fontsize=8)
    figures.append(
        figure(
            "10_mixture_ambiguity",
            fig,
            "A wrong-class mixture reconstructs the held-out pure observation within the declared 0.01 tolerance of its own-class fit or better. Repeated held-out records are not independent new plants.",
        )
    )
    write_json_atomic(OUT / "manifests/figures.json", dict(figures=figures))
    return figures


if __name__ == "__main__":
    export_tables()
    draw_figures()
