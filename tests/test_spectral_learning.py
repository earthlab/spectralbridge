"""Leakage, metrics, selection and calibrated-set contracts for experimental ML."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn", reason="optional analytics extra")
from spectralbridge.spectral_learning import (  # noqa: E402
    StableFSelector,
    calibration_split,
    fit_training_model,
    probabilities,
    fit_temperature,
    temperature_probabilities,
    conformal_threshold,
    conformal_metrics,
    classification_metrics,
    cluster_bootstrap_accuracy,
    outer_folds,
)
from spectralbridge.mixtures import validate_holdout  # noqa: E402

pytestmark = pytest.mark.scientific


def toy():
    rng = np.random.default_rng(7)
    ids = np.repeat(np.arange(30), 2)
    y = np.where(ids < 15, "A", "B")
    X = rng.normal(size=(60, 8)) * 0.2 + (y == "B")[:, None] * np.array(
        [0, 0, 2, 0, 1, 0, 0, 0]
    )
    return X, y, ids


def test_calibration_and_outer_folds_keep_complete_histories():
    X, y, ids = toy()
    proper, cal = calibration_split(ids, seed=6)
    assert set(ids[proper]).isdisjoint(ids[cal])
    np.testing.assert_array_equal(cal, calibration_split(ids, seed=6)[1])
    table = pd.DataFrame(
        {
            "GlobalID": ids,
            "label": y,
            "site": np.where(ids % 2, "S1", "S2"),
            "year": np.tile([2020, 2023], 30),
            "flights": [("f" + str(i % 3),) for i in range(60)],
        }
    )
    for _, _, train, test in outer_folds(table):
        validate_holdout(ids, train, test)
    with pytest.raises(ValueError, match="leakage"):
        validate_holdout(ids, np.ones(len(ids), bool), cal)


def test_wavelength_selector_does_not_learn_from_prediction_outliers():
    X, y, ids = toy()
    selector = StableFSelector(2).fit(X, y)
    before = selector.selected_.copy()
    assert 2 in before and 4 in before
    outlier = X[:1].copy()
    outlier[:, 0] = 1e15
    selector.transform(outlier)
    np.testing.assert_array_equal(selector.selected_, before)
    with pytest.raises(ValueError):
        selector.transform(X[:, :-1])
    with pytest.raises(ValueError):
        StableFSelector(9).fit(X, y)


@pytest.mark.parametrize(
    "model",
    ["logistic", "PLSDA", "SVM", "forest", "centroid", "majority", "stratified"],
)
def test_models_fit_only_supplied_proper_rows_and_return_aligned_scores(model):
    X, y, ids = toy()
    proper, cal = calibration_split(ids, seed=2)
    fitted, record = fit_training_model(
        X[proper], y[proper], ids[proper], model, k=4, inner_folds=2
    )
    assert set(record["proper_training_identities"]) == set(ids[proper])
    for fold in record["inner_memberships"]:
        assert set(fold["train_ids"]).isdisjoint(fold["validation_ids"])
        assert set(fold["train_ids"] + fold["validation_ids"]).isdisjoint(ids[cal])
    chosen = fitted["select"].selected_
    np.testing.assert_allclose(fitted["scale"].mean_, X[proper][:, chosen].mean(0))
    p = probabilities(fitted, X[cal])
    np.testing.assert_allclose(p.sum(1), 1)
    assert p.shape == (cal.sum(), 2)
    if model == "SVM":
        assert fitted["model"].probability is False


def test_metrics_against_hand_calculation_and_sklearn():
    p = np.array([[0.9, 0.1], [0.3, 0.7], [0.6, 0.4], [0.2, 0.8]])
    labels = np.array(["A", "A", "B", "B"])
    result, per, matrix, bins = classification_metrics(labels, p, ["A", "B"])
    np.testing.assert_array_equal(matrix, [[1, 1], [1, 1]])
    assert result["balanced_accuracy"] == result["macro_F1"] == 0.5
    np.testing.assert_allclose(result["Brier"], np.mean([0.02, 0.98, 0.72, 0.08]))
    np.testing.assert_allclose(result["ECE"], np.mean([0.1, 0.7, 0.6, 0.2]))
    from sklearn.metrics import balanced_accuracy_score, f1_score

    pred = np.array(["A", "B", "A", "B"])
    assert result["balanced_accuracy"] == balanced_accuracy_score(labels, pred)
    assert result["macro_F1"] == f1_score(labels, pred, average="macro")
    assert sum(b["N"] for b in bins) == 4 and len(per) == 2


def test_temperature_is_fitted_on_calibration_and_changes_no_argmax():
    p = np.tile([[0.99, 0.01], [0.01, 0.99]], (10, 1))
    labels = np.tile([0, 1], 10)
    labels[:8] = 1 - labels[:8]
    t = fit_temperature(p, labels)
    assert t > 1
    q = temperature_probabilities(p, t)
    np.testing.assert_array_equal(q.argmax(1), p.argmax(1))
    before = classification_metrics(labels, p, [0, 1])[0]["log_loss"]
    assert classification_metrics(labels, q, [0, 1])[0]["log_loss"] < before


def test_conformal_uses_one_maximum_per_identity_and_finite_sample_rank():
    # Three identities; the worst row in repeated identity a must be retained.
    p = np.array([[0.9, 0.1], [0.1, 0.9], [0.8, 0.2], [0.7, 0.3]])
    y = [0, 0, 0, 0]
    ids = ["a", "a", "b", "c"]
    threshold = conformal_threshold(p, y, ids, alpha=0.5)
    # scores per identity .9,.2,.3; ceil((3+1)*.5)=2 -> .3
    np.testing.assert_allclose(threshold, 0.3)
    result = conformal_metrics(p, y, ids, threshold)
    assert result["row_coverage"] == 0.75
    np.testing.assert_allclose(result["identity_joint_coverage"], 2 / 3)
    assert np.isinf(conformal_threshold(p, y, ids, alpha=0.1))
    assert conformal_metrics(p, y, ids, np.inf)["mean_set_size"] == 2


def test_group_bootstrap_preserves_repeated_identity_and_paired_draws():
    truth = np.array(["A", "A", "B", "B", "B", "B"])
    ids = np.array(["a", "a", "b", "b", "c", "c"])
    pred = np.array(["A", "A", "A", "A", "B", "B"])
    draws = cluster_bootstrap_accuracy(
        truth, pred, ids, ["A", "B"], replicates=39, seed=4
    )
    np.testing.assert_array_equal(
        draws,
        cluster_bootstrap_accuracy(truth, pred, ids, ["A", "B"], replicates=39, seed=4),
    )
    assert set(draws).issubset({0.5, 0.75, 1.0})
    perfect = cluster_bootstrap_accuracy(
        truth, truth, ids, ["A", "B"], replicates=39, seed=4
    )
    np.testing.assert_allclose(perfect, 1)


def test_conflicting_biological_labels_and_unknown_metric_truth_rejected():
    X, y, ids = toy()
    y = y.copy()
    y[0] = "B"
    with pytest.raises(ValueError, match="conflicting"):
        fit_training_model(X, y, ids, "logistic")
    with pytest.raises(ValueError, match="known"):
        classification_metrics(["C"], [[0.5, 0.5]], ["A", "B"])


def test_domain_labels_can_vary_within_identity_without_leaking_groups():
    X, y, ids = toy()
    domain = np.tile(["year0", "year1"], 30)
    model, record = fit_training_model(
        X, domain, ids, "logistic", inner_folds=2, allow_repeated_identity_labels=True
    )
    assert record["inner_memberships"]
    for fold in record["inner_memberships"]:
        assert set(fold["train_ids"]).isdisjoint(fold["validation_ids"])
    p = probabilities(model, X)
    draws = cluster_bootstrap_accuracy(
        domain,
        np.array(["year0", "year1"])[p.argmax(1)],
        ids,
        ["year0", "year1"],
        replicates=19,
        stratify=False,
    )
    assert np.isfinite(draws).all()


@pytest.mark.parametrize(
    "method,count",
    [
        ("mean", 1),
        ("median", 1),
        ("medoid", 1),
        ("diversity", 2),
        ("cluster_medoid", 2),
    ],
)
def test_prototypes_have_training_identity_provenance(method, count):
    from spectralbridge.spectral_learning import class_prototypes

    X = np.array([[0, 0], [0.1, 0], [1, 0], [2, 0], [0, 1], [0, 1.1], [0, 2], [0, 3.0]])
    labels = np.repeat(["A", "B"], 4)
    ids = np.array(list("abcdefgh"))
    spectra, classes, positions = class_prototypes(
        X, labels, ids, method=method, count=count, seed=7
    )
    assert spectra.shape == (2 * count, 2)
    assert len(classes) == len(positions) == len(spectra)
    if method in {"mean", "median"}:
        assert (positions == -1).all()
    else:
        np.testing.assert_allclose(spectra, X[positions])
        assert len(set(ids[positions])) == len(positions)
    with pytest.raises(ValueError):
        class_prototypes(X, labels, np.repeat("a", 8))


def test_novelty_pca_is_training_only_and_detects_constructed_outlier():
    from spectralbridge.spectral_learning import fit_novelty_space, novelty_scores

    rng = np.random.default_rng(8)
    train = rng.normal(1, 0.01, (30, 4))
    space = fit_novelty_space(train)
    before = space[0].mean_.copy()
    scores = novelty_scores(np.array([[1, 1, 1, 1], [100, 1, 1, 1]]), train, space)
    assert scores["nearest_RMSE"][1] > scores["nearest_RMSE"][0]
    assert scores["PCA_radius"][1] > scores["PCA_radius"][0]
    np.testing.assert_array_equal(space[0].mean_, before)
    with pytest.raises(ValueError):
        novelty_scores(np.zeros((1, 4)), train, space)


def test_frozen_actual_prediction_metrics_regression():
    """Real prediction probabilities reproduce independently frozen metric math."""
    import json
    from pathlib import Path

    fixture = json.loads(
        (
            Path(__file__).parent
            / "data/scientific_regression/learning_predictions.json"
        ).read_text()
    )
    rows = fixture["records"]
    summary, _, _, _ = classification_metrics(
        [r["truth"] for r in rows],
        np.array([r["probabilities"] for r in rows]),
        fixture["classes"],
    )
    assert summary["balanced_accuracy"] == pytest.approx(
        fixture["expected"]["balanced_accuracy"]
    )
    assert summary["macro_F1"] == pytest.approx(fixture["expected"]["macro_F1"])
    assert len(fixture["source_sha256"]) == 64
