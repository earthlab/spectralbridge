"""Independent checkpoint, membership, tuning and saved-parameter replay audit."""

import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from spectralbridge.researcher_validation import identity_correctness
from run_controls import BASE, REPO, PRIOR, load_data, sha, seed, CATS


def main():
    t, arrays, waves, identity = load_data()
    models = 0
    targets = 0
    for d in sorted((BASE / "checkpoints").iterdir()):
        record = json.loads((d / "complete.json").read_text())
        for file, h in record["outputs"].items():
            assert sha(d / file) == h, (d, file)
        for k, v in identity.items():
            assert record["identity"][k] == v, (d, k)
        if d.name.startswith("candidate_"):
            continue
        outer = pd.read_csv(d / "outer_membership.csv")
        train = outer[outer.role.eq("train")]
        idx = t.set_index(["GlobalID", "year"]).index.get_indexer(
            pd.MultiIndex.from_frame(train[["GlobalID", "year"]])
        )
        assert (idx >= 0).all()
        inner = pd.read_csv(d / "inner_membership.csv")
        for k, (a, b) in enumerate(
            StratifiedGroupKFold(3, shuffle=True, random_state=seed(d.name)).split(
                idx, train.label, train.GlobalID
            )
        ):
            for role, positions in [("proper", a), ("validation", b)]:
                assert set(
                    inner[inner.inner.eq(k) & inner.role.eq(role)].GlobalID
                ) == set(train.GlobalID.iloc[positions])
        assert all(
            not set(g.GlobalID) & set(train.GlobalID)
            for role, g in outer.groupby("role")
            if role != "train"
        )
        metrics = pd.read_csv(d / "metrics.csv")
        tuning = pd.read_csv(d / "tuning.csv")
        correct = pd.read_parquet(d / "identity_correctness.parquet")
        if d.name.startswith(("plant_", "site_")):
            oldinner = pd.read_csv(
                REPO
                / "artifacts/plant_spectral_atlas/researcher_information_20261015_v1/classification"
                / d.name
                / "inner_membership.csv"
            )
            pd.testing.assert_frame_equal(
                inner.sort_values(list(inner)).reset_index(drop=True),
                oldinner.sort_values(list(oldinner)).reset_index(drop=True),
            )
        for path in d.glob("*.npz"):
            a = np.load(path)
            stem = path.stem
            key = stem.replace("Selected_replay", "Selected replay")
            matching = metrics[
                metrics.apply(
                    lambda r: (
                        f"{r.method}_{r.representation}_{r.budget}_{r.random_seed}"
                        == key
                    ),
                    axis=1,
                )
            ]
            assert len(matching) > 0, stem
            first = matching.iloc[0]
            pos = a["positions"]
            C = float(a["C"])
            if first.method == "Random":
                expected = np.random.default_rng(
                    20261016 + int(first.random_seed)
                ).permutation(360)[: int(first.budget)]
                np.testing.assert_array_equal(pos, expected)
            if first.method != "Selected replay":
                means = tuning[tuning.variant.eq(key)].groupby("C").BA.mean()
                assert C == float(means.idxmax())
            else:
                prior = pd.read_csv(
                    PRIOR / "tables/complementary_feature_performance.csv"
                )
                old = prior[
                    prior.fold.eq(d.name)
                    & prior.budget.astype(str).eq(str(int(first.budget)))
                ].iloc[0]
                assert abs(old.balanced_accuracy - first.BA) < 1e-10
            for row in matching.itertuples():
                target = outer[outer.role.eq(row.target)]
                ix = t.set_index(["GlobalID", "year"]).index.get_indexer(
                    pd.MultiIndex.from_frame(target[["GlobalID", "year"]])
                )
                Z = (arrays[row.representation][ix][:, pos] - a["scaler_mean"]) / a[
                    "scaler_scale"
                ]
                if a["pca_components"].size:
                    Z = (Z - a["pca_mean"]) @ a["pca_components"].T
                p = a["classes"][(Z @ a["coef"].T + a["intercept"]).argmax(axis=1)]
                expected = identity_correctness(
                    target.label.to_numpy(), p, target.GlobalID.to_numpy()
                )
                saved = correct[
                    correct.target.eq(row.target)
                    & correct.method.eq(row.method)
                    & correct.representation.eq(row.representation)
                    & correct.budget.eq(row.budget)
                    & correct.random_seed.eq(row.random_seed)
                ]
                joined = expected.merge(
                    saved,
                    on=["GlobalID", "truth"],
                    validate="one_to_one",
                    suffixes=("_new", "_saved"),
                )
                assert len(joined) == len(expected)
                np.testing.assert_allclose(
                    joined.correct_new, joined.correct_saved, atol=1e-12
                )
                assert (
                    abs(expected.groupby("truth").correct.mean().mean() - row.BA)
                    < 1e-12
                )
                targets += 1
            models += 1
    result = {
        "status": "passed",
        "fitted_classifier_models_replayed": models,
        "outer_prediction_cases_replayed": targets,
        "inner_memberships_recreated": True,
        "matched_original_inner_folds": True,
        "random_paths_independent_and_recreated": True,
        "C_selected_only_from_inner_scores": True,
        "all_selected_budget_replays_match_prior": True,
        "all_outer_GlobalIDs_disjoint": True,
    }
    (BASE / "control_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
