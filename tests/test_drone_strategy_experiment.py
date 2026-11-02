"""Analysis contracts for the isolated P161 investigation, no production changes."""

import importlib.util
from pathlib import Path
import geopandas as gpd
import numpy as np
from shapely.geometry import box

P = (
    Path(__file__).resolve().parents[1]
    / "provenance/drone-brdf-strategy/2026-11-02/analyze.py"
)
spec = importlib.util.spec_from_file_location("drone_strategy_experiment", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_repeated_angles_are_not_independent_dimensions():
    a = np.tile([1, 0.03, -0.5], (2000, 1))
    d = m.matrix_diagnostics(a)
    assert d["rank"] == 1 and not d["supported"]
    assert abs(d["stable_rank"] - 1) < 1e-12
    assert d["independent_angular_observations"] is None


def test_full_rank_alone_does_not_pass_condition_gate():
    x = np.linspace(-1, 1, 50)
    d = m.matrix_diagnostics(np.column_stack([np.ones(50), x, x + 1e-8 * x * x]))
    assert d["rank"] == 3
    assert d["condition_number"] > d["condition_limit"]
    assert not d["supported"]
    good = m.matrix_diagnostics(np.column_stack([np.ones(50), x, x * x]))
    assert good["supported"]


def test_overlapping_polygons_are_one_component_not_replicates():
    f = gpd.GeoDataFrame(
        {"GlobalID": ["c", "a", "b", "d"]},
        geometry=[
            box(0, 0, 2, 2),
            box(1, 1, 3, 3),
            box(2, 2, 4, 4),
            box(10, 10, 12, 12),
        ],
    )
    kept = m.independent_polygons(f)
    assert sorted(kept.GlobalID) == ["a", "d"]


def test_angles_and_indices_do_not_invent_finite_zero_denominators():
    assert np.isnan(m.angle_degrees(np.array([[0.0, 0.0]]), [1, 1]))[0]
    np.testing.assert_allclose(
        m.angle_degrees(np.array([[1.0, 2.0]]), [2, 4]), 0, atol=2e-6
    )
    a = np.array([[1.0, -1.0], [2, 1]])
    ix = m.ratio_index(a, 0, 1)
    assert np.isnan(ix[0])
    np.testing.assert_allclose(ix[1], 1 / 3)


def test_index_band_mapping_follows_wavelengths_after_reordering():
    wave = np.array([862, 560, 668, 705])
    assert dict((name, (i, j)) for name, i, j in m.index_band_pairs(wave)) == {
        "NDVI": (0, 2),
        "NDRE": (0, 3),
        "GNDVI": (0, 1),
    }
