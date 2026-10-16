"""Training-mean fraction null control: quantify improvement beyond mixture prior."""

import numpy as np
import pandas as pd
from common import BASE, REPO, CACHE, load, save
from run_abundance import experiments, context, CLASSES
from spectralbridge.researcher_information import fraction_metrics


def main():
    t, arrays, waves, _ = load()
    paths = [
        "abundance_model_comparison.parquet",
        "abundance_by_true_fraction.csv",
        "abundance_bundle_scores.parquet",
        "abundance_by_ambiguity.csv",
        "abundance_case_index.csv",
    ]
    old = {
        p: (
            pd.read_parquet(BASE / "tables" / p)
            if p.endswith("parquet")
            else pd.read_csv(BASE / "tables" / p)
        )
        for p in paths
    }
    old = {p: f[~f.method.eq("Training prior")] for p, f in old.items()}
    metrics = []
    grids = []
    scores = []
    amb = []
    index = []
    priors = []
    for name, kind, proper, cal, targets in experiments(t):
        ctx = context(t, arrays, waves, name, kind, proper, cal, targets)
        prior = ctx["p"]["truth"].mean(axis=0)
        priors.extend(
            dict(fold=name, researcher_category=c, training_mean_fraction=v)
            for c, v in zip(CLASSES, prior)
        )
        for target, mix in ctx["tests"].items():
            truth = mix["truth"]
            p = np.tile(prior, (len(truth), 1))
            with np.load(
                CACHE / "abundance" / name / "baseline_NEON" / f"{target}_MESMA.npz"
            ) as a:
                ranges = a["ambiguity_range"]
            strata = np.select(
                [ranges < 0.1, ranges < 0.3], ["Low", "Moderate"], default="High"
            )
            common = np.sqrt(
                np.sum(
                    ((p @ ctx["classmeans"] - mix["NEON"]) * ctx["weights"]) ** 2,
                    axis=1,
                )
            )
            for rep in ["NEON", "OLI"]:
                rec = dict(
                    fold=name,
                    kind=kind,
                    target=target,
                    method="Training prior",
                    representation=rep,
                    test_bundles=len(np.unique(mix["bundle"])),
                    independent_test_parents=5 * len(np.unique(mix["bundle"])),
                    raw_constraint_violation_fraction=0.0,
                    common_reconstruction_RMSE=float(common.mean()),
                    native_reconstruction_RMSE=np.nan,
                )
                for j, (c, metric) in enumerate(
                    zip(CLASSES, fraction_metrics(truth, p))
                ):
                    metrics.append(dict(**rec, researcher_category=c, **metric))
                    for f in np.unique(np.round(truth[:, j], 6)):
                        ix = np.isclose(truth[:, j], f, atol=1e-6)
                        e = p[ix, j] - truth[ix, j]
                        grids.append(
                            dict(
                                **rec,
                                researcher_category=c,
                                true_fraction=f,
                                N=int(ix.sum()),
                                prediction_mean=p[ix, j].mean(),
                                bias=e.mean(),
                                RMSE=np.sqrt(np.mean(e * e)),
                                MAE=abs(e).mean(),
                                detection_probability=(p[ix, j] > 0.10).mean(),
                            )
                        )
                    for b in np.unique(mix["bundle"]):
                        ix = mix["bundle"] == b
                        scores.append(
                            dict(
                                **rec,
                                bundle=int(b),
                                researcher_category=c,
                                MSE=np.mean((p[ix, j] - truth[ix, j]) ** 2),
                                bias=np.mean(p[ix, j] - truth[ix, j]),
                            )
                        )
                for level in ["Low", "Moderate", "High"]:
                    ix = strata == level
                    if ix.any():
                        amb.append(
                            dict(
                                **rec,
                                ambiguity=level,
                                N=int(ix.sum()),
                                fraction_RMSE=np.sqrt(
                                    np.mean((p[ix] - truth[ix]) ** 2)
                                ),
                                mean_max_fraction_range=ranges[ix].mean(),
                                common_spectral_RMSE=common[ix].mean(),
                            )
                        )
                frame = pd.DataFrame(
                    dict(
                        mixture_id=np.arange(len(p)),
                        bundle=mix["bundle"],
                        ambiguity=strata,
                        common_reconstruction_RMSE=common,
                        native_reconstruction_RMSE=np.nan,
                    )
                )
                for j, c in enumerate(CLASSES):
                    frame["pred_" + c] = p[:, j]
                filename = f"abundance_prior_predictions_{name}_{target}_{rep}.parquet"
                frame.to_parquet(BASE / "tables" / filename, index=False)
                index.append(
                    dict(
                        fold=name,
                        kind=kind,
                        target=target,
                        method="Training prior",
                        representation=rep,
                        predictions=str((BASE / "tables" / filename).relative_to(REPO)),
                        truth=str(
                            (
                                BASE
                                / "tables"
                                / f"synthetic_truth_{name}_{target}.parquet"
                            ).relative_to(REPO)
                        ),
                    )
                )
    new = [metrics, grids, scores, amb, index]
    for path, values in zip(paths, new):
        save(pd.concat([old[path], pd.DataFrame(values)], ignore_index=True), path)
    comparison = pd.read_parquet(BASE / "tables/abundance_model_comparison.parquet")
    save(comparison, "abundance_model_comparison.csv")
    comparison.to_parquet(BASE / "abundance_model_comparison.parquet", index=False)
    save(pd.DataFrame(priors), "training_fraction_prior.csv")
    mse = (
        comparison.assign(MSE=comparison.RMSE**2)
        .groupby(["fold", "kind", "target", "representation", "method"])
        .MSE.mean()
        .unstack("method")
    )
    skill = (
        (1 - mse.div(mse["Training prior"], axis=0))
        .stack()
        .rename("MSE_skill_over_training_prior")
        .reset_index()
    )
    save(skill, "abundance_prior_skill.csv")
    print(
        "Added proper-training-mean null controls; no spectral test data used for predictions."
    )


if __name__ == "__main__":
    main()
