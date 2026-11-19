"""Patch replication and class support constrain exploratory Landsat tests."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
analysis = importlib.import_module("landsat_exploratory_pft_tests")
sys.path.remove(str(DIRECTORY))


def fixture():
    rows = []
    for c, category in enumerate(["Deciduous", "Evergreen"]):
        for patch in range(3):
            for pixel in range(4):
                rows.append(
                    dict(
                        candidate_id=f"{c}-{patch}-{pixel}",
                        patch_group_id=f"{c}-{patch}",
                        researcher_category=category,
                        region=f"region-{c}",
                        **{
                            f"B{i}": 0.02 * i
                            + 0.01 * c
                            + 0.001 * patch
                            + 0.0001 * pixel
                            for i in range(1, 8)
                        },
                    )
                )
    return pd.DataFrame(rows)


def test_duplicate_pixel_replication_does_not_create_more_test_units():
    f = fixture()
    _, patches = analysis.prepare(f, analysis.BANDS)
    _, repeated = analysis.prepare(pd.concat([f] * 5), analysis.BANDS)
    pd.testing.assert_frame_equal(patches, repeated)
    assert len(patches) == 6


def test_region_confounded_pairs_are_not_tested_as_within_region_evidence():
    _, patches = analysis.prepare(fixture(), analysis.BANDS)
    results = analysis.separability(patches, analysis.BANDS)
    pair = results.loc[results.a.eq("Deciduous") & results.b.eq("Evergreen")]
    assert pair.loc[pair.scope.str.startswith("within"), "p_npc"].isna().all()
    assert pair.loc[pair.scope.str.startswith("pooled"), "permutations"].iloc[0] == 20
    finite = results.p_npc.notna()
    assert (results.loc[finite, "p_npc_holm"] >= results.loc[finite, "p_npc"]).all()


def test_holdouts_have_one_patch_prediction_and_flag_absent_training_classes():
    cells, patches = analysis.prepare(fixture(), analysis.BANDS)
    predicted = analysis.identify(cells, patches, analysis.BANDS)
    held = predicted.loc[
        predicted.scheme.eq("leave_one_patch_out") & predicted.unit.eq("patch")
    ]
    assert len(held) == 6 and held.patch_group_id.nunique() == 6
    assert held.train_patch_count.eq(5).all()
    assert held.held_out.eq(held.patch_group_id).all()
    regional = predicted.loc[predicted.scheme.eq("leave_one_region_out")]
    # Both classes live in separate regions; train would contain only one class,
    # so no estimable logistic model is fabricated for these folds.
    assert regional.empty
    assert np.isfinite(held.train_patch_count).all()


def test_unseen_regional_class_has_unavailable_supported_recall():
    f = fixture()
    third = f.loc[f.researcher_category.eq("Evergreen")].copy()
    third["researcher_category"] = "Herbaceous"
    third["region"] = "region-2"
    third["patch_group_id"] = "third-" + third.patch_group_id
    third["candidate_id"] = "third-" + third.candidate_id
    cells, patches = analysis.prepare(
        pd.concat([f, third], ignore_index=True), analysis.BANDS
    )
    predicted = analysis.identify(cells, patches, analysis.BANDS)
    regional = predicted.loc[
        predicted.scheme.eq("leave_one_region_out") & predicted.unit.eq("patch")
    ]
    assert len(regional) == 9
    assert not regional.truth_in_training.any()
    summary = analysis.summarize(predicted)
    summary = summary.loc[summary.scheme.eq("leave_one_region_out")]
    assert summary.recall_supported.isna().all()
    assert summary.supported_n.eq(0).all()
