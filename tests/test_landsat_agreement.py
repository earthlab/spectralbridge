"""Real-sensor agreement contracts: physical support, units and uncertainty."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from spectralbridge.landsat_agreement import (
    ReferenceGrid,
    mask_landsat_qa,
    scale_landsat_sr,
    spectral_angle,
    deming_regression,
    compute_agreement_metrics,
    spatial_bootstrap_indices,
    aggregate_to_landsat_grid,
)


def write(path, array, transform=None, crs="EPSG:32613", scale=True):
    if array.ndim == 2:
        array = np.broadcast_to(array, (7, *array.shape)).copy()
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=array.shape[2],
        height=array.shape[1],
        count=7,
        dtype="float32",
        crs=crs,
        transform=transform or from_origin(500000, 4400000, 1, 1),
        nodata=-9999,
    ) as dst:
        dst.write(array.astype("float32"))
        if scale:
            dst.update_tags(ns="ENVI", reflectance_scale_factor="1")
    return path


def test_qa_all_required_flags_saturation_and_terrain():
    q = np.array([0, *[1 << i for i in range(6)], 1 << 7], np.uint16)
    valid, category = mask_landsat_qa(q, np.zeros_like(q))
    assert valid.tolist() == [True, False, False, False, False, False, False, True]
    valid, _ = mask_landsat_qa(
        np.zeros(4, np.uint16), np.array([0, 1, 1 << 11, 1 << 8])
    )
    assert valid.tolist() == [True, False, False, True]
    assert set(category) == {0, 1, 2, 3, 4}


def test_official_scale_offset_and_negative_reflectance_not_clipped():
    result = scale_landsat_sr([0, 1, 10000, 65455, 65535])
    assert np.isnan(result[[0, 4]]).all()
    np.testing.assert_allclose(result[1:4], [-0.1999725, 0.075, 1.6000125])


def test_partial_coverage_not_normalized_to_full_support(tmp_path):
    path = write(tmp_path / "half.tif", np.ones((30, 15)))
    grid = ReferenceGrid(
        "EPSG:32613", tuple(from_origin(500000, 4400000, 30, 30)), 1, 1
    )
    r = aggregate_to_landsat_grid({"undarkened": path}, grid)
    np.testing.assert_allclose(r["coverage_fraction"], 0.5)
    np.testing.assert_allclose(r["valid_fraction"], 1)
    np.testing.assert_allclose(r["valid_coverage_fraction"], 0.5)
    assert r["contributing_pixels"][0, 0] == 450
    np.testing.assert_allclose(r["means"]["undarkened"], 1)


def test_joint_variant_mask_and_exact_variance(tmp_path):
    array = np.ones((30, 30))
    array[:, 15:] = 3
    adjusted = array * 2
    adjusted[:15, :] = -9999
    p = write(tmp_path / "u.tif", array)
    q = write(tmp_path / "a.tif", adjusted)
    grid = ReferenceGrid(
        "EPSG:32613", tuple(from_origin(500000, 4400000, 30, 30)), 1, 1
    )
    r = aggregate_to_landsat_grid({"u": p, "a": q}, grid)
    np.testing.assert_allclose(r["means"]["u"], 2)
    np.testing.assert_allclose(r["means"]["a"], 4)
    np.testing.assert_allclose(r["variances"]["u"], 1)
    assert r["contributing_pixels"][0, 0] == 450
    np.testing.assert_allclose(r["valid_coverage_fraction"], 0.5)


def test_offsets_are_explicit_and_do_not_mutate_source(tmp_path):
    array = np.ones((30, 60))
    array[:, 30:] = 2
    p = write(tmp_path / "u.tif", array)
    before = p.read_bytes()
    grid = ReferenceGrid(
        "EPSG:32613", tuple(from_origin(500000, 4400000, 30, 30)), 2, 1
    )
    base = aggregate_to_landsat_grid({"u": p}, grid)
    shifted = aggregate_to_landsat_grid({"u": p}, grid, offset_m=(30.0, 0.0))
    np.testing.assert_allclose(base["means"]["u"][0], [[1, 2]])
    assert np.isnan(shifted["means"]["u"][0, 0, 0])
    assert shifted["means"]["u"][0, 0, 1] == 1
    assert p.read_bytes() == before


def test_missing_scale_metadata_refuses_numeric_guess(tmp_path):
    p = write(tmp_path / "u.tif", np.ones((30, 30)) * 1000, scale=False)
    grid = ReferenceGrid(
        "EPSG:32613", tuple(from_origin(500000, 4400000, 30, 30)), 1, 1
    )
    with pytest.raises(ValueError, match="scale metadata"):
        aggregate_to_landsat_grid({"u": p}, grid)


def test_correlated_but_biased_is_not_agreement():
    x = np.array([0.1, 0.2, 0.3, 0.4])
    y = x * 2 + 0.01
    metrics = compute_agreement_metrics(x, y)
    assert metrics["Pearson_r"] > 0.999
    assert metrics["RMSE"] > 0.2
    assert metrics["identity_r2"] < 0
    slope, intercept = deming_regression(x, y)
    np.testing.assert_allclose([slope, intercept], [2, 0.01])
    assert compute_agreement_metrics([np.nan], [1])["N"] == 0


def test_spectral_angle_scale_invariance_and_zero_guard():
    a = np.arange(1, 8)[None, :].astype(float)
    np.testing.assert_allclose(spectral_angle(a, a * 2), 0, atol=1e-6)
    assert np.isnan(spectral_angle(np.zeros_like(a), a))[0]


def test_bootstrap_samples_whole_spatial_blocks():
    rows = np.repeat([0, 10], 4)
    cols = np.tile(np.arange(4), 2)
    draws, n = spatial_bootstrap_indices(rows, cols, replicates=39, seed=4)
    assert n == 2
    for draw in draws:
        multiplicities = np.bincount(draw, minlength=8)
        assert len(set(multiplicities[:4])) == 1
        assert len(set(multiplicities[4:])) == 1
    assert any(len(set(draw)) < 8 for draw in draws)


def test_cross_crs_true_footprint_intersections(tmp_path):
    path = write(
        tmp_path / "geographic.tif",
        np.full((4, 4), 0.25),
        transform=from_origin(0, 0.0003, 0.0001, 0.0001),
        crs="EPSG:4326",
    )
    grid = ReferenceGrid("EPSG:3857", tuple(from_origin(5, 25, 10, 10)), 1, 1)
    result = aggregate_to_landsat_grid({"u": path}, grid)
    assert result["method"] == "transformed_source_cell_polygon_intersection"
    np.testing.assert_allclose(result["valid_coverage_fraction"], 1, atol=1e-6)
    np.testing.assert_allclose(result["means"]["u"], 0.25)
    assert result["contributing_pixels"][0, 0] >= 4
    with pytest.raises(ValueError, match="matching projected CRS"):
        aggregate_to_landsat_grid({"u": path}, grid, offset_m=(30, 0))


def test_missing_data_metrics_and_unmatched_grids(tmp_path):
    assert compute_agreement_metrics([np.nan], [1])["N"] == 0
    p = write(tmp_path / "p.tif", np.ones((30, 30)))
    q = write(
        tmp_path / "q.tif",
        np.ones((30, 30)),
        transform=from_origin(500001, 4400000, 1, 1),
    )
    grid = ReferenceGrid(
        "EPSG:32613", tuple(from_origin(500000, 4400000, 30, 30)), 1, 1
    )
    with pytest.raises(ValueError, match="identical source pixel grid"):
        aggregate_to_landsat_grid({"u": p, "a": q}, grid)
