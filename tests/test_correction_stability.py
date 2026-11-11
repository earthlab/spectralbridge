"""Numerical and rejection-diagnostic regressions, independent of site metrics."""

import numpy as np
import pytest

from spectralbridge.topographic import cluster_covariance


def test_cluster_covariance_agrees_with_independent_svd_influence():
    rng = np.random.default_rng(83)
    x = rng.normal(size=800)
    # Narrow but full-rank direction: normal equations discard this information.
    X = np.c_[np.ones(800), x, x + rng.normal(size=800) * 1e-7]
    residual = rng.normal(size=800)
    groups = np.repeat(np.arange(40), 20)
    inverse = np.linalg.pinv(X)
    influence = np.stack([inverse[:, groups == g] @ residual[groups == g] for g in range(40)])
    expected = (40 / 39) * (799 / 797) * (influence.T @ influence)
    got, count = cluster_covariance(X, residual, groups)
    assert count == 40
    np.testing.assert_allclose(got, expected, rtol=2e-8, atol=1e-4)
    # Invariance of prediction variance to equivalent column coordinates.
    v = np.array([1., .2, .20000001])
    np.testing.assert_allclose(v @ got @ v, v @ expected @ v, rtol=.04)


def test_cluster_covariance_rejects_rank_deficiency():
    with pytest.raises(ValueError, match="Rank-deficient"):
        cluster_covariance(np.ones((20, 2)), np.ones(20), np.arange(20))

