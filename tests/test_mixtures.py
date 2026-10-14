"""Analytically checkable constrained mixtures, selection and leakage contracts."""

import numpy as np
import pytest
from scipy.optimize import minimize
from spectralbridge.mixtures import (
    fit_models,
    fcls,
    model_indices,
    shade_model_errors,
    selection_scores,
    select_endmembers,
    grouped_identity_split,
    mixture_truth,
)


def test_known_fractions_faces_and_sum_one():
    e = np.eye(3)
    y = np.array([[0.2, 0.3, 0.5], [0, 1, 0], [0.5, 0.5, 0]])
    fit = fcls(y, e)
    np.testing.assert_allclose(fit["fractions"], y, atol=1e-10)
    np.testing.assert_allclose(fit["RMSE"], 0, atol=1e-8)
    assert np.min(fit["fractions"]) >= 0
    np.testing.assert_allclose(fit["fractions"].sum(1), 1)


def test_exact_projection_matches_independent_slsqp():
    rng = np.random.default_rng(23)
    e = rng.normal(size=(4, 9))
    y = rng.normal(size=(12, 9))
    result = fcls(y, e)
    for i, target in enumerate(y):
        alt = minimize(
            lambda f: np.mean((f @ e - target) ** 2),
            np.ones(4) / 4,
            bounds=[(0, 1)] * 4,
            constraints={"type": "eq", "fun": lambda f: f.sum() - 1},
            method="SLSQP",
            options={"ftol": 1e-13, "maxiter": 1000},
        )
        assert alt.success
        np.testing.assert_allclose(result["RMSE"][i] ** 2, alt.fun, atol=1e-9)


def test_distinct_class_is_exactly_ambiguous_mixture():
    e = np.array([[1.0, 0], [0, 1], [0.5, 0.5]])
    result = fit_models(e[2:], [0, 1, 2], e, max_components=2, tolerance=1e-6)
    assert result["near_compositions"][0] >= 2
    incorrect = fit_models(e[2:], [0, 1], e[:2], max_components=2)
    np.testing.assert_allclose(incorrect["RMSE"], 0, atol=1e-8)
    np.testing.assert_allclose(incorrect["fractions"], [[0.5, 0.5]], atol=1e-8)


def test_model_enumeration_one_candidate_per_class_and_budget():
    models = model_indices([0, 0, 1, 2], 3, 100)
    assert all(len(set(np.array([0, 0, 1, 2])[m])) == len(m) for m in models)
    with pytest.raises(ValueError, match="budget"):
        model_indices(range(12), 6, 100)


def test_ear_masa_and_cob_are_candidate_modelling_metrics():
    e = np.array([[1.0, 0], [0.5, 0], [0, 1]])
    labels = np.array(["a", "a", "b"])
    error = shade_model_errors(e, e)
    assert error[0, 1] > 0 and error[1, 0] == 0
    scores = selection_scores(e, labels)
    np.testing.assert_allclose(scores["EAR"][:2], [0, (0.5 / np.sqrt(2))])
    np.testing.assert_allclose(scores["MASA"][:2], 0, atol=1e-8)
    ix = select_endmembers(e, labels, "CoB", 1, seed=1, threshold=0.01)
    assert 0 in ix and 2 in ix


def test_selection_is_deterministic_and_ies_not_farthest_point():
    rng = np.random.default_rng(1)
    e = rng.uniform(size=(12, 5))
    labels = np.repeat(["a", "b", "c"], 4)
    for method in [
        "random",
        "medoid",
        "EAR",
        "MASA",
        "CoB",
        "IES",
        "diversity",
        "hybrid",
    ]:
        a = select_endmembers(e, labels, method, 2, seed=5)
        b = select_endmembers(e, labels, method, 2, seed=5)
        np.testing.assert_array_equal(a, b)
        assert len(a) == len(set(a))
    with pytest.raises(ValueError, match="Unknown"):
        select_endmembers(e, labels, "fake", 1)


def test_holdout_purges_repeated_identity():
    train, test = grouped_identity_split(
        ["a", "a", "b", "c"], [False, True, False, False]
    )
    assert test.tolist() == [False, True, False, False]
    assert train.tolist() == [False, False, True, True]
    assert set(np.array(["a", "a", "b", "c"])[train]).isdisjoint(
        np.array(["a", "a", "b", "c"])[test]
    )


def test_mixture_truth_uses_separate_sources_and_reproducible_fractions():
    labels = np.repeat([0, 1, 2], 4)
    sources = np.eye(3)[labels]
    a = mixture_truth(sources, labels, pairs_per_composition=2, seed=8)
    b = mixture_truth(sources, labels, pairs_per_composition=2, seed=8)
    np.testing.assert_array_equal(a["sources"], b["sources"])
    np.testing.assert_allclose(a["truth"].sum(1), 1)
    assert set([0, 0.05, 0.1, 0.5, 0.95, 1]).issubset(set(a["truth"][:, 0]))
    np.testing.assert_allclose(a["spectra"], a["truth"])


def test_explicit_black_shade_has_identifiable_algebra_not_measured_truth():
    e = np.array([[1.0, 0], [0, 1], [0, 0]])
    fit = fcls([[0.2, 0.3]], e)
    np.testing.assert_allclose(fit["fractions"], [[0.2, 0.3, 0.5]], atol=1e-8)
    np.testing.assert_allclose(
        fit["fractions"][:, :2] / fit["fractions"][:, :2].sum(1)[:, None], [[0.4, 0.6]]
    )


def test_zero_fraction_extra_class_is_not_a_second_material_composition():
    result = fit_models(
        [[1, 0, 0]], range(3), np.eye(3), max_components=3, tolerance=1e-8
    )
    assert result["near_compositions"][0] == 1


def test_nearly_collinear_sources_do_not_imply_precise_fractions():
    e = np.array([[1.0, 0.0], [1.0, 1e-7], [0.0, 1.0]])
    target = 0.5 * e[0] + 0.5 * e[1]
    fit = fit_models(target[None], range(3), e, max_components=3, tolerance=1e-6)
    # Equivalent spectra at the declared numerical resolution can have radically different fractions.
    assert fit["RMSE"][0] < 1e-6
    assert fit["near_compositions"][0] >= 2
    assert fit["near_fraction_range"][0].max() > 0.9
