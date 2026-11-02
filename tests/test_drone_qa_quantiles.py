"""Exact, bounded QA quantiles must match NumPy including missing data."""
import warnings

import numpy as np
import pytest

from spectralbridge.qa_plots import _drone_spatial_delta_quantiles


@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_exact_quantiles_match_numpy_with_partial_and_all_nan_pixels(dtype):
    rng = np.random.default_rng(14)
    values = rng.normal(size=(10, 17, 13)).astype(dtype)
    values[rng.random(values.shape) < .3] = np.nan
    values[:, 0, 0] = np.nan
    values[:, 1, 1] = 0
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        expected_median = np.nanmedian(values, axis=0)
        expected_p90 = np.nanpercentile(values, 90, axis=0)
        median, p90 = _drone_spatial_delta_quantiles(values, chunk_pixels=19)
    np.testing.assert_array_equal(median, expected_median)
    np.testing.assert_array_equal(p90, expected_p90)
    assert median.dtype == expected_median.dtype


def test_quantiles_preserve_infinite_value_semantics():
    values = np.array([[[np.inf, -np.inf, np.nan]], [[np.inf, np.inf, np.nan]],
                       [[1., 1., np.nan]]], dtype='float32')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        median, p90 = _drone_spatial_delta_quantiles(values, chunk_pixels=2)
        np.testing.assert_array_equal(median, np.nanmedian(values, axis=0))
        np.testing.assert_array_equal(p90, np.nanpercentile(values, 90, axis=0))
