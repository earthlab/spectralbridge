"""Synthetic contracts for paired endmember/category readiness comparisons."""

from pathlib import Path
import importlib.util

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn", reason="optional analytics extra")
pytest.importorskip("pyarrow", reason="optional source table reader")

BASE = (
    Path(__file__).resolve().parents[1]
    / "provenance/endmember-quality/2026-10-22/ies-comparison-v1"
)
spec = importlib.util.spec_from_file_location(
    "ies_comparison", BASE / "run_comparison.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_background_mapping_never_guesses_mixed_or_missing_labels():
    d = pd.DataFrame(
        dict(
            cover_category=["Non-vegetated & dead"] * 5 + ["Woody shrub"],
            cover_subcategory=[
                "Bare",
                "Rock",
                "Dead",
                "Mixed Dead / Bare / Rock",
                None,
                None,
            ],
        )
    )
    a = module.atomic_labels(d)
    assert a.iloc[:3].tolist() == ["Bare_Rock", "Bare_Rock", "Dead"]
    assert a.iloc[3:5].isna().all()
    assert a.iloc[5] == "Woody shrub"


def test_common_coarsening_is_identical_for_both_taxonomies():
    truth = np.random.default_rng(5).dirichlet(np.ones(6), size=10)
    common = truth @ module.mapping_matrix("common")
    for scheme in module.SCHEMES:
        mapped = truth @ module.mapping_matrix(scheme)
        np.testing.assert_allclose(module.coarsen(mapped, scheme), common)
        np.testing.assert_allclose(mapped.sum(1), 1)
    # A mixture of herbaceous and shrub is one revised class, not false evidence
    # of two independent revised classes; the underlying observation is unchanged.
    w = np.zeros((1, 6))
    w[0, [2, 3]] = 0.5
    assert np.count_nonzero(w @ module.mapping_matrix("revised")) == 1
    assert np.count_nonzero(w @ module.mapping_matrix("original")) == 2


def test_evaluation_bundles_exclude_selected_and_never_share_parents():
    rows = []
    for atom_index, atom in enumerate(module.ATOMS):
        for j in range(5):
            rows.append(
                dict(
                    GlobalID=f"{atom_index}:{j}",
                    atom=atom,
                    site="SITE",
                    year=2000,
                    **{
                        f"band_{b}": float(b == atom_index) + j * 0.001
                        for b in range(7)
                    },
                )
            )
    frame = pd.DataFrame(rows)
    selected = {"0:0", "1:0"}
    pool, x, truth, meta, refs = module.common_parent_targets(frame, selected, seed=3)
    assert set(pool.GlobalID).isdisjoint(selected)
    assert len(x) == 2 * 71
    seen = set()
    for bid, g in meta.groupby("bundle"):
        ids = set(g.parent_ids.iloc[0].split("|"))
        assert len(ids) == 6 and ids.isdisjoint(seen) and ids.isdisjoint(selected)
        seen.update(ids)
        use = meta.bundle.eq(bid).to_numpy()
        np.testing.assert_allclose(truth[use] @ refs[bid], x[use])
    np.testing.assert_allclose(truth.sum(1), 1)


def test_ridge_tuning_groups_are_parent_disjoint():
    atoms = np.repeat(module.ATOMS, 8)
    ids = np.array([f"{a}:{j // 2}" for a in range(6) for j in range(8)])
    e = np.random.default_rng(3).random((len(atoms), 7))
    x, truth, groups, membership = module.training_mixtures(e, atoms, ids)
    assert len(x) == 3 * 12 * 71 and len(np.unique(groups)) == 3
    sets = [set(r["parent_ids"]) for r in membership]
    assert set.union(*sets) == set(ids)
    assert all(not sets[a] & sets[b] for a in range(3) for b in range(a))
    np.testing.assert_allclose(truth.sum(1), 1)


def test_exhaustive_kernel_agrees_with_existing_small_exact_solver(tmp_path):
    rng = np.random.default_rng(17)
    e = rng.random((6, 7))
    labels = np.repeat(np.arange(3), 2)
    target = np.array([0.2, 0.3, 0.5]) @ e[[0, 2, 4]]
    fit = module.stream.search(
        target[None],
        e,
        labels,
        directory=tmp_path / "checkpoints",
        chunk_models=3,
        progress=False,
    )
    from spectralbridge.mixtures import fit_models

    reference = fit_models(target[None], labels, e, max_components=3)
    np.testing.assert_allclose(fit["fractions"], reference["fractions"], atol=1e-9)
    np.testing.assert_allclose(fit["reconstruction"], target[None], atol=1e-9)
    repeated = module.stream.search(
        target[None],
        e,
        labels,
        directory=tmp_path / "checkpoints",
        chunk_models=3,
        progress=False,
    )
    np.testing.assert_array_equal(fit["fractions"], repeated["fractions"])


def test_projection_then_merge_is_not_merge_then_projection():
    from spectralbridge.library_analysis import project_simplex

    raw = np.array([[0.2, 0.2, 0.8, 0.2, -0.4]])
    after_native = module.coarsen(project_simplex(raw), "original")
    after_common = project_simplex(module.coarsen(raw, "original"))
    assert not np.allclose(after_native, after_common)
    np.testing.assert_allclose(after_common, [[0.2, 0.2, 0.4, 0.2]])
    assert after_native.min() >= 0 and after_common.min() >= 0
    np.testing.assert_allclose(after_native.sum(1), 1)
