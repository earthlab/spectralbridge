import numpy as np
import pandas as pd
import pytest
from spectralbridge.spectral_analytics_mixtures import reconstruct_saved_mixtures
from spectralbridge.spectral_analytics_extensions import safe_novelty_scores
from spectralbridge.spectral_learning import fit_novelty_space


def test_saved_parent_fractions_reconstruct_exactly():
    records = pd.DataFrame(
        [dict(source_ids="a@1|b@1", true_fractions='{"A":0.2,"B":0.8}')]
    )
    target, true, classes = reconstruct_saved_mixtures(
        records,
        {"a@1": 0, "b@1": 1},
        np.array([[1, 0], [0, 2]]),
        {"a@1": "A", "b@1": "B"},
    )
    np.testing.assert_allclose(target, [[0.2, 1.6]])
    np.testing.assert_allclose(true, [[0.2, 0.8]])
    assert list(classes) == ["A", "B"]
    with pytest.raises(ValueError, match="distinct"):
        reconstruct_saved_mixtures(
            records, {"a@1": 0, "b@1": 1}, np.ones((2, 2)), {"a@1": "A", "b@1": "A"}
        )


def test_zero_coordinate_target_has_no_angle_but_valid_distances():
    train = np.array([[1.0, 1], [1, 2], [2, 1], [2, 2]])
    scores = safe_novelty_scores([[0, 0], [1, 1]], train, fit_novelty_space(train))
    assert np.isnan(scores["nearest_angle_deg"][0])
    assert np.isfinite(scores["nearest_RMSE"]).all()
    assert np.isfinite(scores["PCA_residual"]).all()
