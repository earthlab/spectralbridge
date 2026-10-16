"""Training-only budget choice, identity intervals and raw composition diagnostics."""

import json
import numpy as np
import pandas as pd
from common import BASE, CACHE, REPO, save, seed
from spectralbridge.researcher_information import (
    RESEARCHER_CATEGORIES,
    identity_weights,
)


def main():
    choices = []
    for folder in sorted((CACHE / "classification").iterdir()):
        tune = pd.read_csv(folder / "inner_tuning.csv")
        tune = tune[~tune.budget.eq("OLI")]
        best = tune.groupby(["budget", "C"]).BA.mean().reset_index()
        best = best.loc[best.groupby("budget").BA.idxmax()]
        threshold = best.BA.max() - 0.02
        eligible = best[best.BA >= threshold].copy()
        eligible["number"] = eligible.budget.astype(int)
        chosen = eligible.sort_values("number").iloc[0]
        outer = pd.read_csv(folder / "metrics.csv")
        row = outer[outer.budget.eq(str(chosen.budget))].iloc[0]
        choices.append(
            dict(
                fold=folder.name,
                kind=row.kind,
                selected_budget=int(chosen.budget),
                C=chosen.C,
                inner_BA=chosen.BA,
                inner_best_BA=best.BA.max(),
                outer_BA=row.balanced_accuracy,
                policy="smallest budget within .02 of best inner-only BA; never outer-selected",
            )
        )
    save(pd.DataFrame(choices), "inner_selected_parsimonious_budget.csv")
    predictions = pd.read_parquet(BASE / "tables/classification_predictions.parquet")
    intervals = []
    for (fold, kind, rep), g in predictions.groupby(["fold", "kind", "representation"]):
        ids = g.GlobalID.to_numpy()
        unique, group = np.unique(ids, return_inverse=True)
        true = g.truth.to_numpy()
        pred = g.predicted.to_numpy()
        w = identity_weights(ids)
        labels = (
            g.drop_duplicates("GlobalID")
            .set_index("GlobalID")
            .loc[unique]
            .truth.to_numpy()
        )
        rng = np.random.default_rng(seed(fold + rep))
        multiplicity = np.zeros((499, len(unique)), int)
        for c in np.unique(labels):
            members = np.flatnonzero(labels == c)
            draws = rng.choice(members, (499, len(members)), replace=True)
            for k in range(499):
                multiplicity[k] += np.bincount(draws[k], minlength=len(unique))
        for c in RESEARCHER_CATEGORIES:
            a, b = true == c, pred == c
            cells = np.zeros((len(unique), 4))
            np.add.at(
                cells,
                group,
                w[:, None] * np.column_stack([a & b, a & ~b, ~a & b, ~a & ~b]),
            )
            tp, fn, fp, tn = (multiplicity @ cells).T
            rates = {
                "recall": tp / (tp + fn),
                "specificity": tn / (tn + fp),
                "FPR": fp / (tn + fp),
                "FNR": fn / (tp + fn),
                "precision": np.divide(
                    tp, tp + fp, out=np.full_like(tp, np.nan), where=tp + fp > 0
                ),
            }
            row = dict(fold=fold, kind=kind, representation=rep, researcher_category=c)
            for metric, v in rates.items():
                row[metric + "_low"], row[metric + "_high"] = np.nanquantile(
                    v, [0.025, 0.975]
                )
            intervals.append(row)
    save(pd.DataFrame(intervals), "class_rate_identity_intervals.csv")
    raw = []
    for r in pd.read_csv(BASE / "tables/abundance_case_index.csv").itertuples():
        if r.method in ["FCLS", "MESMA", "Training prior"]:
            continue
        folder = (REPO / r.predictions).parent
        with np.load(folder / (r.target + ".npz")) as stored:
            p = stored["raw"]
            final = stored["pred"]
        truth = pd.read_parquet(REPO / r.truth)[list(RESEARCHER_CATEGORIES)].to_numpy()
        raw.append(
            dict(
                fold=r.fold,
                kind=r.kind,
                target=r.target,
                method=r.method,
                representation=r.representation,
                raw_fraction_RMSE=np.sqrt(np.mean((p - truth) ** 2)),
                projected_fraction_RMSE=np.sqrt(np.mean((final - truth) ** 2)),
                raw_negative_rows=np.mean((p < 0).any(1)),
                raw_sum_one_violation=np.mean(~np.isclose(p.sum(1), 1)),
            )
        )
    save(pd.DataFrame(raw), "raw_prediction_constraint_diagnostics.csv")
    config = {
        "label_field": "cover_category",
        "classes": list(RESEARCHER_CATEGORIES),
        "seed": 20261015,
        "outer_identity_fold_seed_reused": 20261014,
        "classification_budgets": [1, 2, 3, 5, 7, 10, 20, 50, 100, 360, "OLI7"],
        "proper_parent_bundles": 24,
        "tuning_parent_bundles": 8,
        "maximum_test_parent_bundles": 12,
        "detection_fraction_cutoff": 0.10,
        "ambiguity_metric_tolerance": 0.01,
        "paired_bundle_bootstraps": 499,
        "field_fraction_truth_available": False,
        "continuum_normalization": "not justified by current purity/continuum metadata",
        "neural_network": "not justified initially by only120 independent proper-training parents; not fitted",
        "log_ratio_fractions": "not used; exact zeros would require arbitrary replacement",
        "source_OLI_labels": "Rounded export coordinates accepted by existing validator; overlays use exact packaged centers/FWHM",
        "parsimonious_budget_policy": "training-only synthesis policy within2percentage points of best inner BA; no outer choice",
    }
    (BASE / "configuration.json").write_text(json.dumps(config, indent=2) + "\n")
    print(
        "Saved training-only budget decisions, class identity intervals and composition diagnostics."
    )


if __name__ == "__main__":
    main()
