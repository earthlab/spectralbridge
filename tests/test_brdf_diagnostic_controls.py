"""Synthetic controls for the diagnosed BRDF guard and fit-range behavior."""

import json
from pathlib import Path

import numpy as np
import pytest

import spectralbridge.corrections as corrections


class Cube:
    def __init__(self, data):
        from spectralbridge.radiometry import Radiometry
        self.radiometry = Radiometry(1., 0., "VALID", "Synthetic diagnostic, not Goldhill calibration")
        self.data = data
        self.lines, self.columns, self.bands = data.shape
        self.scale_factor = 1.0
        self.no_data = np.nan
        self.base_key = "synthetic"
        self.mask_no_data = np.ones(data.shape[:2], dtype=bool)
        self.wavelengths = np.array([650.0], dtype="float32")

    def get_ancillary(self, name, radians=True):
        value = 0.4 if name == "solar_zn" else 0.0
        return np.full(self.data.shape[:2], value, dtype="float32")


def test_nonpositive_prediction_guard_can_make_a_discontinuous_band_gain(monkeypatch):
    cube = Cube(np.full((2, 2, 1), 0.2, dtype="float32"))
    cube.brdf_coefficients = {
        "iso": [0.0],
        "vol": [0.0],
        "geo": [1.0],
        "solar_zn_type": "pixel",
    }
    monkeypatch.setattr(
        corrections,
        "calc_volume_kernel",
        lambda *args, **kwargs: np.zeros((2, 2), dtype="float32"),
    )

    def geometric(solar_az, solar_zn, sensor_az, sensor_zn, **kwargs):
        if np.all(solar_zn > 0.6):  # Default reference solar geometry.
            return np.full((2, 2), 0.5, dtype="float32")
        return np.array([[-0.01, 0.01], [-0.01, 0.01]], dtype="float32")

    monkeypatch.setattr(corrections, "calc_geom_kernel", geometric)
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        corrections.apply_brdf_correct(cube, cube.data, 0, 2, 0, 2)


def test_default_fit_range_excludes_large_unscaled_values(tmp_path: Path):
    data = np.full((5, 5, 1), 250.0, dtype="float32")
    data[0, 0, 0] = 0.2
    data[0, 1, 0] = 0.4
    cube = Cube(data)
    path = corrections.fit_and_save_brdf_model(cube, tmp_path / "synthetic_fit")
    model = json.loads(path.read_text())
    # Only two pixels enter the default 0..2 fitting range: too few for a fit.
    assert model["validation"]["status"] == "UNSUPPORTED"
    assert model["validation"]["fits"][0]["eligible"] == 2
    assert "iso" not in model
