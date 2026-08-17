import numpy as np
import pytest

from spectralbridge.brightness_config import load_brightness_coefficients
from spectralbridge.pipelines import pipeline


def test_tm_etm_coefficients_use_current_wavelength_aligned_order() -> None:
    coeffs = load_brightness_coefficients("landsat_tm_etm_to_micasense")
    assert coeffs == pytest.approx(
        {
            1: -2.412679,
            2: -1.670916,
            3: 0.694524,
            4: -2.566724,
            5: -1.097476,
            6: -1.849171,
        }
    )


def test_apply_landsat_brightness_darkens_negative_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    cube = np.full((3, 4, 4), 100.0, dtype=np.float32)

    monkeypatch.setattr(
        pipeline,
        "load_brightness_coefficients",
        lambda system_pair="landsat_to_micasense": {3: -10.12},
    )

    applied = pipeline._apply_landsat_brightness_adjustment(
        cube, system_pair="landsat_to_micasense"
    )

    assert applied[3] == pytest.approx(-10.12)
    expected_gain = 1.0 + (-10.12 / 100.0)
    assert np.isclose(expected_gain, 0.8988)
    assert np.isclose(cube[2, 0, 0], 100.0 * expected_gain)


def test_apply_landsat_brightness_preserves_nodata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cube = np.full((3, 4, 4), 100.0, dtype=np.float32)
    cube[2, 0, 0] = -9999.0
    monkeypatch.setattr(
        pipeline,
        "load_brightness_coefficients",
        lambda system_pair="landsat_to_micasense": {3: -10.0},
    )

    pipeline._apply_landsat_brightness_adjustment(
        cube,
        nodata_value=-9999.0,
    )

    assert cube[2, 0, 0] == -9999.0
    assert cube[2, 1, 1] == pytest.approx(90.0)
