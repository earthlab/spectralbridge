"""A single patch cannot produce a held-class accuracy or a pairwise test."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
hls = importlib.import_module("landsat_hls_pft_tests")
sys.path.remove(str(DIRECTORY))


def test_unseen_training_class_is_unavailable_not_zero_accuracy():
    pairs = pd.DataFrame(
        [
            dict(
                scope="pooled_patches_region_confounded",
                a="Woody shrub",
                b="Evergreen",
                p_npc=np.nan,
                p_npc_holm=np.nan,
            )
        ]
    )
    predictions = pd.DataFrame(
        [
            dict(
                unit="patch",
                scheme="leave_one_patch_out",
                truth="Woody shrub",
                prediction="Evergreen",
                truth_in_training=False,
            )
        ]
    )
    result = hls.table_summary(pairs, predictions).set_index("researcher_category")
    row = result.loc["Woody shrub"]
    assert row.tested_pairs == 0 and row.separability_status == "insufficient_patches"
    assert row.supported_test_patches == 0 and np.isnan(row.held_patch_recall)
    assert row.held_patches == 1


def test_testable_pair_denominator_and_supported_recall_remain_explicit():
    pairs = pd.DataFrame(
        [
            dict(
                scope="pooled_patches_region_confounded",
                a="Deciduous",
                b="Evergreen",
                p_npc=0.1,
                p_npc_holm=1.0,
            ),
            dict(
                scope="pooled_patches_region_confounded",
                a="Deciduous",
                b="Woody shrub",
                p_npc=np.nan,
                p_npc_holm=np.nan,
            ),
        ]
    )
    predictions = pd.DataFrame(
        [
            dict(
                unit="patch",
                scheme="leave_one_patch_out",
                truth="Deciduous",
                prediction=p,
                truth_in_training=True,
            )
            for p in ["Deciduous", "Evergreen"]
        ]
    )
    row = (
        hls.table_summary(pairs, predictions)
        .set_index("researcher_category")
        .loc["Deciduous"]
    )
    assert row.tested_pairs == 1 and row.planned_pairs == 2 and row.supported_pairs == 0
    assert row.held_patch_recall == 0.5 and row.correct_supported_patches == 1
