"""Small synthetic contracts for reusable methods; never rerun the library study."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
from spectralbridge import library_analysis as a  # noqa: E402


def fixture():
    rng = np.random.default_rng(4)
    ids = np.repeat(np.arange(36), 2)
    y = np.where(ids % 2, "B", "A")
    x = rng.normal(0, 0.12, (72, 6)) + (y == "B")[:, None] * np.array(
        [2, 0, 1, 0, 0, 0]
    )
    sites = np.repeat(np.array(["S0", "S1", "S2"])[(np.arange(36) // 2) % 3], 2)
    return x, y, ids, sites


def test_separability_synchronized_family_and_identity_aggregation():
    x, y, ids, _ = fixture()
    w = np.arange(500, 506.0)
    r = a.spectral_separability(
        x, y, w, ids, permutations=39, regions={"visible": (500, 505)}
    )
    assert r["pairs"].n_first.tolist() == [18]
    assert r["pairs"].p_max.iloc[0] <= 0.05
    assert (r["wavelengths"].p_adjusted >= r["wavelengths"].p_max).all()
    assert r["wavelengths"].signed_effect.iloc[0] > 1.5
    assert len(r["regions"]) == 1
    means = np.array([x[ids == i].mean(0) for i in np.unique(ids)])
    direct = a.spectral_separability(means, y[::2], w, permutations=39)
    pd.testing.assert_frame_equal(r["pairs"], direct["pairs"])
    pd.testing.assert_frame_equal(r["wavelengths"], direct["wavelengths"])
    swapped = a.spectral_separability(
        x, np.where(y == "A", "B", "A"), w, ids, permutations=39
    )
    np.testing.assert_allclose(
        swapped["wavelengths"].signed_effect, -r["wavelengths"].signed_effect
    )


def test_separability_masks_missing_wavelength_and_multipair():
    x, y, ids, _ = fixture()
    x[:, 3] = np.nan
    mask = np.ones(6, bool)
    mask[3] = False
    r = a.spectral_separability(x, y, np.arange(6.0), ids, mask=mask, permutations=19)
    assert 3 not in r["retained_columns"]
    with pytest.raises(ValueError, match="finite supported"):
        a.spectral_separability(x, y, np.arange(6.0), ids, permutations=19)
    r2 = a.spectral_separability(
        x, y, np.arange(6.0), ids, missing="drop_columns", permutations=19
    )
    np.testing.assert_array_equal(r["retained_columns"], r2["retained_columns"])
    with pytest.raises(ValueError, match="increasing"):
        a.spectral_separability(x, y, np.arange(6.0)[::-1], ids)
    with pytest.raises(ValueError, match="constant label"):
        a.spectral_separability(np.nan_to_num(x), y, np.arange(6.0), np.zeros(len(x)))
    xx = np.nan_to_num(x)
    yy = np.where(ids < 12, "C", y)
    out = a.spectral_separability(xx, yy, np.arange(6.0), ids, permutations=19)
    assert len(out["pairs"]) == 3
    np.testing.assert_allclose(
        out["wavelengths"].p_adjusted, np.minimum(1, 3 * out["wavelengths"].p_max)
    )


def assert_disjoint(result):
    for _, fold in result["memberships"].groupby("fold"):
        assert set(fold[fold.role == "train"].identity).isdisjoint(
            fold[fold.role == "test"].identity
        )
    for params in result["hyperparameters"]:
        for inner in params["inner_memberships"]:
            assert set(inner["train_ids"]).isdisjoint(inner["validation_ids"])


def test_recognition_nested_identity_metrics_scores_and_order():
    x, y, ids, sites = fixture()
    r = a.evaluate_identifiability(
        x, y, ids, folds=3, inner_folds=2, class_order=["B", "A"]
    )
    assert_disjoint(r)
    assert r["overall"]["balanced_accuracy"] > 0.95
    assert list(r["confusion"].index) == ["B", "A"]
    np.testing.assert_allclose(r["predictions"][["score_0", "score_1"]].sum(axis=1), 1)
    for name, model in r["models"].items():
        train = r["memberships"].query('fold==@name and role=="train"').row.to_numpy()
        np.testing.assert_allclose(model.named_steps["scale"].mean_, x[train].mean(0))
    held = a.evaluate_identifiability(x, y, ids, domains=sites, inner_folds=2)
    assert_disjoint(held)
    for name, model in held["models"].items():
        test = held["memberships"].query('fold==@name and role=="test"').row.to_numpy()
        assert set(sites[test]) == {name}
    pd.testing.assert_frame_equal(
        r["predictions"],
        a.evaluate_identifiability(
            x, y, ids, folds=3, inner_folds=2, class_order=["B", "A"]
        )["predictions"],
    )


def test_domain_purging_across_domains_and_training_only_outliers():
    x, y, ids, sites = fixture()
    sites[1::2] = "repeat"
    # The repeat domain contains every identity: a clear failure rather than leakage.
    with pytest.raises(ValueError, match="purging"):
        a.evaluate_identifiability(x, y, ids, domains=sites, regularization=(1,))
    x, y, ids, sites = fixture()
    original = a.evaluate_identifiability(x, y, ids, domains=sites, regularization=(1,))
    x[sites == "S0"] += 1e5
    changed = a.evaluate_identifiability(x, y, ids, domains=sites, regularization=(1,))
    np.testing.assert_array_equal(
        original["models"]["S0"].named_steps["scale"].mean_,
        changed["models"]["S0"].named_steps["scale"].mean_,
    )
    with pytest.raises(ValueError, match="Insufficient"):
        a.evaluate_identifiability(x[:8], y[:8], ids[:8])
    x[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        a.evaluate_identifiability(x, y, ids)


def test_feature_controls_nested_random_paths_and_wavelengths():
    x, y, ids, _ = fixture()
    w = np.arange(500, 506.0)
    r = a.evaluate_feature_budget(
        x,
        y,
        w,
        ids,
        budgets=(1, 3),
        random_replicates=2,
        folds=2,
        inner_folds=2,
        pca_components=2,
    )
    assert set(r["curve"].method) == {"selected", "random", "full", "PCA"}
    assert len(r["curve"]) == 16
    for (method, rep, fold), rows in (
        r["selected_features"]
        .query('method!="PCA" and method!="full"')
        .groupby(["method", "replicate", "fold"])
    ):
        s1 = set(rows[rows.budget == 1].column)
        s3 = set(rows[rows.budget == 3].column)
        assert s1 <= s3
    for result in r["evaluations"].values():
        assert_disjoint(result)
    selected = r["selected_features"].query('method=="selected" and budget==1')
    assert set(selected.column) == {0}
    reverse = a.evaluate_feature_budget(
        x[:, ::-1],
        y,
        w[::-1],
        ids,
        budgets=(1,),
        random_replicates=1,
        folds=2,
        regularization=(1,),
        include_full=False,
    )
    assert set(reverse["selected_features"].query('method=="selected"').wavelength) == {
        500
    }
    with pytest.raises(ValueError, match="budgets"):
        a.evaluate_feature_budget(x, y, w, ids, budgets=(10,))


def test_paired_representation_identity_alignment_and_dimensions():
    x, y, ids, sites = fixture()
    r = a.compare_representations(
        {"full": x, "reduced": x[:, [0, 2]]}, y, ids, domains=sites, regularization=(1,)
    )
    assert r["summary"].dimensions.tolist() == [6, 2]
    assert len(r["class_metrics"]) == 8
    left = r["evaluations"]["full"]["held_domain"]["memberships"]
    right = r["evaluations"]["reduced"]["held_domain"]["memberships"]
    pd.testing.assert_frame_equal(left, right)
    with pytest.raises(ValueError, match="aligned"):
        a.compare_representations({"bad": x[:-1]}, y, ids)


def parent_fixture():
    return (
        np.array([[1.0, 0, 0], [0, 1, 0], [0, 0, 1]]),
        np.array(["A", "B", "C"]),
        np.array(["pA", "pB", "pC"]),
    )


def test_mixtures_parent_roles_order_and_exact_recovery():
    e, y, ids = parent_fixture()
    m = a.generate_mixtures(
        e, y, ids, class_order=["C", "A", "B"], parent_roles=["test"] * 3
    )
    np.testing.assert_allclose(m["truth"].sum(axis=1), 1)
    for i in range(len(m["spectra"])):
        use = m["parent_indices"][i] >= 0
        np.testing.assert_allclose(
            m["spectra"][i],
            m["parent_fractions"][i, use] @ e[m["parent_indices"][i, use]],
        )
        assert set(m["parent_roles"][i, use]) == {"test"}
        np.testing.assert_array_equal(
            m["parent_categories"][i, use], y[m["parent_indices"][i, use]]
        )
    result = a.constrained_unmixing(m["spectra"], e, endmember_ids=ids)
    np.testing.assert_allclose(result["fractions"][:, [2, 0, 1]], m["truth"], atol=1e-8)
    assert result["RMSE"].max() < 1e-7
    np.testing.assert_array_equal(result["endmember_ids"], ids)
    np.testing.assert_array_equal(
        m["spectra"],
        a.generate_mixtures(e, y, ids, class_order=["C", "A", "B"])["spectra"],
    )
    with pytest.raises(ValueError, match="sum-one"):
        a.generate_mixtures(e, y, ids, triple_grid=((0.2, 0.2, 0.2),))
    with pytest.raises(ValueError, match="budget"):
        a.generate_mixtures(e, y, ids, maximum_mixtures=1)


def test_mesma_candidates_ambiguity_and_restrictions():
    e = np.array([[1.0, 0], [0, 1], [0.5, 0.5]])
    r = a.fit_mesma(
        [[0.5, 0.5]],
        e,
        ["A", "B", "C"],
        candidates=[(2,), (0, 1)],
        max_components=2,
        class_order=["C", "B", "A"],
    )
    assert r["selected_endmembers"][0].tolist() == [2]
    assert r["ambiguity"][0]["near_count"] == 2
    assert r["ambiguity"][0]["maximum_fraction_range"] == 1
    np.testing.assert_allclose(r["candidate_fractions"][0], [[1, 0, 0], [0, 0.5, 0.5]])
    restricted = a.fit_mesma(
        [[0.5, 0.5]], e, ["A", "B", "C"], candidates=[(0, 1)], max_components=2
    )
    assert restricted["ambiguity"][0]["alternative_count"] == 0
    default = a.fit_mesma([[0.5, 0.5]], e, ["A", "B", "C"], max_components=2)
    assert len(default["candidate_models"]) == 6
    with pytest.raises(ValueError, match="indices"):
        a.fit_mesma([[0.5, 0.5]], e, ["A", "B", "C"], candidates=[(7,)])
    with pytest.raises(ValueError, match="nonnegative"):
        a.candidate_ambiguity([[0.5, 0.5]], [-1])
    small = a.candidate_ambiguity([[1, 0], [0, 1]], [0, 0.02], tolerance=0.01)
    large = a.candidate_ambiguity([[1, 0], [0, 1]], [0, 0.02], tolerance=0.03)
    assert small["near_count"] == 1 and large["near_count"] == 2


@pytest.mark.parametrize(
    "values,expected",
    [([-2, 1, 0.8], [0, 0.6, 0.4]), ([0.2, 0.3, 0.5], [0.2, 0.3, 0.5]), ([42], [1])],
)
def test_simplex_known_idempotent(values, expected):
    p = a.project_simplex(values)
    np.testing.assert_allclose(p, expected, atol=1e-12)
    np.testing.assert_allclose(a.project_simplex(p), p, atol=1e-12)
    np.testing.assert_allclose(a.project_simplex([values, values]), [p, p])


def test_projection_euclidean_and_truth_error():
    from scipy.optimize import minimize

    rng = np.random.default_rng(44)
    for raw in rng.normal(size=(8, 4)):
        p = a.project_simplex(raw)
        reference = minimize(
            lambda z: np.sum((z - raw) ** 2),
            np.ones(4) / 4,
            bounds=[(0, None)] * 4,
            constraints={"type": "eq", "fun": lambda z: z.sum() - 1},
            tol=1e-12,
        )
        np.testing.assert_allclose(p, reference.x, atol=1e-6)
        truth = rng.dirichlet(np.ones(4))
        assert np.linalg.norm(p - truth) <= np.linalg.norm(raw - truth) + 1e-12
    with pytest.raises(ValueError, match="finite"):
        a.project_simplex([np.nan, 1])


def test_ridge_train_only_raw_projected_saved_and_nested_groups():
    rng = np.random.default_rng(5)
    f = rng.dirichlet(np.ones(3), 30)
    x = f @ np.eye(3)
    fit = a.fit_ridge_fractions(
        x,
        f,
        groups=np.repeat(np.arange(10), 3),
        alphas=(0.001, 0.1),
        folds=2,
        class_order=["C", "A", "B"],
    )
    np.testing.assert_allclose(fit.preprocessing["mean"], x.mean(0))
    result = fit.predict([[2, -1, 0]])
    assert result["raw_prediction"].min() < 0
    np.testing.assert_allclose(result["projected_prediction"].sum(axis=1), 1)
    assert result["projected_prediction"].min() >= 0
    for fold in fit.tuning["memberships"]:
        assert set(fold["train_ids"]).isdisjoint(fold["validation_ids"])
    raw = (
        (x - fit.preprocessing["mean"]) / fit.preprocessing["scale"]
    ) @ fit.preprocessing["coefficient"].T + fit.preprocessing["intercept"]
    np.testing.assert_allclose(raw, fit.predict(x)["raw_prediction"])
    assert np.sqrt(np.mean((fit.predict(x)["projected_prediction"] - f) ** 2)) < 0.001
    with pytest.raises(ValueError, match="explicit"):
        a.fit_ridge_fractions(x, f, alphas=(0.1, 1))


def test_fraction_metrics_detection_quantification_and_cluster_bootstrap():
    truth = np.array([[0, 1], [0.1, 0.9], [0.5, 0.5], [1, 0.0]])
    pred = np.array([[0.2, 0.8], [0.05, 0.95], [0.6, 0.4], [0.9, 0.1]])
    r = a.fraction_diagnostics(
        truth, pred, class_order=["A", "B"], groups=[0, 0, 1, 1], bootstraps=39
    )
    assert r["per_class"].absent_false_positive_rate.tolist() == [1, 1]
    assert r["per_class"].low_fraction_miss_rate.iloc[0] == 1
    np.testing.assert_allclose(
        r["overall"]["RMSE"], np.sqrt(np.mean((truth - pred) ** 2))
    )
    pd.testing.assert_frame_equal(
        r["intervals"],
        a.fraction_diagnostics(truth, pred, groups=[0, 0, 1, 1], bootstraps=39)[
            "intervals"
        ],
    )
    empty = a.fraction_diagnostics([[0.5, 0.5]], [[0.5, 0.5]])
    assert empty["per_class"].absent_false_positive_rate.isna().all()
    with pytest.raises(ValueError, match="explicit"):
        a.fraction_diagnostics(truth, pred, bootstraps=10)


def test_library_size_training_only_capacity_strategies_and_determinism():
    x, y, ids, sites = fixture()
    r = a.evaluate_library_size(
        x,
        y,
        ids,
        sizes=(4, 8),
        replicates=2,
        domains=sites,
        strategies=("random", "balanced_random", "farthest"),
    )
    assert len(r["metrics"]) == 36
    for (fold, size, strategy, rep), rows in r["selected_identities"].groupby(
        ["fold", "size", "strategy", "replicate"]
    ):
        assert len(rows) == size
        assert set(rows.identity).isdisjoint(ids[sites == fold])
    pd.testing.assert_frame_equal(
        r["metrics"],
        a.evaluate_library_size(
            x,
            y,
            ids,
            sizes=(4, 8),
            replicates=2,
            domains=sites,
            strategies=("random", "balanced_random", "farthest"),
        )["metrics"],
    )
    with pytest.raises(ValueError, match="exceeds"):
        a.evaluate_library_size(x, y, ids, sizes=(100,))


def test_projection_large_offsets_and_extreme_finite_range():
    np.testing.assert_allclose(a.project_simplex([1e16, 1e16]), [0.5, 0.5])
    np.testing.assert_allclose(a.project_simplex([-1e308, 1e308]), [0, 1])
    np.testing.assert_allclose(a.project_simplex([-1e16, -1e16]), [0.5, 0.5])


def test_explicit_budget_and_unused_metadata_guards():
    x, y, ids, _ = fixture()
    with pytest.raises(ValueError, match="unit budget"):
        a.spectral_separability(x, y, np.arange(6.0), ids, maximum_units=10)
    with pytest.raises(ValueError, match="integer"):
        a.spectral_separability(x, y, np.arange(6.0), ids, permutations=19.5)
    with pytest.raises(ValueError, match="unique"):
        a.evaluate_feature_budget(x, y, np.arange(6.0), ids, budgets=(1, 1))
    e, labels, parents = parent_fixture()
    with pytest.raises(ValueError, match="maximum_models"):
        a.fit_mesma(e, e, labels, maximum_models=-1)
    with pytest.raises(ValueError, match="maximum_mixtures"):
        a.generate_mixtures(e, labels, parents, maximum_mixtures=-1)
    with pytest.raises(ValueError, match="Duplicate"):
        a.fit_mesma(e, e, labels, candidates=[(0, 1), (1, 0)], max_components=2)
    with pytest.raises(ValueError, match="aligned"):
        a.fit_ridge_fractions(e, e, groups=[1], alphas=(1,))
