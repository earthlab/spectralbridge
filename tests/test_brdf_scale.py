import json
from pathlib import Path

import numpy as np
import pytest

from spectralbridge.corrections import (
    HYTOOLS_BRDF_KERNEL_CONFIG,
    apply_brdf_correct,
    fit_and_save_brdf_model,
    NDVIBinningConfig,
)


class _FakeCube:
    def __init__(self, data: np.ndarray, scale_factor: float = 1.0) -> None:
        self.data = np.asarray(data, dtype=np.float32)
        from spectralbridge.radiometry import Radiometry
        self.radiometry = Radiometry(scale_factor, 0., "VALID", "Synthetic multiplier calibration")
        self.scale_factor = float(scale_factor)
        self.lines, self.columns, self.bands = self.data.shape
        # Provide plausible wavelengths so NDVI band selection works during tests.
        self.wavelengths = np.linspace(600, 900, self.bands, dtype=np.float32)
        self.mask_no_data = np.ones((self.lines, self.columns), dtype=bool)
        self.no_data = -9999.0
        self.base_key = "fake"

    def get_ancillary(self, name: str, radians: bool = True) -> np.ndarray:
        y, x = np.mgrid[:self.lines, :self.columns]
        if name == "solar_zn":
            return np.full(y.shape, .6, np.float32)
        if name == "sensor_zn":
            return (.05 + .08*x + .03*y).astype(np.float32)
        if name == "sensor_az":
            return (.4*y + .1*x).astype(np.float32)
        return np.zeros(y.shape, np.float32)


def _neutral_coefficients(path: Path, cube) -> Path:
    return fit_and_save_brdf_model(cube, path.parent / path.stem)


def test_brdf_fit_scale_invariant(tmp_path: Path) -> None:
    unitless = np.full((5, 5, 3), 0.3, dtype=np.float32)
    scaled = unitless / 1e-4

    cube_unitless = _FakeCube(unitless, scale_factor=1.0)
    cube_scaled = _FakeCube(scaled, scale_factor=1e-4)

    coeff_unitless = fit_and_save_brdf_model(
        cube_unitless,
        tmp_path / "unitless",
        brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    coeff_scaled = fit_and_save_brdf_model(
        cube_scaled,
        tmp_path / "scaled",
        brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
    )

    model_unitless = json.loads(coeff_unitless.read_text())
    model_scaled = json.loads(coeff_scaled.read_text())

    for key in ("iso", "vol", "geo"):
        assert np.allclose(model_unitless[key], model_scaled[key], atol=1e-3)

    assert model_unitless["volume_kernel"] == "RossThick"
    assert model_unitless["geom_kernel"] == "LiDenseR"
    assert model_unitless["b_r"] == pytest.approx(10.0)
    assert model_unitless["h_b"] == pytest.approx(2.0)
    assert model_unitless["solar_zn_type"] == "scene"


def test_brdf_fit_defaults_to_single_bin_when_ndvi_binning_disabled(tmp_path: Path) -> None:
    unitless = np.full((4, 4, 3), 0.3, dtype=np.float32)
    cube = _FakeCube(unitless, scale_factor=1.0)

    coeff_path = fit_and_save_brdf_model(cube, tmp_path / "default_single_bin")
    model = json.loads(coeff_path.read_text())

    assert model["ndvi_binning_enabled"] is False
    assert model["ndvi_edges"] == pytest.approx([-1.0, 1.0])
    assert len(model["iso"]) == 1


def test_brdf_fit_can_enable_ndvi_binning(tmp_path: Path) -> None:
    unitless = np.full((4, 4, 2), 0.2, dtype=np.float32)
    unitless[:2, :, 1] = 0.6
    cube = _FakeCube(unitless, scale_factor=1.0)

    coeff_path = fit_and_save_brdf_model(
        cube,
        tmp_path / "ndvi_bins_enabled",
        ndvi_config=NDVIBinningConfig(
            enabled=True,
            n_bins=2,
            ndvi_min=0.0,
            ndvi_max=1.0,
            perc_min=None,
            perc_max=None,
        ),
    )
    model = json.loads(coeff_path.read_text())

    assert model["ndvi_binning_enabled"] is True
    assert len(model["ndvi_edges"]) == 3
    assert len(model["iso"]) == 2


def test_correction_respects_raw_scale(tmp_path: Path) -> None:
    unitless = np.full((4, 4, 2), 0.25, dtype=np.float32)
    scaled = unitless / 1e-4
    cube = _FakeCube(scaled, scale_factor=1e-4)

    coeff_path = _neutral_coefficients(tmp_path / "coeff.json", cube)
    corrected = apply_brdf_correct(
        cube,
        cube.data,
        0,
        cube.lines,
        0,
        cube.columns,
        coeff_path=coeff_path,
    )

    assert np.allclose(corrected, cube.data, atol=1e-3)


def test_correction_preserves_shape_and_dtype(tmp_path: Path) -> None:
    scaled = np.full((2, 3, 4), 0.45 / 1e-4, dtype=np.float32)
    cube = _FakeCube(scaled, scale_factor=1e-4)

    coeff_path = _neutral_coefficients(tmp_path / "coeff_dtype.json", cube)
    corrected = apply_brdf_correct(
        cube,
        cube.data,
        0,
        cube.lines,
        0,
        cube.columns,
        coeff_path=coeff_path,
    )

    assert corrected.shape == cube.data.shape
    assert corrected.dtype == np.float32


def test_correction_uses_neutral_factor_without_division_warning(
    tmp_path: Path,
) -> None:
    cube = _FakeCube(np.full((2, 2, 1), 0.25, dtype=np.float32))
    coeff_path = tmp_path / "nonpositive_kernel.json"
    coeff_path.write_text(
        json.dumps(
            {
                "iso": [0.0],
                "vol": [0.0],
                "geo": [0.0],
                "volume_kernel": "RossThick",
                "geom_kernel": "LiSparseReciprocal",
            }
        ),
        encoding="utf-8",
    )

    with np.errstate(divide="raise", invalid="raise"), pytest.raises(ValueError, match="UNSUPPORTED"):
        apply_brdf_correct(cube, cube.data, 0, 2, 0, 2, coeff_path=coeff_path)


def test_outliers_masked_from_fit(tmp_path: Path) -> None:
    unitless = np.full((3, 3, 2), 0.2, dtype=np.float32)
    unitless[..., 1] = 0.35  # ensure NDVI falls inside bins
    unitless[0, 0, 0] = 1.5  # beyond valid range and should be excluded
    scaled = unitless / 1e-4
    cube = _FakeCube(scaled, scale_factor=1e-4)

    coeff_path = fit_and_save_brdf_model(
        cube,
        tmp_path / "outlier",
        rho_max=1.0,
        ndvi_config=NDVIBinningConfig(n_bins=1, ndvi_min=-1.0, perc_min=None, perc_max=None),
    )
    model = json.loads(coeff_path.read_text())

    valid_mean = float(np.mean(unitless[..., 0][unitless[..., 0] < 1.0]))
    assert model["iso"][0][0] == pytest.approx(valid_mean, rel=0.6)
    assert model["iso"][0][0] < 0.5
    assert abs(model["vol"][0][0]) < 0.2
    assert abs(model["geo"][0][0]) < 0.2


def test_correction_uses_saved_ndvi_edges_from_coeff_file(tmp_path: Path) -> None:
    red = np.float32(0.05)
    nir = np.float32(0.28333333)  # NDVI ~= 0.7
    unitless = np.stack(
        [
            np.full((2, 2), red, dtype=np.float32),
            np.full((2, 2), nir, dtype=np.float32),
        ],
        axis=-1,
    )
    cube = _FakeCube(unitless, scale_factor=1.0)

    coeff_dir = tmp_path / "scene"
    coeff_dir.mkdir()
    coeff_path = coeff_dir / "scene_brdf_model.json"
    payload = {
        "iso": [[1.0, 1.0], [1.0, 1.0]],
        "vol": [[0.0, 0.0], [2.0, 2.0]],
        "geo": [[0.0, 0.0], [0.0, 0.0]],
        "volume_kernel": "RossThick",
        "geom_kernel": "LiSparseReciprocal",
        "ndvi_edges": [0.0, 0.8, 1.0],
    }
    coeff_path.write_text(json.dumps(payload), encoding="utf-8")

    # Kernel names and NDVI edges alone do not validate a legacy model.
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        apply_brdf_correct(cube, cube.data, 0, cube.lines, 0, cube.columns, coeff_path=coeff_path)


def test_correction_accepts_saved_hytools_style_kernel_settings(tmp_path: Path) -> None:
    unitless = np.full((3, 3, 2), 0.25, dtype=np.float32)
    cube = _FakeCube(unitless, scale_factor=1.0)

    coeff_dir = tmp_path / "hytools_style"
    coeff_dir.mkdir()
    coeff_path = coeff_dir / "hytools_style_brdf_model.json"
    payload = {
        "iso": [[0.7, 0.7]],
        "vol": [[0.1, 0.1]],
        "geo": [[0.05, 0.05]],
        "volume_kernel": "RossThick",
        "geom_kernel": "LiDenseR",
        "b_r": 10.0,
        "h_b": 2.0,
        "solar_zn_type": "scene",
        "ndvi_edges": [-1.0, 1.0],
    }
    coeff_path.write_text(json.dumps(payload), encoding="utf-8")

    # Kernel names and NDVI edges alone do not validate a legacy model.
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        apply_brdf_correct(cube, cube.data, 0, cube.lines, 0, cube.columns, coeff_path=coeff_path)


def test_response_scaling_preserves_ratios_but_additive_offsets_do_not(tmp_path):
    from spectralbridge.corrections import _brdf_design, BRDFKernelConfig
    from spectralbridge.radiometry import Radiometry

    probe = _FakeCube(np.full((5, 5, 3), 0.3, np.float32))
    design, valid, _ = _brdf_design(probe, BRDFKernelConfig())
    response = (design @ np.array([0.4, 0.05, 0.01])).astype(np.float32)
    models = []
    ratios = []
    for label, multiplier, shift in [("base", 1, 0), ("scaled", 1.7, 0), ("offset", 1, .2)]:
        values = np.repeat((response * multiplier + shift)[..., None], 3, axis=-1)
        cube = _FakeCube(values)
        model = json.loads(fit_and_save_brdf_model(cube, tmp_path / label, rho_max=None).read_text())
        assert model["validation"]["status"] == "VALID"
        beta = np.array([model[k][0][0] for k in ("iso", "vol", "geo")])
        models.append(beta)
        ratios.append(np.asarray(model["reference_design"]) @ beta / (design @ beta)[valid])
    np.testing.assert_allclose(models[1], models[0] * 1.7, rtol=2e-5, atol=2e-7)
    np.testing.assert_allclose(ratios[1], ratios[0], rtol=2e-6)
    assert np.max(abs(ratios[2] - ratios[0])) > 1e-3
    # An encoding offset is decoded before fitting and re-encoded after applying.
    encoded = _FakeCube(np.repeat(((response - .05) / .0001)[..., None], 3, axis=-1))
    encoded.radiometry = Radiometry(.0001, .05, "VALID", "Synthetic affine source")
    path = fit_and_save_brdf_model(encoded, tmp_path / "affine")
    corrected = apply_brdf_correct(encoded, encoded.data, 0, 5, 0, 5, coeff_path=path)
    physical = encoded.radiometry.to_physical(corrected)
    base = _FakeCube(np.repeat(response[..., None], 3, axis=-1))
    base_path = fit_and_save_brdf_model(base, tmp_path / "base_application")
    expected = apply_brdf_correct(base, base.data, 0, 5, 0, 5, coeff_path=base_path)
    np.testing.assert_allclose(physical, expected, rtol=3e-6, atol=1e-7)
