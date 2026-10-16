"""Independent source, leakage, prediction, simplex and numerical audit."""

import json
import logging
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.researcher_information import (
    RESEARCHER_CATEGORIES,
    identity_weights,
    orthogonal_feature_path,
)
from common import BASE, REPO, CACHE, load, save


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t, arrays, waves, identity = load()
    # Check earlier permutation sources against their actual existing ledger.
    root = REPO / "artifacts/plant_spectral_atlas/researcher_pft_statistics"
    old = json.loads((root / "manifest.json").read_text())
    assert old["identity"]["source"] == identity["source_sha256"]
    for name, h in old["outputs"].items():
        if name == "method_comparison.csv" or (
            "flight_history" in name and name.endswith(".npz")
        ):
            assert _file_hash(root / name) == h, name
    checks = {"source_and_reused_permutation_hashes": True}
    previous = json.loads(
        (
            REPO
            / "provenance/scientific-closure/2026-10-15/manifests/final_evidence.json"
        ).read_text()
    )
    metadata_path = (
        "provenance/scientific-closure/2026-10-15/manifests/metadata_audit.json"
    )
    assert previous["source_parquet_sha256"] == identity["source_sha256"]
    assert _file_hash(REPO / metadata_path) == previous["files"][metadata_path]
    pixel_audit = json.loads((REPO / metadata_path).read_text())
    assert pixel_audit["source_pixel_keys_shared_by_distinct_IDs"] == 0
    checks["reused_exact_source_pixel_overlap_pairs_across_IDs"] = 0
    prior_root = REPO / "provenance/spectral-library-analytics/2026-10-14"
    prior = json.loads((prior_root / "evidence_manifest.json").read_text())
    for filename, expected_hash in prior["outputs"].items():
        assert _file_hash(prior_root / filename) == expected_hash, filename
    checks["prior_owned_analytics_outputs_unchanged"] = len(prior["outputs"])

    tables = BASE / "tables"
    a = pd.read_parquet(BASE / "researcher_pft_information_atlas.parquet")
    assert len(a) == 3600 and set(a.class_a) | set(a.class_b) == set(
        RESEARCHER_CATEGORIES
    )
    assert not a.duplicated(["pair", "wavelength_nm"]).any()
    assert not (
        ((a.wavelength_nm >= 1340) & (a.wavelength_nm <= 1450))
        | ((a.wavelength_nm >= 1790) & (a.wavelength_nm <= 2000))
    ).any()
    checks["atlas_complete_10_pairs_360_coordinates_no_gaps"] = True
    cases = 0
    selected_audit = []
    for directory in sorted((CACHE / "single").iterdir()):
        m = pd.read_csv(directory / "memberships.csv")
        assert not set(m[m.role.eq("train")].GlobalID) & set(
            m[m.role.eq("test")].GlobalID
        )
        if directory.name.startswith("site_"):
            assert (
                m[m.role.eq("train")]
                .site.ne(directory.name.removeprefix("site_"))
                .all()
            )
        if directory.name.startswith("paired_"):
            year = int(directory.name.split("_")[1].removeprefix("train"))
            assert m[m.role.eq("train")].year.eq(year).all()
        cases += 1
    checks["single_wavelength_whole_identity_disjoint_cases"] = cases
    train_cases = 0
    for directory in sorted((CACHE / "training_inference").glob("*/*")):
        ledger = json.loads((directory / "complete.json").read_text())
        for fname, h in ledger["outputs"].items():
            assert _file_hash(directory / fname) == h
        m = pd.read_csv(directory / "training_membership.csv")
        parent = pd.read_csv(
            CACHE / "single" / directory.parent.name / "memberships.csv"
        )
        assert set(m.GlobalID).issubset(set(parent[parent.role.eq("train")].GlobalID))
        assert not set(m.GlobalID) & set(parent[parent.role.eq("test")].GlobalID)
        assert m.GlobalID.nunique() == len(m)
        with np.load(directory / "null.npz") as null:
            p = (
                1
                + np.count_nonzero(
                    null["maxima"][:, None] >= abs(null["observed"])[None, :] - 1e-12,
                    axis=0,
                )
            ) / 2000
            np.testing.assert_allclose(p, null["p"], atol=1e-15)
        train_cases += 1
    checks["training_only_blocked_cases_verified"] = train_cases
    assert train_cases == 230
    class_support = []
    for directory in sorted((CACHE / "single").iterdir()):
        m = pd.read_csv(directory / "memberships.csv")
        for (role, label), g in m.groupby(["role", "label"]):
            class_support.append(
                dict(
                    fold=directory.name,
                    role=role,
                    researcher_category=label,
                    identities=g.GlobalID.nunique(),
                    annual_rows=len(g),
                )
            )
    save(pd.DataFrame(class_support), "fold_class_support.csv")

    predictions = pd.read_parquet(tables / "classification_predictions.parquet")
    for directory in sorted((CACHE / "classification").iterdir()):
        members = pd.read_csv(CACHE / "single" / directory.name / "memberships.csv")
        proper = members[members.role.eq("train")]
        ix = t.GlobalID.isin(proper.GlobalID) & t.year.isin(proper.year)
        X = arrays["NEON"][ix]
        y = t.loc[ix, "label"].to_numpy()
        ids = t.loc[ix, "GlobalID"].to_numpy()
        expected = pd.read_csv(directory / "selected_path.csv").column.to_numpy()
        np.testing.assert_array_equal(
            orthogonal_feature_path(X, y, 100, identity_weights(ids, y)), expected
        )
        inners = pd.read_csv(directory / "inner_membership.csv")
        for inner, g in inners.groupby("inner"):
            tr = set(g[g.role.eq("proper")].GlobalID)
            va = set(g[g.role.eq("validation")].GlobalID)
            assert not tr & va
            assert tr | va == set(ids)
            mask = np.isin(ids, list(tr))
            path = orthogonal_feature_path(
                X[mask], y[mask], 100, identity_weights(ids[mask], y[mask])
            )
            selected_audit.extend(
                dict(
                    fold=directory.name,
                    inner=int(inner),
                    rank=j + 1,
                    wavelength_nm=waves["NEON"][col],
                    training_IDs=len(tr),
                    validation_IDs=len(va),
                )
                for j, col in enumerate(path)
            )
        tuning = pd.read_csv(directory / "inner_tuning.csv")
        metrics = pd.read_csv(directory / "metrics.csv")
        for r in metrics.itertuples():
            best = (
                tuning[tuning.budget.astype(str).eq(str(r.budget))]
                .groupby("C")
                .BA.mean()
                .idxmax()
            )
            assert np.isclose(best, r.C)
        # Object label arrays are loaded only from our hash-verified own cache.
        ledger = json.loads((directory / "complete.json").read_text())
        for fname, expected_hash in ledger["outputs"].items():
            assert _file_hash(directory / fname) == expected_hash, fname
        for rep, budget in [("NEON", "360"), ("OLI", "OLI")]:
            p = predictions[
                predictions.fold.eq(directory.name) & predictions.representation.eq(rep)
            ]
            keys = pd.MultiIndex.from_frame(t[["GlobalID", "year"]])
            index = keys.get_indexer(pd.MultiIndex.from_frame(p[["GlobalID", "year"]]))
            with np.load(directory / f"model_{budget}.npz", allow_pickle=True) as model:
                features = arrays[rep][index][:, model["positions"]]
                score = (
                    (features - model["scaler_mean"]) / model["scaler_scale"]
                ) @ model["coef"].T + model["intercept"]
                got = model["classes"][np.argmax(score, axis=1)]
                np.testing.assert_array_equal(got, p.predicted)
    save(
        pd.DataFrame(selected_audit),
        "independently_reconstructed_inner_feature_paths.csv",
    )
    checks["nested_selection_and_saved_model_predictions_reproduced"] = True
    comparison = pd.read_parquet(tables / "abundance_model_comparison.parquet")
    assert set(comparison.researcher_category) == set(RESEARCHER_CATEGORIES)
    members = pd.read_csv(tables / "abundance_parent_memberships.csv")
    for fold, g in members.groupby("fold"):
        p = set(g[g.role.eq("proper")].GlobalID)
        v = set(g[g.role.eq("calibration")].GlobalID)
        te = set(g[~g.role.isin(["proper", "calibration"])].GlobalID)
        assert not p & v and not p & te and not v & te
        for _, r in g.groupby("role"):
            assert r.groupby("GlobalID").bundle.nunique().max() == 1
        if fold.startswith("site_"):
            assert t[t.GlobalID.isin(p | v)].site.ne(fold.removeprefix("site_")).all()
    checked = 0
    gate_metrics = []
    for r in pd.read_csv(tables / "abundance_case_index.csv").itertuples():
        pred = pd.read_parquet(REPO / r.predictions)
        truth = pd.read_parquet(REPO / r.truth)
        cols = ["pred_" + c for c in RESEARCHER_CATEGORIES]
        P = pred[cols].to_numpy()
        Y = truth[list(RESEARCHER_CATEGORIES)].to_numpy()
        assert len(P) == len(Y) and np.all(P >= -1e-10) and np.allclose(P.sum(1), 1)
        assert np.array_equal(pred.bundle, truth.bundle)
        for j, c in enumerate(RESEARCHER_CATEGORIES):
            saved = comparison[
                comparison.fold.eq(r.fold)
                & comparison.target.eq(r.target)
                & comparison.method.eq(r.method)
                & comparison.representation.eq(r.representation)
                & comparison.researcher_category.eq(c)
            ].iloc[0]
            np.testing.assert_allclose(
                np.sqrt(np.mean((P[:, j] - Y[:, j]) ** 2)), saved.RMSE, rtol=1e-12
            )
        if r.method == "Training prior":
            from spectralbridge.mixtures import mixture_truth

            prior = mixture_truth(
                np.eye(5),
                np.asarray(RESEARCHER_CATEGORIES),
                pairs_per_composition=1,
                seed=0,
            )["truth"].mean(0)
            np.testing.assert_allclose(P, np.tile(prior, (len(P), 1)), atol=1e-12)
        if r.method == "Two-stage":
            with np.load((REPO / r.predictions).parent / (r.target + ".npz")) as z:
                for j, c in enumerate(RESEARCHER_CATEGORIES):
                    actual = Y[:, j] > 0
                    gate = z["gate"][:, j]
                    prob = z["presence_probability"][:, j]
                    gate_metrics.append(
                        dict(
                            fold=r.fold,
                            kind=r.kind,
                            target=r.target,
                            representation=r.representation,
                            researcher_category=c,
                            stage_A_recall=gate[actual].mean(),
                            stage_A_FPR=gate[~actual].mean(),
                            stage_A_AUC=roc_auc_score(actual, prob),
                        )
                    )
        checked += 1
    save(pd.DataFrame(gate_metrics), "two_stage_presence_metrics.csv")
    oracle = pd.read_csv(tables / "oracle_solver_controls.csv")
    checks.update(
        abundance_cases_checked=checked,
        abundance_roles_disjoint=True,
        all_saved_predictions_compositions=True,
        fraction_RMSE_independently_reproduced=True,
        oracle_max_fraction_RMSE=float(oracle.fraction_RMSE.max()),
    )
    # Reproduce one single-coordinate AUC with the independent sklearn definition.
    d = CACHE / "single/plant_0"
    mem = pd.read_csv(d / "memberships.csv")
    tr = mem[mem.role.eq("train")]
    te = mem[mem.role.eq("test")]
    pair = RESEARCHER_CATEGORIES[:2]
    tr = tr[tr.label.isin(pair)]
    te = te[te.label.isin(pair)]
    ix = pd.MultiIndex.from_frame(t[["GlobalID", "year"]])
    aidx = ix.get_indexer(pd.MultiIndex.from_frame(tr[["GlobalID", "year"]]))
    bidx = ix.get_indexer(pd.MultiIndex.from_frame(te[["GlobalID", "year"]]))
    y = tr.label.eq(pair[0]).to_numpy()
    means = [
        np.average(
            arrays["NEON"][aidx[y == q], 0],
            weights=identity_weights(tr.GlobalID.to_numpy()[y == q]),
        )
        for q in [False, True]
    ]
    score = arrays["NEON"][bidx, 0] * np.sign(means[1] - means[0])
    auc = roc_auc_score(
        te.label.eq(pair[0]), score, sample_weight=identity_weights(te.GlobalID)
    )
    sw = pd.read_parquet(d / "single_wavelength.parquet")
    expected = sw[
        sw.sensor.eq("NEON") & sw.class_a.eq(pair[0]) & sw.class_b.eq(pair[1])
    ].AUC.iloc[0]
    np.testing.assert_allclose(auc, expected, atol=1e-12)
    checks["single_coordinate_AUC_independent_sklearn"] = True
    checks["status"] = "passed"
    (BASE / "numerical_validation.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
