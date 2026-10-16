"""Controls must preserve nesting, independent identity weight and pairing."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
from spectralbridge.researcher_validation import (
    random_feature_path,
    identity_correctness,
    balanced_accuracy,
    paired_identity_interval,
)


def test_random_subsets_are_nested_unique_reproducible_and_seed_specific():
    path = random_feature_path(360, 17)
    assert np.array_equal(path, random_feature_path(360, 17))
    assert set(path) == set(range(360))
    assert set(path[:7]) < set(path[:20])
    assert not np.array_equal(path, random_feature_path(360, 18))
    with pytest.raises(ValueError):
        random_feature_path(0, 1)


def test_duplicate_acquisitions_do_not_inflate_balanced_accuracy():
    y = np.array(["a", "a", "b", "b"])
    p = np.array(["a", "b", "b", "b"])
    ids = np.array(["1", "2", "3", "4"])
    assert balanced_accuracy(y, p, ids) == 0.75
    take = [0] * 20 + [1, 2, 3]
    assert balanced_accuracy(y[take], p[take], ids[take]) == 0.75
    assert len(identity_correctness(y[take], p[take], ids[take])) == 4


def test_paired_interval_preserves_pairing_and_rejects_pseudoreplication():
    frame = pd.DataFrame(
        {
            "GlobalID": list("abcd"),
            "truth": ["a", "a", "b", "b"],
            "selected": [1, 0, 1, 1],
            "random": [0, 0, 0, 1],
        }
    )
    r = paired_identity_interval(frame, seed=3)
    assert r["difference"] == 0.5 and r["low"] <= 0.5 <= r["high"]
    frame.loc[1, "GlobalID"] = "a"
    with pytest.raises(ValueError):
        paired_identity_interval(frame)
