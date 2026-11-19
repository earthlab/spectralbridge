"""Geography-conditioned null assignments preserve the observed design."""

import importlib
import sys
from pathlib import Path

import numpy as np

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
audit = importlib.import_module("landsat_design_audit")
sys.path.remove(str(DIRECTORY))


def test_assignments_preserve_region_counts_and_include_identity_once():
    labels = np.array(["D", "D", "H", "D", "H", "H", "E", "E"])
    regions = np.array(["a"] * 3 + ["b"] * 3 + ["c"] * 2)
    ensemble = audit.region_assignments(labels, regions)
    assert len(ensemble) == 9
    assert np.array_equal(ensemble[0], labels)
    assert (ensemble == labels).all(axis=1).sum() == 1
    assert len(set(map(tuple, ensemble))) == 9
    for assigned in ensemble:
        for region in set(regions):
            assert sorted(assigned[regions == region]) == sorted(
                labels[regions == region]
            )


def test_balanced_six_patch_resolution_can_reach_first_ten_pair_holm_gate():
    from math import comb

    assert 2 / comb(10, 5) > 0.05 / 10
    assert 2 / comb(12, 6) <= 0.05 / 10


def test_large_pure_region_does_not_enumerate_factorial_duplicates():
    labels = np.array(["E"] * 50)
    ensemble = audit.region_assignments(labels, np.array(["one"] * 50))
    assert ensemble.shape == (1, 50)


def test_exact_budget_is_checked_before_generating_assignments():
    import pytest

    with pytest.raises(ValueError, match="budget exceeded"):
        audit.region_assignments(
            np.array(["a"] * 4 + ["b"] * 4 + ["c"] * 4), np.array(["one"] * 12)
        )
