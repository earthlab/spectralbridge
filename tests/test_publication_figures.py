"""Regression contracts for new descriptive scientific figure calculations."""
import numpy as np
import pandas as pd
import pytest

from examples.publication_figures.figure_data import (
    weighted_pca, representative_indices, segments, verify_manifest,
)


def test_pca_keeps_all_rows_and_uses_total_weighted_variance():
    y = np.array([[0, 0, 1, 2], [1, 2, 0, 1], [3, 1, 4, 0], [2, 4, 3, 5]], float)
    w = [400, 405, 1500, 1505]
    scores, variance, loadings = weighted_pca(y, w)
    covariance = np.cov((y - y.mean(0)) / 2, rowvar=False)
    eigen = np.linalg.eigvalsh(covariance)[::-1]
    np.testing.assert_allclose(variance, eigen[:2] / eigen.sum())
    np.testing.assert_allclose(scores, (y - y.mean(0)) / 2 @ loadings.T)
    assert scores.shape == (len(y), 2)
    for row in loadings:
        assert row[np.argmax(abs(row))] >= 0
    with pytest.raises(ValueError, match='finite'):
        weighted_pca(np.where(y == 0, np.nan, y), w)
    with pytest.raises(ValueError, match='variance'):
        weighted_pca(np.ones((4, 4)), w)


def test_common_support_segments_never_bridge_gaps_or_unordered_grids():
    result = segments([400, 405, 1335, 1455, 1460, 1785, 2005, 2010])
    assert [x.tolist() for x in result] == [[0, 1], [2], [3, 4], [5], [6, 7]]
    with pytest.raises(ValueError):
        segments([405, 400])


def test_representative_is_observed_median_nearest_with_identity_tie_break():
    table = pd.DataFrame({'site': ['S'] * 4, 'year': [2020] * 4,
                          'GlobalID': ['b', 'a', 'c', 'd'], 'cover_category': ['X'] * 4})
    y = np.array([[0, 0], [2, 2], [10, 10], [12, 12]])
    chosen = representative_indices(table, y, [400, 405])
    assert table.loc[chosen['X'], 'GlobalID'] == 'a'
    order = [3, 2, 0, 1]
    shuffled = table.iloc[order].reset_index(drop=True)
    assert shuffled.loc[representative_indices(shuffled, y[order], [400, 405])['X'], 'GlobalID'] == 'a'


def test_upstream_checksum_changes_are_rejected(tmp_path):
    import json
    from hashlib import sha256
    path = tmp_path / 'data.csv'
    path.write_text('original')
    (tmp_path / 'manifest.json').write_text(json.dumps({'outputs': {'data.csv': sha256(b'original').hexdigest()}}))
    verify_manifest(tmp_path, 'manifest.json')
    path.write_text('changed')
    with pytest.raises(ValueError, match='Changed upstream'):
        verify_manifest(tmp_path, 'manifest.json')
