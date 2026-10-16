"""Finite implementation checks against Lean-evaluated rational examples.

These tests do not certify floating-point execution or physical calibration.
"""

import hashlib
import json
from fractions import Fraction
from pathlib import Path
from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose
from sklearn.linear_model import Ridge
from spectralbridge.resample import resample_chunk_to_sensor
from spectralbridge.researcher_information import project_simplex, TrainingTransform
from spectralbridge.mixtures import mixture_truth, fcls, fit_models

ROOT = Path(__file__).resolve().parents[2]
FORMAL = ROOT / "formal"


@pytest.fixture(scope="module")
def exact():
    p = FORMAL / "checks/rational_examples.json"
    data = json.loads(p.read_text())
    stamp = json.loads((FORMAL / "checks/bridge_execution.json").read_text())
    assert (
        stamp["lean_source_sha256"]
        == hashlib.sha256(
            (FORMAL / "SpectralBridge/Bridge.lean").read_bytes()
        ).hexdigest()
    ), "Rerun formal/check.py after changing Lean bridge"
    assert stamp["output_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    return {
        k: np.array([float(Fraction(v)) for v in values]) for k, values in data.items()
    }


def test_convolution(exact):
    got = resample_chunk_to_sensor(
        np.array([[[2.0, 6.0]]]), np.array([400.0, 405.0]), {"b": np.array([1.0, 3.0])}
    )
    assert_allclose(got.ravel(), exact["convolution"], atol=1e-6, rtol=0)


def test_multiplicative(exact):
    from spectralbridge.pipelines.pipeline import _apply_landsat_brightness_adjustment

    # Sufficient spatial dimensions avoid the separately documented axis heuristic bug.
    cube = np.full((7, 10, 11), 100.0, dtype=np.float32)
    coefficients = _apply_landsat_brightness_adjustment(cube)
    assert all(1 + p / 100 >= 0 for p in coefficients.values())
    assert_allclose(cube[0, 0, 0], exact["multiplicative"][0], atol=1e-5, rtol=0)


def test_affine_drone_file_path(exact, tmp_path):
    from spectralbridge.drone_translation import (
        load_drone_translation_plans,
        apply_drone_translation,
    )
    from spectralbridge.envi import hdr_to_dict, memmap_bsq

    waves = [444.0, 475.0, 531.0, 560.0, 650.0, 668.0, 705.0, 717.0, 740.0, 862.0]
    plan = load_drone_translation_plans(None, source_wavelengths_nm=waves)[0]
    plan = replace(
        plan,
        coefficient_set_version=None,
        bands=tuple(
            replace(b, slope=2.0, intercept=1.0, x_min=0.0, x_max=10.0, x_mean=3.0)
            for b in plan.bands
        ),
    )
    stem = tmp_path / "native"
    np.full((10, 2, 3), 3.0, dtype=np.float32).tofile(stem.with_suffix(".img"))
    stem.with_suffix(".hdr").write_text(
        "\n".join(
            [
                "ENVI",
                "samples = 3",
                "lines = 2",
                "bands = 10",
                "data type = 4",
                "interleave = bsq",
                "byte order = 0",
                "data ignore value = -9999",
                "reflectance scale factor = 1",
                "wavelength units = Nanometers",
                "projection = EPSG:32613",
                "fwhm = {28,32,14,27,16,14,10,12,18,57}",
                "wavelength = {" + ",".join(map(str, waves)) + "}",
                "map info = {UTM, 1, 1, 500000, 4400000, 1, 1, 13, North, WGS-84}",
            ]
        )
    )
    out = tmp_path / "translated"
    apply_drone_translation(
        stem.with_suffix(".img"), stem.with_suffix(".hdr"), output_stem=out, plan=plan
    )
    got = memmap_bsq(out.with_suffix(".img"), hdr_to_dict(out.with_suffix(".hdr")))
    assert_allclose(got, exact["affine"][0], atol=1e-6, rtol=0)


def test_polygon_mean_actual_landsat_support(exact, tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    from spectralbridge.landsat_agreement import (
        ReferenceGrid,
        aggregate_to_landsat_grid,
    )

    p = tmp_path / "source.tif"
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        width=2,
        height=1,
        count=7,
        dtype="float32",
        crs="EPSG:32613",
        transform=from_origin(500000, 4400000, 1, 1),
        nodata=-9999,
    ) as dst:
        dst.write(np.broadcast_to(np.array([[2, 6]], dtype=np.float32), (7, 1, 2)))
        dst.update_tags(ns="ENVI", reflectance_scale_factor="1")
    grid = ReferenceGrid("EPSG:32613", tuple(from_origin(500000, 4400000, 2, 1)), 1, 1)
    got = aggregate_to_landsat_grid({"corrected": p}, grid)["means"]["corrected"]
    assert_allclose(got, exact["polygon_mean"][0], atol=1e-10, rtol=0)


def test_synthetic_mixture_grid(exact):
    got = mixture_truth(np.eye(2), ["a", "b"], pairs_per_composition=1)
    use = np.flatnonzero(np.isclose(got["truth"][:, 0], 0.2))[0]
    assert_allclose(got["spectra"][use], exact["mixture"], atol=1e-15, rtol=0)
    assert_allclose(got["spectra"], got["truth"], atol=1e-15, rtol=0)
    assert_allclose(got["truth"].sum(1), 1, atol=1e-15, rtol=0)
    triple = mixture_truth(np.eye(3), ["a", "b", "c"], pairs_per_composition=1)
    assert_allclose(triple["truth"].sum(1), 1, atol=1e-15, rtol=0)
    assert (triple["truth"] >= 0).all()


def test_fcls_oracle(exact):
    got = fcls([[0.25, 0.75]], np.eye(2))
    assert_allclose(got["fractions"][0], exact["fcls_oracle"], atol=1e-10, rtol=0)


def test_mesma_candidate_ambiguity(exact):
    got = fit_models(
        [[0.5, 0.5]], [0, 1, 2], [[1, 0], [0, 1], [0.5, 0.5]], max_components=2
    )
    assert_allclose(got["fractions"][0], exact["mesma"], atol=1e-10, rtol=0)
    assert got["near_compositions"][0] >= 2


def test_ridge_training_and_prediction(exact):
    X = np.array([[-1.0], [1.0]])
    Y = np.array([[1.0, 0.0], [0.0, 1.0]])
    tr = TrainingTransform("full", [500.0]).fit(X)
    m = Ridge(alpha=1.0, fit_intercept=True).fit(tr.transform(X), Y)
    mean = tr.scaler.mean_.copy()
    got = m.predict(tr.transform([[0.5]]))[0]
    assert_allclose(got, exact["ridge"], atol=1e-12, rtol=0)
    assert_allclose(m.coef_.ravel(), [-1 / 3, 1 / 3], atol=1e-12, rtol=0)
    assert_allclose(m.intercept_, [0.5, 0.5], atol=1e-12, rtol=0)
    assert_allclose(tr.scaler.mean_, mean, atol=0, rtol=0)


def test_simplex_projection(exact):
    got = project_simplex([[-2.0, 1.0, 0.8]])[0]
    assert_allclose(got, exact["simplex_projection"], atol=1e-12, rtol=0)
    assert_allclose(project_simplex([got])[0], got, atol=1e-12, rtol=0)
    truth = np.array([0.2, 0.3, 0.5])
    assert np.linalg.norm(got - truth) <= np.linalg.norm(
        np.array([-2.0, 1.0, 0.8]) - truth
    )


def test_audit_axis_counterexample():
    from spectralbridge.pipelines.pipeline import _apply_landsat_brightness_adjustment
    from spectralbridge.brightness_config import load_brightness_coefficients

    cube = np.full((7, 2, 3), 100.0, dtype=np.float32)
    _apply_landsat_brightness_adjustment(cube)
    intended = 100 * (1 + load_brightness_coefficients()[1] / 100)
    assert not np.isclose(cube[0, 1, 0], intended), (
        "Audit finding changed: re-audit axis handling"
    )


def test_audit_epsilon_degenerate_srf():
    got = resample_chunk_to_sensor(
        np.ones((1, 1, 2)), np.array([400.0, 405.0]), {"b": np.array([1e-14, 0.0])}
    )
    assert got.item() < 0.02  # Not constant-preserving: sum/(sum+epsilon).


def test_median_and_clip_do_not_commute_with_mix():
    a, b = np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0])
    assert np.median(a + b) != np.median(a) + np.median(b)
    assert (
        np.clip((-1.0 + 1.0) / 2, 0, 1)
        != (np.clip(-1.0, 0, 1) + np.clip(1.0, 0, 1)) / 2
    )


def test_audit_polygon_chunk_overlap(tmp_path):
    from types import SimpleNamespace
    import pyarrow.parquet  # noqa: F401 — Load submodule explicitly; upstream lazy helper assumes it exists.
    import pandas as pd
    import rasterio
    from rasterio.transform import from_origin
    from spectralbridge.polygon_extraction import process_raster_in_chunks

    p = tmp_path / "source.tif"
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        width=3,
        height=3,
        count=2,
        dtype="float32",
        crs="EPSG:32613",
        transform=from_origin(500000, 4400000, 1, 1),
    ) as dst:
        dst.write(np.ones((2, 3, 3), dtype=np.float32))
    out = tmp_path / "pixels.parquet"
    process_raster_in_chunks(
        SimpleNamespace(path=p), None, SimpleNamespace(path=out), chunk_size=4
    )
    frame = pd.read_parquet(out)
    assert frame.pixel_id.duplicated().any(), (
        "Overlap finding changed; re-audit windows"
    )
    assert frame.pixel_id.nunique() == 9
