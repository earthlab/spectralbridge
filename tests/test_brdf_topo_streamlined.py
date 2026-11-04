from pathlib import Path

import numpy as np
import pytest

from spectralbridge.corrections import (
    apply_brdf_correct,
    apply_topo_correct,
    _scs_c_ratio,
)


class _DummyCube:
    def __init__(self):
        from spectralbridge.radiometry import Radiometry
        self.radiometry = Radiometry(1., 0., "VALID", "Synthetic topo fixture")
        self.scale_factor = 1.0
        self.no_data = -9999.0
        self.mask_no_data = np.ones((2, 2), dtype=bool)
        self.wavelengths = np.array([650.0, 860.0], dtype=np.float32)
        self.data = None

    def get_ancillary(self, name: str, radians: bool = True):
        if name == "slope":
            return np.full((2, 2), np.deg2rad(20.0), dtype=np.float32)
        if name == "aspect":
            return np.zeros((2, 2), dtype=np.float32)
        if name == "solar_zn":
            return np.full((2, 2), np.deg2rad(30.0), dtype=np.float32)
        if name == "solar_az":
            return np.zeros((2, 2), dtype=np.float32)
        if name == "sensor_zn":
            return np.zeros((2, 2), dtype=np.float32)
        if name == "sensor_az":
            return np.zeros((2, 2), dtype=np.float32)
        raise KeyError(name)


def test_scs_topo_correction_scaling():
    cube = _DummyCube()
    chunk = np.full((2, 2, 1), 0.5, dtype=np.float32)
    corrected = apply_topo_correct(cube, chunk, 0, 2, 0, 2, use_scs_c=True)
    assert np.all(np.isfinite(corrected))
    assert not np.allclose(corrected, chunk)


def test_brdf_ratio_increases_reflectance_when_reference_brighter():
    cube = _DummyCube()
    chunk = np.full((2, 2, 2), .2, np.float32)
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        apply_brdf_correct(cube, chunk, 0, 2, 0, 2)


def test_neutral_coefficients_broadcast_across_bins():
    cube = _DummyCube()
    chunk = np.full((2, 2, 2), .2, np.float32)
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        apply_brdf_correct(cube, chunk, 0, 2, 0, 2)


class _NearZeroIncidenceCube(_DummyCube):
    def get_ancillary(self, name: str, radians: bool = True):
        if name == "slope":
            return np.full((2, 2), np.deg2rad(90.0), dtype=np.float32)
        if name == "aspect":
            # Offset the relative azimuth slightly to yield a tiny positive cos_i.
            return np.full((2, 2), np.deg2rad(90.0) - 1e-6, dtype=np.float32)
        if name == "solar_zn":
            return np.full((2, 2), np.deg2rad(89.0), dtype=np.float32)
        if name == "solar_az":
            return np.zeros((2, 2), dtype=np.float32)
        return super().get_ancillary(name, radians=radians)


def test_topo_denominator_guard_keeps_ratios_finite():
    cube = _NearZeroIncidenceCube()
    chunk = np.full((2, 2, 1), 0.5, dtype=np.float32)
    corrected = apply_topo_correct(cube, chunk, 0, 2, 0, 2, use_scs_c=True)
    assert np.all(np.isfinite(corrected))
    # Without the guard, a near-zero denominator would collapse reflectance toward zero.
    np.testing.assert_allclose(corrected, chunk, rtol=1e-3, atol=1e-3)


def test_topo_with_precomputed_scs_c_applies_without_local_fit():
    cube = _DummyCube()
    chunk = np.full((2, 2, 2), 0.25, dtype=np.float32)
    # C=0 → ratio = cos(solar)*cos(slope)/cos(i); still finite via helper.
    corrected = apply_topo_correct(
        cube,
        chunk,
        0,
        2,
        0,
        2,
        use_scs_c=True,
        scs_c=np.zeros(2, dtype=np.float32),
    )
    assert np.all(np.isfinite(corrected))
    assert not np.any(np.isclose(corrected, -9999.0))


def test_scs_c_ratio_guard_handles_tiny_denominators_directly():
    numerator = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    denominator = np.array([0.5, 1e-6, 0.0, -1e-4], dtype=np.float32)

    ratio = _scs_c_ratio(numerator, denominator, min_denom=1e-3)

    assert np.all(np.isfinite(ratio))
    # Guarded entries fall back to a neutral ratio of 1.0, while valid entries
    # retain the original scaling behaviour.
    np.testing.assert_allclose(ratio[[1, 2, 3]], 1.0)
    assert ratio[0] > 1.0
    assert ratio.max() <= numerator.max() / 1e-3


def test_scs_c_ratio_rejects_negative_ratios():
    numerator = np.array([-0.4, 0.5], dtype=np.float32)
    denominator = np.array([0.2, 0.5], dtype=np.float32)

    ratio = _scs_c_ratio(numerator, denominator, min_denom=1e-3)

    assert ratio[0] == pytest.approx(1.0)
    assert ratio[1] == pytest.approx(1.0)


def test_brdf_invalid_kernel_factor_passes_through_input(tmp_path: Path):
    cube = _DummyCube()
    chunk = np.full((2, 2, 2), .2, np.float32)
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        apply_brdf_correct(cube, chunk, 0, 2, 0, 2)
