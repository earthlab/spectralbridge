"""Matched nested random/PCA controls and identity-disjoint temporal recognition."""

from pathlib import Path
import hashlib
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
from spectralbridge.researcher_information import (
    RESEARCHER_CATEGORIES,
    identity_weights,
)
from spectralbridge.researcher_validation import (
    random_feature_path,
    balanced_accuracy,
    identity_correctness,
)
from spectralbridge.mesma_readiness import load_compact_inputs

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
PRIOR = REPO / "provenance/researcher-pft-information/2026-10-15/v1"
sys.path.insert(0, str(PRIOR))
from common import folds, seed  # noqa: E402

LOG = logging.getLogger("controls")
BUDGETS = [1, 2, 3, 5, 7, 10, 20, 50, 100]
CVALUES = [0.1, 1.0, 10.0]
CATS = list(RESEARCHER_CATEGORIES)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_data():
    source = REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    compact = REPO / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact"
    ledger = json.loads((compact.parent / "statistics_manifest.json").read_text())
    assert sha(source) == ledger["identity"]["source"]
    for name in [
        "compact/corr_polygon_year.parquet",
        "compact/olioli_undarkened_polygon_year.parquet",
    ]:
        assert sha(compact.parent / name) == ledger["outputs"][name]
    t, arrays, waves = load_compact_inputs(
        source, compact, include_historical_labels=False
    )
    t = t[
        ["GlobalID", "site", "year", "flight_history", "cover_category", "flights"]
    ].copy()
    t["label"] = t.cover_category
    assert set(t.label) == set(CATS)
    assert all(np.isfinite(a).all() for a in arrays.values())
    identity = {
        "source_sha256": sha(source),
        "compact_manifest_sha256": sha(compact.parent / "statistics_manifest.json"),
        "code_sha256": sha(__file__),
        "helper_sha256": sha(REPO / "src/spectralbridge/researcher_validation.py"),
        "protocol_sha256": sha(BASE / "DESIGN.md"),
        "prior_common_sha256": sha(PRIOR / "common.py"),
    }
    return t, arrays, waves, identity


def fit_transform(X, weights, positions, components=None):
    scaler = StandardScaler().fit(X[:, positions], sample_weight=weights)
    A = scaler.transform(X[:, positions])
    pca = PCA(n_components=components, svd_solver="full").fit(A) if components else None
    return scaler, pca, pca.transform(A) if pca else A


def transform(X, pos, scaler, pca):
    A = scaler.transform(X[:, pos])
    return pca.transform(A) if pca else A


def model_fit(A, y, weights, C):
    return LogisticRegression(C=C, max_iter=1500, solver="lbfgs").fit(
        A, y, sample_weight=weights
    )


def checkpoint(name, identity, action):
    d = BASE / "checkpoints" / name
    d.mkdir(parents=True, exist_ok=True)
    manifest = d / "complete.json"
    if manifest.exists():
        record = json.loads(manifest.read_text())
        assert record["identity"] == identity, name
        for f, h in record["outputs"].items():
            assert sha(d / f) == h, (name, f)
        LOG.info("Reuse %s", name)
        return d
    action(d)
    record = {
        "identity": identity,
        "outputs": {
            str(p.relative_to(d)): sha(p)
            for p in d.rglob("*")
            if p.is_file() and p != manifest
        },
    }
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    return d


def evaluate(t, arrays, tr, targets, name, kind, variants, d):
    train = t.loc[tr]
    ids = train.GlobalID.to_numpy()
    y = train.label.to_numpy()
    cv = list(
        StratifiedGroupKFold(3, shuffle=True, random_state=seed(name)).split(
            arrays["NEON"][tr], y, ids
        )
    )
    member = []
    for k, (a, b) in enumerate(cv):
        assert not set(ids[a]) & set(ids[b])
        for role, ix in [("proper", a), ("validation", b)]:
            member.extend(
                dict(inner=k, role=role, GlobalID=g) for g in np.unique(ids[ix])
            )
    pd.DataFrame(member).to_csv(d / "inner_membership.csv", index=False)
    pd.concat(
        [
            train.assign(role="train"),
            *[t.loc[te].assign(role=target) for target, te in targets],
        ]
    ).drop(columns="flights").to_csv(d / "outer_membership.csv", index=False)
    tuning = []
    metrics = []
    correct = []
    rates = []
    conf = []
    paths = []
    for method, rep, budget, random_seed, components in variants:
        X = arrays[rep][tr]
        if method == "Random":
            path = random_feature_path(X.shape[1], 20261016 + random_seed)
            pos = path[:budget]
        elif method == "Selected replay":
            old = pd.read_csv(
                REPO
                / "artifacts/plant_spectral_atlas/researcher_information_20261015_v1/classification"
                / name
                / "selected_path.csv"
            )
            pos = old.column.to_numpy()[:budget]
        else:
            pos = np.arange(X.shape[1])
        key = f"{method}_{rep}_{budget}_{random_seed}"
        paths.extend(
            dict(variant=key, rank=j + 1, column=int(v)) for j, v in enumerate(pos)
        )
        local = []
        if method == "Selected replay":
            old = pd.read_csv(
                REPO
                / "artifacts/plant_spectral_atlas/researcher_information_20261015_v1/classification"
                / name
                / "metrics.csv"
            )
            chosen = float(old[old.budget.astype(str).eq(str(budget))].C.iloc[0])
        else:
            for k, (a, b) in enumerate(cv):
                weights = identity_weights(ids[a], y[a])
                sc, pc, A = fit_transform(X[a], weights, pos, components)
                V = transform(X[b], pos, sc, pc)
                for C in CVALUES:
                    model = model_fit(A, y[a], weights, C)
                    score = balanced_accuracy(y[b], model.predict(V), ids[b])
                    row = dict(variant=key, inner=k, C=C, BA=score)
                    local.append(row)
                    tuning.append(row)
            means = pd.DataFrame(local).groupby("C").BA.mean()
            chosen = float(means.idxmax())
        weights = identity_weights(ids, y)
        sc, pc, A = fit_transform(X, weights, pos, components)
        model = model_fit(A, y, weights, chosen)
        np.savez_compressed(
            d / (key.replace(" ", "_") + ".npz"),
            positions=pos,
            scaler_mean=sc.mean_,
            scaler_scale=sc.scale_,
            pca_components=pc.components_ if pc else np.empty((0, 0)),
            pca_mean=pc.mean_ if pc else np.empty(0),
            coef=model.coef_,
            intercept=model.intercept_,
            classes=model.classes_.astype(str),
            C=chosen,
        )
        for target, te in targets:
            test = t.loc[te]
            z = test.label.to_numpy()
            tid = test.GlobalID.to_numpy()
            assert not set(ids) & set(tid)
            pred = model.predict(transform(arrays[rep][te], pos, sc, pc))
            meta = dict(
                fold=name,
                kind=kind,
                target=target,
                method=method,
                representation=rep,
                budget=budget,
                random_seed=random_seed,
                C=chosen,
            )
            metrics.append(
                dict(
                    **meta,
                    BA=balanced_accuracy(z, pred, tid),
                    train_IDs=len(np.unique(ids)),
                    test_IDs=len(np.unique(tid)),
                )
            )
            contribution = identity_correctness(z, pred, tid)
            for col, val in meta.items():
                contribution[col] = val
            correct.append(contribution)
            cm = confusion_matrix(
                z, pred, labels=CATS, sample_weight=identity_weights(tid)
            )
            for i, c in enumerate(CATS):
                tp = cm[i, i]
                fn = cm[i].sum() - tp
                fp = cm[:, i].sum() - tp
                tn = cm.sum() - tp - fn - fp
                rates.append(
                    dict(
                        **meta,
                        researcher_category=c,
                        recall=tp / (tp + fn),
                        precision=tp / (tp + fp) if tp + fp else np.nan,
                        FPR=fp / (tn + fp),
                        FNR=fn / (tp + fn),
                    )
                )
                for j, other in enumerate(CATS):
                    conf.append(
                        dict(
                            **meta,
                            truth=c,
                            predicted=other,
                            identity_weighted_count=cm[i, j],
                        )
                    )
        LOG.info("%s %s completed", name, key)
    for f, file in [
        (pd.DataFrame(metrics), "metrics.csv"),
        (pd.DataFrame(tuning), "tuning.csv"),
        (pd.DataFrame(rates), "rates.csv"),
        (pd.DataFrame(conf), "confusions.csv"),
        (pd.DataFrame(paths), "features.csv"),
    ]:
        f.to_csv(d / file, index=False)
    pd.concat(correct, ignore_index=True).to_parquet(
        d / "identity_correctness.parquet", index=False
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t, arrays, waves, identity = load_data()
    jobs = []
    temporal = {}
    for name, kind, tr, te in folds(t):
        if kind in ["plant", "site"]:
            variants = [
                ("Random", "NEON", b, s, None) for s in range(5) for b in BUDGETS
            ]
            variants += [("Selected replay", "NEON", b, -1, None) for b in BUDGETS]
            variants += [("PCA", "NEON", n, -1, n) for n in [20, 50]]
            jobs.append((name, kind, tr, [("target", te)], variants))
        elif kind == "year":
            temporal[name] = (kind, tr, [(name, te)])
        elif kind == "paired_year":
            trainyear = name.split("_")[1]
            fold = name.rsplit("_", 1)[1]
            key = "paired_" + trainyear + "_" + fold
            if key not in temporal:
                temporal[key] = (kind, tr, [])
            temporal[key][2].append((name, te))
    for name, (kind, tr, targets) in temporal.items():
        jobs.append(
            (
                name,
                kind,
                tr,
                targets,
                [("Full", "NEON", 360, -1, None), ("Full", "OLI", 7, -1, None)],
            )
        )

    def run(job):
        name, kind, tr, targets, variants = job
        return checkpoint(
            name,
            identity,
            lambda d: evaluate(t, arrays, tr, targets, name, kind, variants, d),
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        directories = list(pool.map(run, jobs))
    (BASE / "tables").mkdir(exist_ok=True)
    for filename in ["metrics.csv", "rates.csv", "confusions.csv"]:
        pd.concat(
            [pd.read_csv(d / filename) for d in directories], ignore_index=True
        ).to_csv(BASE / "tables" / filename, index=False)
    pd.concat(
        [pd.read_parquet(d / "identity_correctness.parquet") for d in directories],
        ignore_index=True,
    ).to_parquet(BASE / "tables/identity_correctness.parquet", index=False)
    (BASE / "input_identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    LOG.info("All %s controlled training cases complete", len(jobs))


if __name__ == "__main__":
    main()
