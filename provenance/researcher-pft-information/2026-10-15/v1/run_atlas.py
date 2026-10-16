"""Full wavelength information with held-ID, site, year and paired-year targets."""

from itertools import combinations
import logging
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from spectralbridge.researcher_information import (
    RESEARCHER_CATEGORIES,
    identity_weights,
    univariate_discrimination,
    orthogonal_feature_path,
)
from spectralbridge.plant_spectral_atlas import _file_hash
from common import BASE, REPO, LOG, load, save, folds, checkpoint, seed

BUDGETS = [1, 2, 3, 5, 7, 10, 20, 50, 100, 360]


def region(w):
    return np.select(
        [w < 700, w < 750, w < 1340, w < 1790],
        ["Visible", "Red edge", "NIR", "SWIR1"],
        default="SWIR2",
    )


def inference(waves):
    root = REPO / "artifacts/plant_spectral_atlas/researcher_pft_statistics"
    summary = pd.read_csv(root / "method_comparison.csv")
    native = pd.read_parquet(root / "polygon_year_spectra.parquet")
    source_waves = np.array(
        [float(c.split("_wl")[1][:-2]) for c in native if c.startswith("corr_wl")]
    )
    rows = []
    for r in summary[
        summary.blocking.eq("flight_history") & summary.status.eq("tested")
    ].itertuples():
        with np.load(root / "checkpoints" / (r.test_id + ".npz")) as a:
            obs = np.abs(a["curves"][0] / a["se"])
            null = np.sort(a["stats"][1:, 0])
            p = (1 + len(null) - np.searchsorted(null, obs - 1e-12, side="left")) / (
                len(null) + 1
            )
            for j, col in enumerate(a["columns"]):
                assert source_waves[col] in waves, source_waves[col]
                rows.append(
                    dict(
                        pair=r.pair,
                        class_a=r.a,
                        class_b=r.b,
                        site=r.site,
                        year=r.year,
                        wavelength_nm=source_waves[col],
                        matched_effect=a["curves"][0, j] / a["scale"][j],
                        stored_beta=a["curves"][0, j],
                        adjusted_p=min(1.0, 40 * p[j]),
                        within_contrast_maxT_p=p[j],
                        N_a=r.n_a,
                        N_b=r.n_b,
                        evidence_scope="full_cohort_descriptive_not_feature_selection",
                    )
                )
    result = pd.DataFrame(rows)
    save(result, "cohort_wavelength_inference.csv")
    return result


def fit_lr(X, y, ids, positions, C):
    weights = identity_weights(ids, y)
    scaler = StandardScaler().fit(X[:, positions], sample_weight=weights)
    model = LogisticRegression(C=C, max_iter=1500, solver="lbfgs")
    model.fit(scaler.transform(X[:, positions]), y, sample_weight=weights)
    return scaler, model


def ba(y, p, ids):
    weights = identity_weights(ids)
    return np.mean(
        [np.average(p[y == c] == c, weights=weights[y == c]) for c in np.unique(y)]
    )


def classification_fold(t, arrays, waves, name, kind, tr, te, directory):
    train, test = t.loc[tr], t.loc[te]
    X, T = arrays["NEON"][tr], arrays["NEON"][te]
    y, z = train.label.to_numpy(), test.label.to_numpy()
    gids, tid = train.GlobalID.to_numpy(), test.GlobalID.to_numpy()
    assert not set(gids) & set(tid)
    cv = list(
        StratifiedGroupKFold(3, shuffle=True, random_state=seed(name)).split(X, y, gids)
    )
    tune = []
    paths = []
    membership = []
    for inner, (a, b) in enumerate(cv):
        assert not set(gids[a]) & set(gids[b])
        path = orthogonal_feature_path(X[a], y[a], 100, identity_weights(gids[a], y[a]))
        paths.append(path)
        for role, ix in [("proper", a), ("validation", b)]:
            membership.extend(
                dict(inner=inner, role=role, GlobalID=v) for v in np.unique(gids[ix])
            )
        for budget in BUDGETS + ["OLI"]:
            A, V = (
                (arrays["OLI"][tr][a], arrays["OLI"][tr][b])
                if budget == "OLI"
                else (X[a], X[b])
            )
            pos = np.arange(A.shape[1]) if budget in [360, "OLI"] else path[:budget]
            for C in [0.1, 1, 10]:
                sc, model = fit_lr(A, y[a], gids[a], pos, C)
                pred = model.predict(sc.transform(V[:, pos]))
                tune.append(
                    dict(
                        inner=inner, budget=str(budget), C=C, BA=ba(y[b], pred, gids[b])
                    )
                )
    tuning = pd.DataFrame(tune)
    tuning.to_csv(directory / "inner_tuning.csv", index=False)
    pd.DataFrame(membership).to_csv(directory / "inner_membership.csv", index=False)
    fullpath = orthogonal_feature_path(X, y, 100, identity_weights(gids, y))
    pd.DataFrame(
        {
            "rank": np.arange(1, len(fullpath) + 1),
            "column": fullpath,
            "wavelength_nm": waves["NEON"][fullpath],
        }
    ).to_csv(directory / "selected_path.csv", index=False)
    corr = np.corrcoef(X, rowvar=False)
    np.savez_compressed(
        directory / "training_correlation.npz",
        correlation=corr,
        wavelength_nm=waves["NEON"],
    )
    summaries = []
    rates = []
    confusions = []
    predictions = []
    for budget in BUDGETS + ["OLI"]:
        candidates = tuning[tuning.budget.eq(str(budget))].groupby("C").BA.mean()
        C = float(candidates.idxmax())
        A, V = (arrays["OLI"][tr], arrays["OLI"][te]) if budget == "OLI" else (X, T)
        pos = np.arange(A.shape[1]) if budget in [360, "OLI"] else fullpath[:budget]
        sc, model = fit_lr(A, y, gids, pos, C)
        p = model.predict(sc.transform(V[:, pos]))
        weights = identity_weights(tid)
        labels = list(RESEARCHER_CATEGORIES)
        cm = confusion_matrix(z, p, labels=labels, sample_weight=weights)
        summaries.append(
            dict(
                fold=name,
                kind=kind,
                budget=str(budget),
                C=C,
                balanced_accuracy=ba(z, p, tid),
                test_IDs=len(np.unique(tid)),
                train_IDs=len(np.unique(gids)),
            )
        )
        for i, c in enumerate(labels):
            tp = cm[i, i]
            fn = cm[i].sum() - tp
            fp = cm[:, i].sum() - tp
            tn = cm.sum() - tp - fn - fp
            rates.append(
                dict(
                    fold=name,
                    kind=kind,
                    budget=str(budget),
                    researcher_category=c,
                    recall=tp / (tp + fn),
                    precision=tp / (tp + fp) if tp + fp else np.nan,
                    specificity=tn / (tn + fp),
                    FPR=fp / (tn + fp),
                    FNR=fn / (tp + fn),
                    target_IDs=int(test[test.label.eq(c)].GlobalID.nunique()),
                )
            )
            for j, d in enumerate(labels):
                confusions.append(
                    dict(
                        fold=name,
                        kind=kind,
                        budget=str(budget),
                        truth=c,
                        predicted=d,
                        identity_weighted_count=cm[i, j],
                    )
                )
        if budget in [360, "OLI"]:
            predictions.extend(
                dict(
                    fold=name,
                    kind=kind,
                    representation="NEON" if budget == 360 else "OLI",
                    GlobalID=gid,
                    year=int(year),
                    truth=true,
                    predicted=pr,
                )
                for gid, year, true, pr in zip(tid, test.year, z, p)
            )
            np.savez_compressed(
                directory / f"model_{budget}.npz",
                positions=pos,
                scaler_mean=sc.mean_,
                scaler_scale=sc.scale_,
                coef=model.coef_,
                intercept=model.intercept_,
                classes=model.classes_,
            )
    pd.DataFrame(summaries).to_csv(directory / "metrics.csv", index=False)
    pd.DataFrame(rates).to_csv(directory / "class_rates.csv", index=False)
    pd.DataFrame(confusions).to_csv(directory / "confusion.csv", index=False)
    pd.DataFrame(predictions).to_parquet(directory / "predictions.parquet", index=False)


def single_fold(t, arrays, waves, name, kind, tr, te, directory):
    rows = []
    class_rows = []
    train, test = t.loc[tr], t.loc[te]
    assert not set(train.GlobalID) & set(test.GlobalID)
    pd.concat([train.assign(role="train"), test.assign(role="test")]).drop(
        columns="flights"
    ).to_csv(directory / "memberships.csv", index=False)
    for sensor in ["NEON", "OLI"]:
        X, T = arrays[sensor][tr], arrays[sensor][te]
        for a, b in combinations(RESEARCHER_CATEGORIES, 2):
            ta = train.label.isin([a, b]).to_numpy()
            tb = test.label.isin([a, b]).to_numpy()
            if (
                min(train[ta].groupby("label").GlobalID.nunique()) < 10
                or min(test[tb].groupby("label").GlobalID.nunique()) < 3
            ):
                continue
            r = univariate_discrimination(
                X[ta],
                train.label.to_numpy()[ta] == a,
                train.GlobalID.to_numpy()[ta],
                T[tb],
                test.label.to_numpy()[tb] == a,
                test.GlobalID.to_numpy()[tb],
            )
            for j, w in enumerate(waves[sensor]):
                rows.append(
                    dict(
                        pair=a + " / " + b,
                        class_a=a,
                        class_b=b,
                        wavelength_nm=w,
                        sensor=sensor,
                        fold=name,
                        kind=kind,
                        train_IDs=train[ta].GlobalID.nunique(),
                        test_IDs=test[tb].GlobalID.nunique(),
                        **{k: v[j] for k, v in r.items()},
                    )
                )
        # Prespecified balanced-prior multiclass nearest-mean rule at each coordinate.
        means = np.array(
            [
                np.average(
                    X[train.label.eq(c)],
                    axis=0,
                    weights=identity_weights(train[train.label.eq(c)].GlobalID),
                )
                for c in RESEARCHER_CATEGORIES
            ]
        )
        pred = np.argmin((T[:, :, None] - means.T[None, :, :]) ** 2, axis=2)
        for i, c in enumerate(RESEARCHER_CATEGORIES):
            use = test.label.eq(c).to_numpy()
            weight = identity_weights(test[use].GlobalID)
            recall = np.average(pred[use] == i, axis=0, weights=weight)
            class_rows.extend(
                dict(
                    fold=name,
                    kind=kind,
                    sensor=sensor,
                    researcher_category=c,
                    wavelength_nm=w,
                    recall=recall[j],
                )
                for j, w in enumerate(waves[sensor])
            )
    pd.DataFrame(rows).to_parquet(directory / "single_wavelength.parquet", index=False)
    pd.DataFrame(class_rows).to_csv(
        directory / "single_wavelength_class_recall.csv", index=False
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t, arrays, waves, identity = load()
    identity.update(
        code=_file_hash(__file__),
        helper=_file_hash(REPO / "src/spectralbridge/researcher_information.py"),
        common=_file_hash(BASE / "common.py"),
    )
    inference(waves["NEON"])
    singles = []
    class_singles = []
    metrics = []
    rates = []
    cm = []
    pred = []
    selected = []
    foldlist = list(folds(t))
    for number, (name, kind, tr, te) in enumerate(foldlist, 1):
        LOG.info("Single-wavelength fold %s/%s %s", number, len(foldlist), name)
        d = checkpoint(
            "single/" + name,
            identity,
            lambda d: single_fold(t, arrays, waves, name, kind, tr, te, d),
        )
        singles.append(pd.read_parquet(d / "single_wavelength.parquet"))
        class_singles.append(pd.read_csv(d / "single_wavelength_class_recall.csv"))
        if kind in ["plant", "site"]:
            LOG.info("Nested complementary feature budgets: %s", name)
            d = checkpoint(
                "classification/" + name,
                identity,
                lambda d: classification_fold(t, arrays, waves, name, kind, tr, te, d),
            )
            for target, file in [
                (metrics, "metrics.csv"),
                (rates, "class_rates.csv"),
                (cm, "confusion.csv"),
            ]:
                target.append(pd.read_csv(d / file))
            pred.append(pd.read_parquet(d / "predictions.parquet"))
            path = pd.read_csv(d / "selected_path.csv")
            path["fold"] = name
            path["kind"] = kind
            selected.append(path)
    sw = pd.concat(singles, ignore_index=True)
    save(sw, "single_wavelength_discrimination.parquet")
    save(sw, "single_wavelength_discrimination.csv")
    save(
        pd.concat(class_singles, ignore_index=True),
        "single_wavelength_class_recall.csv",
    )
    for frame, name in [
        (pd.concat(metrics), "complementary_feature_performance.csv"),
        (pd.concat(rates), "class_specific_transfer.csv"),
        (pd.concat(cm), "confusion_matrices.csv"),
        (pd.concat(pred), "classification_predictions.parquet"),
        (pd.concat(selected), "complementary_selection.csv"),
    ]:
        save(frame, name)
    # Reuse already validated category-only whole-spectrum temporal class metrics.
    prior = pd.read_csv(
        REPO
        / "provenance/scientific-closure/2026-10-15/tables/all_class_detection_rates.csv"
    )
    save(
        prior[prior.scheme.eq("researcher_level")].drop(columns=["scheme"]),
        "reused_researcher_class_rates_all_domains.csv",
    )
    LOG.info("Atlas/classification experiments complete")


if __name__ == "__main__":
    main()
