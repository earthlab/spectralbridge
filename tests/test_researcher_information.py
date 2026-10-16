# ruff: noqa: E402
"""Researcher-only labels, grouped metrics, complementary features and fractions."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn", reason="optional analytics extra")
from sklearn.metrics import roc_auc_score
from scipy.optimize import minimize
from spectralbridge.researcher_information import (
    RESEARCHER_CATEGORIES,
    validate_researcher_labels,
    identity_weights,
    project_simplex,
    weighted_auc,
    univariate_discrimination,
    orthogonal_feature_path,
    disconnected_derivative,
    disjoint_parent_bundles,
    fraction_metrics,
    TrainingTransform,
)


def test_labels_cannot_silently_reintroduce_historical_codes():
    validate_researcher_labels(RESEARCHER_CATEGORIES)
    with pytest.raises(ValueError):
        validate_researcher_labels(["DBS"])
    with pytest.raises(ValueError):
        identity_weights(["a", "a"], ["x", "y"])


def test_simplex_matches_independent_constrained_optimizer():
    X = np.array([[-2, 1, 0.8], [0.3, 0.4, 0.3], [2, 2, 2], [0.1, -0.1, 0.7]])
    p = project_simplex(X)
    assert np.all(p >= 0)
    np.testing.assert_allclose(p.sum(1), 1)
    for x, y in zip(X, p):
        r = minimize(
            lambda z: np.sum((z - x) ** 2),
            np.ones(3) / 3,
            bounds=[(0, 1)] * 3,
            constraints={"type": "eq", "fun": lambda z: z.sum() - 1},
            method="SLSQP",
            tol=1e-12,
        )
        np.testing.assert_allclose(y, r.x, atol=1e-6)


def test_weighted_auc_ties_and_direction_match_sklearn():
    z = np.array([0, 1, 0, 1, 1], bool)
    s = np.array([0, 1, 1, 2, 0.0])
    w = np.array([1, 2, 1, 1, 3.0])
    np.testing.assert_allclose(
        weighted_auc(z, np.c_[s, -s], w),
        [roc_auc_score(z, s, sample_weight=w), roc_auc_score(z, -s, sample_weight=w)],
    )


def test_univariate_rule_is_training_only_and_repeat_invariant():
    X = np.array([[0, 3], [1, 2], [5, 1], [6, 0.0]])
    y = np.array([0, 0, 1, 1], bool)
    r = univariate_discrimination(X, y, list("abcd"), X, y, list("abcd"))
    np.testing.assert_allclose(r["balanced_accuracy"], 1)
    repeated = univariate_discrimination(
        np.repeat(X, 3, 0),
        np.repeat(y, 3),
        np.repeat(list("abcd"), 3),
        np.repeat(X, 2, 0),
        np.repeat(y, 2),
        np.repeat(list("abcd"), 2),
    )
    for key in ["effect", "balanced_accuracy", "AUC", "BA_low", "BA_high"]:
        np.testing.assert_allclose(r[key], repeated[key])
    assert r["direction"][1] == -1


def test_orthogonal_path_skips_duplicate_for_complementary_signal():
    rng = np.random.default_rng(8)
    X = rng.normal(size=(200, 3))
    X[:, 1] = X[:, 0]
    y = np.where(X[:, 0] > 0, "a", np.where(X[:, 2] > 0, "b", "c"))
    path = orthogonal_feature_path(X, y, 3)
    assert 2 in path[:2]
    assert not {0, 1}.issubset(path[:2])


def test_derivatives_do_not_bridge_gap_and_fit_transform_does_not_see_test():
    w = np.array([400, 405, 410, 1500, 1505, 1510])
    X = np.array([np.r_[w[:3] * 2, w[3:] * 3 + 900], np.r_[w[:3] * 2, w[3:] * 3 + 100]])
    d = disconnected_derivative(X, w)
    np.testing.assert_allclose(d, np.tile([2, 2, 2, 3, 3, 3], (2, 1)))
    np.testing.assert_allclose(disconnected_derivative(X, w, 2), 0, atol=1e-10)
    tr = TrainingTransform("full", w).fit(X)
    mean = tr.scaler.mean_.copy()
    tr.transform(X * 100)
    np.testing.assert_array_equal(mean, tr.scaler.mean_)


def test_bundles_keep_id_histories_together_and_never_reuse_parent():
    t = pd.DataFrame(
        [
            dict(GlobalID=f"{c}{i}", cover_category=c, year=y)
            for c in RESEARCHER_CATEGORIES
            for i in range(5)
            for y in [2020, 2023]
        ]
    )
    b = disjoint_parent_bundles(t, 3, 17)
    chosen = t.loc[b.ravel()]
    assert chosen.GlobalID.nunique() == 15 and chosen.year.eq(2020).all()
    assert all(
        set(t.loc[row].cover_category) == set(RESEARCHER_CATEGORIES) for row in b
    )
    f = fraction_metrics(np.eye(5), np.eye(5))
    assert all(x["RMSE"] == 0 and x["FPR"] == 0 for x in f)


def test_compact_loader_can_avoid_constructing_historical_labels(tmp_path, monkeypatch):
    import json
    import spectralbridge.mesma_readiness as module

    compact = tmp_path / "compact"
    compact.mkdir()
    metadata = []
    neon = []
    oli = []
    for i, c in enumerate(RESEARCHER_CATEGORIES[:2]):
        metadata.append(
            {
                **dict.fromkeys(module.META),
                "GlobalID": str(i),
                "cover_category": c,
                "aop_site": "NIWO",
            }
        )
        base = dict(
            GlobalID=str(i),
            site="NIWO",
            year=2023,
            flight_observations=1,
            flight_history=json.dumps([json.dumps(["flight", "image"])]),
        )
        neon.append({**base, "corr_wl400nm": i + 1.0, "corr_wl405nm": i + 2.0})
        oli.append(
            {
                **base,
                **{
                    f"olioli_undarkened_wl{w}nm": i + 1.0
                    for w in [443, 482, 561.4, 654.6, 864.7, 1608.9, 2200.7]
                },
            }
        )
    source = tmp_path / "source.parquet"
    pd.DataFrame(metadata).to_parquet(source)
    pd.DataFrame(neon).to_parquet(compact / "corr_polygon_year.parquet")
    pd.DataFrame(oli).to_parquet(compact / "olioli_undarkened_polygon_year.parquet")

    def forbidden(*args, **kwargs):
        raise AssertionError("Historical taxonomic labels must not be constructed")

    monkeypatch.setattr(module, "tag_pfts", forbidden)
    monkeypatch.setattr(module, "load_pft_crosswalk", forbidden)
    table, arrays, _ = module.load_compact_inputs(
        source, compact, include_historical_labels=False
    )
    assert "pft_code" not in table and arrays["NEON"].shape == (2, 2)
    assert set(table.cover_category) == set(RESEARCHER_CATEGORIES[:2])


def test_baseline_prediction_exports_cannot_alias_methods():
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).parents[1]
        / "provenance/researcher-pft-information/2026-10-15/v1/finalize_exports.py"
    )
    spec = importlib.util.spec_from_file_location("researcher_export_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.baseline_filename("target", "FCLS") != module.baseline_filename(
        "target", "MESMA"
    )
    metadata = pd.DataFrame(
        {"mixture_id": [0, 1], "bundle": [0, 0], "ambiguity": ["Low", "High"]}
    )
    a = module.prediction_frame(metadata, np.eye(2), ["A", "B"], [0.1, 0.2], [0.3, 0.4])
    b = module.prediction_frame(
        metadata, np.eye(2)[::-1], ["A", "B"], [0.5, 0.6], [0.7, 0.8]
    )
    assert not a.equals(b) and list(a.pred_A) == [1, 0]
    assert "pred_A" not in metadata


def test_training_only_maximum_null_matches_existing_blocked_engine():
    import importlib.util
    from pathlib import Path
    from spectralbridge.pft_method_audit import method_statistics, AuditConfig

    path = (
        Path(__file__).parents[1]
        / "provenance/researcher-pft-information/2026-10-15/v1/training_inference.py"
    )
    spec = importlib.util.spec_from_file_location("training_max_null_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rng = np.random.default_rng(7)
    X = rng.normal(size=(12, 4))
    z = np.tile([0, 1], 6)
    blocks = np.repeat(np.arange(3), 4)
    r = module.max_t_null(X, z, blocks, permutations=39, seed=8)
    legacy = method_statistics(
        X,
        z,
        blocks,
        np.arange(400, 420, 5),
        config=AuditConfig(permutations=39),
        seed=8,
    )
    np.testing.assert_allclose(r["maxima"], legacy["stats"][1:, 0], atol=1e-12)
    np.testing.assert_allclose(
        r["observed"], legacy["curves"][0] / legacy["se"], atol=1e-12
    )
