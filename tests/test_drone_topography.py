"""Independent physical-axis, shadow and statistical recovery controls."""

import numpy as np
import pytest
from spectralbridge.drone_topography import (
    terrain_geometry,
    solar_incidence,
    solar_visibility,
    fit_topographic_model,
    topographic_factors,
)


def test_metric_plane_slope_aspect_and_incidence():
    row, col = np.indices((20, 20))
    z = 100 + col * 0.5
    g = terrain_geometry(z, pixel_size=1)
    np.testing.assert_allclose(g["slope_deg"], np.rad2deg(np.arctan(0.5)))
    np.testing.assert_allclose(g["aspect_deg"], 270)
    assert solar_incidence(30, 180, 30, 180) == pytest.approx(1.0)
    assert solar_incidence(30, 0, 30, 180) == pytest.approx(0.5)
    np.testing.assert_allclose(
        solar_incidence(0, np.arange(0, 360, 30), 45, 70), np.cos(np.pi / 4)
    )


def test_dem_holes_remain_unknown_after_smoothing():
    z = np.zeros((20, 20))
    z[10, 10] = np.nan
    g = terrain_geometry(z, pixel_size=0.5, smoothing_sigma_m=2)
    assert np.isnan(g["elevation"][10, 10]) and not g["valid"][10, 10]


def test_solar_obstruction_and_missing_coverage_are_distinct():
    def wall(x, y):
        return np.where((y >= 4) & (y <= 6), 10.0, 0.0)

    hit = solar_visibility(
        np.array([0.0]),
        np.array([0.0]),
        np.array([0.0]),
        solar_zenith_deg=45,
        solar_azimuth_deg=0,
        sample_surface=wall,
        maximum_distance=10,
    )
    assert hit["shadow"][0] and hit["covered"][0]
    clear = solar_visibility(
        [0.0],
        [0.0],
        [0.0],
        solar_zenith_deg=45,
        solar_azimuth_deg=180,
        sample_surface=wall,
        maximum_distance=10,
    )
    assert not clear["shadow"][0] and clear["covered"][0]

    def missing(x, y):
        return np.where(y > 7, np.nan, 0.0)

    unknown = solar_visibility(
        [0.0],
        [0.0],
        [0.0],
        solar_zenith_deg=45,
        solar_azimuth_deg=0,
        sample_surface=missing,
        maximum_distance=10,
    )
    assert not unknown["covered"][0] and not unknown["shadow"][0]


def test_known_positive_and_negative_C_are_recovered_without_sign_constraint():
    rng = np.random.default_rng(42)
    x = np.tile(np.linspace(0.3, 0.95, 40), 12)
    groups = np.repeat(np.arange(12), 40)
    for C in [0.2, -0.1]:
        y = 0.1 * (x + C) + rng.normal(0, 0.0001, len(x))
        m = fit_topographic_model(x, y, groups)
        assert m["status"] == "NUMERICALLY_SUPPORTED"
        assert m["C"] == pytest.approx(C, abs=0.005)
        assert m["C_interval"][0] < C < m["C_interval"][1]


def test_negative_denominator_branch_is_not_a_valid_positive_ratio():
    m = dict(
        status="NUMERICALLY_SUPPORTED",
        method="scsc",
        C=-2.0,
        C_interval=[-2.1, -1.9],
        incidence_range=[0.1, 1.0],
        policy={"min_denominator": 0.001},
    )
    out = topographic_factors([0.5, 0.8], 10, 30, m)
    assert not out["supported"].any() and np.isnan(out["factor"]).all()
    m.update(C=-0.2, C_interval=[-0.25, -0.15])
    out = topographic_factors([0.2, 0.8], 10, 30, m)
    assert not out["supported"][0] and out["supported"][1]


def test_minnaert_recovers_known_exponent_and_preserves_spectral_ratios():
    rng = np.random.default_rng(2)
    x = np.tile(np.linspace(0.3, 1, 30), 10)
    groups = np.repeat(np.arange(10), 30)
    y = 0.15 * x**0.7 * np.exp(rng.normal(0, 0.001, len(x)))
    m = fit_topographic_model(x, y, groups, method="minnaert")
    assert m["k"] == pytest.approx(0.7, abs=0.005)
    f = topographic_factors(x, 15, 30, m)["factor"]
    corrected = y * f
    assert np.std(corrected) / np.mean(corrected) < 0.002
    np.testing.assert_allclose((2 * y * f) / (y * f), 2)


def test_spatial_groups_not_number_of_pixels_control_uncertainty():
    x = np.linspace(0.3, 0.9, 100)
    y = 0.1 * x + 0.02
    m = fit_topographic_model(x, y, np.ones(100))
    assert m["status"] == "UNSUPPORTED"


def test_spatial_holdout_buffer_excludes_boundary_without_mutating_labels():
    from spectralbridge.drone_topography import spatial_training_mask

    labels = np.zeros((8, 8), int)
    labels[:, 4:] = 1
    original = labels.copy()
    train = spatial_training_mask(labels, 1, buffer_cells=2)
    assert not train[:, 2:].any() and train[:, :2].all()
    np.testing.assert_array_equal(labels, original)
    with pytest.raises(ValueError):
        spatial_training_mask(labels, 9)


def test_large_supported_gain_is_retained_and_near_pole_is_missing():
    m = dict(
        status="NUMERICALLY_SUPPORTED",
        method="scsc",
        C=-0.5,
        C_interval=[-0.500001, -0.499999],
        incidence_range=[0.1, 1.0],
        policy={"min_denominator": 0.001},
    )
    result = topographic_factors([0.5, 0.50101], 0, 0, m)
    assert not result["supported"][0] and np.isnan(result["factor"][0])
    assert result["supported"][1] and result["factor"][1] > 400
