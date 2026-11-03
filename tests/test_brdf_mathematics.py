"""Published-equation fixtures and independent mathematical BRDF properties."""

import json
from pathlib import Path

import numpy as np
import pytest

from spectralbridge import corrections as c

REFERENCE = json.loads(
    (Path(__file__).parent / "data/brdf/published_equation_references.json").read_text()
)


@pytest.mark.parametrize("kernel", ["RossThick", "LiDenseR", "LiSparseReciprocal"])
def test_independent_60_digit_published_reference_values(kernel):
    for row in REFERENCE["rows"]:
        angles = np.deg2rad([0, row["solar_deg"], row["relative_deg"], row["view_deg"]])
        function = c.calc_volume_kernel if kernel == "RossThick" else c.calc_geom_kernel
        kwargs = {} if kernel == "RossThick" else dict(b_r=row["b_r"], h_b=row["h_b"])
        actual = function(*angles, kernel_type=kernel, **kwargs)
        # Grazing derivatives amplify binary64 input-angle representation error.
        rtol = 2e-9 if max(row["solar_deg"], row["view_deg"]) > 89 else 3e-12
        np.testing.assert_allclose(
            actual, row[kernel], rtol=rtol, atol=3e-12, err_msg=str(row)
        )


@pytest.mark.parametrize("kernel", ["RossThick", "LiDenseR", "LiSparseReciprocal"])
def test_nadir_invariance_reciprocity_and_wrapping(kernel):
    function = c.calc_volume_kernel if kernel == "RossThick" else c.calc_geom_kernel
    for zenith in np.deg2rad([0, 5, 10, 30, 45, 60, 89.9]):
        azimuth = np.deg2rad([0, 45, 90, 135, 180, 360, -360])
        result = function(0.3, zenith, azimuth, 0, kernel_type=kernel)
        np.testing.assert_allclose(result, result[0], atol=3e-14, rtol=3e-14)
    s = np.deg2rad(np.array([0, 5, 30, 45, 60, 89]))
    v = s[::-1]
    az = np.deg2rad(np.array([0, 45, 90, 135, 180, 360]))
    result = function(0, s, az, v, kernel_type=kernel)
    reciprocal = function(az, v, 0, s, kernel_type=kernel)
    np.testing.assert_allclose(result, reciprocal, rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(
        result,
        function(2 * np.pi, s, az - 4 * np.pi, v, kernel_type=kernel),
        rtol=2e-13,
        atol=2e-13,
    )
    assert function(0, 0, 0, 0, kernel_type=kernel) == pytest.approx(0, abs=1e-15)


@pytest.mark.parametrize("kernel", ["RossThick", "LiDenseR", "LiSparseReciprocal"])
def test_scalar_vector_and_raster_broadcasting_invalid_geometry(kernel):
    function = c.calc_volume_kernel if kernel == "RossThick" else c.calc_geom_kernel
    solar = np.deg2rad(np.array([5.0, 30.0, 60.0]))[:, None]
    view = np.deg2rad(np.array([0.0, 10.0, 45.0, 80.0]))[None, :]
    raster = function(0, solar, 1.2, view, kernel_type=kernel)
    assert raster.shape == (3, 4) and raster.dtype == np.float64
    for i in range(3):
        for j in range(4):
            assert raster[i, j] == function(
                0, solar[i, 0], 1.2, view[0, j], kernel_type=kernel
            )
    for bad in [np.nan, np.inf, -0.01, np.pi / 2, np.pi]:
        assert np.isnan(function(0, bad, 0, 0, kernel_type=kernel))
        assert np.isnan(function(0, 0, 0, bad, kernel_type=kernel))
    assert np.isnan(function(np.inf, 0, 0, 0, kernel_type=kernel))
    with pytest.raises(ValueError):
        function(0, np.zeros((2, 3)), 0, np.zeros((4, 2)), kernel_type=kernel)


def test_dense_is_not_sparse_and_shape_is_not_an_amplitude_multiplier():
    a = np.deg2rad([0, 30, 90, 45])
    dense = c.calc_geom_kernel(*a, kernel_type="LiDenseR", b_r=2.5)
    sparse = c.calc_geom_kernel(*a, kernel_type="LiSparseReciprocal", b_r=2.5)
    assert abs(dense - sparse) > 0.1
    base = c.calc_geom_kernel(*a, kernel_type="LiDenseR", b_r=1)
    assert not np.isclose(dense, 2.5 * base)
    for bad in [0, -1, np.inf, np.nan, [1, 2]]:
        with pytest.raises(ValueError, match="crown parameters"):
            c.calc_geom_kernel(*a, kernel_type="LiDenseR", b_r=bad)


def test_opposite_grazing_rays_preserve_small_phase_complement():
    theta = np.deg2rad(89.999999)
    secant = np.hypot(1, np.tan(theta))
    # Equal transformed zeniths, opposite azimuths, h/b=2 -> no overlap.
    # Analytically (1+cos(2 theta))*sec(theta)^2 = 2 exactly.
    dense = c.calc_geom_kernel(0, theta, np.pi, theta, kernel_type="LiDenseR")
    sparse = c.calc_geom_kernel(
        0, theta, np.pi, theta, kernel_type="LiSparseReciprocal"
    )
    assert dense == pytest.approx(1 / secant - 2, abs=1e-15)
    assert sparse == pytest.approx(1 - 2 * secant, abs=3e-8)


def test_nonreciprocal_names_cannot_silently_select_reciprocal_kernels():
    for name in ["li_dense", "li_sparse"]:
        with pytest.raises(ValueError, match="Ambiguous nonreciprocal"):
            c.calc_geom_kernel(0, 0.3, 1, 0.2, kernel_type=name)
    assert c.calc_geom_kernel(
        0, 0.3, 1, 0.2, kernel_type="LiSparseR"
    ) == c.calc_geom_kernel(0, 0.3, 1, 0.2, kernel_type="LiSparseReciprocal")


def test_model_math_version_prevents_application_and_cache_reuse(tmp_path):
    from types import SimpleNamespace
    from spectralbridge.radiometry import Radiometry

    y, x = np.mgrid[:8, :8]
    angles = [
        np.zeros((8, 8)),
        np.full((8, 8), 0.6),
        x * 0.35,
        0.05 + x * 0.04 + y * 0.03,
    ]
    kv = c.calc_volume_kernel(*angles, kernel_type="RossThick")
    kg = c.calc_geom_kernel(*angles, kernel_type="LiSparseReciprocal")
    data = (0.3 + 0.02 * kv + 0.01 * kg)[..., None].astype(np.float32)
    cube = SimpleNamespace(
        data=data,
        radiometry=Radiometry(1.0, 0.0, "VALID", "Synthetic equation control"),
        bands=1,
        mask_no_data=np.ones((8, 8), bool),
        wavelengths=np.array([650]),
        no_data=-9999.0,
    )
    cube.get_ancillary = lambda name, radians=True: (
        angles[["solar_az", "solar_zn", "sensor_az", "sensor_zn"].index(name)]
        if radians
        else np.rad2deg(
            angles[["solar_az", "solar_zn", "sensor_az", "sensor_zn"].index(name)]
        )
    )
    path = c.fit_and_save_brdf_model(cube, tmp_path)
    model = json.loads(path.read_text())
    assert model["validation"]["status"] == "VALID"
    assert model["kernel_math_version"] == c.BRDF_KERNEL_MATH_VERSION
    current = c.apply_brdf_correct(cube, data, 0, 8, 0, 8, coeff_path=path)
    assert current.shape == data.shape and current.dtype == np.float32
    original_view = angles[3][0, 0]
    angles[3][0, 0] = -0.1
    masked = c.apply_brdf_correct(cube, data, 0, 8, 0, 8, coeff_path=path)
    assert masked[0, 0, 0] == cube.no_data
    assert np.isfinite(masked[1:, :, :]).all()
    angles[3][0, 0] = original_view
    model.pop("kernel_math_version")
    path.write_text(json.dumps(model))
    historical_bytes = path.read_bytes()
    with pytest.raises(ValueError, match="kernel mathematics"):
        c.apply_brdf_correct(cube, data, 0, 8, 0, 8, coeff_path=path)
    with pytest.raises(ValueError, match="stale or unvalidated"):
        c.fit_and_save_brdf_model(cube, tmp_path)
    assert path.read_bytes() == historical_bytes


def test_invalid_reference_and_design_are_explicit():
    with pytest.raises(ValueError, match="reference geometry"):
        c._reference_design(
            c.ReferenceGeometry(solar_zenith_deg=90), c.BRDFKernelConfig()
        )
    from types import SimpleNamespace

    angles = {
        "solar_zn": np.array([[0.3, 0.3]]),
        "solar_az": np.zeros((1, 2)),
        "sensor_zn": np.array([[0.1, -0.1]]),
        "sensor_az": np.zeros((1, 2)),
    }
    cube = SimpleNamespace(
        mask_no_data=np.ones((1, 2), bool),
        get_ancillary=lambda name, radians=True: angles[name],
    )
    design, valid, _ = c._brdf_design(cube, c.BRDFKernelConfig())
    np.testing.assert_array_equal(valid, [[True, False]])
    assert np.isnan(design[0, 1, 1:]).all()
