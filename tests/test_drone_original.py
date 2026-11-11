"""Original-photo experiment contracts and independent synthetic identifiability."""

import numpy as np
import pytest
from spectralbridge.drone_original import (
    calibrated_integer_to_fraction,
    fit_target_effects,
    fit_target_amplitudes,
    apply_supported_factors,
    reference_in_hull,
    prepare_calibrated_orthomosaic,
)


def test_vendor_encoding_is_not_raw_black_subtraction_or_uint16_range():
    np.testing.assert_allclose(
        calibrated_integer_to_fraction([0, 32768, 65535]), [0, 1, 65535 / 32768]
    )
    with pytest.raises(ValueError):
        calibrated_integer_to_fraction([1], scale=0)


def test_target_effects_separate_spatial_signal_from_angular_signal():
    rng = np.random.default_rng(9)
    targets = np.repeat(np.arange(20), 8)
    x = rng.normal(size=(160, 2)) + targets[:, None] * 0.05
    y = targets * 0.2 + x @ np.array([0.3, -0.15])
    fit = fit_target_effects(np.c_[np.ones(160), x], y, targets)
    np.testing.assert_allclose(fit["angular_beta"], [0.3, -0.15], atol=1e-10)
    np.testing.assert_allclose(fit["residual"], 0, atol=1e-10)
    with pytest.raises(ValueError, match="unsupported"):
        fit_target_effects(np.c_[np.ones(160), x[:, 0], x[:, 0]], y, targets)


def test_multiplicative_shape_recovers_target_amplitudes():
    rng = np.random.default_rng(8)
    targets = np.repeat(np.arange(16), 10)
    X = np.c_[np.ones(160), rng.uniform(-0.1, 0.1, 160), rng.uniform(-1.5, 0.8, 160)]
    expected = np.array([1.0, 0.7, -0.12])
    y = (0.1 + targets * 0.03) * (X @ expected)
    fit = fit_target_amplitudes(X, y, targets)
    np.testing.assert_allclose(fit["beta"], expected, rtol=1e-5)
    np.testing.assert_allclose(fit["amplitudes"], 0.1 + np.arange(16) * 0.03, rtol=1e-5)


def test_combined_application_never_fills_a_failed_stage_with_identity():
    out, valid = apply_supported_factors(
        [0.2, 0.3, 0.4, 1.2],
        [2, 2, -1, 1],
        [1.5] * 4,
        topo_supported=[True, False, True, True],
        brdf_supported=True,
    )
    np.testing.assert_allclose(out[[0, 3]], [0.6, 1.8])
    assert np.isnan(out[1:3]).all()
    assert valid.tolist() == [True, False, False, True]


def test_joint_support_rejects_reference_inside_marginal_ranges_only():
    X = np.array([[1, 0, 0], [1, 1, 0], [1, 0, 1]])
    assert reference_in_hull(X, [1, 0.2, 0.2])
    assert not reference_in_hull(X, [1, 0.9, 0.9])


def test_immutable_radiometry_preserves_grid_alpha_and_values_above_one(tmp_path):
    import rasterio
    from rasterio.transform import from_origin

    transform = from_origin(450000, 4400000, 0.1, 0.1)
    source = tmp_path / "source.tif"
    a = np.full((11, 8, 8), 49152, "uint16")
    a[10] = 65535
    a[10, 0, 0] = 0
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        width=8,
        height=8,
        count=11,
        dtype="uint16",
        crs="EPSG:26913",
        transform=transform,
    ) as d:
        d.write(a)
    destination = tmp_path / "new.tif"
    kwargs = dict(
        wavelengths_nm=[444, 475, 531, 560, 650, 668, 705, 717, 740, 842],
        source_scale=1 / 32768,
        source_offset=0.0,
        provenance={"synthetic": True},
        target_transform=transform,
        target_shape=(8, 8),
    )
    first = prepare_calibrated_orthomosaic(source, destination, **kwargs)
    with rasterio.open(destination) as d:
        assert d.transform == transform
        assert d.scales == (0.0001,) * 10
        assert d.read(1)[1, 1] == 15000
        assert d.dataset_mask()[0, 0] == 0
        assert np.isnan(d.read(1)[0, 0])
    assert prepare_calibrated_orthomosaic(source, destination, **kwargs) == first
    with pytest.raises(FileExistsError):
        prepare_calibrated_orthomosaic(
            source, destination, **(kwargs | {"source_scale": 1 / 65535})
        )


def test_ecef_ray_intersection_preserves_ray_and_detects_missing_surface():
    from spectralbridge.drone_original import intersect_ecef_ray

    def identity(points):
        return points

    def plane(xy):
        return 2 + 0.1 * xy[:, 0]

    ray = np.array([0.2, 0.1, -1.0])
    result = intersect_ecef_ray(
        [0, 0, 10],
        ray,
        to_project=identity,
        sample_height=plane,
        maximum_distance=30,
        step_metres=0.25,
    )
    assert result["status"] == "BRACKETED_DEM_INTERSECTION"
    p = result["ecef"]
    assert p[2] == pytest.approx(2 + 0.1 * p[0], abs=1e-7)
    assert np.linalg.norm(np.cross(p - [0, 0, 10], ray)) < 1e-8

    def gap(xy):
        values = plane(xy)
        values[(xy[:, 0] > 0.3) & (xy[:, 0] < 0.6)] = np.nan
        return values

    missing = intersect_ecef_ray(
        [0, 0, 10],
        ray,
        to_project=identity,
        sample_height=gap,
        maximum_distance=30,
        step_metres=0.25,
    )
    assert missing["status"] == "UNSUPPORTED_SURFACE_GAP_OR_ORIGIN"


def test_corrected_source_export_keeps_geometry_and_requires_both_stages(tmp_path):
    import rasterio
    from spectralbridge.drone_original import write_corrected_photo

    values = np.full((8, 9), 0.4)
    ts = np.ones(values.shape, bool)
    ts[0, 0] = False
    record = write_corrected_photo(
        tmp_path / "new.tif",
        values,
        2.0,
        1.5,
        topographic_supported=ts,
        brdf_supported=True,
        provenance=dict(
            project_fingerprint="fixture",
            camera_key=1,
            wavelength_nm=650,
            matched_processing_stage="topo_then_brdf",
        ),
    )
    assert record["dimensions"] == [9, 8]
    with rasterio.open(tmp_path / "new.tif") as d:
        assert np.isnan(d.read(1)[0, 0])
        assert d.dataset_mask()[0, 0] == 0
        assert d.read(1)[1, 1] == pytest.approx(1.2)
    with pytest.raises(FileExistsError):
        write_corrected_photo(
            tmp_path / "new.tif",
            values,
            2.0,
            1.0,
            topographic_supported=True,
            brdf_supported=True,
            provenance={},
        )


def test_original_observation_kernel_design_matches_shared_reference():
    from spectralbridge.drone_original import ross_li_design, reference_design

    design = ross_li_design([0, 0], [45, 45], [0, 0], [0, 0])
    assert design.shape == (2, 3)
    np.testing.assert_allclose(design, np.tile(reference_design(), (2, 1)), atol=1e-7)


def test_temporal_groups_are_invariant_to_datetime_storage_resolution():
    from spectralbridge.drone_original import temporal_minute_groups

    values = ["2023-08-15T18:47:01", "2023-08-15T18:47:59", "2023-08-15T18:48:01"]
    expected = temporal_minute_groups(values)
    assert expected[0] == expected[1] and expected[1] != expected[2]
    np.testing.assert_array_equal(
        temporal_minute_groups(np.array(values, dtype="datetime64[us]")), expected
    )
    np.testing.assert_array_equal(
        temporal_minute_groups(np.array(values, dtype="datetime64[ns]")), expected
    )
