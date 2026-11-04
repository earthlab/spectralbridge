"""Source quality and runtime prediction regression tests shared by drone/AOP."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from spectralbridge import corrections as c
from spectralbridge.radiometry import Radiometry


def cube(scale=1.0, config=None):
    config = config or c.BRDFKernelConfig()
    yy, xx = np.mgrid[:12, :15]
    angles = {
        "solar_zn": np.full(xx.shape, 0.65),
        "solar_az": np.full(xx.shape, 1.2),
        "sensor_zn": 0.03 + xx * 0.025 + yy * 0.01,
        "sensor_az": xx * 0.22 + yy * 0.11,
    }
    kv = c.calc_volume_kernel(
        angles["solar_az"],
        angles["solar_zn"],
        angles["sensor_az"],
        angles["sensor_zn"],
        kernel_type=config.volume_kernel,
    )
    kg = c.calc_geom_kernel(
        angles["solar_az"],
        angles["solar_zn"],
        angles["sensor_az"],
        angles["sensor_zn"],
        kernel_type=config.geom_kernel,
        b_r=config.b_r,
        h_b=config.h_b,
    )
    physical = np.stack(
        [0.3 + 0.04 * kv + 0.02 * kg, 0.5 + 0.02 * kv + 0.01 * kg], axis=-1
    ).astype("float32")
    obj = SimpleNamespace(
        data=physical / scale,
        mask_no_data=np.ones(xx.shape, bool),
        source_valid_mask=None,
        radiometry=Radiometry(
            scale, 0, "VALID", "Synthetic independent equation fixture"
        ),
        bands=2,
        lines=12,
        columns=15,
        wavelengths=np.array([650, 862]),
        no_data=-9999.0,
    )
    obj.get_ancillary = lambda name, radians=True: (
        angles[name] if radians else np.rad2deg(angles[name])
    )
    return obj, angles


def test_explicit_source_alpha_cannot_contaminate_a_fit_with_a_stale_combined_mask(
    tmp_path,
):
    obj, _ = cube(0.0001)
    obj.source_valid_mask = np.ones((12, 15), bool)
    obj.source_valid_mask[:3, :4] = False
    obj.data[:3, :4] = 65535
    path = c.fit_and_save_brdf_model(obj, tmp_path, rho_max=None)
    model = json.loads(path.read_text())
    assert all(r["eligible"] == 168 for r in model["validation"]["fits"])
    assert model["validation"]["status"] == "VALID"
    assert all(
        r["excluded_source_footprint"] == 12 for r in model["validation"]["fits"]
    )
    out = c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)
    assert (out[:3, :4] == obj.no_data).all()
    assert np.isfinite(out[3:]).all()


def test_missing_view_geometry_is_a_persisted_unsupported_result(tmp_path):
    obj, angles = cube()
    angles.pop("sensor_zn")
    path = c.fit_and_save_brdf_model(obj, tmp_path)
    model = json.loads(path.read_text())
    assert model["validation"]["status"] == "UNSUPPORTED"
    assert "sensor_zn" in " ".join(model["validation"]["reasons"])
    assert "iso" not in model


def test_negative_angles_cannot_make_the_scene_solar_mean_valid(tmp_path):
    obj, angles = cube()
    angles["sensor_zn"][0, 0] = -9999
    angles["solar_zn"][0, 0] = 80  # invalid row must not change the scene mean
    path = c.fit_and_save_brdf_model(
        obj, tmp_path, brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG
    )
    m = json.loads(path.read_text())
    assert m["scene_solar_zenith_rad"] == pytest.approx(0.65, abs=1e-7)


def test_known_direction_and_single_decoding_are_platform_independent(tmp_path):
    for sensor, scale in [
        ("drone_declared_fixture", 0.0001999969482421875),
        ("AOP_declared_fixture", 0.0001),
    ]:
        obj, _ = cube(scale, c.HYTOOLS_BRDF_KERNEL_CONFIG)
        path = c.fit_and_save_brdf_model(
            obj, tmp_path / sensor, brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG
        )
        m = json.loads(path.read_text())
        assert m["validation"]["status"] == "VALID"
        result = c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)
        reference = c._reference_design(
            c.ReferenceGeometry(), c.HYTOOLS_BRDF_KERNEL_CONFIG
        )
        truth = np.array([[0.3, 0.04, 0.02], [0.5, 0.02, 0.01]]) @ reference
        np.testing.assert_allclose(
            obj.radiometry.to_physical(result),
            np.broadcast_to(truth, result.shape),
            atol=2e-7,
        )


def test_runtime_rejects_positive_but_unresolved_denominator_without_gain_clipping(
    tmp_path,
):
    obj, angles = cube()
    path = c.fit_and_save_brdf_model(obj, tmp_path)
    model = json.loads(path.read_text())
    X, valid, _ = c._brdf_design(obj, c.BRDFKernelConfig())
    reference = np.array(model["reference_design"])
    component = next(j for j in [1, 2] if reference[j] > X[..., j][valid].min() + 1e-3)
    beta = np.zeros(3)
    beta[component] = 1e8
    beta[0] = -X[..., component][valid].min() * 1e8 + 0.01
    assert (X[valid] @ beta > 0).all() and reference @ beta > 0
    model["iso"][0][0], model["vol"][0][0], model["geo"][0][0] = beta
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError, match="prediction"):
        c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)


def test_documented_saturation_is_nodata_but_an_observed_zero_survives(tmp_path):
    obj, _ = cube()
    obj.radiometry = Radiometry(
        1.0,
        0.0,
        "VALID",
        "Synthetic quality fixture",
        encoding={
            "kind": "fractional_physical_reflectance",
            "nodata": -9999,
            "saturation": {
                "status": "DOCUMENTED",
                "value": 65535,
                "provenance": "synthetic sensor flag",
            },
        },
    )
    obj.data[0, 0, 0] = 65535
    obj.data[0, 1, 0] = 0
    path = c.fit_and_save_brdf_model(obj, tmp_path)
    m = json.loads(path.read_text())
    assert m["validation"]["status"] == "VALID"
    result = c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)
    assert result[0, 0, 0] == obj.no_data
    assert result[0, 1, 0] == 0
    assert np.isfinite(result[0, 0, 1])


def test_rank_one_has_no_neutral_fitted_coefficients(tmp_path):
    obj, angles = cube()
    angles["sensor_zn"][:] = 0
    angles["sensor_az"][:] = 0
    path = c.fit_and_save_brdf_model(
        obj, tmp_path, brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG
    )
    m = json.loads(path.read_text())
    assert m["validation"]["status"] == "UNSUPPORTED"
    assert all(r["stable_rank"] == 1 for r in m["validation"]["fits"])
    assert "iso" not in m
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)


def test_band_identity_and_policy_changes_cannot_reuse_a_model(tmp_path):
    obj, _ = cube()
    path = c.fit_and_save_brdf_model(obj, tmp_path)
    original = path.read_bytes()
    obj.wavelengths = obj.wavelengths[::-1]
    with pytest.raises(ValueError, match="band identities"):
        c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)
    obj.wavelengths = obj.wavelengths[::-1]
    m = json.loads(original)
    m.pop("validation_policy")
    path.write_text(json.dumps(m))
    old = path.read_bytes()
    with pytest.raises(ValueError, match="validation policy"):
        c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)
    with pytest.raises(ValueError, match="stale or unvalidated"):
        c.fit_and_save_brdf_model(obj, tmp_path)
    assert path.read_bytes() == old


def test_runtime_uncertainty_is_rechecked_instead_of_neutral_fallback(tmp_path):
    obj, _ = cube()
    path = c.fit_and_save_brdf_model(obj, tmp_path)
    model = json.loads(path.read_text())
    model["validation"]["fits"][0]["coefficient_covariance"] = (
        np.eye(3) * 100
    ).tolist()
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError, match="unresolved model prediction"):
        c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=path)


def test_transparent_background_cannot_set_ndvi_stratum_edges(tmp_path):
    obj, _ = cube()
    obj.source_valid_mask = np.ones((12, 15), bool)
    obj.source_valid_mask[:3, :4] = False
    obj.data[:3, :4, 0] = 0
    obj.data[:3, :4, 1] = 65535
    path = c.fit_and_save_brdf_model(
        obj,
        tmp_path,
        rho_max=None,
        ndvi_config=c.NDVIBinningConfig(
            enabled=True, n_bins=2, ndvi_min=0, ndvi_max=1, perc_min=0, perc_max=100
        ),
    )
    model = json.loads(path.read_text())
    assert model["ndvi_edges"][-1] < 0.5
    assert all(r["eligible"] <= 168 for r in model["validation"]["fits"])


def test_ndvi_quality_uses_the_same_wavelengths_as_the_ndvi_calculation(tmp_path):
    obj, _ = cube()
    obj.data = np.stack(
        [obj.data[..., 0], obj.data[..., 0] * 0.8, obj.data[..., 1]], axis=-1
    )
    obj.bands = 3
    obj.wavelengths = np.array([650, 668, 862])
    obj.no_data = 0
    obj.data[0, 0, 1] = 0  # missing668nm, not the separate650nm channel
    path = c.fit_and_save_brdf_model(
        obj,
        tmp_path,
        ndvi_config=c.NDVIBinningConfig(
            enabled=True, n_bins=2, ndvi_min=0, ndvi_max=1, perc_min=0, perc_max=100
        ),
    )
    model = json.loads(path.read_text())
    assert model["ndvi_edges"][-1] < 0.9


def test_common_positive_signal_multiplier_cancels_in_the_brdf_factor(tmp_path):
    obj, _ = cube(config=c.HYTOOLS_BRDF_KERNEL_CONFIG)
    scaled, _ = cube(config=c.HYTOOLS_BRDF_KERNEL_CONFIG)
    multiplier = 65535 / 32768
    scaled.data *= multiplier
    first = c.fit_and_save_brdf_model(
        obj,
        tmp_path / "first",
        rho_max=None,
        brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    second = c.fit_and_save_brdf_model(
        scaled,
        tmp_path / "second",
        rho_max=None,
        brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    a = json.loads(first.read_text())
    b = json.loads(second.read_text())
    for key in ["iso", "vol", "geo"]:
        np.testing.assert_allclose(
            np.array(b[key]), np.array(a[key]) * multiplier, rtol=1e-5, atol=1e-7
        )
    out1 = c.apply_brdf_correct(obj, obj.data, 0, 12, 0, 15, coeff_path=first)
    out2 = c.apply_brdf_correct(scaled, scaled.data, 0, 12, 0, 15, coeff_path=second)
    np.testing.assert_allclose(out2, out1 * multiplier, atol=2e-7)


def test_old_brdf_headers_are_not_approved_library_inputs():
    from spectralbridge.radiometry import require_library_header

    header = Radiometry(1, 0, "VALID", "Synthetic header fixture").header()
    header.update(
        {
            "brdf status": "VALID",
            "brdf model schema": 2,
            "brdf kernel math version": c.BRDF_KERNEL_MATH_VERSION,
        }
    )
    with pytest.raises(ValueError, match="validation policy"):
        require_library_header(header)
    header["brdf validation policy"] = c.BRDF_VALIDATION_POLICY
    assert require_library_header(header).status == "VALID"
    header["brdf status"] = "NOT_REQUESTED"
    header.pop("brdf validation policy")
    assert require_library_header(header).status == "VALID"
