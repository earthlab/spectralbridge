"""Paired mask comparisons use shared pixels and whole held-out polygons."""

import importlib
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
comparison = importlib.import_module("compare_drone_mask_pft_information")
sys.path.pop(0)


def test_shared_pixel_medians_use_identical_intersection_and_keep_coverage():
    a = np.repeat([[1.0], [3.0], [100.0], [9.0]], 5, axis=1)
    b = a.copy()
    b[2] = np.nan
    labels = pd.DataFrame(
        {"GlobalID": ["p", "p", "p", "q"], "cover_category": ["Evergreen"] * 4}
    )
    spectra, coverage = comparison.polygon_medians(a, b, labels)
    primary = spectra[
        (spectra.GlobalID == "p") & (spectra.population == "shared_pixels")
    ]
    assert primary.B1.tolist() == [2, 2]
    own = spectra[(spectra.GlobalID == "p") & (spectra.population == "retained_pixels")]
    assert own.B1.tolist() == [3, 2]
    assert coverage.iloc[0].null_pixels == 3 and coverage.iloc[0].mask10_pixels == 2


def test_identical_arms_have_zero_effect_and_accuracy_change():
    rng = np.random.default_rng(9)
    a = rng.normal(size=(20, 5))
    z = np.tile([0, 1], 10)
    effect = comparison.effect_change(
        a, a, z, np.repeat(["a", "b"], 10), 4, permutations=39
    )
    assert effect["effect_delta"] == 0 and effect["p_loss"] == 1
    records = []
    for arm in ["null", "mask10"]:
        for i in range(10):
            records.append(
                dict(arm=arm, GlobalID=str(i), truth=str(i % 2), prediction=str(i % 2))
            )
    accuracy = comparison.paired_accuracy(pd.DataFrame(records), 3, permutations=39)
    assert accuracy["delta_ba"] == 0 and accuracy["p_loss"] == 1


def test_paired_loss_direction_and_class_balancing():
    rows = []
    for arm in ["null", "mask10"]:
        for i in range(20):
            rows.append(
                dict(
                    arm=arm,
                    GlobalID=f"p{i:02}",
                    truth=str(i % 2),
                    prediction=str(i % 2) if arm == "null" else str(1 - i % 2),
                )
            )
    result = comparison.paired_accuracy(pd.DataFrame(rows), 8, permutations=999)
    assert np.isclose(result["delta_ba"], -1) and result["p_loss"] <= 0.005


def test_csv_arm_names_are_not_parsed_as_missing(tmp_path):
    path = tmp_path / "result.csv"
    comparison.write_table(
        pd.DataFrame({"arm": ["null", "mask10"], "score": [1, 2]}), path
    )
    restored = pd.read_csv(path)
    assert restored.arm.tolist() == ["unmasked", "mask10"]
