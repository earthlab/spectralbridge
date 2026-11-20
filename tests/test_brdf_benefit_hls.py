"""Official HLS counterfactual arithmetic is not a new calibration model."""

import importlib
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
hls = importlib.import_module("brdf_benefit_hls")
sys.path.pop(0)
pytestmark = pytest.mark.skipif(
    shutil.which("cc") is None, reason="Official reference kernels require a C compiler"
)


def test_no_adjustment_at_identical_nadir_reference_geometry():
    out = hls.factors(
        np.array([35.0, 35.0]), np.array([0.0, 0.0]), np.array([0.0, 180.0]), 35.0
    )
    np.testing.assert_array_equal(out, np.ones((2, 7)))


def test_reconstruction_has_only_the_expected_original_rounding_error():
    cf = hls.factors(
        np.array([40.0, 50.0]), np.array([8.0, 13.0]), np.array([25.0, 190.0]), 45.0
    )
    before = np.full((2, 7), 0.23742)
    encoded = np.floor(before * cf * 10000 + 0.5) / 10000
    reconstructed = encoded / cf
    assert np.all(abs(reconstructed - before) <= 0.00005 / cf + 1e-15)
    np.testing.assert_allclose(reconstructed * cf, encoded, rtol=1e-14)
    np.testing.assert_array_equal(cf[:, 0], cf[:, 1])


def test_unsupported_angle_fill_or_geometry_is_rejected():
    with pytest.raises(ValueError, match="physical domain"):
        hls.factors(np.array([400.0]), np.array([1.0]), np.array([0.0]), 45.0)
    with pytest.raises(ValueError, match="Finite angles"):
        hls.factors(np.array([np.nan]), np.array([1.0]), np.array([0.0]), 45.0)
