"""Small controls for the source-specific fixed-library experiment, not its data."""

from pathlib import Path
import importlib.util
import sys
import numpy as np
import pandas as pd

PATH = (
    Path(__file__).resolve().parents[1] / "provenance/endmember-quality/2026-10-19/v1"
)
sys.path.insert(0, str(PATH))
spec = importlib.util.spec_from_file_location(
    "endmember_quality", PATH / "run_analysis.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.path.pop(0)


def test_random_control_preserves_exact_parent_counts_and_class_counts():
    identities = np.repeat(np.arange(8), 5)
    selected = np.array([0, 1, 8, 12, 14, 15, 28])
    draw = module.matched_random_indices(selected, identities, np.random.default_rng(9))
    np.testing.assert_array_equal(
        np.unique(identities[draw], return_counts=True),
        np.unique(identities[selected], return_counts=True),
    )
    assert len(np.unique(draw)) == len(selected)
    np.testing.assert_array_equal(
        draw,
        module.matched_random_indices(selected, identities, np.random.default_rng(9)),
    )


def test_coverage_is_identity_weighted_not_pixel_weighted():
    classes = module.CLASSES
    e = np.eye(5)
    y = np.r_[classes, np.repeat(classes[0], 9)]
    x = np.vstack([e, np.repeat(e[1:2], 9, axis=0)])
    ids = np.r_[np.arange(5), np.repeat(0, 9)]
    rows, detail = module.coverage(x, y, e, classes, ids)
    assert np.isclose(rows.recall.iloc[0], 0.1)
    assert np.isclose(detail["weights"][ids == 0].sum(), 1)
    assert np.isclose(rows.recall.iloc[1], 1)


def test_cross_class_hull_certificate_checks_constraints_and_class_order():
    classes = module.CLASSES[:3]
    e = np.array([[1.0, 0], [0, 1], [0.5, 0.5]])
    result = module.cross_class_certificate(e[2], classes[2], e, classes)
    assert result["feasible"]
    np.testing.assert_allclose(result["class_fractions"], [0.5, 0.5, 0, 0, 0])
    np.testing.assert_allclose(
        result["weights"] @ e[result["local_indices"]], e[2], atol=1e-8
    )
    impossible = module.cross_class_certificate([2, 2], classes[2], e, classes)
    assert not impossible["feasible"] and impossible["status"] == 2


def test_synthetic_bundles_never_share_parent_and_store_truth():
    rows = []
    for year in [2020, 2023]:
        for c, category in enumerate(module.CLASSES):
            for parent in range(4):
                rows.append(
                    dict(
                        GlobalID=f"{year}:{c}:{parent}",
                        category=category,
                        site="SITE",
                        year=year,
                        **{f"b{j}": float(j == c) for j in range(5)},
                    )
                )
    frame = pd.DataFrame(rows)
    bands = [f"b{j}" for j in range(5)]
    x, truth, meta, parents = module.make_bundle_targets(
        frame, bands, seed=2, bundles_per_domain=2
    )
    assert len(x) == 4 * 45 and meta.bundle.nunique() == 4
    np.testing.assert_allclose(truth.sum(1), 1)
    np.testing.assert_allclose(np.einsum("ij,ijk->ik", truth, parents), x)
    seen = set()
    for _, group in meta.groupby("bundle"):
        assert group.parent_ids.nunique() == 1
        ids = set(group.parent_ids.iloc[0].split("|"))
        assert len(ids) == 5 and seen.isdisjoint(ids)
        seen.update(ids)


def test_label_loader_accepts_only_string_numpy_array(tmp_path):
    import pytest

    p = tmp_path / "labels.npy"
    np.save(p, np.array(["A", "B"], object))
    np.testing.assert_array_equal(module.read_labels(p), ["A", "B"])
    np.save(p, np.array([1, 2]))
    with pytest.raises(ValueError, match="string"):
        module.read_labels(p)
