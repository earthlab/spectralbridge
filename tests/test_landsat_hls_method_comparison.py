"""Pairwise discriminability estimates retain patch units and unavailable cases."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DIRECTORY = Path(__file__).resolve().parents[1] / "examples/publication_figures"
sys.path.insert(0, str(DIRECTORY))
methods = importlib.import_module("landsat_hls_method_comparison")
expansion = importlib.import_module("landsat_hls_reference_expansion")
sys.path.remove(str(DIRECTORY))


def test_pairwise_balanced_accuracy_weights_classes_not_patch_counts():
    rows = []
    for label, base, count in [("Deciduous", 0.0, 2), ("Evergreen", 10.0, 5)]:
        for index in range(count):
            rows.append(
                dict(
                    patch_group_id=f"{label}-{index}",
                    researcher_category=label,
                    **{band: base + 0.01 * index for band in methods.BANDS},
                )
            )
    scores, predictions = methods.pairwise_prediction(pd.DataFrame(rows))
    pair = scores.loc[scores.a.eq("Deciduous") & scores.b.eq("Evergreen")].iloc[0]
    assert pair.balanced_accuracy == 1 and pair.n_a == 2 and pair.n_b == 5
    held = predictions.loc[
        predictions.a.eq("Deciduous") & predictions.b.eq("Evergreen")
    ]
    assert len(held) == 7 and held.patch_group_id.nunique() == 7
    assert held.train_patches.eq(6).all() and not held.held_patch_in_training.any()


def test_single_patch_class_does_not_produce_pairwise_accuracy():
    rows = []
    for label, count in [("Deciduous", 1), ("Evergreen", 3)]:
        for index in range(count):
            rows.append(
                dict(
                    patch_group_id=f"{label}-{index}",
                    researcher_category=label,
                    **{band: float(index) for band in methods.BANDS},
                )
            )
    scores, _ = methods.pairwise_prediction(pd.DataFrame(rows))
    pair = scores.loc[scores.a.eq("Deciduous") & scores.b.eq("Evergreen")].iloc[0]
    assert (
        np.isnan(pair.balanced_accuracy) and pair.status == "insufficient_patch_support"
    )


def test_mean_pairwise_estimate_retains_range_and_available_denominator():
    table = pd.DataFrame([dict(researcher_category="Deciduous")])
    pairs = pd.DataFrame(
        [
            dict(a="Deciduous", b=b, balanced_accuracy=v)
            for b, v in [
                ("Evergreen", 0.7),
                ("Herbaceous", 0.9),
                ("Woody shrub", np.nan),
            ]
        ]
    )
    result = methods.add_pairwise_estimates(table, pairs).iloc[0]
    assert np.isclose(result.pairwise_mean_ba, 0.8)
    assert result.pairwise_min_ba == 0.7 and result.pairwise_max_ba == 0.9
    assert result.pairwise_estimated_pairs == 2


def test_changed_parent_cannot_reuse_copied_regional_reference_tables(
    tmp_path, monkeypatch
):
    import pytest

    parent = tmp_path / "parent"
    parent.mkdir()
    dest = tmp_path / "expanded"
    dest.mkdir()
    monkeypatch.setattr(expansion, "PARENT", parent)
    monkeypatch.setattr(expansion, "OUTPUT", dest)
    (parent / "manifest.json").write_text('{"version": 1}')
    (parent / "hls_l30_nominal_95pct_observations.csv").write_text("original")
    expansion.validate_parent()
    expansion.validate_parent()
    (parent / "manifest.json").write_text('{"version": 2}')
    with pytest.raises(ValueError, match="Parent HLS stage changed"):
        expansion.validate_parent()
