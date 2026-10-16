"""Machine-equivalent truth fractions must combine counts and squared errors."""

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")


def test_calibration_collapses_equivalent_fractions_without_equal_weighting(
    monkeypatch,
):
    base = (
        Path(__file__).resolve().parents[1]
        / "provenance/researcher-evidence/2026-10-16/v1"
    )
    monkeypatch.syspath_prepend(str(base))
    spec = importlib.util.spec_from_file_location(
        "fraction_calibration", base / "prepare_calibration.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frame = pd.DataFrame(
        {
            "fold": ["f", "f"],
            "kind": ["plant", "plant"],
            "target": ["t", "t"],
            "method": ["Ridge", "Ridge"],
            "representation": ["NEON", "NEON"],
            "researcher_category": ["Evergreen", "Evergreen"],
            "true_fraction": [0.1, 0.10000000000000002],
            "N": [1, 3],
            "prediction_mean": [0.0, 1.0],
            "bias": [-0.1, 0.9],
            "MAE": [0.1, 0.9],
            "detection_probability": [0.0, 1.0],
            "RMSE": [0.1, 0.9],
        }
    )
    saved = frame.copy(deep=True)
    result = module.collapse_fraction_grid(frame)
    assert len(result) == 1 and result.N.iloc[0] == 4
    assert result.prediction_mean.iloc[0] == 0.75
    assert result.detection_probability.iloc[0] == 0.75
    assert result.RMSE.iloc[0] == pytest.approx(np.sqrt((0.01 + 3 * 0.81) / 4))
    pd.testing.assert_frame_equal(frame, saved)
