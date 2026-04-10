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
        self.scale_factor = float(scale_factor)
        self.lines, self.columns, self.bands = self.data.shape
        # Provide plausible wavelengths so NDVI band selection works during tests.
        self.wavelengths = np.linspace(600, 900, self.bands, dtype=np.float32)
        self.mask_no_data = np.ones((self.lines, self.columns), dtype=bool)
        self.no_data = -9999.0
        self.base_key = "fake"

    def get_ancillary(self, name: str, radians: bool = True) -> np.ndarray:
        shape = (self.lines, self.columns)
        if name in {"solar_zn", "sensor_zn"}:
            return np.full(shape, 0.1, dtype=np.float32)
        if name in {"solar_az", "sensor_az", "slope", "aspect"}:
            return np.full(shape, 0.0, dtype=np.float32)
        raise KeyError(name)


def _neutral_coefficients(path: Path, bands: int) -> Path:
    payload = {
        "iso": [1.0 for _ in range(bands)],
        "vol": [0.0 for _ in range(bands)],
        "geo": [0.0 for _ in range(bands)],
        "volume_kernel": "RossThick",
        "geom_kernel": "LiSparseReciprocal",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


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

    coeff_path = _neutral_coefficients(tmp_path / "coeff.json", cube.bands)
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

    coeff_path = _neutral_coefficients(tmp_path / "coeff_dtype.json", cube.bands)
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


def test_outliers_masked_from_fit(tmp_path: Path) -> None:
    unitless = np.full((3, 3, 2), 0.2, dtype=np.float32)
    unitless[..., 1] = 0.35  # ensure NDVI falls inside bins
    unitless[0, 0, 0] = 1.5  # beyond valid range and should be excluded
    scaled = unitless / 1e-4
    cube = _FakeCube(scaled, scale_factor=1e-4)

    coeff_path = fit_and_save_brdf_model(
        cube,
        tmp_path / "outlier",
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

    corrected = apply_brdf_correct(
        cube,
        cube.data,
        0,
        cube.lines,
        0,
        cube.columns,
        coeff_path=coeff_path,
        ndvi_config=NDVIBinningConfig(
            n_bins=2,
            ndvi_min=0.0,
            ndvi_max=1.0,
            perc_min=None,
            perc_max=None,
        ),
    )

    np.testing.assert_allclose(corrected, cube.data, atol=1e-6)


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

    corrected = apply_brdf_correct(
        cube,
        cube.data,
        0,
        cube.lines,
        0,
        cube.columns,
        coeff_path=coeff_path,
        brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
        ndvi_config=NDVIBinningConfig(
            n_bins=1,
            ndvi_min=-1.0,
            ndvi_max=1.0,
            perc_min=None,
            perc_max=None,
        ),
    )

    assert corrected.shape == cube.data.shape
    assert corrected.dtype == np.float32
    assert np.all(np.isfinite(corrected))
