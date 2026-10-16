"""Scientific display reductions preserve domain support and weighting semantics."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("matplotlib")
from examples.manuscript_synthesis.figure_data import (
    summarize_effects,
    summarize_calibration,
)
from examples.manuscript_synthesis.palette import PALETTE
from examples.manuscript_synthesis.build_figure import segments


def test_effect_map_requires_all_cohorts_and_preserves_signed_median():
    f = pd.DataFrame(
        {
            "pair": ["a / b"] * 4,
            "wavelength_nm": [500] * 4,
            "matched_effect": [-2, -1, 3, 4],
            "adjusted_p": [0.01] * 4,
        }
    )
    row = summarize_effects(f).iloc[0]
    assert row.effect == 1 and not row.same_direction and not row.consistent_evidence
    assert (
        row.minimum_effect == -2
        and row.maximum_effect == 4
        and row.supported_cohorts == 4
    )
    with pytest.raises(ValueError):
        summarize_effects(f.iloc[:3])


def test_faint_effect_cells_are_not_pooled_or_averaged_p_values():
    f = pd.DataFrame(
        {
            "pair": ["a / b"] * 4,
            "wavelength_nm": [500] * 4,
            "matched_effect": [1, 2, 3, 4],
            "adjusted_p": [0.001, 0.001, 0.001, 0.051],
        }
    )
    r = summarize_effects(f).iloc[0]
    assert r.effect == 2.5 and r.supported_cohorts == 3 and not r.consistent_evidence
    f["adjusted_p"] = 0.049
    assert summarize_effects(f).consistent_evidence.all()


def test_calibration_keeps_equal_held_site_weight_instead_of_pooling_rows():
    f = pd.DataFrame(
        {
            "kind": ["site"] * 3,
            "representation": ["NEON"] * 3,
            "method": ["Ridge"] * 3,
            "researcher_category": ["Evergreen"] * 3,
            "true_fraction": [0.5] * 3,
            "prediction_mean": [0.1, 0.2, 0.9],
            "fold": ["A", "B", "C"],
            "N": [1, 1, 1000],
        }
    )
    r = summarize_calibration(f).iloc[0]
    assert r.prediction_mean == pytest.approx(0.4)
    assert r.fold_count == 3
    assert abs(r.prediction_mean - np.average(f.prediction_mean, weights=f.N)) > 0.4


def test_plot_segments_do_not_cross_atmospheric_gaps():
    w = np.array([1325, 1330, 1335, 1455, 1460, 1785, 2005, 2010])
    result = segments(w)
    assert [r.tolist() for r in result] == [[0, 1, 2], [3, 4], [5], [6, 7]]


def test_exact_cornflower_blue_has_one_categorical_meaning():
    def values(d):
        for v in d.values():
            if isinstance(v, dict):
                yield from values(v)
            else:
                yield v

    assert sum(v == "#6495ED" for v in values(PALETTE)) == 1
    assert PALETTE["selected"] == "#6495ED"
    assert PALETTE["models"]["MESMA15"] != PALETTE["models"]["Ridge120"]
