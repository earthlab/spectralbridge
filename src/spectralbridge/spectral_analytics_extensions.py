"""Training-confined prototype, domain and withheld-class diagnostics.

Experimental audit outputs; no operational classification or purity guarantee.
"""

from pathlib import Path
import json
import logging
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from .spectral_learning import (
    LearningConfig,
    outer_folds,
    class_prototypes,
    classification_metrics,
    fit_training_model,
    probabilities,
    fit_novelty_space,
    novelty_scores,
    conformal_threshold,
)
from .spectral_library_analytics import (
    SCHEMES,
    load_analytics_inputs,
    scheme_data,
    prepare_fold,
    stable_seed,
)
from .plant_spectral_atlas import _file_hash
from .bulk.provenance import write_json_atomic

LOG = logging.getLogger(__name__)


def checkpoint(directory, identity, action):
    """Publish a stage ledger last; reject altered completed outputs."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    ledger = directory / "manifest.json"
    if ledger.exists():
        saved = json.loads(ledger.read_text())
        if saved["identity"] != identity:
            raise ValueError("Different extension configuration: " + str(directory))
        if not all(
            (directory / p).exists() and _file_hash(directory / p) == h
            for p, h in saved["outputs"].items()
        ):
            raise ValueError("Altered extension output: " + str(directory))
        return directory
    action(directory)
    outputs = {
        str(p.relative_to(directory)): _file_hash(p)
        for p in sorted(directory.rglob("*"))
        if p.is_file() and p != ledger
    }
    write_json_atomic(ledger, dict(identity=identity, outputs=outputs))
    return directory


def novelty_threshold(scores, identities, quantile=0.95):
    """Known-only higher empirical quantile of whole-identity maxima."""
    if not 0 < quantile < 1:
        raise ValueError("Quantile must be in (0,1)")
    frame = pd.DataFrame(dict(score=scores, identity=identities))
    if not np.isfinite(frame.score).all() or not len(frame):
        raise ValueError("Finite nonempty calibration scores required")
    return float(
        frame.groupby("identity").score.max().quantile(quantile, interpolation="higher")
    )


def unknown_metrics(is_unknown, scores, threshold):
    """Unknown precision/recall and known rejection at a prechosen threshold."""
    truth, scores = np.asarray(is_unknown, bool), np.asarray(scores, float)
    if truth.shape != scores.shape or not truth.any() or truth.all():
        raise ValueError("Both known and unknown aligned targets required")
    rejected = scores > threshold
    tp = int(np.sum(truth & rejected))
    return dict(
        unknown_recall=float(rejected[truth].mean()),
        known_false_rejection=float(rejected[~truth].mean()),
        unknown_precision=tp / int(rejected.sum()) if rejected.any() else np.nan,
        unknown_average_precision=float(average_precision_score(truth, scores)),
        unknown_prevalence=float(truth.mean()),
        threshold=float(threshold),
        known_rows=int((~truth).sum()),
        unknown_rows=int(truth.sum()),
    )


def safe_novelty_scores(values, training, space):
    """Keep zero selected-band spectra for distance/PCA; angle is undefined."""
    X, T = np.asarray(values, float), np.asarray(training, float)
    goodX = np.linalg.norm(X, axis=1) > 0
    goodT = np.linalg.norm(T, axis=1) > 0
    angle = np.full(len(X), np.nan)
    if goodX.any() and goodT.any():
        angle[goodX] = novelty_scores(X[goodX], T[goodT], space)["nearest_angle_deg"]
    scaler, pca = space
    Z = scaler.transform(X)
    scores = pca.transform(Z)
    return dict(
        nearest_angle_deg=angle,
        nearest_RMSE=cdist(X, T).min(1) / np.sqrt(X.shape[1]),
        PCA_radius=np.sqrt(
            np.sum(scores**2 / np.maximum(pca.explained_variance_, 1e-12), axis=1)
        ),
        PCA_residual=np.sqrt(np.mean((Z - pca.inverse_transform(scores)) ** 2, axis=1)),
    )


def run_extensions(source, compact, root, *, config=None):
    """Run declared secondary comparisons with per-fold restart checkpoints."""
    root = Path(root)
    config = config or LearningConfig()
    table, arrays, waves, actual, identity = load_analytics_inputs(
        source, compact, root
    )
    identity = dict(
        source_sha256=identity["source_sha256"],
        seed=config.seed,
        code_sha256=_file_hash(Path(__file__)),
    )
    base = root / "extensions"
    dirs = []
    for scheme, field in SCHEMES.items():
        t, a = scheme_data(table, arrays, field)
        for fold, kind, train, test in outer_folds(t, config):
            if kind not in {"plant", "site", "year"}:
                continue
            prepared, support, status = prepare_fold(
                t, a, actual, fold, kind, train, test, config
            )
            if prepared is None:
                continue
            context = dict(scheme=scheme, fold=fold, kind=kind)

            def action(directory):
                rows, members, unknown, unknown_rows, unknown_members = (
                    [],
                    [],
                    [],
                    [],
                    [],
                )
                pi, ci, ti = [prepared[k] for k in ["proper", "calibration", "test"]]
                # One earliest available proper-training observation per identity.
                candidates = (
                    t.iloc[pi]
                    .sort_values(["GlobalID", "year"])
                    .drop_duplicates("GlobalID")
                    .index.to_numpy()
                )
                for rep, sensor, k in [
                    ("NEON_full", "NEON", "all"),
                    ("NEON_k7", "NEON", 7),
                    ("OLI", "OLI", "all"),
                ]:
                    X = a[sensor]
                    # Primary selector fitted only on the same proper training.
                    from .spectral_learning import StableFSelector

                    selector = StableFSelector(k).fit(X[pi], t.label.iloc[pi])
                    positions = selector.selected_
                    scaler = StandardScaler().fit(X[pi][:, positions])
                    Z = scaler.transform(X[:, positions])
                    y = t.label.to_numpy()
                    classes = np.unique(y[pi])
                    for method in [
                        "mean",
                        "median",
                        "medoid",
                        "cluster_medoid",
                        "diversity",
                    ]:
                        counts = (
                            [1]
                            if method in {"mean", "median", "medoid"}
                            else [1, 2, 5, 10, 20, 50]
                        )
                        for count in counts:
                            common = dict(
                                **context,
                                representation=rep,
                                method=method,
                                prototypes_per_class=count,
                            )
                            if (
                                t.iloc[candidates]
                                .groupby("label")
                                .GlobalID.nunique()
                                .min()
                                < count
                            ):
                                rows.append(
                                    dict(
                                        **common,
                                        status="insufficient_independent_candidates",
                                    )
                                )
                                continue
                            P, labels, source_ix = class_prototypes(
                                Z[candidates],
                                y[candidates],
                                t.GlobalID.iloc[candidates],
                                method=method,
                                count=count,
                                seed=prepared["seed"],
                            )
                            dist = cdist(Z[ti], P) / np.sqrt(len(positions))
                            pred = labels[dist.argmin(1)]
                            proba = np.zeros((len(ti), len(classes)))
                            for j, c in enumerate(classes):
                                proba[:, j] = pred == c
                            metrics, _, _, _ = classification_metrics(
                                y[ti], proba, classes
                            )
                            rows.append(
                                dict(
                                    **common,
                                    status="evaluated",
                                    balanced_accuracy=metrics["balanced_accuracy"],
                                    macro_F1=metrics["macro_F1"],
                                    heldout_scaled_RMSE=float(dist.min(1).mean()),
                                    test_rows=len(ti),
                                    test_identities=t.GlobalID.iloc[ti].nunique(),
                                )
                            )
                            for label, ix in zip(labels, source_ix):
                                members.append(
                                    dict(
                                        **common,
                                        label=label,
                                        source_GlobalID=t.GlobalID.iloc[candidates[ix]]
                                        if ix >= 0
                                        else None,
                                        source_year=int(t.year.iloc[candidates[ix]])
                                        if ix >= 0
                                        else None,
                                        synthesized_center=ix < 0,
                                    )
                                )
                    if not len(ci):
                        unknown.append(
                            dict(
                                **context,
                                representation=rep,
                                status="no_independent_calibration",
                            )
                        )
                        continue
                    if kind != "plant":
                        continue  # Withheld-class challenge complements spatial/temporal closed-set tests.
                    for omitted in classes:
                        proper = pi[y[pi] != omitted]
                        cal = ci[y[ci] != omitted]
                        if (
                            len(np.unique(y[proper])) < 2
                            or len(cal) < 10
                            or not np.any(y[ti] == omitted)
                            or np.all(y[ti] == omitted)
                        ):
                            unknown.append(
                                dict(
                                    **context,
                                    representation=rep,
                                    omitted_class=omitted,
                                    status="insufficient_withheld_class_support",
                                )
                            )
                            continue
                        model, fit = fit_training_model(
                            X[proper],
                            y[proper],
                            t.GlobalID.iloc[proper],
                            "logistic",
                            k=k,
                            seed=prepared["seed"],
                        )
                        selected = model["select"].selected_
                        space = fit_novelty_space(X[proper][:, selected])
                        scores_cal = safe_novelty_scores(
                            X[cal][:, selected], X[proper][:, selected], space
                        )
                        scores_test = safe_novelty_scores(
                            X[ti][:, selected], X[proper][:, selected], space
                        )
                        pc, pt = (
                            probabilities(model, X[cal]),
                            probabilities(model, X[ti]),
                        )
                        scores_cal["one_minus_confidence"] = 1 - pc.max(1)
                        scores_test["one_minus_confidence"] = 1 - pt.max(1)
                        enc = np.array(
                            [np.where(model.classes_ == v)[0][0] for v in y[cal]]
                        )
                        conformal_q = conformal_threshold(
                            pc, enc, t.GlobalID.iloc[cal], 0.1
                        )
                        scores_cal["empty_conformal_set"] = (
                            ((1 - pc) > conformal_q).all(1).astype(float)
                        )
                        scores_test["empty_conformal_set"] = (
                            ((1 - pt) > conformal_q).all(1).astype(float)
                        )
                        for score_name, score in scores_test.items():
                            threshold = (
                                0.5
                                if score_name == "empty_conformal_set"
                                else novelty_threshold(
                                    scores_cal[score_name][
                                        np.isfinite(scores_cal[score_name])
                                    ],
                                    t.GlobalID.iloc[cal].to_numpy()[
                                        np.isfinite(scores_cal[score_name])
                                    ],
                                )
                            )
                            valid = np.isfinite(score)
                            result = unknown_metrics(
                                (y[ti] == omitted)[valid], score[valid], threshold
                            )
                            result["undefined_score_rows"] = int((~valid).sum())
                            unknown.append(
                                dict(
                                    **context,
                                    representation=rep,
                                    omitted_class=omitted,
                                    detector=score_name,
                                    status="evaluated",
                                    **result,
                                )
                            )
                            for i, value in zip(ti, score):
                                unknown_rows.append(
                                    dict(
                                        **context,
                                        representation=rep,
                                        omitted_class=omitted,
                                        detector=score_name,
                                        GlobalID=t.GlobalID.iloc[i],
                                        year=int(t.year.iloc[i]),
                                        truth_label=y[i],
                                        is_unknown=y[i] == omitted,
                                        score=float(value),
                                        threshold=threshold,
                                    )
                                )
                        for role, indices in [
                            ("proper_training", proper),
                            ("known_calibration", cal),
                            ("outer_test", ti),
                        ]:
                            for i in indices:
                                unknown_members.append(
                                    dict(
                                        **context,
                                        representation=rep,
                                        omitted_class=omitted,
                                        GlobalID=t.GlobalID.iloc[i],
                                        year=int(t.year.iloc[i]),
                                        label=y[i],
                                        role=role,
                                    )
                                )
                pd.DataFrame(rows).to_csv(directory / "prototypes.csv", index=False)
                pd.DataFrame(members).to_csv(
                    directory / "prototype_memberships.csv", index=False
                )
                pd.DataFrame(unknown).to_csv(directory / "unknown.csv", index=False)
                pd.DataFrame(unknown_rows).to_parquet(
                    directory / "unknown_predictions.parquet", index=False
                )
                pd.DataFrame(unknown_members).to_parquet(
                    directory / "unknown_memberships.parquet", index=False
                )

            LOG.info("Prototype/unknown %s %s", scheme, fold)
            dirs.append(checkpoint(base / f"{scheme}_{fold}", identity, action))
    for name in ["prototypes", "prototype_memberships", "unknown"]:
        frames = [
            pd.read_csv(d / f"{name}.csv")
            for d in dirs
            if (d / f"{name}.csv").stat().st_size > 2
        ]
        pd.concat(frames, ignore_index=True).to_csv(root / f"{name}.csv", index=False)
    return dirs


def run_domains(source, compact, root, *, config=None):
    """Predict observational domains on held-out identities, not instrument causes."""
    config = config or LearningConfig()
    root = Path(root)
    table, arrays, waves, actual, metadata = load_analytics_inputs(
        source, compact, root
    )
    identity = dict(
        source_sha256=metadata["source_sha256"],
        seed=config.seed,
        code_sha256=_file_hash(Path(__file__)),
        experiment="domains_fixed_logistic_C1",
    )

    def action(directory):
        results, predictions, membership = [], [], []
        domains = [
            ("site", table, arrays, table.site),
            ("year_all_sites", table, arrays, table.year.astype(str)),
        ]
        niwo = table.site.eq("NIWO").to_numpy()
        domains.append(
            (
                "year_within_NIWO",
                table.loc[niwo].reset_index(drop=True),
                {s: a[niwo] for s, a in arrays.items()},
                table.year[niwo].astype(str).reset_index(drop=True),
            )
        )
        flight = actual["NEON"].index.to_frame(index=False)
        flight = flight.merge(
            table[["GlobalID", "site"]].drop_duplicates(),
            on="GlobalID",
            validate="many_to_one",
        )
        flight_arrays = {s: a.to_numpy(float) for s, a in actual.items()}
        domains.append(("acquisition", flight, flight_arrays, flight.flight_id))
        for domain, t, a, labels in domains:
            y, ids = np.asarray(labels), t.GlobalID.to_numpy()
            # Domain labels may legitimately vary within a repeated identity.
            cv = StratifiedGroupKFold(3, shuffle=True, random_state=config.seed)
            for fold, (tr, te) in enumerate(cv.split(a["NEON"], y, ids)):
                if set(ids[tr]) & set(ids[te]):
                    raise ValueError("Leaking domain identities")
                support = (
                    pd.DataFrame(dict(id=ids[tr], label=y[tr]))
                    .groupby("label")
                    .id.nunique()
                )
                classes = support[support >= config.minimum_train].index.to_numpy()
                tr = tr[np.isin(y[tr], classes)]
                te = te[np.isin(y[te], classes)]
                if len(classes) < 2 or not len(te):
                    results.append(
                        dict(domain=domain, fold=fold, status="insufficient_support")
                    )
                    continue
                for sensor in ["NEON", "OLI"]:
                    model, fit = fit_training_model(
                        a[sensor][tr],
                        y[tr],
                        ids[tr],
                        "logistic",
                        seed=stable_seed(domain + str(fold)),
                        tune=False,
                        allow_repeated_identity_labels=True,
                    )
                    p = probabilities(model, a[sensor][te])
                    metrics, perclass, matrix, reliability = classification_metrics(
                        y[te], p, model.classes_
                    )
                    from .spectral_learning import cluster_bootstrap_accuracy

                    pred = model.classes_[p.argmax(1)]
                    draws = cluster_bootstrap_accuracy(
                        y[te],
                        pred,
                        ids[te],
                        model.classes_,
                        replicates=config.bootstraps,
                        seed=config.seed,
                        stratify=False,
                    )
                    results.append(
                        dict(
                            domain=domain,
                            fold=fold,
                            sensor=sensor,
                            status="evaluated_fixed_C1",
                            classes=len(classes),
                            train_identities=len(set(ids[tr])),
                            test_identities=len(set(ids[te])),
                            **metrics,
                            BA_low=np.quantile(draws, 0.025),
                            BA_high=np.quantile(draws, 0.975),
                        )
                    )
                    predictions.extend(
                        dict(
                            domain=domain,
                            fold=fold,
                            sensor=sensor,
                            GlobalID=ids[i],
                            truth=y[i],
                            predicted=pred[j],
                        )
                        for j, i in enumerate(te)
                    )
                membership.extend(
                    dict(
                        domain=domain, fold=fold, GlobalID=ids[i], label=y[i], role=role
                    )
                    for role, ix in [("train", tr), ("test", te)]
                    for i in ix
                )
                LOG.info("Domain %s fold %s complete", domain, fold)
        pd.DataFrame(results).to_csv(directory / "domain_performance.csv", index=False)
        pd.DataFrame(predictions).to_parquet(
            directory / "domain_predictions.parquet", index=False
        )
        pd.DataFrame(membership).to_parquet(
            directory / "domain_memberships.parquet", index=False
        )

    return checkpoint(root / "domains", identity, action)
