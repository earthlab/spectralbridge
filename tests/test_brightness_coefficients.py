import numpy as np
import pytest

from spectralbridge.brightness_config import load_brightness_coefficients
from spectralbridge.pipelines import pipeline


def test_oli_coefficients_use_table_mountain_hls_medians() -> None:
    coeffs = load_brightness_coefficients("landsat_to_micasense")
    assert coeffs[1] == pytest.approx(-4.444952)
    assert coeffs[4] == pytest.approx(0.694524)
    assert coeffs[7] == pytest.approx(-1.849171)


def test_tm_coefficients_use_wavelength_aligned_order() -> None:
    coeffs = load_brightness_coefficients("landsat_tm_etm_to_micasense")
    assert coeffs[2] == pytest.approx(-1.670916)


def test_etm_coefficients_use_wavelength_aligned_order() -> None:
    coeffs = load_brightness_coefficients("landsat_tm_etm_to_micasense")
    assert coeffs[3] == pytest.approx(0.694524)


def test_tm_coefficients_are_oli_bands_2_through_7() -> None:
    oli = load_brightness_coefficients("landsat_to_micasense")
    tm = load_brightness_coefficients("landsat_tm_etm_to_micasense")
    assert tm == {idx: oli[idx + 1] for idx in range(1, 7)}


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
