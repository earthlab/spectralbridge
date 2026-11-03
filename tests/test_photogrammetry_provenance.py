"""Isolated provenance diagnostics; no production algorithm change."""

import importlib.util
from pathlib import Path
import numpy as np

P = (
    Path(__file__).resolve().parents[1]
    / "provenance/photogrammetry-metadata/2026-11-02/validate.py"
)
spec = importlib.util.spec_from_file_location("metadata_provenance_validation", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_aspect_is_downslope_clockwise_from_north():
    yy, xx = np.mgrid[:7, :7]
    slope, aspect = m.horn_terrain(xx, 1, 1)
    np.testing.assert_allclose(slope[2:5, 2:5], 45)
    np.testing.assert_allclose(aspect[2:5, 2:5], 270)
    slope, aspect = m.horn_terrain(-yy, 1, 1)
    np.testing.assert_allclose(slope[2:5, 2:5], 45)
    np.testing.assert_allclose(aspect[2:5, 2:5], 180)


def test_terrain_preserves_missing_neighbour_support():
    z = np.ones((7, 7))
    z[3, 3] = -9999
    slope, aspect = m.horn_terrain(z, 1, 1, -9999)
    assert np.isnan(slope[2:5, 2:5]).all()
    assert np.isnan(aspect[2:5, 2:5]).all()
    assert np.isnan(slope[0]).all()
    assert np.isfinite(slope[1, 1])


def test_circular_residuals_cross_north_correctly():
    np.testing.assert_allclose(
        m.circular_difference([359, 1, 180], [1, 359, 0]), [-2, 2, -180]
    )


def test_numeric_fingerprint_is_never_automatically_calibration():
    # A missing observational population remains missing in compact summaries.
    assert m.summary([np.nan]) == {"n": 0}
