"""Power planning respects exchangeability; new data never overwrite the parent."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
power = importlib.import_module("landsat_hls_power_planning")
build = importlib.import_module("landsat_hls_power_reference_build")
annotation = importlib.import_module("landsat_photo_annotation")
sys.path.remove(str(DIRECTORY))


def test_small_design_enumerates_every_block_assignment_once():
    labels, ensemble = power.label_ensemble(2, 3, 1000, np.random.default_rng(6))
    assert ensemble.shape == (216, 12)
    assert len(np.unique(ensemble, axis=0)) == 216
    np.testing.assert_array_equal(ensemble[0], labels)
    assert (ensemble.reshape(216, 3, 4).sum(axis=2) == 2).all()
    # Complement symmetry prevents a nominal .005 result with this small design.
    values = np.random.default_rng(2).normal(size=(12, 7)) + labels[:, None] * 100
    assert power.npc_p(values, labels, ensemble, np.repeat(range(3), 4)) >= 2 / 216


def test_power_npc_matches_original_exact_statistic():
    rng = np.random.default_rng(14)
    labels, ensemble = power.label_ensemble(2, 2, 1000, rng)
    values = rng.normal(size=(8, 7)) + labels[:, None]
    blocks = np.repeat(range(2), 4)
    original = annotation.exact_statistics(values, labels, blocks)
    assert power.npc_p(values, labels, ensemble, blocks) == pytest.approx(
        original["p_npc"]
    )


def test_random_design_preserves_block_counts_and_is_reproducible():
    labels, ensemble = power.label_ensemble(4, 3, 50, np.random.default_rng(8))
    _, repeated = power.label_ensemble(4, 3, 50, np.random.default_rng(8))
    np.testing.assert_array_equal(ensemble, repeated)
    np.testing.assert_array_equal(ensemble[0], labels)
    assert (ensemble.reshape(50, 3, 8).sum(axis=2) == 4).all()


def test_planning_target_uses_uncertainty_not_point_estimate():
    assert power.wilson(83, 100)[0] < 0.8
    assert power.wilson(91, 100)[0] > 0.8


def test_append_preserves_old_values_and_rejects_repeated_physical_cell():
    parent = pd.DataFrame(dict(candidate_id=["old"], aerial_year=[2023], B1=[0.123]))
    addition = pd.DataFrame(dict(candidate_id=["new"], aerial_year=[2023], B1=[0.456]))
    result = build.combine_tables(parent, addition, ["candidate_id", "aerial_year"])
    pd.testing.assert_series_equal(result.iloc[0], parent.iloc[0])
    with pytest.raises(ValueError, match="Repeated physical identity"):
        build.combine_tables(parent, parent, ["candidate_id", "aerial_year"])


def test_changed_frozen_source_fails_before_new_reference_geometry(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(build, "REVIEW", tmp_path / "review")
    monkeypatch.setattr(build, "PARENT", tmp_path / "parent")
    monkeypatch.setattr(build, "review_specification", lambda: [])
    build.PARENT.mkdir()
    (build.PARENT / "manifest.json").write_text("{}")
    source = build.PARENT / "hls_l30_nominal_95pct_observations.csv"
    source.write_text("old")
    build.freeze()
    source.write_text("changed")
    with pytest.raises(ValueError, match="Frozen review changed"):
        build.freeze()


def test_bounded_analysis_retains_exact_small_design_and_limits_large_space():
    sys.path.insert(0, str(DIRECTORY))
    analysis = importlib.import_module("landsat_hls_power_analysis")
    sys.path.remove(str(DIRECTORY))
    rng = np.random.default_rng(22)
    labels = np.r_[np.zeros(3), np.ones(3)]
    values = rng.normal(size=(6, 7)) + labels[:, None]
    blocks = np.zeros(6, int)
    expected = annotation.exact_statistics(values, labels, blocks)
    actual = analysis.bounded_statistics(values, labels, blocks)
    assert actual["permutation_method"] == "exact"
    assert actual["p_npc"] == expected["p_npc"]
    # Force the large-space route; use fewer draws only in this synthetic test.
    original = analysis.DRAW_COUNT
    analysis.DRAW_COUNT = 200
    try:
        labels = np.r_[np.zeros(11), np.ones(11)]
        values = rng.normal(size=(22, 7)) + labels[:, None] * 10
        blocks = np.repeat(range(2), 11)
        # Both blocks need mixed labels; alternate labels within each block.
        labels = np.tile([0, 1], 11)
        values = rng.normal(size=(22, 7)) + labels[:, None] * 10
        first = analysis.bounded_statistics(values, labels, blocks)
        second = analysis.bounded_statistics(values, labels, blocks)
        assert first == second
        assert first["permutation_method"].startswith("monte_carlo")
        assert first["permutations"] == 200
        assert first["label_space_size"] > 100000
        assert 1 / 200 <= first["p_npc"] <= 0.05
    finally:
        analysis.DRAW_COUNT = original
