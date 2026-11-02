"""Physical units and fit rejection are contracts, not appearance checks."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from spectralbridge.radiometry import Radiometry, require_radiometry
from spectralbridge.corrections import fit_and_save_brdf_model, apply_brdf_correct


def cube(data, radiometry):
    result = SimpleNamespace(
        data=data,
        radiometry=radiometry,
        bands=data.shape[-1],
        mask_no_data=np.ones(data.shape[:2], bool),
        wavelengths=np.array([650.0, 860.0]),
        no_data=-9999.0,
    )
    result.get_ancillary = lambda name, radians=True: np.full(
        data.shape[:2], 0.4 if name == "solar_zn" else 0.0, np.float32
    )
    return result


def test_affine_roundtrip_and_unknown():
    r = Radiometry(0.0001, -0.1, "VALID", "calibration certificate fixture")
    stored = np.array([1000.0, 3500.0], np.float32)
    np.testing.assert_allclose(r.to_physical(stored), [0.0, 0.25], atol=3e-8)
    np.testing.assert_allclose(r.to_stored(r.to_physical(stored)), stored, atol=0.001)
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        require_radiometry(SimpleNamespace(scale_factor=1.0))


def test_nadir_rank_deficiency_is_persisted_and_cannot_be_applied(tmp_path):
    c = cube(
        np.full((8, 8, 2), 0.3, np.float32), Radiometry(1.0, 0.0, "VALID", "synthetic")
    )
    p = fit_and_save_brdf_model(c, tmp_path)
    m = json.loads(p.read_text())
    assert m["validation"]["status"] == "UNSUPPORTED"
    assert all(x["rank"] < 3 for x in m["validation"]["fits"])
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        apply_brdf_correct(c, c.data, 0, 8, 0, 8, coeff_path=p)


def test_unverified_goldhill_like_counts_do_not_acquire_calibration(tmp_path):
    c = cube(
        np.full((8, 8, 2), 250.0, np.float32),
        Radiometry(None, None, "UNSUPPORTED", "no calibration"),
    )
    p = fit_and_save_brdf_model(c, tmp_path)
    m = json.loads(p.read_text())
    assert m["validation"]["status"] == "UNSUPPORTED"
    assert m["radiometry"]["scale"] is None
    assert "iso" not in m


def test_kernels_match_pinned_hytools_and_nadir_azimuth_invariance():
    from pathlib import Path
    from spectralbridge.corrections import calc_geom_kernel, calc_volume_kernel

    fixture = json.loads(
        (Path(__file__).parent / "data/brdf/hytools_pinned_kernels.json").read_text()
    )
    angles = [np.array(a, np.float32) for a in fixture["angles_radians"]]
    np.testing.assert_allclose(
        calc_volume_kernel(*angles, kernel_type="RossThick"),
        fixture["RossThick"],
        atol=6e-7,
    )
    for kernel, b_r in [("LiSparseReciprocal", 1.0), ("LiDenseR", 10.0)]:
        np.testing.assert_allclose(
            calc_geom_kernel(*angles, kernel_type=kernel, b_r=b_r),
            fixture[kernel],
            atol=2e-6,
        )
        az = np.arange(12, dtype="float32").reshape(3, 4) * 0.5
        constant = np.full_like(az, 0.5)
        actual = calc_geom_kernel(
            az,
            constant,
            np.zeros_like(az),
            np.zeros_like(az),
            kernel_type=kernel,
            b_r=b_r,
        )
        np.testing.assert_allclose(actual, actual[0, 0], atol=1e-7)


def test_neon_divisor_and_explicit_offset_are_not_magnitude_inferred(tmp_path):
    import h5py
    from spectralbridge.io.neon import read_neon_reflectance_unitless

    with h5py.File(tmp_path / "source.h5", "w") as h:
        d = h.create_dataset(
            "Reflectance_Data", data=np.array([1000.0, 3500.0, -9999.0], np.float32)
        )
        d.attrs["Scale_Factor"] = 10000.0
        d.attrs["Data_Ignore_Value"] = -9999.0
        actual, raw_scale, _ = read_neon_reflectance_unitless(d)
        np.testing.assert_allclose(actual[:2], [0.1, 0.35], atol=3e-8)
        d.attrs["Add_Offset"] = -0.1
        with pytest.raises(ValueError, match="offset has no established convention"):
            read_neon_reflectance_unitless(d)
        d.attrs["spectralbridge_radiometry"] = json.dumps(
            Radiometry(
                0.0001,
                -0.1,
                "VALID",
                "Synthetic offset certificate with explicit direction",
            ).record()
        )
        actual, _, _ = read_neon_reflectance_unitless(d)
        np.testing.assert_allclose(actual[:2], [0.0, 0.25], atol=3e-8)
        assert np.isnan(actual[-1])
        assert raw_scale == 10000.0
        np.testing.assert_array_equal(d[:], [1000.0, 3500.0, -9999.0])


def test_full_rank_zero_prediction_is_invalid_not_unsupported(tmp_path):
    c = cube(
        np.zeros((8, 8, 2), np.float32),
        Radiometry(1.0, 0.0, "VALID", "synthetic zero-reflectance fixture"),
    )
    y, x = np.mgrid[:8, :8]
    c.get_ancillary = lambda name, radians=True: (
        np.full(x.shape, 0.6, np.float32)
        if name == "solar_zn"
        else (0.05 + 0.08 * x + 0.03 * y).astype(np.float32)
        if name == "sensor_zn"
        else (0.4 * y + 0.1 * x).astype(np.float32)
        if name == "sensor_az"
        else np.zeros(x.shape, np.float32)
    )
    p = fit_and_save_brdf_model(c, tmp_path)
    model = json.loads(p.read_text())
    assert all(r["rank"] == 3 for r in model["validation"]["fits"])
    assert model["validation"]["status"] == "INVALID"
    assert "iso" not in model
