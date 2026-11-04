"""Independent geometry/convention fixtures; no production observations fixed here."""

import numpy as np
import pytest
from pyproj import Transformer, Geod

from spectralbridge.drone_view_geometry import (
    NadirFootprint,
    camera_rays,
    footprint_candidates,
    assign_camera,
    aggregate_kernels,
)
from spectralbridge import corrections as c


def test_rays_are_to_sensor_not_camera_to_ground():
    ground = [[0, 0, 0]]
    cameras = [[0, 10, 10], [10, 0, 10], [0, -10, 10], [-10, 0, 10], [0, 0, 10]]
    zen, az, _ = camera_rays(ground, cameras, grid_to_true_deg=0)
    np.testing.assert_allclose(zen[0], np.deg2rad([45, 45, 45, 45, 0]))
    np.testing.assert_allclose(az[0], np.deg2rad([0, 90, 180, 270, 0]))


def test_invalid_height_and_unknown_rotation_are_not_zero_view():
    zen, az, _ = camera_rays([[0, 0, 2]], [[1, 1, 2], [1, 1, 1]], grid_to_true_deg=0)
    assert np.isnan(zen).all() and np.isnan(az).all()
    zen, _, _ = camera_rays([[0, 0, 0]], [[0, 0, 10]], grid_to_true_deg=np.nan)
    assert np.isnan(zen).all()


def test_true_north_conversion_matches_independent_geodesic():
    t = Transformer.from_crs(26913, 4326, always_xy=True)
    x, y = 450000.0, 4432000.0
    geod = Geod(ellps="GRS80")
    gamma = geod.inv(*t.transform(x, y), *t.transform(x, y + 10))[0]
    _, az, _ = camera_rays([[x, y, 0]], [[x, y + 10, 10]], grid_to_true_deg=gamma)
    np.testing.assert_allclose(az[0, 0] % (2 * np.pi), np.deg2rad(gamma) % (2 * np.pi))


def test_rotated_rectangle_and_unsupported_assignment():
    fp = NadirFootprint(4, 2, 1, 1000)
    delta = np.array([[[1.5, 0, 1], [0, 1.5, 1]], [[5, 5, 1], [6, 6, 1]]])
    good, center = footprint_candidates(delta, np.array([0.0, 0.0]), fp)
    assert good[0].tolist() == [True, False]
    assert assign_camera(delta, good, center, rule="nearest").tolist() == [0, -1]
    rotated, _ = footprint_candidates(delta, np.array([np.pi / 2, np.pi / 2]), fp)
    assert rotated[0].tolist() == [False, True]


def test_central_selection_can_differ_without_reading_reflectance():
    delta = np.array([[[0, 8, 10], [9, 0, 10]]])
    good, center = footprint_candidates(delta, [0, 0], NadirFootprint(4, 2, 1, 1000))
    assert assign_camera(delta, good, center, rule="nearest")[0] == 0
    assert assign_camera(delta, good, center, rule="central")[0] == 1


def test_kernel_mixture_is_not_kernel_of_mean_angles():
    az = np.deg2rad([[0, 180]])
    zen = np.deg2rad([[20, 20]])
    kv = c.calc_volume_kernel(0, 0.6, az, zen, "RossThick")
    kg = c.calc_geom_kernel(0, 0.6, az, zen, "LiDenseR", b_r=10, h_b=2)
    design = aggregate_kernels(kv, kg, [[True, True]])
    np.testing.assert_allclose(design[0, 1:], [kv.mean(), kg.mean()])
    wrong = c.calc_geom_kernel(0, 0.6, az.mean(), zen.mean(), "LiDenseR", b_r=10, h_b=2)
    assert not np.isclose(design[0, 2], wrong)
    absent = aggregate_kernels(kv, kg, [[False, False]])
    assert np.isnan(absent[0, 1:]).all()


def test_chunked_geometry_is_identical_and_deterministic():
    ground = np.array([[0, 0, 0], [1, 2, 3], [3, 4, 5]], float)
    cameras = np.array([[0, 2, 10], [4, 5, 11]], float)
    whole = camera_rays(ground, cameras, grid_to_true_deg=1)[0]
    parts = np.concatenate(
        [camera_rays(g[None], cameras, grid_to_true_deg=1)[0] for g in ground]
    )
    np.testing.assert_array_equal(whole, parts)


def test_invalid_dimensions_fail_explicitly():
    with pytest.raises(ValueError):
        NadirFootprint(0, 960, 5.5, 3.75)
    with pytest.raises(ValueError):
        camera_rays([1, 2, 3], [[0, 0, 10]], grid_to_true_deg=0)


def test_simulated_kernel_design_preserves_shared_fit_guards(tmp_path):
    """A mixture input changes design rows, never estimator or production status."""
    import importlib.util
    import hashlib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = root / "provenance/goldhill-viewing-geometry/2026-11-04/fit_experiments.py"
    spec = importlib.util.spec_from_file_location("p173_fixture_adapter", script)
    module = importlib.util.module_from_spec(spec)
    # Frozen research adapters use generic imports. Contain their import state
    # so this test cannot replace another investigation's `common` module.
    import sys
    original_path = sys.path[:]
    original_common = sys.modules.pop("common", None)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
        if original_common is None:
            sys.modules.pop("common", None)
        else:
            sys.modules["common"] = original_common
    yy, xx = np.mgrid[:20, :20]
    zen = 0.03 + xx * 0.025 + yy * 0.005
    az = xx * 0.24 + yy * 0.09
    kv = c.calc_volume_kernel(1.2, 0.6, az, zen, "RossThick")
    kg = c.calc_geom_kernel(1.2, 0.6, az, zen, "LiDenseR", b_r=10, h_b=2)
    design = np.stack([np.ones_like(kv), kv, kg], axis=-1)
    beta = np.array([0.4, 0.03, 0.02])
    data = np.repeat((design @ beta)[..., None], 10, axis=-1).astype("float32")
    geometry = dict(
        solar_az=np.full(xx.shape, np.rad2deg(1.2)),
        solar_zn=np.full(xx.shape, np.rad2deg(0.6)),
        sensor_az=np.zeros(xx.shape),
        sensor_zn=np.zeros(xx.shape),
    )
    cube = module.Cube(data, np.ones(xx.shape, bool), geometry, scale=1)
    identity = hashlib.sha256(design.tobytes()).hexdigest()
    original = c._brdf_design
    fitter = module.blend_adapter(c.fit_and_save_brdf_model, design, identity)
    path = fitter(
        cube, tmp_path / "model", brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG
    )
    import json

    model = json.loads(path.read_text())
    assert model["validation"]["status"] == "VALID"
    assert model["radiometry"]["status"] == "HYPOTHETICAL_UNVERIFIED"
    assert all(row["eligible"] == 400 for row in model["validation"]["fits"])
    assert c._brdf_design is original
    with pytest.raises(ValueError, match="HYPOTHETICAL_UNVERIFIED"):
        cube.radiometry.require_valid()
    apply = module.blend_adapter(c.apply_brdf_correct, design, identity)
    corrected = apply(
        cube,
        data,
        0,
        20,
        0,
        20,
        coeff_path=path,
        brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    reference = (
        c._reference_design(c.ReferenceGeometry(), c.HYTOOLS_BRDF_KERNEL_CONFIG) @ beta
    )
    np.testing.assert_allclose(corrected, reference, rtol=1e-5)
