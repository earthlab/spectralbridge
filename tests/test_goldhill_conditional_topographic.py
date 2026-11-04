"""Synthetic tests for the isolated hypothesis workflow and production boundary."""

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

PATH = (
    Path(__file__).resolve().parents[1]
    / "provenance/goldhill-conditional-topographic/2026-11-03/experiment.py"
)
spec = importlib.util.spec_from_file_location("p171_experiment_test", PATH)
exp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = exp
spec.loader.exec_module(exp)


def fixture(scale=1):
    yy, xx = np.indices((12, 15))
    geometry = {
        "slope": np.deg2rad(5 + xx * 2).astype("float32"),
        "aspect": (yy / 12 * 2 * np.pi).astype("float32"),
        "solar_zn": np.full((12, 15), 0.5, np.float32),
        "solar_az": np.full((12, 15), 2.0, np.float32),
    }
    ci = exp.current.calc_cosine_i(
        geometry["solar_zn"],
        geometry["solar_az"],
        geometry["aspect"],
        geometry["slope"],
    )
    data = (
        np.stack([0.15 * ci + 0.07, 0.4 * ci + 0.03], axis=-1).astype("float32") / scale
    )
    mask = np.ones(ci.shape, bool)
    mask[0, 0] = False
    return exp.Cube(data, mask, geometry, scale)


def test_hypothesis_still_rejected_by_production():
    cube = fixture()
    assert cube.radiometry.status == "HYPOTHETICAL_UNVERIFIED"
    with pytest.raises(ValueError, match="HYPOTHETICAL_UNVERIFIED"):
        exp.current.fit_scs_c_coefficients(cube)
    with pytest.raises(ValueError):
        cube.radiometry.require_valid()


def test_adapter_retains_actual_scientific_bytecode():
    original = exp.current.fit_scs_c_coefficients
    clone = exp.isolated(original)
    assert clone.__code__ is original.__code__
    assert clone.__globals__ is not original.__globals__
    assert (
        clone.__globals__["require_radiometry"]
        is not original.__globals__["require_radiometry"]
    )


def test_scale_invariance_once_and_mask_preservation():
    a, b = fixture(), fixture(exp.SCALE)
    fit = exp.isolated(exp.current.fit_scs_c_coefficients)
    ca, cb = fit(a, chunk_y=4), fit(b, chunk_y=4)
    np.testing.assert_allclose(ca, cb, atol=2e-6)
    apply = exp.isolated(exp.current.apply_topo_correct)
    qa = apply(a, a.data, 0, 12, 0, 15, scs_c=ca)
    qb = apply(b, b.data, 0, 12, 0, 15, scs_c=cb)
    np.testing.assert_allclose(
        qa, b.radiometry.to_physical(qb), atol=1e-6, equal_nan=True
    )
    assert np.isnan(qa[0, 0]).all()
    assert np.all(np.isfinite(qa[1:]))


def test_denominator_uncertainty_rejects_pole_without_factor_cap():
    ci = np.array([0.35, 0.45, 0.8, -0.1])
    ref = np.full(4, 0.7)
    support = exp.denominator_support(
        ci, ref, -0.347, -0.4, -0.3, 0, 1, np.ones(4, bool)
    )
    np.testing.assert_array_equal(support, [False, True, True, False])
    # Numerically large but resolved positive denominators are not gain-clipped.
    support = exp.denominator_support(
        np.array([0.002]), np.array([0.9]), 0, 0, 0, 0, 1, np.array([True])
    )
    assert support[0]
    assert exp.current._scs_c_ratio(np.array([0.9]), np.array([0.002]))[0] > 400
