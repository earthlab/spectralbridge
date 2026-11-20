"""A common-unit bridge preserves predictions and prevents double conversion."""

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

DIRECTORY = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location(
    "physical_aop_registry", DIRECTORY / "build_physical_aop_translation_registry.py"
)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
sys.path.remove(str(DIRECTORY))


def fixture():
    return dict(
        coefficient_set_version="fixture",
        records=[
            dict(
                slope=0.9,
                intercept=-25.0,
                rmse=10.0,
                worst_loso_rmse=20.0,
                x_min=0.0,
                x_mean=2000.0,
                x_max=10000.0,
                r2=0.95,
                status="caution",
                coefficient_set_version="fixture",
            )
        ],
    )


def test_change_of_units_preserves_predictions_and_dimensionless_evidence():
    original = fixture()
    converted = bridge.convert_common_divisor(
        original, 10000, {"verified_header": "fixture"}
    )
    old = original["records"][0]
    new = converted["records"][0]
    x = np.array([0, 0.1, 0.5, 1.0])
    np.testing.assert_allclose(
        new["slope"] * x + new["intercept"],
        (old["slope"] * (x * 10000) + old["intercept"]) / 10000,
    )
    assert (
        new["intercept"] == -0.0025
        and new["rmse"] == 0.001
        and new["worst_loso_rmse"] == 0.002
    )
    assert (
        new["x_mean"] == 0.2
        and new["r2"] == old["r2"]
        and new["status"] == old["status"]
    )
    assert (
        original["records"][0]["intercept"] == -25
        and "reflectance_units" not in original
    )


def test_unit_bridge_refuses_duplicate_or_invalid_conversion():
    converted = bridge.convert_common_divisor(fixture(), 10000, {})
    with pytest.raises(ValueError, match="double conversion"):
        bridge.convert_common_divisor(converted, 10000, {})
    for invalid in [0, -1, np.nan, np.inf]:
        with pytest.raises(ValueError, match="divisor"):
            bridge.convert_common_divisor(fixture(), invalid, {})
