"""Replay same-candidate ridge with independent normal equations and exact parents."""

import json
import numpy as np
import pandas as pd
from spectralbridge.researcher_information import project_simplex
from run_controls import BASE, REPO, load_data, CATS
from run_abundance import experiments, context, mixtures_for


def main():
    t, arrays, waves, _ = load_data()
    cases = 0
    max_error = 0.0
    for name, kind, proper, cal, targets in experiments(t):
        ctx = context(t, arrays, waves, name, kind, proper, cal, targets)
        for rep in ["NEON", "OLI"]:
            d = BASE / "checkpoints" / ("candidate_" + name + "_" + rep)
            saved = pd.read_csv(d / "candidate_parents.csv")
            selected = pd.read_csv(
                REPO
                / "artifacts/plant_spectral_atlas/researcher_information_20261015_v1/abundance"
                / name
                / ("baseline_" + rep)
                / "selected_endmembers.csv"
            )
            selected = selected[selected.method.eq("MESMA")]
            rows = ctx["bp"].ravel()[selected.parent_index.to_numpy()]
            bundles = np.column_stack(
                [rows[selected.researcher_category.eq(c)] for c in CATS]
            )
            assert set(saved.GlobalID) == set(t.loc[bundles.ravel()].GlobalID)
            assert not set(saved.GlobalID) & set(
                ctx["members"][ctx["members"].role.ne("proper")].GlobalID
            )
            mix = mixtures_for(t, arrays, bundles)
            a = np.load(d / "model.npz")
            np.testing.assert_allclose(mix[rep].mean(axis=0), a["mean"], atol=1e-10)
            scale = mix[rep].std(axis=0)
            scale[scale == 0] = 1
            np.testing.assert_allclose(scale, a["scale"], rtol=1e-10, atol=1e-10)
            X = (mix[rep] - a["mean"]) / a["scale"]
            Y = mix["truth"]
            ym = Y.mean(axis=0)
            xm = X.mean(axis=0)
            V = (ctx["v"][rep] - a["mean"]) / a["scale"]
            scores = []
            for alpha in [0.1, 10]:
                coef = np.linalg.solve(
                    (X - xm).T @ (X - xm) + alpha * np.eye(X.shape[1]),
                    (X - xm).T @ (Y - ym),
                ).T
                intercept = ym - xm @ coef.T
                loss = np.sqrt(
                    np.mean(
                        (project_simplex(V @ coef.T + intercept) - ctx["v"]["truth"])
                        ** 2
                    )
                )
                scores.append((loss, alpha, coef, intercept))
            best = min(scores, key=lambda z: z[0])
            assert best[1] == float(a["alpha"])
            np.testing.assert_allclose(best[2], a["coef"], rtol=1e-7, atol=1e-8)
            for target, test in ctx["tests"].items():
                p = project_simplex(
                    ((test[rep] - a["mean"]) / a["scale"]) @ best[2].T + best[3]
                )
                old = np.load(d / (target + ".npz"))
                np.testing.assert_allclose(old["truth"], test["truth"], atol=1e-12)
                err = float(abs(p - old["pred"]).max())
                max_error = max(err, max_error)
                np.testing.assert_allclose(p, old["pred"], atol=1e-8, rtol=1e-7)
                cases += 1
    result = {
        "status": "passed",
        "target_cases": cases,
        "same_15_MESMA_candidate_IDs": True,
        "roles_disjoint": True,
        "alpha_independently_selected_only_on_tuning": True,
        "normal_equation_max_prediction_difference": max_error,
    }
    (BASE / "candidate_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
