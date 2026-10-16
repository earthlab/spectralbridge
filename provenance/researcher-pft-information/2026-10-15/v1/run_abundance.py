"""Common parent-disjoint synthetic researcher-category abundance benchmark."""

import json
from concurrent.futures import ThreadPoolExecutor
import logging
import warnings
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from spectralbridge.researcher_information import (
    RESEARCHER_CATEGORIES,
    disjoint_parent_bundles,
    project_simplex,
    fraction_metrics,
    TrainingTransform,
    orthogonal_feature_path,
)
from spectralbridge.mixtures import mixture_truth, fit_models, fcls, select_endmembers
from spectralbridge.pft_method_audit import wavelength_weights
from spectralbridge.plant_spectral_atlas import _file_hash
from common import BASE, REPO, LOG, load, save, folds, checkpoint, seed

CLASSES = np.array(RESEARCHER_CATEGORIES)


def role_split(table, fraction, name):
    unique = table.drop_duplicates("GlobalID")
    a, b = train_test_split(
        unique.GlobalID,
        test_size=fraction,
        stratify=unique.cover_category,
        random_state=seed(name),
    )
    return table[table.GlobalID.isin(a)], table[table.GlobalID.isin(b)]


def experiments(t):
    for name, kind, tr, te in folds(t, paired=False):
        proper, cal = role_split(t.loc[tr], 0.2, name)
        yield name, kind, proper, cal, {"target": t.loc[te]}
    niwo = t[t.site.eq("NIWO")].groupby("GlobalID").filter(lambda g: len(g) == 2)
    pool, target = role_split(niwo, 0.2, "paired_shared_test")
    proper, cal = role_split(pool, 0.25, "paired_shared_calibration")
    for year in [2020, 2023]:
        yield (
            f"paired_train{year}",
            "paired_year",
            proper[proper.year.eq(year)],
            cal[cal.year.eq(year)],
            {
                "target2020": target[target.year.eq(2020)],
                "target2023": target[target.year.eq(2023)],
            },
        )


def mixtures_for(table, arrays, bundles):
    result = {}
    truth = []
    bundle_id = []
    records = []
    for sensor, X in arrays.items():
        curves = []
        for b, ix in enumerate(bundles):
            mix = mixture_truth(X[ix], CLASSES, pairs_per_composition=1, seed=0)
            assert np.array_equal(mix["classes"], CLASSES)
            curves.append(mix["spectra"])
            if sensor == "NEON":
                truth.append(mix["truth"])
                bundle_id.extend([b] * len(mix["truth"]))
                for i, (indices, fractions) in enumerate(
                    zip(mix["sources"], mix["source_fractions"])
                ):
                    valid = indices >= 0
                    records.append(
                        dict(
                            bundle=b,
                            within_bundle=i,
                            source_ids="|".join(table.loc[ix[indices[valid]]].GlobalID),
                            source_years="|".join(
                                table.loc[ix[indices[valid]]].year.astype(str)
                            ),
                            source_fractions=json.dumps(fractions[valid].tolist()),
                        )
                    )
        result[sensor] = np.concatenate(curves)
    result["truth"] = np.concatenate(truth)
    result["bundle"] = np.asarray(bundle_id)
    result["records"] = pd.DataFrame(records)
    return result


def context(t, arrays, waves, name, kind, proper, cal, targets):
    bp = disjoint_parent_bundles(proper, 24, seed(name + "_proper"))
    bc = disjoint_parent_bundles(cal, 8, seed(name + "_calibration"))
    testbundles = {
        k: disjoint_parent_bundles(
            tab,
            12,
            seed("shared_" + name.removesuffix("2020").removesuffix("2023") + "_test"),
        )
        for k, tab in targets.items()
    }
    assert len(bp) == 24 and len(bc) == 8, (name, len(bp), len(bc))
    roles = []
    for role, tab, bundles in [("proper", proper, bp), ("calibration", cal, bc)] + [
        (k, targets[k], b) for k, b in testbundles.items()
    ]:
        for bundle, ix in enumerate(bundles):
            for c, index in zip(CLASSES, ix):
                roles.append(
                    dict(
                        fold=name,
                        kind=kind,
                        role=role,
                        bundle=bundle,
                        researcher_category=c,
                        GlobalID=t.loc[index, "GlobalID"],
                        year=t.loc[index, "year"],
                        source_index=int(index),
                    )
                )
    members = pd.DataFrame(roles)
    properids = set(members[members.role.eq("proper")].GlobalID)
    calids = set(members[members.role.eq("calibration")].GlobalID)
    testids = set(members[~members.role.isin(["proper", "calibration"])].GlobalID)
    assert not properids & calids and not properids & testids and not calids & testids
    assert all(
        g.groupby("GlobalID").bundle.nunique().max() == 1
        for _, g in members.groupby("role")
    )
    p = mixtures_for(t, arrays, bp)
    v = mixtures_for(t, arrays, bc)
    tests = {k: mixtures_for(t, arrays, b) for k, b in testbundles.items()}
    parentX = {k: X[bp.ravel()] for k, X in arrays.items()}
    parent_labels = np.tile(CLASSES, len(bp))
    scale = float(np.median(np.sqrt(np.mean(parentX["NEON"] ** 2, axis=1))))
    weights = np.sqrt(wavelength_weights(waves["NEON"])) / scale
    classmeans = np.array(
        [parentX["NEON"][parent_labels == c].mean(axis=0) for c in CLASSES]
    )
    path = orthogonal_feature_path(parentX["NEON"], parent_labels, 20)
    return dict(
        p=p,
        v=v,
        tests=tests,
        members=members,
        parentX=parentX,
        parent_labels=parent_labels,
        scale=scale,
        weights=weights,
        classmeans=classmeans,
        path=path,
        bp=bp,
        testbundles=testbundles,
    )


def model(method, param):
    if method.startswith("Ridge"):
        return Ridge(alpha=param)
    if method.startswith("PLS"):
        return PLSRegression(n_components=param, scale=False, max_iter=500)
    if method == "Random forest":
        return RandomForestRegressor(
            n_estimators=100,
            max_depth=param,
            min_samples_leaf=5,
            n_jobs=1,
            random_state=20261015,
        )
    if method == "Gradient boosting":
        return MultiOutputRegressor(
            HistGradientBoostingRegressor(
                max_iter=80,
                max_leaf_nodes=param,
                max_bins=64,
                l2_regularization=1,
                early_stopping=False,
                random_state=20261015,
            )
        )
    raise ValueError(method)


def baseline(ctx, waves, sensor, directory):
    library = ctx["parentX"][sensor] / ctx["scale"]
    w = (
        np.sqrt(wavelength_weights(waves[sensor]))
        if sensor == "NEON"
        else np.ones(7) / np.sqrt(7)
    )
    labels = ctx["parent_labels"]
    medoid = select_endmembers(library * w, labels, "medoid", 1)
    ear = select_endmembers(library * w, labels, "EAR", 3)
    pd.DataFrame(
        {
            "method": ["FCLS"] * len(medoid) + ["MESMA"] * len(ear),
            "parent_index": np.r_[medoid, ear],
            "researcher_category": labels[np.r_[medoid, ear]],
        }
    ).to_csv(directory / "selected_endmembers.csv", index=False)
    for target, mix in ctx["tests"].items():
        X = mix[sensor] / ctx["scale"] * w
        fits = {
            "FCLS": fcls(X, library[medoid] * w),
            "MESMA": fit_models(X, labels[ear], library[ear] * w, tolerance=0.01),
        }
        for method, fit in fits.items():
            np.testing.assert_array_equal(
                fit["classes"], np.arange(5) if method == "FCLS" else CLASSES
            )
            np.savez_compressed(
                directory / f"{target}_{method}.npz",
                pred=fit["fractions"],
                native_RMSE=fit["RMSE"],
                ambiguity_range=fit["near_fraction_range"].max(axis=1),
                near_compositions=fit["near_compositions"],
            )
        if sensor == "NEON":
            oracle = []
            ranks = []
            for b, ix in enumerate(ctx["testbundles"][target]):
                e = ctx["arrays"]["NEON"][ix] / ctx["scale"] * w
                use = mix["bundle"] == b
                fit = fcls(X[use], e)
                oracle.append(
                    dict(
                        bundle=b,
                        N=int(use.sum()),
                        fraction_RMSE=float(
                            np.sqrt(
                                np.mean((fit["fractions"] - mix["truth"][use]) ** 2)
                            )
                        ),
                        spectral_RMSE=float(np.mean(fit["RMSE"])),
                    )
                )
                ranks.append(
                    dict(
                        bundle=b,
                        affine_rank=int(np.linalg.matrix_rank(e[1:] - e[0])),
                        condition_number=float(np.linalg.cond(e[1:] - e[0])),
                    )
                )
            pd.DataFrame(oracle).to_csv(directory / f"{target}_oracle.csv", index=False)
            pd.DataFrame(ranks).to_csv(
                directory / f"{target}_oracle_rank.csv", index=False
            )


def supervised(ctx, waves, method, representation, directory, training_bundles=24):
    sensor = "OLI" if representation == "OLI" else "NEON"
    kind = "full" if representation in ["NEON", "OLI"] else representation
    positions = (
        ctx["path"][: int(kind.removeprefix("selected"))]
        if kind.startswith("selected")
        else None
    )
    keep = ctx["p"]["bundle"] < training_bundles
    transform = TrainingTransform(kind, waves[sensor], positions).fit(
        ctx["p"][sensor][keep]
    )
    X = transform.transform(ctx["p"][sensor][keep])
    Y = ctx["p"]["truth"][keep]
    V = transform.transform(ctx["v"][sensor])
    Z = ctx["v"]["truth"]
    params = (
        [0.1, 10]
        if method.startswith("Ridge")
        else [5, min(15, X.shape[1])]
        if method.startswith("PLS")
        else [12, None]
        if method == "Random forest"
        else [7, 15]
    )
    best = None
    scores = []
    for param in dict.fromkeys(params):
        fitted = model(method, param)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fitted.fit(X, Y)
        pred = project_simplex(fitted.predict(V))
        error = float(np.sqrt(np.mean((pred - Z) ** 2)))
        scores.append(
            dict(
                parameter=str(param),
                tuning_fraction_RMSE=error,
                warnings="|".join(str(w.message) for w in caught),
            )
        )
        if best is None or error < best[0]:
            best = (error, fitted, param)
    pd.DataFrame(scores).to_csv(directory / "tuning.csv", index=False)
    for target, mix in ctx["tests"].items():
        raw = best[1].predict(transform.transform(mix[sensor]))
        pred = project_simplex(raw)
        np.savez_compressed(directory / (target + ".npz"), pred=pred, raw=raw)
    np.savez_compressed(
        directory / "transform.npz",
        mean=transform.scaler.mean_,
        scale=transform.scaler.scale_,
        selected=np.array([]) if positions is None else positions,
        PCA_components=np.array([])
        if transform.pca is None
        else transform.pca.components_,
    )
    (directory / "parameters.json").write_text(
        json.dumps(
            {
                "method": method,
                "representation": representation,
                "selected_parameter": best[2],
                "proper_training_bundles": training_bundles,
                "independent_proper_parents": 5 * training_bundles,
                "training_mixtures": len(Y),
                "calibration_mixtures": len(Z),
                "normalization_fit_role": "proper_training_only",
            },
            indent=2,
        )
        + "\n"
    )


def two_stage(ctx, waves, sensor, directory):
    transform = TrainingTransform("full", waves[sensor]).fit(ctx["p"][sensor])
    X = transform.transform(ctx["p"][sensor])
    V = transform.transform(ctx["v"][sensor])
    Y = ctx["p"]["truth"]
    Z = ctx["v"]["truth"]
    detector = []
    regressor = []
    thresholds = []
    tuning = []
    for j, c in enumerate(CLASSES):
        present = Y[:, j] > 0
        classifier = LogisticRegression(
            C=1, class_weight="balanced", max_iter=1000
        ).fit(X, present)
        score = classifier.predict_proba(V)[:, 1]
        true = Z[:, j] > 0
        values = [
            (np.mean([(score[true] >= q).mean(), (score[~true] < q).mean()]), q)
            for q in [0.1, 0.3, 0.5, 0.7, 0.9]
        ]
        cutoff = max(values, key=lambda v: v[0])[1]
        best = None
        for alpha in [0.1, 10]:
            r = Ridge(alpha=alpha).fit(X[present], Y[present, j])
            e = np.mean((r.predict(V[true]) - Z[true, j]) ** 2)
            if best is None or e < best[0]:
                best = (e, r, alpha)
        detector.append(classifier)
        regressor.append(best[1])
        thresholds.append(cutoff)
        tuning.append(
            dict(researcher_category=c, presence_threshold=cutoff, ridge_alpha=best[2])
        )
    pd.DataFrame(tuning).to_csv(directory / "tuning.csv", index=False)
    for target, mix in ctx["tests"].items():
        T = transform.transform(mix[sensor])
        prob = np.column_stack([m.predict_proba(T)[:, 1] for m in detector])
        raw = np.maximum(np.column_stack([m.predict(T) for m in regressor]), 0)
        gate = prob >= thresholds
        empty = ~gate.any(axis=1)
        gate[empty, np.argmax(prob[empty], axis=1)] = True
        raw *= gate
        # Project only the admitted face; rejected classes remain exactly zero.
        pred = np.zeros_like(raw)
        for mask in np.unique(gate, axis=0):
            ix = np.all(gate == mask, axis=1)
            if mask.sum() == 1:
                pred[np.ix_(ix, mask)] = 1
            else:
                pred[np.ix_(ix, mask)] = project_simplex(raw[np.ix_(ix, mask)])
        np.savez_compressed(
            directory / (target + ".npz"),
            pred=pred,
            raw=raw,
            presence_probability=prob,
            gate=gate,
        )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t, arrays, waves, identity = load()
    identity.update(
        code=_file_hash(__file__),
        helper=_file_hash(REPO / "src/spectralbridge/researcher_information.py"),
        common=_file_hash(BASE / "common.py"),
        mixtures=_file_hash(REPO / "src/spectralbridge/mixtures.py"),
    )
    metrics = []
    grid = []
    bundle_scores = []
    members = []
    oracles = []
    cases = []
    ambiguity_rows = []
    for name, kind, proper, cal, targets in experiments(t):
        LOG.info("Abundance parent-disjoint experiment %s", name)
        ctx = context(t, arrays, waves, name, kind, proper, cal, targets)
        ctx["arrays"] = arrays
        members.append(ctx["members"])
        baseline_dirs = {}
        for sensor in ["NEON", "OLI"]:
            baseline_dirs[sensor] = checkpoint(
                "abundance/" + name + "/baseline_" + sensor,
                identity,
                lambda d, s=sensor: baseline(ctx, waves, s, d),
            )
        for target in targets:
            o = pd.read_csv(baseline_dirs["NEON"] / f"{target}_oracle.csv")
            o["fold"] = name
            o["target"] = target
            oracles.append(o)
        work = [
            (m, r, 24)
            for r in [
                "NEON",
                "OLI",
                "shape",
                "derivative1",
                "derivative2",
                "PCA20",
                "selected7",
                "selected20",
            ]
            for m in ["Ridge", "PLS"]
        ]
        work += [
            (m, r, 24)
            for r in ["NEON", "OLI"]
            for m in ["Random forest", "Gradient boosting", "Two-stage"]
        ]
        work += [(m, "NEON", n) for m in ["Ridge", "PLS"] for n in [8, 16]]
        fitted = []

        def fit_item(item):
            number, (method, representation, n) = item
            label = method if n == 24 else method + f" ({n} bundles)"
            LOG.info(
                "%s case %s/%s: %s / %s", name, number, len(work), label, representation
            )
            key = method.replace(" ", "_") + "_" + representation + "_n" + str(n)
            d = checkpoint(
                "abundance/" + name + "/" + key,
                identity,
                lambda d: (
                    two_stage(ctx, waves, representation, d)
                    if method == "Two-stage"
                    else supervised(ctx, waves, method, representation, d, n)
                ),
            )
            return label, representation, d

        with ThreadPoolExecutor(max_workers=3) as executor:
            fitted = list(executor.map(fit_item, enumerate(work, 1)))
        for target, mix in ctx["tests"].items():
            truth = mix["truth"]
            a = np.load(baseline_dirs["NEON"] / f"{target}_MESMA.npz")[
                "ambiguity_range"
            ]
            strata = np.select([a < 0.1, a < 0.3], ["Low", "Moderate"], default="High")
            allfits = [
                (m, s, d) for s, d in baseline_dirs.items() for m in ["FCLS", "MESMA"]
            ] + fitted
            truthframe = mix["records"].copy()
            for j, c in enumerate(CLASSES):
                truthframe[c] = truth[:, j]
            truthframe["fold"] = name
            truthframe["target"] = target
            truthframe["kind"] = kind
            truthframe.to_parquet(
                BASE / "tables" / f"synthetic_truth_{name}_{target}.parquet",
                index=False,
            )
            for method, representation, d in allfits:
                path = d / (
                    f"{target}_{method}.npz"
                    if method in ["FCLS", "MESMA"]
                    else target + ".npz"
                )
                with np.load(path) as archive:
                    p = archive["pred"]
                    raw_violation = (
                        float(
                            np.mean(
                                (archive["raw"] < 0).any(1)
                                | (~np.isclose(archive["raw"].sum(1), 1))
                            )
                        )
                        if "raw" in archive
                        else 0.0
                    )
                    native = (
                        archive["native_RMSE"]
                        if "native_RMSE" in archive
                        else np.full(len(p), np.nan)
                    )
                assert np.all(p >= -1e-10) and np.allclose(p.sum(1), 1)
                common_error = np.sqrt(
                    np.sum(
                        ((p @ ctx["classmeans"] - mix["NEON"]) * ctx["weights"]) ** 2,
                        axis=1,
                    )
                )
                rec = dict(
                    fold=name,
                    kind=kind,
                    target=target,
                    method=method,
                    representation=representation,
                    test_bundles=len(np.unique(mix["bundle"])),
                    independent_test_parents=5 * len(np.unique(mix["bundle"])),
                    raw_constraint_violation_fraction=raw_violation,
                    common_reconstruction_RMSE=float(common_error.mean()),
                    native_reconstruction_RMSE=float(np.nanmean(native))
                    if np.isfinite(native).any()
                    else np.nan,
                )
                for j, (c, met) in enumerate(zip(CLASSES, fraction_metrics(truth, p))):
                    metrics.append(dict(**rec, researcher_category=c, **met))
                    for f in np.unique(np.round(truth[:, j], 6)):
                        ix = np.isclose(truth[:, j], f, atol=1e-6)
                        e = p[ix, j] - truth[ix, j]
                        grid.append(
                            dict(
                                **rec,
                                researcher_category=c,
                                true_fraction=f,
                                N=int(ix.sum()),
                                prediction_mean=float(p[ix, j].mean()),
                                bias=float(e.mean()),
                                RMSE=float(np.sqrt(np.mean(e * e))),
                                MAE=float(abs(e).mean()),
                                detection_probability=float(np.mean(p[ix, j] > 0.10)),
                            )
                        )
                for b in np.unique(mix["bundle"]):
                    ix = mix["bundle"] == b
                    for j, c in enumerate(CLASSES):
                        bundle_scores.append(
                            dict(
                                **rec,
                                bundle=int(b),
                                researcher_category=c,
                                MSE=float(np.mean((p[ix, j] - truth[ix, j]) ** 2)),
                                bias=float(np.mean(p[ix, j] - truth[ix, j])),
                            )
                        )
                for level in ["Low", "Moderate", "High"]:
                    ix = strata == level
                    if ix.any():
                        ambiguity_rows.append(
                            dict(
                                **rec,
                                ambiguity=level,
                                N=int(ix.sum()),
                                fraction_RMSE=float(
                                    np.sqrt(np.mean((p[ix] - truth[ix]) ** 2))
                                ),
                                mean_max_fraction_range=float(a[ix].mean()),
                                common_spectral_RMSE=float(common_error[ix].mean()),
                            )
                        )
                out = pd.DataFrame(
                    dict(
                        mixture_id=np.arange(len(p)),
                        bundle=mix["bundle"],
                        ambiguity=strata,
                        common_reconstruction_RMSE=common_error,
                        native_reconstruction_RMSE=native,
                    )
                )
                for j, c in enumerate(CLASSES):
                    out["pred_" + c] = p[:, j]
                out.to_parquet(d / f"{target}_predictions.parquet", index=False)
                cases.append(
                    dict(
                        fold=name,
                        kind=kind,
                        target=target,
                        method=method,
                        representation=representation,
                        predictions=str(
                            (d / f"{target}_predictions.parquet").relative_to(REPO)
                        ),
                        truth=str(
                            (
                                BASE
                                / "tables"
                                / f"synthetic_truth_{name}_{target}.parquet"
                            ).relative_to(REPO)
                        ),
                    )
                )
    comparison = pd.DataFrame(metrics)
    save(comparison, "abundance_model_comparison.parquet")
    save(comparison, "abundance_model_comparison.csv")
    save(pd.DataFrame(grid), "abundance_by_true_fraction.csv")
    save(pd.DataFrame(bundle_scores), "abundance_bundle_scores.parquet")
    save(pd.DataFrame(ambiguity_rows), "abundance_by_ambiguity.csv")
    save(pd.concat(members), "abundance_parent_memberships.csv")
    save(pd.concat(oracles), "oracle_solver_controls.csv")
    save(pd.DataFrame(cases), "abundance_case_index.csv")
    LOG.info("All researcher-category synthetic abundance comparisons complete")


if __name__ == "__main__":
    main()
