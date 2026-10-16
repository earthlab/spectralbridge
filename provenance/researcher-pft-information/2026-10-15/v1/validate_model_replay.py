"""Replay selected abundance pipelines; independently solve ridge normal equations."""

import json
from pathlib import Path
import tempfile
import numpy as np
from sklearn.cross_decomposition import PLSRegression
from spectralbridge.researcher_information import TrainingTransform, project_simplex
from common import BASE, CACHE, load
from run_abundance import experiments, context, model, two_stage, baseline


def main():
    t, arrays, waves, _ = load()
    checks = []
    for name, kind, proper, cal, targets in experiments(t):
        ctx = context(t, arrays, waves, name, kind, proper, cal, targets)
        ctx["arrays"] = arrays
        cases = [(m, r, 24) for m in ["Ridge", "PLS"] for r in ["NEON", "OLI"]]
        if name == "plant_0":
            cases += [
                (m, r, 24)
                for m in ["Ridge", "PLS"]
                for r in [
                    "shape",
                    "derivative1",
                    "derivative2",
                    "PCA20",
                    "selected7",
                    "selected20",
                ]
            ]
            cases += [(m, "NEON", n) for m in ["Ridge", "PLS"] for n in [8, 16]]
            cases += [
                (m, r, 24)
                for m in ["Random forest", "Gradient boosting"]
                for r in ["NEON", "OLI"]
            ]
        for method, rep, n in cases:
            d = (
                CACHE
                / "abundance"
                / name
                / (method.replace(" ", "_") + "_" + rep + "_n" + str(n))
            )
            params = json.loads((d / "parameters.json").read_text())
            sensor = "OLI" if rep == "OLI" else "NEON"
            tfkind = "full" if rep in ["NEON", "OLI"] else rep
            positions = (
                ctx["path"][: int(rep.removeprefix("selected"))]
                if rep.startswith("selected")
                else None
            )
            use = ctx["p"]["bundle"] < n
            transform = TrainingTransform(tfkind, waves[sensor], positions).fit(
                ctx["p"][sensor][use]
            )
            with np.load(d / "transform.npz") as expected:
                np.testing.assert_allclose(
                    transform.scaler.mean_, expected["mean"], atol=1e-12
                )
                np.testing.assert_allclose(
                    transform.scaler.scale_, expected["scale"], atol=1e-12
                )
            X = transform.transform(ctx["p"][sensor][use])
            Y = ctx["p"]["truth"][use]
            parameter = params["selected_parameter"]
            if method == "Ridge":
                xm, ym = X.mean(0), Y.mean(0)
                A = X - xm
                coef = np.linalg.solve(
                    A.T @ A + parameter * np.eye(X.shape[1]), A.T @ (Y - ym)
                )

                def predict(T):
                    return (T - xm) @ coef + ym
            else:
                fitted = (
                    PLSRegression(n_components=parameter, scale=False, max_iter=500)
                    if method == "PLS"
                    else model(method, parameter)
                )
                fitted.fit(X, Y)
                predict = fitted.predict
            for target, mix in ctx["tests"].items():
                got = project_simplex(predict(transform.transform(mix[sensor])))
                expected = np.load(d / (target + ".npz"))["pred"]
                np.testing.assert_allclose(got, expected, atol=2e-8, rtol=1e-7)
                checks.append(
                    dict(
                        fold=name,
                        target=target,
                        method=method,
                        representation=rep,
                        training_bundles=n,
                        max_absolute_prediction_difference=float(
                            abs(got - expected).max()
                        ),
                        training_transform_reproduced=True,
                    )
                )
        if name == "plant_0":
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for rep in ["NEON", "OLI"]:
                    d = root / rep
                    d.mkdir()
                    baseline(ctx, waves, rep, d)
                    for method in ["FCLS", "MESMA"]:
                        got = np.load(d / ("target_" + method + ".npz"))["pred"]
                        expected = np.load(
                            CACHE
                            / "abundance"
                            / name
                            / ("baseline_" + rep)
                            / ("target_" + method + ".npz")
                        )["pred"]
                        np.testing.assert_allclose(got, expected, atol=1e-10)
                        checks.append(
                            dict(
                                fold=name,
                                method=method,
                                representation=rep,
                                max_absolute_prediction_difference=float(
                                    abs(got - expected).max()
                                ),
                            )
                        )
                d = root / "two_stage"
                d.mkdir()
                two_stage(ctx, waves, "NEON", d)
                got = np.load(d / "target.npz")["pred"]
                expected = np.load(
                    CACHE / "abundance" / name / "Two-stage_NEON_n24/target.npz"
                )["pred"]
                np.testing.assert_allclose(got, expected, atol=1e-10)
                checks.append(
                    dict(
                        fold=name,
                        method="Two-stage",
                        representation="NEON",
                        max_absolute_prediction_difference=float(
                            abs(got - expected).max()
                        ),
                    )
                )
    result = {
        "status": "passed",
        "independent_ridge_normal_equations": True,
        "replayed_prediction_cases": len(checks),
        "checks": checks,
    }
    (BASE / "model_replay_validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        "Reproduced",
        len(checks),
        "abundance prediction cases, with independent ridge normal equations.",
    )


if __name__ == "__main__":
    main()
