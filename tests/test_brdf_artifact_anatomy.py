"""Synthetic regression controls for the isolated historical diagnostic helpers."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "provenance/brdf-artifact-anatomy/2026-11-03/analyze.py"
)
SPEC = importlib.util.spec_from_file_location("artifact_anatomy", SCRIPT)
anatomy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(anatomy)


def test_historical_guard_preserves_zero_sign_and_nonfinite_cases():
    den = np.array([-1, 0, 0.25, np.nan, np.inf, 0.25], dtype=np.float32)
    num = np.float32(2)
    factor, positive, bad = anatomy.apply_factor(den, num, np.ones(6, bool))
    np.testing.assert_array_equal(factor, [1, 1, 8, 1, 1, 8])
    np.testing.assert_array_equal(positive, [False, False, True, False, True, True])
    assert bad[4]  # Infinite prediction gives zero ratio, then identity.


@pytest.mark.parametrize("num", [0, -2, np.nan])
def test_nonpositive_or_nan_reference_takes_identity(num):
    factor, _, _ = anatomy.apply_factor(
        np.array([0.1, 2], np.float32), num, np.ones(2, bool)
    )
    np.testing.assert_array_equal(factor, [1, 1])


def test_unvisited_bin_copies_input_without_capping_visited_gain():
    den = np.array([1e-7, 1e-7], np.float32)
    factor, _, _ = anatomy.apply_factor(den, np.float32(3), np.array([True, False]))
    assert factor[0] > 1e7
    assert factor[1] == 1


def test_native_edge_comparison_requires_matching_orientation_and_support():
    state = np.zeros((4, 6), bool)
    state[:, 3:] = True
    valid = np.ones_like(state)
    out = anatomy.boundary_comparison(state, state.copy(), valid, pixel_m=0.2)
    assert out["actual_edges"] == 4
    assert out["dice"] == 1
    assert out["xor_edges"] == 0
    assert out["max_directed_edge_displacement_m"] == 0
    shifted = np.zeros_like(state)
    shifted[:, 4:] = True
    out = anatomy.boundary_comparison(state, shifted, valid, pixel_m=0.2)
    assert out["dice"] == 0
    assert out["max_directed_edge_displacement_m"] == pytest.approx(0.2)


def test_unvisited_island_has_four_edges_separate_from_main_sign_boundary():
    sign = np.ones((7, 9), bool)
    sign[:, :2] = False
    visited = np.ones_like(sign)
    visited[3, 6] = False
    output = sign & visited
    all_valid = np.ones_like(sign)
    sign_only = anatomy.boundary_comparison(output, sign, all_valid)
    assert sign_only["xor_edges"] == 4
    full = anatomy.boundary_comparison(output, sign & visited, all_valid)
    assert full["dice"] == 1
    main = anatomy.boundary_comparison(output, sign, visited)
    assert main["xor_edges"] == 0
    assert main["actual_edges"] == sign_only["predicted_edges"]
