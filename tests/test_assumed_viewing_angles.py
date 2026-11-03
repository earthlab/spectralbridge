"""Independent geometry/compact-reduction checks for the read-only experiment."""

from pathlib import Path
import importlib.util
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "assumed_views", ROOT / "provenance/assumed-viewing-angles/2026-11-03/analyze.py"
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def test_relative_azimuth_is_converted_to_absolute_and_wraps():
    solar = np.array([350.0, 10.0, 200.0], np.float32)
    sensor = a.relative_to_absolute(solar, 45.0)
    np.testing.assert_allclose(sensor, [35.0, 55.0, 245.0])
    # Independent circular difference, rather than treating 45 as absolute north.
    np.testing.assert_allclose((sensor - solar + 180) % 360 - 180, 45.0)


def test_weighted_singular_values_match_all_repeated_rows():
    sa = np.array([231.401, 231.404, 231.407], np.float32)
    weights = np.array([5, 9, 6])
    scene = float(np.deg2rad(np.float32(35.567)))
    result = a.constant_case(sa, weights, scene, 15, 45)
    full = np.repeat(sa, weights)[None, :]
    X, _ = a.design(
        full,
        np.full_like(full, np.rad2deg(scene)),
        a.relative_to_absolute(full, 45),
        np.full_like(full, 15),
        np.ones(full.shape, bool),
        scene,
    )
    np.testing.assert_allclose(
        result["singular_values"],
        np.linalg.svd(X.reshape(-1, 3).astype(float), compute_uv=False),
        atol=2e-14,
    )
    assert not result["angular_numerical_gate"]
    assert result["canonical_constant_relative_rank"] == 1


def test_nadir_kernel_does_not_invent_azimuth_observations():
    sa = np.array([172.0, 231.0], np.float32)
    scene = float(np.deg2rad(np.float32(30)))
    rows = [
        a.constant_case(sa, np.array([10, 10]), scene, 0, rel)
        for rel in [0, 45, 90, 135, 180]
    ]
    for row in rows[1:]:
        np.testing.assert_allclose(
            [row["RossThick"], row["LiDenseR"]],
            [rows[0]["RossThick"], rows[0]["LiDenseR"]],
            atol=1e-6,
        )
    assert all(not row["angular_numerical_gate"] for row in rows)


@pytest.mark.parametrize("name", a.SCENARIOS)
def test_synthetic_angles_are_bounded_and_deterministic(name):
    z, az = a.scenario_map(name, 0, 35, 35, 48, 0.1, 117)
    zz, aa = a.scenario_map(name, 0, 35, 35, 48, 0.1, 117)
    np.testing.assert_array_equal(z, zz)
    np.testing.assert_array_equal(az, aa)
    assert (z >= 0).all() and (z <= 30).all()
    assert (az >= 0).all() and (az < 360).all()


def test_full_numerical_rank_is_not_physical_acceptance():
    z, az = a.scenario_map("smooth_map", 0, 35, 35, 48, 0.1, 117)
    sa = np.full(z.shape, 231, np.float32)
    X, valid = a.design(
        sa,
        np.full(z.shape, 35, np.float32),
        az,
        z,
        np.ones(z.shape, bool),
        float(np.deg2rad(35)),
    )
    A = X[valid].astype(float)
    d = a.diagnostics(np.linalg.svd(A, compute_uv=False), len(A))
    assert d["rank"] == 3 and d["angular_numerical_gate"]
    assert d["model_status"].startswith("UNSUPPORTED")
    assert d["supported_bands"] == 0


def test_weighted_percentiles_match_expanded_population():
    x = np.array([3.0, 1.0, 7.0])
    weights = np.array([4, 3, 2])
    np.testing.assert_allclose(
        a.weighted_quantiles(x, weights),
        np.percentile(np.repeat(x, weights), [0, 1, 50, 99, 100]),
    )


def test_transparent_finite_background_cannot_bias_polygon_spectrum():
    import geopandas as gpd
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import box

    raw = np.broadcast_to(
        np.array([[1.0, 2.0], [3.0, 65535.0]], np.float32)[..., None], (2, 2, 10)
    ).copy()
    alpha = np.array([[10000.0, 10000.0], [10000.0, 0.0]], np.float32)
    mask = a.spectral_valid_mask(np.isfinite(raw).all(-1), alpha)
    frame = gpd.GeoDataFrame(
        dict(GlobalID=["target"], cover_category=["Evergreen"], species=["fixture"]),
        geometry=[box(0, 0, 2, 2)],
        crs="EPSG:26913",
    )
    with rasterio.MemoryFile() as mem:
        with mem.open(
            driver="GTiff",
            width=2,
            height=2,
            count=10,
            dtype="float32",
            crs="EPSG:26913",
            transform=from_origin(0, 2, 1, 1),
        ) as src:
            rows = a.baseline_polygons("fixture", src, raw, mask, frame, {"target"})
    assert len(rows) == 1 and rows[0]["pixels"] == 3
    assert rows[0]["b1"] == 2.0
    assert raw[1, 1, 0] == 65535.0  # Original numerical data are not changed.
