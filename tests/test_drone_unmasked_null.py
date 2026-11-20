"""The research null preserves failed QA and never substitutes identity values."""

import importlib
from pathlib import Path
import sys

import numpy as np
import pytest

DIRECTORY = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(DIRECTORY))
null = importlib.import_module("run_unmasked_drone_translation_null")
sys.path.remove(str(DIRECTORY))


def model():
    return dict(
        ndvi_binning_enabled=False,
        reference_design=[1, 0, 0],
        validation=dict(
            status="INVALID",
            fits=[
                dict(
                    band=0,
                    bin=0,
                    rank=3,
                    status="INVALID",
                    diagnostic_coefficient_estimate=[1, 1, 0],
                )
            ],
        ),
    )


def test_null_uses_failed_fit_estimate_without_mutating_status():
    record = model()
    values = np.full((1, 3, 1), 2, np.float32)
    design = np.array([[[1, 1, 0], [1, -1, 0], [1, -2, 0]]], float)
    actual, qa = null.diagnostic_brdf(values, design, record)
    assert actual[0, 0, 0] == 1
    assert np.isnan(actual[0, 1:, 0]).all()
    assert record["validation"]["status"] == "INVALID"
    assert qa[0]["original_fit_status"] == "INVALID"
    assert qa[0]["numerical_exclusions"] == 2


def test_null_preserves_nodata_and_refuses_missing_fits():
    record = model()
    actual, _ = null.diagnostic_brdf(
        np.array([[[np.nan]]], np.float32), np.array([[[1, 0, 0]]]), record
    )
    assert np.isnan(actual).all()
    record["validation"]["fits"][0]["rank"] = 2
    with pytest.raises(ValueError, match="full-rank"):
        null.diagnostic_brdf(
            np.ones((1, 1, 1), np.float32), np.array([[[1, 0, 0]]]), record
        )
