"""Isolated experiment contracts; no production calibration inferred."""

import importlib.util
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

P = (
    Path(__file__).resolve().parents[1]
    / "provenance/drone-radiometric-recovery/2026-11-02/recover.py"
)
spec = importlib.util.spec_from_file_location("recovery_experiment", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_inverse_offsets_negative_and_large_values():
    x = np.array([-5, 0, 5000, 12000, np.nan], np.float32)
    y = m.inverse_values(x, 174, 65535)
    np.testing.assert_allclose(y[:4], 174 + x[:4].astype(float) * 6.5361, rtol=1e-7)
    assert np.isnan(y[-1]) and y[3] > 65535
    with pytest.raises(ValueError):
        m.inverse_values(x, 3, 3)


def test_raster_preserves_grid_alpha_mask_and_nodata(tmp_path):
    src, dst = tmp_path / "source.tif", tmp_path / "recovered.tif"
    data = np.array([[[0, 12], [-9999, 10000]], [[255, 255], [0, 255]]], np.float32)
    with rasterio.open(
        src,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=2,
        dtype="float32",
        crs="EPSG:26913",
        transform=from_origin(400000, 4400000, 0.1, 0.1),
        nodata=-9999,
    ) as f:
        f.write(data)
        f.colorinterp = (
            rasterio.enums.ColorInterp.gray,
            rasterio.enums.ColorInterp.alpha,
        )
        f.write_mask(np.array([[255, 255], [0, 255]], np.uint8))
    record = m.recover_raster(
        src, dst, dict(bands=[dict(band=1, original_min=174, original_max=65535)])
    )
    assert record["masks_unchanged"]
    with rasterio.open(dst) as f:
        np.testing.assert_array_equal(f.read(2), data[1])
        assert f.read(1)[1, 0] == -9999
        assert f.read(1)[0, 0] == 174
    with pytest.raises(FileExistsError):
        m.recover_raster(src, dst, dict(bands=[]))


def test_supported_design_multiplicative_fit_invariance():
    # Full-rank synthetic angular terms; no eligibility gate or unit changes.
    rng = np.random.default_rng(63)
    X = np.column_stack(
        [np.ones(200), rng.uniform(-0.1, 0.1, 200), rng.uniform(-0.2, 0.2, 200)]
    )
    y = X @ np.array([0.4, 0.03, 0.02])
    ref = np.array([1, 0.04, -0.1])
    a = 6.5535
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    ba = np.linalg.lstsq(X, a * y, rcond=None)[0]
    np.testing.assert_allclose((ref @ ba) / (X @ ba), (ref @ b) / (X @ b), rtol=1e-13)
