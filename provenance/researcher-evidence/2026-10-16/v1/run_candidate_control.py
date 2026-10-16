"""Ridge with exactly the retained MESMA candidate parents, on unchanged targets."""

import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from spectralbridge.researcher_information import TrainingTransform, project_simplex
from run_controls import BASE, REPO, PRIOR, load_data, checkpoint, sha, CATS
from run_abundance import experiments, context, mixtures_for


def main():
    t, arrays, waves, identity = load_data()
    identity.update(
        control_code=sha(__file__),
        control_design=sha(BASE / "ABUNDANCE_CONTROL_DESIGN.md"),
    )
    metrics = []
    paired = []
    for name, kind, proper, cal, targets in experiments(t):
        ctx = context(t, arrays, waves, name, kind, proper, cal, targets)
        for rep in ["NEON", "OLI"]:

            def run(d):
                selected = pd.read_csv(
                    REPO
                    / "artifacts/plant_spectral_atlas/researcher_information_20261015_v1/abundance"
                    / name
                    / ("baseline_" + rep)
                    / "selected_endmembers.csv"
                )
                selected = selected[selected.method.eq("MESMA")]
                parentindex = selected.parent_index.to_numpy()
                rows = ctx["bp"].ravel()[parentindex]
                bundles = np.column_stack(
                    [rows[selected.researcher_category.eq(c)] for c in CATS]
                )
                assert bundles.shape == (3, 5)
                members = t.loc[bundles.ravel(), ["GlobalID", "year", "label"]].copy()
                assert members.GlobalID.nunique() == 15
                members.to_csv(d / "candidate_parents.csv", index=False)
                mix = mixtures_for(t, arrays, bundles)
                tx = TrainingTransform("full", waves[rep]).fit(mix[rep])
                X = tx.transform(mix[rep])
                Y = mix["truth"]
                V = tx.transform(ctx["v"][rep])
                Z = ctx["v"]["truth"]
                best = None
                tuning = []
                for alpha in [0.1, 10]:
                    m = Ridge(alpha=alpha).fit(X, Y)
                    loss = float(
                        np.sqrt(np.mean((project_simplex(m.predict(V)) - Z) ** 2))
                    )
                    tuning.append(dict(alpha=alpha, tuning_RMSE=loss))
                    if best is None or loss < best[0]:
                        best = (loss, alpha, m)
                pd.DataFrame(tuning).to_csv(d / "tuning.csv", index=False)
                np.savez_compressed(
                    d / "model.npz",
                    mean=tx.scaler.mean_,
                    scale=tx.scaler.scale_,
                    coef=best[2].coef_,
                    intercept=best[2].intercept_,
                    alpha=best[1],
                )
                for target, test in ctx["tests"].items():
                    P = project_simplex(best[2].predict(tx.transform(test[rep])))
                    np.savez_compressed(
                        d / (target + ".npz"),
                        pred=P,
                        truth=test["truth"],
                        bundle=test["bundle"],
                    )

            d = checkpoint("candidate_" + name + "_" + rep, identity, run)
            for target in ctx["tests"]:
                a = np.load(d / (target + ".npz"))
                P, Y, b = a["pred"], a["truth"], a["bundle"]
                ref = pd.read_parquet(
                    REPO
                    / "artifacts/plant_spectral_atlas/researcher_information_20261015_v1/abundance"
                    / name
                    / ("baseline_" + rep)
                    / (target + "_MESMA_predictions.parquet")
                )[["pred_" + c for c in CATS]].to_numpy()
                rng = np.random.default_rng(20261016)
                bm = []
                br = []
                for k in np.unique(b):
                    bm.append(np.mean((P[b == k] - Y[b == k]) ** 2))
                    br.append(np.mean((ref[b == k] - Y[b == k]) ** 2))
                draw = rng.integers(0, len(bm), (999, len(bm)))
                delta = np.sqrt(np.asarray(bm)[draw].mean(axis=1)) - np.sqrt(
                    np.asarray(br)[draw].mean(axis=1)
                )
                lo, hi = np.quantile(delta, [0.025, 0.975])
                metrics.append(
                    dict(
                        fold=name,
                        kind=kind,
                        target=target,
                        representation=rep,
                        RMSE=float(np.sqrt(np.mean((P - Y) ** 2))),
                        MESMA_RMSE=float(np.sqrt(np.mean((ref - Y) ** 2))),
                        difference_low=lo,
                        difference_high=hi,
                        proper_parents=15,
                        proper_mixtures=510,
                    )
                )
    pd.DataFrame(metrics).to_csv(BASE / "tables/same_candidate_ridge.csv", index=False)
    print("Same-candidate control complete:", len(metrics), "target cases")


if __name__ == "__main__":
    main()
