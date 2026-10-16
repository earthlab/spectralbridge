"""Scientific identities for paired closure and label/false-detection contracts."""

import numpy as np
import pandas as pd
import pytest
from spectralbridge.spectral_closure import (
    spectral_shape,
    paired_partition,
    paired_partition_bootstrap,
    closure_labels,
    one_vs_rest_metrics,
)


def test_balanced_partition_recovers_known_orthogonal_effects():
    # Two classes, two polygons each; uniform time shift, stable polygon effect.
    A = np.array([[0.0, 0], [2, 0], [10, 0], [12, 0]])
    B = A + [0, 3]
    r = paired_partition(A, B, ["a", "a", "b", "b"], [0.5, 0.5])
    assert r["class_SS"] == pytest.approx(100)
    assert r["polygon_within_class_SS"] == pytest.approx(4)
    assert r["year_SS"] == pytest.approx(9)
    assert r["class_by_year_SS"] == pytest.approx(0)
    assert r["residual_change_SS"] == pytest.approx(0)
    assert r["total_SS"] == pytest.approx(113)
    reverse = paired_partition(B, A, ["a", "a", "b", "b"], [0.5, 0.5])
    assert reverse == r


def test_partition_interaction_is_not_silently_called_common_year():
    A = np.array([[1.0], [3.0], [10.0], [12.0]])
    B = A + np.array([[2], [2], [-2], [-2]])
    r = paired_partition(A, B, ["a", "a", "b", "b"], [1])
    assert r["year_SS"] == 0
    assert r["class_by_year_SS"] == 8
    assert sum(
        r[k]
        for k in [
            "class_SS",
            "polygon_within_class_SS",
            "year_SS",
            "class_by_year_SS",
            "residual_change_SS",
        ]
    ) == pytest.approx(r["total_SS"])
    boot = paired_partition_bootstrap(A, B, ["a", "a", "b", "b"], [1], replicates=19)
    assert boot == paired_partition_bootstrap(
        A, B, ["a", "a", "b", "b"], [1], replicates=19
    )


def test_shape_is_scale_invariant_preserves_negative_and_does_not_mutate():
    a = np.array([[-1.0, 2, 3], [2, 3, 4]])
    old = a.copy()
    shape, amp = spectral_shape(a, [1, 2, 1])
    scaled, _ = spectral_shape(a * np.array([[3], [5]]), [1, 2, 1])
    np.testing.assert_allclose(shape, scaled)
    np.testing.assert_array_equal(a, old)
    assert shape[0, 0] < 0
    np.testing.assert_allclose(
        np.sum(shape**2 * np.array([0.25, 0.5, 0.25]), axis=1), 1
    )
    with pytest.raises(ValueError):
        spectral_shape(np.zeros((2, 3)), [1, 1, 1])


def test_hierarchy_does_not_guess_missing_taxa_or_physical_purity():
    t = pd.DataFrame(
        dict(
            species=["Pinus contorta", "Pinus", "Unidentified", None],
            pft_code=["ECT", "UNASSIGNED", "UNASSIGNED", "UNASSIGNED"],
            cover_category=["Evergreen", "Woody shrub", "Non-vegetated & dead", None],
        )
    )
    result = closure_labels(t)
    assert result.species_level.notna().sum() == 1
    assert result.broad_pft.notna().sum() == 1
    assert result.coarse_cover.iloc[2] == "Nonvegetated/dead proxy"


def test_false_positive_negative_definitions_and_undefined_precision():
    r = one_vs_rest_metrics(
        ["a", "a", "b", "b"], ["a", "b", "b", "b"], ["a", "b", "c"]
    ).set_index("label")
    assert r.loc["a", "FNR"] == 0.5 and r.loc["a", "FPR"] == 0
    assert r.loc["b", "FPR"] == 0.5 and r.loc["b", "specificity"] == 0.5
    assert np.isnan(r.loc["c", "precision"]) and np.isnan(r.loc["c", "recall"])


def test_class_intervals_resample_ids_not_repeated_rows():
    from spectralbridge.spectral_closure import cluster_rate_intervals

    y = np.array(["a", "a", "b", "b"])
    p = np.array(["a", "b", "b", "b"])
    ids = np.array(["a1", "a2", "b1", "b2"])
    first = cluster_rate_intervals(y, p, ids, ["a", "b"], replicates=39)
    repeated = cluster_rate_intervals(
        np.repeat(y, 2), np.repeat(p, 2), np.repeat(ids, 2), ["a", "b"], replicates=39
    )
    pd.testing.assert_frame_equal(first, repeated)
    assert first.iloc[0].FPR_low == 0 and first.iloc[0].FPR_high == 0
